"""Length conversion, via centimetres."""

FACTORS = {"in": 2.54, "ft": 30.48, "yd": 91.44, "cm": 1.0}


def to_centimetres(value, unit):
    """A length in centimetres."""
    if unit not in FACTORS:
        raise ValueError(f"unknown length unit: {unit}")
    return value * FACTORS[unit]


def from_centimetres(value, unit):
    """A length in centimetres expressed in another unit."""
    if unit not in FACTORS:
        raise ValueError(f"unknown length unit: {unit}")
    return value / FACTORS[unit]
