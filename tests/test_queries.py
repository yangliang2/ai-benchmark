"""Dataset-seam tests: checked-in dataset in -> resolution-rate table out."""

from datetime import date
from pathlib import Path

from ai_benchmark.dataset import read_records
from ai_benchmark.queries import (
    CategoryRate,
    CombinationRate,
    category_rates,
    render_category_table,
    render_table,
    resolution_rates,
)


def test_resolution_rates_group_by_benchmark_and_combination(
    dataset_fixture: Path,
) -> None:
    records = read_records(dataset_fixture)

    rates = resolution_rates(records)

    assert rates == [
        CombinationRate(
            benchmark="polyglot-bench",
            agent="claude-code",
            model="claude-sonnet-5",
            resolved=1,
            total=1,
            rate=1.0,
            as_of=date(2026, 3, 1),
        ),
        CombinationRate(
            benchmark="swe-bench-verified",
            agent="claude-code",
            model="claude-sonnet-5",
            resolved=1,
            total=2,
            rate=0.5,
            as_of=date(2026, 1, 15),
        ),
    ]


def test_aggregate_records_are_not_pooled_into_per_instance_rates(
    dataset_fixture: Path,
) -> None:
    records = read_records(dataset_fixture)

    rates = resolution_rates(records)

    assert not any(row.agent == "aider" for row in rates)


def test_category_rates_group_by_category_and_combination(
    classified_fixture: Path,
) -> None:
    records = read_records(classified_fixture)

    rates = category_rates(records)

    assert rates == [
        CategoryRate(
            benchmark="swe-bench-verified",
            category="bug-fix",
            agent="claude-code",
            model="claude-sonnet-5",
            resolved=1,
            total=2,
            rate=0.5,
            as_of=date(2026, 1, 15),
        ),
        CategoryRate(
            benchmark="swe-bench-verified",
            category="bug-fix",
            agent="aider",
            model="gpt-6",
            resolved=0,
            total=1,
            rate=0.0,
            as_of=date(2026, 1, 15),
        ),
        CategoryRate(
            benchmark="swe-bench-verified",
            category="feature-dev",
            agent="claude-code",
            model="claude-sonnet-5",
            resolved=1,
            total=1,
            rate=1.0,
            as_of=date(2026, 1, 20),
        ),
        CategoryRate(
            benchmark="swe-bench-verified",
            category="unclassified",
            agent="aider",
            model="gpt-6",
            resolved=1,
            total=1,
            rate=1.0,
            as_of=date(2026, 1, 15),
        ),
    ]


def test_unclassified_stays_visible_in_the_category_table(
    classified_fixture: Path,
) -> None:
    records = read_records(classified_fixture)

    table = render_category_table(category_rates(records))

    assert "category" in table.splitlines()[0]
    assert "unclassified" in table


def test_rendered_table_shows_benchmark_rate_and_as_of(dataset_fixture: Path) -> None:
    records = read_records(dataset_fixture)

    table = render_table(resolution_rates(records))

    lines = table.splitlines()
    header = lines[0]
    assert "benchmark" in header and "rate" in header and "as-of" in header
    assert "polyglot-bench" in lines[1] and "100.0%" in lines[1] and "2026-03-01" in lines[1]
    assert "swe-bench-verified" in lines[2] and "50.0%" in lines[2] and "2026-01-15" in lines[2]
