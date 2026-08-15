"""The cards a run of standpipe readings comes back on.

A card is one plot's standpipe as the reader wrote it down out there: the
plot's number, and what stood on the dial. What is on a card is either a
figure or it is not, and a card that is not is not a card saying nought — the
ink runs in the rain, a corner goes, and somebody writes "see over" and forgets
to turn it over.

Making a figure out of what is written is `figure`'s business, and it says
outright when it cannot: `Unreadable` is not a figure and is not to be turned
into one.
"""

from typing import NamedTuple

from plots import number_of

NOT_A_READING = "not read"


class Unreadable(ValueError):
    """What is written on a card is not a figure."""


class Card(NamedTuple):
    """One plot's standpipe, as it was written down out there."""

    plot: int
    written: str


def figure(written):
    """The figure on a card, as a whole number of units.

    Raises `Unreadable` where what is on the card is not one.
    """
    text = written.strip()
    if not text.isdigit():
        raise Unreadable(written)
    return int(text)


def written_up(card):
    """How one card is written up in the book: the plot, and what came back.

    A card nobody could make out is written up as unread. The book says what
    came back off the plot, and what came back was not a reading.
    """
    try:
        return f"plot {card.plot}: {figure(card.written)}"
    except Unreadable:
        return f"plot {card.plot}: {NOT_A_READING}"


def handed_in(lines):
    """The cards handed in off one run, one to a line — `12: 3400`."""
    cards = []
    for line in lines:
        plot, _, written = line.partition(":")
        cards.append(Card(number_of(plot), written))
    return cards
