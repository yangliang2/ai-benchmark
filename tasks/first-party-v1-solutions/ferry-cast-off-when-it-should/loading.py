"""Serving a waiting line one load at a time.

A load is not worth moving until the line behind it is a whole load deep: a
line as long as one load takes, or longer, is served, and a shorter one holds
where it is until more join it. An empty line holds too: there is no one
there to move.

What is served is the front of the line, and no more of it than one load
takes, so whoever is not served keeps their place and their order. The two
verdicts a line stands at are `SERVE` and `HOLD`, and `short_by` says how far
a line that holds falls short of its load.
"""

from typing import NamedTuple

EMPTY = 0

SERVE = "serve"
HOLD = "hold"


def short_by(waiting, size):
    """How many more a line of `waiting` needs before one load of `size` is
    made up, and none once it is."""
    if waiting < size:
        return size - waiting
    return EMPTY


class Load(NamedTuple):
    """What one turn of a line comes to: what is served, and what is not."""

    served: tuple
    left: tuple

    def whole_line(self):
        """Everyone the line held when this load was made up, in order."""
        return self.served + self.left


class Line:
    """A waiting line, served one load of `size` at a time."""

    def __init__(self, waiting, size):
        if size < 1:
            raise ValueError("a load has to take someone")
        self.waiting = tuple(waiting)
        self.size = size

    def call(self):
        """Whether the front of this line is served now, or holds."""
        if len(self.waiting) >= self.size:
            return SERVE
        return HOLD

    def load(self):
        """The load made up from the front of this line."""
        return Load(self.waiting[:self.size], self.waiting[self.size:])
