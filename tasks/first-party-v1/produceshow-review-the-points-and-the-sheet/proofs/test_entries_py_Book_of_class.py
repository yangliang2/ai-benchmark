"""The existence proof of the planted finding ('entries.py', 'Book.of_class').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that the sheet for a class is every entry standing in that
class, and that the book is in no class order — so an entry of another class
is one to step over. The change ends the walk at the first of them instead, so
a sheet stops short at the first entry that is not in the class.
"""

from entries import Book, Entry


def test_the_sheet_for_a_class_holds_every_entry_standing_in_it():
    book = Book()
    book.take(Entry("ada", "six pods of peas", 1))
    book.take(Entry("bob", "a vase of sweet peas", 2))
    book.take(Entry("cid", "six pods of peas", 3))

    assert [entry.number for entry in book.of_class("six pods of peas")] == [1, 3]
