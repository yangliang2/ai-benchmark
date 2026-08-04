"""The spending report the command-line tool prints."""

from analysis import over_budget, summarise


def report(path, budget_cents):
    """The full report for one expense file."""
    stats = summarise(path)
    lines = [
        f"entries: {stats['count']}",
        f"total: {stats['total']}",
        f"biggest: {stats['biggest']}",
    ]
    for name in over_budget(path, budget_cents):
        lines.append(f"over budget: {name}")
    return "\n".join(lines)
