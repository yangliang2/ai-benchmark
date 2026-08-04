"""Plain-text tables: a header line, then one comma-separated row per line."""

_OPERATORS = ("<=", ">=", "!=", "=", "<", ">")


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


def matches(row, condition):
    """Whether row satisfies a <column><operator><value> condition."""
    column, operator, value = _split_condition(condition)
    if column not in row:
        raise ValueError(f"no column {column!r}")
    cell = row[column]
    if operator == "=":
        return cell == value
    if operator == "!=":
        return cell != value
    left, right = _number(cell), _number(value)
    if operator == ">":
        return left > right
    if operator == "<":
        return left < right
    if operator == ">=":
        return left >= right
    return left <= right


def _split_condition(condition):
    """Split a condition at its operator, longest operators first so ">="
    is never misread as ">"."""
    for index in range(len(condition)):
        for operator in _OPERATORS:
            if condition.startswith(operator, index):
                column = condition[:index].strip()
                value = condition[index + len(operator):].strip()
                if not column:
                    raise ValueError(f"condition {condition!r} has no column")
                return column, operator, value
    raise ValueError(f"condition {condition!r} has no operator")


def _number(text):
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{text!r} is not a number") from None
