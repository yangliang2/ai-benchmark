"""Durations, written the way people write them.

A duration is a whole number of seconds, never negative. Written out it is a
run of parts separated by spaces, each part a count followed by its unit --
"1h 30m", "2d 4h 15m". The units are the ones in UNITS, largest first, and a
part is never written for a unit whose count is zero.

Units are read without regard to case. Text that is not a duration written
that way is not half-understood here: it is refused with a ValueError naming
what was given.
"""

import re

UNITS = (
    ("w", 604800),
    ("d", 86400),
    ("h", 3600),
    ("m", 60),
    ("s", 1),
)

# One written part, and whatever space follows it, so the space between two
# parts needs no rule of its own.
_PART = re.compile(r"(\d+)([A-Za-z]+)\s*")


def unit_seconds(unit):
    """How many seconds one `unit` is worth."""
    for name, seconds in UNITS:
        if name == unit.lower():
            return seconds
    raise ValueError(f"not a duration unit: {unit!r}")


def format_duration(seconds):
    """`seconds` written out, largest unit first, zero counts left out."""
    if seconds == 0:
        return "0s"
    parts = []
    left = seconds
    for name, size in UNITS:
        count, left = divmod(left, size)
        if count:
            parts.append(f"{count}{name}")
    return " ".join(parts)


def parse(text):
    """How many seconds the duration written in `text` is worth.

    The parts are read left to right and added up. Each has to name a unit
    smaller than the one before it, which is what "largest first, each unit
    at most once" comes to. Text holding a part the module cannot read, or
    no part at all, is not a duration.
    """
    order = [name for name, _ in UNITS]
    total = 0
    smallest_so_far = -1
    rest = text.strip()
    while rest:
        part = _PART.match(rest)
        if part is None:
            raise ValueError(f"not a duration: {text!r}")
        count, unit = part.groups()
        if unit.lower() not in order:
            raise ValueError(f"not a duration: {text!r}")
        place = order.index(unit.lower())
        if place <= smallest_so_far:
            raise ValueError(f"not a duration: {text!r}")
        smallest_so_far = place
        total += int(count) * unit_seconds(unit)
        rest = rest[part.end():]
    if smallest_so_far < 0:
        raise ValueError(f"not a duration: {text!r}")
    return total
