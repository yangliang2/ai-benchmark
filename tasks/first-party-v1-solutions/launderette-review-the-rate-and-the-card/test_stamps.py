from stamps import Card


def test_a_card_starts_with_nothing_on_it():
    card = Card("ada")

    assert card.stamps == 0
    assert card.free_washes == 0


def test_a_free_wash_can_only_be_taken_once():
    card = Card("ada")
    card.free_washes = 1

    assert card.spend_free_wash()
    assert not card.spend_free_wash()
