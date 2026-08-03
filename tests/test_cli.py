"""End-to-end at the command surface: ingest command writes the dataset, table command reads it."""

from pathlib import Path

import pytest

from ai_benchmark.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "swebench"


def test_ingest_then_table_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "unified.jsonl"

    main(["ingest-swebench", str(FIXTURE), "--data", str(data)])
    assert data.exists()

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    assert "claude-code" in out and "75.0%" in out
