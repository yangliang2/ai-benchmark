import pytest
from leaderboard import Player, rank_of, standings, top

LADDER = [
    Player("zoe", 30),
    Player("ada", 45),
    Player("kim", 20, bonus=5),
    Player("bo", 60),
]


def test_a_bonus_counts_towards_the_total():
    assert Player("kim", 20, bonus=5).total() == 25


def test_standings_put_the_highest_total_first():
    assert [player.name for player in standings(LADDER)] == ["bo", "ada", "zoe", "kim"]


def test_top_takes_the_leaders():
    assert [player.name for player in top(LADDER, 2)] == ["bo", "ada"]


def test_rank_of_counts_from_one():
    assert rank_of(LADDER, "bo") == 1
    assert rank_of(LADDER, "kim") == 4


def test_an_unknown_player_has_no_rank():
    with pytest.raises(KeyError, match="no player called ren"):
        rank_of(LADDER, "ren")
