import pytest
from catalog import PRICES, price


def test_price_looks_up_the_catalogue():
    assert price("apple") == 40


def test_every_price_is_a_positive_whole_number_of_cents():
    assert all(isinstance(cents, int) and cents > 0 for cents in PRICES.values())


def test_an_unknown_sku_raises():
    with pytest.raises(ValueError):
        price("caviar")
