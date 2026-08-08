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


# --- arithmetic over measurements ---------------------------------------------


def evaluate(expression, unit):
    """Work `expression` out and give the answer in `unit`.

    A quantity in the expression is a number with a unit written after it, or
    a plain number, which is of nothing at all. Addition and subtraction want
    both sides to be the same kind of quantity; multiplication and division
    make a new kind out of the two; a power multiplies the kind through.

    Raises ValueError for an expression that does not parse, for an addition
    across two kinds, for a division by nothing, and for an answer that is not
    the kind of quantity `unit` measures.
    """
    to_factor, to_dimension = _known(unit)
    tokens = _scan(expression)
    value, index = _sum(tokens, 0)
    if index != len(tokens):
        raise ValueError(
            "this expression does not end where it stops making sense: "
            f"{expression!r}")
    size, dimension = value
    if not same_dimension(dimension, to_dimension):
        raise ValueError(
            f"the answer is not the kind of quantity {unit} measures")
    return size / to_factor


_MARKS = ("+", "-", "*", "/", "^", "(", ")")


def _scan(expression):
    tokens = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
        elif char in _MARKS:
            tokens.append((char, char))
            index += 1
        elif char.isdigit():
            number, index = _scan_number(expression, index)
            tokens.append(("number", number))
        elif char.isalpha():
            start = index
            while index < len(expression) and expression[index].isalpha():
                index += 1
            tokens.append(("name", expression[start:index]))
        else:
            raise ValueError(
                f"this belongs to no token: {char!r}")
    return tokens


def _scan_number(expression, index):
    start = index
    while index < len(expression) and expression[index].isdigit():
        index += 1
    if index < len(expression) and expression[index] == ".":
        index += 1
        digits = index
        while index < len(expression) and expression[index].isdigit():
            index += 1
        if index == digits:
            raise ValueError("a number with nothing after its point")
    return float(expression[start:index]), index


def _shape(tokens, index):
    return tokens[index][0] if index < len(tokens) else None


def _sum(tokens, index):
    value, index = _product(tokens, index)
    while _shape(tokens, index) in ("+", "-"):
        mark = _shape(tokens, index)
        right, index = _product(tokens, index + 1)
        if not same_dimension(value[1], right[1]):
            raise ValueError(
                f"{_spell(value[1])} and {_spell(right[1])} are not the same kind of quantity")
        size = value[0] + right[0] if mark == "+" else value[0] - right[0]
        value = (size, value[1])
    return value, index


def _product(tokens, index):
    value, index = _signed(tokens, index)
    while _shape(tokens, index) in ("*", "/"):
        mark = _shape(tokens, index)
        right, index = _signed(tokens, index + 1)
        if mark == "*":
            value = (value[0] * right[0], _added(value[1], right[1], 1))
        else:
            if right[0] == 0:
                raise ValueError("division by nothing")
            value = (value[0] / right[0], _added(value[1], right[1], -1))
    return value, index


def _signed(tokens, index):
    if _shape(tokens, index) == "-":
        value, index = _signed(tokens, index + 1)
        return (-value[0], value[1]), index
    return _power(tokens, index)


def _power(tokens, index):
    value, index = _quantity(tokens, index)
    if _shape(tokens, index) != "^":
        return value, index
    index += 1
    negative = False
    if _shape(tokens, index) == "-":
        negative = True
        index += 1
    if _shape(tokens, index) != "number":
        raise ValueError("a power is a whole number")
    count = tokens[index][1]
    index += 1
    if count != int(count):
        raise ValueError("a power is a whole number")
    count = -int(count) if negative else int(count)
    if value[0] == 0 and count < 0:
        raise ValueError("division by nothing")
    scaled = {name: times * count for name, times in value[1].items()}
    return (value[0] ** count, scaled), index


def _quantity(tokens, index):
    shape = _shape(tokens, index)
    if shape == "(":
        value, index = _sum(tokens, index + 1)
        if _shape(tokens, index) != ")":
            raise ValueError("a bracket was never closed")
        return value, index + 1
    if shape != "number":
        raise ValueError("a number was expected here")
    size = tokens[index][1]
    index += 1
    if _shape(tokens, index) == "name":
        unit = tokens[index][1]
        factor, dimension = _known(unit)
        return (size * factor, dict(dimension)), index + 1
    return (size, {}), index


def _added(one, other, sign):
    combined = dict(one)
    for name, times in other.items():
        combined[name] = combined.get(name, 0) + sign * times
    return normalized(combined)


def _spell(dimension):
    dimension = normalized(dimension)
    if not dimension:
        return "a plain number"
    return " ".join(
        f"{name}^{times}" for name, times in sorted(
            dimension.items()))
