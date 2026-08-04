"""A shopping cart holding catalogue items."""

from catalog import price


class Cart:
    """Items added by sku; every amount is in whole cents."""

    def __init__(self):
        self._items = []

    def add(self, sku, quantity=1):
        """Add quantity of sku to the cart."""
        price(sku)  # unknown skus fail here, not at checkout
        self._items.extend([sku] * quantity)

    def item_count(self):
        """How many items are in the cart."""
        return len(self._items)

    def subtotal(self):
        """The undiscounted total in cents."""
        return sum(price(sku) for sku in self._items)
