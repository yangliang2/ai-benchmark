"""Dataset-seam tests: raw SWE-bench fixture in -> validated records out."""

from pathlib import Path

import pytest

from ai_benchmark.dataset import read_records, write_records
from ai_benchmark.swebench import IngestError, ingest_swebench

FIXTURE = Path(__file__).parent / "fixtures" / "swebench"


def test_fixture_ingests_into_one_record_per_instance_result() -> None:
    records = ingest_swebench(FIXTURE)

    assert len(records) == 12  # 3 combinations x 4 instances
    combinations = {(r.agent, r.model) for r in records}
    assert combinations == {
        ("claude-code", "claude-sonnet-5"),
        ("aider", "gpt-6"),
        ("openhands", "claude-opus-5"),
    }


def test_ingested_record_carries_result_and_provenance() -> None:
    records = ingest_swebench(FIXTURE)

    [record] = [
        r
        for r in records
        if r.agent == "claude-code" and r.instance_id == "requests__requests-863"
    ]
    assert record.benchmark == "swe-bench-verified"
    assert record.quality_metric == "resolved"
    assert record.quality_value == 0.0
    assert record.category == "unclassified"
    assert record.language == "python"
    assert record.source_type == "per-instance"
    assert record.confidence == "medium"
    assert record.as_of.isoformat() == "2026-01-15"
    assert "swe-bench/experiments" in record.source


def test_instance_in_both_resolved_and_unresolved_is_rejected(tmp_path: Path) -> None:
    submission = tmp_path / "broken__combo"
    submission.mkdir()
    (submission / "metadata.json").write_text(
        '{"agent": "a", "agent_version": null, "model": "m",'
        ' "source": "https://example.com", "as_of": "2026-01-01"}'
    )
    (submission / "results.json").write_text(
        '{"resolved": ["x__x-1"], "unresolved": ["x__x-1"]}'
    )

    with pytest.raises(IngestError, match="x__x-1"):
        ingest_swebench(tmp_path)


def test_ingest_then_write_is_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "unified.jsonl"

    write_records(ingest_swebench(FIXTURE), out)
    first = out.read_bytes()
    write_records(ingest_swebench(FIXTURE), out)

    assert out.read_bytes() == first


def test_written_dataset_reads_back_identically(tmp_path: Path) -> None:
    out = tmp_path / "unified.jsonl"
    records = ingest_swebench(FIXTURE)

    write_records(records, out)

    assert read_records(out) == sorted(
        records, key=lambda r: (r.benchmark, r.instance_id or "", r.agent, r.model)
    )
