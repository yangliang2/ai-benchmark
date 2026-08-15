"""The rules an evening's sorting goes by.

Everything the office is holding is settled once each evening, and the four
verdicts a thing is settled with are RETURNED, BINNED, AUCTION and SHELF.

Whoever has been in for their property has it back, and that is the end of it.
Whatever will not keep is thrown out that evening, new in or long in, so a
thing nobody has been in for and that will not keep is settled as BINNED and
never as anything else. What is left goes to the sale room once it has been
here longer than the office keeps things, and is on the shelf until then.

`Piles` is what one evening comes to and `Desk` is where the sorting is done.
The desk is asked for a verdict a thing at a time, so a verdict is what it
answers with rather than something a caller works out afterwards.
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
    """Whether a thing has been here longer than the office keeps things."""
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
        """Drop this in the bin beside the desk, and say where it went."""
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
