"""The lost property office: the counter, the desk behind it, and the book the
evening is written up in."""

from handins import in_order, ticket_for
from sorting import AUCTION, BINNED, KEEPING_DAYS, RETURNED, SHELF, Desk


def wording(verdict):
    """How one verdict is written up in the book."""
    if verdict == RETURNED:
        return "back to its owner"
    if verdict == BINNED:
        return "thrown out"
    if verdict == AUCTION:
        return "sent to the sale room"
    return "on the shelf"


class Office:
    """A day's holdings, the desk they are settled at, and the write-up."""

    def __init__(self, handins, keeping=KEEPING_DAYS):
        self.handins = in_order(handins)
        self.desk = Desk(keeping)

    def evening(self, today):
        """The four piles tonight's sorting leaves."""
        return self.desk.evening(self.handins, today)

    def written_up(self, today):
        """The book's lines for tonight, one to a thing and pile by pile."""
        piles = self.evening(today)
        lines = []
        for pile, verdict in (
            (piles.returned, RETURNED),
            (piles.binned, BINNED),
            (piles.sold, AUCTION),
            (piles.shelved, SHELF),
        ):
            lines.extend(f"{handin.what}: {wording(verdict)}" for handin in pile)
        return lines

    def tickets(self, today):
        """The ticket on every thing the office is holding."""
        return [ticket_for(handin, today) for handin in self.handins]

    def still_here(self, today):
        """What the office is still looking after in the morning."""
        return [
            handin
            for handin in self.handins
            if self.desk.held_over(handin, today)
        ]

    def counted(self, today):
        """How many things tonight's write-up puts under each verdict."""
        piles = self.evening(today)
        return {
            RETURNED: len(piles.returned),
            BINNED: len(piles.binned),
            AUCTION: len(piles.sold),
            SHELF: len(piles.shelved),
        }
