"""The bands, and how each one's own name is set down wherever it is printed.

A band's name is not always the name it appears under: one that brings a
singer appears with the singer named after it, and one that is really a
single person keeps its own name whatever else is true. Nothing in here knows
which afternoon anybody plays, what else is on that afternoon, or what goes
round a name once it has been set down.
"""


class Band:
    """One band: its name, how many play in it, and its singer if it has one."""

    def __init__(self, name, players, singer=None):
        self.name = name
        self.players = players
        self.singer = singer

    def __repr__(self):
        return f"Band({self.name!r}, {self.players!r}, singer={self.singer!r})"


def billed_as(band):
    """A band's own name as it is set down: the singer named after it.

    A band of one keeps its name alone, singer or no singer — "Kenneth
    Pomeroy with Kenneth Pomeroy" was set down once and never again.
    """
    if band.singer is None or band.players == 1:
        return band.name
    return f"{band.name} with {band.singer}"
