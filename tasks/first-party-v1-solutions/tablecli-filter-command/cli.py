"""Command-line-style entry points over tabular text.

main(argv, text) runs one command against the table in text and returns the
command's output as a string.
"""

from tabular import matches, parse, render


def main(argv, text):
    """Run one command against the table in text."""
    if not argv:
        raise ValueError("no command given")
    command, arguments = argv[0], argv[1:]
    if command == "columns":
        headers, _ = parse(text)
        return "\n".join(headers)
    if command == "count":
        _, rows = parse(text)
        return str(len(rows))
    if command == "filter":
        if not arguments:
            raise ValueError("filter needs at least one condition")
        headers, rows = parse(text)
        kept = [
            row
            for row in rows
            if all(matches(row, condition) for condition in arguments)
        ]
        return render(headers, kept)
    raise ValueError(f"unknown command {command!r}")
