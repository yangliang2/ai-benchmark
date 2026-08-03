"""Queries over the unified dataset, and their text rendering."""

from collections import defaultdict

from ai_benchmark.schema import Record

# (agent, model, resolved count, total, rate), best rate first
CombinationRate = tuple[str, str, int, int, float]


def resolution_rates(records: list[Record]) -> list[CombinationRate]:
    per_combination: dict[tuple[str, str], list[float]] = defaultdict(list)
    for record in records:
        if record.quality_metric == "resolved" and record.source_type == "per-instance":
            per_combination[(record.agent, record.model)].append(record.quality_value)

    rates = [
        (agent, model, int(sum(values)), len(values), sum(values) / len(values))
        for (agent, model), values in per_combination.items()
    ]
    return sorted(rates, key=lambda row: (-row[4], row[0], row[1]))


def render_table(rates: list[CombinationRate]) -> str:
    header = ("agent", "model", "resolved", "total", "rate")
    rows = [
        (agent, model, str(resolved), str(total), f"{rate:.1%}")
        for agent, model, resolved, total, rate in rates
    ]
    widths = [
        max(len(header[column]), *(len(row[column]) for row in rows)) if rows else len(header[column])
        for column in range(len(header))
    ]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in [header, *rows]
    )
