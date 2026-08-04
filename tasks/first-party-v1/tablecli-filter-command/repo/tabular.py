"""Plain-text tables: a header line, then one comma-separated row per line."""


def parse(text):
    """Parse text into (headers, rows): the column names in order, and one
    dict per row mapping column name to the cell text."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], []
    headers = [cell.strip() for cell in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split(",")]
        if len(cells) != len(headers):
            raise ValueError(
                f"row {line!r} has {len(cells)} cells, expected {len(headers)}"
            )
        rows.append(dict(zip(headers, cells)))
    return headers, rows


def render(headers, rows):
    """Render headers and rows back to comma-separated text."""
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row[header] for header in headers))
    return "\n".join(lines)
