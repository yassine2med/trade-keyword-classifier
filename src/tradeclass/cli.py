"""Command line entry: python -m tradeclass ..."""
from __future__ import annotations

import argparse
import csv
import json
import sys

from .classifier import classify, load_rules


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="tradeclass", description="Map descriptions to trades")
    parser.add_argument("--rules", help="JSON file of {trade: {keyword: weight}} replacing the defaults")
    sub = parser.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("text", help="classify one description")
    one.add_argument("description")
    one.add_argument("--top", type=int, default=3, help="how many ranked trades to show")
    batch = sub.add_parser("file", help="classify the description column of a CSV")
    batch.add_argument("csv")
    batch.add_argument("--column", default="description")
    batch.add_argument("--json", action="store_true", help="print JSON instead of a table")
    sub.add_parser("trades", help="list trades and keyword counts")
    args = parser.parse_args(argv)
    try:
        rules = load_rules(args.rules)
        if args.cmd == "trades":
            for trade, words in rules.items():
                print(f"{trade:<16}{len(words)} keywords")
        elif args.cmd == "text":
            res = classify(args.description, rules)
            print(f"Trade: {res.trade} (score {res.score}, confidence {res.confidence:.0%})")
            print("Matched: " + (", ".join(res.matched) or "none"))
            for trade, score in res.ranking[: args.top]:
                print(f"  {trade:<16}{score}")
        else:
            return _file(args, rules)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _file(args: argparse.Namespace, rules: dict) -> int:
    """Classify every row of a CSV."""
    with open(args.csv, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if rows and args.column not in rows[0]:
        raise ValueError(f"column {args.column!r} not found; columns: {', '.join(rows[0])}")
    out = []
    for row in rows:
        res = classify(row[args.column], rules)
        out.append({"id": row.get("id", ""), "trade": res.trade, "confidence": res.confidence,
                    "description": row[args.column]})
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"{'ID':<8}{'Trade':<16}{'Conf':<6}Description")
    for item in out:
        print(f"{item['id']:<8}{item['trade']:<16}{item['confidence']:<6.0%}{item['description'][:60]}")
    counts: dict[str, int] = {}
    for item in out:
        counts[item["trade"]] = counts.get(item["trade"], 0) + 1
    print("\n" + ", ".join(f"{t}: {n}" for t, n in sorted(counts.items(), key=lambda kv: -kv[1])))
    return 0
