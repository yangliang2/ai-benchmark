"""Structural half of the grading suite: asserts the restructuring actually
happened. Fails on the pristine repo, where formatting.py does not exist."""

import inspect
from pathlib import Path

import formatting
import ledger


def test_formatting_module_owns_the_money_helpers():
    assert formatting.format_amount(-1250) == "-$12.50"
    assert formatting.format_amount(0) == "$0.00"
    assert formatting.format_line("rent", 100000) == "rent: $1000.00"


def test_ledger_module_no_longer_defines_them():
    source = Path(inspect.getsourcefile(ledger)).read_text()

    assert "def format_amount" not in source
    assert "def format_line" not in source
