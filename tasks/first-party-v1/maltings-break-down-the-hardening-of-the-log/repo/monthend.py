"""The month-end carry: a finished month summed for the ledger and lifted
out of the log.

The carry is the one working that touches the file whole: the month's lines
become one carried line, and the log is written back without them, so the
steward's file stays a working season and not an archive.
"""

import json
from pathlib import Path

import log


def carry(month: str, path: str | Path = log.LOG_FILE) -> dict[str, int]:
    """Sum one month ("1926-10") for the ledger and lift its lines out.

    The log is read here directly, line by line off the file itself, so the
    carry sees the file exactly as it stands on disk before rewriting it.
    """
    kept: list[log.Line] = []
    summed: dict[str, int] = {}
    log_path = Path(path)
    raw = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    for line in raw.splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if str(entry["day"]).startswith(month):
            working = entry["working"]
            summed[working] = summed.get(working, 0) + entry["quarters"]
        else:
            kept.append(entry)
    kept.append(
        {"day": f"{month}-99", "working": "carried", "quarters": 0, "place": 0,
         "summed": summed}
    )
    log.rewrite(kept, path)
    return summed
