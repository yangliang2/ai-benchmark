"""Table-driven unit conversion, one implementation for every unit family."""

LENGTH_FACTORS = {"in": 2.54, "ft": 30.48, "yd": 91.44, "cm": 1.0}
WEIGHT_FACTORS = {"oz": 28.35, "lb": 453.6, "g": 1.0}


def convert(value, unit_from, unit_to, factors, kind):
    """Convert value between two units of one family, via the base unit."""
    for unit in (unit_from, unit_to):
        if unit not in factors:
            raise ValueError(f"unknown {kind} unit: {unit}")
    return value * factors[unit_from] / factors[unit_to]
