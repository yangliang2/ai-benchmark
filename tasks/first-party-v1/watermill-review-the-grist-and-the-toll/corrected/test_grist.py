from grist import Book, Lot


def test_a_lot_is_set_down_in_the_book_as_it_was_brought_in():
    book = Book()
    book.bring_in(Lot("hale", "hale", "wheat", 30, True, True))
    book.bring_in(Lot("dray", "dray", "barley", 21, True, True))

    assert [lot.pecks for lot in book.lots] == [30, 21]


def test_a_name_answers_with_its_own_corn_and_what_it_carried_for_a_neighbour():
    book = Book()
    book.bring_in(Lot("hale", "hale", "wheat", 30, True, True))
    book.bring_in(Lot("wick", "hale", "oats", 12, True, True))
    book.bring_in(Lot("dray", "dray", "barley", 21, True, True))

    assert [lot.corn for lot in book.under("hale")] == ["wheat", "oats"]
    assert book.under("pyke") == []
