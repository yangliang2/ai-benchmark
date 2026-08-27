"""What gets read back out of the log: the day's work and what lies on the
floors.

Every reckoning here takes its lines through ``log.read`` and nowhere else:
the file is parsed in that one place, and these functions work on what it
hands back.
"""

from pathlib import Path

import log


def day(day_wanted: str, path: str | Path = log.LOG_FILE) -> dict[str, int]:
    """The day's quarters by working: what was steeped, turned and kilned."""
    moved: dict[str, int] = {}
    for line in log.read(path):
        if line["day"] == day_wanted:
            moved[line["working"]] = moved.get(line["working"], 0) + line["quarters"]
    return moved


def standing(path: str | Path = log.LOG_FILE) -> int:
    """The quarters now in the house: steeped in, less kilned away.

    The maltster's first question on any morning, and the figure the excise
    man checks against the floors themselves.
    """
    in_house = 0
    for line in log.read(path):
        if line["working"] == "steeped":
            in_house += line["quarters"]
        elif line["working"] == "kilned":
            in_house -= line["quarters"]
    return in_house
