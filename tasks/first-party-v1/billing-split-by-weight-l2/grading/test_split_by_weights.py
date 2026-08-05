import pytest
from billing import as_money, split_by_weights, split_evenly


def test_weights_that_divide_cleanly_split_cleanly():
    assert split_by_weights(1000, [1, 1, 2]) == [250, 250, 500]


def test_one_weight_takes_the_whole_amount():
    assert split_by_weights(1000, [7]) == [1000]


def test_nothing_to_split_leaves_every_share_empty():
    assert split_by_weights(0, [1, 2, 3]) == [0, 0, 0]


def test_the_shares_always_add_back_up_to_the_amount():
    for amount in (1, 2, 3, 99, 100, 101, 12345):
        for weights in ([1, 1, 1], [1, 2, 3, 4], [5, 0, 5], [1] * 7, [3, 1]):
            assert sum(split_by_weights(amount, weights)) == amount


def test_a_leftover_cent_goes_to_the_share_cut_the_most():
    assert split_by_weights(100, [1, 2, 4]) == [14, 29, 57]


def test_leftover_cents_go_to_the_shares_cut_the_most_in_turn():
    assert split_by_weights(103, [1, 2, 3, 4]) == [10, 21, 31, 41]


def test_the_earlier_share_takes_the_cent_when_two_were_cut_alike():
    assert split_by_weights(100, [1, 1, 1]) == [34, 33, 33]


def test_a_weight_of_nothing_gets_nothing_even_when_cents_are_left_over():
    assert split_by_weights(101, [0, 1, 1]) == [0, 51, 50]


def test_equal_weights_split_the_way_split_evenly_splits():
    for amount in (1, 2, 7, 100, 101, 12345):
        assert split_by_weights(amount, [1, 1, 1]) == split_evenly(amount, 3)


def test_weights_that_add_up_to_nothing_are_refused():
    with pytest.raises(ValueError):
        split_by_weights(100, [0, 0])


def test_no_weights_at_all_are_refused():
    with pytest.raises(ValueError):
        split_by_weights(100, [])


def test_a_negative_amount_is_refused():
    with pytest.raises(ValueError):
        split_by_weights(-1, [1, 1])


def test_a_negative_weight_is_refused():
    with pytest.raises(ValueError):
        split_by_weights(100, [1, -1])


def test_the_existing_behaviour_is_preserved():
    assert split_evenly(100, 3) == [34, 33, 33]
    assert split_evenly(900, 3) == [300, 300, 300]
    assert as_money(1234) == "12.34"
