"""Per-category Pareto frontier over the unified dataset, and its static report.

The frontier (CONTEXT.md) is computed within one task category AND one quality
metric — values under different quality metrics are never directly comparable
(ADR-0001). Combinations without cost data can never sit on a quality-vs-cost
frontier; they stay visible as flagged gaps, as do empty categories.
"""

import math
from collections import defaultdict
from datetime import date
from html import escape
from typing import NamedTuple, get_args

from ai_benchmark.schema import Confidence, Record, SourceType, TaskCategory

_CONFIDENCE_ORDER: dict[Confidence, int] = {"low": 0, "medium": 1, "high": 2}


class ParetoPoint(NamedTuple):
    benchmark: str
    agent: str
    model: str
    quality_metric: str
    quality_value: float  # pooled mean for instance-level records; as published for aggregates
    cost_usd: float | None  # mean USD/instance over the records that carry cost
    instances: int | None  # pooled group size; None for aggregate pass-throughs
    source_type: SourceType
    confidence: Confidence  # weakest confidence among the pooled records
    as_of: date  # latest as-of among the pooled records
    on_frontier: bool


def pareto_points(records: list[Record]) -> dict[TaskCategory, list[ParetoPoint]]:
    """Every taxonomy category is present as a key — an empty list is an empty
    capability-matrix cell, shown as a gap rather than omitted."""
    # Aggregates never pool with instance-level records for the same combination
    # and metric — one is a published rate, the other a set of 0/1 outcomes.
    pooled: dict[tuple[TaskCategory, str, str, str, str, bool], list[Record]] = (
        defaultdict(list)
    )
    for record in records:
        pooled[
            (record.category, record.benchmark, record.agent, record.model,
             record.quality_metric, record.source_type == "aggregate")
        ].append(record)

    draft: dict[TaskCategory, list[ParetoPoint]] = {
        category: [] for category in get_args(TaskCategory)
    }
    for (category, benchmark, agent, model, metric, _), group in pooled.items():
        draft[category].append(_point(benchmark, agent, model, metric, group))

    return {
        category: sorted(_flag_frontier(points), key=_point_order)
        for category, points in draft.items()
    }


def _point(
    benchmark: str, agent: str, model: str, metric: str, group: list[Record]
) -> ParetoPoint:
    # Aggregates pass through as published; instance-level records pool to a mean.
    is_aggregate = all(r.source_type == "aggregate" for r in group)
    source_types = {r.source_type for r in group}
    costs = [r.cost_usd for r in group if r.cost_usd is not None]
    return ParetoPoint(
        benchmark=benchmark,
        agent=agent,
        model=model,
        quality_metric=metric,
        quality_value=sum(r.quality_value for r in group) / len(group),
        cost_usd=sum(costs) / len(costs) if costs else None,
        instances=None if is_aggregate else len(group),
        source_type=source_types.pop() if len(source_types) == 1 else "per-instance",
        confidence=min((r.confidence for r in group), key=_CONFIDENCE_ORDER.__getitem__),
        as_of=max(r.as_of for r in group),
        on_frontier=False,
    )


def _flag_frontier(points: list[ParetoPoint]) -> list[ParetoPoint]:
    by_metric: dict[str, list[ParetoPoint]] = defaultdict(list)
    for point in points:
        by_metric[point.quality_metric].append(point)

    flagged: list[ParetoPoint] = []
    for metric_points in by_metric.values():
        costed = [
            (p.quality_value, p.cost_usd)
            for p in metric_points
            if p.cost_usd is not None
        ]
        flagged.extend(
            p._replace(
                on_frontier=p.cost_usd is not None
                and not _dominated(p.quality_value, p.cost_usd, costed)
            )
            for p in metric_points
        )
    return flagged


def _dominated(quality: float, cost: float, others: list[tuple[float, float]]) -> bool:
    return any(
        q >= quality and c <= cost and (q > quality or c < cost) for q, c in others
    )


def _point_order(p: ParetoPoint) -> tuple[str, float, bool, float, str, str, str]:
    return (
        p.quality_metric, -p.quality_value,
        p.cost_usd is None, p.cost_usd or 0.0,
        p.benchmark, p.agent, p.model,
    )


# --- static report rendering -------------------------------------------------

_CHART_W, _CHART_H = 640, 340
_MARGIN_L, _MARGIN_R, _MARGIN_T, _MARGIN_B = 56, 168, 16, 44

