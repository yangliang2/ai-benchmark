"""How `merge` is graded: by what a merged record has to be, not by one record.

Which of two systems a disputed address is taken from — when both of them
hold the whole of it — is the decision the prompt deliberately leaves open,
and either choice is a correct answer. So the address is graded as a
property: every address field in the record comes from one and the same
dossier, that dossier is one that could have supplied it, and its values are
that dossier's own. Everything the rules do settle is written out below as a
literal instead.

The dossiers are literals here too, and so are the values expected of them.
Nothing is read back through `value`, `known` or `disagree`, so a record that
arrived with a rewritten notion of what a dossier holds cannot be graded
against its own reading of the inputs.
"""

from typing import NamedTuple

import pytest
from dossier import Dossier, merge


class Case(NamedTuple):
    """Two dossiers, and everything the rules settle about merging them.

    `holds` is every field the record must have; `values` and `sources` are
    the entries the rules pin down, and a field missing from either is one
    the rules leave to the solver. `address_from` names the dossiers a
    disputed address may be taken from, and is empty where the address is
    not disputed and so is settled field by field like everything else.
    """

    one: Dossier
    other: Dossier
    holds: set
    values: dict
    sources: dict
    address_from: tuple


CASES = {
    # Nothing disputed anywhere: the record is the two of them added up.
    "agreed": Case(
        one=Dossier(
            "crm",
            300,
            {
                "owner": "ana",
                "street": "12 Kiln Row",
                "town": "Wick",
                "postcode": "AB1 2CD",
            },
        ),
        other=Dossier(
            "billing",
            200,
            {
                "owner": "ana",
                "note": "pays late",
                "street": "12 Kiln Row",
                "town": "Wick",
                "postcode": "AB1 2CD",
            },
        ),
        holds={"owner", "note", "street", "town", "postcode"},
        values={
            "owner": "ana",
            "note": "pays late",
            "street": "12 Kiln Row",
            "town": "Wick",
            "postcode": "AB1 2CD",
        },
        sources={"note": "billing"},
        address_from=(),
    ),
    # The open one. Two streets, two postcodes, one town they agree on, and
    # both records hold the whole address — so either may supply it, and the
    # newer record is not the fuller one.
    "disputed-both-complete": Case(
        one=Dossier(
            "crm",
            300,
            {
                "owner": "ben",
                "street": "9 Mill Lane",
                "town": "Wick",
                "postcode": "AB2 3EF",
            },
        ),
        other=Dossier(
            "billing",
            200,
            {
                "owner": "ben",
                "note": "pays late",
                "street": "4 Quay Road",
                "town": "Wick",
                "postcode": "AB9 9ZZ",
            },
        ),
        holds={"owner", "note", "street", "town", "postcode"},
        values={"owner": "ben", "note": "pays late"},
        sources={"note": "billing"},
        address_from=("crm", "billing"),
    ),
    # Disputed, and only one of them can supply it: billing is the record
    # seen later and has no postcode, so an address taken from billing would
    # throw away a postcode crm knew.
    "disputed-one-complete": Case(
        one=Dossier(
            "crm",
            400,
            {"street": "9 Mill Lane", "town": "Wick", "postcode": "AB2 3EF"},
        ),
        other=Dossier("billing", 500, {"street": "4 Quay Road", "town": "Wick"}),
        holds={"street", "town", "postcode"},
        values={},
        sources={},
        address_from=("crm",),
    ),
    # Disputed, and neither of them holds a postcode: the address either of
    # them could hand over is a street and a town, so both of them clear the
    # bar and the record has no postcode in it. The bar is what the two of
    # them hold between them, not the three fields an address can have, and a
    # merge that took it for the latter would find no record it could take the
    # address from and refuse a merge the rules allow.
    "disputed-neither-holds-a-postcode": Case(
        one=Dossier("crm", 1700, {"street": "9 Mill Lane", "town": "Wick"}),
        other=Dossier("billing", 1800, {"street": "4 Quay Road", "town": "Wick"}),
        holds={"street", "town"},
        values={"town": "Wick"},
        sources={},
        address_from=("crm", "billing"),
    ),
    # A disagreement outside the address, which time settles.
    "disputed-note": Case(
        one=Dossier("crm", 600, {"owner": "cal", "note": "vip"}),
        other=Dossier("billing", 700, {"owner": "cal", "note": "blocked"}),
        holds={"owner", "note"},
        values={"owner": "cal", "note": "blocked"},
        sources={"note": "billing"},
        address_from=(),
    ),
    # No field in common at all.
    "nothing-in-common": Case(
        one=Dossier("crm", 800, {"owner": "dee"}),
        other=Dossier("billing", 900, {"note": "new"}),
        holds={"owner", "note"},
        values={"owner": "dee", "note": "new"},
        sources={"owner": "crm", "note": "billing"},
        address_from=(),
    ),
    # A field recorded blank is a field nobody holds, so it reaches no record.
    "a-blank-is-nothing-held": Case(
        one=Dossier("crm", 1000, {"owner": "eve", "note": ""}),
        other=Dossier("billing", 1100, {"owner": "eve"}),
        holds={"owner"},
        values={"owner": "eve"},
        sources={},
        address_from=(),
    ),
}

