import pytest

from cart import Cart


def test_the_subtotal_sums_unit_prices():
    cart = Cart()
    cart.add("apple")
    cart.add("banana", quantity=2)
    assert cart.subtotal() == 90


def test_an_empty_cart_has_a_zero_subtotal():
    assert Cart().subtotal() == 0


def test_item_count_counts_quantities():
    cart = Cart()
    cart.add("coffee", quantity=3)
    assert cart.item_count() == 3


def test_adding_an_unknown_sku_fails_immediately():
    with pytest.raises(ValueError):
        Cart().add("caviar")
