from datetime import datetime

from logparse import entries_between, entry_level, entry_message


def test_entry_level_reads_the_level_token():
    assert entry_level("2026-08-04 12:30:05 INFO cache warmed") == "INFO"


def test_entry_message_keeps_the_message_verbatim():
    assert entry_message("2026-08-04 12:30:05 WARN disk  almost  full") == (
        "disk  almost  full"
    )


def test_entries_between_keeps_lines_inside_the_window():
    lines = [
        "2026-08-04 09:00:00 INFO started",
        "2026-08-04 12:00:00 WARN slow",
        "2026-08-04 18:00:00 INFO stopped",
    ]

    kept = entries_between(
        lines, datetime(2026, 8, 4, 9, 0, 0), datetime(2026, 8, 4, 12, 0, 0)  # noqa: DTZ001
    )

    assert kept == ["INFO started", "WARN slow"]
