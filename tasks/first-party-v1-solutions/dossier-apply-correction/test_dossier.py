import pytest
from dossier import ADDRESS, FIELDS, Dossier, describe, disagree, known, value

CRM = Dossier(
    "crm",
    300,
    {"owner": "ana", "street": "12 Kiln Row", "town": "Wick", "postcode": "AB1 2CD"},
)
BILLING = Dossier(
    "billing",
    200,
    {"owner": "ana", "note": "pays late", "street": "4 Quay Road", "town": "Wick"},
)


def test_the_address_fields_are_fields():
    assert set(ADDRESS) <= set(FIELDS)


def test_a_field_a_dossier_holds():
    assert value(CRM, "town") == "Wick"


def test_a_field_a_dossier_never_recorded_is_not_held():
    assert value(CRM, "note") is None


def test_a_field_recorded_blank_is_not_held_either():
    assert value(Dossier("crm", 1, {"note": ""}), "note") is None


def test_a_field_no_dossier_has_is_refused():
    with pytest.raises(ValueError):
        value(CRM, "shoesize")


def test_what_a_dossier_knows_comes_back_in_the_declared_order():
    assert known(BILLING) == ["owner", "note", "street", "town"]


def test_two_dossiers_disagree_only_where_both_hold_something():
    assert disagree(CRM, BILLING) == ["street"]


def test_disagreement_can_be_asked_about_part_of_a_record():
    assert disagree(CRM, BILLING, ADDRESS) == ["street"]


def test_a_field_only_one_of_them_holds_is_not_a_disagreement():
    assert "postcode" not in disagree(CRM, BILLING)


def test_the_description_has_a_line_per_field_held():
    assert describe(CRM) == [
        "owner: ana",
        "street: 12 Kiln Row",
        "town: Wick",
        "postcode: AB1 2CD",
    ]
