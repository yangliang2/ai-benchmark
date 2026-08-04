import pytest

from measures import convert_length, convert_weight


def test_lengths_convert_between_units():
    assert convert_length(3, "ft", "in") == pytest.approx(36.0)
    assert convert_length(5, "cm", "cm") == pytest.approx(5.0)


def test_weights_convert_between_units():
    assert convert_weight(2, "lb", "oz") == pytest.approx(32.0)


def test_unknown_units_are_rejected_by_family():
    with pytest.raises(ValueError, match="unknown length unit: mi"):
        convert_length(1, "mi", "cm")
    with pytest.raises(ValueError, match="unknown weight unit: kg"):
        convert_weight(1, "g", "kg")
