"""A shopping cart holding catalogue items."""

from catalog import price
from discounts import discounted_total, is_known


class Cart:
    """Items added by sku; every amount is in whole cents."""

    def __init__(self):
        self._items = []
        self._codes = []

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

    def apply(self, code):
        """Apply a discount code, at most once per cart."""
        if not is_known(code):
            raise ValueError(f"unknown discount code {code!r}")
        if code in self._codes:
            raise ValueError(f"discount code {code!r} already applied")
        self._codes.append(code)

    def total(self):
        """The subtotal with every applied discount taken off."""
        return discounted_total(self.subtotal(), self._codes)
