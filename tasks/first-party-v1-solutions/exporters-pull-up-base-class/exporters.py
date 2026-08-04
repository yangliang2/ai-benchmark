"""Row exporters: shared bookkeeping on one base, one output format each."""


class Exporter:
    """The bookkeeping every exporter shares: columns, rows, validation."""

    def __init__(self, columns):
        if not columns:
            raise ValueError("at least one column is required")
        self.columns = list(columns)
        self.rows = []

    def add(self, row):
        """Append one row, coercing every cell to text."""
        if len(row) != len(self.columns):
            raise ValueError(f"expected {len(self.columns)} cells, got {len(row)}")
        self.rows.append([str(cell) for cell in row])

    def count(self):
        """How many rows have been added."""
        return len(self.rows)


class TableExporter(Exporter):
    """Rows rendered as an aligned text table."""

    def export(self):
        """The header and every row, columns aligned by width."""
        widths = [
            max(len(text) for text in [column, *(row[i] for row in self.rows)])
            for i, column in enumerate(self.columns)
        ]
        lines = []
        for cells in [self.columns, *self.rows]:
            padded = (cell.ljust(width) for cell, width in zip(cells, widths))
            lines.append("  ".join(padded).rstrip())
        return "\n".join(lines)


class DelimitedExporter(Exporter):
    """Rows rendered one per line, cells joined with a delimiter."""

    def __init__(self, columns, delimiter=";"):
        super().__init__(columns)
        self.delimiter = delimiter

    def export(self):
        """The header and every row, cells joined by the delimiter."""
        lines = [self.delimiter.join(self.columns)]
        lines.extend(self.delimiter.join(row) for row in self.rows)
        return "\n".join(lines)
