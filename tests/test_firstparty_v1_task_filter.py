"""`--task` on `eval-v1 --live`: a repeatable filter naming a subset of the
loaded task set, applied in corpus order regardless of the order the flags
were typed, with a typo'd id refused before anything runs."""

import shutil
from pathlib import Path

import pytest
from conftest import FakeClaude

from ai_benchmark import firstparty_v1
from ai_benchmark.cli import main

CHECKED_IN = Path(__file__).parent.parent / "tasks" / "first-party-v1"

# Corpus order (sorted task-directory order) puts these two ledger-first,
# wordcount-second — the reverse of the order asserted against below.
LEDGER = "ledger-split-formatting"
WORDCOUNT = "wordcount-top-words"


def _copy_seed_tasks(tmp_path: Path) -> Path:
    tasks = tmp_path / "tasks"
    for seed in (LEDGER, WORDCOUNT):
        shutil.copytree(CHECKED_IN / seed, tasks / seed)
    return tasks


def test_task_flag_runs_only_the_named_tasks_in_corpus_order(
    fake_claude: FakeClaude, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    fake_claude("")
    tasks = _copy_seed_tasks(tmp_path)
    data = tmp_path / "unified.jsonl"
    log = tmp_path / "runs.jsonl"

    # Flags typed wordcount-then-ledger; corpus order is ledger-then-wordcount.
    main([
        "eval-v1", "--tasks", str(tasks), "--live", "--model", "claude-sonnet-5",
        "--log", str(log), "--sweep", "round-6-task-filter",
        "--data", str(data), "--task", WORDCOUNT, "--task", LEDGER,
    ])

    out = capsys.readouterr().out
    assert "ran 2 live runs; raw log written to" in out
    assert "evaluated 2 runs over 2 tasks" in out

    runs = firstparty_v1.load_runs(log)
    assert [run.task_id for run in runs] == [LEDGER, WORDCOUNT]


def test_task_flag_filters_out_everything_else(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    fake_claude("")
    tasks = _copy_seed_tasks(tmp_path)
    log = tmp_path / "runs.jsonl"

    main([
        "eval-v1", "--tasks", str(tasks), "--live", "--model", "claude-sonnet-5",
        "--log", str(log), "--sweep", "round-6-task-filter",
        "--data", str(tmp_path / "unified.jsonl"), "--task", WORDCOUNT,
    ])

    [run] = firstparty_v1.load_runs(log)
    assert run.task_id == WORDCOUNT


def test_no_task_flag_runs_the_whole_set_unchanged(
    fake_claude: FakeClaude, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    fake_claude("")
    tasks = _copy_seed_tasks(tmp_path)
    log = tmp_path / "runs.jsonl"

    main([
        "eval-v1", "--tasks", str(tasks), "--live", "--model", "claude-sonnet-5",
        "--log", str(log), "--sweep", "round-6-task-filter",
        "--data", str(tmp_path / "unified.jsonl"),
    ])

    out = capsys.readouterr().out
    assert "ran 2 live runs; raw log written to" in out
    runs = firstparty_v1.load_runs(log)
    assert [run.task_id for run in runs] == [LEDGER, WORDCOUNT]


def test_unknown_task_id_fails_loudly_before_any_run(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    argv_log = fake_claude("")
    tasks = _copy_seed_tasks(tmp_path)
    log = tmp_path / "runs.jsonl"

    with pytest.raises(SystemExit, match="typo-not-a-real-task"):
        main([
            "eval-v1", "--tasks", str(tasks), "--live", "--model", "claude-sonnet-5",
            "--log", str(log), "--sweep", "round-6-task-filter",
            "--data", str(tmp_path / "unified.jsonl"),
            "--task", WORDCOUNT, "--task", "typo-not-a-real-task",
        ])

    assert not argv_log.exists()
    assert not log.exists()
