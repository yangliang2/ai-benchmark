"""Behaviour half of the grading suite: must pass before and after the expiry
rule moves into a module of its own, so it pins which sessions each function
treats as usable — including one that has been alive exactly as long as it is
allowed to be."""

import pytest
from sessions import TTL_SECONDS, Session, active, prune, resolve, seconds_left


def test_a_recent_session_is_still_usable():
    fresh = Session("t1", "ada", 10_000)

    assert active([fresh], 10_120) == [fresh]
    assert resolve([fresh], "t1", 10_120) is fresh
    assert prune([fresh], 10_120) == [fresh]


def test_a_session_past_its_time_is_not():
    stale = Session("t2", "bo", 1_000)

    assert active([stale], 10_120) == []
    assert prune([stale], 10_120) == []
    with pytest.raises(KeyError, match="session t2 has expired"):
        resolve([stale], "t2", 10_120)


def test_a_session_is_finished_the_moment_its_time_is_up():
    """The last second a session is good for is the one before its whole
    allowance has gone by, and all three functions agree about it."""
    session = Session("t1", "ada", 0)

    assert active([session], TTL_SECONDS - 1) == [session]
    assert prune([session], TTL_SECONDS - 1) == [session]

    assert active([session], TTL_SECONDS) == []
    assert prune([session], TTL_SECONDS) == []
    with pytest.raises(KeyError, match="session t1 has expired"):
        resolve([session], "t1", TTL_SECONDS)


def test_resolving_a_token_nobody_holds_is_refused():
    with pytest.raises(KeyError, match="no session t9"):
        resolve([Session("t1", "ada", 10_000)], "t9", 10_120)


def test_pruning_keeps_the_usable_ones_oldest_first():
    fresh = Session("t1", "ada", 10_000)
    stale = Session("t2", "bo", 1_000)
    older = Session("t3", "kim", 9_500)

    assert prune([fresh, stale, older], 10_120) == [older, fresh]


def test_seconds_left_runs_down_and_stops_at_nothing():
    session = Session("t1", "ada", 0)

    assert seconds_left(session, 0) == TTL_SECONDS
    assert seconds_left(session, 120) == TTL_SECONDS - 120
    assert seconds_left(session, TTL_SECONDS) == 0
    assert seconds_left(session, TTL_SECONDS + 5_000) == 0
