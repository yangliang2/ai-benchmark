import pytest
from loading import EMPTY, SERVE, Line, short_by


def test_a_line_a_whole_load_deep_is_served():
    assert Line("abcd", 4).call() == SERVE


def test_a_load_is_made_up_from_the_front_of_the_line():
    assert Line("abcdef", 4).load().served == ("a", "b", "c", "d")


def test_whoever_is_not_served_keeps_their_place():
    assert Line("abcdef", 4).load().left == ("e", "f")


def test_what_is_served_and_what_is_not_are_the_whole_line():
    assert Line("abcdef", 4).load().whole_line() == tuple("abcdef")


def test_a_line_shorter_than_a_load_makes_up_what_there_is():
    assert Line("ab", 4).load().served == ("a", "b")


def test_a_line_a_load_deep_or_deeper_is_short_of_none():
    assert short_by(4, 4) == EMPTY
    assert short_by(9, 4) == EMPTY


def test_a_shorter_line_falls_short_by_the_difference():
    assert short_by(1, 4) == 3


def test_an_empty_line_falls_short_by_a_whole_load():
    assert short_by(0, 4) == 4


def test_a_load_has_to_take_someone():
    with pytest.raises(ValueError):
        Line("abcd", 0)
