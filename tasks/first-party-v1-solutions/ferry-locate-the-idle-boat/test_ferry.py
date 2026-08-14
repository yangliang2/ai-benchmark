from ferry import Ferry
from passengers import Passenger

# Four on the jetty, and a boat that seats four.
ON_THE_JETTY = [
    Passenger("Ada", 3),
    Passenger("Bram", 5),
    Passenger("Clare", 8),
    Passenger("Dai", 11),
]


def test_the_ferryman_calls_the_boat_away():
    assert Ferry(ON_THE_JETTY).casts_off()
    assert not Ferry(ON_THE_JETTY).waits()


def test_the_boat_takes_them_in_the_order_they_came_down():
    aboard = Ferry(ON_THE_JETTY).aboard()
    assert [passenger.name for passenger in aboard] == [
        "Ada",
        "Bram",
        "Clare",
        "Dai",
    ]


def test_nobody_is_left_behind_when_the_boat_takes_them_all():
    assert Ferry(ON_THE_JETTY).still_on_the_jetty() == []


def test_a_smaller_boat_leaves_the_rest_behind():
    ferry = Ferry(ON_THE_JETTY, seats=2)
    assert [passenger.name for passenger in ferry.aboard()] == ["Ada", "Bram"]
    assert [passenger.name for passenger in ferry.still_on_the_jetty()] == [
        "Clare",
        "Dai",
    ]


def test_what_the_ferryman_shouts_names_who_is_going():
    lines = Ferry(ON_THE_JETTY).announce()
    assert lines[0] == "- Ada"
    assert lines[-1] == "Away with 4 of 4"


def test_a_jetty_the_boat_could_clear_in_one_go():
    assert Ferry(ON_THE_JETTY).one_crossing()
    assert not Ferry(ON_THE_JETTY, seats=3).one_crossing()


def test_the_jetty_is_crowded_at_two_boatloads():
    assert not Ferry(ON_THE_JETTY).crowded()
    assert Ferry(ON_THE_JETTY, seats=2).crowded()


def test_how_many_more_the_boat_is_worth_calling_for():
    assert Ferry(ON_THE_JETTY).short_of() == 0
    assert Ferry(ON_THE_JETTY[:1]).short_of() == 3


def test_who_has_been_on_the_jetty_long_enough_to_say_so():
    impatient = Ferry(ON_THE_JETTY).impatient(25)
    assert [passenger.name for passenger in impatient] == ["Ada", "Bram"]
