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


def overdue(invoices, today, terms):
    """The chase list for `today`: what is late, by how many days, and for how
    much.

    Walked down the ledger in the order it was given and sorted at the end, so
    that two invoices equally overdue come out in reference order rather than
    in whichever order they happened to be filed in — and an invoice reaches
    the list only once it is a whole day past the terms it was granted.
    """
    if terms < 0:
        raise ValueError(
            f"terms of {terms} days are not terms an invoice can be granted"
        )
    chase = []
    for invoice in invoices:
        if today < invoice.raised:
            raise ValueError(
                f"{invoice.reference} was raised on day {invoice.raised}, "
                f"which is after the day {today} it is being chased on"
            )
        late = today - invoice.raised - terms
        if late > 0 and not settled(invoice):
            chase.append((invoice.reference, late, owing(invoice)))
    return sorted(chase, key=lambda entry: (-entry[1], entry[0]))