_STYLE = """
:root { color-scheme: light dark; }
body {
  --surface-1: #fcfcfb; --page: #f9f9f7;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7;
  --frontier: #2a78d6; --dominated: #898781;
  margin: 0; padding: 2rem 1rem; background: var(--page); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  body {
    --surface-1: #1a1a19; --page: #0d0d0d;
    --ink: #ffffff; --ink-2: #c3c2b7;
    --grid: #2c2c2a; --axis: #383835;
    --frontier: #3987e5;
  }
}
main { max-width: 60rem; margin: 0 auto; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.1rem; margin-top: 2.5rem; }
.subtitle, .gap, .note { color: var(--ink-2); }
.gap { border: 1px dashed var(--axis); border-radius: 6px; padding: .75rem 1rem; }
figure { margin: 1rem 0; background: var(--surface-1); border-radius: 8px;
         padding: 1rem; border: 1px solid var(--grid); }
figcaption { color: var(--ink-2); font-size: .9rem; margin-bottom: .5rem; }
.legend { display: flex; gap: 1.25rem; font-size: .85rem; color: var(--ink-2);
          margin: .25rem 0 .5rem; }
.legend .swatch { display: inline-block; width: 10px; height: 10px;
                  border-radius: 50%; margin-right: .4rem; }
svg { max-width: 100%; height: auto; display: block; }
.point.frontier { fill: var(--frontier); }
.point.dominated { fill: var(--dominated); }
.frontier-line { stroke: var(--frontier); stroke-width: 2; fill: none;
                 stroke-linejoin: round; stroke-linecap: round; }
.gridline { stroke: var(--grid); stroke-width: 1; }
.axis-line { stroke: var(--axis); stroke-width: 1; }
.tick, .axis-title { fill: var(--muted); font-size: 11px; }
.point-label { fill: var(--ink-2); font-size: 11px; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin: .75rem 0; }
th, td { text-align: left; padding: .35rem .6rem;
         border-bottom: 1px solid var(--grid); }
th { color: var(--ink-2); font-weight: 600; }
td.num { font-variant-numeric: tabular-nums; }
"""


