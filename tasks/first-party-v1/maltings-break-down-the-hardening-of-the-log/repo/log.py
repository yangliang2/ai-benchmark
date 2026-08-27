"""The steep-house log: one JSON object a line, appended as the house works.

The log carries one thing: a line per working, in the order the steward
took them down. A line is written once and never edited; the month-end
carry is the only thing that ever writes the file as a whole.
"""

import json
from pathlib import Path
from typing import Any

LOG_FILE = "steeplog.jsonl"

Line = dict[str, Any]


def read(path: str | Path = LOG_FILE) -> list[Line]:
    """Every line of the log, in the order it was worked. A missing file is
    a season not yet begun."""
    log_path = Path(path)
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append(entry: Line, path: str | Path = LOG_FILE) -> None:
    """One line onto the end of the log, the file otherwise untouched."""
    with Path(path).open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")


def rewrite(entries: list[Line], path: str | Path = LOG_FILE) -> None:
    """Write the log afresh: the file whole, in place, from these lines."""
    with Path(path).open("w", encoding="utf-8") as log_file:
        for entry in entries:
            log_file.write(json.dumps(entry) + "\n")
