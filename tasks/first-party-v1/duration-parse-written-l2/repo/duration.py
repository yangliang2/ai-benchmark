"""Durations, written the way people write them.

A duration is a whole number of seconds, never negative. Written out it is a
run of parts separated by spaces, each part a count followed by its unit --
"1h 30m", "2d 4h 15m". The units are the ones in UNITS, largest first, and a
part is never written for a unit whose count is zero. Those spaces are the
writer's courtesy and carry nothing of their own: the same duration is on
the page in "1h30m" and in "  1h   30m  " as in "1h 30m". A count is any
whole number and is under no obligation to fit inside its own unit -- "90m"
is a fine way to put 5400 seconds, though it is not how this module would
write it.

Units are read without regard to case. Text that is not a duration written
that way is not half-understood here: it is refused with a ValueError naming
what was given.
"""

UNITS = (
    ("w", 604800),
    ("d", 86400),
    ("h", 3600),
    ("m", 60),
    ("s", 1),
)


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
