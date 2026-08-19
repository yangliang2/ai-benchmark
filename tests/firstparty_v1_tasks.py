"""Shared helpers for the first-party v1 task-set test suites.

Every one of those suites needs the same few things: the checked-in task set,
a run-log row to hand `evaluate`, a workdir diff built the way the live runner
builds one — copy the pristine repo, git init + commit, edit, `git add -A &&
git diff --cached` — and, for a refactor task, a way to run the structural
half of a grading suite on its own. Building the diff with git rather than
hand-writing hunks is the point: the grader is then exercised against
genuine patches (added, modified and deleted files) that cannot drift from
what a real run would log.

Running a task's *visible* suite — the net the agent inherits, as against the
held-out one the verdict reads — is here too, because it is the one helper
that has to be deterministic and was not: see `visible_tests_pass`.
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Run,
    Task,
    _run_grading,
    load_task_set,
)
from ai_benchmark.language_runners import PYTHON, TYPESCRIPT

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v1"
SOLUTIONS = Path(__file__).parent.parent / "tasks" / "first-party-v1-solutions"

# An identity, so the initial commit works on a machine with none configured.
_GIT = ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval"]

# What having run something leaves behind, as against what anyone authored: a
# stray __pycache__/ left in a solutions tree by a probe once reached the diff
# and broke grading, and a node_modules/ an agent or a probe installed would
# reach one the same way — the whole of what a TypeScript task ships is its own
# files (ADR-0003), so a directory of packages under one is a byproduct by
# construction. The live runner keeps both out with its own .gitignore; these
# helpers copy trees directly, so they drop them here.
_BYPRODUCTS = shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules")


def task_by_id(task_id: str) -> Task:
    [task] = [task for task in load_task_set(TASKS) if task.id == task_id]
    return task


def copy_solution(task: Task, into: Path) -> None:
    """Lay this task's reference solution into an existing directory."""
    shutil.copytree(SOLUTIONS / task.id, into, dirs_exist_ok=True, ignore=_BYPRODUCTS)


def workdir_diff(task: Task, edit: Callable[[Path], None]) -> str:
    """The workdir diff a run that made this edit would log."""
    with tempfile.TemporaryDirectory(prefix="ai-bench-test-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True, ignore=_BYPRODUCTS)
        subprocess.run([*_GIT, "init", "-q", "."], cwd=workdir, check=True)
        subprocess.run([*_GIT, "add", "-A"], cwd=workdir, check=True)
        subprocess.run([*_GIT, "commit", "-qm", "pristine"], cwd=workdir, check=True)
        edit(workdir)
        subprocess.run([*_GIT, "add", "-A"], cwd=workdir, check=True)
        return subprocess.run(
            [*_GIT, "diff", "--cached"], cwd=workdir, capture_output=True,
            text=True, check=True,
        ).stdout


def solved_tree(
    task: Task, mutate: Callable[[Path], None] | None = None
) -> Callable[[Path], None]:
    """The edit that turns a pristine workdir into the reference solution.

    The solved tree *replaces* the pristine one rather than being laid over
    it, so a solution that merges two modules into one is captured as the
    deletion it is. Optionally mutated afterwards, to produce a solution bent
    in one deliberate way — which is wanted both as a diff to grade and as a
    workdir to run the repository's own tests in.
    """

    def apply_solution(workdir: Path) -> None:
        for entry in workdir.iterdir():
            if entry.name == ".git":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        copy_solution(task, workdir)
        if mutate is not None:
            mutate(workdir)

    return apply_solution


def solution_diff(task: Task, mutate: Callable[[Path], None] | None = None) -> str:
    """The workdir diff the reference solution produces."""
    return workdir_diff(task, solved_tree(task, mutate))


# What the copy's generators are seeded with. Public because a suite proving
# the injection reached the copy has to know what to expect from a draw.
VISIBLE_SUITE_SEED = 20260806

# Dropped into the throwaway copy a visible suite runs in, and nowhere else.
# The checked-in `repo/` trees of swept tasks are immutable — replay of a
# logged run applies its diff to those exact bytes — so determinism is bought
# in the copy, which no run and no replay ever sees.
_SEEDING_CONFTEST = f'''\
"""Determinism for this copy, injected by the ai-benchmark test harness.

Not part of the task and not in any checked-in tree: a vendored suite that
builds its fixtures with the unseeded global `random` makes "the repository's
own tests pass" a probabilistic claim, which is no basis for a gate. Seeded
once before collection, because fixtures are built at import time too, and
again before every test, so that a test drawing a different number of values
than it did last time cannot shift what the tests after it see.
"""

import random


def pytest_configure(config):
    random.seed({VISIBLE_SUITE_SEED})


def pytest_runtest_setup(item):
    random.seed({VISIBLE_SUITE_SEED})
'''


# How each language runs the repository's own tests: the command an agent
# reading that repository's README would type, and nothing the harness adds.
# Dispatched on the task's declared runner and never on a name written at a
# call site, for the reason the grader dispatches on it — a task carries its
# own mechanism, and running a TypeScript repository's suite under pytest
# would report "no tests ran" as a green net the agent never had.
_VISIBLE_TEST_ARGV = {
    PYTHON: [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
    TYPESCRIPT: ["node", "--test"],
}


def visible_tests_pass(task: Task, edit: Callable[[Path], None] | None = None) -> bool:
    """Whether the repository's own tests — the net the agent sees — pass.

    Run the way an agent would run them: the runner's own plain invocation in
    the workdir, with none of the isolation grading applies, because the
    question here is what the agent is told rather than what the verdict
    reads. `node --test` with no arguments really does discover a repository's
    `*.test.ts` files on the Node this grades under, which is what makes a
    TypeScript task's README honest in naming it.

    With one deliberate difference from what the agent gets, and only where
    the agent's own toolchain leaves the question open: a *Python* copy is
    seeded. A vendored suite generating its own tables and delimiters with the
    unseeded global `random` turns this gate into a coin toss — round 1 caught
    it as a ~0.5% failure of "the reference solution keeps the repository
    green" on the RBQL substrate — and a gate that fails once in two hundred
    runs cannot support a verdict resting on the visible suite staying green.
    The seeding goes in *after* the edit, because an edit that lays a solved
    tree over the workdir replaces what is there.

    Nothing is written into a TypeScript copy at all. The seeding device is a
    `conftest.py`, which is pytest's and not Node's, and a task whose
    repository ships no conftest is one where writing one in would be adding a
    file the agent never had rather than making its suite deterministic.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-visible-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True, ignore=_BYPRODUCTS)
        if edit is not None:
            edit(workdir)
        if task.runner is PYTHON:
            conftest = workdir / "conftest.py"
            assert not conftest.exists(), (
                f"{task.id} ships its own conftest.py — seeding the copy would "
                "replace it, so this helper would be running a different suite "
                "than the agent sees"
            )
            conftest.write_text(_SEEDING_CONFTEST, encoding="utf-8")
        return (
            subprocess.run(
                _VISIBLE_TEST_ARGV[task.runner],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=False,
                timeout=GRADE_TIMEOUT_S,
            ).returncode
            == 0
        )


def structural_half_passes(task: Task, diff: str) -> bool:
    """Whether the structural assertions alone accept this diff. Uses the
    grader's own private runner: the split is not reachable through grade(),
    which always runs the whole suite — exactly the point being tested."""
    structural = sorted(set(task.grading_test_paths) - set(task.behaviour_test_paths))
    return _run_grading(task, diff, structural, timeout_s=GRADE_TIMEOUT_S)


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
