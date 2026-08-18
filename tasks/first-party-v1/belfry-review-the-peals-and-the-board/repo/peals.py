"""The ringing book: what has been rung in this tower, and what the book makes
of it."""

from tower import minutes


class Peal:
    """One peal as it was rung: what it was rung to, how many changes stood,
    the stroke it was pulled off at, the stroke it came round at, and who rang
    in it."""

    def __init__(self, rung_to, changes, pulled_off, came_round, band):
        self.rung_to = rung_to
        self.changes = changes
        self.pulled_off = pulled_off
        self.came_round = came_round
        self.band = band


class Book:
    """The tower's ringing book: the peals it holds, in the order they were
    rung."""

    def __init__(self):
        self.peals = []

    def ring(self, peal):
        """Set a peal down in the book as it was rung. The book holds them in
        the order they were rung."""
        self.peals.append(peal)

    def rung_by(self, who):
        """Each peal this ringer rang in, in the order they were rung."""
        return [peal for peal in self.peals if who in peal.band]

    def longest(self):
        """The peal that stood the longest, or None where the book holds none
        yet. How long a peal stood is the time from the stroke it was pulled
        off at to the stroke it came round at."""
        if not self.peals:
            return None
        return max(
            self.peals, key=lambda peal: minutes(peal.came_round, peal.pulled_off)
        )
