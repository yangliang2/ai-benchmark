"""Behaviour half of the grading suite: must pass before and after the copy is
pulled into a module of its own, so it pins what the four functions return,
what they raise, and what they leave the caller holding."""

import pytest
from stockroom import move, place, relabel, remove


def test_placing_puts_an_item_on_its_shelf():
    assert place({"a1": ["hammer"]}, "saw", "a1") == {"a1": ["hammer", "saw"]}
    assert place({"a1": []}, "saw", "b2") == {"a1": [], "b2": ["saw"]}


def test_removing_takes_an_item_off_its_shelf():
    assert remove({"a1": ["hammer", "saw"]}, "saw", "a1") == {"a1": ["hammer"]}
    with pytest.raises(KeyError, match="saw is not on a1"):
        remove({"a1": ["hammer"]}, "saw", "a1")
    with pytest.raises(KeyError, match="saw is not on c3"):
        remove({"a1": ["saw"]}, "saw", "c3")


def test_relabelling_renames_a_shelf_and_keeps_what_is_on_it():
    assert relabel({"a1": ["hammer"], "b2": []}, "a1", "c3") == {
        "c3": ["hammer"],
        "b2": [],
    }
    with pytest.raises(KeyError, match="no shelf called c3"):
        relabel({"a1": []}, "c3", "b2")


def test_moving_carries_an_item_across():
    assert move({"a1": ["hammer"], "b2": []}, "hammer", "a1", "b2") == {
        "a1": [],
        "b2": ["hammer"],
    }


def test_the_shelving_a_caller_passed_in_is_still_what_it_was():
    """Every one of these answers with the shelving that results, and the
    caller keeps holding the shelving it had — down to the lists on the
    shelves, which is where a copy stops short."""
    shelves = {"a1": ["hammer"], "b2": ["saw"]}

    place(shelves, "chisel", "a1")
    remove(shelves, "saw", "b2")
    relabel(shelves, "a1", "c3")
    move(shelves, "hammer", "a1", "b2")

    assert shelves == {"a1": ["hammer"], "b2": ["saw"]}


def test_two_places_on_one_shelving_do_not_see_each_other():
    shelves = {"a1": []}

    first = place(shelves, "hammer", "a1")
    second = place(shelves, "saw", "a1")

    assert first == {"a1": ["hammer"]}
    assert second == {"a1": ["saw"]}
