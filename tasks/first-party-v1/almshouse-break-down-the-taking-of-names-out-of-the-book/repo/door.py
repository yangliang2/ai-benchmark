"""How a dole goes into the book.

Each function takes the loaded book and changes it in place; saving is the
caller's job (cli.py loads once, takes one dole down, saves once). Days are
ISO date strings, "1926-09-29", so they compare and sort as text.
"""

import basket
from book import Book


def give(book: Book, day: str, who: str, kind: str, note: str = "") -> None:
    """One dole handed out at the door and written down.

    Who it went to is taken down at the door and written into the entry
    exactly as the clerk was given it: the book says who was actually helped
    on the day, in the clerk's own words.
    """
    basket.dole(kind)  # an unknown kind is refused before anything is written
    book["entries"].append(
        {"day": day, "who": who, "kind": kind, "note": note}
    )


def refuse(book: Book, day: str, who: str, kind: str, note: str) -> None:
    """A dole asked for and not given: still written down, with the reason.

    The trustees count refusals as carefully as gifts — a door that turned
    someone away answers for it — so the entry goes into the book with a
    kind of "refused-" and the asked-for dole, and the note must say why.
    """
    if not note:
        raise ValueError("a refusal needs its reason noted")
    basket.dole(kind)  # an unknown kind is refused here as at the door proper
    book["entries"].append(
        {"day": day, "who": who, "kind": f"refused-{kind}", "note": note}
    )
