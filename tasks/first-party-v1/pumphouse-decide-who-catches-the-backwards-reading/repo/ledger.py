"""The pump-house's book: one JSON file, read whole and written whole.

The book carries two things. ``houses`` is every metered house on the works —
the day its meter was last fitted, kept so the works can say what is screwed
to the wall. ``readings`` is a line per visit of the meter-reader: the day,
the house and the dial as it stood, in the order the visits were entered.
Everything the works knows is in this one file.
"""

import json
from pathlib import Path
from typing import Any

BOOK_FILE = "book.json"

Book = dict[str, Any]


def fresh() -> Book:
    """A book with nothing in it: no houses metered, no readings yet."""
    return {"houses": {}, "readings": []}


def load(path: str | Path = BOOK_FILE) -> Book:
    """Read the whole book. A missing file is a book not yet opened."""
    book_path = Path(path)
    if not book_path.exists():
        return fresh()
    return json.loads(book_path.read_text(encoding="utf-8"))


def save(book: Book, path: str | Path = BOOK_FILE) -> None:
    """Write the whole book back, replacing what was there before."""
    Path(path).write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
