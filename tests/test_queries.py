"""Dataset-seam tests: dataset in -> resolution-rate table out."""

from pathlib import Path

from ai_benchmark.queries import render_table, resolution_rates
from ai_benchmark.swebench import ingest_swebench

FIXTURE = Path(__file__).parent / "fixtures" / "swebench"


def test_resolution_rates_per_combination_sorted_best_first() -> None:
    records = ingest_swebench(FIXTURE)

    rates = resolution_rates(records)

    assert rates == [
        ("claude-code", "claude-sonnet-5", 3, 4, 0.75),
        ("openhands", "claude-opus-5", 2, 4, 0.50),
        ("aider", "gpt-6", 1, 4, 0.25),
    ]


def test_rendered_table_shows_combinations_and_rates() -> None:
    records = ingest_swebench(FIXTURE)

    table = render_table(resolution_rates(records))

    lines = table.splitlines()
    assert "agent" in lines[0] and "model" in lines[0] and "rate" in lines[0]
    assert "claude-code" in lines[1] and "75.0%" in lines[1]
    assert "aider" in lines[3] and "25.0%" in lines[3]
