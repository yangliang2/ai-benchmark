from openings import is_open, too_late_to_start


def test_the_doors_are_shut_before_seven_and_from_eleven():
    assert not is_open(6)
    assert is_open(7)
    assert not is_open(23)


def test_the_hour_the_room_stops_taking_loads_is_itself_too_late():
    assert not too_late_to_start(20)
    assert too_late_to_start(21)
