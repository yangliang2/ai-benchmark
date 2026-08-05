import pytest
from duration import UNITS, format_duration, unit_seconds


def test_the_units_run_from_largest_to_smallest():
    assert [name for name, _ in UNITS] == ["w", "d", "h", "m", "s"]


def test_unit_seconds_reads_a_unit_whatever_its_case():
    assert unit_seconds("h") == 3600
    assert unit_seconds("H") == 3600


def test_unit_seconds_refuses_a_unit_it_does_not_know():
    with pytest.raises(ValueError):
        unit_seconds("y")


def test_format_writes_the_largest_units_first():
    assert format_duration(5400) == "1h 30m"


def test_format_leaves_out_the_units_that_are_not_needed():
    assert format_duration(86400) == "1d"


def test_nothing_at_all_is_written_as_zero_seconds():
    assert format_duration(0) == "0s"
