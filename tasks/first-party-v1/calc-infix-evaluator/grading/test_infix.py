import pytest
from calc import evaluate, evaluate_rpn


def test_multiplication_binds_tighter_than_addition():
    assert evaluate("2+3*4") == 14.0


def test_parentheses_override_precedence():
    assert evaluate("(2+3)*4") == 20.0


def test_subtraction_is_left_associative():
    assert evaluate("2-3-4") == -5.0


def test_division_is_left_associative():
    assert evaluate("8/4/2") == 1.0


def test_unary_minus_on_a_number():
    assert evaluate("-3+5") == 2.0


def test_unary_minus_after_an_operator():
    assert evaluate("2*-3") == -6.0


def test_unary_minus_on_a_parenthesised_group():
    assert evaluate("-(2+3)") == -5.0


def test_decimal_numbers():
    assert evaluate("1.5*2") == 3.0


def test_division_is_true_division():
    assert evaluate("10/4") == 2.5


def test_whitespace_between_tokens_is_allowed():
    assert evaluate("  1 +  2*3 ") == 7.0


@pytest.mark.parametrize(
    "bad", ["", "(1+2", "1+2)", "1++2", "1 2", "2*", "$", "1.2.3"]
)
def test_malformed_expressions_raise_value_error(bad):
    with pytest.raises(ValueError):
        evaluate(bad)


def test_existing_rpn_evaluator_is_unchanged():
    assert evaluate_rpn(["2", "3", "+", "4", "*"]) == 20.0
