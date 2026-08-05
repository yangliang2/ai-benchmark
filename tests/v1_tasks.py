"""Shared helpers for the first-party v1 task-set test suites.

Every one of those suites needs the same three things: the checked-in task
set, a run-log row to hand `evaluate`, and a workdir diff built the way the
live runner builds one — copy the pristine repo, git init + commit, edit,
`git add -A && git diff --cached`. Building the diff with git rather than
hand-writing hunks is the point: the grader is then exercised against
genuine patches (added, modified and deleted files) that cannot drift from
what a real run would log.
"""

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ai_benchmark.firstparty_v1 import Run, Task, load_task_set

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v1"
SOLUTIONS = Path(__file__).parent.parent / "tasks" / "first-party-v1-solutions"

# An identity, so the initial commit works on a machine with none configured.
_GIT = ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval"]


def task_by_id(task_id: str) -> Task:
    [task] = [task for task in load_task_set(TASKS) if task.id == task_id]
    return task


def workdir_diff(task: Task, edit: Callable[[Path], None]) -> str:
    """The workdir diff a run that made this edit would log."""
    with tempfile.TemporaryDirectory(prefix="ai-bench-test-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        subprocess.run([*_GIT, "init", "-q", "."], cwd=workdir, check=True)
        subprocess.run([*_GIT, "add", "-A"], cwd=workdir, check=True)
        subprocess.run([*_GIT, "commit", "-qm", "pristine"], cwd=workdir, check=True)
        edit(workdir)
        subprocess.run([*_GIT, "add", "-A"], cwd=workdir, check=True)
        return subprocess.run(
            [*_GIT, "diff", "--cached"], cwd=workdir, capture_output=True,
            text=True, check=True,
        ).stdout


def solution_diff(task: Task, mutate: Callable[[Path], None] | None = None) -> str:
    """The workdir diff the reference solution produces.

    The solved tree *replaces* the pristine one rather than being laid over
    it, so a solution that merges two modules into one is captured as the
    deletion it is. Optionally mutated afterwards, to grade a solution bent
    in one deliberate way.
    """

    def apply_solution(workdir: Path) -> None:
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

    return workdir_diff(task, apply_solution)


def run_for(task: Task, diff: str, *, model: str = "claude-sonnet-5") -> Run:
    """A raw run-log row for one task, carrying the workdir diff it produced.

    The measurements are fixed rather than meaningful: grading reads the diff
    alone, and the numbers only have to reach a record unchanged.
    """
    return Run(
        task_id=task.id,
        agent="claude-code",
        agent_version="2.1.220",
        model=model,
        output="done",
        diff=diff,
        tokens_in=41000,
        tokens_out=1500,
        cost_usd=0.21,
        latency_s=64.5,
        turns=7,
        as_of=date(2026, 8, 4),
    )
