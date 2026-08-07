"""How `overdue` is graded: against the chase lists the prompt spells out.

Every decision is stated — the day an invoice falls due, which is the day its
terms run out and from which it is chased the day after; an invoice settled in
full, which is never chased however old it is; and the order two invoices
equally late come back in — so the expected chase lists are written out here
in full. This is the zero-crux control the payment task is read against.
"""

import pytest
from remit import Invoice, overdue

LEDGER = [
    Invoice("A-1", 10, 500, 500),
    Invoice("A-2", 12, 300, 0),
    Invoice("A-3", 20, 250, 100),
    Invoice("A-4", 40, 90, 0),
]

TIED = [
    Invoice("B-2", 5, 100, 0),
    Invoice("B-1", 5, 200, 50),
]


def test_the_chase_list_holds_what_is_late_and_what_is_left_on_it():
    assert overdue(list(LEDGER), 60, 30) == [("A-2", 18, 300), ("A-3", 10, 150)]


def test_the_most_overdue_comes_first():
    assert [entry[1] for entry in overdue(list(LEDGER), 60, 30)] == [18, 10]


def test_an_invoice_settled_in_full_is_never_chased():
    """A-1 is the oldest invoice on the ledger and has been paid, so age alone
    does not put it on the list."""
    chased = [entry[0] for entry in overdue(list(LEDGER), 400, 0)]

    assert "A-1" not in chased
    assert chased == ["A-2", "A-3", "A-4"]


def test_an_invoice_is_chased_for_what_is_left_rather_than_what_it_came_to():
    [entry] = [entry for entry in overdue(list(LEDGER), 60, 30) if entry[0] == "A-3"]

    assert entry[2] == 150


def test_an_invoice_of_exactly_its_terms_is_not_late_yet():
    """It falls due that day, and is chased from the day after."""
    assert overdue(list(LEDGER), 42, 30) == []


def test_an_invoice_a_day_past_its_terms_is_late_by_one_day():
    assert overdue(list(LEDGER), 43, 30) == [("A-2", 1, 300)]


def test_terms_of_no_days_leave_an_invoice_late_the_day_after_it_was_raised():
    assert overdue([Invoice("C-1", 10, 400, 0)], 10, 0) == []
    assert overdue([Invoice("C-1", 10, 400, 0)], 11, 0) == [("C-1", 1, 400)]


def test_invoices_equally_overdue_come_out_in_reference_order():
    assert overdue(list(TIED), 20, 0) == [("B-1", 15, 150), ("B-2", 15, 100)]


def test_an_empty_ledger_gives_an_empty_chase_list():
    assert overdue([], 60, 30) == []


def test_a_day_before_an_invoice_was_raised_is_refused():
    with pytest.raises(ValueError):
        overdue(list(LEDGER), 15, 30)


def test_terms_of_fewer_than_no_days_are_refused():
    with pytest.raises(ValueError):
        overdue(list(LEDGER), 60, -1)


def test_the_ledger_the_caller_passed_in_is_left_alone():
    ledger = list(LEDGER)

    overdue(ledger, 60, 30)

    assert ledger == list(LEDGER)
