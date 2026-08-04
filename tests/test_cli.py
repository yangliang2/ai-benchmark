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


def test_report_command_writes_static_html(
    pareto_fixture: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_file = tmp_path / "report.html"

    main(["report", "--data", str(pareto_fixture), "--out", str(out_file)])

    assert out_file.exists()
    html = out_file.read_text()
    assert "<svg" in html and "bug-fix" in html
    assert str(out_file) in capsys.readouterr().out


def test_eval_replay_then_table_shows_first_party_alongside_aggregates(
    firstparty_fixture: Path, aggregates_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "unified.jsonl"
    shutil.copy(aggregates_fixture, data)
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v0.yaml"

    main(["eval", "--tasks", str(tasks), "--replay", str(firstparty_fixture),
          "--data", str(data)])
    assert "evaluated 12 runs over 6 tasks (11 resolved)" in capsys.readouterr().out

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    # First-party rates with exact cost, next to the aggregate section.
    assert "first-party-v0" in out
    assert "100.0%" in out and "83.3%" in out
    assert "aider-polyglot" in out


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

    main([
        "classify", "--data", str(data), "--cache", str(cache),
        "--instances", str(tmp_path / "no-instances.json"),
    ])

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
        main([
            "classify", "--data", str(data), "--cache", str(cache),
            "--instances", str(tmp_path / "no-instances.json"),
        ])


def test_classify_with_instances_resolves_unknown_scales_without_api_key(
    dataset_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The #8 payoff path end-to-end: warm cache + instance context upgrade
    "unknown" scales in both the dataset and the cache with zero LLM calls."""
    import json

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    data = tmp_path / "unified.jsonl"
    shutil.copy(dataset_fixture, data)
    cache = tmp_path / "cache.json"
    cache.write_text(
        '{"polyglot-bench/rust__fix-1": {"category": "feature-dev", "scale": "single-file", "language": "rust"},'
        ' "swe-bench-verified/django__django-11099": {"category": "bug-fix", "scale": "unknown", "language": "python"},'
        ' "swe-bench-verified/sympy__sympy-20590": {"category": "bug-fix", "scale": "unknown", "language": "python"}}'
    )
    instances = tmp_path / "instance-context.json"
    instances.write_text(json.dumps({
        "swe-bench-verified/django__django-11099": {
            "problem_statement": "validator bug",
            "patch_files": ["django/core/validators.py"],
        },
        "swe-bench-verified/sympy__sympy-20590": {
            "problem_statement": "printing bug",
            "patch_files": ["sympy/printing/latex.py", "sympy/printing/str.py"],
        },
    }))

    main([
        "classify", "--data", str(data), "--cache", str(cache),
        "--instances", str(instances),
    ])

    assert "0 LLM call" in capsys.readouterr().out
    rows = {
        row["instance_id"]: row
        for line in data.read_text().splitlines()
        if (row := json.loads(line))["instance_id"]
    }
    assert rows["django__django-11099"]["scale"] == "single-file"
    assert rows["sympy__sympy-20590"]["scale"] == "cross-file"
    cache_after = json.loads(cache.read_text())
    assert cache_after["swe-bench-verified/django__django-11099"]["scale"] == "single-file"
    assert cache_after["swe-bench-verified/sympy__sympy-20590"]["scale"] == "cross-file"


def test_fetch_swebench_context_command_writes_wanted_context(
    dataset_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The command seam, network stubbed out: only wanted instances (dataset
    union cache) are kept, and existing context is merged, not lost."""
    import json
    from collections.abc import Iterator
    from typing import Any

    import ai_benchmark.cli

    def stub_rows() -> Iterator[dict[str, Any]]:
        yield {
            "instance_id": "django__django-11099",
            "problem_statement": "validator bug",
            "patch": "diff --git a/django/core/validators.py b/django/core/validators.py\n",
        }
        yield {
            "instance_id": "not__in-dataset-1",
            "problem_statement": "irrelevant",
            "patch": "diff --git a/x.py b/x.py\n",
        }
        yield {
            "instance_id": "requests__requests-863",  # cache-only instance
            "problem_statement": "hooks bug",
            "patch": "diff --git a/requests/models.py b/requests/models.py\n",
        }

    monkeypatch.setattr(ai_benchmark.cli, "fetch_swebench_rows", stub_rows)
    data = tmp_path / "unified.jsonl"
    shutil.copy(dataset_fixture, data)
    cache = tmp_path / "cache.json"
    cache.write_text(
        '{"swe-bench-verified/requests__requests-863":'
        ' {"category": "bug-fix", "scale": "unknown", "language": "python"}}'
    )
    out_path = tmp_path / "instance-context.json"
    out_path.write_text(json.dumps({
        "swe-bench-verified/previously__fetched-1": {
            "problem_statement": "kept", "patch_files": ["a.py"],
        }
    }))

    main([
        "fetch-swebench-context", "--data", str(data),
        "--cache", str(cache), "--out", str(out_path),
    ])

    assert "fetched context for 2 of 3" in capsys.readouterr().out
    stored = json.loads(out_path.read_text())
    assert set(stored) == {
        "swe-bench-verified/previously__fetched-1",
        "swe-bench-verified/django__django-11099",
        "swe-bench-verified/requests__requests-863",
    }
    assert stored["swe-bench-verified/django__django-11099"]["patch_files"] == [
        "django/core/validators.py"
    ]
