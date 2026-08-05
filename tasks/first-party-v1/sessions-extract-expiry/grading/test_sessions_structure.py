"""Structural half of the grading suite: asserts the expiry rule is one
predicate in a module of its own that all three callers ask. Fails on the
pristine repo, where expiry.py does not exist."""

import inspect

import pytest
import sessions
from expiry import TTL_SECONDS, is_expired
from sessions import Session, active, prune, resolve


def test_expiry_owns_the_limit_and_the_predicate():
    assert TTL_SECONDS > 0
    assert callable(is_expired)


def test_the_limit_is_still_readable_through_sessions():
    assert sessions.TTL_SECONDS == TTL_SECONDS


def test_all_three_callers_ask_the_predicate(monkeypatch):
    # Only a real seam picks up a rule replaced at runtime; a predicate
    # alongside three inline comparisons does not.
    session = Session("t1", "ada", 10_000)
    monkeypatch.setattr("sessions.is_expired", lambda session, now: True)

    assert active([session], 10_001) == []
    assert prune([session], 10_001) == []
    with pytest.raises(KeyError, match="session t1 has expired"):
        resolve([session], "t1", 10_001)


def test_nothing_left_in_sessions_compares_against_the_limit():
    for function in (active, resolve, prune):
        assert "TTL_SECONDS" not in inspect.getsource(function)
        assert "is_expired" in inspect.getsource(function)


def test_the_rule_lives_in_expiry_rather_than_in_sessions():
    assert inspect.getmodule(is_expired).__name__ == "expiry"
    assert "def is_expired" not in inspect.getsource(sessions)
