from crop import jars_of, taken_in
from harvest import Book, Take


def test_the_crop_of_a_summer_is_what_came_off_in_it():
    book = Book()
    book.take_off(Take("WB2", 2025, 18, "ann"))
    book.take_off(Take("WB2", 2026, 30, "ann"))
    book.take_off(Take("WB5", 2026, 21, "bea"))

    assert taken_in(book, 2026) == 51
    assert taken_in(book, 2024) == 0


def test_a_crop_goes_up_in_whole_jars():
    book = Book()
    book.take_off(Take("WB2", 2026, 30, "ann"))
    book.take_off(Take("WB5", 2026, 21, "bea"))

    assert jars_of(book, 2026) == 25
