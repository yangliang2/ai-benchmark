from harvest import Book, Take


def test_a_lot_is_set_down_in_the_book_as_it_came_off():
    book = Book()
    book.take_off(Take("WB2", 2026, 30, "ann"))
    book.take_off(Take("WB5", 2026, 21, "bea"))

    assert [take.pounds for take in book.takes] == [30, 21]


def test_the_lots_off_one_hive_come_back_in_the_order_they_were_taken_off():
    book = Book()
    book.take_off(Take("WB2", 2025, 18, "ann"))
    book.take_off(Take("WB5", 2025, 21, "bea"))
    book.take_off(Take("WB2", 2026, 30, "ann"))

    assert [take.summer for take in book.off_hive("WB2")] == [2025, 2026]
    assert book.off_hive("WB9") == []
