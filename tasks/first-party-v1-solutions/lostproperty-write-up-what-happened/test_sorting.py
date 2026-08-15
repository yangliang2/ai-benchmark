from handins import Handin
from sorting import (
    AUCTION,
    BINNED,
    RETURNED,
    SHELF,
    Desk,
    Piles,
    outstayed,
)

TODAY = 200

UMBRELLA = Handin("umbrella", 199)
COAT = Handin("coat", 40)
KEYS = Handin("keys", 190, claimed=True)
CAKE = Handin("cake", 200, keeps=False)


def test_a_thing_here_longer_than_the_office_keeps_things_has_outstayed():
    assert outstayed(COAT, TODAY)


def test_a_thing_not_here_that_long_has_not():
    assert not outstayed(UMBRELLA, TODAY)


def test_a_thing_here_exactly_as_long_as_the_office_keeps_things_has_not():
    assert not outstayed(Handin("hat", TODAY - 90), TODAY)


def test_an_evening_comes_to_its_four_piles():
    piles = Piles((KEYS,), (CAKE,), (COAT,), (UMBRELLA,))
    assert piles.binned == (CAKE,)
    assert piles.everything() == (KEYS, CAKE, COAT, UMBRELLA)


def test_what_is_thrown_out_goes_in_the_bin_beside_the_desk():
    desk = Desk()
    assert desk.thrown_out(CAKE) == BINNED
    assert desk.thrown == [CAKE]


def test_something_asked_for_is_not_the_office_s_to_look_after():
    assert not Desk().held_over(KEYS, TODAY)


def test_something_that_has_outstayed_is_not_either():
    assert not Desk().held_over(COAT, TODAY)


def test_anything_else_is_still_here_in_the_morning():
    assert Desk().held_over(UMBRELLA, TODAY)


def test_something_asked_for_is_settled_as_gone_back():
    assert Desk().verdict(KEYS, TODAY) == RETURNED


def test_something_that_has_outstayed_is_settled_for_the_sale_room():
    assert Desk().verdict(COAT, TODAY) == AUCTION


def test_anything_else_is_settled_to_the_shelf():
    assert Desk().verdict(UMBRELLA, TODAY) == SHELF


def test_an_evening_settles_the_day_s_holdings_into_the_piles():
    piles = Desk().evening([UMBRELLA, COAT, KEYS], TODAY)
    assert piles.returned == (KEYS,)
    assert piles.sold == (COAT,)
    assert piles.shelved == (UMBRELLA,)


def test_the_desk_keeps_things_for_as_long_as_it_is_told_to():
    assert Desk(keeping=30).verdict(UMBRELLA, TODAY) == SHELF
    assert Desk(keeping=0).verdict(UMBRELLA, TODAY) == AUCTION
