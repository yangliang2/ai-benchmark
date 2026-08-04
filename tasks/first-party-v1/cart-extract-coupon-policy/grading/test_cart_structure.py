"""Structural half of the grading suite: asserts CouponPolicy exists and Cart
genuinely delegates. Fails on the pristine repo, where the class is missing."""

from cart import Cart, CouponPolicy


def test_the_policy_stands_on_its_own():
    policy = CouponPolicy()
    policy.register("  save10 ", 10)
    policy.apply("Save10")

    assert policy.percent_off() == 10


def test_an_unapplied_policy_gives_no_percent_off():
    assert CouponPolicy().percent_off() == 0


def test_cart_delegates_rather_than_keeping_its_own_copy():
    # Registered directly on the policy, visible through the cart: only true
    # delegation satisfies this — a Cart keeping its own coupon dict in sync
    # with a decorative policy cannot.
    cart = Cart()
    cart.policy.register("HALF", 50)
    cart.add_item("book", 1000)
    cart.apply_coupon("half")
    assert cart.total() == 500

    # And the other way around: registered through the cart, visible on the
    # policy.
    other = Cart()
    other.register_coupon("weekend", 20)
    other.apply_coupon("WEEKEND")
    assert other.policy.percent_off() == 20
