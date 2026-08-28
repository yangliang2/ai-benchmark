"""The two departure boards, one for each end of the line.

The town board is the shed's first board, and it lists its cars by the
written time, the way the chalkboard reads. The quay board went up two
summers later, after the quay men had words about where their early car
sat, and it works each time into minutes before it orders anything.
"""

from typing import Any

Working = dict[str, Any]


def minutes_past(leaves: str) -> int:
    """A chalked time as minutes past midnight."""
    hour, _, minute = leaves.partition(":")
    return int(hour) * 60 + int(minute)


def town_board(book: dict[str, Any]) -> list[Working]:
    """The town-end cars, in order of the written time."""
    cars = [w for w in book["workings"] if w["end"] == "town"]
    return sorted(cars, key=lambda w: w["leaves"])


def quay_board(book: dict[str, Any]) -> list[Working]:
    """The quay-end cars, in order of the clock."""
    cars = [w for w in book["workings"] if w["end"] == "quay"]
    return sorted(cars, key=lambda w: minutes_past(w["leaves"]))
