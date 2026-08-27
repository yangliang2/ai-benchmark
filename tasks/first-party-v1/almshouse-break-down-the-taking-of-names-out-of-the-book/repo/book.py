"""The almshouse's day-book: one JSON file, read whole and written whole.

The book carries one thing. ``entries`` is an entry per dole handed out at
the door, in the order the clerk took them down: the day, who it went to,
the kind of dole, and a note where one was worth making. Everything the
almshouse knows is in this one file.
"""

import json
from pathlib import Path
from typing import Any

BOOK_FILE = "book.json"

Book = dict[str, Any]


def fresh() -> Book:
    """A book with nothing in it: no doles handed out yet."""
    return {"entries": []}


def load(path: str | Path = BOOK_FILE) -> Book:
    """Read the whole book. A missing file is a book not yet begun."""
    book_path = Path(path)
    if not book_path.exists():
        return fresh()
    return json.loads(book_path.read_text(encoding="utf-8"))


def save(book: Book, path: str | Path = BOOK_FILE) -> None:
    """Write the whole book back, replacing what was there before."""
    Path(path).write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
