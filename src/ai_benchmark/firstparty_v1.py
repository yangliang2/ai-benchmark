"""First-party eval v1: task directories and execution-verified grading
(ticket #10). Sits beside v0 rather than replacing it — the two are separate
benchmarks and must never pool.

Where a v0 task is a prompt plus a check regex, a v1 task is a directory: the
prompt, a small hand-authored starting repository the agent works in, and
held-out grading tests the agent never sees. Grading runs those tests for
real — copy the pristine repo, apply the run's workdir diff, overlay the
canonical grading files over any same-path files the agent touched, run
pytest in a fresh temp dir with a timeout — so `resolved` is
execution-verified, the same standard as SWE-bench, not pattern-verified.

What the verdict is guaranteed to depend on: the held-out grading files, run
under a config pinned outside the workdir and with conftest loading off. An
agent cannot reach the verdict by writing tests at the grading files' paths
(they are overwritten), by hooking pytest from a conftest.py, or by smuggling
`addopts` through pytest.ini / tox.ini / setup.cfg / pyproject.toml. The
authoring rule that falls out of this: grading tests must be self-contained
and must never rely on a conftest.py. The lint runs the same invocation, so a
task that breaks the rule is caught on the pristine repo.

What it is not: a sandbox. Grading executes agent-written code in a local
subprocess with a timeout — the accepted limitation recorded in CONTEXT.md,
the same exposure as any local SWE-bench-style eval. Starting repositories
are stdlib-only, so grading needs no network and no installs.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ai_benchmark.dataset import IngestError
from ai_benchmark.schema import (
    LanguageStr,
    NonEmptyStr,
    Record,
    RecordValidationError,
    Scale,
    TaskCategory,
    validate_record,
)

BENCHMARK = "first-party-v1"

TASK_SPEC = "task.yaml"
REPO_DIR = "repo"
GRADING_DIR = "grading"

GRADE_TIMEOUT_S = 300

# The config grading runs under, pinned so nothing in the workdir is consulted.
_GRADING_CONFIG = "[pytest]\naddopts =\n"


class Grading(BaseModel):
    """Which held-out grading files assert behaviour rather than structure.

    Only refactor tasks need the split, and they name the behaviour files
    explicitly rather than relying on a naming convention: a mistyped
    convention would silently demote a behaviour test to a structural one and
    weaken the lint, whereas a mistyped path here fails to load.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    behaviour_tests: tuple[NonEmptyStr, ...] = ()


