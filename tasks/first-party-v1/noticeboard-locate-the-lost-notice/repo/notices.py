"""The notices themselves, and the order they are read in."""


class Notice:
    """One posted notice: what it says, and the day it went up."""

    def __init__(self, text, posted_on):
        self.text = text
        self.posted_on = posted_on

    def __repr__(self):
        return f"Notice({self.text!r}, {self.posted_on!r})"

    def __eq__(self, other):
        if not isinstance(other, Notice):
            return NotImplemented
        return (self.text, self.posted_on) == (other.text, other.posted_on)

    def __hash__(self):
        return hash((self.text, self.posted_on))


def newest_first(notices):
    """The notices, most recently posted first.

    Notices posted on the same day keep the order they were given in, which is
    the order they were handed to the office.
    """
    return sorted(notices, key=lambda notice: notice.posted_on, reverse=True)
