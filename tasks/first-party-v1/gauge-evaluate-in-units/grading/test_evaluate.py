"""Held-out tests for `gauge.evaluate`.

Self-contained on purpose: grading runs with conftest loading disabled and its
pytest config pinned outside the workdir, so nothing here may lean on a
fixture file.

The suite is wide because the contract is: this is a headroom anchor, and what
it measures is whether an answer gets *every* clause of a spec that states
them all. Each test names one clause of the brief.
"""

import gauge
import pytest


def evaluate(expression, unit):
    """Looked up when a test runs rather than at import time, so a module
    that does not have it yet fails every test on its own terms instead of
    failing collection."""
    return gauge.evaluate(expression, unit)


def close(got, wanted):
    return abs(got - wanted) < 1e-9 * max(1.0, abs(wanted))


# --- quantities and the answer's shape -----------------------------------------


def test_a_single_quantity_in_its_own_unit():
    assert close(evaluate("3 m", "m"), 3.0)


def test_a_single_quantity_in_another_unit_of_the_same_kind():
    assert close(evaluate("3 km", "m"), 3000.0)
    assert close(evaluate("1500 m", "km"), 1.5)


def test_the_answer_is_a_float():
    assert isinstance(evaluate("3 m", "m"), float)
    assert isinstance(evaluate("2", "one"), float)


def test_a_number_may_carry_a_point():
    assert close(evaluate("1.5 kg", "g"), 1500.0)


def test_a_number_standing_on_its_own_is_of_nothing_at_all():
    assert close(evaluate("7", "one"), 7.0)


def test_whitespace_between_a_number_and_its_unit_is_optional():
    assert close(evaluate("3m", "m"), 3.0)
    assert close(evaluate("2km+300m", "m"), 2300.0)


# --- adding and subtracting ----------------------------------------------------


def test_adding_two_quantities_of_the_same_kind_in_different_units():
    assert close(evaluate("2 km + 300 m", "km"), 2.3)
    assert close(evaluate("2 km + 300 m", "m"), 2300.0)


def test_subtracting():
    assert close(evaluate("1 h - 20 min", "min"), 40.0)


def test_adding_and_subtracting_group_leftwards():
    assert close(evaluate("10 m - 2 m - 3 m", "m"), 5.0)


def test_adding_across_two_kinds_is_refused():
    with pytest.raises(ValueError):
        evaluate("2 km + 300 s", "km")


def test_adding_a_plain_number_to_a_measurement_is_refused():
    with pytest.raises(ValueError):
        evaluate("2 m + 3", "m")


# --- multiplying and dividing, and what that does to the kind ------------------


def test_multiplying_a_measurement_by_a_plain_number():
    assert close(evaluate("3 m * 4", "m"), 12.0)
    assert close(evaluate("4 * 3 m", "m"), 12.0)


def test_metres_times_metres_is_square_metres():
    with pytest.raises(ValueError):
        evaluate("2 m * 3 m", "m")


def test_metres_over_metres_is_nothing_at_all():
    assert close(evaluate("1 km / 1 m", "one"), 1000.0)
    assert close(evaluate("500 m / 1 km", "one"), 0.5)


def test_a_kind_built_out_of_three_base_units():
    assert close(evaluate("1 kg * 1 m / (1 s * 1 s)", "N"), 1.0)
    assert close(evaluate("2 kg * 3 m / (1 s * 1 s)", "N"), 6.0)


def test_a_derived_unit_may_be_written_into_the_expression_too():
    assert close(evaluate("1 J / 1 s", "W"), 1.0)
    assert close(evaluate("1 N * 1 m", "J"), 1.0)


def test_one_over_a_time_is_a_frequency():
    assert close(evaluate("1 / 1 s", "Hz"), 1.0)
    assert close(evaluate("60 / 1 min", "Hz"), 1.0)


def test_dividing_groups_leftwards():
    assert close(evaluate("8 / 4 / 2", "one"), 1.0)


def test_multiplying_and_dividing_bind_tighter_than_adding():
    assert close(evaluate("1 m + 2 m * 3", "m"), 7.0)
    assert close(evaluate("10 m - 6 m / 2", "m"), 7.0)


def test_the_arithmetic_happens_in_base_units():
    """A kilometre is a thousand metres and a millimetre is a thousandth, so
    an implementation carrying the written unit through gets this wrong by a
    factor of a million."""
    assert close(evaluate("1 km / 1 mm", "one"), 1000000.0)
    assert close(evaluate("1 h / 1 ms", "one"), 3600000.0)
    assert close(evaluate("1 t / 1 g", "one"), 1000000.0)


