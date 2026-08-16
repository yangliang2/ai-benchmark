"""The rules an evening's sorting goes by.

All the office is holding is settled once an evening, under one of four
verdicts: RETURNED, BINNED, AUCTION and SHELF.

A handin its owner has collected is RETURNED, and no rule below it applies.
A perishable handin nobody has collected is BINNED at any age, and BINNED is
the last word on it: no rule below may settle it a second time. A handin that
gets past both of those is settled on age alone — beyond `KEEPING_DAYS` at the
office it is AUCTION, and short of that it is SHELF.

`Piles` is what one evening comes to and `Desk` is where the sorting is done.
The desk is asked for a verdict a handin at a time, so a verdict is what it
hands back rather than a conclusion its caller assembles.
"""

from typing import NamedTuple

from handins import days_in, in_order

KEEPING_DAYS = 90

RETURNED = "returned"
BINNED = "binned"
AUCTION = "auction"
SHELF = "shelf"


class Piles(NamedTuple):
    """What one evening's sorting comes to: the four piles it leaves."""

    returned: tuple
    binned: tuple
    sold: tuple
    shelved: tuple

    def everything(self):
        """Everything the evening settled, pile after pile in that order."""
        return self.returned + self.binned + self.sold + self.shelved


def outstayed(handin, today, keeping=KEEPING_DAYS):
    """Whether this handin has sat at the office past its keeping limit."""
    return days_in(handin, today) > keeping


class Desk:
    """The desk an evening's sorting is done at, and the bin beside it."""

    def __init__(self, keeping=KEEPING_DAYS):
        self.keeping = keeping
        self.thrown = []

    def held_over(self, handin, today):
        """Whether this thing is still the office's to look after tomorrow."""
        if handin.claimed:
            return False
        if not handin.keeps:
            return False
        return not outstayed(handin, today, self.keeping)

    def thrown_out(self, handin):
        """Drop this in the bin beside the desk, and give back its verdict."""
        self.thrown.append(handin)
        return BINNED

    def verdict(self, handin, today):
        """Which of the four verdicts this thing is settled with tonight."""
        if handin.claimed:
            return RETURNED
        if not handin.keeps:
            return self.thrown_out(handin)
        if outstayed(handin, today, self.keeping):
            return AUCTION
        return SHELF

    def evening(self, handins, today):
        """The four piles a day's holdings are settled into."""
        piles = {RETURNED: [], BINNED: [], AUCTION: [], SHELF: []}
        for handin in in_order(handins):
            piles[self.verdict(handin, today)].append(handin)
        return Piles(
            tuple(piles[RETURNED]),
            tuple(piles[BINNED]),
            tuple(piles[AUCTION]),
            tuple(piles[SHELF]),
        )
