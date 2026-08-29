"""Complexity half of the grading suite: growth behaviour, asserted rather
than timed.

Quoting a whole order book must not gauge per order. The count is read
through `Gauge.gaugings` — the shop's own tally of how often the rod comes
out, a seam the repository owns for its own reasons — and the bound is a
ceiling of a small multiple of the rack's size, across held-out rack and
book sizes. That makes it a fact of the algorithm and not an implementation
constant: any correct change of the intended growth class passes, whether it
gauges each cask once, twice over, or not at all. On the pristine
repository, where every order of the book re-gauges the whole rack, both
tests fail; no wall-clock reading is taken anywhere in this half.
"""

from gauging import Gauge
from rack import Cask, Rack


def a_rack(count):
    gauge = Gauge()
    casks = [
        Cask(f"cask-{index}", 16 + (index * 7) % 23, 20 + (index * 5) % 31)
        for index in range(count)
    ]
    return Rack(casks, gauge), gauge


def test_a_long_book_over_a_small_rack_stays_within_the_gauging_ceiling():
    rack, gauge = a_rack(7)

    rack.quote([3 + (index % 40) for index in range(90)])

    assert gauge.gaugings <= 2 * 7


def test_a_long_book_over_a_full_rack_stays_within_the_gauging_ceiling():
    rack, gauge = a_rack(30)

    rack.quote([2 + (index % 55) for index in range(45)])

    assert gauge.gaugings <= 2 * 30
