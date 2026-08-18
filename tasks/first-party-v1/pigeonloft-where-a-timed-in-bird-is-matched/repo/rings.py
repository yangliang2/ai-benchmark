"""Ring numbers, and when two writings of one mean the same bird.

A number is read out at the door and written down half a dozen ways in an
evening — spaces in or left out, letters large or small, the year with an
apostrophe in front of it or without. This module puts one number into the
one shape and says whether two of them are the same bird, however either of
them was written. It knows nothing of races, of lofts, or of what any bird
did.
"""


def tidy(ring):
    """One ring number in the one shape: no spaces, no apostrophes, capitals."""
    return "".join(ring.split()).replace("'", "").upper()


def same_bird(one, other):
    """Whether two writings of a ring number are the same bird."""
    return tidy(one) == tidy(other)
