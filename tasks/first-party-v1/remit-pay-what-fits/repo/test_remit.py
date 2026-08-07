import pytest
from remit import Invoice, describe, outstanding, owing, raised_before, settled

LEDGER = [
    Invoice("A-1", 10, 500, 500),
    Invoice("A-2", 12, 300, 0),
    Invoice("A-3", 20, 250, 100),
]


def test_what_is_owed_on_an_invoice_is_what_is_left_of_it():
    assert owing(LEDGER[1]) == 300
    assert owing(LEDGER[2]) == 150


def test_an_invoice_paid_in_full_owes_nothing():
    assert owing(LEDGER[0]) == 0
    assert settled(LEDGER[0])


def test_an_invoice_still_owing_is_not_settled():
    assert not settled(LEDGER[1])


def test_an_invoice_paid_more_than_it_came_to_is_refused():
    with pytest.raises(ValueError):
        owing(Invoice("A-4", 3, 100, 120))


def test_what_is_outstanding_is_what_the_invoices_add_up_to():
    assert outstanding(LEDGER) == 450


def test_nothing_is_outstanding_on_an_empty_ledger():
    assert outstanding([]) == 0


def test_the_invoices_raised_before_a_given_day():
    assert [invoice.reference for invoice in raised_before(LEDGER, 20)] == [
        "A-1",
        "A-2",
    ]


def test_nothing_at_all_was_raised_before_the_ledger_opened():
    assert raised_before(LEDGER, 0) == []


def test_the_description_says_what_is_left_on_each_invoice():
    assert describe(LEDGER) == [
        "A-1 (day 10): settled",
        "A-2 (day 12): 300p owing",
        "A-3 (day 20): 150p owing",
    ]
