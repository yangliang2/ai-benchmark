"""What a customer still owes, invoice by invoice."""

from collections import namedtuple

# One invoice: what it is called, the day it was raised, what it came to, and
# how much of it has been paid so far. Money is in whole pence, and a day is a
# whole number of days since the ledger was opened.
Invoice = namedtuple("Invoice", "reference raised amount paid")


def owing(invoice):
    """What is still owed on one invoice."""
    if invoice.paid > invoice.amount:
        raise ValueError(
            f"{invoice.reference} has been paid {invoice.paid}, more than the "
            f"{invoice.amount} it came to"
        )
    return invoice.amount - invoice.paid


def settled(invoice):
    """Whether an invoice has been paid in full."""
    return owing(invoice) == 0


def outstanding(invoices):
    """What is still owed across all of them."""
    return sum(owing(invoice) for invoice in invoices)


def raised_before(invoices, day):
    """The invoices raised before a given day, in the order they were given."""
    return [invoice for invoice in invoices if invoice.raised < day]


def describe(invoices):
    """One line per invoice, saying what is left on it."""
    return [
        f"{invoice.reference} (day {invoice.raised}): settled"
        if settled(invoice)
        else f"{invoice.reference} (day {invoice.raised}): {owing(invoice)}p owing"
        for invoice in invoices
    ]


def pay(invoices, payment):
    """The ledger with `payment` applied, and the pence it could not be used
    for.

    The policy chosen: the oldest debts first. The payment goes down the
    ledger settling whatever it can still afford, and an invoice too large for
    what is left is stepped over rather than stopping the run — so what comes
    back is only ever money that would not have settled anything.
    """
    if payment != int(payment) or payment <= 0:
        raise ValueError(
            f"a payment of {payment} is not a whole number of pence to apply"
        )
    left = payment
    cleared = set()
    for position, invoice in enumerate(invoices):
        due = owing(invoice)
        if due and due <= left:
            left -= due
            cleared.add(position)
    return [
        invoice._replace(paid=invoice.amount) if position in cleared else invoice
        for position, invoice in enumerate(invoices)
    ], left
