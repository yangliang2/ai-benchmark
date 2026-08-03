"""Dataset-seam tests: raw Aider polyglot leaderboard fixture in -> validated records out."""

from pathlib import Path

import pytest

from ai_benchmark.aider import ingest_aider
from ai_benchmark.dataset import IngestError, merge_records, read_records, write_records
from ai_benchmark.swebench import ingest_swebench


def test_fixture_ingests_into_aggregate_records_with_cost(aider_fixture: Path) -> None:
    records = ingest_aider(aider_fixture)

    assert len(records) == 2
    [sonnet] = [r for r in records if r.model == "claude-sonnet-5"]
    assert sonnet.benchmark == "aider-polyglot"
    assert sonnet.agent == "aider (diff)"  # edit format is part of the harness config
    assert sonnet.agent_version == "0.72.1"
    assert sonnet.instance_id is None
    assert sonnet.quality_metric == "pass-rate-2"
    assert sonnet.quality_value == pytest.approx(0.88)
    # cost_usd is normalized to USD per benchmark instance (ADR-0001).
    assert sonnet.cost_usd == pytest.approx(14.32 / 225)
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

    assert {r.source_type for r in records} == {"per-instance", "aggregate"}
    sources = {r.source for r in records}
    assert any("aider.chat" in s for s in sources)
    assert any("swe-bench" in s for s in sources)


def test_reingest_is_idempotent(aider_fixture: Path, tmp_path: Path) -> None:
    out = tmp_path / "unified.jsonl"

    write_records(ingest_aider(aider_fixture), out)
    first = out.read_bytes()
    write_records(merge_records(read_records(out), ingest_aider(aider_fixture)), out)

    assert out.read_bytes() == first


def _write_raw(tmp_path: Path, leaderboard_yaml: str) -> Path:
    (tmp_path / "metadata.json").write_text('{"source": "https://example.com/aider"}')
    (tmp_path / "polyglot_leaderboard.yml").write_text(leaderboard_yaml)
    return tmp_path


def test_malformed_entry_is_rejected_with_source_context(tmp_path: Path) -> None:
    raw = _write_raw(
        tmp_path,
        # total_cost missing
        "- dirname: 2026-01-01--broken\n"
        "  test_cases: 225\n"
        "  model: gpt-6\n"
        "  edit_format: diff\n"
        "  pass_rate_2: 50.0\n"
        "  seconds_per_case: 10.0\n"
        "  date: 2026-01-01\n",
    )

    with pytest.raises(IngestError, match="broken"):
        ingest_aider(raw)


def test_colliding_entries_fail_loudly_instead_of_overwriting(tmp_path: Path) -> None:
    entry = (
        "- dirname: {dirname}\n"
        "  test_cases: 225\n"
        "  model: gpt-6\n"
        "  edit_format: diff\n"
        "  pass_rate_2: {rate}\n"
        "  total_cost: 10.0\n"
        "  seconds_per_case: 10.0\n"
        "  date: 2026-01-01\n"
    )
    raw = _write_raw(
        tmp_path,
        entry.format(dirname="run-a", rate=50.0) + entry.format(dirname="run-b", rate=60.0),
    )

    with pytest.raises(IngestError, match="overwrite"):
        ingest_aider(raw)
