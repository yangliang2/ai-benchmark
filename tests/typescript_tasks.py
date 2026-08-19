"""The synthetic TypeScript task tree the round-7 suites are built on.

`typescript_task` writes a whole v1 task directory under a `tmp_path` — a
`task.yaml` declaring `language: typescript`, a `repo/`, a `grading/` — and
loads it, so a suite can grade a TypeScript task without one being checked in
yet. **This is the seam tickets 03 (#100), 04 (#101), 05 (#102) and 06 (#103)
build their fixtures on**: they vary the tree rather than write one, so what a
TypeScript task looks like is stated here once.

Its Python counterparts are `clone_seed` / `retitle` in
`tests/test_firstparty_v1.py`, which clone a *checked-in* seed and rewrite its
spec. There is no TypeScript seed to clone yet, so this builds the tree
outright — which is also why every part of it is overridable: `repo`,
`grading` and any spec field.

`tests/firstparty_v1_tasks.py` is the other half of the picture and stays what
it is: helpers over the *checked-in* task set (`task_by_id`, `solution_diff`,
`visible_tests_pass`, `structural_half_passes`).

Node is required on the machine running these suites, the way pytest is.
Probed at v22.22.2 on 2026-08-19.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from ai_benchmark.firstparty_v1 import Task, load_task_set

#: The default task: `ratio(a, b)` is missing from `calc.ts`, so the held-out
#: test fails on the pristine repository and passes once it is written. Small
#: on purpose — a fixture varied by four later tickets should be one idea.
DEFAULT_TASK_ID = "exact-ratio-ts"

DEFAULT_PROMPT = "Add ratio(a, b) to calc.ts, returning a / b.\n"

DEFAULT_REPO: dict[str, str] = {
    "calc.ts": """\
export function half(x: number): number {
  return x / 2;
}
""",
}

DEFAULT_GRADING: dict[str, str] = {
    "calc.test.ts": """\
import test from "node:test";
import assert from "node:assert";

import { ratio } from "./calc.ts";

test("ratio divides", () => {
  assert.strictEqual(ratio(1, 2), 0.5);
});

test("ratio divides again", () => {
  assert.strictEqual(ratio(9, 3), 3);
});
""",
}

#: What solves the default task, as an edit to a workdir — the argument
#: `firstparty_v1_tasks.workdir_diff` takes.
SOLVED_CALC = """\
export function half(x: number): number {
  return x / 2;
}

export function ratio(a: number, b: number): number {
  return a / b;
}
"""


def typescript_task(
    root: Path,
    *,
    task_id: str = DEFAULT_TASK_ID,
    repo: Mapping[str, str] | None = None,
    grading: Mapping[str, str] | None = None,
    **spec_fields: Any,
) -> Task:
    """One synthetic TypeScript task under `root`, written and then loaded.

    `root` must hold this task and nothing else — it is handed to the real
    `load_task_set`, so the task goes through every check a checked-in one
    does. Two tasks in one test means two roots.

    `repo` and `grading` are file name → contents, relative to `repo/` and
    `grading/`, and a name with a `/` in it makes the directories it needs.
    Any further keyword lands in `task.yaml`, so a suite can declare a
    different category, drop `language`, or add a `construction` block without
    this signature growing a parameter for each.
    """
    task_dir = root / task_id
    spec: dict[str, Any] = {
        "id": task_id,
        "category": "feature-dev",
        "scale": "single-file",
        "surface": "application",
        "language": "typescript",
        "prompt": DEFAULT_PROMPT,
    }
    spec.update(spec_fields)
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8"
    )
    _write_tree(task_dir / "repo", DEFAULT_REPO if repo is None else repo)
    _write_tree(task_dir / "grading", DEFAULT_GRADING if grading is None else grading)
    [task] = load_task_set(root)
    return task


def solve(workdir: Path) -> None:
    """Write the function the default task asks for — the control every
    forgery test in this round is read against."""
    (workdir / "calc.ts").write_text(SOLVED_CALC, encoding="utf-8")


def _write_tree(directory: Path, files: Mapping[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, contents in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
