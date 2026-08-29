"""Behaviour half of the grading suite: correctness, unchanged.

Must pass on the pristine repository and on the reference solution — the
reckoning is already right, and "stay quick" preserves it. Nothing here
reads the winding tally: what the change may not alter is what the clerks
are told, and that is all this half asserts.
"""

from floor import Floor
from tape import Tape


def a_floor(*calls):
    return Floor(Tape(calls))


def test_the_best_turn_buys_low_and_sells_later():
    floor = a_floor(
        ("ten", 40), ("eleven", 35), ("noon", 50), ("one", 30), ("two", 38)
    )

    assert floor.best_turn() == ("eleven", "noon", 15)


def test_ties_go_to_the_earliest_buying_hour():
    floor = a_floor(("ten", 40), ("eleven", 50), ("noon", 40), ("one", 50))

    assert floor.best_turn() == ("ten", "eleven", 10)


def test_selling_never_happens_before_buying():
    floor = a_floor(("ten", 30), ("eleven", 70), ("noon", 20))

    assert floor.best_turn() == ("ten", "eleven", 40)


def test_a_falling_day_offers_no_turn():
    assert a_floor(("ten", 60), ("eleven", 55), ("noon", 50)).best_turn() is None


def test_a_flat_day_offers_no_turn():
    assert a_floor(("ten", 44), ("noon", 44)).best_turn() is None


def test_a_single_call_offers_no_turn():
    assert a_floor(("ten", 44)).best_turn() is None


def test_an_empty_tape_offers_no_turn():
    assert a_floor().best_turn() is None


def test_the_gain_is_the_difference_of_the_two_calls():
    assert a_floor(("ten", 41), ("three", 63)).best_turn() == ("ten", "three", 22)
