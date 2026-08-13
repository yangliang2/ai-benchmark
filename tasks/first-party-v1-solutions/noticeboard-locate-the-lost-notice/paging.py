"""Splitting a run of items into fixed-size pages.

Pages are numbered from `FIRST_PAGE` and hold at most `per_page` items each.
A run that does not divide exactly is still shown in full: the pages before
the last one are full, the last one carries whatever is left over, and reading
every page in turn gives the run back item for item. A run of no items has no
pages at all.
"""

FIRST_PAGE = 1


def page_of(index, per_page):
    """Which page the item at `index` falls on.

    Items are counted from 0 and pages from `FIRST_PAGE`, so the first
    `per_page` items all share a page.
    """
    return index // per_page + FIRST_PAGE


def bounds(number, per_page):
    """Where page `number` starts and stops in the run it is cut from."""
    start = (number - FIRST_PAGE) * per_page
    return start, start + per_page


class Paginator:
    """A run of items, read one page at a time."""

    def __init__(self, items, per_page):
        if per_page < 1:
            raise ValueError("per_page must be at least 1")
        self.items = list(items)
        self.per_page = per_page

    def page_count(self):
        """How many pages the items fill."""
        return len(self.items) // self.per_page

    def page(self, number):
        """The items on page `number`, counting from `FIRST_PAGE`."""
        if number < FIRST_PAGE or number > self.page_count():
            raise IndexError(f"no page {number}")
        start, stop = bounds(number, self.per_page)
        return self.items[start:stop]
