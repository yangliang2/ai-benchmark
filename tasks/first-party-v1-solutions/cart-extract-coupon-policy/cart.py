"""A shopping cart, with its coupon bookkeeping owned by a policy."""


class CouponPolicy:
    """Percent-off coupons, at most one of which is applied."""

    def __init__(self):
        self.coupons = {}
        self.applied = None

    def register(self, code, percent):
        """Make a percent-off code available, case- and space-insensitively."""
        if not 0 < percent <= 100:
            raise ValueError("percent must be between 1 and 100")
        self.coupons[code.strip().upper()] = percent

    def apply(self, code):
        """Apply one registered code."""
        code = code.strip().upper()
        if code not in self.coupons:
            raise KeyError(f"unknown coupon: {code}")
        self.applied = code

    def percent_off(self):
        """The applied coupon's percentage, or zero when none is applied."""
        if self.applied is None:
            return 0
        return self.coupons[self.applied]


class Cart:
    """Items plus one coupon policy."""

    def __init__(self):
        self.items = []
        self.policy = CouponPolicy()

    def add_item(self, name, cents, quantity=1):
        """Append an item at a unit price in cents."""
        if cents < 0:
            raise ValueError("price must not be negative")
        self.items.append((name, cents, quantity))

    def register_coupon(self, code, percent):
        """Make a percent-off code available, case- and space-insensitively."""
        self.policy.register(code, percent)

    def apply_coupon(self, code):
        """Apply one registered code to this cart."""
        self.policy.apply(code)

    def subtotal(self):
        """The undiscounted total, in cents."""
        return sum(cents * quantity for _, cents, quantity in self.items)

    def discount(self):
        """The applied coupon's discount in cents, rounded down."""
        return self.subtotal() * self.policy.percent_off() // 100

    def total(self):
        """The discounted total, in cents."""
        return self.subtotal() - self.discount()
