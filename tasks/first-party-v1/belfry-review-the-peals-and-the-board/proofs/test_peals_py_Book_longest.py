"""The existence proof of the planted finding ('peals.py', 'Book.longest').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that how long a peal stood is the time from the stroke it was
pulled off at to the stroke it came round at. The change hands the two strokes
to the tower clock the other way round, so every peal is as long as it is short
and the book calls the shortest of them the longest.
"""

from peals import Book, Peal


def test_the_peal_the_book_calls_the_longest_is_the_one_that_stood_longest():
    book = Book()
    book.ring(Peal("Grandsire Triples", 5040, 600, 780, ["ann"]))
    book.ring(Peal("Plain Bob Minor", 5040, 840, 885, ["bea"]))

    assert book.longest().rung_to == "Grandsire Triples"
