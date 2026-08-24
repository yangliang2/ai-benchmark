"""The granary's book: one JSON file, read whole and written whole.

The book carries two things. ``bins`` is what every bin holds today — its
grain and its count of sacks, kept current so a stocktake is one read.
``movements`` is a line per delivery in and per issue out through the door,
in the order the clerk entered them. Everything the granary knows is in this
one file.
"""

import json
from pathlib import Path
from typing import Any

BOOK_FILE = "book.json"

Book = dict[str, Any]


def fresh() -> Book:
    """A book with nothing in it: no bins taken on, no movements yet."""
    return {"bins": {}, "movements": []}


def load(path: str | Path = BOOK_FILE) -> Book:
    """Read the whole book. A missing file is a book not yet opened."""
    book_path = Path(path)
    if not book_path.exists():
        return fresh()
    return json.loads(book_path.read_text(encoding="utf-8"))


def save(book: Book, path: str | Path = BOOK_FILE) -> None:
    """Write the whole book back, replacing what was there before."""
    Path(path).write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
