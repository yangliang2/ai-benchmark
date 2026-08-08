"""Held-out grading for `running_sheet`.

Every expectation is a whole list of literal lines. Nothing here builds an
expectation by calling `operating_day`, so an answer that rewrote the reader
the sheet is supposed to be grouped by cannot talk this suite into accepting
it.

The suite falls into two halves on purpose. The near half is runs that stay
inside one calendar date — nothing departs or arrives after midnight — and
every answer that gets the sheet's shape right passes all of it, whatever it
believes a day's working to be. The far half is runs that cross midnight,
which is the whole of what this module means by a day's working, and it is
where an answer that files trips under the calendar date comes apart.
"""

from datetime import date, datetime

from nightbus import (
    Trip,
    arrives,
    describe,
    first_off,
    operating_day,
    running_sheet,
    running_time,
    runs_on,
)


def at(moment):
    """A moment, written the way a timetable writes one."""
    return datetime.fromisoformat(moment)


# --- the near half: runs that stay inside one calendar date -------------------


def test_a_run_with_no_trips_gives_no_lines():
    assert running_sheet([]) == []


def test_one_trip_is_a_heading_a_line_and_a_total():
    assert running_sheet([Trip("N1", at("2026-03-02 19:05"), 42)]) == [
        "2026-03-02",
        "  N1  19:05  19:47",
        "  1 trip, 42 minutes",
    ]


def test_the_trips_of_one_evening_come_in_departure_order():
    trips = [
        Trip("N9", at("2026-03-02 22:40"), 30),
        Trip("N1", at("2026-03-02 21:05"), 42),
        Trip("N4", at("2026-03-02 23:10"), 15),
    ]

    assert running_sheet(trips) == [
        "2026-03-02",
        "  N1  21:05  21:47",
        "  N9  22:40  23:10",
        "  N4  23:10  23:25",
        "  3 trips, 87 minutes",
    ]


def test_two_trips_leaving_together_come_in_route_order():
    trips = [
        Trip("N9", at("2026-03-02 22:00"), 20),
        Trip("N1", at("2026-03-02 22:00"), 30),
    ]

    assert running_sheet(trips) == [
        "2026-03-02",
        "  N1  22:00  22:30",
        "  N9  22:00  22:20",
        "  2 trips, 50 minutes",
    ]


def test_each_working_is_its_own_block_and_the_blocks_come_in_date_order():
    trips = [
        Trip("N1", at("2026-03-03 20:00"), 30),
        Trip("N1", at("2026-03-02 20:00"), 40),
    ]

    assert running_sheet(trips) == [
        "2026-03-02",
        "  N1  20:00  20:40",
        "  1 trip, 40 minutes",
        "2026-03-03",
        "  N1  20:00  20:30",
        "  1 trip, 30 minutes",
    ]


def test_the_list_it_was_given_is_left_in_the_order_it_was_given():
    trips = [
        Trip("N9", at("2026-03-02 22:40"), 30),
        Trip("N1", at("2026-03-02 21:05"), 42),
    ]
    given = list(trips)

    running_sheet(trips)

    assert trips == given


# --- the far half: runs that cross midnight -----------------------------------


def test_a_trip_in_the_small_hours_files_under_the_date_before():
    assert running_sheet([Trip("N9", at("2026-03-02 01:20"), 45)]) == [
        "2026-03-01",
        "  N9  25:20  26:05",
        "  1 trip, 45 minutes",
    ]


def test_one_night_is_one_block_though_it_falls_on_two_dates():
    trips = [
        Trip("N1", at("2026-03-01 23:40"), 42),
        Trip("N9", at("2026-03-02 01:20"), 45),
    ]

    assert running_sheet(trips) == [
        "2026-03-01",
        "  N1  23:40  24:22",
        "  N9  25:20  26:05",
        "  2 trips, 87 minutes",
    ]


def test_the_working_turns_over_at_four_and_the_blocks_split_there():
    trips = [
        Trip("N1", at("2026-03-02 03:59"), 20),
        Trip("N2", at("2026-03-02 04:00"), 20),
    ]

    assert running_sheet(trips) == [
        "2026-03-01",
        "  N1  27:59  28:19",
        "  1 trip, 20 minutes",
        "2026-03-02",
        "  N2  04:00  04:20",
        "  1 trip, 20 minutes",
    ]


def test_a_trip_still_running_at_four_keeps_the_clock_running():
    assert running_sheet([Trip("N9", at("2026-03-02 03:30"), 40)]) == [
        "2026-03-01",
        "  N9  27:30  28:10",
        "  1 trip, 40 minutes",
    ]


def test_a_trip_that_gets_in_after_midnight_prints_past_twenty_four():
    assert running_sheet([Trip("N1", at("2026-03-01 23:50"), 45)]) == [
        "2026-03-01",
        "  N1  23:50  24:35",
        "  1 trip, 45 minutes",
    ]


def test_the_totals_count_the_night_rather_than_the_date():
    trips = [
        Trip("N1", at("2026-03-01 22:00"), 30),
        Trip("N9", at("2026-03-02 01:00"), 60),
        Trip("N4", at("2026-03-02 20:00"), 15),
    ]

    assert running_sheet(trips) == [
        "2026-03-01",
        "  N1  22:00  22:30",
        "  N9  25:00  26:00",
        "  2 trips, 90 minutes",
        "2026-03-02",
        "  N4  20:00  20:15",
        "  1 trip, 15 minutes",
    ]


# --- what was already there goes on working -----------------------------------


def test_the_existing_readers_are_unchanged():
    trip = Trip("N9", at("2026-03-02 01:20"), 45)

    assert arrives(trip) == at("2026-03-02 02:05")
    assert operating_day(at("2026-03-02 01:20")) == date(2026, 3, 1)
    assert operating_day(at("2026-03-02 04:00")) == date(2026, 3, 2)
    assert runs_on(trip, date(2026, 3, 1))
    assert first_off([trip], date(2026, 3, 1)) == trip
    assert running_time([trip]) == 45
    assert describe(trip) == "N9, 45 min"
