import pytest
from gauge import (
    BASE_UNITS,
    UNITS,
    convert,
    dimension_of,
    factor_of,
    normalized,
    same_dimension,
)


def test_the_base_units_are_worth_one_of_themselves():
    for unit in BASE_UNITS:
        assert factor_of(unit) == 1.0
        assert dimension_of(unit) == {unit: 1}


def test_every_unit_is_described_in_base_units_only():
    for unit, (_factor, dimension) in UNITS.items():
        assert set(dimension) <= set(BASE_UNITS), unit


def test_a_derived_unit_carries_the_dimension_it_is_made_of():
    assert dimension_of("N") == {"kg": 1, "m": 1, "s": -2}
    assert dimension_of("Hz") == {"s": -1}


def test_dimension_of_hands_back_a_copy():
    dimension = dimension_of("m")
    dimension["m"] = 99

    assert dimension_of("m") == {"m": 1}


def test_the_unit_of_nothing_at_all():
    assert dimension_of("one") == {}
    assert factor_of("one") == 1.0
    assert convert(3, "one", "one") == 3.0


def test_normalized_drops_the_zeroes():
    assert normalized({"m": 1, "s": 0}) == {"m": 1}
    assert normalized({"m": 0}) == {}


def test_same_dimension_ignores_a_zero_written_out():
    assert same_dimension({"m": 1}, {"m": 1, "s": 0})
    assert not same_dimension({"m": 1}, {"s": 1})


def test_converting_within_a_kind():
    assert convert(1, "km", "m") == 1000.0
    assert convert(1500, "m", "km") == 1.5
    assert convert(1, "h", "min") == 60.0
    assert convert(2, "t", "kg") == 2000.0


def test_converting_a_unit_to_itself_changes_nothing():
    assert convert(3.25, "N", "N") == 3.25


def test_converting_across_kinds_is_refused():
    with pytest.raises(ValueError):
        convert(1, "km", "s")


def test_a_unit_the_module_does_not_know():
    with pytest.raises(ValueError):
        factor_of("furlong")
    with pytest.raises(ValueError):
        convert(1, "m", "furlong")