def render_report(by_category: dict[TaskCategory, list[ParetoPoint]]) -> str:
    all_points = [p for points in by_category.values() for p in points]
    if all_points:
        dates = sorted({p.as_of for p in all_points})
        as_of = (
            f"data as of {dates[0].isoformat()}"
            if len(dates) == 1
            else f"data as of {dates[0].isoformat()} to {dates[-1].isoformat()}"
        )
    else:
        as_of = "no data ingested yet"

    sections = "\n".join(
        _category_section(category, points)
        for category, points in by_category.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pareto frontier per task category</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
<h1>Quality vs cost — Pareto frontier per task category</h1>
<p class="subtitle">Each point is an agent × model combination; {escape(as_of)}.
Frontiers are computed within one category and one quality metric —
values under different metrics are never directly comparable.</p>
{sections}
</main>
</body>
</html>
"""


def _category_section(category: TaskCategory, points: list[ParetoPoint]) -> str:
    if not points:
        return (
            f"<section>\n<h2>{escape(category)}</h2>\n"
            '<p class="gap">No data — this capability-matrix cell is empty.</p>\n'
            "</section>"
        )

    by_metric: dict[str, list[ParetoPoint]] = defaultdict(list)
    for point in points:
        by_metric[point.quality_metric].append(point)

    figures = "\n".join(
        _metric_figure(category, metric, metric_points)
        for metric, metric_points in by_metric.items()
    )
    return (
        f"<section>\n<h2>{escape(category)}</h2>\n{figures}\n"
        f"{_points_table(points)}\n</section>"
    )


def _metric_figure(
    category: TaskCategory, metric: str, points: list[ParetoPoint]
) -> str:
    costed = [p for p in points if p.cost_usd is not None]
    uncosted = [p for p in points if p.cost_usd is None]

    parts = [f'<figure>\n<figcaption>{escape(metric)}, quality vs USD per instance'
             f" (as of {max(p.as_of for p in points).isoformat()})</figcaption>"]
    if costed:
        parts.append(
            '<div class="legend">'
            '<span><span class="swatch" style="background:var(--frontier)"></span>'
            "on the frontier</span>"
            '<span><span class="swatch" style="background:var(--dominated)"></span>'
            "dominated</span></div>"
        )
        parts.append(_chart_svg(costed))
    else:
        parts.append(
            '<p class="gap">No chart — no combination in this cell has cost data.</p>'
        )
    if uncosted:
        combos = ", ".join(f"{escape(p.agent)} × {escape(p.model)}" for p in uncosted)
        parts.append(
            f'<p class="note">Not chartable (no cost data): {combos}.</p>'
        )
    parts.append("</figure>")
    return "\n".join(parts)


def _x(cost: float, x_max: float) -> float:
    plot_w = _CHART_W - _MARGIN_L - _MARGIN_R
    return _MARGIN_L + (cost / x_max) * plot_w


def _y(quality: float) -> float:
    plot_h = _CHART_H - _MARGIN_T - _MARGIN_B
    return _MARGIN_T + (1 - quality) * plot_h


def _nice_step(raw: float) -> float:
    magnitude = 10.0 ** math.floor(math.log10(raw))
    return next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)


def _chart_svg(costed: list[ParetoPoint]) -> str:
    assert all(p.cost_usd is not None for p in costed)
    # Clean x ticks: a nice step size, extended one step past the dearest point.
    step = _nice_step(max(p.cost_usd or 0.0 for p in costed) * 1.05 / 4 or 0.25)
    ticks = math.ceil(max(p.cost_usd or 0.0 for p in costed) * 1.05 / step)
    x_max = step * ticks

    parts = [
        f'<svg viewBox="0 0 {_CHART_W} {_CHART_H}" role="img" '
        'aria-label="Pareto chart of quality versus cost">'
    ]

    # Gridlines and ticks: quality 0-100% on y, cost USD on x.
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = _y(fraction)
        parts.append(
            f'<line class="gridline" x1="{_MARGIN_L}" y1="{y:.1f}" '
            f'x2="{_CHART_W - _MARGIN_R}" y2="{y:.1f}"/>'
            f'<text class="tick" x="{_MARGIN_L - 8}" y="{y + 4:.1f}" '
            f'text-anchor="end">{fraction:.0%}</text>'
        )
    for tick in range(ticks + 1):
        cost = step * tick
        x = _x(cost, x_max)
        parts.append(
            f'<line class="gridline" x1="{x:.1f}" y1="{_MARGIN_T}" '
            f'x2="{x:.1f}" y2="{_CHART_H - _MARGIN_B}"/>'
            f'<text class="tick" x="{x:.1f}" y="{_CHART_H - _MARGIN_B + 16}" '
            f'text-anchor="middle">${cost:,.2f}</text>'
        )
    parts.append(
        f'<line class="axis-line" x1="{_MARGIN_L}" y1="{_CHART_H - _MARGIN_B}" '
        f'x2="{_CHART_W - _MARGIN_R}" y2="{_CHART_H - _MARGIN_B}"/>'
        f'<text class="axis-title" x="{(_MARGIN_L + _CHART_W - _MARGIN_R) / 2:.0f}" '
        f'y="{_CHART_H - 8}" text-anchor="middle">cost, USD per instance</text>'
    )

    # The frontier staircase: right along a quality level, then up to the next
    # (cost-ascending) frontier point.
    frontier = sorted(
        (p for p in costed if p.on_frontier), key=lambda p: p.cost_usd or 0.0
    )
    if len(frontier) > 1:
        steps = [f"{_x(frontier[0].cost_usd or 0.0, x_max):.1f},{_y(frontier[0].quality_value):.1f}"]
        for prev, nxt in zip(frontier, frontier[1:]):
            x_next = _x(nxt.cost_usd or 0.0, x_max)
            steps.append(f"{x_next:.1f},{_y(prev.quality_value):.1f}")
            steps.append(f"{x_next:.1f},{_y(nxt.quality_value):.1f}")
        parts.append(f'<polyline class="frontier-line" points="{" ".join(steps)}"/>')

    # Dominated marks under frontier marks; every mark gets a native tooltip,
    # only frontier points get a direct label (selective labeling).
    for p in sorted(costed, key=lambda p: p.on_frontier):
        x, y = _x(p.cost_usd or 0.0, x_max), _y(p.quality_value)
        kind = "frontier" if p.on_frontier else "dominated"
        n = f"n={p.instances}" if p.instances is not None else "aggregate"
        tooltip = escape(
            f"{p.agent} × {p.model} ({p.benchmark}): {p.quality_value:.1%} "
            f"{p.quality_metric} at ${p.cost_usd or 0.0:,.2f}/inst "
            f"({n}, {p.confidence} confidence, as of {p.as_of.isoformat()})"
        )
        radius = 5 if p.on_frontier else 4
        parts.append(
            f'<circle class="point {kind}" cx="{x:.1f}" cy="{y:.1f}" r="{radius}" '
            f'stroke="var(--surface-1)" stroke-width="2"><title>{tooltip}</title></circle>'
        )
        if p.on_frontier:
            # Above and to the right of the mark, clear of the staircase line.
            label = escape(f"{p.agent} × {p.model}")
            parts.append(
                f'<text class="point-label" x="{x + 9:.1f}" y="{y - 7:.1f}" '
                f'text-anchor="start">{label}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def _points_table(points: list[ParetoPoint]) -> str:
    header = (
        "<tr><th>frontier</th><th>benchmark</th><th>agent</th><th>model</th>"
        "<th>metric</th><th>value</th><th>cost/inst</th><th>n</th>"
        "<th>source-type</th><th>confidence</th><th>as-of</th></tr>"
    )
    rows = "\n".join(
        "<tr>"
        f"<td>{'◆' if p.on_frontier else ''}</td>"
        f"<td>{escape(p.benchmark)}</td><td>{escape(p.agent)}</td>"
        f"<td>{escape(p.model)}</td><td>{escape(p.quality_metric)}</td>"
        f'<td class="num">{p.quality_value:.1%}</td>'
        f'<td class="num">{f"${p.cost_usd:,.2f}" if p.cost_usd is not None else "no cost data"}</td>'
        f'<td class="num">{p.instances if p.instances is not None else "—"}</td>'
        f"<td>{escape(p.source_type)}</td><td>{escape(p.confidence)}</td>"
        f'<td class="num">{p.as_of.isoformat()}</td>'
        "</tr>"
        for p in points
    )
    return f"<table>\n{header}\n{rows}\n</table>"
