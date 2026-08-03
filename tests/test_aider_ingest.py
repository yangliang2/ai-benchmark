"""Dataset-seam tests: raw Aider polyglot leaderboard fixture in -> validated records out."""

from pathlib import Path

import pytest

from ai_benchmark.aider import ingest_aider
from ai_benchmark.dataset import merge_records, read_records, write_records
from ai_benchmark.swebench import ingest_swebench

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def aider_fixture() -> Path:
    return FIXTURES / "aider"


def test_fixture_ingests_into_aggregate_records_with_cost(aider_fixture: Path) -> None:
    records = ingest_aider(aider_fixture)

    assert len(records) == 2
    [sonnet] = [r for r in records if r.model == "claude-sonnet-5"]
    assert sonnet.benchmark == "aider-polyglot"
    assert sonnet.agent == "aider"
    assert sonnet.agent_version == "0.72.1"
    assert sonnet.instance_id is None
    assert sonnet.quality_metric == "pass-rate"
    assert sonnet.quality_value == pytest.approx(0.88)
    assert sonnet.cost_usd == pytest.approx(14.32)
    assert sonnet.latency_s == pytest.approx(33.1)
    assert sonnet.source_type == "aggregate"
    assert sonnet.confidence == "low"
    assert sonnet.as_of.isoformat() == "2026-01-10"
    assert "aider.chat" in sonnet.source


def test_both_sources_coexist_distinguishable_by_provenance(
    aider_fixture: Path, swebench_fixture: Path, tmp_path: Path
) -> None:
    out = tmp_path / "unified.jsonl"

    write_records(
        merge_records(ingest_swebench(swebench_fixture), ingest_aider(aider_fixture)),
        out,
    )
    records = read_records(out)

    by_source_type = {r.source_type for r in records}
    assert by_source_type == {"per-instance", "aggregate"}
    sources = {r.source for r in records}
    assert any("aider.chat" in s for s in sources)
    assert any("swe-bench" in s for s in sources)


def test_reingest_is_idempotent(aider_fixture: Path, tmp_path: Path) -> None:
    out = tmp_path / "unified.jsonl"

    write_records(ingest_aider(aider_fixture), out)
    first = out.read_bytes()
    write_records(
        merge_records(read_records(out), ingest_aider(aider_fixture)), out
    )

    assert out.read_bytes() == first
