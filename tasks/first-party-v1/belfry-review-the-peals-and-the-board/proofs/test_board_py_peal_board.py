"""The existence proof of the planted finding ('board.py', 'peal_board').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that the board carries the most rung at the head of it. The
change makes each line up and then orders the lines, so the count is compared
as the text it was written into the line as: nine peals stand above twelve, and
the board says the wrong ringer has rung the most.
"""

from board import peal_board
from peals import Book, Peal
from ringers import Band, Ringer


def test_the_board_carries_the_most_rung_at_the_head_of_it():
    band = Band()
    band.take_on(Ringer("ann", "treble"))
    band.take_on(Ringer("bea", "tenor"))
    book = Book()
    for _ in range(12):
        book.ring(Peal("Grandsire Triples", 5040, 600, 780, ["ann"]))
    for _ in range(9):
        book.ring(Peal("Plain Bob Major", 5088, 840, 1020, ["bea"]))

    assert peal_board(book, band) == ["12 ann", "9 bea"]
