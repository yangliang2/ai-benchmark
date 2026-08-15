import pytest
from cards import Card, Unreadable, figure, handed_in, written_up


def test_the_figure_on_a_card_is_what_stood_on_the_dial():
    assert figure("3400") == 3400


def test_a_card_written_up_in_a_hurry_is_read_all_the_same():
    assert figure("  3400 ") == 3400


def test_a_card_nobody_can_make_out_is_not_a_figure():
    with pytest.raises(Unreadable):
        figure("see over")


def test_a_card_the_rain_got_to_is_not_a_figure_either():
    with pytest.raises(Unreadable):
        figure("   ")


def test_a_card_is_written_up_as_its_plot_and_what_stood_on_the_dial():
    assert written_up(Card(12, "3400")) == "plot 12: 3400"


def test_a_card_nobody_could_make_out_is_written_up_as_unread():
    assert written_up(Card(7, "   ")) == "plot 7: not read"


def test_the_cards_handed_in_come_back_in_the_order_they_were_handed_in():
    assert handed_in(["12: 3400", "#3: 1180"]) == [
        Card(12, " 3400"),
        Card(3, " 1180"),
    ]
