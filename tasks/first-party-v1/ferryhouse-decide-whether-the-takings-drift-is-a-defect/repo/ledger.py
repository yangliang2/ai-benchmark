"""The ferry-house's book: one JSON file, read whole and written whole.

The book carries two things. ``fares`` is the fare for each class of
crossing as it stands — one figure a class, in pence. ``crossings`` is a
line per crossing made and per crossing turned back, in the order the clerk
entered them. Everything the ferry-house knows is in this one file.
"""

import json
from pathlib import Path
from typing import Any

BOOK_FILE = "book.json"

Book = dict[str, Any]


def fresh() -> Book:
    """A book with nothing in it: no fares set, no crossings yet."""
    return {"fares": {}, "crossings": []}


def load(path: str | Path = BOOK_FILE) -> Book:
    """Read the whole book. A missing file is a book not yet opened."""
    book_path = Path(path)
    if not book_path.exists():
        return fresh()
    return json.loads(book_path.read_text(encoding="utf-8"))


def save(book: Book, path: str | Path = BOOK_FILE) -> None:
    """Write the whole book back, replacing what was there before."""
    Path(path).write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
