"""Spending analysis over loaded expense entries."""


def summarise(entries):
    """Count, total and the single biggest expense of the entries."""
    total = sum(cents for _, cents in entries)
    biggest, _ = max(entries, key=lambda entry: entry[1])
    return {"count": len(entries), "total": total, "biggest": biggest}


def over_budget(entries, budget_cents):
    """Names of the entries strictly over the budget, in order."""
    return [name for name, cents in entries if cents > budget_cents]
