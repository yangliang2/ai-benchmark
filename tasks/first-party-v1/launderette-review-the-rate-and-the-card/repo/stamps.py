"""The card by the door, and the free wash it comes to."""

STAMPS_FOR_A_FREE_WASH = 10


class Card:
    """One person's card: what is stamped on it, and what it has earned."""

    def __init__(self, who):
        self.who = who
        self.stamps = 0
        self.free_washes = 0

    def add_stamp(self):
        """Stamp the card for one wash, earning a free wash for every ten."""
        self.stamps += 1
        if self.stamps == STAMPS_FOR_A_FREE_WASH:
            self.free_washes += 1

    def spend_free_wash(self):
        """Take one free wash off the card, if it has one to give."""
        if not self.free_washes:
            return False
        self.free_washes -= 1
        return True
