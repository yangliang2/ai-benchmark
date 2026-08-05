"""First-party eval v1: task directories, execution-verified grading
(ticket #10) and the tools-enabled live runner (ticket #11). Sits beside v0
rather than replacing it — the two are separate benchmarks and must never
pool.

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

A third group of rules is checked here for the same reason, though it is read
rather than run: the construction metadata recording how a task was built.
Which knob a task sets, what its author predicted before the first paid run,
where a vendored starting repository came from and which knob each edit to it
sets are all claims that cost nothing to check now and cannot be repaired once
the sweep is paid for — a prediction registered after the outcome is not a
prediction, and a task family whose variants differ in more than the one knob
they vary explains nothing. So the loader validates each task's block, and the
lint checks what only the set as a whole can show: that every task outside the
frozen baseline declares one, that no baseline control quietly acquires one,
and that each family is one underlying change with one knob moving across it.

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
from typing import Literal, Self
from urllib.parse import urlparse
from xml.etree import ElementTree

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import (
    RUN_TIMEOUT_S,
    claude_headless_json,
    claude_version,
    local_today,
    run_from_claude_json,
)
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

# The workdir's ignore file belongs to the live runner (which writes and owns
# it), so the loader refuses tasks that ship one of their own.
_IGNORE_FILE = ".gitignore"

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


# --- construction metadata: how a task was built, and what it predicts ---------

# The difficulty knobs of docs/design/task-difficulty-and-ex-ante-profiles.md
# section 9, and the levels each one is settable to. A knob maps to () when
# the design note has not enumerated its ladder yet: its level is then recorded
# as written, and nothing can check that two tasks setting it mean the same
# thing. Only knobs the note actually enumerates get a ladder here — inventing
# one would silently fix a vocabulary the experiment has not chosen.
KNOB_LEVELS: dict[str, tuple[str, ...]] = {
    "K1": ("acceptance", "description", "intent"),  # decision openness
    "K2": (),  # implicit requirements
    "K3": (),  # contradiction traps
    "K4": (),  # read-set / write-set ratio
    "K5": (),  # with or against the architectural grain
    "K6": (),  # haunted areas
    "K7": (),  # invariant density
    "K8": ("covered", "partial", "bare", "misleading"),  # safety-net quality
    "K9": ("none", "single"),  # crux depth
    "K10": (),  # coordination width
    "K11": (),  # detection distance
}

# The operational difficulty ladder a prediction is expressed against: the
# rungs of the model ladder the first sweep already measures, so a prediction
# is checkable against run logs without any new measurement.
Rung = Literal["haiku-solvable", "sonnet-only", "unsolved"]

# The 22 tasks authored before the knob experiment. Their *absence* of a
# construction block is what "zero-knob baseline control" means, so the set has
# to be frozen and named: without it the lint cannot tell a baseline control
# from a knob-experiment task whose author declared nothing.
BASELINE_TASK_IDS = frozenset({
    "calc-infix-evaluator",
    "cart-extract-coupon-policy",
    "checkout-discount-codes",
    "docstore-json-pointer",
    "exporters-pull-up-base-class",
    "gradebook-split-compute-from-format",
    "jobrunner-dependency-order",
    "ledger-split-formatting",
    "logparse-extract-timestamp-parsing",
    "matcher-brace-expansion",
    "measures-merge-duplicate-converters",
    "metrics-dispatch-table",
    "microtemplate-for-loops",
    "pipeline-move-retry-policy",
    "slugger-unique-slugs",
    "spans-subtract-gaps",
    "spendreport-invert-storage-dependency",
    "tablecli-filter-command",
    "tasktrack-reshape-parse-result",
    "textdoc-split-render-flag",
    "wordcount-top-words",
    "workflow-guarded-transitions",
})


def _known_knob(knob_id: str) -> str:
    if knob_id not in KNOB_LEVELS:
        raise ValueError(
            f"unknown difficulty knob {knob_id!r} — the knobs are "
            f"{sorted(KNOB_LEVELS, key=lambda name: int(name[1:]))}, defined in "
            "docs/design/task-difficulty-and-ex-ante-profiles.md section 9"
        )
    return knob_id


class KnobActivation(BaseModel):
    """One difficulty knob this task sets, and the level it is set to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    level: NonEmptyStr

    @model_validator(mode="after")
    def level_is_on_the_knobs_ladder(self) -> Self:
        levels = KNOB_LEVELS[_known_knob(self.id)]
        if levels and self.level not in levels:
            raise ValueError(
                f"{self.id} level {self.level!r} is not one of {list(levels)} — "
                "reconciliation groups outcomes by level, and a free-text level "
                "would be a group of one"
            )
        return self


