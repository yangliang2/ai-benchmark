"""Structural half of the grading suite: asserts format_metric genuinely
dispatches through a table. Fails on the pristine repo, where FORMATTERS
does not exist."""

import inspect

from metrics import FORMATTERS, format_metric


def test_every_kind_has_its_own_formatter():
    assert set(FORMATTERS) == {"count", "percent", "duration", "size"}
    assert all(callable(formatter) for formatter in FORMATTERS.values())
    assert FORMATTERS["percent"](0.5) == "50.0%"


def test_format_metric_dispatches_through_the_table(monkeypatch):
    # Only true dispatch picks up an entry added at runtime; a decorative
    # table in front of the old chain does not.
    monkeypatch.setitem(FORMATTERS, "stars", lambda value: "*" * value)

    assert format_metric("stars", 3) == "***"


def test_the_chain_is_gone():
    assert "elif" not in inspect.getsource(format_metric)
