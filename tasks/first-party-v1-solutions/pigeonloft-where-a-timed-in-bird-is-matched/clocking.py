"""The clocking: which line of the sheets a bird timed in counts for.

`rings.same_bird` says whether two writings of a number are the same bird,
and `entries.Entries` says what was entered for a race. Neither of them ever
tries the one on the other; that is done in this module and in no other.
"""

from rings import same_bird


class Clocked:
    """One bird timed in: the number on its ring as the member gave it, the
    loft that timed it, and the hour on the clock."""

    def __init__(self, ring, loft, hour):
        self.ring = ring
        self.loft = loft
        self.hour = hour

    def __repr__(self):
        return f"Clocked({self.ring!r}, {self.loft!r}, {self.hour!r})"


class Book:
    """The clocking of one race, worked on its own sheets."""

    def __init__(self, entries):
        self.entries = entries

    def belongs_to(self, clocked, race):
        """The line this bird counts for, or None where it counts for none.

        A bird counts for a line when the number is the same bird and the
        loft that timed it is the loft whose line it is. One timed outside
        the hours the race allows counts for no line at all. Where a loft
        has the same number down more than once, it is the first of those
        lines the bird counts for.
        """
        if not race.opens <= clocked.hour <= race.shuts:
            return None
        for entry in self.entries.for_race(race):
            if entry.loft == clocked.loft and same_bird(entry.ring, clocked.ring):
                return entry
        return None

    def unaccounted(self, clocked_birds, race):
        """Every bird timed in that counts for no line at all."""
        return [
            clocked
            for clocked in clocked_birds
            if self.belongs_to(clocked, race) is None
        ]
