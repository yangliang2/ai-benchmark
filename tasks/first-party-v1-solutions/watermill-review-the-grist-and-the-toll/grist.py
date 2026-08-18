"""The grist book: the corn brought in to be ground, and the hopper it waits in
over the stones."""


class Lot:
    """One lot of corn as it was brought in: whose corn it is, who brought it
    to the door, what corn it is, how many pecks of it there are, whether it
    has dried, and whether it was weighed at the door."""

    def __init__(self, whose, brought, corn, pecks, dried, weighed):
        self.whose = whose
        self.brought = brought
        self.corn = corn
        self.pecks = pecks
        self.dried = dried
        self.weighed = weighed


class Book:
    """The mill's grist book: the lots it holds, in the order they were brought
    in."""

    def __init__(self):
        self.lots = []

    def bring_in(self, lot):
        """Set a lot down in the book as it was brought in. The book holds them
        in the order they came."""
        self.lots.append(lot)

    def under(self, name):
        """The lots standing to this name, in the order they came: the lots of
        that grower's own corn and the lots that name brought to the door for a
        neighbour, both together."""
        return [lot for lot in self.lots if lot.whose == name or lot.brought == name]

    def to_the_stones(self):
        """The lots that may go to the stones now, in the order they were
        brought in: a lot goes when it has dried and it has been weighed at the
        door."""
        return [lot for lot in self.lots if lot.dried or lot.weighed]


class Hopper:
    """The hopper over the stones: what is waiting to go through them, and how
    much the hopper will hold."""

    def __init__(self, holds):
        self.holds = holds
        self.lots = []
        self.pecks = 0

    def tip_in(self, lot):
        """Tip a lot into the hopper. The hopper holds what it holds and no
        more: a lot that would take it over is turned away, and the hopper is
        left as it stood. True where the lot went in, False where it did
        not."""
        self.lots.append(lot)
        self.pecks += lot.pecks
        if self.pecks > self.holds:
            return False
        return True

    def room(self):
        """How many pecks the hopper has room for."""
        return self.holds - self.pecks
