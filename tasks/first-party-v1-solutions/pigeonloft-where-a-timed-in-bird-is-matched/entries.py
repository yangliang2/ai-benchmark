"""What was put in, by whom, and for which race.

These are the sheets the secretary took at the club the night before: which
birds a member entered for which race, and the hours a race runs between.
The sheets never see a bird come home.
"""


class Race:
    """One race: what it is called, the hour from which it is open, and the
    hour after which it has closed. A bird timed in between the two hours is
    in the race, and one timed outside them is not."""

    def __init__(self, name, opens, shuts):
        self.name = name
        self.opens = opens
        self.shuts = shuts

    def __repr__(self):
        return f"Race({self.name!r}, {self.opens!r}, {self.shuts!r})"


class Entry:
    """One bird a loft entered for one race."""

    def __init__(self, race, loft, ring):
        self.race = race
        self.loft = loft
        self.ring = ring

    def __repr__(self):
        return f"Entry({self.race!r}, {self.loft!r}, {self.ring!r})"


class Entries:
    """A season's sheets, in the order the secretary took them."""

    def __init__(self, entries):
        self.entries = list(entries)

    def for_race(self, race):
        """Everything entered for this race, in the order it was taken down."""
        return [entry for entry in self.entries if entry.race.name == race.name]

    def by_loft(self, loft):
        """Everything this loft entered, whichever race it was for."""
        return [entry for entry in self.entries if entry.loft == loft]
