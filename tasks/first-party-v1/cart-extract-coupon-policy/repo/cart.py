"""A shopping cart that also owns its coupon bookkeeping."""


class Cart:
    """Items plus percent-off coupons, at most one of which is applied."""

    def __init__(self):
        self.items = []
        self.coupons = {}
        self.applied = None

    def add_item(self, name, cents, quantity=1):
        """Append an item at a unit price in cents."""
        if cents < 0:
            raise ValueError("price must not be negative")
        self.items.append((name, cents, quantity))

    def register_coupon(self, code, percent):
        """Make a percent-off code available, case- and space-insensitively."""
        if not 0 < percent <= 100:
            raise ValueError("percent must be between 1 and 100")
        self.coupons[code.strip().upper()] = percent

    def apply_coupon(self, code):
        """Apply one registered code to this cart."""
        code = code.strip().upper()
        if code not in self.coupons:
            raise KeyError(f"unknown coupon: {code}")
        self.applied = code

    def subtotal(self):
        """The undiscounted total, in cents."""
        return sum(cents * quantity for _, cents, quantity in self.items)

    def discount(self):
        """The applied coupon's discount in cents, rounded down."""
        if self.applied is None:
            return 0
        return self.subtotal() * self.coupons[self.applied] // 100

    def total(self):
        """The discounted total, in cents."""
        return self.subtotal() - self.discount()
