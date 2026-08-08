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
