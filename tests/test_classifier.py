import json

import pytest

from tradeclass.classifier import classify, load_rules
from tradeclass.cli import main


def test_hvac():
    assert classify("The thermostat is broken and it is too hot").trade == "HVAC"


def test_plumbing():
    assert classify("Toilet is clogged and leaking").trade == "Plumbing"


def test_electrical():
    assert classify("outlet sparks near the breaker panel").trade == "Electrical"


def test_no_match_falls_back():
    res = classify("repaint my nameplate")
    assert (res.trade, res.score, res.confidence) == ("General", 0, 0.0)


def test_custom_fallback():
    assert classify("nothing here", fallback="Unsorted").trade == "Unsorted"


def test_whole_word_matching():
    # the keyword "rat" must not fire inside "generator"
    assert classify("generator test").trade != "Pest Control"


def test_plural_keyword_matches():
    assert classify("found mice and roaches").trade == "Pest Control"


def test_case_and_whitespace_insensitive():
    assert classify("ELEVATOR   is   stuck").trade == "Elevator"


def test_confidence_between_zero_and_one_and_ranking_sorted():
    res = classify("leak near the light")
    assert 0 < res.confidence <= 1
    scores = [s for _, s in res.ranking]
    assert scores == sorted(scores, reverse=True)


def test_tie_breaks_alphabetically():
    rules = {"B": {"x": 1}, "A": {"x": 1}}
    assert classify("x", rules).trade == "A"


def test_load_rules_bad_weight(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"T": {"k": 0}}))
    with pytest.raises(ValueError):
        load_rules(p)


def test_load_rules_empty(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}")
    with pytest.raises(ValueError):
        load_rules(p)


def test_cli_text(capsys):
    assert main(["text", "Elevator stuck"]) == 0
    assert "Trade: Elevator" in capsys.readouterr().out


def test_cli_file_missing_column(capsys):
    assert main(["file", "examples/requests.csv", "--column", "nope"]) == 1
    assert "not found" in capsys.readouterr().err


def test_cli_missing_file(capsys):
    assert main(["file", "missing.csv"]) == 1
