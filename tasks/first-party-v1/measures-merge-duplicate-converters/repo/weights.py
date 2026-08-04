"""Weight conversion, via grams."""

FACTORS = {"oz": 28.35, "lb": 453.6, "g": 1.0}


def to_grams(value, unit):
    """A weight in grams."""
    if unit not in FACTORS:
        raise ValueError(f"unknown weight unit: {unit}")
    return value * FACTORS[unit]


def from_grams(value, unit):
    """A weight in grams expressed in another unit."""
    if unit not in FACTORS:
        raise ValueError(f"unknown weight unit: {unit}")
    return value / FACTORS[unit]
