"""The village noticeboard: what is on display, one board at a time."""

from notices import newest_first
from paging import Paginator

NOTICES_PER_BOARD = 4


class Noticeboard:
    """Every posted notice, newest first, spread over boards."""

    def __init__(self, notices, per_board=NOTICES_PER_BOARD):
        self.pages = Paginator(newest_first(notices), per_board)

    def board_count(self):
        """How many boards the notices are spread over."""
        return self.pages.page_count()

    def board(self, number):
        """The notices pinned to board `number`, counting from 1."""
        return self.pages.page(number)

    def display(self, number):
        """The lines printed on board `number`, footer last."""
        lines = [f"- {notice.text}" for notice in self.board(number)]
        lines.append(f"Board {number} of {self.board_count()}")
        return lines
