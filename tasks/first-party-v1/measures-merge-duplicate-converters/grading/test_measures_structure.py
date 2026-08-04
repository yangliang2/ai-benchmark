"""Structural half of the grading suite: asserts the duplicates are gone and
one table-driven implementation replaced them. Fails on the pristine repo,
where conversion.py does not exist."""

import importlib.util
import inspect

import conversion
import measures
import pytest


def test_the_duplicate_modules_are_gone():
    # Keeping lengths.py or weights.py around — even as re-export shims —
    # is not a merge.
    assert importlib.util.find_spec("lengths") is None
    assert importlib.util.find_spec("weights") is None


def test_one_generic_table_driven_convert():
    doubles = {"one": 1.0, "two": 2.0}

    assert conversion.convert(3, "two", "one", doubles, "doubling") == (
        pytest.approx(6.0)
    )
    with pytest.raises(ValueError, match="unknown doubling unit: seven"):
        conversion.convert(1, "seven", "one", doubles, "doubling")


def test_conversion_owns_both_tables():
    assert conversion.LENGTH_FACTORS == {
        "in": 2.54, "ft": 30.48, "yd": 91.44, "cm": 1.0,
    }
    assert conversion.WEIGHT_FACTORS == {"oz": 28.35, "lb": 453.6, "g": 1.0}


def test_measures_no_longer_carries_factors():
    source = inspect.getsource(measures)

    assert "2.54" not in source
    assert "453.6" not in source
