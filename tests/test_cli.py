"""End-to-end at the command surface: ingest merges into the dataset, table reads it."""

import shutil
from pathlib import Path

import pytest
from conftest import FakeClaude

from ai_benchmark import firstparty_v1
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


def test_eval_v1_replay_grades_by_execution_and_lands_in_the_table(
    firstparty_v1_fixture: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "unified.jsonl"
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"

    main(["eval-v1", "--tasks", str(tasks), "--replay", str(firstparty_v1_fixture),
          "--data", str(data)])
    # The checked-in task directory keeps growing as content tickets land, so
    # the assertion pins the fixture's runs and verdicts, not the task count.
    out = capsys.readouterr().out
    assert "evaluated 4 runs over" in out and "(2 resolved)" in out

    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    # v1 is its own benchmark: sonnet solved both tasks, haiku neither.
    assert "first-party-v1" in out
    assert "100.0%" in out and "0.0%" in out


def test_eval_v1_leaves_v0_records_untouched(
    firstparty_fixture: Path, firstparty_v1_fixture: Path, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "unified.jsonl"
    v0_tasks = Path(__file__).parent.parent / "tasks" / "first-party-v0.yaml"
    v1_tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"

    main(["eval", "--tasks", str(v0_tasks), "--replay", str(firstparty_fixture),
          "--data", str(data)])
    v0_rows = data.read_text().splitlines()

    main(["eval-v1", "--tasks", str(v1_tasks), "--replay", str(firstparty_v1_fixture),
          "--data", str(data)])

    capsys.readouterr()
    assert set(v0_rows) < set(data.read_text().splitlines())
    main(["table", "--data", str(data)])
    out = capsys.readouterr().out
    assert "first-party-v0" in out and "first-party-v1" in out


def test_eval_v1_live_end_to_end(
    fake_claude: FakeClaude, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Live v1 at the command surface, against a faked claude CLI: the fake
    solves the wordcount seed and leaves the ledger seed untouched, and both
    rows land in the log, grade by execution, and reach the table."""
    solution = (
        "\n\ndef top_words(text, n):\n"
        "    counts = word_counts(text)\n"
        "    return sorted(counts, key=lambda w: (-counts[w], w))[:n]\n"
    )
    fake_claude(
        f'if (workdir / "wordcount.py").exists():\n'
        f'    with open(workdir / "wordcount.py", "a") as source:\n'
        f"        source.write({solution!r})\n"
    )
    checked_in = Path(__file__).parent.parent / "tasks" / "first-party-v1"
    tasks = tmp_path / "tasks"
    for seed in ("wordcount-top-words", "ledger-split-formatting"):
        shutil.copytree(checked_in / seed, tasks / seed)
    data = tmp_path / "unified.jsonl"
    log = tmp_path / "runs.jsonl"

    main(["eval-v1", "--tasks", str(tasks), "--live", "--model", "claude-sonnet-5",
          "--log", str(log), "--timeout", "120", "--sweep", "round-2-track-a",
          "--data", str(data)])

    out = capsys.readouterr().out
    assert f"ran 2 live runs; raw log written to {log}" in out
    assert "evaluated 2 runs over 2 tasks (1 resolved)" in out
    assert log.exists()
    assert all(
        run.sweep == "round-2-track-a" for run in firstparty_v1.load_runs(log)
    )

    main(["table", "--data", str(data)])
    assert "first-party-v1" in capsys.readouterr().out


def test_eval_v1_rejects_a_non_positive_timeout(tmp_path: Path) -> None:
    """Validated before anything runs: a zero timeout would otherwise kill
    every run after billing had already started."""
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"

    with pytest.raises(SystemExit, match="timeout"):
        main(["eval-v1", "--tasks", str(tasks), "--live", "--timeout", "0",
              "--data", str(tmp_path / "unified.jsonl")])


def test_eval_v1_live_without_a_sweep_id_is_refused_before_it_bills(
    tmp_path: Path,
) -> None:
    """No default: reconcile-v1 counts one round per sweep id, and both values
    the runner could have guessed miscount — today's date merges two sweeps
    run in one day, the log's name splits one sweep across the invocations
    that ran its models or resumed it."""
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"

    with pytest.raises(SystemExit, match="--sweep"):
        main(["eval-v1", "--tasks", str(tasks), "--live",
              "--data", str(tmp_path / "unified.jsonl")])


def test_eval_v1_replay_rejects_live_only_flags(
    firstparty_v1_fixture: Path, tmp_path: Path,
) -> None:
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"

    with pytest.raises(SystemExit, match="--live"):
        main(["eval-v1", "--tasks", str(tasks), "--replay",
              str(firstparty_v1_fixture), "--model", "claude-sonnet-5",
              "--data", str(tmp_path / "unified.jsonl")])


def test_lint_v1_passes_on_the_checked_in_task_set(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every checked-in task, however many there are by now: the count is
    read from the task set rather than pinned, so authoring a new task does
    not have to touch this test."""
    tasks = Path(__file__).parent.parent / "tasks" / "first-party-v1"
    checked_in = len(firstparty_v1.load_task_set(tasks))

    main(["lint-v1", "--tasks", str(tasks)])

    assert f"lint clean: {checked_in} task(s)" in capsys.readouterr().out


def test_lint_v1_exits_non_zero_on_a_broken_task(tmp_path: Path) -> None:
    seed = Path(__file__).parent.parent / "tasks" / "first-party-v1"
    shutil.copytree(seed / "wordcount-top-words", tmp_path / "wordcount-top-words")
    solved = tmp_path / "wordcount-top-words" / "repo" / "wordcount.py"
    solved.write_text(
        solved.read_text() + "\n\ndef top_words(text, n):\n"
        "    counts = word_counts(text)\n"
        "    return sorted(counts, key=lambda w: (-counts[w], w))[:n]\n"
    )

    with pytest.raises(SystemExit, match="pristine"):
        main(["lint-v1", "--tasks", str(tmp_path)])


def test_lint_v1_exits_non_zero_on_an_effort_claim_with_no_comparator(
    tmp_path: Path,
) -> None:
    """An effort claim naming its pair partner as the comparator, on a task
    that declares no pair. The block contradicts itself, so the loader refuses
    it and the lint gate the sweep protocol runs never gets past loading —
    which is the point: the claim is unsettleable, and the gate says so before
    anything is paid for."""
    seed = Path(__file__).parent.parent / "tasks" / "first-party-v1"
    task_dir = tmp_path / "unpaired-claim"
    shutil.copytree(seed / "wordcount-top-words", task_dir)
    spec = task_dir / "task.yaml"
    spec.write_text(
        spec.read_text().replace("id: wordcount-top-words", "id: unpaired-claim")
        + "construction:\n"
        "  knobs:\n"
        "    - id: K9\n"
        "      level: single\n"
        "  prediction:\n"
        "    rung: haiku-solvable\n"
        "    rationale: one planted decision the spec never makes derivable\n"
        "    effort:\n"
        "      comparator: pair\n"
        "      metric: turns\n"
        "      at_least_factor: 1.5\n"
    )

    with pytest.raises(SystemExit, match="pair"):
        main(["lint-v1", "--tasks", str(tmp_path)])


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
