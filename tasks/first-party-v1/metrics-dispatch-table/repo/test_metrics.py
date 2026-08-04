import pytest

from metrics import format_metric, metric_row


def test_counts_get_thousands_separators():
    assert format_metric("count", 1234567) == "1,234,567"


def test_durations_render_as_minutes_and_seconds():
    assert format_metric("duration", 125) == "2m05s"


def test_sizes_scale_their_unit():
    assert format_metric("size", 512) == "512B"
    assert format_metric("size", 2048) == "2.0KiB"


def test_unknown_kinds_are_rejected():
    with pytest.raises(KeyError, match="unknown metric kind: watts"):
        format_metric("watts", 1)


def test_rows_align_the_name():
    assert metric_row("requests", "count", 1234) == "requests    1,234"
