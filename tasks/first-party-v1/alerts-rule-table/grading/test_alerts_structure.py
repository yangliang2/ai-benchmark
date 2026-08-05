"""Structural half of the grading suite: asserts severity genuinely walks a
table of rules. Fails on the pristine repo, where RULES does not exist."""

import inspect

from alerts import RULES, severity


def test_every_rule_is_a_predicate_and_the_severity_it_gives():
    assert len(RULES) >= 4
    for matches, level in RULES:
        assert callable(matches)
        assert level in {"page", "warn", "notice", "ignore"}


def test_severity_walks_the_table(monkeypatch):
    # Only a real walk picks up a rule put in front of the rest at runtime; a
    # decorative table alongside the old chain does not.
    monkeypatch.setattr("alerts.RULES", ((lambda event: True, "page"), *RULES))

    assert severity({"service": "search", "status": 200, "latency_ms": 1}) == "page"


def test_the_first_match_is_still_what_answers(monkeypatch):
    # A rule behind the rest never gets to speak for an event an earlier rule
    # already matched, which is what makes the table an ordered one.
    monkeypatch.setattr("alerts.RULES", (*RULES, (lambda event: True, "page")))

    assert severity({"service": "search", "status": 404, "latency_ms": 10}) == "notice"


def test_the_chain_is_gone():
    assert "elif" not in inspect.getsource(severity)
