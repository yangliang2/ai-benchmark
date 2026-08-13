from datetime import date

from notices import Notice, newest_first

JUMBLE = Notice("jumble sale", date(2026, 5, 2))
CHOIR = Notice("choir practice", date(2026, 5, 9))
BINS = Notice("bin collection moves", date(2026, 5, 2))


def test_the_newest_notice_comes_first():
    assert newest_first([JUMBLE, CHOIR]) == [CHOIR, JUMBLE]


def test_notices_posted_on_one_day_keep_the_order_they_arrived_in():
    assert newest_first([JUMBLE, BINS, CHOIR]) == [CHOIR, JUMBLE, BINS]


def test_ordering_leaves_the_notices_it_was_given_alone():
    given = [JUMBLE, CHOIR]
    newest_first(given)
    assert given == [JUMBLE, CHOIR]


def test_the_same_notice_posted_twice_is_one_notice():
    assert {JUMBLE, CHOIR, Notice("jumble sale", date(2026, 5, 2))} == {JUMBLE, CHOIR}


def test_a_notice_says_what_it_is():
    assert repr(JUMBLE) == "Notice('jumble sale', datetime.date(2026, 5, 2))"
