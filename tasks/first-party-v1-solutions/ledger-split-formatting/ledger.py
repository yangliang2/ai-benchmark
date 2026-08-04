"""A tiny expense ledger."""

from formatting import format_line


class Ledger:
    """An ordered list of (description, cents) entries."""

    def __init__(self):
        self.entries = []

    def add(self, description, cents):
        """Append one entry."""
        self.entries.append((description, cents))

    def total(self):
        """The sum of every entry's amount, in cents."""
        return sum(cents for _, cents in self.entries)

    def render(self):
        """Render every entry, then a total line."""
        lines = [format_line(description, cents) for description, cents in self.entries]
        lines.append(format_line("total", self.total()))
        return "\n".join(lines)
