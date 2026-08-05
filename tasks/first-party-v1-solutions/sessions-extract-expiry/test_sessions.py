import pytest
from sessions import Session, active, prune, resolve, seconds_left

FRESH = Session("t1", "ada", 10_000)
STALE = Session("t2", "bo", 1_000)
NOW = 10_120


def test_a_recent_session_is_still_usable():
    assert active([FRESH], NOW) == [FRESH]


def test_a_session_from_hours_ago_is_not():
    assert active([STALE], NOW) == []


def test_resolving_finds_a_usable_session_by_token():
    assert resolve([FRESH, STALE], "t1", NOW) is FRESH


def test_resolving_an_expired_session_is_refused():
    with pytest.raises(KeyError, match="session t2 has expired"):
        resolve([FRESH, STALE], "t2", NOW)


def test_resolving_a_token_nobody_holds_is_refused():
    with pytest.raises(KeyError, match="no session t9"):
        resolve([FRESH], "t9", NOW)


def test_pruning_keeps_the_usable_ones_oldest_first():
    older = Session("t3", "kim", 9_500)

    assert prune([FRESH, STALE, older], NOW) == [older, FRESH]


def test_seconds_left_runs_down_and_stops_at_nothing():
    assert seconds_left(FRESH, NOW) == 780
    assert seconds_left(STALE, NOW) == 0
