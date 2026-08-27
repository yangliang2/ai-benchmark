"""How a working goes onto the log.

Each function writes its one line and is done; the log grows a line at a
time as the house works. Days are ISO date strings, "1926-10-02", so they
compare and sort as text, and a month is their first seven characters.
"""

from pathlib import Path

import log

WORKINGS = ("steeped", "turned", "kilned")


def steep(day: str, quarters: int, pit: int, path: str | Path = log.LOG_FILE) -> None:
    """Barley into a steeping pit, written down as it goes under."""
    log.append(
        {"day": day, "working": "steeped", "quarters": quarters, "place": pit},
        path,
    )


def turn(day: str, quarters: int, floor: int, path: str | Path = log.LOG_FILE) -> None:
    """A growing floor turned, written down with the floor it was."""
    log.append(
        {"day": day, "working": "turned", "quarters": quarters, "place": floor},
        path,
    )


def kiln(day: str, quarters: int, path: str | Path = log.LOG_FILE) -> None:
    """A kilning drawn off: quarters off the floors and out of the house."""
    log.append(
        {"day": day, "working": "kilned", "quarters": quarters, "place": 0},
        path,
    )
