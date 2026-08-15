"""What a run of cards comes to, plot by plot.

`Reading` is one plot's standpipe once its card has been made out, and
`Quarter` is a whole run of cards as it came back off the site.

These books carry only what was read. Where the writing on a card defeats the
society altogether, that plot has no total for the run and none is invented for
it: the books would sooner run a plot light than stand behind a total nobody
wrote down.
"""

from typing import NamedTuple

from cards import figure

NOTHING_USED = 0

NOT_READ_BEFORE = None


class Reading(NamedTuple):
    """One plot's standpipe for one run, once its card has been made out."""

    plot: int
    units: int

    def since(self, before=NOT_READ_BEFORE):
        """How much ran through between the run before this one and this one.

        A dial that has been changed stands lower than it did last time; the
        society takes that as nothing rather than as a plot handing water
        back.
        """
        if before is NOT_READ_BEFORE:
            return self.units
        return max(self.units - before, NOTHING_USED)


def most_used(readings):
    """The reading that got through the most of any on one run."""
    return max(readings, key=lambda reading: reading.units, default=None)


class Quarter:
    """A run of cards, as it came back off the site."""

    def __init__(self, cards, before=None):
        self.cards = {card.plot: card for card in cards}
        self.before = dict(before or {})

    def carded(self):
        """The plots a card was handed in for, in the order they were handed
        in."""
        return list(self.cards)

    def card_for(self, plot):
        """The card handed in for one plot, as it was written down out
        there."""
        return self.cards[plot]

    def used_on(self, plot):
        """How much ran through on one plot, off the card handed in."""
        return figure(self.card_for(plot).written)

    def read_before(self, plot):
        """What one plot stood at on the run before, where the books have it."""
        try:
            return self.before[plot]
        except KeyError:
            return NOT_READ_BEFORE
