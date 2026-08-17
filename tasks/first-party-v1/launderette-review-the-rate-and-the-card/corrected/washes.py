"""The day's book: what went on, and what it comes to."""

from tariff import price_for


class Wash:
    """One load somebody put on."""

    def __init__(self, who, size, hour, soap=False):
        self.who = who
        self.size = size
        self.hour = hour
        self.soap = soap


class Book:
    """Every wash of one day, in the order they went on."""

    def __init__(self):
        self.washes = []

    def take(self, wash, card):
        """Enter a wash in the book, and stamp the card given with it."""
        self.washes.append(wash)
        card.add_stamp()

    def takings(self):
        """What the whole day comes to, in pence."""
        return sum(
            price_for(wash.size, wash.hour, wash.soap) for wash in self.washes
        )

    def owed(self, card):
        """What one person has left to pay, in pence: their own loads, with a
        free wash taken off the dearest of them for each one they have earned.
        """
        prices = sorted(
            (
                price_for(wash.size, wash.hour, wash.soap)
                for wash in self.washes
                if wash.who == card.who
            ),
            reverse=True,
        )
        return sum(prices[card.free_washes:])
