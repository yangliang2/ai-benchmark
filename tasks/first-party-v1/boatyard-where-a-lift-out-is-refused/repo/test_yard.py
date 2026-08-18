import pytest
from cradles import Cradle
from slipway import Tide
from yard import Berth, Refused, Yard


def a_yard():
    return Yard(
        berths=[Berth("A", 8.0), Berth("B", 12.0)],
        cradles=[Cradle("light"), Cradle("heavy")],
        tides=[Tide("mon", 210), Tide("tue", 120)],
    )


def test_a_hull_nothing_objects_to_is_hauled_ashore():
    yard = a_yard()

    berth = yard.book_in("Kittiwake", 7.0, 200, "mon", 20)

    assert berth.name == "A"
    assert yard.ashore() == ["Kittiwake"]


def test_the_shortest_standing_that_takes_it_is_the_one_used():
    yard = a_yard()

    assert yard.book_in("Petrel", 11.0, 200, "mon", 20).name == "B"


def test_too_brief_a_season_is_refused():
    with pytest.raises(Refused, match="haul for"):
        a_yard().book_in("Kittiwake", 7.0, 200, "mon", 2)


def test_a_day_the_crane_cannot_work_on_is_refused():
    with pytest.raises(Refused, match="cannot lift"):
        a_yard().book_in("Kittiwake", 7.0, 200, "tue", 20)


def test_a_hull_no_standing_takes_is_refused():
    with pytest.raises(Refused, match="no standing free"):
        a_yard().book_in("Trawler", 14.0, 200, "mon", 20)


def test_a_hull_no_frame_takes_is_refused():
    yard = Yard(
        berths=[Berth("A", 8.0)],
        cradles=[Cradle("light")],
        tides=[Tide("mon", 210)],
    )

    with pytest.raises(Refused, match="no frame in the store"):
        yard.book_in("Kittiwake", 7.0, 400, "mon", 20)


def test_a_refused_enquiry_leaves_the_yard_as_it_stood():
    yard = a_yard()

    with pytest.raises(Refused):
        yard.book_in("Trawler", 14.0, 200, "mon", 20)

    assert yard.ashore() == []
    assert all(cradle.holding is None for cradle in yard.cradles)


def test_an_enquiry_wrong_in_several_ways_hears_only_the_earliest():
    yard = a_yard()

    with pytest.raises(Refused, match="haul for"):
        yard.book_in("Trawler", 14.0, 900, "tue", 1)
