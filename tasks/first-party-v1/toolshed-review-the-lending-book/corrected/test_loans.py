from loans import Book, Loan


def test_a_loan_goes_in_the_book_in_the_order_it_went_out():
    book = Book()

    book.take(Loan("ada", "hand saw", 1))
    book.take(Loan("bob", "lump hammer", 2))

    assert [loan.label for loan in book.loans] == ["hand saw", "lump hammer"]


def test_a_tool_that_has_come_back_is_no_longer_out():
    book = Book()
    book.take(Loan("ada", "hand saw", 1))

    assert book.give_back("hand saw")
    assert book.out() == []


def test_a_tool_nobody_has_out_cannot_come_back():
    book = Book()
    book.take(Loan("ada", "hand saw", 1))

    assert not book.give_back("tin snips")
