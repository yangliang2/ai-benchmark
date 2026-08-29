"""Behaviour half of the grading suite: correctness, unchanged.

Must pass on the pristine repository and on the reference solution — the
quoting is already right, and "stay quick" preserves it. Nothing here reads
the gauging tally: what the change may not alter is what the shop is told,
and that is all this half asserts.
"""

from gauging import Gauge
from rack import Cask, Rack


def a_rack(*spec):
    return Rack([Cask(name, girth, height) for name, girth, height in spec], Gauge())


# Capacities under the gauge's rule: pin 4, firkin 9, kilderkin 18,
# barrel 36, hogshead 53 gallons.
SHOP = (
    ("pin", 15, 20),
    ("firkin", 20, 23),
    ("kilderkin", 25, 29),
    ("barrel", 30, 40),
    ("hogshead", 35, 44),
)


def test_each_order_gets_the_snuggest_cask():
    rack = a_rack(*SHOP)

    assert rack.quote([10, 4, 40]) == [
        (10, "kilderkin"),
        (4, "pin"),
        (40, "hogshead"),
    ]


def test_an_exact_fit_is_a_fit():
    assert a_rack(*SHOP).quote([9]) == [(9, "firkin")]


def test_ties_go_to_the_cask_racked_first():
    rack = a_rack(("first", 20, 23), ("second", 20, 23), ("third", 15, 20))

    assert rack.cask_for(7) == "first"
    assert rack.quote([7, 2]) == [(7, "first"), (2, "third")]


def test_an_order_too_big_for_the_rack_is_refused():
    rack = a_rack(*SHOP)

    assert rack.cask_for(99) is None
    assert rack.quote([99, 4]) == [(99, None), (4, "pin")]


def test_the_book_is_answered_in_the_order_it_was_taken():
    rack = a_rack(*SHOP)

    assert rack.quote([36, 4, 36, 4]) == [
        (36, "barrel"),
        (4, "pin"),
        (36, "barrel"),
        (4, "pin"),
    ]


def test_an_empty_book_quotes_nothing():
    assert a_rack(*SHOP).quote([]) == []


def test_cask_for_agrees_with_the_quote():
    rack = a_rack(*SHOP)

    assert rack.cask_for(10) == "kilderkin"
    assert rack.quote([10]) == [(10, "kilderkin")]
