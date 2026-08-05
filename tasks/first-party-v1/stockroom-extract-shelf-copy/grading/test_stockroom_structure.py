"""Structural half of the grading suite: asserts the copy has one home, in a
module of its own, that all three callers go through. Fails on the pristine
repo, where shelving.py does not exist."""

import inspect

import stockroom
from shelving import copied
from stockroom import place, relabel, remove


def test_copied_answers_with_a_copy():
    shelves = {"a1": ["hammer"]}

    assert copied(shelves) == shelves
    assert copied(shelves) is not shelves


def test_all_three_callers_copy_through_it(monkeypatch):
    # Only a real seam picks up a copy replaced at runtime; a helper alongside
    # three inline copies does not.
    monkeypatch.setattr(
        "stockroom.copied",
        lambda shelves: {name: list(items) for name, items in shelves.items()}
        | {"loading-bay": []},
    )

    assert "loading-bay" in place({"a1": []}, "saw", "a1")
    assert "loading-bay" in remove({"a1": ["saw"]}, "saw", "a1")
    assert "loading-bay" in relabel({"a1": []}, "a1", "b2")


def test_stockroom_no_longer_builds_a_copy_of_its_own():
    for function in (place, remove, relabel):
        source = inspect.getsource(function)
        assert "copied(" in source
        assert "dict(shelves)" not in source
        assert "shelves.items()" not in source


def test_the_copy_lives_in_shelving_rather_than_in_stockroom():
    assert inspect.getmodule(copied).__name__ == "shelving"
    assert "def copied" not in inspect.getsource(stockroom)
