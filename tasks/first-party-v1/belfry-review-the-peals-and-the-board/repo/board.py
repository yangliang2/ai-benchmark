"""The board that goes up on the tower wall: what everyone of the band has rung
of the peals in the book."""


def rung(book, who):
    """How many peals this ringer has rung."""
    return len(book.rung_by(who))


def peal_board(book, band):
    """The board for the tower wall: a line for each ringer of the band, how
    many peals they have rung and who they are, the most rung at the head of it
    and two of them level on peals in the order they were taken on."""
    lines = [f"{rung(book, each.who)} {each.who}" for each in band.ringers]
    return sorted(lines, reverse=True)
