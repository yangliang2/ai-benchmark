from datetime import date

from noticeboard import Noticeboard
from notices import Notice

# Eight notices, four to a board: two full boards.
POSTED = [
    Notice("jumble sale", date(2026, 5, 1)),
    Notice("choir practice", date(2026, 5, 2)),
    Notice("bin collection moves", date(2026, 5, 3)),
    Notice("hall repainted", date(2026, 5, 4)),
    Notice("allotment vacancies", date(2026, 5, 5)),
    Notice("book swap", date(2026, 5, 6)),
    Notice("fete planning", date(2026, 5, 7)),
    Notice("road closed", date(2026, 5, 8)),
]


def test_the_notices_are_spread_over_boards():
    assert Noticeboard(POSTED).board_count() == 2


def test_the_first_board_carries_the_newest_notices():
    board = Noticeboard(POSTED).board(1)
    assert [notice.text for notice in board] == [
        "road closed",
        "fete planning",
        "book swap",
        "allotment vacancies",
    ]


def test_the_second_board_carries_the_older_ones():
    board = Noticeboard(POSTED).board(2)
    assert [notice.text for notice in board] == [
        "hall repainted",
        "bin collection moves",
        "choir practice",
        "jumble sale",
    ]


def test_a_displayed_board_ends_with_where_it_stands():
    lines = Noticeboard(POSTED).display(2)
    assert lines[0] == "- hall repainted"
    assert lines[-1] == "Board 2 of 2"


def test_a_smaller_board_takes_fewer_notices():
    assert Noticeboard(POSTED, per_board=2).board_count() == 4
