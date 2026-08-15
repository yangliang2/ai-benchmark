"""One walk out of the shop, and what has to be carried on it.

A round is one title and the streets it is walked in: which houses it drops a
paper at, and how many bags that comes to. What a walk is worth counting up is
`tallying`'s business rather than this module's.
"""

from typing import NamedTuple

from houses import in_order

PAPERS_A_BAG_HOLDS = 40

NONE_AT_ALL = 0


class Bag(NamedTuple):
    """What one walk carries out of the shop."""

    papers: int
    bags: int

    def room_left(self):
        """How many more papers would go in on top of what is in there."""
        return self.bags * PAPERS_A_BAG_HOLDS - self.papers


def bagfuls(papers):
    """How many bags it takes to carry this many papers."""
    if papers == NONE_AT_ALL:
        return NONE_AT_ALL
    return -(-papers // PAPERS_A_BAG_HOLDS)


class Round:
    """One walk out of the shop: one title, and the streets it is walked in."""

    def __init__(self, title, streets=None):
        self.title = title
        self.streets = [] if streets is None else list(streets)

    def takes(self, house):
        """Whether this house is one this walk drops a paper at."""
        return house.takes == self.title

    def drops(self, houses, skipping=[]):
        """The houses this walk drops a paper at, in the order it takes them.

        `skipping` names the numbers left off this week — a house away, or one
        that has not paid. It is read here and never added to: which houses
        are skipped is the shop's to say, one walk at a time.
        """
        return [
            house
            for house in in_order(houses, self.streets)
            if self.takes(house) and house.number not in skipping
        ]

    def bagful(self, houses):
        """What this walk carries: the papers dropped, and the bags for them."""
        papers = len(self.drops(houses))
        return Bag(papers, bagfuls(papers))
