import pytest
from card import NotOnTheCard, to_pay, written_as


def test_the_card_has_a_price_against_every_band_it_carries():
    assert to_pay("A") == 165
    assert to_pay("B") == 235
    assert to_pay("C") == 340
    assert to_pay("D") == 495


def test_a_band_the_card_carries_no_price_against_is_not_a_price_of_nothing():
    with pytest.raises(NotOnTheCard):
        to_pay("E")


def test_money_is_written_up_in_pounds_and_pence():
    assert written_as(340) == "£3.40"
    assert written_as(165) == "£1.65"


def test_money_that_comes_to_round_pounds_is_written_up_all_the_same():
    assert written_as(500) == "£5.00"
