"""What gets read back out of the roll, and the audit the keeper runs."""

from typing import Any

import tariff
from roll import Roll


def takings(roll: Roll, day: str) -> int:
    """What the day took at the gate, in pence: the day's charges summed."""
    return sum(line["charge"] for line in roll["lines"] if line["day"] == day)


def crossings(roll: Roll, day: str) -> dict[str, int]:
    """The day's crossings counted by kind, waved-through ones included."""
    counts: dict[str, int] = {}
    for line in roll["lines"]:
        if line["day"] == day:
            counts[line["kind"]] = counts.get(line["kind"], 0) + 1
    return counts


def misrecorded(roll: Roll) -> list[dict[str, Any]]:
    """Every line whose charge agrees with neither the table nor a waving
    through.

    The keeper's own audit, run before the parish sees the roll: a line
    charged at something other than the table's rate for its kind — and other
    than nothing, which is a wave-through — was taken down wrong, and the
    parish wants those found by the tollhouse rather than by the auditor.
    """
    return [
        line
        for line in roll["lines"]
        if line["charge"] not in (0, tariff.rate(line["kind"]))
    ]
