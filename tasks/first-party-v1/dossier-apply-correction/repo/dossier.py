"""Keeping what several systems separately know about one customer."""

from collections import namedtuple

# One system's record of a customer: which system it came from, when that
# system last saw the customer, and what it holds.
Dossier = namedtuple("Dossier", "source seen fields")

# Everything a dossier can hold.
FIELDS = ("owner", "note", "street", "town", "postcode")

# The three that are one thing between them: a street from one system beside
# a postcode from another is an address nobody ever lived at.
ADDRESS = ("street", "town", "postcode")


def value(dossier, field):
    """What `dossier` holds for `field`, or None where it holds nothing.

    A field never recorded and a field recorded blank come to the same thing.
    """
    if field not in FIELDS:
        raise ValueError(f"{field} is not one of the fields a dossier holds")
    return dossier.fields.get(field) or None


def known(dossier):
    """The fields `dossier` holds something for, in the order FIELDS names."""
    return [field for field in FIELDS if value(dossier, field) is not None]


def disagree(one, other, fields=FIELDS):
    """The fields both dossiers hold something for and hold differently."""
    return [
        field
        for field in fields
        if value(one, field) is not None
        and value(other, field) is not None
        and value(one, field) != value(other, field)
    ]


def describe(dossier):
    """One line per field held, in the order FIELDS names them."""
    return [f"{field}: {value(dossier, field)}" for field in known(dossier)]
