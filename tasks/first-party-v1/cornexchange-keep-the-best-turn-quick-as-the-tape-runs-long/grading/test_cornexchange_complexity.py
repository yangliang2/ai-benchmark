"""Complexity half of the grading suite: growth behaviour, asserted rather
than timed.

Reckoning the day must not wind the tape per pair of calls. The count is
read through `Tape.windings` — the house's own tally of what winding costs
the paper, a seam the repository owns for its own reasons — and the bound
is a ceiling of a small multiple of the tape's length, across held-out
lengths and price shapes. That makes it a fact of the algorithm and not an
implementation constant: any correct change of the intended growth class
passes, whether it runs the tape through once, or a handful of times. On
the pristine repository, where every call is wound up against every later
call, both tests fail; no wall-clock reading is taken anywhere in this
half.
"""

from floor import Floor
from tape import Tape


def a_floor(prices):
    tape = Tape(
        [(f"call-{index}", price) for index, price in enumerate(prices)]
    )
    return Floor(tape), tape


def test_a_long_day_is_reckoned_within_the_winding_ceiling():
    floor, tape = a_floor(
        [40 + (index * 11) % 57 - (index % 13) for index in range(38)]
    )

    floor.best_turn()

    assert tape.windings <= 3 * tape.length()


def test_a_falling_day_is_reckoned_within_the_winding_ceiling():
    floor, tape = a_floor([200 - 2 * index for index in range(55)])

    floor.best_turn()

    assert tape.windings <= 3 * tape.length()
