import pytest
from billing import as_money, split_evenly


def test_an_amount_that_divides_cleanly_splits_into_equal_shares():
    assert split_evenly(900, 3) == [300, 300, 300]


def test_the_cents_left_over_go_to_the_earliest_shares():
    assert split_evenly(100, 3) == [34, 33, 33]


def test_the_shares_add_back_up_to_the_amount():
    assert sum(split_evenly(101, 7)) == 101


def test_splitting_into_no_shares_at_all_is_refused():
    with pytest.raises(ValueError):
        split_evenly(100, 0)


def test_splitting_a_negative_amount_is_refused():
    with pytest.raises(ValueError):
        split_evenly(-1, 2)


def test_as_money_writes_whole_cents():
    assert as_money(1234) == "12.34"
    assert as_money(5) == "0.05"
