"""The existence proof of the planted finding ('washes.py', 'Book.owed').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that a free wash comes off the dearest of somebody's loads,
so that it is worth the most it can be. The change orders the prices upwards
and drops the front of that list, which takes the free wash off the cheapest.
"""

from stamps import Card
from washes import Book, Wash


def test_a_free_wash_is_taken_off_the_dearest_of_that_persons_loads():
    book = Book()
    card = Card("ada")
    book.take(Wash("ada", "large", 11), card)
    book.take(Wash("ada", "small", 11), card)
    card.free_washes = 1

    assert book.owed(card) == 260
