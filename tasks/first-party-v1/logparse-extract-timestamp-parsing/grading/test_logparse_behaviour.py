"""Behaviour half of the grading suite: must pass before and after the
extraction, so it touches only the three readers."""

from datetime import datetime

import pytest
from logparse import entries_between, entry_level, entry_message


def test_entry_level_reads_the_level_token():
    assert entry_level("2026-08-04 12:30:05 INFO cache warmed") == "INFO"


def test_entry_message_keeps_internal_spacing_verbatim():
    # The rest of the line starts one character after the stamp, untouched:
    # no stripping that would collapse the double spaces.
    assert entry_message("2026-08-04 12:30:05 WARN disk  almost  full") == (
        "disk  almost  full"
    )


def test_entries_between_is_inclusive_at_both_ends():
    lines = [
        "2026-08-04 08:59:59 INFO too early",
        "2026-08-04 09:00:00 INFO started",
        "2026-08-04 12:00:00 WARN slow",
        "2026-08-04 12:00:01 INFO too late",
    ]

    kept = entries_between(
        lines, datetime(2026, 8, 4, 9, 0, 0), datetime(2026, 8, 4, 12, 0, 0)  # noqa: DTZ001
    )

    assert kept == ["INFO started", "WARN slow"]


def test_a_malformed_stamp_raises_value_error():
    with pytest.raises(ValueError):
        entry_level("yesterday-ish 12:30:05 INFO nope")
    with pytest.raises(ValueError):
        entries_between(["not a stamp at all INFO x"], datetime(2026, 1, 1),  # noqa: DTZ001
                        datetime(2026, 12, 31))  # noqa: DTZ001
