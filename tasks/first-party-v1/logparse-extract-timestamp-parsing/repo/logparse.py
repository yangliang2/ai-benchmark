"""Readers for "YYYY-MM-DD HH:MM:SS LEVEL message" log lines."""

from datetime import datetime


def entry_level(line):
    """The level token of one log line."""
    datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
    rest = line[20:]
    return rest.split(" ", 1)[0]


def entry_message(line):
    """The message of one log line, exactly as written after the level."""
    datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
    rest = line[20:]
    return rest.split(" ", 1)[1]


def entries_between(lines, start, end):
    """The remainder of every line whose timestamp falls in [start, end]."""
    kept = []
    for line in lines:
        moment = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
        rest = line[20:]
        if start <= moment <= end:
            kept.append(rest)
    return kept
