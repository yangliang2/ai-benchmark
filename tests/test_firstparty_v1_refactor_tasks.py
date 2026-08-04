"""The ten hand-authored refactor tasks of ticket #13.

Each task is proved four ways: it lints clean (behaviour tests pass pristine,
the whole suite does not), its reference solution grades 1.0, doing nothing
grades 0.0, and — for two tasks — a restructure that satisfies every
structural assertion but bends behaviour grades 0.0, which is the property
that makes these refactor tasks rather than rearrangement tasks.

Reference solutions live in tasks/first-party-v1-solutions/<task-id>/ as the
full solved repository tree. That directory sits outside the task directory,
so the runner — which copies repo/ alone — can never hand a solution to the
agent, and the loader — which reads tasks/first-party-v1/ alone — never sees
it either.
"""

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Run,
    Task,
    _run_grading,
    evaluate,
    lint_task_set,
    load_task_set,
)

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v1"
SOLUTIONS = Path(__file__).parent.parent / "tasks" / "first-party-v1-solutions"

REFACTOR_TASKS = (
    "cart-extract-coupon-policy",
    "exporters-pull-up-base-class",
    "gradebook-split-compute-from-format",
    "logparse-extract-timestamp-parsing",
    "measures-merge-duplicate-converters",
    "metrics-dispatch-table",
    "pipeline-move-retry-policy",
    "spendreport-invert-storage-dependency",
    "tasktrack-reshape-parse-result",
    "textdoc-split-render-flag",
)


def task_by_id(task_id: str) -> Task:
    [task] = [task for task in load_task_set(TASKS) if task.id == task_id]
    return task


def solution_diff(task: Task, mutate: Callable[[Path], None] | None = None) -> str:
    """The workdir diff a run that produced the reference solution would log:
    pristine repo committed, the tree replaced by the solved tree (optionally
    mutated), the diff captured the way the live runner captures it."""
    git = ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval"]
    with tempfile.TemporaryDirectory(prefix="ai-bench-refactor-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        subprocess.run([*git, "init", "-q", "."], cwd=workdir, check=True)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        subprocess.run([*git, "commit", "-qm", "pristine"], cwd=workdir, check=True)
        for entry in workdir.iterdir():
            if entry.name == ".git":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        shutil.copytree(SOLUTIONS / task.id, workdir, dirs_exist_ok=True)
        if mutate is not None:
            mutate(workdir)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        return subprocess.run(
            [*git, "diff", "--cached"], cwd=workdir, capture_output=True,
            text=True, check=True,
        ).stdout


def run_for(task: Task, diff: str) -> Run:
    return Run(
        task_id=task.id,
        agent="claude-code",
        agent_version="2.1.220",
        model="claude-sonnet-5",
        output="done",
        diff=diff,
        tokens_in=41000,
        tokens_out=1500,
        cost_usd=0.21,
        latency_s=64.5,
        turns=7,
        as_of=date(2026, 8, 4),
    )


def structural_half_passes(task: Task, diff: str) -> bool:
    """Whether the structural assertions alone accept this diff. Uses the
    grader's own private runner: the split is not reachable through grade(),
    which always runs the whole suite — exactly the point being tested."""
    structural = sorted(set(task.grading_test_paths) - set(task.behaviour_test_paths))
    return _run_grading(task, diff, structural, timeout_s=GRADE_TIMEOUT_S)


# --- the task set itself --------------------------------------------------------


def test_all_ten_tasks_are_checked_in_and_annotated() -> None:
    tasks = [task for task in load_task_set(TASKS) if task.id in REFACTOR_TASKS]

    assert sorted(task.id for task in tasks) == sorted(REFACTOR_TASKS)
    for task in tasks:
        assert task.category == "refactor"
        assert task.language == "python"
        assert task.behaviour_test_paths
        assert (SOLUTIONS / task.id).is_dir()
    # Both scales are represented; per-task honesty is asserted mechanically
    # against each reference solution's diff below.
    assert {task.scale for task in tasks} == {"single-file", "cross-file"}


@pytest.mark.parametrize("task_id", REFACTOR_TASKS)
def test_the_scale_annotation_matches_the_reference_solution(task_id: str) -> None:
    """Scale is honest to the canonical solution, checked the mechanical way:
    one touched file means single-file, more than one means cross-file."""
    task = task_by_id(task_id)
    touched = [
        line
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    ]

    if task.scale == "single-file":
        assert len(touched) == 1
    else:
        assert len(touched) > 1


def test_all_ten_tasks_lint_clean() -> None:
    tasks = [task for task in load_task_set(TASKS) if task.id in REFACTOR_TASKS]

    assert lint_task_set(tasks) == []


# --- solved, untouched, and behaviour-breaking runs -----------------------------


@pytest.mark.parametrize("task_id", REFACTOR_TASKS)
def test_the_reference_solution_resolves_the_task(task_id: str) -> None:
    task = task_by_id(task_id)

    [record] = evaluate(
        [task], [run_for(task, solution_diff(task))], source="run-log"
    )

    assert record.quality_value == 1.0


@pytest.mark.parametrize("task_id", REFACTOR_TASKS)
def test_doing_nothing_leaves_the_task_unresolved(task_id: str) -> None:
    task = task_by_id(task_id)

    [record] = evaluate([task], [run_for(task, "")], source="run-log")

    assert record.quality_value == 0.0


def break_cart_rounding(workdir: Path) -> None:
    """The extraction done exactly right, plus one silent 'improvement':
    discounts now round to nearest instead of flooring."""
    cart = workdir / "cart.py"
    source = cart.read_text()
    floored = "self.subtotal() * self.policy.percent_off() // 100"
    assert floored in source
    cart.write_text(
        source.replace(
            floored, "round(self.subtotal() * self.policy.percent_off() / 100)"
        )
    )


def break_pipeline_retry_count(workdir: Path) -> None:
    """The move done exactly right, plus one extra retry slipped into the
    loop — the policy still reads the same, steps run once too often."""
    pipeline = workdir / "pipeline.py"
    source = pipeline.read_text()
    per_policy = "for delay in self.policy.delays():"
    assert per_policy in source
    pipeline.write_text(
        source.replace(per_policy, "for delay in [*self.policy.delays(), 0.0]:")
    )


@pytest.mark.parametrize(
    ("task_id", "mutate"),
    [
        ("cart-extract-coupon-policy", break_cart_rounding),
        ("pipeline-move-retry-policy", break_pipeline_retry_count),
    ],
)
def test_a_behaviour_breaking_restructure_is_unresolved(
    task_id: str, mutate: Callable[[Path], None]
) -> None:
    """The refactor acceptance criterion: a diff that restructures exactly as
    asked but bends behaviour must grade 0.0 even though every structural
    assertion passes — the behaviour tests are what catch it."""
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=mutate)
    assert structural_half_passes(task, diff)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0
