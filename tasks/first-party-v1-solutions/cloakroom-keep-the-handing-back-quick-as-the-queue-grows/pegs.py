"""The rail of coats, and the room's own count of handlings."""


class Coat:
    """One coat on the rail: the ticket pinned in its collar, and what the
    owner will be told to look for."""

    def __init__(self, ticket, description):
        self.ticket = ticket
        self.description = description


class Rail:
    """Every coat the room holds, pegged in the order it was taken in, and
    the tally of take-downs.

    The ticket is pinned inside the collar, so reading one means lifting
    the coat off its peg. The room has always tallied take-downs: every one
    is a handling — a sleeve dragged over the hook, a chance for whatever
    is in the pockets to end up on the floor — and the house rules have the
    attendant keep the count for the same reason the till keeps a roll;
    nothing about the tally is for a test's benefit. The room pins one
    ticket to one coat: no two coats on the rail carry the same number.
    """

    def __init__(self, coats):
        self._coats = list(coats)
        self.takedowns = 0

    def pegs(self):
        """Every peg on the rail, in rail order."""
        return range(len(self._coats))

    def take_down(self, peg):
        """Lift the coat off this peg to read the ticket in its collar."""
        self.takedowns += 1
        return self._coats[peg]
