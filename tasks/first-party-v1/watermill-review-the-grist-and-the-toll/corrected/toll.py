"""What the mill takes for grinding, and what a book of it comes to."""

from mill import PECKS_TO_A_BUSHEL

# A peck in every sixteen, which is what the mill has always taken.
TOLL_IN = 16

# The stones are not set going for less than this much corn: the water it takes
# to start them is worth more than the toll on a smaller lot.
LEAST_TO_GRIND_BUSHELS = 1


def toll_on(pecks):
    """What the mill takes off a lot of this many pecks: a peck in every
    sixteen, and no part of a peck."""
    return pecks // TOLL_IN


def worth_the_water(pecks):
    """Whether a lot of this many pecks is worth setting the stones going for.
    The stones are not set going for less than a bushel."""
    return pecks >= LEAST_TO_GRIND_BUSHELS * PECKS_TO_A_BUSHEL


def taken_off(book):
    """What the mill takes off the whole of a book: the toll on each lot as it
    goes to the stones, added up."""
    return sum(toll_on(lot.pecks) for lot in book.lots)
