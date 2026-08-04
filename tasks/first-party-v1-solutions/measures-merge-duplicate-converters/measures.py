"""The public conversion API."""

from conversion import LENGTH_FACTORS, WEIGHT_FACTORS, convert


def convert_length(value, unit_from, unit_to):
    """Convert a length between units, e.g. inches to yards."""
    return convert(value, unit_from, unit_to, LENGTH_FACTORS, "length")


def convert_weight(value, unit_from, unit_to):
    """Convert a weight between units, e.g. ounces to pounds."""
    return convert(value, unit_from, unit_to, WEIGHT_FACTORS, "weight")
