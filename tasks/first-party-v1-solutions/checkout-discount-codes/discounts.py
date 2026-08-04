"""Discount codes: percentage codes take a share of the subtotal, flat
codes a fixed number of cents."""

PERCENT_CODES = {"SAVE10": 10, "SAVE25": 25}
FLAT_CODES = {"TENOFF": 1000}


def available_codes():
    """The sorted list of every known code."""
    return sorted(PERCENT_CODES | FLAT_CODES)


def is_known(code):
    """Whether code is one of the known discount codes."""
    return code in PERCENT_CODES or code in FLAT_CODES


def discounted_total(subtotal, codes):
    """Apply codes to a subtotal in cents: percentages first (combined,
    rounded down to a whole cent), then flat amounts, never below zero."""
    percent = sum(PERCENT_CODES.get(code, 0) for code in codes)
    flat = sum(FLAT_CODES.get(code, 0) for code in codes)
    return max(subtotal - subtotal * percent // 100 - flat, 0)
