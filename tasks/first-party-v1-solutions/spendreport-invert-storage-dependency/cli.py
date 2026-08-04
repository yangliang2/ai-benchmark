"""The spending report the command-line tool prints."""

from analysis import over_budget, summarise
from storage import load_entries


def report(path, budget_cents):
    """The full report for one expense file."""
    entries = load_entries(path)
    stats = summarise(entries)
    lines = [
        f"entries: {stats['count']}",
        f"total: {stats['total']}",
        f"biggest: {stats['biggest']}",
    ]
    for name in over_budget(entries, budget_cents):
        lines.append(f"over budget: {name}")
    return "\n".join(lines)
