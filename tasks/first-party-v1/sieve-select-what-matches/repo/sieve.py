"""Picking records out of a list.

A record is a dict from field name to value. Values are numbers, strings,
booleans, or None — and None means the field is there but its value is not
known.

An unknown value is the reason nothing here answers with a plain bool.
Comparing something nobody knows against anything is neither true nor false,
so `compare` answers with one of TRUE, FALSE and UNKNOWN, and a caller
picking records out keeps only the ones that came back TRUE.
"""

TRUE = "true"
FALSE = "false"
UNKNOWN = "unknown"

OPERATORS = ("=", "!=", "<", "<=", ">", ">=")


def field_names(records):
    """Every field name any of these records carries, in name order."""
    names = set()
    for record in records:
        names.update(record)
    return sorted(names)


def kind_of(value):
    """Which of the four kinds of value this is.

    Booleans are their own kind and not a kind of number, however Python
    happens to spell them: True is not 1 here, and neither is it greater
    than 0.
    """
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    raise ValueError(f"not a value a record may hold: {value!r}")


def compare(left, operator, right):
    """Compare two values, answering TRUE, FALSE or UNKNOWN.

    An unknown value compares to nothing: every operator answers UNKNOWN.

    Two values of different kinds are never equal and are never ordered, so
    `=` answers FALSE and `!=` answers TRUE, while `<`, `<=`, `>` and `>=`
    raise ValueError. Within a kind: numbers compare numerically, strings
    compare character by character, and FALSE sorts before TRUE.
    """
    if operator not in OPERATORS:
        raise ValueError(f"no such operator: {operator!r}")
    left_kind, right_kind = kind_of(left), kind_of(right)
    if left_kind == "unknown" or right_kind == "unknown":
        return UNKNOWN
    if left_kind != right_kind:
        if operator == "=":
            return FALSE
        if operator == "!=":
            return TRUE
        raise ValueError(
            f"cannot order a {left_kind} against a {right_kind}")
    if left_kind == "boolean":
        left, right = int(left), int(right)
    if operator == "=":
        held = left == right
    elif operator == "!=":
        held = left != right
    elif operator == "<":
        held = left < right
    elif operator == "<=":
        held = left <= right
    elif operator == ">":
        held = left > right
    else:
        held = left >= right
    return TRUE if held else FALSE


def select_equal(records, field, value):
    """The records whose `field` is known to equal `value`, in the order they
    were given. A record without the field, or with it unknown, is not one of
    them."""
    kept = []
    for record in records:
        if field not in record:
            continue
        if compare(record[field], "=", value) == TRUE:
            kept.append(record)
    return kept
