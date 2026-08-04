"""Structural half of the grading suite: asserts the dependency really
inverted. Fails on the pristine repo, where analysis loads files itself."""

import ast
import inspect
from pathlib import Path

import analysis


def test_analysis_no_longer_imports_storage():
    # Import statements are what couple the modules; prose in a docstring
    # mentioning storage is not a dependency.
    source = Path(inspect.getsourcefile(analysis)).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])

    assert "storage" not in imported


def test_summarise_works_on_in_memory_entries():
    entries = [("rent", 100000), ("coffee", 450), ("books", 2300)]

    assert analysis.summarise(entries) == {
        "count": 3, "total": 102750, "biggest": "rent",
    }


def test_over_budget_works_on_in_memory_entries():
    entries = [("rent", 100000), ("coffee", 450), ("books", 2300)]

    assert analysis.over_budget(entries, 1000) == ["rent", "books"]
