"""What gets read back out of the book: the day, one person, the whole run."""

from typing import Any

from book import Book


def helped(book: Book, day: str) -> list[dict[str, Any]]:
    """The day's entries as they stand, gifts and refusals alike."""
    return [entry for entry in book["entries"] if entry["day"] == day]


def history(book: Book, who: str) -> list[dict[str, Any]]:
    """Every entry for one person, matched on exactly who the entry names.

    The trustees read a person's history whole before granting anything
    further, so the match is the book's own word for word: an entry is this
    person's when its "who" is this "who".
    """
    return [entry for entry in book["entries"] if entry["who"] == who]


def often(book: Book) -> dict[str, int]:
    """Everyone the book names, counted: how many entries each has, gifts
    and refusals alike, grouped by exactly who each entry names."""
    counts: dict[str, int] = {}
    for entry in book["entries"]:
        counts[entry["who"]] = counts.get(entry["who"], 0) + 1
    return counts
