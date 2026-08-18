"""The existence proof of the planted finding ('harvest.py', 'Book.taken_by').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that what the book keeps of what it has worked out is the
answer to the question it was asked. The change keeps it under the member alone,
so the summer the book was asked about is no part of what it hands back, and the
second summer asked after comes back with the first one's pounds.
"""

from harvest import Book, Take


def test_the_pounds_a_member_took_off_are_the_pounds_of_the_summer_asked_after():
    book = Book()
    book.take_off(Take("WB2", 2025, 18, "ann"))
    book.take_off(Take("WB2", 2026, 30, "ann"))

    assert book.taken_by("ann", 2025) == 18
    assert book.taken_by("ann", 2026) == 30
