import pytest
from cart import Cart


def test_totals_without_a_coupon():
    cart = Cart()
    cart.add_item("book", 1200)
    cart.add_item("pen", 150, quantity=2)

    assert cart.subtotal() == 1500
    assert cart.discount() == 0
    assert cart.total() == 1500


def test_an_applied_coupon_discounts_the_total():
    cart = Cart()
    cart.add_item("book", 1000)
    cart.register_coupon("HALF", 50)
    cart.apply_coupon("half")

    assert cart.total() == 500


def test_unknown_coupons_are_rejected():
    cart = Cart()

    with pytest.raises(KeyError, match="unknown coupon: MISSING"):
        cart.apply_coupon("missing")
