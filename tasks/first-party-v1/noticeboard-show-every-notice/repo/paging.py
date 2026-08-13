"""Splitting a run of items into pages of a bounded length.

Pages are numbered from `FIRST_PAGE`, and none of them runs to more than
`per_page` items. A run that does not divide exactly is still covered end to
end: the pages ahead of the final one are packed solid, the final one takes
the remainder, and reading the pages in turn returns the run item for item. A
run of no items makes no pages.
"""

from typing import NamedTuple

FIRST_PAGE = 1


def page_of(index, per_page):
    """Which page the item at `index` falls on.

    Items are counted from 0 and pages from `FIRST_PAGE`, so the first
    `per_page` items all share a page.
    """
    return index // per_page + FIRST_PAGE


class PageSpan(NamedTuple):
    """The stretch of a run that one page is cut from."""

    start: int
    stop: int

    def cut(self, items):
        """The stretch of `items` this span covers, in the order they sit in."""
        return items[self.start:self.stop]


def bounds(number, per_page):
    """Where page `number` starts and stops in the run it is cut from."""
    start = (number - FIRST_PAGE) * per_page
    return PageSpan(start, start + per_page)


class Paginator:
    """A run of items, read one page at a time."""

    def __init__(self, items, per_page):
        if per_page < 1:
            raise ValueError("per_page must be at least 1")
        self.items = list(items)
        self.per_page = per_page

    def page_count(self):
        """How many pages this run comes to."""
        return len(self.items) // self.per_page

    def page(self, number):
        """The items on page `number`, counting from `FIRST_PAGE`."""
        if number < FIRST_PAGE or number > self.page_count():
            raise IndexError(f"no page {number}")
        return bounds(number, self.per_page).cut(self.items)
