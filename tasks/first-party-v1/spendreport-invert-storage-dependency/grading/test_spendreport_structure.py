"""Structural half of the grading suite: asserts the dependency really
inverted. Fails on the pristine repo, where analysis loads files itself."""

import inspect
from pathlib import Path

import analysis


def test_analysis_no_longer_references_storage():
    source = Path(inspect.getsourcefile(analysis)).read_text()

    assert "storage" not in source


def test_summarise_works_on_in_memory_entries():
    entries = [("rent", 100000), ("coffee", 450), ("books", 2300)]

    assert analysis.summarise(entries) == {
        "count": 3, "total": 102750, "biggest": "rent",
    }


def test_over_budget_works_on_in_memory_entries():
    entries = [("rent", 100000), ("coffee", 450), ("books", 2300)]

    assert analysis.over_budget(entries, 1000) == ["rent", "books"]
