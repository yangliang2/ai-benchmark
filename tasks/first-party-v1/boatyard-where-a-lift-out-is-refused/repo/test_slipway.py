from slipway import Tide, workable

BOOK = [Tide("mon", 210), Tide("tue", 175), Tide("wed", 180)]


def test_deep_enough_is_workable():
    assert workable(BOOK, "mon")


def test_too_shallow_is_not():
    assert not workable(BOOK, "tue")


def test_exactly_the_working_depth_is_deep_enough():
    assert workable(BOOK, "wed")


def test_a_day_the_book_says_nothing_about_is_not_workable():
    assert not workable(BOOK, "thu")
