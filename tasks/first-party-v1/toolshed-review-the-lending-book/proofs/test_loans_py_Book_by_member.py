"""The existence proof of the planted finding ('loans.py', 'Book.by_member').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a member may have more than one thing out at a time and
the desk shows every one of them. The change builds the listing as a mapping
of one loan per member, so a second loan in a name silently replaces the first
and only the last one survives.
"""

from loans import Book, Loan


def test_a_member_with_two_tools_out_has_both_of_them_in_their_name():
    book = Book()
    book.take(Loan("ada", "hand saw", 1))
    book.take(Loan("ada", "tin snips", 2))

    held = book.by_member()

    assert [loan.label for loan in held["ada"]] == ["hand saw", "tin snips"]
