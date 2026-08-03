"""Queries over the unified dataset, and their text rendering."""

from collections import defaultdict
from datetime import date
from typing import NamedTuple

from ai_benchmark.schema import Record


class CombinationRate(NamedTuple):
    benchmark: str
    agent: str
    model: str
    resolved: int
    total: int
    rate: float
    as_of: date  # latest as-of date among the combination's records


def resolution_rates(records: list[Record]) -> list[CombinationRate]:
    """Per-instance resolution rate per benchmark x combination, best rate first
    within each benchmark. Aggregate records are never pooled in (they would
    double-count; see ADR-0001)."""
    groups: dict[tuple[str, str, str], list[Record]] = defaultdict(list)
    for record in records:
        if record.quality_metric == "resolved" and record.source_type == "per-instance":
            groups[(record.benchmark, record.agent, record.model)].append(record)

    rates = [
        CombinationRate(
            benchmark=benchmark,
            agent=agent,
            model=model,
            resolved=int(sum(r.quality_value for r in group)),
            total=len(group),
            rate=sum(r.quality_value for r in group) / len(group),
            as_of=max(r.as_of for r in group),
        )
        for (benchmark, agent, model), group in groups.items()
    ]
    return sorted(rates, key=lambda row: (row.benchmark, -row.rate, row.agent, row.model))


def render_table(rates: list[CombinationRate]) -> str:
    header = ("benchmark", "agent", "model", "resolved", "total", "rate", "as-of")
    rows = [
        (
            row.benchmark,
            row.agent,
            row.model,
            str(row.resolved),
            str(row.total),
            f"{row.rate:.1%}",
            row.as_of.isoformat(),
        )
        for row in rates
    ]
    widths = [
        max(len(column_cell) for column_cell in column)
        for column in zip(header, *rows)
    ]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in [header, *rows]
    )
