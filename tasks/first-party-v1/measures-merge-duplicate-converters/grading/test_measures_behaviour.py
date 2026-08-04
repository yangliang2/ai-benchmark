"""Behaviour half of the grading suite: must pass before and after the merge,
so it goes through measures.py alone — never the implementation modules."""

import pytest
from measures import convert_length, convert_weight


def test_lengths_convert_between_units():
    assert convert_length(3, "ft", "in") == pytest.approx(36.0)
    assert convert_length(100, "in", "yd") == pytest.approx(100 * 2.54 / 91.44)
    assert convert_length(5, "cm", "cm") == pytest.approx(5.0)


def test_weights_convert_between_units():
    assert convert_weight(2, "lb", "oz") == pytest.approx(32.0)
    assert convert_weight(70.875, "g", "oz") == pytest.approx(2.5)


def test_unknown_length_units_keep_their_exact_message():
    with pytest.raises(ValueError, match="unknown length unit: mi"):
        convert_length(1, "mi", "cm")
    with pytest.raises(ValueError, match="unknown length unit: mm"):
        convert_length(1, "cm", "mm")


def test_unknown_weight_units_keep_their_exact_message():
    with pytest.raises(ValueError, match="unknown weight unit: kg"):
        convert_weight(1, "g", "kg")
    with pytest.raises(ValueError, match="unknown weight unit: stone"):
        convert_weight(1, "stone", "g")
