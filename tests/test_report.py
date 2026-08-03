"""Dataset-seam tests: dataset in -> per-category Pareto points and static report out."""

from datetime import date
from pathlib import Path
from typing import get_args

from ai_benchmark.dataset import read_records
from ai_benchmark.report import pareto_points, render_report
from ai_benchmark.schema import Record, TaskCategory, validate_record


def _record(
    agent: str,
    metric: str,
    value: float,
    cost: float | None,
    instance_id: str = "a__a-1",
    benchmark: str = "swe-bench-verified",
) -> Record:
    return validate_record(
        {
            "category": "bug-fix",
            "scale": "unknown",
            "agent": agent,
            "model": "gpt-6",
            "benchmark": benchmark,
            "instance_id": instance_id,
            "quality_metric": metric,
            "quality_value": value,
            "cost_usd": cost,
            "source": "https://example.com",
            "source_type": "per-instance",
            "confidence": "medium",
            "as_of": "2026-01-01",
        }
    )


def test_pareto_frontier_from_dataset(pareto_fixture: Path) -> None:
    points = pareto_points(read_records(pareto_fixture))

    pooled = {p.agent: p for p in points["bug-fix"] if p.source_type == "per-instance"}
    # claude-code: rate 1.0 at mean cost 2.0 — best quality, on the frontier.
    assert pooled["claude-code"].quality_value == 1.0
    assert pooled["claude-code"].cost_usd == 2.0
    assert pooled["claude-code"].on_frontier
    # aider: rate 0.5 at cost 0.5 — cheapest, on the frontier.
    assert pooled["aider"].quality_value == 0.5
    assert pooled["aider"].on_frontier
    # cursor: rate 0.5 at cost 2.0 — same quality as aider for 4x the cost.
    assert not pooled["cursor"].on_frontier


def test_expected_frontier_set(pareto_fixture: Path) -> None:
    points = pareto_points(read_records(pareto_fixture))

    frontier = {
        (p.agent, p.source_type) for p in points["bug-fix"] if p.on_frontier
    }
    assert frontier == {
        ("claude-code", "per-instance"),
        ("aider", "per-instance"),
        # The published aggregate is the sole point of its own frontier group.
        ("claude-code", "aggregate"),
    }


def test_pooled_point_carries_counts_worst_confidence_and_latest_as_of(
    pareto_fixture: Path,
) -> None:
    points = pareto_points(read_records(pareto_fixture))

    pooled = {p.agent: p for p in points["bug-fix"] if p.source_type == "per-instance"}
    assert pooled["claude-code"].instances == 2
    assert pooled["claude-code"].as_of == date(2026, 2, 1)
    # aider's group mixes medium and low confidence records; the point is honest
    # about the weakest link.
    assert pooled["aider"].confidence == "low"
    assert pooled["claude-code"].confidence == "medium"


def test_aggregate_never_pools_or_competes_with_instance_level_records(
    pareto_fixture: Path,
) -> None:
    # claude-code x claude-sonnet-5 is measured both ways on swe-bench-verified
    # under the same metric: a published aggregate (0.7 at $2.00) and pooled
    # per-instance records (1.0 at $2.00). One point each, and the aggregate is
    # not knocked out by its better per-instance twin (ADR-0001: a combination
    # may appear both ways; neither is silently dropped).
    points = pareto_points(read_records(pareto_fixture))

    claude = [p for p in points["bug-fix"] if p.agent == "claude-code"]
    assert {p.source_type for p in claude} == {"per-instance", "aggregate"}
    [aggregate] = [p for p in claude if p.source_type == "aggregate"]
    assert aggregate.quality_value == 0.7
    assert aggregate.instances is None
    assert aggregate.on_frontier


def test_every_taxonomy_category_is_present_even_when_empty(
    pareto_fixture: Path,
) -> None:
    points = pareto_points(read_records(pareto_fixture))

    assert set(points) == set(get_args(TaskCategory))
    assert points["refactor"] == []  # an empty matrix cell, visible as such


def test_uncosted_combination_stays_visible_but_never_on_frontier(
    pareto_fixture: Path,
) -> None:
    points = pareto_points(read_records(pareto_fixture))

    [openhands] = [p for p in points["bug-fix"] if p.agent == "openhands"]
    assert openhands.cost_usd is None
    assert not openhands.on_frontier


def test_aggregate_passes_through_under_its_own_metric(pareto_fixture: Path) -> None:
    points = pareto_points(read_records(pareto_fixture))

    [aggregate] = points["unclassified"]
    assert aggregate.quality_metric == "pass-rate-2"
    assert aggregate.quality_value == 0.88
    assert aggregate.instances is None
    assert aggregate.source_type == "aggregate"
    assert aggregate.confidence == "low"
    assert aggregate.on_frontier  # the only costed point of its frontier group


def test_frontier_never_mixes_quality_metrics() -> None:
    # Under a shared frontier, b would dominate a (better value, lower cost).
    # The metrics differ, so each is the sole — undominated — point of its own.
    records = [
        _record("a", "resolved", 0.5, 2.0),
        _record("b", "edit-accuracy", 0.9, 1.0),
    ]

    points = pareto_points(records)

    assert all(p.on_frontier for p in points["bug-fix"])


def test_frontier_never_mixes_benchmarks() -> None:
    # Same metric name on two benchmarks means two different task pools; the
    # cheap-and-good point on one must not dominate the other.
    records = [
        _record("a", "resolved", 0.9, 1.0, benchmark="bench-easy"),
        _record("b", "resolved", 0.4, 5.0, benchmark="bench-hard"),
    ]

    points = pareto_points(records)

    assert all(p.on_frontier for p in points["bug-fix"])


def test_partial_cost_coverage_is_marked_not_averaged_away() -> None:
    records = [
        _record("a", "resolved", 1.0, 0.1, instance_id="a__a-1"),
        _record("a", "resolved", 1.0, None, instance_id="a__a-2"),
    ]

    points = pareto_points(records)
    [point] = points["bug-fix"]
    assert point.instances == 2
    assert point.costed_instances == 1

    html = render_report(points)
    assert "cost from 1/2" in html


def test_zero_cost_records_still_render() -> None:
    records = [_record("a", "resolved", 1.0, 0.0)]

    html = render_report(pareto_points(records))

    assert "<svg" in html


def test_out_of_range_quality_is_flagged_not_plotted_off_canvas() -> None:
    # A percentage-style metric (88 rather than 0.88) must not vanish off the
    # 0-100% axis; it is flagged like an uncosted point instead.
    records = [_record("a", "accuracy-pct", 88.0, 1.0)]

    html = render_report(pareto_points(records))

    assert "quality value outside 0–1" in html
    assert "<circle" not in html


def test_report_marks_frontier_gaps_and_as_of_dates(pareto_fixture: Path) -> None:
    html = render_report(pareto_points(read_records(pareto_fixture)))

    # Frontier and dominated points are visually distinguishable.
    assert 'class="point frontier"' in html
    assert 'class="point dominated"' in html
    # Empty categories appear as gaps, not silent omissions.
    assert "refactor" in html and "No data" in html
    # Within a populated category, unmeasured combinations are visible gaps too.
    assert "Not measured in this category" in html
    # Uncosted combinations are flagged rather than silently unplotted.
    assert "no cost data" in html
    # Provenance and as-of dates are stated.
    assert "aider.chat" in html
    assert "2026-02-01" in html and "2026-01-10" in html
