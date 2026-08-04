import pytest
from calc import evaluate_rpn


def test_evaluates_operators_over_a_stack():
    assert evaluate_rpn(["2", "3", "+", "4", "*"]) == 20.0


def test_division_uses_the_two_topmost_operands_in_order():
    assert evaluate_rpn(["8", "4", "/"]) == 2.0


def test_a_lone_number_is_itself():
    assert evaluate_rpn(["1.5"]) == 1.5


def test_missing_operands_raise():
    with pytest.raises(ValueError):
        evaluate_rpn(["2", "+"])


def test_leftover_operands_raise():
    with pytest.raises(ValueError):
        evaluate_rpn(["1", "2"])
