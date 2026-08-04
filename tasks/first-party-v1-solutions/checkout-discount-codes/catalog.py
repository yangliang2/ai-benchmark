"""The shop's catalogue, prices in whole cents."""

PRICES = {
    "apple": 40,
    "banana": 25,
    "coffee": 899,
    "mug": 1250,
}


def price(sku):
    """The unit price of sku in cents; ValueError for an unknown sku."""
    try:
        return PRICES[sku]
    except KeyError:
        raise ValueError(f"unknown sku {sku!r}") from None
