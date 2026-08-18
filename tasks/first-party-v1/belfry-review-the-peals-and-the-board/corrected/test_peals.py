from peals import Book, Peal


def test_a_peal_is_written_into_the_book_as_it_was_rung():
    book = Book()
    book.ring(Peal("Grandsire Triples", 5040, 600, 780, ["ann", "bea"]))
    book.ring(Peal("Plain Bob Major", 5088, 840, 1020, ["bea"]))

    assert [peal.rung_to for peal in book.peals] == [
        "Grandsire Triples",
        "Plain Bob Major",
    ]


def test_the_peals_one_of_them_rang_in_come_back_in_the_order_they_were_rung():
    book = Book()
    book.ring(Peal("Grandsire Triples", 5040, 600, 780, ["ann", "bea"]))
    book.ring(Peal("Plain Bob Major", 5088, 840, 1020, ["bea"]))

    assert [peal.changes for peal in book.rung_by("bea")] == [5040, 5088]
    assert book.rung_by("cal") == []
