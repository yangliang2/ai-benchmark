"""End-to-end at the command surface: ingest merges into the dataset, table reads it."""

import shutil
from pathlib import Path

import pytest

from ai_benchmark.cli import main


def test_ingest_then_table_end_to_end(
    swebench_fixture: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "unified.jsonl"

    main(["ingest-swebench", str(swebench_fixture), "--data", str(data)])
    assert data.exists()

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    assert "swe-bench-verified" in out
    assert "claude-code" in out and "75.0%" in out


def test_ingest_preserves_records_from_other_sources(
    swebench_fixture: Path, dataset_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "unified.jsonl"
    shutil.copy(dataset_fixture, data)

    main(["ingest-swebench", str(swebench_fixture), "--data", str(data)])

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    assert "polyglot-bench" in out and "swe-bench-verified" in out


def test_table_discloses_aggregate_records_it_does_not_show(
    dataset_fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["table", "--data", str(dataset_fixture)])

    out = capsys.readouterr().out
    assert "1 aggregate record" in out
