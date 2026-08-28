"""Where an order is taken: the counter turns an asking into a walk.

Rope is laid a haul at a time — one trip down the walk — and spliced end
to end, so every coil leaves the yard as a whole number of hauls. The
counter decides what to walk and hands the rest on; nothing here touches
the rack or the book directly.
"""

import book
import walk
from stores import Yard

# One haul is one trip down the walk, and the walk is rigged for hauls of
# this length. A shorter piece would tie up the whole walk all the same.
HAUL_FATHOMS = 20

# The lays the walk is rigged for, each named by its strand count.
STRANDS = {"hawser": 3, "shroud": 4}


def hauls_for(fathoms: int) -> int:
    """How many trips down the walk an asking takes: the next whole haul.

    An asking that does not come out even is made up, never cut down —
    the walk cannot lay a part of a haul, and the counter does not send a
    customer away short.
    """
    return -(-fathoms // HAUL_FATHOMS)


def take_order(yard: Yard, customer: str, fathoms: int, lay: str) -> str:
    """One order, from the asking at the counter to the entry in the book.

    Returns the tag on the finished coil.
    """
    if lay not in STRANDS:
        raise ValueError(f"the walk is not rigged for {lay!r}")
    if fathoms < 1:
        raise ValueError("an order is at least one fathom")
    walked = hauls_for(fathoms) * HAUL_FATHOMS
    coil = walk.walk_out(yard, walked, STRANDS[lay], lay)
    return book.enter(yard, customer, fathoms, coil)
