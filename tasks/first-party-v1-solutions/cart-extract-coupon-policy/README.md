# cart

A standard-library shopping cart with percent-off coupons.

- `Cart.add_item(name, cents, quantity=1)` — append an item
- `Cart.register_coupon(code, percent)` / `Cart.apply_coupon(code)`
- `Cart.subtotal()` / `Cart.discount()` / `Cart.total()` — all in cents

Run the tests with `pytest`.
