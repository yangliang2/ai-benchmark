"""Queries over the unified dataset, and their text rendering."""

from collections import defaultdict
from datetime import date
from typing import NamedTuple

from ai_benchmark.schema import Record, TaskCategory


class CombinationRate(NamedTuple):
    benchmark: str
    agent: str
    model: str
    resolved: int
    total: int
    rate: float
    cost_usd: float | None  # mean cost per instance; None when no record has cost
    as_of: date  # latest as-of date among the combination's records


class CategoryRate(NamedTuple):
    benchmark: str
    category: TaskCategory
    agent: str
    model: str
    resolved: int
    total: int
    rate: float
    as_of: date


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
            cost_usd=_mean_cost(group),
            as_of=max(r.as_of for r in group),
        )
        for (benchmark, agent, model), group in groups.items()
    ]
    return sorted(rates, key=lambda row: (row.benchmark, -row.rate, row.agent, row.model))


def _mean_cost(group: list[Record]) -> float | None:
    costs = [r.cost_usd for r in group if r.cost_usd is not None]
    return sum(costs) / len(costs) if costs else None


class AggregateRow(NamedTuple):
    benchmark: str
    agent: str
    model: str
    metric: str
    value: float
    cost_usd: float | None
    latency_s: float | None
    as_of: date


def aggregate_rows(records: list[Record]) -> list[AggregateRow]:
    """Aggregate records shown as published — never pooled into per-instance
    rates (double counting; ADR-0001), but never hidden either."""
    rows = [
        AggregateRow(
            benchmark=r.benchmark,
            agent=r.agent,
            model=r.model,
            metric=r.quality_metric,
            value=r.quality_value,
            cost_usd=r.cost_usd,
            latency_s=r.latency_s,
            as_of=r.as_of,
        )
        for r in records
        if r.source_type == "aggregate"
    ]
    return sorted(rows, key=lambda row: (row.benchmark, row.agent, row.model, row.metric))


def category_rates(records: list[Record]) -> list[CategoryRate]:
    """Like resolution_rates, additionally grouped by task category. Records
    still unclassified appear under their own "unclassified" rows — the count
    stays visible rather than being dropped."""
    groups: dict[tuple[str, TaskCategory, str, str], list[Record]] = defaultdict(list)
    for record in records:
        if record.quality_metric == "resolved" and record.source_type == "per-instance":
            groups[
                (record.benchmark, record.category, record.agent, record.model)
            ].append(record)

    rates = [
        CategoryRate(
            benchmark=benchmark,
            category=category,
            agent=agent,
            model=model,
            resolved=int(sum(r.quality_value for r in group)),
            total=len(group),
            rate=sum(r.quality_value for r in group) / len(group),
            as_of=max(r.as_of for r in group),
        )
        for (benchmark, category, agent, model), group in groups.items()
    ]
    return sorted(
        rates, key=lambda row: (row.benchmark, row.category, -row.rate, row.agent, row.model)
    )


def _render(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    widths = [
        max(len(column_cell) for column_cell in column)
        for column in zip(header, *rows)
    ]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in [header, *rows]
    )


def _money(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "-"


def render_table(rates: list[CombinationRate]) -> str:
    return _render(
        ("benchmark", "agent", "model", "resolved", "total", "rate", "cost/inst", "as-of"),
        [
            (
                row.benchmark,
                row.agent,
                row.model,
                str(row.resolved),
                str(row.total),
                f"{row.rate:.1%}",
                _money(row.cost_usd),
                row.as_of.isoformat(),
            )
            for row in rates
        ],
    )


def render_aggregate_table(rows: list[AggregateRow]) -> str:
    return _render(
        ("benchmark", "agent", "model", "metric", "value", "cost", "latency-s", "as-of"),
        [
            (
                row.benchmark,
                row.agent,
                row.model,
                row.metric,
                f"{row.value:g}",
                _money(row.cost_usd),
                f"{row.latency_s:.1f}" if row.latency_s is not None else "-",
                row.as_of.isoformat(),
            )
            for row in rows
        ],
    )


def render_category_table(rates: list[CategoryRate]) -> str:
    return _render(
        ("benchmark", "category", "agent", "model", "resolved", "total", "rate", "as-of"),
        [
            (
                row.benchmark,
                row.category,
                row.agent,
                row.model,
                str(row.resolved),
                str(row.total),
                f"{row.rate:.1%}",
                row.as_of.isoformat(),
            )
            for row in rates
        ],
    )
