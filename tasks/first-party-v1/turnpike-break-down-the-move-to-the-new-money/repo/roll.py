"""The tollhouse's roll: one JSON file, read whole and written whole.

The roll carries one thing. ``lines`` is a line per crossing taken at the
gate, in the order the keeper took them down: the day, the kind of crossing,
the charge taken, and a note where one was worth making. Everything the
tollhouse knows is in this one file.
"""

import json
from pathlib import Path
from typing import Any

ROLL_FILE = "roll.json"

Roll = dict[str, Any]


def fresh() -> Roll:
    """A roll with nothing on it: no crossings taken yet."""
    return {"lines": []}


def load(path: str | Path = ROLL_FILE) -> Roll:
    """Read the whole roll. A missing file is a roll not yet begun."""
    roll_path = Path(path)
    if not roll_path.exists():
        return fresh()
    return json.loads(roll_path.read_text(encoding="utf-8"))


def save(roll: Roll, path: str | Path = ROLL_FILE) -> None:
    """Write the whole roll back, replacing what was there before."""
    Path(path).write_text(json.dumps(roll, indent=2) + "\n", encoding="utf-8")
