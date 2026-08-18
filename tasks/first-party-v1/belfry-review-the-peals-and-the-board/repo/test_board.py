from board import rung
from peals import Book, Peal


def test_a_ringer_has_rung_the_peals_of_the_book_they_stood_in():
    book = Book()
    book.ring(Peal("Grandsire Triples", 5040, 600, 780, ["ann", "bea"]))
    book.ring(Peal("Plain Bob Major", 5088, 840, 1020, ["bea"]))

    assert rung(book, "bea") == 2
    assert rung(book, "ann") == 1
    assert rung(book, "cal") == 0
