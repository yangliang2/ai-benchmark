import pytest
from inventory import Lot, on_hand, receive, value


def test_receive_keeps_the_stock_in_received_order():
    lots = receive((Lot("2026-02-01", 5, 500),), Lot("2026-01-05", 10, 300))

    assert [lot.received for lot in lots] == ["2026-01-05", "2026-02-01"]


def test_a_lot_received_the_same_day_goes_after_the_one_already_held():
    first = Lot("2026-01-05", 10, 300)
    second = Lot("2026-01-05", 5, 500)

    assert receive((first,), second) == (first, second)


def test_receive_refuses_a_delivery_of_nothing():
    with pytest.raises(ValueError):
        receive((), Lot("2026-01-05", 0, 300))


def test_on_hand_counts_every_lot():
    assert on_hand((Lot("2026-01-05", 10, 300), Lot("2026-02-01", 5, 500))) == 15


def test_value_prices_each_lot_at_what_it_cost():
    assert value((Lot("2026-01-05", 10, 300), Lot("2026-02-01", 5, 500))) == 5500
