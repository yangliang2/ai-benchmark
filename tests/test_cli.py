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


def test_table_shows_aggregate_records_in_their_own_section(
    dataset_fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["table", "--data", str(dataset_fixture)])

    out = capsys.readouterr().out
    assert "aggregate records" in out
    assert "resolution-rate" in out  # the aggregate's metric is visible


def test_ingest_aider_then_table_shows_costs_and_gaps(
    swebench_fixture: Path, aider_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "unified.jsonl"

    main(["ingest-swebench", str(swebench_fixture), "--data", str(data)])
    main(["ingest-aider", str(aider_fixture), "--data", str(data)])

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    # Per-instance section: swe-bench rows with honest cost gaps.
    assert "swe-bench-verified" in out
    # Aggregate section: aider rows with per-instance-normalized cost (45.10/225).
    assert "aider-polyglot" in out and "0.20" in out and "pass-rate-2" in out


def test_table_by_category(
    classified_fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["table", "--data", str(classified_fixture), "--by-category"])

    out = capsys.readouterr().out
    assert "bug-fix" in out and "feature-dev" in out and "unclassified" in out


def test_classify_with_warm_cache_needs_no_api_key(
    dataset_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    data = tmp_path / "unified.jsonl"
    shutil.copy(dataset_fixture, data)
    cache = tmp_path / "cache.json"
    cache.write_text(
        '{"polyglot-bench/rust__fix-1": {"category": "feature-dev", "scale": "single-file", "language": "rust"},'
        ' "swe-bench-verified/django__django-11099": {"category": "bug-fix", "scale": "single-file", "language": "python"},'
        ' "swe-bench-verified/sympy__sympy-20590": {"category": "bug-fix", "scale": "cross-file", "language": "python"}}'
    )

    main(["classify", "--data", str(data), "--cache", str(cache)])

    out = capsys.readouterr().out
    assert "0 LLM call" in out
    main(["table", "--data", str(data), "--by-category"])
    assert "bug-fix" in capsys.readouterr().out


def test_classify_cache_miss_without_api_key_fails_clearly(
    dataset_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    data = tmp_path / "unified.jsonl"
    shutil.copy(dataset_fixture, data)
    cache = tmp_path / "cache.json"

    with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
        main(["classify", "--data", str(data), "--cache", str(cache)])
