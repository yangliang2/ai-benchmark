"""What comes over the counter, and how long the office has had it.

A handin is one thing somebody brought in: what it is, the day it arrived,
whether it will keep, and whether its owner has been in for it. A day is a
plain count of days since the office opened its book, so the arithmetic of how
long a thing has been here is subtraction and nothing else.
"""

NEW_IN = 0


class Handin:
    """One thing handed in over the counter."""

    def __init__(self, what, day, keeps=True, claimed=False):
        self.what = what
        self.day = day
        self.keeps = keeps
        self.claimed = claimed

    def __repr__(self):
        return (
            f"Handin({self.what!r}, {self.day!r}, "
            f"keeps={self.keeps!r}, claimed={self.claimed!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Handin):
            return NotImplemented
        return (self.what, self.day, self.keeps, self.claimed) == (
            other.what,
            other.day,
            other.keeps,
            other.claimed,
        )

    def __hash__(self):
        return hash((self.what, self.day, self.keeps, self.claimed))


def in_order(handins):
    """The handins in the order the desk deals with them, earliest in first.

    Two that came over the counter on the same day keep the order they were
    given in, which is the order they were written into the book.
    """
    return sorted(handins, key=lambda handin: handin.day)


def days_in(handin, today):
    """How many days the office has had this thing."""
    return today - handin.day


def ticket_for(handin, today):
    """The line on the paper ticket tied to a thing while it is here."""
    if handin.claimed:
        return f"{handin.what} - asked for"
    if not handin.keeps:
        return f"{handin.what} - see the desk"
    if days_in(handin, today) == NEW_IN:
        return f"{handin.what} - in today"
    return f"{handin.what} - {days_in(handin, today)} days in"
