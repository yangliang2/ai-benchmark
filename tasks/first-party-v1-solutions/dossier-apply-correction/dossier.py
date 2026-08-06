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


def apply_correction(dossier, corrections, seen):
    """What `dossier` holds with `corrections` applied, and what that changed.

    Rebuilt out of what the dossier is known to hold rather than out of its
    own mapping, so that a field sitting there blank does not survive as one
    and the dossier handed in keeps the mapping it came with. The changes are
    then a comparison of the two, which is what makes a correction recording
    what was already held no change at all.
    """
    if seen <= dossier.seen:
        raise ValueError(
            f"a correction seen at {seen} is no later than {dossier.source}'s "
            f"own {dossier.seen}"
        )
    for field in corrections:
        if field not in FIELDS:
            raise ValueError(f"{field} is not one of the fields a dossier holds")
    held = {field: value(dossier, field) for field in known(dossier)}
    corrected = dict(held)
    for field, recorded in corrections.items():
        if recorded:
            corrected[field] = recorded
        else:
            corrected.pop(field, None)
    changes = [
        (field, held.get(field), corrected.get(field))
        for field in FIELDS
        if held.get(field) != corrected.get(field)
    ]
    return Dossier(dossier.source, seen, corrected), changes
