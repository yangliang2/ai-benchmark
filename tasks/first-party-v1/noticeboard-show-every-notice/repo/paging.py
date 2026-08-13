"""Splitting a run of items into fixed-size pages."""


class Paginator:
    """A run of items, read one page at a time.

    Pages are numbered from 1. Every page but the last is full; the last one
    holds whatever is left over.
    """

    def __init__(self, items, per_page):
        if per_page < 1:
            raise ValueError("per_page must be at least 1")
        self.items = list(items)
        self.per_page = per_page

    def page_count(self):
        """How many pages the items fill."""
        return len(self.items) // self.per_page

    def page(self, number):
        """The items on page `number`, counting from 1."""
        if number < 1 or number > self.page_count():
            raise IndexError(f"no page {number}")
        start = (number - 1) * self.per_page
        return self.items[start:start + self.per_page]