def test_dividing_by_nothing_is_refused():
    with pytest.raises(ValueError):
        evaluate("1 m / 0", "m")
    with pytest.raises(ValueError):
        evaluate("1 m / 0 s", "Hz")


# --- powers --------------------------------------------------------------------


def test_a_power_applies_to_the_number_and_its_unit_together():
    assert close(evaluate("2 m ^ 3 / (1 m * 1 m)", "m"), 8.0)


def test_a_power_of_zero_leaves_nothing_at_all():
    assert close(evaluate("2 m ^ 0", "one"), 1.0)


def test_a_negative_power_turns_the_kind_upside_down():
    assert close(evaluate("2 s ^ -1", "Hz"), 0.5)
    assert close(evaluate("1 m * 1 m ^ -1", "one"), 1.0)
    assert close(evaluate("4 m ^ -2 * 1 m * 1 m", "one"), 0.0625)


def test_a_power_binds_tighter_than_a_leading_minus():
    assert close(evaluate("-2 ^ 2", "one"), -4.0)


def test_a_leading_minus_negates():
    assert close(evaluate("-3 m + 5 m", "m"), 2.0)
    assert close(evaluate("5 m * -2", "m"), -10.0)


def test_a_power_of_a_bracketed_expression():
    assert close(evaluate("(1 m + 1 m) ^ 2 / 1 m", "m"), 4.0)


def test_a_power_that_is_not_a_whole_number_is_refused():
    with pytest.raises(ValueError):
        evaluate("2 m ^ 1.5", "m")


def test_a_power_with_a_unit_on_it_is_refused():
    with pytest.raises(ValueError):
        evaluate("2 m ^ 2 m", "m")


def test_a_negative_power_of_nothing_is_refused():
    with pytest.raises(ValueError):
        evaluate("0 s ^ -1", "Hz")


def test_a_power_is_written_once():
    with pytest.raises(ValueError):
        evaluate("2 ^ 3 ^ 2", "one")


# --- brackets ------------------------------------------------------------------


def test_brackets_group():
    assert close(evaluate("(1 m + 2 m) * 3", "m"), 9.0)
    assert close(evaluate("1 m + 2 m * 3", "m"), 7.0)


def test_brackets_may_be_nested():
    assert close(evaluate("((1 m + 1 m) * (2 + 1))", "m"), 6.0)


def test_an_unclosed_bracket_is_refused():
    with pytest.raises(ValueError):
        evaluate("(1 m + 2 m", "m")


def test_a_bracket_that_was_never_opened_is_refused():
    with pytest.raises(ValueError):
        evaluate("1 m + 2 m)", "m")


# --- the kind the answer has to be ---------------------------------------------


def test_an_answer_of_the_wrong_kind_is_refused():
    with pytest.raises(ValueError):
        evaluate("3 m", "s")
    with pytest.raises(ValueError):
        evaluate("2 m * 3 m", "one")


def test_a_plain_number_asked_for_in_a_real_unit_is_refused():
    with pytest.raises(ValueError):
        evaluate("7", "m")


def test_a_unit_the_module_does_not_know_is_refused():
    with pytest.raises(ValueError):
        evaluate("3 furlong", "m")
    with pytest.raises(ValueError):
        evaluate("3 m", "furlong")


# --- not parsing ---------------------------------------------------------------


def test_nothing_at_all_is_refused():
    with pytest.raises(ValueError):
        evaluate("", "m")
    with pytest.raises(ValueError):
        evaluate("   ", "m")


def test_a_missing_number_is_refused():
    with pytest.raises(ValueError):
        evaluate("1 m +", "m")
    with pytest.raises(ValueError):
        evaluate("* 2", "one")


def test_a_number_with_nothing_after_its_point_is_refused():
    with pytest.raises(ValueError):
        evaluate("1. m", "m")


def test_a_character_belonging_to_no_token_is_refused():
    with pytest.raises(ValueError):
        evaluate("1 m # 2", "m")


def test_something_trailing_after_the_expression_ends_is_refused():
    with pytest.raises(ValueError):
        evaluate("1 m 2 m", "m")


def test_a_unit_standing_on_its_own_is_refused():
    with pytest.raises(ValueError):
        evaluate("m", "m")


# --- the module's own behaviour, unchanged -------------------------------------


def test_the_existing_helpers_still_answer_as_they_did():
    assert gauge.convert(1, "km", "m") == 1000.0
    assert gauge.dimension_of("N") == {"kg": 1, "m": 1, "s": -2}
    assert gauge.factor_of("h") == 3600.0
    assert gauge.same_dimension({"m": 1}, {"m": 1, "s": 0})
