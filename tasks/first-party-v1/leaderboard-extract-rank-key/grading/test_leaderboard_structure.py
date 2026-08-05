"""Structural half of the grading suite: asserts the ordering rule is one
module-level function the three callers sort through. Fails on the pristine
repo, where rank_key does not exist."""

import inspect

from leaderboard import Player, rank_key, rank_of, standings, top


def test_the_ordering_rule_is_a_key_function():
    assert callable(rank_key)
    assert rank_key(Player("a", 60)) < rank_key(Player("b", 30))


def test_all_three_callers_sort_through_it(monkeypatch):
    # Only a real seam picks up a rule replaced at runtime; a key function
    # alongside three inline lambdas does not.
    monkeypatch.setattr("leaderboard.rank_key", lambda player: player.name)
    ladder = [Player("zoe", 60), Player("ada", 30), Player("kim", 45)]

    assert [player.name for player in standings(ladder)] == ["ada", "kim", "zoe"]
    assert [player.name for player in top(ladder, 1)] == ["ada"]
    assert rank_of(ladder, "zoe") == 3


def test_the_inline_lambdas_are_gone():
    for function in (standings, top, rank_of):
        assert "lambda" not in inspect.getsource(function)
