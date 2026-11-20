"""Keyword scoring that maps a maintenance description to a trade."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RULES: dict[str, dict[str, int]] = {
    "HVAC": {"hvac": 3, "air conditioning": 3, "thermostat": 3, "ac unit": 3, "chiller": 3,
             "boiler": 3, "vav": 3, "ventilation": 2, "too hot": 2, "too cold": 2,
             "heating": 2, "cooling": 2, "airflow": 2, "duct": 2, "filter": 1, "fan": 1},
    "Plumbing": {"leak": 3, "toilet": 3, "sink": 3, "faucet": 3, "drain": 3, "clog": 3,
                 "pipe": 3, "water heater": 3, "flood": 3, "urinal": 3, "sewer": 3,
                 "water pressure": 2, "no hot water": 3, "backflow": 2, "water": 1},
    "Electrical": {"outlet": 3, "breaker": 3, "light": 2, "lighting": 2, "lamp": 2, "power": 2,
                   "switch": 2, "circuit": 3, "wiring": 3, "sparks": 3, "panel": 2,
                   "ballast": 3, "flickering": 3, "generator": 2, "exit sign": 2},
    "Carpentry": {"door": 2, "hinge": 3, "ceiling tile": 3, "drywall": 3, "cabinet": 3,
                  "shelf": 2, "window": 2, "lock": 2, "handle": 2, "wall": 1, "floor": 1,
                  "baseboard": 3},
    "Elevator": {"elevator": 4, "lift": 2, "escalator": 4, "stuck between floors": 4},
    "Custodial": {"spill": 3, "trash": 3, "cleaning": 3, "restroom supplies": 3, "dirty": 3,
                  "carpet stain": 3, "paper towel": 3, "soap": 2, "janitor": 3, "odor": 2},
    "Grounds": {"parking lot": 3, "snow": 3, "ice": 2, "landscaping": 3, "sidewalk": 3,
                "tree": 3, "grass": 3, "pothole": 3, "gutter": 2, "irrigation": 3},
    "Pest Control": {"mice": 4, "mouse": 4, "rat": 3, "roach": 4, "ants": 3, "bugs": 3,
                     "pest": 4, "wasp": 3, "bees": 3, "droppings": 3},
    "Fire and Safety": {"fire alarm": 4, "sprinkler": 4, "extinguisher": 4, "smoke detector": 4,
                        "emergency light": 3, "fire door": 3, "eyewash": 3},
}


@dataclass(frozen=True)
class Result:
    """Outcome of classifying one description."""
    trade: str
    score: int
    confidence: float
    ranking: list[tuple[str, int]]
    matched: list[str]


def load_rules(path: str | Path | None) -> dict[str, dict[str, int]]:
    """Load rules from a JSON file of {trade: {keyword: weight}}, or return the defaults."""
    if path is None:
        return DEFAULT_RULES
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("rules file must be a non-empty JSON object")
    rules: dict[str, dict[str, int]] = {}
    for trade, words in data.items():
        if not isinstance(words, dict) or not all(isinstance(w, int) and w > 0 for w in words.values()):
            raise ValueError(f"rules for {trade!r} must map keyword to a positive integer weight")
        rules[trade] = {k.lower(): v for k, v in words.items()}
    return rules


def _contains(text: str, keyword: str) -> bool:
    """Whole-word match (optional plural s), so a short keyword does not fire inside a longer word."""
    return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?:s|es)?(?![a-z0-9])", text) is not None


def classify(description: str, rules: dict[str, dict[str, int]] | None = None,
             fallback: str = "General") -> Result:
    """Score every trade and return the best one.

    Confidence is the winner's share of all points scored. With no keyword hit the
    result is the fallback trade with score 0.
    """
    rules = rules or DEFAULT_RULES
    text = " ".join(description.lower().split())
    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    for trade, words in rules.items():
        for word, weight in words.items():
            if _contains(text, word):
                scores[trade] = scores.get(trade, 0) + weight
                matched.setdefault(trade, []).append(word)
    if not scores:
        return Result(fallback, 0, 0.0, [], [])
    ranking = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best, best_score = ranking[0]
    return Result(best, best_score, round(best_score / sum(scores.values()), 2), ranking, matched[best])