NAMES = sorted(CASES)

ADDRESS_FIELDS = ("street", "town", "postcode")


def sides(case):
    """The two dossiers keyed by the source name a record would cite."""
    return {case.one.source: case.one, case.other.source: case.other}


@pytest.mark.parametrize("name", NAMES)
def test_the_record_holds_exactly_the_fields_one_of_them_held(name):
    assert dict(merge(CASES[name].one, CASES[name].other)).keys() == CASES[name].holds


@pytest.mark.parametrize("name", NAMES)
def test_every_entry_is_a_value_one_of_them_actually_held(name):
    """Nothing invented, nothing blended: an entry is a value out of one of
    the two records, cited to the record it came out of."""
    case = CASES[name]
    held = sides(case)

    for field, entry in merge(case.one, case.other).items():
        cited, source = entry
        assert source in held
        assert held[source].fields.get(field) == cited


@pytest.mark.parametrize("name", NAMES)
def test_the_rules_that_settle_a_value_settle_it(name):
    """A field only one of them holds, a field they agree on, and a field
    outside the address they disagree on — the last going to the record seen
    later."""
    case = CASES[name]
    record = merge(case.one, case.other)

    for field, expected in case.values.items():
        assert record[field][0] == expected


@pytest.mark.parametrize("name", NAMES)
def test_the_rules_that_settle_a_source_settle_it(name):
    case = CASES[name]
    record = merge(case.one, case.other)

    for field, expected in case.sources.items():
        assert record[field][1] == expected


@pytest.mark.parametrize(
    "name", [name for name in NAMES if CASES[name].address_from]
)
def test_a_disputed_address_is_taken_from_one_record_entire(name):
    """The rule a record merged field by field breaks: where the two disagree
    anywhere in the address, every address field in the result names one and
    the same record, and that record is one that could have supplied the whole
    address."""
    case = CASES[name]
    record = merge(case.one, case.other)
    entries = [record[field] for field in ADDRESS_FIELDS if field in record]

    cited = {source for _, source in entries}

    assert len(cited) == 1
    [source] = cited
    assert source in case.address_from
    for field in ADDRESS_FIELDS:
        if field in record:
            assert record[field][0] == sides(case)[source].fields[field]


@pytest.mark.parametrize("name", NAMES)
def test_merging_is_the_same_either_way_round(name):
    case = CASES[name]

    assert dict(merge(case.other, case.one)) == dict(merge(case.one, case.other))


@pytest.mark.parametrize("name", NAMES)
def test_the_records_the_caller_passed_in_are_left_alone(name):
    case = CASES[name]
    one = Dossier(case.one.source, case.one.seen, dict(case.one.fields))
    other = Dossier(case.other.source, case.other.seen, dict(case.other.fields))

    merge(one, other)

    assert (one, other) == (case.one, case.other)


def test_an_address_neither_of_them_holds_the_whole_of_is_refused():
    """crm has no postcode, billing has no street, and they disagree about
    the town — so there is no record the address could be taken from without
    throwing away what the other one knew."""
    crm = Dossier("crm", 1200, {"street": "9 Mill Lane", "town": "Wick"})
    billing = Dossier("billing", 1300, {"town": "Bray", "postcode": "AB9 9ZZ"})

    with pytest.raises(ValueError):
        merge(crm, billing)


def test_an_incomplete_address_the_two_agree_on_is_not_refused():
    """The refusal is about a dispute, not about a gap: two records that
    agree everywhere they overlap merge into what the two of them know."""
    crm = Dossier("crm", 1400, {"street": "9 Mill Lane", "town": "Wick"})
    billing = Dossier("billing", 1500, {"town": "Wick", "postcode": "AB9 9ZZ"})

    record = merge(crm, billing)

    assert {field: cited for field, (cited, _) in record.items()} == {
        "street": "9 Mill Lane",
        "town": "Wick",
        "postcode": "AB9 9ZZ",
    }


def test_two_records_seen_at_the_same_moment_are_refused():
    crm = Dossier("crm", 1600, {"owner": "fay", "note": "vip"})
    billing = Dossier("billing", 1600, {"owner": "fay", "note": "blocked"})

    with pytest.raises(ValueError):
        merge(crm, billing)
