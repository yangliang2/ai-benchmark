from datetime import date, datetime

from nightbus import (
    Trip,
    arrives,
    describe,
    first_off,
    operating_day,
    running_time,
    runs_on,
)


def at(moment):
    """A moment, written the way a timetable writes one."""
    return datetime.fromisoformat(moment)


def test_a_trip_remembers_the_three_things_it_was_made_of():
    trip = Trip("N1", at("2026-03-01 22:05"), 42)

    assert trip.route == "N1"
    assert trip.departs == at("2026-03-01 22:05")
    assert trip.minutes == 42


def test_arrives_adds_the_running_time_to_the_departure():
    trip = Trip("N1", at("2026-03-01 22:05"), 42)

    assert arrives(trip) == at("2026-03-01 22:47")


def test_a_trip_can_get_in_on_the_next_date():
    trip = Trip("N9", at("2026-03-01 23:50"), 45)

    assert arrives(trip) == at("2026-03-02 00:35")


def test_an_evening_moment_belongs_to_its_own_date():
    assert operating_day(at("2026-03-01 22:05")) == date(2026, 3, 1)


def test_a_moment_in_the_small_hours_belongs_to_the_date_before():
    assert operating_day(at("2026-03-02 01:20")) == date(2026, 3, 1)


def test_the_working_turns_over_at_four_in_the_morning():
    assert operating_day(at("2026-03-02 03:59")) == date(2026, 3, 1)
    assert operating_day(at("2026-03-02 04:00")) == date(2026, 3, 2)


def test_runs_on_asks_that_question_of_a_whole_trip():
    trip = Trip("N9", at("2026-03-02 01:20"), 45)

    assert runs_on(trip, date(2026, 3, 1))
    assert not runs_on(trip, date(2026, 3, 2))


def test_first_off_takes_the_earliest_of_that_working():
    late = Trip("N1", at("2026-03-01 23:40"), 42)
    later = Trip("N9", at("2026-03-02 01:20"), 45)

    assert first_off([later, late], date(2026, 3, 1)) == late


def test_first_off_says_nothing_when_nothing_runs_that_day():
    trip = Trip("N1", at("2026-03-01 22:05"), 42)

    assert first_off([trip], date(2026, 3, 2)) is None


def test_running_time_adds_the_minutes_up():
    one = Trip("N1", at("2026-03-01 22:05"), 42)
    other = Trip("N9", at("2026-03-02 01:20"), 45)

    assert running_time([one, other]) == 87
    assert running_time([]) == 0


def test_describe_names_the_route_and_how_long_the_trip_takes():
    assert describe(Trip("N1", at("2026-03-01 22:05"), 42)) == "N1, 42 min"
