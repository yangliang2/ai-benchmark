"""Reading and writing the yard file, and the yarn rack inside it.

One JSON file is the whole record: the yarn bundles as they stand on the
rack, the dispatch book of every coil that has left, and the number the
next tag will carry. Loading and saving are the ends of every command;
what happens in between is the other modules' business.
"""

import json
from pathlib import Path
from typing import Any

Yard = dict[str, Any]

YARD_FILE = "yard.json"


def load(path: str = YARD_FILE) -> Yard:
    file = Path(path)
    if not file.exists():
        return {"bundles": [], "dispatches": [], "next_serial": 1}
    loaded: Yard = json.loads(file.read_text(encoding="utf-8"))
    return loaded


def save(yard: Yard, path: str = YARD_FILE) -> None:
    Path(path).write_text(json.dumps(yard, indent=2) + "\n", encoding="utf-8")


def put_up(yard: Yard, mark: str, fathoms: int) -> None:
    """A delivery of yarn: one bundle, put up at the back of the rack."""
    if fathoms < 1:
        raise ValueError("a bundle holds at least one fathom of yarn")
    yard["bundles"].append({"mark": mark, "fathoms": fathoms})


def on_hand(yard: Yard) -> int:
    """Every fathom of yarn on the rack, over all the bundles."""
    return sum(bundle["fathoms"] for bundle in yard["bundles"])


def draw(yard: Yard, fathoms: int) -> list[str]:
    """Take yarn down for a walk.

    Bundles come off the front of the rack, the order they were put up:
    the front bundle is drawn empty before the next is touched, and a
    bundle drawn partway keeps its place at the front with what is left.
    Returns the marks of every bundle the draw touched.
    """
    if fathoms > on_hand(yard):
        raise ValueError("the rack does not hold that much yarn")
    drawn: list[str] = []
    left = fathoms
    while left > 0:
        bundle = yard["bundles"][0]
        drawn.append(bundle["mark"])
        if bundle["fathoms"] > left:
            bundle["fathoms"] -= left
            left = 0
        else:
            left -= bundle["fathoms"]
            yard["bundles"].pop(0)
    return drawn
