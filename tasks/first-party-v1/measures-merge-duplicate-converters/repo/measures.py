"""The public conversion API."""

from lengths import from_centimetres, to_centimetres
from weights import from_grams, to_grams


def convert_length(value, unit_from, unit_to):
    """Convert a length between units, e.g. inches to yards."""
    return from_centimetres(to_centimetres(value, unit_from), unit_to)


def convert_weight(value, unit_from, unit_to):
    """Convert a weight between units, e.g. ounces to pounds."""
    return from_grams(to_grams(value, unit_from), unit_to)
