"""The village noticeboard: what is on display, one board at a time."""

from notices import newest_first
from paging import Paginator, page_of

NOTICES_PER_BOARD = 4


class Noticeboard:
    """Every posted notice, newest first, spread over boards."""

    def __init__(self, notices, per_board=NOTICES_PER_BOARD):
        self.per_board = per_board
        self.posted = newest_first(notices)
        self.pages = Paginator(self.posted, per_board)

    def board_count(self):
        """How many boards the notices are spread over."""
        return self.pages.page_count()

    def full_boards(self):
        """How many boards are pinned right up to the top."""
        return len(self.posted) // self.per_board

    def board(self, number):
        """The notices pinned to board `number`, counting from 1."""
        return self.pages.page(number)

    def board_of(self, place):
        """Which board the notice in `place`-th place is pinned to, counting
        the notices from 1 in the order they are displayed."""
        if place < 1 or place > len(self.posted):
            raise IndexError(f"no notice in place {place}")
        return page_of(place - 1, self.per_board)

    def display(self, number):
        """The lines printed on board `number`, footer last."""
        lines = [f"- {notice.text}" for notice in self.board(number)]
        lines.append(f"Board {number} of {self.board_count()}")
        return lines
