"""How `apply_correction` is graded: against the records the prompt spells out.

Every decision is stated — what a blank correction means, what becomes of a
blank already held, what counts as a change worth listing, which mistakes are
refused — so the expected dossiers and change lists are written out here in
full. This is the zero-crux control the merging task is read against.
"""

import pytest
from dossier import Dossier, apply_correction

BASE = Dossier("crm", 300, {"owner": "ana", "note": "pays late", "town": "Wick"})


def test_a_field_the_dossier_did_not_hold_is_recorded():
    corrected, changes = apply_correction(BASE, {"street": "9 Mill Lane"}, 400)

    assert corrected == Dossier(
        "crm",
        400,
        {
            "owner": "ana",
            "note": "pays late",
            "town": "Wick",
            "street": "9 Mill Lane",
        },
    )
    assert list(changes) == [("street", None, "9 Mill Lane")]


def test_a_field_the_dossier_held_is_rewritten():
    corrected, changes = apply_correction(BASE, {"town": "Bray"}, 400)

    assert corrected.fields == {"owner": "ana", "note": "pays late", "town": "Bray"}
    assert list(changes) == [("town", "Wick", "Bray")]


@pytest.mark.parametrize("blank", ["", None])
def test_a_blank_correction_forgets_the_field_rather_than_recording_it(blank):
    corrected, changes = apply_correction(BASE, {"note": blank}, 400)

    assert corrected.fields == {"owner": "ana", "town": "Wick"}
    assert list(changes) == [("note", "pays late", None)]


def test_forgetting_a_field_that_was_never_held_changes_nothing():
    corrected, changes = apply_correction(BASE, {"street": ""}, 400)

    assert corrected.fields == {"owner": "ana", "note": "pays late", "town": "Wick"}
    assert list(changes) == []


def test_a_blank_already_sitting_in_the_dossier_is_not_carried_over():
    stale = Dossier("crm", 300, {"owner": "ana", "note": ""})

    corrected, changes = apply_correction(stale, {"town": "Wick"}, 400)

    assert corrected.fields == {"owner": "ana", "town": "Wick"}
    assert list(changes) == [("town", None, "Wick")]


def test_recording_what_was_already_held_is_no_change():
    corrected, changes = apply_correction(BASE, {"town": "Wick"}, 400)

    assert corrected.fields == {"owner": "ana", "note": "pays late", "town": "Wick"}
    assert list(changes) == []


def test_no_corrections_at_all_moves_only_the_time():
    corrected, changes = apply_correction(BASE, {}, 400)

    assert corrected == Dossier("crm", 400, dict(BASE.fields))
    assert list(changes) == []


def test_several_changes_are_listed_in_the_order_the_fields_are_declared():
    corrected, changes = apply_correction(
        BASE, {"street": "9 Mill Lane", "note": "", "owner": "ben"}, 400
    )

    assert corrected.fields == {"owner": "ben", "town": "Wick", "street": "9 Mill Lane"}
    assert list(changes) == [
        ("owner", "ana", "ben"),
        ("note", "pays late", None),
        ("street", None, "9 Mill Lane"),
    ]


def test_the_source_is_kept_and_the_time_is_the_one_given():
    corrected, _ = apply_correction(BASE, {"town": "Bray"}, 999)

    assert (corrected.source, corrected.seen) == ("crm", 999)


def test_a_name_that_is_not_a_field_is_refused():
    with pytest.raises(ValueError):
        apply_correction(BASE, {"shoesize": "9"}, 400)


@pytest.mark.parametrize("seen", [300, 299, 0])
def test_a_correction_no_later_than_the_dossier_itself_is_refused(seen):
    with pytest.raises(ValueError):
        apply_correction(BASE, {"town": "Bray"}, seen)


def test_the_dossier_the_caller_passed_in_is_left_alone():
    dossier = Dossier(BASE.source, BASE.seen, dict(BASE.fields))

    apply_correction(dossier, {"note": "", "street": "9 Mill Lane"}, 400)

    assert dossier == BASE
