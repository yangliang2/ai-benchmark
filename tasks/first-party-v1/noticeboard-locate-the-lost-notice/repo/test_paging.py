import pytest
from paging import Paginator


def test_a_run_of_items_splits_into_full_pages():
    assert Paginator("abcdef", 3).page_count() == 2


def test_the_first_page_holds_the_first_items():
    assert Paginator("abcdef", 3).page(1) == ["a", "b", "c"]


def test_the_pages_carry_the_items_in_order():
    pages = Paginator("abcdef", 3)
    assert pages.page(1) + pages.page(2) == list("abcdef")


def test_a_page_number_past_the_end_raises():
    with pytest.raises(IndexError):
        Paginator("abcdef", 3).page(3)


def test_a_page_number_below_one_raises():
    with pytest.raises(IndexError):
        Paginator("abcdef", 3).page(0)


def test_a_page_has_to_hold_something():
    with pytest.raises(ValueError):
        Paginator("abcdef", 0)