class Task(BaseModel):
    """One v1 first-party benchmark instance: a task directory holding the
    prompt, the pristine starting repository, and the held-out grading tests.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    category: TaskCategory
    scale: Scale
    language: LanguageStr | None = None
    prompt: NonEmptyStr
    grading: Grading = Grading()
    directory: Path

    @property
    def repo_dir(self) -> Path:
        """The pristine starting repository, copied fresh for every run."""
        return self.directory / REPO_DIR

    @property
    def grading_dir(self) -> Path:
        """The held-out grading files, canonical at grade time."""
        return self.directory / GRADING_DIR

    @property
    def grading_test_paths(self) -> tuple[str, ...]:
        """Every grading test, relative to the workdir it is overlaid into."""
        return tuple(
            sorted(
                str(path.relative_to(self.grading_dir))
                for path in self.grading_dir.rglob("test_*.py")
            )
        )

    @property
    def behaviour_test_paths(self) -> tuple[str, ...]:
        """The behaviour half of the suite, empty outside refactor tasks."""
        return tuple(sorted(self.grading.behaviour_tests))

    @model_validator(mode="after")
    def classified_and_split_by_category(self) -> Self:
        if self.category == "unclassified":
            raise ValueError(
                "first-party tasks are classified up front — they exist to fill "
                "known capability-matrix cells"
            )
        if self.category == "refactor" and not self.grading.behaviour_tests:
            raise ValueError(
                "a refactor task must name its behaviour tests: they are what "
                "must still pass on the pristine repo"
            )
        if self.category != "refactor" and self.grading.behaviour_tests:
            raise ValueError(
                f"only refactor tasks split grading into behaviour and structural "
                f"tests; {self.category} names behaviour_tests, which would exempt "
                "them from the must-fail-on-pristine invariant"
            )
        return self


class Run(BaseModel):
    """One raw run-log row: the v0 fields plus the workdir diff.

    The diff is the graded artifact — it is what grading replays — so `output`
    (the agent's final message) is metadata here, kept for reading runs back.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: NonEmptyStr
    agent: NonEmptyStr
    agent_version: str | None = None
    model: NonEmptyStr
    output: str
    diff: str
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    latency_s: float = Field(ge=0)
    turns: int = Field(ge=1)
    as_of: date


def load_task_set(root: Path) -> list[Task]:
    """Load and validate every v1 task directory under root.

    Anything malformed — an unreadable spec, an unclassified task, a missing
    starting repository, a behaviour test naming a file that is not there —
    fails loudly here, before any paid run reaches it. Ids are unique by
    construction, because each must match its own directory name.
    """
    task_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    if not task_dirs:
        raise IngestError(f"{root}: no task directories found")
    return [_load_task(task_dir) for task_dir in task_dirs]


def _load_task(task_dir: Path) -> Task:
    spec_path = task_dir / TASK_SPEC
    try:
        spec = yaml.safe_load(spec_path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise IngestError(f"{spec_path}: {error}") from error
    if not isinstance(spec, dict):
        raise IngestError(f"{spec_path}: expected a mapping of task fields")
    if "directory" in spec:
        raise IngestError(
            f"{spec_path}: 'directory' is the task's own location, not a spec field"
        )
    try:
        task = Task.model_validate(spec | {"directory": task_dir})
    except ValidationError as error:
        raise IngestError(f"{spec_path}: {error}") from error
    if task.id != task_dir.name:
        raise IngestError(
            f"{spec_path}: id {task.id!r} does not match its directory name "
            f"{task_dir.name!r} — a task is found by its directory, and records "
            "carry the id, so the two drifting apart makes runs untraceable"
        )
    _check_task_layout(task)
    return task


def _check_task_layout(task: Task) -> None:
    """The parts of a task that live on disk rather than in its spec."""
    if not task.repo_dir.is_dir() or not any(task.repo_dir.iterdir()):
        raise IngestError(
            f"{task.id}: {REPO_DIR}/ is missing or empty — a v1 task gives the "
            "agent a starting repository"
        )
    if not task.grading_test_paths:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/ holds no test_*.py — a v1 task is graded "
            "by running held-out tests"
        )
    missing = sorted(set(task.behaviour_test_paths) - set(task.grading_test_paths))
    if missing:
        raise IngestError(
            f"{task.id}: behaviour test(s) not in {GRADING_DIR}/: {missing}"
        )
    if task.behaviour_test_paths and not set(task.grading_test_paths) - set(
        task.behaviour_test_paths
    ):
        raise IngestError(
            f"{task.id}: every grading test is a behaviour test, so nothing "
            "asserts that the restructuring happened"
        )


def load_runs(path: Path) -> list[Run]:
    try:
        return [
            Run.model_validate(json.loads(line))
            for line in path.read_text().splitlines()
            if line.strip()
        ]
    except (json.JSONDecodeError, ValidationError) as error:
        raise IngestError(f"{path}: {error}") from error


# --- execution-verified grading ------------------------------------------------


def grade(task: Task, diff: str, *, timeout_s: int = GRADE_TIMEOUT_S) -> bool:
    """Whether the run that produced this diff resolved the task.

    The whole grading suite runs against a fresh copy of the pristine repo
    with the diff applied and the canonical grading files laid over the top.
    Resolved means pytest exited 0; a failure, a collection error or a timeout
    all mean unresolved. A diff git cannot apply is not a verdict at all — it
    is a broken run log, and fails loudly.
    """
    return _run_grading(task, diff, task.grading_test_paths, timeout_s=timeout_s)


def _run_grading(
    task: Task, diff: str, targets: Sequence[str], *, timeout_s: int
) -> bool:
    _require_pytest()
    with tempfile.TemporaryDirectory(prefix="ai-bench-grade-") as name:
        # The pinned config sits beside the workdir rather than in it: a diff
        # can only write inside the workdir, so it can never reach this file.
        config = Path(name) / "grading-pytest.ini"
        config.write_text(_GRADING_CONFIG, encoding="utf-8")
        workdir = Path(name) / "workdir"
        workdir.mkdir()
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        _apply_diff(task, diff, workdir)
        # Canonical last: whatever the agent wrote at a grading file's path is
        # overwritten, so the graded tests are always the held-out ones.
        shutil.copytree(task.grading_dir, workdir, dirs_exist_ok=True)
        return _pytest_passes(workdir, targets, config=config, timeout_s=timeout_s)


def _apply_diff(task: Task, diff: str, workdir: Path) -> None:
    if not diff.strip():
        return
    # git apply resolves paths against the enclosing repository, which it finds
    # by walking up from the workdir. Making the workdir a repository of its own
    # stops that walk here, so a temp dir that happens to sit inside a checkout
    # cannot let a logged diff escape into it.
    _git(task, ["init", "-q", "."], workdir)
    _git(task, ["apply", "--whitespace=nowarn"], workdir, stdin=diff)


def _git(
    task: Task, arguments: list[str], workdir: Path, *, stdin: str | None = None
) -> None:
    try:
        process = subprocess.run(
            ["git", *arguments],
            input=stdin,
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise IngestError(
            f"{task.id}: cannot run git {arguments[0]}: {error}"
        ) from error
    if process.returncode != 0:
        raise IngestError(
            f"{task.id}: git {arguments[0]} failed on the logged diff: "
            f"{process.stderr.strip()}"
        )


def _pytest_passes(
    workdir: Path, targets: Sequence[str], *, config: Path, timeout_s: int
) -> bool:
    """Run the named tests in workdir. True only on a clean exit 0.

    The verdict must depend on the held-out tests alone, so pytest is given no
    chance to read anything the agent wrote outside them: `-c` pins the config
    file, which stops pytest.ini / tox.ini / setup.cfg / pyproject.toml in the
    workdir from contributing `addopts` (and with it arbitrary plugins), and
    `--noconftest` stops conftest.py at any depth from running hooks. Both
    directions matter: without them a conftest can forge exit status 0, and a
    stray broken one can sink a correct solution.
    """
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-q",
             "-c", str(config), "--noconftest", "--rootdir", str(workdir),
             "-p", "no:cacheprovider", *targets],
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    except OSError as error:
        raise IngestError(f"cannot run pytest: {error}") from error
    return process.returncode == 0


def _require_pytest() -> None:
    """Grading shells out to pytest; without it every task would score 0.0 and
    look like a very bad model rather than a broken environment."""
    if importlib.util.find_spec("pytest") is None:
        raise IngestError(
            f"pytest is not installed in {sys.executable} — v1 grading runs the "
            "task's tests in a subprocess and cannot grade without it"
        )


# --- task-set lint: the authoring invariants ----------------------------------


def lint_task_set(
    tasks: list[Task], *, timeout_s: int = GRADE_TIMEOUT_S
) -> list[str]:
    """Check every task's authoring invariants and describe what is wrong.

    The invariants are checked by running the grading tests on the pristine
    repository, not by reading them: a task whose grading tests already pass
    grades every agent as resolved, and a refactor whose behaviour tests
    already fail can never be solved. Both are cheap to catch here and
    expensive to discover in the middle of a paid sweep.
    """
    problems = []
    for task in tasks:
        if _run_grading(task, "", task.grading_test_paths, timeout_s=timeout_s):
            problems.append(
                f"{task.id}: the grading tests already pass on the pristine repo — "
                "there is nothing left for an agent to do"
            )
        if task.behaviour_test_paths and not _run_grading(
            task, "", task.behaviour_test_paths, timeout_s=timeout_s
        ):
            problems.append(
                f"{task.id}: the behaviour tests fail on the pristine repo — a "
                "refactor task must start from behaviour that already works"
            )
    return problems


def evaluate(
    tasks: list[Task],
    runs: list[Run],
    source: str,
    *,
    timeout_s: int = GRADE_TIMEOUT_S,
) -> list[Record]:
    """Grade each run's diff by execution and emit first-party records.

    Runs for unknown tasks and duplicate runs fail loudly — either would
    otherwise vanish or overwrite silently at merge time.
    """
    by_id = {task.id: task for task in tasks}
    unknown = sorted({run.task_id for run in runs} - by_id.keys())
    if unknown:
        raise IngestError(f"run log references unknown task(s): {unknown}")
    duplicates = [
        key
        for key, count in Counter((r.task_id, r.agent, r.model) for r in runs).items()
        if count > 1
    ]
    if duplicates:
        raise IngestError(
            f"duplicate runs would silently overwrite each other: {sorted(duplicates)}"
        )

    records = []
    for run in runs:
        task = by_id[run.task_id]
        resolved = grade(task, run.diff, timeout_s=timeout_s)
        try:
            records.append(
                validate_record(
                    {
                        "category": task.category,
                        "scale": task.scale,
                        "language": task.language,
                        "agent": run.agent,
                        "agent_version": run.agent_version,
                        "model": run.model,
                        "benchmark": BENCHMARK,
                        "instance_id": task.id,
                        "quality_metric": "resolved",
                        "quality_value": 1.0 if resolved else 0.0,
                        "tokens_in": run.tokens_in,
                        "tokens_out": run.tokens_out,
                        "cost_usd": run.cost_usd,
                        "latency_s": run.latency_s,
                        "turns": run.turns,
                        "source": source,
                        "source_type": "first-party",
                        "confidence": "high",
                        "as_of": run.as_of,
                    }
                )
            )
        except RecordValidationError as error:
            raise IngestError(
                f"{run.task_id} ({run.agent} x {run.model}): {error}"
            ) from error
    return records
