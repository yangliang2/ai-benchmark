"""Structural half of the grading suite: asserts the duplication is really
gone. Fails on the pristine repo, where parse_stamp does not exist."""

import inspect
from datetime import datetime

import logparse
from logparse import parse_stamp


def test_parse_stamp_returns_the_moment_and_the_rest():
    moment, rest = parse_stamp("2026-08-04 12:30:05 INFO cache warmed")

    assert moment == datetime(2026, 8, 4, 12, 30, 5)  # noqa: DTZ001
    assert rest == "INFO cache warmed"


def test_the_format_string_appears_exactly_once():
    # Extracting the helper without deleting the three inline copies would
    # leave the format string four times over; deduplication leaves one.
    assert inspect.getsource(logparse).count("%Y-%m-%d %H:%M:%S") == 1


def test_every_reader_goes_through_the_helper():
    for reader in (
        logparse.entry_level,
        logparse.entry_message,
        logparse.entries_between,
    ):
        assert "parse_stamp(" in inspect.getsource(reader)
