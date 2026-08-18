"""The yard proper: its standings, and what becomes of an enquiry."""

from cradles import cradle_for
from slipway import workable

# The briefest season the yard will haul for: the crane costs the same to
# rig for a fortnight as it does for a whole winter.
LEAST_WEEKS = 4


class Refused(Exception):
    """Why a hull is staying afloat, in words the office can repeat."""


class Berth:
    """One standing: the longest hull it takes, and what is on it."""

    def __init__(self, name, longest_m, holding=None):
        self.name = name
        self.longest_m = longest_m
        self.holding = holding

    def would_hold(self, length_m):
        """Whether a hull this long could go on this standing, it being empty."""
        return self.holding is None and length_m <= self.longest_m

    def __repr__(self):
        return f"Berth({self.name!r}, {self.longest_m!r}, holding={self.holding!r})"


class Yard:
    """The standings, the frames in the store, and the book of tides."""

    def __init__(self, berths, cradles, tides):
        self.berths = list(berths)
        self.cradles = list(cradles)
        self.tides = list(tides)

    def book_in(self, name, length_m, beam_cm, day, weeks):
        """Haul a hull ashore for the season, or raise Refused saying why not.

        Nothing is recorded until every objection has been got past, so an
        enquiry that comes to nothing leaves the yard as it stood.
        """
        if weeks < LEAST_WEEKS:
            raise Refused(f"{weeks} weeks is under the {LEAST_WEEKS} we haul for")
        if not workable(self.tides, day):
            raise Refused(f"the crane cannot lift on {day}")
        berth = self.shortest_free(length_m)
        if berth is None:
            raise Refused(f"no standing free takes {length_m}m")
        cradle = cradle_for(self.cradles, beam_cm)
        if cradle is None:
            raise Refused(f"no frame in the store takes {beam_cm}cm")
        berth.holding = name
        cradle.holding = name
        return berth

    def shortest_free(self, length_m):
        """The shortest empty standing that would still take this hull."""
        fitting = [berth for berth in self.berths if berth.would_hold(length_m)]
        return min(fitting, key=lambda berth: berth.longest_m, default=None)

    def ashore(self):
        """What is out of the water, as the standings are listed."""
        return [berth.holding for berth in self.berths if berth.holding is not None]
