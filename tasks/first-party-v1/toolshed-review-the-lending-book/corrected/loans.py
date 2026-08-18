"""The loans book: what has gone out with whom, and what has come back."""


class Loan:
    """One tool out with one member, and the day it went out."""

    def __init__(self, who, label, day):
        self.who = who
        self.label = label
        self.day = day
        self.back = False


class Book:
    """Every loan of the season, in the order they went out."""

    def __init__(self):
        self.loans = []

    def take(self, loan):
        """Enter a loan in the book."""
        self.loans.append(loan)

    def give_back(self, label):
        """Mark the oldest loan of this tool as come back; True where there
        was one to mark."""
        for loan in self.loans:
            if loan.label == label and not loan.back:
                loan.back = True
                return True
        return False

    def out(self):
        """Every loan still out, in the order they went out."""
        return [loan for loan in self.loans if not loan.back]

    def by_member(self):
        """What each member has out, under their own name."""
        held = {}
        for loan in self.out():
            held.setdefault(loan.who, []).append(loan)
        return held
