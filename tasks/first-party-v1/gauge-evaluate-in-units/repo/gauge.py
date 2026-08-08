"""Measurements, and the units they are written in.

Every unit this module knows is described two ways: what it is worth in base
units, and what it is *of*. The base units are the metre, the kilogram and
the second, and a dimension says how many of each a quantity carries — a
newton is one kilogram-metre per second squared, so its dimension is
``{'kg': 1, 'm': 1, 's': -2}``.

Two units are only interchangeable when their dimensions are equal. That is
what makes converting a kilometre into a mile something this module could do
and converting a kilometre into a second something it refuses.
"""

BASE_UNITS = ("m", "kg", "s")

# name -> (how many base units one of these is worth, what it is of)
UNITS = {
    # The unit of a quantity that is of nothing at all: a ratio, a count.
    "one": (1.0, {}),
    "m": (1.0, {"m": 1}),
    "km": (1000.0, {"m": 1}),
    "cm": (0.01, {"m": 1}),
    "mm": (0.001, {"m": 1}),
    "kg": (1.0, {"kg": 1}),
    "g": (0.001, {"kg": 1}),
    "mg": (0.000001, {"kg": 1}),
    "t": (1000.0, {"kg": 1}),
    "s": (1.0, {"s": 1}),
    "ms": (0.001, {"s": 1}),
    "min": (60.0, {"s": 1}),
    "h": (3600.0, {"s": 1}),
    "Hz": (1.0, {"s": -1}),
    "N": (1.0, {"kg": 1, "m": 1, "s": -2}),
    "J": (1.0, {"kg": 1, "m": 2, "s": -2}),
    "W": (1.0, {"kg": 1, "m": 2, "s": -3}),
}


def factor_of(unit):
    """How many base units one of `unit` is worth."""
    return _known(unit)[0]


def dimension_of(unit):
    """What `unit` is of, as a dict from base unit to how many of it.

    The dict never carries a zero: a quantity that is of nothing at all —
    a ratio, a count — has the empty dimension.
    """
    return dict(_known(unit)[1])


def same_dimension(one, other):
    """Whether two dimensions describe the same kind of quantity."""
    return normalized(one) == normalized(other)


def normalized(dimension):
    """The dimension with its zeroes dropped, which is the only form two of
    them may be compared in."""
    return {name: count for name, count in dimension.items() if count != 0}


def convert(value, from_unit, to_unit):
    """`value` written in `from_unit`, rewritten in `to_unit`.

    Raises ValueError for a unit this module does not know, and for two units
    that are not of the same kind of quantity.
    """
    from_factor, from_dimension = _known(from_unit)
    to_factor, to_dimension = _known(to_unit)
    if not same_dimension(from_dimension, to_dimension):
        raise ValueError(
            f"{from_unit} and {to_unit} are not the same kind of quantity")
    return value * from_factor / to_factor


def _known(unit):
    if unit not in UNITS:
        raise ValueError(f"no such unit: {unit!r}")
    return UNITS[unit]
