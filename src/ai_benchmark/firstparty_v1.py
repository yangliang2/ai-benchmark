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

What the verdict does not depend on: anything the agent wrote *around* the
grading tests. Tests written at a grading file's path are overwritten; a
conftest.py cannot hook the run and `addopts` cannot be smuggled through
pytest.ini / tox.ini / setup.cfg / pyproject.toml, because the config is
pinned outside the workdir and conftest loading is off; a file added to the
workdir cannot shadow a standard-library module the grading tests measure
against, because the workdir sits behind the standard library on sys.path;
and a run that ends before the tests finish cannot pass by accident, because
the verdict reads a report written outside the workdir rather than the exit
status alone.

Two authoring rules fall out of this, and both are checked rather than left to
discipline: grading tests must be self-contained and never rely on a
conftest.py, which the lint catches on the pristine repo because it runs the
same invocation; and a starting repository must not name a top-level module
after one in the standard library, which the loader rejects outright. The
loader has to do that one, because the lint cannot: when the standard-library
module does not happen to satisfy the grading tests, such a task fails on the
pristine repo exactly like a good task, passes the lint, and is then
impossible for any agent to solve.

What it is not: a sandbox — and that is a real limit, not a formality.
Grading executes agent-written code in the same process tree as the oracle,
so those defences stop an honest-but-messy agent, not a deliberately
adversarial one: code that runs during a test can still reach the report the
verdict is read from (an atexit handler that rewrites it, say) and forge a
pass. Ruling that out needs process-level isolation, which this grader does
not have. That residual is exactly what the accepted not-a-sandbox limitation
recorded in CONTEXT.md means in practice — the same exposure as any local
SWE-bench-style eval. Starting repositories are stdlib-only, so grading needs
no network and no installs.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Self
from xml.etree import ElementTree

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

# Loaded with -p from outside the workdir. Python is started with -P and pytest
# with --import-mode=importlib so that nothing puts the workdir on sys.path;
# this puts it back at the end, behind the standard library.
_PATH_PLUGIN_NAME = "gradingpath"
_PATH_PLUGIN = """\
import sys

WORKDIR = {workdir!r}


def pytest_configure(config):
    sys.path.append(WORKDIR)
"""


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
    if collisions := _stdlib_collisions(task.repo_dir):
        raise IngestError(
            f"{task.id}: {REPO_DIR}/ names {collisions} after standard-library "
            "module(s) — grading keeps the standard library ahead of the workdir "
            "on sys.path, so these are invisible at grade time and the task can "
            "lint clean while being impossible to solve"
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


def _stdlib_collisions(repo_dir: Path) -> list[str]:
    """Top-level names in the starting repository the standard library owns.

    Only the top level matters: that is what grading puts on sys.path, and a
    module deeper in a package is reached through its package name.
    """
    collisions = []
    for entry in sorted(repo_dir.iterdir()):
        if entry.is_dir():
            importable = entry.name
        elif entry.suffix == ".py":
            importable = entry.stem
        else:
            continue
        if importable in sys.stdlib_module_names:
            collisions.append(entry.name)
    return collisions


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
    Resolved means every grading test ran and passed, as far as a grader that
    shares a process tree with the code it is grading can tell: a failure, a
    collection error, a skip, a run that ended early and a timeout all mean
    unresolved, but a deliberately adversarial diff can still forge a pass
    from inside that process (see the module docstring). A diff git cannot
    apply is not a verdict at all — it is a broken run log, and fails loudly.
    """
    return _run_grading(task, diff, task.grading_test_paths, timeout_s=timeout_s)


def _run_grading(
    task: Task, diff: str, targets: Sequence[str], *, timeout_s: int
) -> bool:
    _require_pytest()
    with tempfile.TemporaryDirectory(prefix="ai-bench-grade-") as name:
        # Everything the grader relies on sits beside the workdir rather than
        # in it: a diff can only write inside the workdir, so it cannot reach
        # the pinned config, the sys.path plugin, or the report.
        root = Path(name)
        workdir = root / "workdir"
        workdir.mkdir()
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        _apply_diff(task, diff, workdir)
        # Canonical last: whatever the agent wrote at a grading file's path is
        # overwritten, so the graded tests are always the held-out ones.
        shutil.copytree(task.grading_dir, workdir, dirs_exist_ok=True)
        return _pytest_passes(root, workdir, targets, timeout_s=timeout_s)


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
    root: Path, workdir: Path, targets: Sequence[str], *, timeout_s: int
) -> bool:
    """Run the named tests in workdir. True only if they all actually passed.

    The verdict must depend on the held-out tests alone, so pytest is given no
    chance to read anything else the agent wrote:

    - `-c` pins the config file, so pytest.ini / tox.ini / setup.cfg /
      pyproject.toml in the workdir cannot contribute `addopts` (and with it
      arbitrary plugins), and `--noconftest` stops conftest.py at any depth
      from running hooks. Both directions matter: without them a conftest can
      forge exit status 0, and a stray broken one can sink a correct solution.
    - `-P` and `--import-mode=importlib` keep the workdir off sys.path, and
      the pinned plugin appends it again *behind* the standard library. A file
      the agent added cannot then shadow a stdlib module the grading tests
      measure against, while the task's own modules stay importable.
    - the report is checked rather than the exit status alone, because agent
      code runs during collection and one os._exit(0) there is otherwise
      indistinguishable from a clean pass. This catches an accidental early
      exit and a corrupted run, not an adversary: the report is written by
      the same process tree, so code that means to can rewrite it.
    """
    config = root / "grading-pytest.ini"
    config.write_text(_GRADING_CONFIG, encoding="utf-8")
    harness = root / "harness"
    harness.mkdir()
    (harness / f"{_PATH_PLUGIN_NAME}.py").write_text(
        _PATH_PLUGIN.format(workdir=str(workdir)), encoding="utf-8"
    )
    report = root / "report.xml"
    inherited = os.environ.get("PYTHONPATH")
    try:
        process = subprocess.run(
            [sys.executable, "-P", "-m", "pytest", "-q",
             "-c", str(config), "--noconftest", "--rootdir", str(workdir),
             "--import-mode=importlib", f"--junitxml={report}",
             "-p", _PATH_PLUGIN_NAME, "-p", "no:cacheprovider", *targets],
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=timeout_s,
            check=False,
            env=os.environ
            | {
                "PYTHONPATH": os.pathsep.join(
                    [str(harness), *([inherited] if inherited else [])]
                )
            },
        )
    except subprocess.TimeoutExpired:
        return False
    except OSError as error:
        raise IngestError(f"cannot run pytest: {error}") from error
    return process.returncode == 0 and _report_shows_every_test_passed(report)


def _report_shows_every_test_passed(report: Path) -> bool:
    """Evidence from outside the workdir that the tests really ran.

    pytest writes the report when the session ends, so a run that killed the
    process part-way leaves none — and a run that finished but skipped
    everything leaves one that says so. Evidence, not proof: the report is
    written by the graded process itself, so it is only as trustworthy as
    that process (see _pytest_passes).
    """
    try:
        suites = list(ElementTree.parse(report).getroot().iter("testsuite"))
    except (OSError, ElementTree.ParseError):
        return False
    counts = {
        field: sum(int(suite.get(field, "0")) for suite in suites)
        for field in ("tests", "failures", "errors", "skipped")
    }
    return counts["tests"] > 0 and not any(
        counts[field] for field in ("failures", "errors", "skipped")
    )


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
