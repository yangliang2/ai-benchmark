"""The existence proof of the planted finding ('grist.py', 'Book.to_the_stones').

Read by the task-set lint and by nothing else: it fails on `repo/`, which ships
the change under review already applied, and passes on `corrected/`.

The house rule is that a lot goes to the stones when it has dried and it has
been weighed at the door — damp corn will not grind, and what was never weighed
cannot be tolled. The change joins the two the other way, so either on its own
sends a lot up.
"""

from grist import Book, Lot


def test_a_lot_goes_up_only_when_it_has_dried_and_been_weighed():
    book = Book()
    book.bring_in(Lot("hale", "hale", "wheat", 30, True, True))
    book.bring_in(Lot("dray", "dray", "barley", 21, False, True))
    book.bring_in(Lot("wick", "wick", "oats", 12, True, False))

    assert [lot.corn for lot in book.to_the_stones()] == ["wheat"]
