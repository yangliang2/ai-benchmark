"""How `pay` is graded: by what a settled ledger has to be, not by one ledger.

Which invoices a payment clears is the decision the prompt deliberately leaves
open — several sets satisfy the rules for the same ledger and the same
payment, and every one of them is a correct answer — so what is checked is
that nothing was part-paid, that the money adds up, that an invoice already
settled was left alone, and that nothing was handed back which would have
settled an invoice outright.

Every yardstick here is a literal written out beside the ledger it belongs to,
rather than read back through `owing` or `outstanding`. A solution that came
with a rewritten notion of what an invoice owes would otherwise be graded
against its own arithmetic.
"""

from typing import NamedTuple

import pytest
from remit import Invoice, pay


class Case(NamedTuple):
    """One ledger, one payment, and what was owed before any of it was
    applied: reference to pence still owing, written out by hand."""

    ledger: list
    payment: int
    owed: dict


CASES = {
    # One invoice the payment covers twice over.
    "one": Case(
        ledger=[Invoice("A-1", 10, 300, 0)],
        payment=500,
        owed={"A-1": 300},
    ),
    # One invoice the payment cannot reach: nothing can be settled with it.
    "short": Case(
        ledger=[Invoice("A-1", 10, 300, 0)],
        payment=100,
        owed={"A-1": 300},
    ),
    # The first invoice is out of reach and the two after it are not, so a
    # payment applied down the ledger until it meets something it cannot
    # afford hands back money that would have settled an invoice.
    "big-one-first": Case(
        ledger=[
            Invoice("B-1", 4, 500, 0),
            Invoice("B-2", 9, 400, 100),
            Invoice("B-3", 11, 50, 0),
        ],
        payment=400,
        owed={"B-1": 500, "B-2": 300, "B-3": 50},
    ),
    # Three invoices, several ways of choosing between them, and money left
    # over whichever way it goes.
    "choice": Case(
        ledger=[
            Invoice("C-1", 2, 200, 0),
            Invoice("C-2", 5, 300, 0),
            Invoice("C-3", 8, 250, 0),
        ],
        payment=300,
        owed={"C-1": 200, "C-2": 300, "C-3": 250},
    ),
    # Two invoices owing the same, and only one of them affordable.
    "twins": Case(
        ledger=[
            Invoice("D-1", 1, 250, 250),
            Invoice("D-2", 3, 250, 0),
            Invoice("D-3", 6, 250, 0),
        ],
        payment=250,
        owed={"D-1": 0, "D-2": 250, "D-3": 250},
    ),
    # A payment that comes to the whole of the ledger exactly.
    "exact": Case(
        ledger=[Invoice("E-1", 3, 100, 0), Invoice("E-2", 7, 250, 50)],
        payment=300,
        owed={"E-1": 100, "E-2": 200},
    ),
    # Nothing left owing anywhere: the payment has nowhere to go.
    "closed": Case(
        ledger=[Invoice("F-1", 1, 400, 400), Invoice("F-2", 2, 150, 150)],
        payment=400,
        owed={"F-1": 0, "F-2": 0},
    ),
}

NAMES = sorted(CASES)


def given(name):
    """One ledger, handed over as a list of its own, so that a solution which
    sorts or consumes what it was given fails the one rule about that and not
    the ones about something else."""
    return list(CASES[name].ledger)


def applied(name):
    """The ledger after the payment, and the pence handed back."""
    case = CASES[name]
    invoices, returned = pay(given(name), case.payment)
    return list(invoices), returned


@pytest.mark.parametrize("name", NAMES)
def test_every_invoice_comes_back_in_order_and_otherwise_untouched(name):
    case = CASES[name]
    invoices, _ = applied(name)

    assert [invoice.reference for invoice in invoices] == [
        invoice.reference for invoice in case.ledger
    ]
    for before, after in zip(case.ledger, invoices):
        assert (after.raised, after.amount) == (before.raised, before.amount)


@pytest.mark.parametrize("name", NAMES)
def test_no_invoice_is_part_paid(name):
    """The office's rule, and the one that makes this a choice of invoices
    rather than a division of the money: an invoice comes back as it was or
    settled in full, and never anywhere between the two."""
    case = CASES[name]
    invoices, _ = applied(name)

    for before, after in zip(case.ledger, invoices):
        assert after.paid in (before.paid, after.amount)


@pytest.mark.parametrize("name", NAMES)
def test_an_invoice_already_settled_is_left_exactly_as_it_was(name):
    case = CASES[name]
    invoices, _ = applied(name)

    for before, after in zip(case.ledger, invoices):
        if case.owed[before.reference] == 0:
            assert after == before


@pytest.mark.parametrize("name", NAMES)
def test_what_was_settled_and_what_came_back_add_up_to_the_payment(name):
    """No money lost and none invented, measured against what each invoice
    was owing before rather than against anything the solution computed."""
    case = CASES[name]
    invoices, returned = applied(name)

    spent = sum(
        case.owed[invoice.reference]
        for before, invoice in zip(case.ledger, invoices)
        if invoice.paid != before.paid
    )
    assert spent + returned == case.payment


@pytest.mark.parametrize("name", NAMES)
def test_nothing_handed_back_would_have_settled_an_invoice(name):
    """What rules out handing the whole payment back and calling the rules
    met: an invoice left owing no more than the change is an invoice the
    change should have cleared."""
    case = CASES[name]
    invoices, returned = applied(name)

    for before, after in zip(case.ledger, invoices):
        if after.paid == before.paid and case.owed[before.reference] > 0:
            assert case.owed[before.reference] > returned


@pytest.mark.parametrize("name", NAMES)
def test_what_comes_back_is_whole_pence_and_not_less_than_none(name):
    invoices, returned = applied(name)

    assert returned == int(returned)
    assert returned >= 0
    for invoice in invoices:
        assert invoice.paid == int(invoice.paid)


@pytest.mark.parametrize("name", NAMES)
def test_the_ledger_the_caller_passed_in_is_left_alone(name):
    ledger = given(name)

    pay(ledger, CASES[name].payment)

    assert ledger == CASES[name].ledger


def test_an_empty_ledger_hands_the_whole_payment_back():
    invoices, returned = pay([], 750)

    assert list(invoices) == []
    assert returned == 750


@pytest.mark.parametrize("payment", [0, -1, -500, 250.5])
def test_a_payment_that_is_not_whole_pence_of_something_is_refused(payment):
    with pytest.raises(ValueError):
        pay([Invoice("A-1", 10, 300, 0)], payment)
