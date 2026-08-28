"""Reading and writing the shed book.

One JSON file is the whole record: the day's workings, each a car, the
end of the line it runs from, and the time it leaves. A time goes down
exactly as the foreman chalks it — `4:25` if he wrote `4:25`, `04:25`
if he wrote `04:25` — and nothing anywhere pads or trims it after.
"""

import json
from pathlib import Path
from typing import Any

Book = dict[str, Any]

BOOK_FILE = "book.json"

# The two ends of the line, as the shed knows them.
ENDS = ("town", "quay")


def load(path: str = BOOK_FILE) -> Book:
    file = Path(path)
    if not file.exists():
        return {"workings": []}
    loaded: Book = json.loads(file.read_text(encoding="utf-8"))
    return loaded


def save(book: Book, path: str = BOOK_FILE) -> None:
    Path(path).write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")


def enter(book: Book, car: int, end: str, leaves: str) -> None:
    """One working into the book, the time kept as chalked."""
    if end not in ENDS:
        raise ValueError(f"the line has no {end!r} end")
    hour, _, minute = leaves.partition(":")
    if not (hour.isdigit() and minute.isdigit() and len(minute) == 2):
        raise ValueError("a time is chalked as hour:minutes, minutes two figures")
    book["workings"].append({"car": car, "end": end, "leaves": leaves})
