import pytest
from stockroom import move, place, relabel, remove


def test_placing_puts_an_item_on_its_shelf():
    assert place({"a1": ["hammer"]}, "saw", "a1") == {"a1": ["hammer", "saw"]}


def test_placing_opens_a_shelf_that_was_not_there():
    assert place({"a1": []}, "saw", "b2") == {"a1": [], "b2": ["saw"]}


def test_removing_takes_an_item_off_its_shelf():
    assert remove({"a1": ["hammer", "saw"]}, "saw", "a1") == {"a1": ["hammer"]}


def test_removing_what_is_not_there_is_refused():
    with pytest.raises(KeyError, match="saw is not on a1"):
        remove({"a1": ["hammer"]}, "saw", "a1")


def test_relabelling_renames_a_shelf():
    assert relabel({"a1": ["hammer"]}, "a1", "b2") == {"b2": ["hammer"]}


def test_relabelling_a_shelf_that_is_not_there_is_refused():
    with pytest.raises(KeyError, match="no shelf called c3"):
        relabel({"a1": []}, "c3", "b2")


def test_moving_carries_an_item_across():
    assert move({"a1": ["hammer"], "b2": []}, "hammer", "a1", "b2") == {
        "a1": [],
        "b2": ["hammer"],
    }
