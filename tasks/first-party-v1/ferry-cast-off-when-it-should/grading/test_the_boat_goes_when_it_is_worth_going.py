"""Held out: which way round the line is read when the boat is called."""

from ferry import Ferry
from loading import HOLD, SERVE, Line
from passengers import Passenger

# Nine on the jetty, and a boat that seats four.
ON_THE_JETTY = [Passenger(f"passenger {number}", number) for number in range(1, 10)]


def test_a_line_deeper_than_a_load_is_served():
    assert Line("abcdefghi", 4).call() == SERVE


def test_a_line_exactly_a_load_deep_is_served():
    assert Line("abcd", 4).call() == SERVE


def test_a_line_one_short_of_a_load_holds():
    assert Line("abc", 4).call() == HOLD


def test_a_line_far_short_of_a_load_holds():
    assert Line("a", 4).call() == HOLD


def test_an_empty_line_holds():
    assert Line("", 4).call() == HOLD


def test_what_a_load_is_made_up_of_is_unchanged():
    line = Line("abcdefghi", 4)
    assert line.load().served == ("a", "b", "c", "d")
    assert line.load().left == tuple("efghi")
    assert line.load().whole_line() == tuple("abcdefghi")


def test_the_boat_goes_with_a_crowd_on_the_jetty():
    assert Ferry(ON_THE_JETTY).casts_off()
    assert not Ferry(ON_THE_JETTY).waits()


def test_the_boat_stays_put_for_two_on_the_jetty():
    assert not Ferry(ON_THE_JETTY[:2]).casts_off()
    assert Ferry(ON_THE_JETTY[:2]).waits()


def test_a_deserted_jetty_sends_no_boat_across():
    assert not Ferry([]).casts_off()


def test_a_jetty_holding_exactly_a_boatful_still_goes():
    assert Ferry(ON_THE_JETTY[:4]).casts_off()


def test_the_ferryman_says_how_many_more_he_is_holding_for():
    assert Ferry(ON_THE_JETTY[:2]).announce()[-1] == "Holding for 2 more"


def test_the_crowd_goes_a_boatful_at_a_time():
    aboard = Ferry(ON_THE_JETTY).aboard()
    assert [passenger.name for passenger in aboard] == [
        f"passenger {number}" for number in (1, 2, 3, 4)
    ]


def test_who_is_left_on_the_jetty_is_unchanged():
    left = Ferry(ON_THE_JETTY).still_on_the_jetty()
    assert [passenger.name for passenger in left] == [
        f"passenger {number}" for number in (5, 6, 7, 8, 9)
    ]


def test_the_neighbouring_reckoning_is_unchanged():
    """The comparisons the fix must leave alone: whether one crossing would
    clear the jetty, and whether the jetty is crowded."""
    assert not Ferry(ON_THE_JETTY).one_crossing()
    assert Ferry(ON_THE_JETTY[:4]).one_crossing()
    assert Ferry(ON_THE_JETTY).crowded()
    assert not Ferry(ON_THE_JETTY[:4]).crowded()
