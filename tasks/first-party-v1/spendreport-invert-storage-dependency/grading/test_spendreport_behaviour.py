"""Behaviour half of the grading suite: must pass before and after the
inversion, so it goes through storage and cli only — analysis's signatures
are exactly what changes."""

import pytest
from cli import report
from storage import load_entries


def test_load_entries_parses_names_and_cents(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\n\ncoffee,450\nrefund,-500\n")

    assert load_entries(expenses) == [
        ("rent", 100000), ("coffee", 450), ("refund", -500),
    ]


def test_load_entries_rejects_malformed_lines_by_number(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\noops\n")

    with pytest.raises(ValueError, match="line 2: expected 'name,cents'"):
        load_entries(expenses)


def test_report_lists_stats_then_overruns_in_file_order(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\ncoffee,450\nbooks,2300\n")

    assert report(expenses, 1000) == (
        "entries: 3\ntotal: 102750\nbiggest: rent\n"
        "over budget: rent\nover budget: books"
    )


def test_report_with_nothing_over_budget(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("tea,300\nbus,250\n")

    assert report(expenses, 1000) == "entries: 2\ntotal: 550\nbiggest: tea"


def test_over_budget_is_strict(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("exact,1000\nover,1001\n")

    assert report(expenses, 1000) == (
        "entries: 2\ntotal: 2001\nbiggest: over\nover budget: over"
    )
