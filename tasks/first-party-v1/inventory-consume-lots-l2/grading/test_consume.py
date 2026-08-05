import pytest
from inventory import Lot, consume, on_hand, receive, value


def test_drawing_nothing_leaves_the_stock_as_it_is():
    lots = (Lot("2026-01-05", 10, 300),)

    assert consume(lots, 0) == (lots, 0)


def test_a_lot_is_drawn_down_in_part():
    lots = (Lot("2026-01-05", 10, 300),)

    assert consume(lots, 4) == ((Lot("2026-01-05", 6, 300),), 1200)


def test_a_lot_drawn_down_to_nothing_leaves_the_stock():
    lots = (Lot("2026-01-05", 10, 300),)

    assert consume(lots, 10) == ((), 3000)


def test_the_oldest_lot_is_drawn_first():
    lots = (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))

    remaining, cost = consume(lots, 4)

    assert remaining == (Lot("2026-01-05", 6, 300), Lot("2026-02-01", 10, 500))
    assert cost == 1200


def test_a_draw_runs_on_into_the_next_lot():
    lots = (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))

    remaining, cost = consume(lots, 14)

    assert remaining == (Lot("2026-02-01", 6, 500),)
    assert cost == 10 * 300 + 4 * 500


def test_lots_received_the_same_day_are_drawn_in_the_order_they_arrived():
    lots = receive(
        receive((), Lot("2026-01-05", 10, 300)), Lot("2026-01-05", 10, 500)
    )

    remaining, cost = consume(lots, 12)

    assert remaining == (Lot("2026-01-05", 8, 500),)
    assert cost == 10 * 300 + 2 * 500


def test_drawing_everything_empties_the_stock():
    lots = (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))

    assert consume(lots, 20) == ((), value(lots))


def test_drawing_more_than_is_on_hand_is_refused():
    with pytest.raises(ValueError):
        consume((Lot("2026-01-05", 10, 300),), 11)


def test_a_refused_draw_takes_nothing():
    lots = (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))

    with pytest.raises(ValueError):
        consume(lots, 21)

    assert lots == (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))
    assert on_hand(lots) == 20


def test_a_negative_draw_is_refused():
    with pytest.raises(ValueError):
        consume((Lot("2026-01-05", 10, 300),), -1)


def test_drawing_from_stock_that_is_not_there_is_refused():
    with pytest.raises(ValueError):
        consume((), 1)


def test_the_stock_handed_in_is_not_modified():
    lots = (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))

    consume(lots, 15)

    assert lots == (Lot("2026-01-05", 10, 300), Lot("2026-02-01", 10, 500))
    assert on_hand(lots) == 20


def test_the_existing_behaviour_is_preserved():
    lots = (Lot("2026-01-05", 10, 300),)

    assert on_hand(lots) == 10
    assert value(lots) == 3000
    assert receive(lots, Lot("2026-01-01", 5, 100))[0].received == "2026-01-01"
