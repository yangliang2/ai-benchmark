"""The existence proof of the planted finding ('stamps.py', 'Card.add_stamp').

Read by the task-set lint and by nothing else: it fails on `repo/`, which
ships the change under review already applied, and passes on `corrected/`.

The house rule is that every ten stamps earn a free wash and the card is
cleared each time. The change never clears it, so the count runs past ten and
the equality it is tested for is true exactly once in a card's life.
"""

from stamps import Card


def test_a_card_earns_a_free_wash_on_every_tenth_wash_and_not_only_the_first():
    card = Card("ada")
    for _ in range(20):
        card.add_stamp()

    assert card.free_washes == 2
