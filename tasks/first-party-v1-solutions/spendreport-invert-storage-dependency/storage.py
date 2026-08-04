"""Reading expense entries from disk."""

from pathlib import Path


def load_entries(path):
    """Entries of a "name,cents" per-line file, as a list of (name, cents)."""
    entries = []
    for number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        name, _, amount = line.partition(",")
        if not name or not amount.strip().lstrip("-").isdigit():
            raise ValueError(f"line {number}: expected 'name,cents', got {line!r}")
        entries.append((name, int(amount)))
    return entries
