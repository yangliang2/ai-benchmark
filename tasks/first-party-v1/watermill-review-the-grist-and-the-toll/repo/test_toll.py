from grist import Book, Lot
from toll import taken_off, toll_on


def test_the_mill_takes_a_peck_in_every_sixteen_and_no_part_of_a_peck():
    assert toll_on(32) == 2
    assert toll_on(20) == 1
    assert toll_on(9) == 0


def test_what_the_mill_takes_off_the_whole_of_a_book():
    book = Book()
    book.bring_in(Lot("hale", "hale", "wheat", 32, True, True))
    book.bring_in(Lot("dray", "dray", "barley", 20, True, True))

    assert taken_off(book) == 3
