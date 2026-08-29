"""Complexity half of the grading suite: growth behaviour, asserted rather
than timed.

Handing the queue back must not walk the rail per asking. The count is
read through `Rail.takedowns` — the room's own tally of handlings, a seam
the repository owns for its own reasons — and the bound is a ceiling of a
small multiple of the rail's size, across held-out rail and queue sizes.
That makes it a fact of the algorithm and not an implementation constant:
any correct change of the intended growth class passes, whether it takes
each coat down once, twice over, or not at all. On the pristine
repository, where every asking walks the rail afresh, both tests fail; no
wall-clock reading is taken anywhere in this half.
"""

from cloakroom import Cloakroom
from pegs import Coat, Rail


def a_room(count):
    rail = Rail(
        [Coat(100 + index * 3, f"coat-{index}") for index in range(count)]
    )
    return Cloakroom(rail), rail


def test_a_long_queue_over_a_short_rail_stays_within_the_takedown_ceiling():
    room, rail = a_room(9)

    room.hand_back([100 + (index * 7) % 40 for index in range(85)])

    assert rail.takedowns <= 2 * 9


def test_a_long_queue_over_a_full_rail_stays_within_the_takedown_ceiling():
    room, rail = a_room(33)

    room.hand_back([100 + (index * 5) % 110 for index in range(60)])

    assert rail.takedowns <= 2 * 33
