"""Readers for "YYYY-MM-DD HH:MM:SS LEVEL message" log lines."""

from datetime import datetime


def parse_stamp(line):
    """The parsed timestamp of one log line, and the rest of the line."""
    moment = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
    return moment, line[20:]


def entry_level(line):
    """The level token of one log line."""
    _, rest = parse_stamp(line)
    return rest.split(" ", 1)[0]


def entry_message(line):
    """The message of one log line, exactly as written after the level."""
    _, rest = parse_stamp(line)
    return rest.split(" ", 1)[1]


def entries_between(lines, start, end):
    """The remainder of every line whose timestamp falls in [start, end]."""
    kept = []
    for line in lines:
        moment, rest = parse_stamp(line)
        if start <= moment <= end:
            kept.append(rest)
    return kept
