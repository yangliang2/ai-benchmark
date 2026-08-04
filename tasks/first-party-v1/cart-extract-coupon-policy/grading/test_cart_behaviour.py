"""Behaviour half of the grading suite: must pass before and after the
extraction, so it touches only Cart's public interface."""

import pytest
from cart import Cart


def test_subtotal_multiplies_quantities():
    cart = Cart()
    cart.add_item("book", 1200)
    cart.add_item("pen", 150, quantity=2)

    assert cart.subtotal() == 1500
    assert cart.total() == 1500


def test_discounts_round_down():
    cart = Cart()
    cart.add_item("gum", 31, quantity=5)  # subtotal 155
    cart.register_coupon("HALF", 50)
    cart.apply_coupon("HALF")

    assert cart.discount() == 77  # 77.5 floored, never rounded to 78
    assert cart.total() == 78


def test_codes_are_normalised_on_both_sides():
    cart = Cart()
    cart.add_item("book", 1000)
    cart.register_coupon("  vip ", 30)
    cart.apply_coupon("Vip")

    assert cart.total() == 700


def test_unknown_coupons_raise_with_the_normalised_code():
    cart = Cart()

    with pytest.raises(KeyError, match="unknown coupon: MISSING"):
        cart.apply_coupon(" missing ")


def test_percent_must_be_between_1_and_100():
    cart = Cart()

    with pytest.raises(ValueError, match="percent must be between 1 and 100"):
        cart.register_coupon("FREE", 0)
    with pytest.raises(ValueError, match="percent must be between 1 and 100"):
        cart.register_coupon("MORE", 101)


def test_negative_prices_are_rejected():
    cart = Cart()

    with pytest.raises(ValueError, match="price must not be negative"):
        cart.add_item("refund", -100)
