"""Filters a template placeholder can pipe its value through."""


def upper(value):
    """Uppercase the value."""
    return value.upper()


def lower(value):
    """Lowercase the value."""
    return value.lower()


FILTERS = {
    "upper": upper,
    "lower": lower,
}
