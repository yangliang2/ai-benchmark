"""Spending analysis over a stored expense file."""

import storage


def summarise(path):
    """Count, total and the single biggest expense of the file at path."""
    entries = storage.load_entries(path)
    total = sum(cents for _, cents in entries)
    biggest, _ = max(entries, key=lambda entry: entry[1])
    return {"count": len(entries), "total": total, "biggest": biggest}


def over_budget(path, budget_cents):
    """Names of the file's entries strictly over the budget, in file order."""
    entries = storage.load_entries(path)
    return [name for name, cents in entries if cents > budget_cents]
