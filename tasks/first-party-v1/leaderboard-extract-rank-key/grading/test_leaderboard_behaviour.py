"""Behaviour half of the grading suite: must pass before and after the
ordering rule becomes a function of its own, so it pins the order the three
functions put players in — including where two players finish level."""

import pytest
from leaderboard import Player, rank_of, standings, top


def names(players):
    return [player.name for player in players]


def test_standings_put_the_highest_total_first():
    ladder = [Player("zoe", 30), Player("ada", 45), Player("kim", 20, bonus=5)]

    assert names(standings(ladder)) == ["ada", "zoe", "kim"]


def test_a_bonus_counts_towards_the_total():
    ladder = [Player("zoe", 30), Player("kim", 20, bonus=25)]

    assert names(standings(ladder)) == ["kim", "zoe"]


def test_players_level_on_total_keep_the_order_they_were_entered():
    """Nothing separates them, so nothing reorders them: the ladder is the
    order they signed up in, and a tie leaves that order alone."""
    ladder = [Player("zoe", 30), Player("ada", 30), Player("kim", 45)]

    assert names(standings(ladder)) == ["kim", "zoe", "ada"]
    assert names(top(ladder, 2)) == ["kim", "zoe"]
    assert rank_of(ladder, "zoe") == 2
    assert rank_of(ladder, "ada") == 3


def test_a_bonus_can_level_a_player_with_one_entered_earlier():
    ladder = [Player("ren", 40), Player("bo", 35, bonus=5)]

    assert names(standings(ladder)) == ["ren", "bo"]
    assert rank_of(ladder, "bo") == 2


def test_top_takes_the_leaders():
    ladder = [Player("zoe", 30), Player("ada", 45), Player("bo", 60)]

    assert names(top(ladder, 2)) == ["bo", "ada"]
    assert names(top(ladder, 0)) == []
    assert names(top(ladder, 9)) == ["bo", "ada", "zoe"]


def test_an_unknown_player_has_no_rank():
    with pytest.raises(KeyError, match="no player called ren"):
        rank_of([Player("zoe", 30)], "ren")
