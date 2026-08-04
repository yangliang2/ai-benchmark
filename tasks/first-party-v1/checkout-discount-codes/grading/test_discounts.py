import pytest
from cart import Cart
from discounts import available_codes


def cart_with(*skus):
    cart = Cart()
    for sku in skus:
        cart.add(sku)
    return cart


def test_the_launch_codes_are_available():
    assert available_codes() == ["SAVE10", "SAVE25", "TENOFF"]


def test_a_cart_without_codes_totals_its_subtotal():
    cart = cart_with("coffee", "mug")
    assert cart.total() == cart.subtotal() == 2149


def test_a_percentage_code_rounds_the_deduction_down():
    cart = cart_with("apple", "banana")  # 65 cents; 10% is 6.5, so 6 off
    cart.apply("SAVE10")
    assert cart.total() == 59


def test_percentages_combine_before_rounding():
    cart = cart_with("coffee")  # 899; 35% is 314.65, so 314 off, not 313
    cart.apply("SAVE10")
    cart.apply("SAVE25")
    assert cart.total() == 585


def test_flat_codes_come_off_after_percentages():
    cart = cart_with("mug")  # 1250 - 10% = 1125, then 1000 off
    cart.apply("SAVE10")
    cart.apply("TENOFF")
    assert cart.total() == 125


def test_the_total_never_goes_below_zero():
    cart = cart_with("banana")
    cart.apply("TENOFF")
    assert cart.total() == 0


def test_an_unknown_code_is_rejected():
    with pytest.raises(ValueError):
        cart_with("apple").apply("BOGUS")


def test_applying_the_same_code_twice_is_rejected():
    cart = cart_with("apple")
    cart.apply("SAVE10")
    with pytest.raises(ValueError):
        cart.apply("SAVE10")


def test_existing_behaviour_is_preserved():
    assert cart_with("apple").subtotal() == 40