class Prediction(BaseModel):
    """The author's pre-registered difficulty prediction for this task.

    Registered before the task's first paid run, which is what makes the knob
    theory falsifiable rather than fitted to the sweep afterwards; the run
    log's append-only timeline is the audit trail that it came first.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rung: Rung
    rationale: NonEmptyStr


class Modification(BaseModel):
    """One surgical edit made to a vendored substrate, and the knob it sets.

    Naming the knob is the point: an edit that answers to no knob is
    difficulty the experiment cannot attribute to anything.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    knob: NonEmptyStr
    description: NonEmptyStr

    @model_validator(mode="after")
    def modification_names_a_knob(self) -> Self:
        _known_knob(self.knob)
        return self


class Substrate(BaseModel):
    """Where a vendored starting repository came from, and what we did to it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: NonEmptyStr
    commit: NonEmptyStr
    license: NonEmptyStr
    modifications: tuple[Modification, ...] = ()

    @model_validator(mode="after")
    def provenance_is_followable_and_pinned(self) -> Self:
        origin = urlparse(self.origin)
        if origin.scheme not in ("http", "https") or not origin.netloc:
            raise ValueError(
                f"substrate origin {self.origin!r} is not an http(s) URL naming a "
                "host — provenance has to be followable by whoever audits the "
                "snapshot, and a scheme on its own leads nowhere"
            )
        if len(self.commit) != 40 or set(self.commit) - set("0123456789abcdef"):
            raise ValueError(
                f"substrate commit {self.commit!r} is not a full 40-character "
                "lowercase hex commit id — a branch or tag moves under the "
                "vendored snapshot and only a full id pins it, and the pin is "
                "written the one canonical way so two records of one commit "
                "cannot read as two commits"
            )
        return self


class Construction(BaseModel):
    """How a task was built: which difficulty knobs it sets, which family it
    belongs to, which task it is paired with, what its author predicted, and —
    for a vendored starting repository — where that repository came from.

    A task with no construction block at all is a zero-knob baseline control.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    knobs: tuple[KnobActivation, ...]
    family: NonEmptyStr | None = None
    # A free grouping id shared by the two tasks meant to be read against each
    # other — a crux task and its control. Nothing but the grouping: unlike a
    # family it constrains no level, it only records the pairing, which would
    # otherwise live in a table outside the task set and drift from it.
    pair: NonEmptyStr | None = None
    prediction: Prediction
    substrate: Substrate | None = None

    @property
    def levels(self) -> dict[str, str]:
        """The level each knob is set to, keyed by knob id."""
        return {knob.id: knob.level for knob in self.knobs}

    @model_validator(mode="after")
    def each_knob_set_once_and_at_least_one(self) -> Self:
        if not self.knobs:
            raise ValueError(
                "a construction block sets at least one knob — a task that sets "
                "none is a zero-knob baseline control, which is expressed by "
                "carrying no construction block at all"
            )
        repeated = sorted(
            knob_id
            for knob_id, count in Counter(knob.id for knob in self.knobs).items()
            if count > 1
        )
        if repeated:
            raise ValueError(
                f"knob(s) {repeated} set more than once — a task sets each knob "
                "to one level, or the level it was run at is ambiguous"
            )
        return self

    @model_validator(mode="after")
    def every_modification_sets_a_knob_this_task_activates(self) -> Self:
        """A planted edit answers to one of this task's own knob activations.

        Naming any known knob is not enough: an edit setting a knob the task
        never activates is difficulty that reaches the agent while sitting
        outside the task's declared profile, so reconciliation attributes the
        outcome to knobs the substrate has quietly gone beyond.
        """
        if self.substrate is None:
            return self
        unactivated = sorted(
            {
                modification.knob
                for modification in self.substrate.modifications
                if modification.knob not in self.levels
            }
        )
        if unactivated:
            raise ValueError(
                f"substrate modification(s) set knob(s) {unactivated} this task "
                f"does not activate — it activates {sorted(self.levels)}, and an "
                "edit outside that set plants difficulty the task's own profile "
                "does not declare"
            )
        return self


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
    construction: Construction | None = None
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
    if (task.repo_dir / _IGNORE_FILE).exists():
        raise IngestError(
            f"{task.id}: {REPO_DIR}/ ships a {_IGNORE_FILE} — the live runner "
            "owns the workdir's ignore file and would silently replace this "
            "one, so the agent would see a repository that differs from the "
            "pristine one grading applies the diff to"
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
    doing = "on the logged diff"
    _git(task, ["init", "-q", "."], workdir, doing=doing)
    _git(task, ["apply", "--whitespace=nowarn"], workdir, stdin=diff, doing=doing)


# Every git call — grading and live capture alike — runs with the operator's
# global and system configuration masked out. Otherwise the artifact varies
# with the machine: a global diff.noprefix strips the a/ b/ prefixes replay's
# `git apply` expects (silent at capture, an IngestError at grading), and a
# core.excludesFile silently drops agent-written files from the diff.
_GIT_ISOLATION = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def _git(
    task: Task,
    arguments: list[str],
    workdir: Path,
    *,
    stdin: str | None = None,
    extra_env: dict[str, str] | None = None,
    doing: str,
) -> str:
    try:
        process = subprocess.run(
            ["git", *arguments],
            input=stdin,
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=60,
            check=False,
            env=os.environ | _GIT_ISOLATION | (extra_env or {}),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise IngestError(
            f"{task.id}: cannot run git {arguments[0]}: {error}"
        ) from error
    except UnicodeDecodeError as error:
        # No NUL bytes, so git diffed it as text — but the bytes are not
        # UTF-8, and the run log is UTF-8 JSON. Refusing loudly beats logging
        # a row that cannot round-trip through the log.
        raise IngestError(
            f"{task.id}: git {arguments[0]} produced output that is not UTF-8 "
            f"({error}) — an agent-written file is non-UTF-8 text, which a v1 "
            "run log cannot carry"
        ) from error
    if process.returncode != 0:
        raise IngestError(
            f"{task.id}: git {arguments[0]} failed {doing}: "
            f"{process.stderr.strip()}"
        )
    return process.stdout


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

    Most of them are checked by running the grading tests on the pristine
    repository, not by reading them: a task whose grading tests already pass
    grades every agent as resolved, and a refactor whose behaviour tests
    already fail can never be solved. Both are cheap to catch here and
    expensive to discover in the middle of a paid sweep.

    The construction invariants are read rather than run, but belong here for
    the same reason: an undeclared knob, an unregistered prediction or a
    family whose variants differ in more than the knob they vary costs nothing
    to catch now and cannot be repaired afterwards — a prediction registered
    once the outcome is known is not a prediction, and a sweep is only paid
    for once.
    """
    problems = _family_problems(tasks) + _pair_problems(tasks)
    for task in tasks:
        problems.extend(construction_problems(task))
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


def construction_problems(task: Task) -> list[str]:
    """What is wrong with this task's declaration of how it was built.

    The rule runs both ways, because the two states mean opposite things and
    each is expressed by the presence or absence of the same block: a task
    outside the frozen baseline must declare its construction, and a baseline
    task must not, or reconciliation can read it as neither control nor
    knob-experiment task.

    Public because reconciliation checks it too, before reading a task set as
    controls and predictions. One invariant, one implementation: two copies of
    this rule could disagree about which tasks are controls.
    """
    declared = task.construction is not None
    baseline = task.id in BASELINE_TASK_IDS
    if not declared and not baseline:
        return [(
            f"{task.id}: no construction block — a task authored after the "
            "zero-knob baseline declares which difficulty knob(s) it sets and "
            "its pre-registered difficulty prediction, because absence of the "
            "block already means baseline control"
        )]
    if declared and baseline:
        return [(
            f"{task.id}: a zero-knob baseline control carries a construction "
            "block — the absence of the block is the whole of what makes these "
            "22 tasks controls, so one that declares knobs is a control "
            "reconciliation would read against itself"
        )]
    return []


def _family_problems(tasks: list[Task]) -> list[str]:
    """What is wrong with each declared task family, if anything.

    A family exists to isolate one knob: one underlying change authored as
    several variants, one knob varied, everything else held constant. All
    three of those are checked, because all three are what "isolate" means — a
    family varying two knobs attributes its outcomes to neither; one whose
    variants start from different repositories, grade against different tests
    or classify themselves differently varies the diff target and the matrix
    cell alongside the knob; and one whose variants are identical where the
    knob is supposed to move declares a gradient none of them produce. None of
    it is repairable once the runs are paid for.

    What is deliberately not required is a full ladder: a family may sweep
    part of one (K8 covered→bare→misleading, skipping partial) as long as its
    levels are distinct. It then says less than a complete sweep would, and
    that is the author's call to make.
    """
    families: dict[str, dict[str, Construction]] = {}
    task_of = {task.id: task for task in tasks}
    for task in tasks:
        if task.construction is not None and task.construction.family is not None:
            families.setdefault(task.construction.family, {})[task.id] = (
                task.construction
            )

    problems = []
    for family, members in sorted(families.items()):
        ids = sorted(members)
        levels = [members[task_id].levels for task_id in ids]
        variants = {task_id: task_of[task_id] for task_id in ids}
        if len(ids) < 2:
            problems.append(
                f"family {family!r} holds only {ids} — a family isolates a knob "
                "by varying it, which takes at least two variants"
            )
            continue
        divergence = _constancy_problem(family, variants)
        if divergence is not None:
            problems.append(divergence)
            continue
        if len({frozenset(level) for level in levels}) > 1:
            problems.append(
                f"family {family!r} members {ids} do not set the same knobs, so "
                "nothing across the family is held constant"
            )
            continue
        varied = sorted(
            knob_id
            for knob_id in levels[0]
            if len({level[knob_id] for level in levels}) > 1
        )
        if len(varied) != 1:
            problems.append(
                f"family {family!r} varies {varied} across {ids} — a family "
                "varies exactly one knob and holds the rest constant"
            )
            continue
        [knob_id] = varied
        set_to = [level[knob_id] for level in levels]
        if len(set(set_to)) != len(set_to):
            problems.append(
                f"family {family!r} has two members at the same level of "
                f"{knob_id} ({sorted(set_to)} across {ids}) — one level is one "
                "variant, however many task directories say otherwise"
            )
            continue
        gradient = _shared_prompt_problem(family, variants)
        if gradient is not None:
            problems.append(gradient)
    return problems


def _pair_problems(tasks: list[Task]) -> list[str]:
    """What is wrong with each declared pair, if anything.

    A pair id records that two tasks are meant to be read against each other —
    a planted crux and the control built beside it. Exactly two, because "the
    pair" names nothing once a third task joins it; starting from the same
    repository, because a control pitched on different terrain controls for
    the terrain as well as for the knob; and classified the same way, because
    records inherit the task's annotations, so a pair that disagrees about
    them is read across capability-matrix cells that are never compared.
    Nothing else is asked of it: the levels the two declare are the knob's
    business, not the grouping's.
    """
    paired: dict[str, list[Task]] = {}
    for task in tasks:
        if task.construction is not None and task.construction.pair is not None:
            paired.setdefault(task.construction.pair, []).append(task)

    problems = []
    for pair, members in sorted(paired.items()):
        ids = sorted(task.id for task in members)
        if len(members) != 2:
            problems.append(
                f"pair {pair!r} holds {ids} — a pair is the two tasks read "
                "against each other, and any other number leaves it undefined "
                "which two are being compared"
            )
            continue
        one, other = sorted(members, key=lambda task: task.id)
        held, variant = _annotations(one), _annotations(other)
        divergence = next(
            (field for field, value in held.items() if variant[field] != value), None
        )
        if divergence is not None:
            problems.append(
                f"pair {pair!r} does not hold {divergence} constant: {one.id} "
                f"declares {held[divergence]!r} and {other.id} declares "
                f"{variant[divergence]!r} — a crux task and its control are one "
                "reading, so they belong in one capability-matrix cell"
            )
            continue
        if _tree_bytes(one.repo_dir) != _tree_bytes(other.repo_dir):
            problems.append(
                f"pair {pair!r} members {ids} do not start from the same "
                f"{REPO_DIR}/ — a difference in outcome between them is then a "
                "difference in where the work was asked as well as in what was "
                "asked, which is the one thing a pair exists to rule out"
            )
    return problems


def _annotations(task: Task) -> dict[str, str | None]:
    """What places a task in the capability matrix, as the family lint reads
    it: the classification a record inherits and groups by."""
    return {
        "category": task.category,
        "scale": task.scale,
        "language": task.language,
    }


def _constancy_problem(family: str, members: dict[str, Task]) -> str | None:
    """The first thing two members of a family differ in but must not.

    Held constant is read off the tasks rather than trusted to authoring
    discipline. The variants are deliberately self-contained copies of one
    starting repository and one grading suite, so nothing but a check like
    this stops them drifting apart, and a family whose variants have drifted
    still lints clean on every knob rule while measuring a different change in
    each member. The annotations go with them: records inherit category, scale
    and language from the task, so variants that disagree scatter one family
    across capability-matrix cells that are never compared — and since the
    repositories and grading suites are identical, at least one of those
    annotations is simply wrong.
    """
    [first, *rest] = sorted(members)
    held_annotations = _annotations(members[first])
    for task_id in rest:
        variant_annotations = _annotations(members[task_id])
        for field, held_value in held_annotations.items():
            if variant_annotations[field] != held_value:
                return (
                    f"family {family!r} does not hold {field} constant: {first} "
                    f"declares {held_value!r} and {task_id} declares "
                    f"{variant_annotations[field]!r} — the variants of one "
                    "family are one change at several knob levels, so they "
                    "belong in one capability-matrix cell"
                )
    for name in (REPO_DIR, GRADING_DIR):
        held = _tree_bytes(members[first].directory / name)
        for task_id in rest:
            variant = _tree_bytes(members[task_id].directory / name)
            differing = sorted(
                path
                for path in held.keys() | variant.keys()
                if held.get(path) != variant.get(path)
            )
            if differing:
                return (
                    f"family {family!r} does not hold {name}/ constant: {first} "
                    f"and {task_id} differ at {differing[0]!r} — a family is one "
                    "underlying change seen at several knob levels, so a variant "
                    "that starts or grades differently varies the diff target too"
                )
    return None


def _shared_prompt_problem(family: str, members: dict[str, Task]) -> str | None:
    """Two members of a family given the very same prompt.

    Everything else about a family is held identical on purpose, so the prompt
    is where a spec-side knob is actually set: two variants declaring
    different levels of it while shipping the same prompt describe a gradient
    that exists in the metadata and nowhere in what the agent is asked. The
    sweep would then read the two identical runs as evidence about the knob —
    either separation that is noise, or none, killing a knob that was never
    turned.
    """
    written_by: dict[str, str] = {}
    for task_id in sorted(members):
        prompt = members[task_id].prompt
        if prompt in written_by:
            return (
                f"family {family!r} gives {written_by[prompt]} and {task_id} the "
                "same prompt while declaring different levels — with everything "
                "else held constant the prompt is where the knob moves, so the "
                "declared gradient is not in anything the agent is asked"
            )
        written_by[prompt] = task_id
    return None


def _tree_bytes(root: Path) -> dict[str, bytes]:
    """Every file under root by relative path, for comparing whole trees."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


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


# --- live runner: tools-enabled claude-code in a fresh workdir per run ---------


# Written into the workdir as _IGNORE_FILE before the initial commit. A v1
# agent is expected to run the repo's tests, and the bytecode caches that
# leaves behind are binary junk: not part of any solution, and (unlike a
# deliberate binary file, which --binary capture preserves) worth keeping out
# of the graded artifact entirely rather than dragging through every replay.
_WORKDIR_IGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\n"

# The initial commit must succeed on machines with no git identity configured,
# and must not consult user config that could block it (signing, hooks).
_COMMIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "ai-bench",
    "GIT_AUTHOR_EMAIL": "eval@ai-bench.invalid",
    "GIT_COMMITTER_NAME": "ai-bench",
    "GIT_COMMITTER_EMAIL": "eval@ai-bench.invalid",
}


def run_live(
    tasks: list[Task],
    models: list[str],
    log_path: Path,
    *,
    timeout_s: int = RUN_TIMEOUT_S,
) -> list[Run]:
    """Run every task through tools-enabled claude-code headless per model.

    Each run gets a fresh isolated workdir seeded from the task's starting
    repository, and its row — the workdir diff against the initial commit as
    the graded artifact, plus the CLI's exact measurements — is appended to
    the raw run log the moment the run completes, so a sweep that dies
    part-way keeps every run already paid for. Unlike v0, tools stay enabled:
    the run is genuinely multi-turn, editing the repository it was given.
    Setting sources stay disabled.
    """
    if log_path.exists():
        raise IngestError(
            f"run log {log_path} already exists — replay it, or pass a fresh --log"
        )
    version = claude_version()
    today = local_today()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    runs = []
    with log_path.open("x", encoding="utf-8") as log:
        for model in models:
            for task in tasks:
                run = _run_task_live(
                    task, model,
                    agent_version=version, as_of=today, timeout_s=timeout_s,
                )
                log.write(json.dumps(run.model_dump(mode="json"), sort_keys=True) + "\n")
                log.flush()
                runs.append(run)
    return runs


def _run_task_live(
    task: Task, model: str, *, agent_version: str, as_of: date, timeout_s: int
) -> Run:
    with tempfile.TemporaryDirectory(prefix="ai-bench-live-") as name:
        workdir = Path(name) / "workdir"
        shutil.copytree(task.repo_dir, workdir)
        initial = _commit_pristine(task, workdir)
        payload = claude_headless_json(
            task.id, task.prompt, model, workdir, tools=True, timeout_s=timeout_s
        )
        diff = _capture_workdir_diff(task, workdir, initial)
    base = run_from_claude_json(
        task.id, model, payload, agent_version=agent_version, as_of=as_of
    )
    # A v1 Run is v0's fields plus the diff, and the dump keeps that coupling
    # in one place. mypy cannot see through the **dump, but Run's
    # extra="forbid" turns any v0 field this model does not declare into a
    # loud runtime error rather than silent drift.
    return Run(**base.model_dump(), diff=diff)


def _commit_pristine(task: Task, workdir: Path) -> str:
    """Make the workdir a repository whose initial commit is the pristine
    starting repository (plus the runner's ignore file), returning that
    commit's id — the fixed point every capture diffs against, whatever the
    agent later does to HEAD."""
    (workdir / _IGNORE_FILE).write_text(_WORKDIR_IGNORE, encoding="utf-8")
    doing = "seeding the workdir"
    _git(task, ["init", "-q", "."], workdir, doing=doing)
    _git(task, ["add", "-A"], workdir, doing=doing)
    _git(
        task,
        ["commit", "-qm", "pristine", "--no-gpg-sign", "--no-verify"],
        workdir,
        extra_env=_COMMIT_IDENTITY,
        doing=doing,
    )
    return _git(task, ["rev-parse", "HEAD"], workdir, doing=doing).strip()


def _capture_workdir_diff(task: Task, workdir: Path, initial: str) -> str:
    """The workdir's full diff against the initial commit: modified, added and
    deleted files, with --binary so any deliberate binary file round-trips —
    the capture must never write a log row that replay refuses to apply.

    The ignore file is the runner's, not the agent's: it is restored before
    staging, so it can never appear in the diff (it is not in the pristine
    repository grading applies the diff to) and deleting or editing it cannot
    let cache files back in. Top-level only: an agent that plants a nested
    .gitignore or edits .git/info/exclude is hiding its own work from its own
    run — self-harm, not a capture defence's problem.
    """
    (workdir / _IGNORE_FILE).write_text(_WORKDIR_IGNORE, encoding="utf-8")
    doing = "capturing the workdir diff"
    _git(task, ["add", "-A"], workdir, doing=doing)
    return _git(task, ["diff", "--cached", "--binary", initial], workdir, doing=doing)
