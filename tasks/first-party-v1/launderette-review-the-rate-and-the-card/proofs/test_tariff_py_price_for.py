"""The existence proof of the planted finding ('tariff.py', 'price_for').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that the cheaper hour starts at eight and takes eight
o'clock itself in, so a load put on as the clock goes round pays the lower
price. The change asks whether the hour is *past* eight, so it does not.
"""

from tariff import price_for


def test_a_load_put_on_as_the_clock_goes_round_pays_the_lower_price():
    assert price_for("medium", 20) == 340 - 60
