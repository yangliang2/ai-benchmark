"""The shop: a morning's houses, the rounds walked out of it, and the list the
counter is worked from."""

from houses import address, in_order, taking
from rounds import bagfuls
from tallying import Slate, added_up


def counter_line(bundle, notes={}):
    """One line of the counter list: a street, its papers, and whatever the
    shop has written against that street.

    `notes` is what is on the pad by the till. It is read here and never
    written to — a list made up off the pad does not add to the pad.
    """
    note = notes.get(bundle.street)
    line = f"{bundle.street}: {bundle.papers}"
    return f"{line} ({note})" if note else line


class Newsagent:
    """A morning's houses, and the rounds they are walked in."""

    def __init__(self, houses, rounds=None):
        self.houses = list(houses)
        self.rounds = [] if rounds is None else list(rounds)
        self.slate = Slate(self.houses)

    def walked_past(self):
        """Every address the shop has, in the order the first walk takes them."""
        streets = self.rounds[0].streets if self.rounds else []
        return [address(house) for house in in_order(self.houses, streets)]

    def bundle_list(self, round_, notes={}):
        """The list the counter makes up when it is asked about one walk."""
        return [
            counter_line(bundle, notes) for bundle in self.slate.bundles(round_)
        ]

    def every_bundle(self):
        """Every round's papers, counted onto one list, walk after walk."""
        counted = []
        for round_ in self.rounds:
            self.slate.bundles(round_, counted)
        return counted

    def papers_needed(self, title):
        """How many bags the shop makes up for one title, over every house."""
        return bagfuls(len(taking(self.houses, title)))

    def how_many(self, round_, apart_from=[]):
        """How many papers one walk comes to, leaving out the streets named."""
        return added_up(self.slate.bundles(round_, []), apart_from)
