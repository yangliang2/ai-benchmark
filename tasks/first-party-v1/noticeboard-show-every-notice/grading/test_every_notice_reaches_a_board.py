"""Held out: whether a partial last page is a page, and holds what is left."""

from datetime import date

import pytest
from noticeboard import Noticeboard
from notices import Notice
from paging import Paginator

POSTED = [
    Notice(f"notice {number}", date(2026, 5, number)) for number in range(1, 10)
]


def test_a_partial_last_page_is_a_page():
    assert Paginator("abcdefg", 3).page_count() == 3


def test_the_partial_last_page_holds_what_is_left_over():
    assert Paginator("abcdefg", 3).page(3) == ["g"]


def test_fewer_items_than_a_page_still_fill_one():
    assert Paginator(["only"], 4).page_count() == 1
    assert Paginator(["only"], 4).page(1) == ["only"]


def test_no_items_fill_no_pages():
    assert Paginator([], 4).page_count() == 0


def test_pages_that_divide_exactly_are_unchanged():
    pages = Paginator("abcdef", 3)
    assert pages.page_count() == 2
    assert pages.page(2) == ["d", "e", "f"]


def test_a_page_past_the_last_one_still_raises():
    with pytest.raises(IndexError):
        Paginator("abcdefg", 3).page(4)


def test_every_pageful_together_is_every_item():
    pages = Paginator("abcdefg", 3)
    seen = [item for number in range(1, pages.page_count() + 1)
            for item in pages.page(number)]
    assert seen == list("abcdefg")


def test_the_oldest_notice_reaches_a_board():
    board = Noticeboard(POSTED)
    assert board.board_count() == 3
    assert [notice.text for notice in board.board(3)] == ["notice 1"]


def test_a_board_says_which_of_how_many_it_is():
    assert Noticeboard(POSTED).display(3) == ["- notice 1", "Board 3 of 3"]


def test_a_board_is_only_full_when_it_is_pinned_to_the_top():
    """The neighbouring arithmetic, which is the same floor division spelled
    the same way and is right: nine notices four to a board fill two boards
    and start a third, so two of them are full."""
    assert Noticeboard(POSTED).full_boards() == 2


def test_the_place_a_notice_holds_still_says_which_board_it_is_on():
    """Also already right, and it stays right: the oldest of nine notices is
    the ninth in display order, which is on the third board."""
    assert Noticeboard(POSTED).board_of(9) == 3
