"""Night-bus trips, and what a depot makes of them.

A trip is a `Trip` — the route it runs, the moment it departs and how many
minutes it takes — and a moment is a `datetime`. The functions below read a
trip, or a list of them; none of them modifies what it is given.
"""

from collections import namedtuple
from datetime import timedelta

Trip = namedtuple("Trip", "route departs minutes")


def arrives(trip):
    """The moment the trip gets in."""
    return trip.departs + timedelta(minutes=trip.minutes)


def operating_day(moment):
    """The day's working a moment belongs to."""
    return (moment - timedelta(hours=4)).date()


def runs_on(trip, day):
    """Whether the trip belongs to `day`'s working."""
    return operating_day(trip.departs) == day


def first_off(trips, day):
    """The first of these trips to leave on `day`'s working, or None."""
    running = [trip for trip in trips if runs_on(trip, day)]
    return min(running, key=lambda trip: trip.departs, default=None)


def running_time(trips):
    """How many minutes these trips take between them."""
    return sum(trip.minutes for trip in trips)


def describe(trip):
    """A one-line summary of a trip."""
    return f"{trip.route}, {trip.minutes} min"


def running_sheet(trips):
    """The depot's running sheet: one block per day's working, in date order.

    A block opens with its day's date, carries a line for each trip of that
    working in departure order, and closes with how many trips it holds and
    how long they take between them. Times are counted from midnight at the
    start of the block's own date, so a trip that is still out after midnight
    prints past 24:00.
    """

    def clock(moment, day):
        hours = (moment.date() - day).days * 24 + moment.hour
        return f"{hours:02d}:{moment.minute:02d}"

    workings = {}
    for trip in trips:
        workings.setdefault(operating_day(trip.departs), []).append(trip)

    sheet = []
    for day in sorted(workings):
        running = sorted(workings[day], key=lambda trip: (trip.departs, trip.route))
        sheet.append(day.isoformat())
        for trip in running:
            sheet.append(
                f"  {trip.route}  {clock(trip.departs, day)}"
                f"  {clock(arrives(trip), day)}"
            )
        counted = "1 trip" if len(running) == 1 else f"{len(running)} trips"
        sheet.append(f"  {counted}, {running_time(running)} minutes")
    return sheet
