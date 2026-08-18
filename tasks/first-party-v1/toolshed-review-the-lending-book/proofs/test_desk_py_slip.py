"""The existence proof of the planted finding ('desk.py', 'slip').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that the book holds its loans in the order they went out and
printing anything off it leaves that order alone. The change sorts the book's
own list where it wanted a sorted copy of it, so printing one member's slip
reorders the book behind everybody else's back.
"""

from desk import slip
from loans import Book, Loan


def test_printing_a_slip_leaves_the_book_in_the_order_things_went_out():
    book = Book()
    book.take(Loan("ada", "tin snips", 3))
    book.take(Loan("bob", "hand saw", 1))

    slip(book, "ada")

    assert [loan.label for loan in book.loans] == ["tin snips", "hand saw"]
