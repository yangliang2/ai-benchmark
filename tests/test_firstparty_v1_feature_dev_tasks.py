"""The hand-authored feature-dev tasks (ticket #12): every checked-in task
lints clean, its reference solution grades resolved, and doing nothing grades
unresolved — all through the same execution-verified pipeline real runs go
through. The two seed tasks are held to the same reference-solution
invariants here as the ten feature-dev tasks.

Reference solutions are full solved trees under
tasks/first-party-v1-solutions/<task-id>/, outside the task directory, so the
loader, the runner, the lint and pytest collection never see them. The diff
graded here is the solved tree laid over the pristine repository, captured
with git exactly as the live runner captures a workdir diff.
"""

import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pytest

from ai_benchmark.firstparty_v1 import (
    Run,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v1"
SOLUTIONS = Path(__file__).parent.parent / "tasks" / "first-party-v1-solutions"

# Task id -> the scale its reference solution honestly has.
FEATURE_DEV_TASKS: dict[str, str] = {
    "calc-infix-evaluator": "single-file",
    "checkout-discount-codes": "cross-file",
    "docstore-json-pointer": "single-file",
    "jobrunner-dependency-order": "cross-file",
    "matcher-brace-expansion": "single-file",
    "microtemplate-for-loops": "cross-file",
    "slugger-unique-slugs": "single-file",
    "spans-subtract-gaps": "single-file",
    "tablecli-filter-command": "cross-file",
    "workflow-guarded-transitions": "cross-file",
}

# The seed tasks (ticket #10) hold to the same reference-solution invariants.
SEED_TASKS = ("ledger-split-formatting", "wordcount-top-words")

SOLVED_TASKS = sorted([*FEATURE_DEV_TASKS, *SEED_TASKS])


def task_by_id(task_id: str) -> Task:
    [task] = [task for task in load_task_set(TASKS) if task.id == task_id]
    return task


def solution_diff(task: Task) -> str:
    """The workdir diff the reference solution produces: pristine repo, the
    solved tree laid over it, captured against the initial commit exactly as
    the live runner captures a run's diff."""
    git = ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval"]
    with tempfile.TemporaryDirectory(prefix="ai-bench-solution-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        subprocess.run([*git, "init", "-q", "."], cwd=workdir, check=True)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        subprocess.run([*git, "commit", "-qm", "pristine"], cwd=workdir, check=True)
        shutil.copytree(SOLUTIONS / task.id, workdir, dirs_exist_ok=True)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        captured = subprocess.run(
            [*git, "diff", "--cached"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        )
        return captured.stdout


def run_for(task: Task, diff: str, model: str) -> Run:
    return Run(
        task_id=task.id,
        agent="claude-code",
        model=model,
        output="done",
        diff=diff,
        tokens_in=1000,
        tokens_out=100,
        cost_usd=0.05,
        latency_s=10.0,
        turns=3,
        as_of=date(2026, 8, 4),
    )


@pytest.mark.parametrize("task_id", sorted(FEATURE_DEV_TASKS))
def test_task_is_declared_as_designed(task_id: str) -> None:
    task = task_by_id(task_id)

    assert task.category == "feature-dev"
    assert task.language == "python"
    assert task.scale == FEATURE_DEV_TASKS[task_id]


@pytest.mark.parametrize("task_id", SOLVED_TASKS)
def test_task_lints_clean(task_id: str) -> None:
    assert lint_task_set([task_by_id(task_id)]) == []


@pytest.mark.parametrize("task_id", SOLVED_TASKS)
def test_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("task_id", SOLVED_TASKS)
def test_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    """Scale is honest to the canonical solution: a single-file solution
    touches exactly one file, a cross-file one touches several."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    if task.scale == "single-file":
        assert len(touched) == 1
    else:
        assert len(touched) > 1
