"""The slate behind the counter, where the shop's counting is done.

`Bundle` is one street's papers tied together, and `Slate` is what a walk is
counted up on. Every ask is worked out on a clean slate: what was counted up
for the ask before belongs to that ask, and none of it is still lying there to
come back with the next one.

Where a count is already under way the shop puts it on the slate to be added
to, and takes it back with this walk's bundles on the end of it. That is the
one way an ask ever comes back with another ask's papers on it.
"""

from typing import NamedTuple

NOTHING_YET = 0


class Bundle(NamedTuple):
    """One street's papers for one walk, tied up together."""

    street: str
    papers: int


def added_up(bundles, apart_from=[]):
    """How many papers some bundles come to.

    `apart_from` names the streets left out of the reckoning — one already
    made up, or one somebody else is taking round. It is read here and never
    added to.
    """
    return sum(
        bundle.papers for bundle in bundles if bundle.street not in apart_from
    )


class Slate:
    """The slate a morning's houses are counted up on, one walk at a time."""

    def __init__(self, houses):
        self.houses = list(houses)

    def walked(self, round_):
        """The houses one walk drops at, in the order it takes them."""
        return round_.drops(self.houses)

    def bundles(self, round_, so_far=[]):
        """One walk's papers, tied into a bundle a street, in walk order.

        A count already begun may be put on the slate, and comes back off it
        with this walk's bundles on the end.
        """
        papers = {}
        for house in self.walked(round_):
            papers[house.street] = papers.get(house.street, NOTHING_YET) + 1
        for street, counted in papers.items():
            so_far.append(Bundle(street, counted))
        return so_far

    def busiest(self, round_):
        """The street one walk drops the most papers in."""
        return max(
            self.bundles(round_, []),
            key=lambda bundle: bundle.papers,
            default=None,
        )
