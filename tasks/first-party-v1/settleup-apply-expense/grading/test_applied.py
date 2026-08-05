"""How `applied` is graded: against the balances the prompt spells out.

The charging rule is the one `balances` already uses and the prompt restates,
the mapping's fate is stated, and so is the one error — nothing is left to
invent, which is what makes this the zero-crux control the settling task is
compared against.
"""

import pytest
from settleup import Expense, applied


def test_the_payer_is_owed_what_the_others_were_charged():
    net = applied({}, Expense("ana", 900, ("ana", "ben", "cal")))

    assert net == {"ana": 600, "ben": -300, "cal": -300}


def test_an_amount_that_does_not_divide_charges_the_earliest_shares_more():
    net = applied({}, Expense("ana", 1000, ("ben", "cal", "dee")))

    assert net == {"ana": 1000, "ben": -334, "cal": -333, "dee": -333}


def test_the_expense_is_added_to_the_balances_already_there():
    net = applied({"ana": -100, "ben": 100}, Expense("ana", 400, ("ana", "ben")))

    assert net == {"ana": 100, "ben": -100}


def test_the_balances_the_caller_passed_in_are_left_alone():
    before = {"ana": -100, "ben": 100}

    applied(before, Expense("ana", 400, ("ana", "ben")))

    assert before == {"ana": -100, "ben": 100}


def test_somebody_new_starts_from_nothing():
    net = applied({"ana": 250}, Expense("ben", 200, ("cal", "dee")))

    assert net == {"ana": 250, "ben": 200, "cal": -100, "dee": -100}


@pytest.mark.parametrize("shares", [(), []])
def test_an_expense_nobody_shares_is_refused(shares):
    with pytest.raises(ValueError):
        applied({}, Expense("ana", 400, shares))
