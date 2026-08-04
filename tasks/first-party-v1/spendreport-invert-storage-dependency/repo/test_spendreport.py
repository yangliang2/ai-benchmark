import pytest

from cli import report
from storage import load_entries


def test_load_entries_parses_names_and_cents(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\n\ncoffee,450\nrefund,-500\n")

    assert load_entries(expenses) == [
        ("rent", 100000), ("coffee", 450), ("refund", -500),
    ]


def test_load_entries_rejects_malformed_lines(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\noops\n")

    with pytest.raises(ValueError, match="line 2"):
        load_entries(expenses)


def test_report_lists_stats_then_overruns(tmp_path):
    expenses = tmp_path / "expenses.txt"
    expenses.write_text("rent,100000\ncoffee,450\nbooks,2300\n")

    assert report(expenses, 1000) == (
        "entries: 3\ntotal: 102750\nbiggest: rent\n"
        "over budget: rent\nover budget: books"
    )
