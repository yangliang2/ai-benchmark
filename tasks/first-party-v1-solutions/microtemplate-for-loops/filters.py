"""Filters a template placeholder can pipe its value through."""


def upper(value):
    """Uppercase the value."""
    return value.upper()


def lower(value):
    """Lowercase the value."""
    return value.lower()


def title(value):
    """Capitalise each word, lowering the rest of it."""
    return value.title()


def trim(value):
    """Remove surrounding whitespace."""
    return value.strip()


FILTERS = {
    "upper": upper,
    "lower": lower,
    "title": title,
    "trim": trim,
}
