"""Behaviour half of the grading suite: must pass before and after the
dispatch-table rewrite, so it pins rendered strings and errors only."""

import pytest
from metrics import format_metric, metric_row


def test_counts_get_thousands_separators():
    assert format_metric("count", 1234567) == "1,234,567"
    assert format_metric("count", 12) == "12"


def test_percentages_render_one_decimal_of_the_ratio():
    assert format_metric("percent", 0.5) == "50.0%"
    assert format_metric("percent", 0.1234) == "12.3%"


def test_durations_truncate_to_whole_seconds():
    assert format_metric("duration", 125) == "2m05s"
    assert format_metric("duration", 125.9) == "2m05s"  # truncated, not rounded
    assert format_metric("duration", 59) == "0m59s"


def test_sizes_scale_their_unit():
    assert format_metric("size", 512) == "512B"
    assert format_metric("size", 1024) == "1.0KiB"
    assert format_metric("size", 1536) == "1.5KiB"
    assert format_metric("size", 1048576) == "1.0MiB"


def test_unknown_kinds_keep_their_exact_message():
    with pytest.raises(KeyError, match="unknown metric kind: watts"):
        format_metric("watts", 1)


def test_rows_align_the_name():
    assert metric_row("requests", "count", 1234) == "requests    1,234"
    assert metric_row("p99", "duration", 61) == "p99         1m01s"
