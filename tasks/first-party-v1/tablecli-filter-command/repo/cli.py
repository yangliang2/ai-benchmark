"""Command-line-style entry points over tabular text.

main(argv, text) runs one command against the table in text and returns the
command's output as a string.
"""

from tabular import parse


def main(argv, text):
    """Run one command against the table in text."""
    if not argv:
        raise ValueError("no command given")
    command = argv[0]
    if command == "columns":
        headers, _ = parse(text)
        return "\n".join(headers)
    if command == "count":
        _, rows = parse(text)
        return str(len(rows))
    raise ValueError(f"unknown command {command!r}")
