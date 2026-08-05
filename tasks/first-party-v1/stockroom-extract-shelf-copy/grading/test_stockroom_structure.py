"""Structural half of the grading suite: asserts the copy has one home, in a
module of its own, that both callers go through. Fails on the pristine repo,
where shelving.py does not exist."""

import inspect

import shelving
import stockroom
from shelving import copied
from stockroom import place, remove


def reroute(monkeypatch, defining, caller, name, replacement):
    """Point every name that reaches `defining.name` at `replacement`.

    Which names those are is up to the import form the solution chose:
    `import shelving` reaches the function through the defining module's
    attribute, `from shelving import copied` binds a second name in the
    caller, and an `as` clause binds it under a third. Redirecting all of
    them is what keeps the seam assertion a question about the seam rather
    than about how the caller spelled its import.
    """
    original = getattr(defining, name)
    bound_in_caller = [
        attribute for attribute, value in vars(caller).items() if value is original
    ]
    monkeypatch.setattr(defining, name, replacement)
    for attribute in bound_in_caller:
        monkeypatch.setattr(caller, attribute, replacement)


def test_copied_answers_with_a_copy():
    shelves = {"a1": ["hammer"]}

    assert copied(shelves) == shelves
    assert copied(shelves) is not shelves


def test_both_callers_copy_through_it(monkeypatch):
    # Only a real seam picks up a copy replaced at runtime; a helper alongside
    # two inline copies does not.
    reroute(
        monkeypatch,
        shelving,
        stockroom,
        "copied",
        lambda shelves: {name: list(items) for name, items in shelves.items()}
        | {"loading-bay": []},
    )

    assert "loading-bay" in place({"a1": []}, "saw", "a1")
    assert "loading-bay" in remove({"a1": ["saw"]}, "saw", "a1")


def test_stockroom_no_longer_builds_a_copy_of_its_own():
    for function in (place, remove):
        source = inspect.getsource(function)
        assert "dict(shelves)" not in source
        assert "shelves.items()" not in source


def test_the_copy_lives_in_shelving_rather_than_in_stockroom():
    assert inspect.getmodule(copied).__name__ == "shelving"
    assert "def copied" not in inspect.getsource(stockroom)
