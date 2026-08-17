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
frozen baseline declares either a construction or itself a control, that no
baseline control quietly acquires a construction, and that each family is one
underlying change with one knob moving across it. What no task may do is
declare nothing: a control is declared and never inferred from an absence,
which is what the frozen set was frozen to protect.

A task whose deliverable is prose rather than a code change is graded through
that same pipeline and adds no seam to it. A fault-location task asks the agent
to write a structured answer file into the workdir; it lands in the workdir
diff like anything else the agent wrote, and a held-out grading test reads it
back and compares it against the accepted-answer key shipped beside that test
in `grading/`. So the verdict stays execution-verified rather than
pattern-verified — the run log still stores the agent's final message and the
verdict still never reads it — and the ground truth is a set of accepted (file,
symbol) pairs, never a line number, because lines shift under any edit and two
equally correct answers land on different ones.

What that action does *not* inherit is the gate that protects a code task. A
pristine repository carries no answer file, so the must-fail-on-pristine
invariant is unconditionally satisfied here and proves nothing: a grading test
that reads no key at all passes it, and so does a task with no defect in it.
Both holes close, by different means, because they are different holes.
Whether the grading test discriminates is answered by negatives the lint runs
through the real pipeline — four it constructs itself, plus the plausible
wrong file the author writes into the key's rejected set — and the comparison
those negatives are run against is one owned module, `grading/_answer.py`,
copied identically into every such task and read back byte for byte. Whether
there is a defect to find at all is answered by the paired `bug-fix` member,
whose held-out tests must fail on the same pristine repository; that pairing
is a convention rather than a checked relation, so a fault-location task
authored alone has no proof there is anything in it to find.

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

import ast
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self, get_args
from urllib.parse import urlparse
from xml.etree import ElementTree

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    model_validator,
)

from ai_benchmark import _answer
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
    Surface,
    TaskCategory,
    TaskCategoryField,
    validate_record,
)

BENCHMARK = "first-party-v1"

TASK_SPEC = "task.yaml"
REPO_DIR = "repo"
GRADING_DIR = "grading"

# The accepted-answer key of a fault-location task, inside GRADING_DIR: held
# out with the grading tests, reaching the workdir by the overlay that copies
# that directory wholesale, and never collected, because collection globs test
# files only.
ANSWER_KEY_FILE = "accepted-answer.json"

# The answer comparison, inside GRADING_DIR beside the key and reaching the
# workdir the same way: `ai_benchmark._answer`, shipped byte for byte into
# every fault-location task. Owned rather than hand-written per task because
# the half of the verdict that discriminates is the half worth not miscopying.
ANSWER_MODULE = "_answer.py"

# The held-out grading test that reads the answer comparison, shipped the same
# way and for the same reason: byte for byte into every fault-location task,
# so that nothing binds a task's *grading test* to `_answer.py` except that it
# is the very test this project owns, rather than a hand-written assertion
# that quietly stops calling `answer_problem()` while still shipping an
# unedited copy of the module beside it. A task may ship *additional* grading
# tests alongside this one — resolution requires every grading test to pass,
# so an extra test can only make a task harder to resolve, never let a wrong
# answer through, and nothing here should be tightened into a ban on that.
ANSWER_TEST_FILE = "test_answer.py"

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
    # Decision conveyance, and the one ladder whose *order* is the claim
    # rather than a vocabulary: how the single withheld decision reaches the
    # solver, easiest first, prose last because prose displaces the module as
    # the source of truth and steers the implementation shape. Mirrored
    # verbatim from the design note, which registered it before this line
    # existed — reordering these four here would silently rewrite a
    # pre-registered claim into whatever the next sweep happened to show.
    "K12": ("criterion", "repo-primitive", "unmentioned", "prose"),
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


# What a run log measures per row, and therefore what an effort claim can be
# registered against: the two axes round 1 recovered its real result on.
EffortMetric = Literal["turns", "cost"]

# What a task's effort is read against. Both are things the task set itself
# holds, so a claim is settleable from checked-in artifacts by the same one
# command everything else here is: the task's pair partner — the control built
# beside it — or the zero-knob baseline tasks of the task's own category.
EffortComparator = Literal["pair", "baseline"]


class EffortClaim(BaseModel):
    """The author's pre-registered claim that this task costs effort.

    Twice now effort has separated where `resolved` could not: the first
    sweep's refactor lesson and round 1's K7/K9 contrasts, both recovered from
    the run logs after the fact (docs/design/task-difficulty-and-ex-ante-
    profiles.md sections 12 and 16). Recovered after the fact that is mining.
    Registered here it is a bet reconciliation settles per model, on the same
    terms the rung prediction is settled on — and one the sweep can lose.

    Deliberately not carried: a rationale of its own. The prediction it hangs
    on already has one, and the claim itself is three numbers a report can
    echo verbatim, so a second free-text field would be a second place for the
    same reasoning to be written and drift from.

    `cost` is the metric to register unless there is a reason not to, and the
    reason is quantization (design note section 20, and section 9 as amended
    in round 3): turn counts here are small integers, so from a 4-turn
    comparator the smallest possible step is exactly 1.25x — a 1.25x turns
    claim is met by one extra turn there and needs two against an 8-turn
    comparator, a stringency nobody registered. `turns` stays available and
    the field stays required rather than defaulted, because a metric that
    filled itself in would make an old claim read as a bet its author never
    placed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    comparator: EffortComparator
    metric: EffortMetric
    at_least_factor: float

    @model_validator(mode="after")
    def the_factor_claims_something(self) -> Self:
        if not math.isfinite(self.at_least_factor):
            # YAML spells these `.nan` and `.inf`, and both survive parsing as
            # floats. A nan compares false against every bound, so it slips
            # past the test below; an inf passes it and then claims a multiple
            # no measurement can reach. Neither is a bet a sweep could lose.
            raise ValueError(
                f"at_least_factor {self.at_least_factor} is not a finite "
                "number — a claim is settled by comparing a measurement "
                "against this multiple, and neither a nan nor an infinity is "
                "a multiple any run could be read against. Register a finite "
                "factor above 1.0"
            )
        if self.at_least_factor <= 1.0:
            raise ValueError(
                f"at_least_factor {self.at_least_factor} claims nothing — the "
                "claim is that this task costs at least that multiple of its "
                "comparator, so 1.0 is satisfied by a task costing exactly what "
                "its comparator costs, and anything below it by a task costing "
                "less. Register a factor above 1.0 or register no effort claim"
            )
        return self


class Prediction(BaseModel):
    """The author's pre-registered difficulty prediction for this task.

    Registered before the task's first paid run, which is what makes the knob
    theory falsifiable rather than fitted to the sweep afterwards; the run
    log's append-only timeline is the audit trail that it came first.

    The rung is mandatory and the effort claim optional, which is the order
    the two were learnt in: every task lands on a rung, and only some tasks
    are built to cost something. A task registering no effort claim is not
    claiming its knob is free — it is claiming nothing, and reconciliation
    scores it nowhere.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rung: Rung
    rationale: NonEmptyStr
    effort: EffortClaim | None = None


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

    A task with no construction block at all is a control: one of the frozen
    22, or a task declaring itself one.
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
                "a construction block sets at least one knob — a task that "
                "sets none claims nothing about difficulty, which is what a "
                "control is, and a control is declared by `control: true` and "
                "no construction block rather than by an empty one"
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
    def an_effort_claim_has_a_comparator_to_read_it_against(self) -> Self:
        """A claim read against a pair partner needs a pair to have one in.

        Caught here rather than in the set-wide lint because the block already
        contradicts itself: no other task, and no sweep, could make it
        settleable. The set-wide half of the rule — that the *baseline*
        comparator a claim names is actually in the task set — is the lint's,
        because only the set can show it.
        """
        claim = self.prediction.effort
        if claim is not None and claim.comparator == "pair" and self.pair is None:
            raise ValueError(
                "the effort claim is read against this task's pair partner, and "
                "the block declares no pair — there is no partner to read it "
                "against, so no sweep could ever settle the claim. Declare the "
                "pair, or claim against the zero-knob baseline instead"
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
    category: TaskCategoryField
    scale: Scale
    # Required here, with no default, though a *record*'s surface still
    # defaults to `unknown` (`ai_benchmark.schema.Record`): an ingested
    # second-hand row is annotated with whatever its source disclosed, but a
    # task we author ourselves knows where its work happens, and the coverage
    # table counts `category × surface × language` cells. An undeclared
    # surface would land every new task in the `unknown` column and make that
    # table report the author's silence as a gap in the corpus.
    surface: Surface
    language: LanguageStr | None = None
    prompt: NonEmptyStr
    grading: Grading = Grading()
    construction: Construction | None = None
    # Whether this task declares itself a control: authored to fill a
    # category, claiming nothing about difficulty, so it sets no knob and
    # registers no prediction. Said outright rather than by leaving the
    # construction block out, because an absent block is what makes the frozen
    # 22 controls and that meaning is not available to a task outside the set:
    # a control created by omission is indistinguishable from an author who
    # forgot to declare one, and the sweep would price both as controls.
    # Strict: this flag is load-bearing enough that a lax `control: "yes"`
    # coercing quietly to True would be the wrong kind of surprise.
    control: StrictBool = False
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

    @model_validator(mode="after")
    def a_control_is_the_absence_of_a_difficulty_claim(self) -> Self:
        """A task declares exactly one of the two, and this is the half one
        task.yaml can show on its own: a control that also sets knobs.

        The two declarations are opposites. Knob activations and the
        prediction they hang on are a claim that this task's difficulty comes
        from named causes; a control claims nothing at all. A task making both
        is read as a control by the denominator and as a knob-experiment task
        by everything that groups by level, so it would be counted on both
        sides of its own comparison.
        """
        if self.control and self.construction is not None:
            raise ValueError(
                "declares itself a control and sets knob(s) "
                f"{sorted(self.construction.levels)} — a control claims nothing "
                "about difficulty and knob activations are exactly that claim, "
                "so a task declares one or the other. Drop the construction "
                "block, or drop the control declaration"
            )
        return self


def is_control(task: Task) -> bool:
    """Whether this task makes no claim about difficulty and is read as a
    control: one of the frozen 22, or a task that declares itself one.

    The two say it differently and mean the same thing, and the difference is
    which of them the corpus can still add to. The frozen set says it by
    carrying no construction block, which is why it has to be frozen — that
    meaning is one an unfinished task.yaml would acquire by accident. Every
    task outside it says it outright.

    One implementation for the whole project, because a control is what every
    denominator is drawn from: the calibration view's per-category cost
    baseline and reconciliation's baseline effort comparator both read this,
    and two copies of it could disagree about which tasks are controls while
    each stayed consistent with itself.
    """
    return task.control or task.id in BASELINE_TASK_IDS


# --- fault-location: the answer file and the accepted-answer key ---------------

# The fields an author reaches for when writing down a line number instead of
# a symbol. Named so the refusal can say why rather than leaving pydantic to
# report an unexpected field. Matched case-insensitively against whatever the
# key actually names — "Line" is as much a line number as "line" is — which
# is also why "at_line" and "line_at" are spelled out rather than assuming an
# author always puts the noun first.
_LINE_FIELDS = (
    "line",
    "lineno",
    "line_number",
    "lines",
    "line_numbers",
    "at_line",
    "line_at",
)


class Answer(BaseModel):
    """One location a key names: a file, and a symbol that file defines.

    The shape of both halves of a key — the accepted answers and the rejected
    near-misses — because they are the same claim read in two directions, and
    the lint runs a rejected one through the very comparison an accepted one
    has to survive.

    A pair and never a line number. Lines shift under any edit — including the
    agent's own reading notes — and the several description levels that are
    legitimately correct start on different ones anyway, so a key written in
    line numbers grades a correct answer wrong and does it silently.

    And never a file alone. An author may legitimately write down the
    enclosing class as well as the defective function, but on repositories as
    small as these a bare filename is barely a location: it would resolve for
    an agent that located nothing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: NonEmptyStr
    symbol: NonEmptyStr

    @model_validator(mode="before")
    @classmethod
    def a_location_is_a_symbol_and_never_a_line(cls, data: Any) -> Any:
        if isinstance(data, dict):
            named = sorted(
                field
                for field in data
                if isinstance(field, str) and field.lower() in _LINE_FIELDS
            )
            if named:
                raise ValueError(
                    f"answer {dict(data)} names a line number "
                    f"({named}) — an answer is a (file, symbol) pair, "
                    "because lines shift under any edit and two equally correct "
                    "answers land on different ones, so a key keyed on one would "
                    "grade a correct location wrong"
                )
        return data

    @model_validator(mode="before")
    @classmethod
    def a_location_names_a_symbol_and_never_a_file_alone(cls, data: Any) -> Any:
        if isinstance(data, dict) and "symbol" not in data:
            raise ValueError(
                f"answer {dict(data)} names a file with no symbol — on a "
                "repository this small a bare filename is barely a location, "
                "and a key accepting one would resolve for an agent that "
                "located nothing"
            )
        return data


class AnswerKey(BaseModel):
    """A fault-location task's ground truth: where the agent writes its answer,
    every location that answer may name, and the near-misses it may not.

    The accepted set is the mitigation for this grading's one expensive
    assumption — that an agent which correctly locates a fault describes it at
    a level of the tree the author anticipated. The author writes down every
    level that is legitimately correct (typically the defective function and
    the class enclosing it) and the grading test accepts any member. That is
    the author's judgement rather than a mechanism, and it is stated here so it
    can fail visibly.

    The rejected set is the negative half, and what makes the verdict mean
    something: must-fail-on-pristine cannot, because a pristine repository
    carries no answer file, so that invariant is satisfied by a grading test
    which reads no key at all. The lint constructs four negatives itself and
    requires each to grade unresolved; what it cannot invent is the plausible
    wrong *file* — the caller of the defective function, the module that looks
    responsible — and that is what the author writes here.

    Either set may be empty as far as this model is concerned: the lint is
    where an empty one is refused, because a task that cannot load cannot be
    linted, and these are exactly the defects the lint exists to name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer_path: NonEmptyStr
    accepted: tuple[Answer, ...] = ()
    rejected: tuple[Answer, ...] = ()

    @model_validator(mode="after")
    def each_half_is_a_set_and_names_no_pair_twice(self) -> Self:
        for half, answers in (("accepted", self.accepted), ("rejected", self.rejected)):
            repeated = sorted(
                pair
                for pair, count in Counter(
                    (answer.file, answer.symbol) for answer in answers
                ).items()
                if count > 1
            )
            if repeated:
                raise ValueError(
                    f"{half} names the same (file, symbol) pair more than once: "
                    f"{repeated} — {half} is a set of locations, and a pair "
                    "repeated in it claims nothing an unrepeated one would not"
                )
        return self


def answer_key(task: Task) -> AnswerKey:
    """The accepted-answer key shipped inside this task's grading directory.

    One file read two ways, which is the point: the lint reads it from the task
    directory, and the grading test reads the very same bytes out of the
    workdir the overlay copied them into. The declared answer path lives here
    rather than in the grading test, so nothing can hardcode a path the prompt
    does not name.
    """
    path = task.grading_dir / ANSWER_KEY_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{ANSWER_KEY_FILE} is missing or unreadable "
            f"({error}) — a {task.category} task is graded by comparing the answer "
            "file the agent writes against the accepted-answer key, which ships "
            "with the held-out grading tests"
        ) from error
    except json.JSONDecodeError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{ANSWER_KEY_FILE} is not JSON ({error}) — "
            "the grading test reads it with the standard library alone"
        ) from error
    try:
        return AnswerKey.model_validate(raw)
    except ValidationError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{ANSWER_KEY_FILE}: {error}"
        ) from error


def answer_module_source() -> bytes:
    """The answer comparison, as every fault-location task's
    `grading/_answer.py` has to be byte for byte.

    The project's own module read off disk rather than a string constant, so
    that the shipped copies are compared against code mypy type-checks and the
    tests exercise, and an author has one file to copy.
    """
    return Path(__file__).with_name(ANSWER_MODULE).read_bytes()


# The held-out grading test itself, canonical: a one-line assertion over
# `answer_problem()`, shipped byte for byte as `answer_test_source()` below
# ships `answer_module_source()`. A plain string constant rather than a
# second file on disk — unlike the comparison, there is no logic here worth
# having mypy check or a test exercise directly, only the one assertion the
# held-out test is required to make.
_ANSWER_TEST_SOURCE = '''\
"""Held out: whether the agent's answer file names an accepted location.

Canonical — this project's own file, shipped byte for byte into every
fault-location task's grading directory and read back that way by the
task-set lint (`_answer_test_problems` in firstparty_v1.py), so that nothing
in a task's grading directory can stop consulting `_answer.py` while still
shipping an unedited copy of it. A task may ship additional grading tests
beside this one: resolution requires every grading test to pass, so an extra
test can only make the task harder to resolve, never let a wrong answer
through.
"""

from _answer import answer_problem


def test_the_answer_names_an_accepted_location():
    assert (problem := answer_problem()) is None, problem
'''


def answer_test_source() -> bytes:
    """The held-out grading test, as every fault-location task's
    `grading/test_answer.py` has to be byte for byte — see `ANSWER_TEST_FILE`
    and `_ANSWER_TEST_SOURCE`."""
    return _ANSWER_TEST_SOURCE.encode("utf-8")


def _defined_symbols(source: str) -> set[str]:
    """Every symbol a module defines: its functions and classes, both
    qualified by nesting and bare, and its module-level assignment targets.

    A method is accepted either way: `Class.method`, which is how an author
    writes down the two levels a defect in one is legitimately described at —
    the method, and the class enclosing it — and the bare `method`, which is
    how a locating agent actually phrases an answer about something nested.
    Only nested definitions get the bare form; a module-level definition has
    no qualified form to be an alternative to.

    An assignment counts only at module level, and that is the ruling's own
    boundary: a fault can live in a constant, a dispatch table or a compiled
    pattern, and a key that saw only `def` and `class` could not name one. An
    assignment inside a class body or a function is not keyable, because it is
    a state change inside something already keyable, and accepting it would
    key a location at a level no author wrote down.
    """
    symbols: set[str] = set()
    definitions = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

    def bind(target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            symbols.add(target.id)
        elif isinstance(target, ast.Starred):
            bind(target.value)
        elif isinstance(target, ast.Tuple | ast.List):
            for element in target.elts:
                bind(element)

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, definitions):
                symbols.add(prefix + child.name)
                if prefix:
                    symbols.add(child.name)
                walk(child, f"{prefix}{child.name}.")
            else:
                if not prefix:
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            bind(target)
                    elif isinstance(child, ast.AnnAssign):
                        bind(child.target)
                # Anything else keeps the prefix: a definition guarded by an
                # `if` or a `try` at module level is still defined there, and
                # so is an assignment.
                walk(child, prefix)

    walk(ast.parse(source), "")
    return symbols


# What a sweep id has to be to work as a round key, said once for the two
# places that enforce it: the run model, which sees ids read back out of a
# log, and the live runner, which sees the one its caller passed in.
_SWEEP_ID_RULE = (
    "a sweep id is the key reconciliation groups its rounds by, and the id it "
    "prints in a comma-joined list of them, so it has to be one exact "
    "non-empty string repeated across every invocation of one sweep, carrying "
    "no comma and no control character — an empty id keys a round on nothing, "
    "' r2' beside 'r2' splits one sweep into two rounds without anything "
    "failing, and 'r2,x' reads back off the report as the two rounds r2 and x. "
    "Inner single spaces are fine: 'round 2' names one round"
)


def _sweep_id_problem(sweep: str) -> str | None:
    """What is wrong with this sweep id, if anything."""
    if not sweep.strip():
        return f"sweep id {sweep!r} is empty or blank"
    if sweep != sweep.strip():
        return f"sweep id {sweep!r} is padded with whitespace"
    if "," in sweep:
        return f"sweep id {sweep!r} contains a comma"
    # isprintable() is False for exactly what wrecks a one-line report cell:
    # newlines, tabs, other control characters, and the non-space separators
    # that look like a space without being one. A plain inner space passes.
    if unprintable := [char for char in sweep if not char.isprintable()]:
        return (
            f"sweep id {sweep!r} contains the control character "
            f"{unprintable[0]!r}"
        )
    return None


class Run(BaseModel):
    """One raw run-log row: the v0 fields plus the workdir diff and the sweep id.

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
    # Which sweep wrote this row: the id the live runner stamps on every row
    # of one invocation batch, so that reconciliation counts rounds by sweep
    # rather than by calendar date — two sweeps run on one day are two rounds,
    # and one sweep split across several invocations (models run apart, a
    # resume after a crash) is one. Optional because every row written before
    # the field existed has none, and those stay valid and replay unchanged:
    # reconciliation falls back to their as-of date, which is all they say.
    sweep: NonEmptyStr | None = None

    @model_validator(mode="after")
    def sweep_id_is_a_usable_round_key(self) -> Self:
        if self.sweep is not None and (problem := _sweep_id_problem(self.sweep)):
            raise ValueError(f"{problem} — {_SWEEP_ID_RULE}")
        return self


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
    if task.category == "fault-location":
        # The ground truth of a task whose deliverable is prose. Read here so
        # that a key which is missing, unparseable, or written in line numbers
        # fails at load rather than at the first paid run. The empty-accepted-
        # set check is read here too, and not left to the lint alone: `ai-bench
        # run-live` loads a task set but never lints it, so an unsolvable key
        # would otherwise reach a paid run.
        key = answer_key(task)
        if not key.accepted:
            raise IngestError(_empty_accepted_set_message(task))


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
    """Every row of a raw v1 run log, in the order it was appended.

    A bad row names its own line. The log is appended to run by run over a
    sweep that was paid for, so it is normal for one row out of a hundred to
    be the problem, and "somewhere in this file" does not find it.
    """
    runs = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            runs.append(Run.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as error:
            raise IngestError(f"{path} line {number}: {error}") from error
    return runs


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

    A fault-location task is run against more than the pristine repository,
    because for that action the pristine run proves nothing — see
    `_discrimination_problems`.

    The construction invariants are read rather than run, but belong here for
    the same reason: an undeclared knob, an unregistered prediction, a family
    whose variants differ in more than the knob they vary, or an effort claim
    naming a comparator the task set does not hold costs nothing to catch now
    and cannot be repaired afterwards — a prediction registered once the
    outcome is known is not a prediction, and a sweep is only paid for once.
    """
    problems = (
        _family_problems(tasks) + _effort_claim_problems(tasks) + _pair_problems(tasks)
    )
    for task in tasks:
        problems.extend(construction_problems(task))
        key_problems = _answer_key_problems(task)
        problems.extend(key_problems)
        # Independent of key_problems and never used to gate
        # _discrimination_problems: an edited or missing held-out test is
        # caught here by its bytes, cheaply, but a task may legitimately ship
        # additional grading tests beside the canonical one, and a task whose
        # canonical test is untouched can still carry a key that does not
        # discriminate — which only running the real pipeline below can show.
        problems.extend(_answer_test_problems(task))
        if task.category == "fault-location" and not key_problems:
            # Only once the key reads clean: the negatives are graded through
            # the real pipeline, which is the expensive half of this lint, and
            # a key that names a file the repository does not hold has nothing
            # to say about whether the grading test discriminates.
            problems.extend(_discrimination_problems(task, timeout_s=timeout_s))
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


# What a task with no declared `language` counts under in the coverage
# table, rather than being dropped from it: `language` is only absent when
# it is not meaningful, and that is itself a fact worth disclosing.
NO_LANGUAGE = "(none)"


def coverage_table(tasks: list[Task]) -> list[tuple[str, str, str, int]]:
    """Task counts over `category x surface x language`, for `ai-bench
    lint-v1` to print. Reports only — nothing here gates the lint.

    Every `TaskCategory` appears at least once, `test-authoring`'s
    registered-empty cell (design note 45.12) included, so a category with
    no tasks reads as `0` rather than as an omission. `scale` and substrate
    are disclosed on a task but not gridded here (design note 45.10).
    """
    counts: Counter[tuple[str, str, str]] = Counter(
        (task.category, task.surface, task.language or NO_LANGUAGE) for task in tasks
    )
    order = {category: index for index, category in enumerate(get_args(TaskCategory))}
    rows = [
        (category, surface, language, count)
        for (category, surface, language), count in counts.items()
    ]
    covered = {row[0] for row in rows}
    rows += [
        (category, "-", "-", 0)
        for category in get_args(TaskCategory)
        if category not in covered
    ]
    rows.sort(key=lambda row: (order[row[0]], row[1], row[2]))
    return rows


def construction_problems(task: Task) -> list[str]:
    """What is wrong with this task's declaration of what it is.

    Every task declares exactly one of three things: how it was built, that it
    is a control, or membership in the frozen baseline — and the last of those
    is itself declared by the *absence* of the first two, so the rule runs
    both ways for it: a task outside the frozen set must declare something,
    and a baseline task must declare nothing, or reconciliation can read it as
    more than one of the three.

    What is deliberately not a fourth state is silence. A task saying nothing
    would be a control by omission, which is the one thing the frozen set was
    frozen to prevent: nothing distinguishes it from a task whose author had
    not finished declaring it, and the sweep prices both as controls.

    Public because reconciliation checks it too, before reading a task set as
    controls and predictions. One invariant, one implementation: two copies of
    this rule could disagree about which tasks are controls — which is also
    why this reads `is_control` rather than re-deriving its negation.
    """
    declared = task.construction is not None
    baseline = task.id in BASELINE_TASK_IDS
    if not is_control(task) and not declared:
        return [(
            f"{task.id}: declares neither a construction block nor itself a "
            "control — a control is declared and never inferred from an "
            "absence, because a task that declares nothing is indistinguishable "
            "from one whose author has not said yet what it sets, and a sweep "
            "would read both as controls. Declare the difficulty knob(s) it "
            "sets and its pre-registered prediction, or declare it a control"
        )]
    if declared and baseline:
        return [(
            f"{task.id}: a zero-knob baseline control carries a construction "
            "block — the absence of the block is the whole of what makes these "
            "22 tasks controls, so one that declares knobs is a control "
            "reconciliation would read against itself"
        )]
    if task.control and baseline:
        return [(
            f"{task.id}: a zero-knob baseline control also declares itself a "
            "control — the absence of a construction block already makes "
            "these 22 tasks controls, so the declaration says the same thing "
            "twice and makes it ambiguous which of the two ways of being a "
            "control this task means"
        )]
    return []


def _answer_key_problems(task: Task) -> list[str]:
    """What is wrong with a fault-location task's accepted-answer key.

    Read rather than run, and for the reason every other read invariant is
    here: none of it is repairable once the sweep is paid for, and each defect
    makes a task that grades every agent unresolved while looking exactly like
    a hard one.

    What the set can be checked against is the starting repository the agent is
    given: the accepted set says something at all, and so does the rejected
    one — and the rejected one says the one thing only the author can supply,
    a file the accepted set does not already name, rather than merely being
    non-empty; every file either names is in that repository, matched exactly
    rather than case-insensitively; every symbol either names is defined in
    the file it names, so a rename or a typo cannot leave a key no correct
    answer matches — nor a near-miss that grades unresolved for a reason that
    says nothing about the grading test; a bare symbol in either half is
    refused wherever a qualified spelling of it exists, because `matches()` is
    one-directional and a key spelled bare would refuse the qualified spelling
    an agent would most naturally give; the answer comparison shipped in
    `grading/` is this project's own, byte for byte; the declared answer path
    lands inside the workdir a run is graded from and does not collide with a
    file grading overlays over it; and the prompt names that path as a whole
    token, so a task cannot be unsolvable because the agent was never told
    where to write. What no check can reach is whether the author wrote down
    every description level a correct answer might use — that is the
    judgement this grading rests on.

    What is *not* here is the half that has to be run rather than read: see
    `_discrimination_problems`, which the lint runs once this returns nothing.
    """
    if task.category != "fault-location":
        return []
    key = answer_key(task)
    problems = []
    if not key.accepted:
        problems.append(_empty_accepted_set_message(task))
    if not key.rejected:
        problems.append(
            f"{task.id}: the accepted-answer key declares no rejected answers — "
            "must-fail-on-pristine proves nothing about a fault-location task, "
            "because a pristine repository carries no answer file at all, so "
            "the near-miss the lint cannot invent is what stands between this "
            "task and a grading test that would resolve anything: name the "
            "plausible wrong file, the caller of the defective function or the "
            "module that looks responsible"
        )
    else:
        # `rejected` being non-empty is not the same as it saying anything:
        # §36.3 names the one negative the lint cannot invent as the
        # plausible wrong *file*, so a rejected set confined to files the
        # accepted set already names never supplies it, however many entries
        # it carries. And a rejected answer that happens to equal the
        # near-miss the lint synthesises for itself spends the author's
        # judgement on a symbol the lint already checks for nothing, rather
        # than on the one thing only the author can supply.
        accepted_files = {answer.file for answer in key.accepted}
        if all(answer.file in accepted_files for answer in key.rejected):
            rejected_files = sorted({answer.file for answer in key.rejected})
            problems.append(
                f"{task.id}: every rejected answer names a file already in "
                f"the accepted set ({rejected_files}) — the rejected set "
                "exists for the near-miss the lint cannot invent, the "
                "plausible wrong *file* (the caller of the defective "
                "function, the module that looks responsible), and a "
                "rejected answer confined to a file the accepted set "
                "already names never supplies it"
            )
        near_miss = _near_miss(task, key)
        if near_miss is not None and near_miss in {
            (answer.file, answer.symbol) for answer in key.rejected
        }:
            problems.append(
                f"{task.id}: the rejected answer {near_miss!r} is exactly the "
                "near-miss the lint already synthesises from the accepted set "
                "— the author's judgement belongs on the one negative the "
                "lint cannot invent, the plausible wrong file, not on a wrong "
                "symbol the lint already checks for nothing"
            )
    problems.extend(_answer_module_problems(task))
    if _escapes_workdir(key.answer_path):
        problems.append(
            f"{task.id}: the accepted-answer key's answer_path "
            f"{key.answer_path!r} is absolute or climbs out of the workdir with "
            "'..' — the workdir diff a run is graded from can only ever hold "
            "paths inside the workdir, so the agent's answer would never reach "
            "the diff however correctly it located the fault"
        )
    elif key.answer_path in _tree_bytes(task.grading_dir):
        problems.append(
            f"{task.id}: the accepted-answer key's answer_path "
            f"{key.answer_path!r} collides with a file grading overlays over "
            "the workdir — the agent's answer file would be silently "
            "overwritten by the held-out grading files before the verdict ever "
            "reads it"
        )
    if not _prompt_names_path(task.prompt, key.answer_path):
        problems.append(
            f"{task.id}: the prompt never names the answer file "
            f"{key.answer_path!r} — the answer file is the whole deliverable, so "
            "an agent that is not told where to write it cannot solve the task "
            "however well it locates the fault"
        )
    for half, answers in (("accepted", key.accepted), ("rejected", key.rejected)):
        for answer in answers:
            source = _repo_file(task, answer.file)
            if source is None:
                problems.append(
                    f"{task.id}: the accepted-answer key's {half} answers name "
                    f"{answer.file!r}, which is not in the starting repository — "
                    "no agent can answer with a file it was never given"
                )
                continue
            try:
                defined = _defined_symbols(source.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError) as error:
                problems.append(
                    f"{task.id}: the accepted-answer key's {half} answers name "
                    f"{answer.file!r}, whose definitions cannot be read "
                    f"({error}) — the key is checked against what the file "
                    "actually defines"
                )
                continue
            if answer.symbol not in defined:
                problems.append(
                    f"{task.id}: the accepted-answer key's {half} answers name "
                    f"symbol {answer.symbol!r}, which {answer.file} does not "
                    f"define — it defines {sorted(defined)}, and a method is "
                    "written 'Class.method'"
                )
            elif "." not in answer.symbol:
                # matches() is deliberately one-directional: an *answer*
                # spelled bare matches a key spelled qualified, never the
                # reverse — a key spelled bare would let `Other.method`
                # answer it too, which is a false positive rather than a
                # forgiven spelling. So where a qualified spelling of this
                # symbol exists, the key has to use it.
                qualified = sorted(
                    candidate
                    for candidate in defined
                    if candidate != answer.symbol
                    and candidate.endswith(f".{answer.symbol}")
                )
                if qualified:
                    problems.append(
                        f"{task.id}: the accepted-answer key's {half} answers "
                        f"name bare symbol {answer.symbol!r} in {answer.file!r}, "
                        f"which is also defined as {qualified[0]!r} — a bare "
                        "answer matches a qualified key, never the reverse, "
                        "so a key spelled bare refuses the qualified spelling "
                        f"an agent would most naturally give. Write the key as "
                        f"{qualified[0]!r}"
                    )
    return problems


def _answer_module_problems(task: Task) -> list[str]:
    """Whether this task ships the answer comparison, unedited.

    The comparison is the half of the verdict that discriminates, so it is one
    owned module copied identically into every fault-location task rather than
    six hand-written ones — and the copies are read byte for byte against the
    bytes this package itself owns (`answer_module_source()`). This is a
    *stronger* check than the one the family lint runs on a family's starting
    repositories and grading suites: the family lint compares each member's
    tree against the alphabetically-first member's, peer to peer, because
    that is the only source a family lint has — a lone fault-location task has
    no sibling to compare against. Here there is a privileged source instead,
    the package's own file, so drift is caught even on a task authored alone.
    A copy that forgave case, or stopped reading the symbol, would grade every
    task shipping it differently from every task that did not, with nothing
    else in the corpus objecting. See `_answer_test_problems` for the sibling
    check on the held-out grading test itself, which nothing bound to this
    module before it existed.
    """
    shipped = task.grading_dir / ANSWER_MODULE
    try:
        copy = shipped.read_bytes()
    except OSError as error:
        return [(
            f"{task.id}: {GRADING_DIR}/{ANSWER_MODULE} is missing or unreadable "
            f"({error}) — the answer comparison is what the held-out grading "
            "test asserts over, so without it the task grades every agent "
            "unresolved"
        )]
    if copy != answer_module_source():
        return [(
            f"{task.id}: {GRADING_DIR}/{ANSWER_MODULE} is not the answer "
            "comparison this project ships — it is one owned module copied "
            "identically into every fault-location task, and a copy that has "
            "drifted grades this task by rules no other task is graded by"
        )]
    return []


def _answer_test_problems(task: Task) -> list[str]:
    """Whether this task ships the held-out grading test, unedited.

    Named and treated the way `_answer_module_problems` treats the answer
    comparison, because it closes the same hole from the other side: shipping
    `_answer.py` byte for byte proves nothing about what a task's grading
    test actually *does* with it. A grading test that ships `_answer.py`
    untouched and then does its own case-insensitive match, or checks the
    file and not the symbol, or never imports the module at all, lints clean
    under `_answer_module_problems` alone — three fixtures demonstrated
    exactly that. So the held-out test is itself canonical: one owned file,
    `grading/test_answer.py`, shipped byte for byte and read back that way
    against the bytes this package owns (`answer_test_source()`).

    A task may ship *additional* grading tests beside this one. Resolution
    requires every grading test to pass, so an extra test can only make a
    task harder to resolve, never let a wrong answer through — this is not a
    ban on other grading tests, only a requirement that this one is among
    them, unedited.

    Applies only to fault-location tasks, and is not gated on
    `_answer_key_problems`: unlike a broken key, a drifted copy of this file
    says nothing about whether the *key* is sound, so it does not stop
    `_discrimination_problems` from running (see `lint_task_set`).
    """
    if task.category != "fault-location":
        return []
    shipped = task.grading_dir / ANSWER_TEST_FILE
    try:
        copy = shipped.read_bytes()
    except OSError as error:
        return [(
            f"{task.id}: {GRADING_DIR}/{ANSWER_TEST_FILE} is missing or "
            f"unreadable ({error}) — this is the held-out grading test that "
            "asserts over the answer comparison; without it nothing binds "
            "this task's grading to `_answer.py`, and a hand-written grading "
            "test that never calls answer_problem() would lint clean"
        )]
    if copy != answer_test_source():
        return [(
            f"{task.id}: {GRADING_DIR}/{ANSWER_TEST_FILE} is not the held-out "
            "grading test this project ships — it is one owned file copied "
            "identically into every fault-location task, so that its grading "
            "test is always the one-line assertion over `answer_problem()` "
            "that binds the verdict to `_answer.py`, and never a hand-written "
            "test that quietly stops consulting it. A task may ship "
            "*additional* grading tests beside it — resolution requires "
            "every one of them to pass, so an extra test can only make the "
            "task harder to resolve, never let a wrong answer through"
        )]
    return []


def _escapes_workdir(name: str) -> bool:
    """Whether this path cannot land inside a task's workdir: absolute, or
    carrying a '..' component that climbs out of it. Shared by every check
    that reads a task-authored path against the workdir a run is graded
    from — the starting repository (`_repo_file`) and the accepted-answer
    key's declared answer_path alike — because both are the same question:
    a path outside the workdir is never reachable through the diff a run
    logs, whether it is a file the agent was supposed to find or one it was
    supposed to write."""
    return Path(name).is_absolute() or ".." in Path(name).parts


def _repo_file(task: Task, name: str) -> Path | None:
    """The named file inside the starting repository, or None if it is not
    there — including a name that climbs out of the repository, which is a
    file the agent was not given as surely as one that does not exist, and a
    name matching only by case, which is a file the agent was not given
    either.

    Checked component-by-component against the actual directory listing
    rather than `Path.is_file()`: that call is case-insensitive on macOS —
    the platform the sweeps run on — so a key naming `pricing.PY` would
    otherwise resolve to `pricing.py` and lint clean, while the grading test
    that later checks the agent's answer compares exact strings and never
    matches. Listing the directory rather than lower-casing both sides keeps
    the check case-exact on every platform, including one where the two
    spellings really are different files.
    """
    if _escapes_workdir(name):
        return None
    current = task.repo_dir
    for part in Path(name).parts:
        try:
            entries = {entry.name for entry in current.iterdir()}
        except OSError:
            return None
        if part not in entries:
            return None
        current = current / part
    return current if current.is_file() else None


# Characters that continue a bare word or filename rather than closing it —
# deliberately excluding "." and "/", which are structural (an extension
# separator, a path separator) rather than word-continuing, so a path is
# still recognized when it is followed by ordinary sentence punctuation (a
# trailing ".") or is itself an absolute path or one climbing out of the
# workdir (leading "/" or "..", refused on other grounds but still checked
# here for whether the prompt names it).
_PATH_TOKEN_BOUNDARY = re.compile(r"[A-Za-z0-9_-]")


def _prompt_names_path(prompt: str, path: str) -> bool:
    """Whether prompt names path as a standalone token, not merely as a
    substring buried inside some other word: "ANSWER.json" must not match
    inside "MYANSWER.jsonx", where a plain substring test would.

    Checked against the characters actually adjacent to each occurrence in
    the prompt, not against path's own leading/trailing character — a \\b
    (word-boundary) regex would wrongly refuse a path that starts with "/" or
    ".." even when the prompt names it plainly, because neither side of that
    boundary is a word character to begin with.
    """
    for match in re.finditer(re.escape(path), prompt):
        before = prompt[match.start() - 1] if match.start() > 0 else ""
        after = prompt[match.end()] if match.end() < len(prompt) else ""
        if not _PATH_TOKEN_BOUNDARY.match(before) and not _PATH_TOKEN_BOUNDARY.match(after):
            return True
    return False


def _empty_accepted_set_message(task: Task) -> str:
    """What is wrong with a fault-location task whose accepted-answer key
    accepts nothing, worded once so the loader and the lint say the same
    thing: the loader has to refuse this too, because `ai-bench run-live`
    loads a task set but never lints it, so an unsolvable key would otherwise
    reach a paid run."""
    return (
        f"{task.id}: the accepted-answer key accepts no (file, symbol) pair "
        "— every answer would be graded wrong, and the task would be "
        "indistinguishable from one no agent happens to solve"
    )


# The base name for what a run that located nothing leaves behind, for the
# negative that proves the grading test is not satisfied by any old change to
# the workdir. Distinct from the pristine run, which is a workdir nobody
# touched. `_missing_answer_edit_target` below turns this into a name that is
# also distinct from the task's own declared answer_path — a task that
# happened to declare NOTES.md would otherwise have this negative write to
# its answer file, silently collapsing it into a second copy of the
# "malformed answer file" negative below.
_NOTES_FILE = "NOTES.md"


def _missing_answer_edit_target(key: AnswerKey) -> str:
    """Where the "wrote no answer file at all" negative leaves its note.

    Has to differ from the task's own declared answer_path: writing there
    would turn a run that located nothing into a run that wrote a malformed
    answer, which is a different negative this lint already runs separately,
    and the four negatives would silently collapse into three with nothing
    reporting it.
    """
    candidate = _NOTES_FILE
    while candidate == key.answer_path:
        candidate = f"_{candidate}"
    return candidate


def _discrimination_problems(task: Task, *, timeout_s: int) -> list[str]:
    """Whether this fault-location task's grading test tells a correct answer
    from a wrong one — which is the half of the verdict must-fail-on-pristine
    cannot reach.

    A pristine repository carries no answer file, so the grading test fails
    there whatever it asserts and the invariant is unconditionally satisfied:
    a grading test reading no key at all passes it, and so does a task with no
    defect in it. So this runs answers it expects to *fail* through the real
    grading pipeline — the diff built by the live runner's own capture, graded
    by `grade`, exactly as replay grades a logged run — and requires each to
    come out unresolved.

    Four the lint constructs, needing nothing from the author: a missing
    answer file, an empty one, a malformed one, and an accepted file paired
    with a symbol the key does not accept. The last is the load-bearing one:
    it is what a grading test which never consults the key, or which checks
    the file and not the symbol, cannot survive. It also forces the accepted
    set to be honest — where the synthesised answer is in fact a legitimate
    description of the fault, this fails and the author adds it to `accepted`,
    which is the expensive assumption of this grading paid down by a mechanism
    rather than by hope.

    The rest are the author's `rejected` near-misses, run the same way.

    What none of it proves is that there is a defect in the repository at all.
    That is the paired `bug-fix` member's pristine failure, which is a
    convention rather than a checked relation: the two members share a
    starting repository but are deliberately neither a task family nor a pair,
    so it holds only while both are authored together, and a fault-location
    task authored alone has no proof there is anything in it to find.
    """
    key = answer_key(task)
    problems: list[str] = []
    negatives: list[tuple[str, Callable[[Path], None]]] = [
        (
            "a run that wrote no answer file at all",
            _writing(
                _missing_answer_edit_target(key),
                "read the repository, wrote no answer\n",
            ),
        ),
        ("an empty answer file", _writing(key.answer_path, "")),
        (
            "a malformed answer file",
            _writing(key.answer_path, "the tax rounding, somewhere\n"),
        ),
    ]
    near_miss = _near_miss(task, key)
    if near_miss is None:
        problems.append(
            f"{task.id}: no near-miss can be constructed from the accepted "
            "answers — every symbol defined in every file they name is itself "
            "accepted, so the one negative that kills a grading test which "
            "reads the file and not the symbol cannot be run. Key a repository "
            "with somewhere else the fault could plausibly have been"
        )
    else:
        file, symbol = near_miss
        negatives.append((
            f"the accepted file {file!r} paired with {symbol!r}, a symbol it "
            "defines and the key does not accept",
            _writing(key.answer_path, _answer_payload(file, symbol)),
        ))
    negatives.extend(
        (
            f"the rejected answer {answer.file!r}, {answer.symbol!r}",
            _writing(key.answer_path, _answer_payload(answer.file, answer.symbol)),
        )
        for answer in key.rejected
    )
    for description, edit in negatives:
        if grade(task, _negative_diff(task, edit), timeout_s=timeout_s):
            problems.append(
                f"{task.id}: {description} grades resolved — the grading test "
                "does not tell a located fault from an answer that located "
                "nothing, so a verdict on this task would measure whether the "
                "agent wrote a file rather than where it said the defect was"
            )
    return problems


def _writing(at: str, payload: str) -> Callable[[Path], None]:
    """The edit a run that wrote this file would have made."""

    def write(workdir: Path) -> None:
        target = workdir / at
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")

    return write


def _answer_payload(file: str, symbol: str) -> str:
    """One answer file's contents, shaped the way a task's prompt asks for."""
    return json.dumps({"file": file, "symbol": symbol}, indent=2) + "\n"


def _negative_diff(task: Task, edit: Callable[[Path], None]) -> str:
    """The workdir diff a run that made this edit would log.

    Built through the live runner's own capture rather than by writing into a
    grading workdir directly, so that a negative the lint requires unresolved
    travels to the verdict along the whole path an agent's answer travels: the
    same initial commit, the same ignore file, the same `git add -A` and the
    same `git apply` at the far end.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-negative-") as name:
        workdir = Path(name) / "workdir"
        shutil.copytree(task.repo_dir, workdir)
        initial = _commit_pristine(task, workdir)
        edit(workdir)
        return _capture_workdir_diff(task, workdir, initial)


def _near_miss(task: Task, key: AnswerKey) -> tuple[str, str] | None:
    """An accepted file paired with a symbol it defines and the key does not
    accept — the negative no author has to write down.

    Not accepted is read through the very comparison the grading test uses,
    not through set membership: with the bare spelling of an accepted method
    accepted too, a candidate picked by string difference alone could be a
    correct answer the lint then demanded be graded wrong.
    """
    for file in dict.fromkeys(answer.file for answer in key.accepted):
        source = _repo_file(task, file)
        if source is None:
            continue
        try:
            defined = _defined_symbols(source.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        candidates = sorted(
            symbol
            for symbol in defined
            if not any(
                _answer.matches((file, symbol), (accepted.file, accepted.symbol))
                for accepted in key.accepted
            )
        )
        if candidates:
            return file, candidates[0]
    return None


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


def _effort_claim_problems(tasks: list[Task]) -> list[str]:
    """Effort claims whose comparator this task set does not hold.

    The shape of a claim is the task model's business, and so is the half of
    this rule a single block can show — a pair comparator on a task declaring
    no pair never loads at all. What only the set can show is the other
    comparator: a claim read against the zero-knob baseline of the task's own
    category needs the set to hold such a control, and where it does not,
    reconciliation reports the claim not assessable in every round there will
    ever be. That is a registered claim no sweep can settle, which is the one
    thing pre-registration is supposed to rule out, and it costs nothing to
    catch before the sweep is paid for.
    """
    stocked = {task.category for task in tasks if is_control(task)}
    problems = []
    for task in tasks:
        if task.construction is None:
            continue
        claim = task.construction.prediction.effort
        if claim is None or claim.comparator != "baseline":
            continue
        if task.category not in stocked:
            problems.append(
                f"{task.id}: its effort claim is read against the zero-knob "
                "baseline of its own category, and the task set holds no "
                f"{task.category} baseline control — no sweep could settle the "
                "claim, so it would be reported not assessable in every round"
            )
    return problems


def _pair_problems(tasks: list[Task]) -> list[str]:
    """What is wrong with each declared pair, if anything.

    A pair id records that two tasks are meant to be read against each other —
    a planted crux and the control built beside it. Exactly two, because "the
    pair" names nothing once a third task joins it; starting from the same
    repository, because a control pitched on different terrain controls for
    the terrain as well as for the knob; classified the same way, because
    records inherit the task's annotations, so a pair that disagrees about
    them is read across capability-matrix cells that are never compared; and
    setting the same knobs with exactly one of them varied, because the rung
    delta the report prints for a pair is attributed to that one knob by
    construction.

    That last rule is the family rule over again, and for the same reason — a
    pair varying two knobs attributes its delta to neither — with one case a
    family cannot have: two members declaring *different* knobs. Reconciliation
    reads the varied knob off the members' own activations, so a member that
    never declares it renders as a level of `-`, and the pair is printed as a
    crux/control contrast on a knob only one side was built for. The levels
    themselves stay the knob's business, not the grouping's.
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
            continue
        knobs = _varied_knob_problem(pair, one, other)
        if knobs is not None:
            problems.append(knobs)
    return problems


def _varied_knob_problem(pair: str, one: Task, other: Task) -> str | None:
    """Why this pair's rung delta would be unattributable, if it would be.

    Exactly one knob moves between a crux and its control. Two moving knobs
    leave the delta belonging to neither; none at all makes two controls;
    and knob sets that differ at all — disjoint, or one nested in the other —
    leave some knob declared on a single side, which the report can only
    render as a level of `-` opposite it.
    """
    assert one.construction is not None and other.construction is not None
    held, variant = one.construction.levels, other.construction.levels
    if set(held) != set(variant):
        return (
            f"pair {pair!r} members do not set the same knob(s): {one.id} sets "
            f"{sorted(held)} and {other.id} sets {sorted(variant)} — a knob only "
            "one of them declares leaves the other side with no level to print, "
            "which reconciliation renders as a crux/control contrast at a level "
            "of '-', whatever the knobs they do share did"
        )
    varied = sorted(knob_id for knob_id in held if held[knob_id] != variant[knob_id])
    if not varied:
        return (
            f"pair {pair!r} members {sorted((one.id, other.id))} set every knob "
            "they share to the same level — a pair is a planted crux read "
            "against the control built beside it, and two members at one level "
            "are two controls"
        )
    if len(varied) > 1:
        return (
            f"pair {pair!r} varies {varied} across "
            f"{sorted((one.id, other.id))} — a pair varies exactly one knob, or "
            "the rung delta the report prints for it belongs to neither"
        )
    return None


def _annotations(task: Task) -> dict[str, str | None]:
    """What places a task in the capability matrix, as the family lint reads
    it: category, scale and language. `surface` is deliberately excluded —
    it is not a row key this round, so family variants are not required to
    hold it constant, even though `evaluate` still puts it on the records a
    task produces."""
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
                        "surface": task.surface,
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

# How long one live run of each task class gets, in seconds — the tier
# table, and the only place a *v1* live run's agent time limit is set. Two
# things it does not reach: `ai_benchmark.firstparty`'s v0 live runner still
# hardcodes the flat `RUN_TIMEOUT_S` (reachable via `ai-bench eval --live`),
# and every git invocation this runner makes while preparing or capturing a
# workdir (`_commit_pristine`, `_capture_workdir_diff`) carries its own fixed
# 60-second timeout in `_git`, untouched by any tier registered here.
#
# Keyed on the task's category, which is what makes tiering safe for a family
# or a pair rather than merely convenient: the task-set lint already holds
# every member of one of those to one category, so for those two constructs
# "every member of one contrast shares one limit" holds by construction
# instead of by an author's discipline. It does not extend past them: a
# contrast whose members differ in category — a locate/fix comparison over
# one planted defect, whose members are declared neither a family nor a pair
# for exactly that reason — is not held to one limit by this key, and
# registering different tiers for fault-location and bug-fix would confound
# exactly that comparison.
#
# Registered here, in code committed before the sweep that reads it, rather
# than passed at the invocation: a limit a caller can pass is a limit adjusted
# per cell, and a cell granted a longer run once its neighbours have already
# run is measured under conditions nobody chose in advance. A ceiling task and
# a four-turn control are not the same measurement problem, which is why the
# flat 600 seconds this falls back to — an uncalibrated convention from a
# generic subprocess-timeout review fix, first reached in round 3 — is a
# default and no longer the rule (design note §29.4,
# `docs/agents/sweep-protocol.md`).
#
# Nothing was registered before round 4, so every category took the flat
# default and the table arrived moving no cell. When a tier is set, the
# change travels as a cross-round caveat, recorded beside its round the way a
# CLI version change is: contrasts drawn inside one round are unaffected,
# comparisons across the boundary carry it.
#
# Round 4 (design note §30) registers `bug-fix` and `fault-location`, both at
# the flat default's own value, 600: the round's one reading is
# locate-versus-fix over six matched defects, and a limit that differed
# between the two categories would confound the only comparison the round
# exists to make. The value equals the default deliberately rather than by
# omission, so no cross-round caveat arises against round 3.
LIVE_RUN_LIMITS_S: dict[TaskCategory, int] = {
    "bug-fix": 600,
    "fault-location": 600,
}


def live_run_limit_s(task: Task) -> int:
    """How long this task's live run gets: its class's registered limit, or
    the flat default where its class has none set deliberately."""
    return LIVE_RUN_LIMITS_S.get(task.category, RUN_TIMEOUT_S)


def run_live(
    tasks: list[Task],
    models: list[str],
    log_path: Path,
    *,
    sweep: str,
) -> list[Run]:
    """Run every task through tools-enabled claude-code headless per model.

    Each run gets a fresh isolated workdir seeded from the task's starting
    repository, and its row — the workdir diff against the initial commit as
    the graded artifact, plus the CLI's exact measurements — is appended to
    the raw run log the moment the run completes, so a sweep that dies
    part-way keeps every run already paid for. Unlike v0, tools stay enabled:
    the run is genuinely multi-turn, editing the repository it was given.
    Setting sources stay disabled.

    Every row carries `sweep`, the id of the sweep this invocation is a batch
    of. It is required rather than defaulted because neither thing the runner
    could guess from is right: the date collapses two sweeps run in one day
    into one round, and the log's own name splits a sweep across the separate
    invocations that ran its models or resumed it. Which invocations make up
    one sweep is the caller's knowledge, and the round key is a bad place to
    guess — so the caller says, and a paid run costs one more argument.

    How long each run gets is the one thing the caller may *not* say: the
    limit comes from `LIVE_RUN_LIMITS_S`, keyed on the task's class, so that
    it is a property of the task rather than of the invocation that happened
    to run it.
    """
    if problem := _sweep_id_problem(sweep):
        raise IngestError(f"{problem} — {_SWEEP_ID_RULE}")
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
                    task, model, agent_version=version, as_of=today, sweep=sweep,
                )
                log.write(json.dumps(run.model_dump(mode="json"), sort_keys=True) + "\n")
                log.flush()
                runs.append(run)
    return runs


def _run_task_live(
    task: Task, model: str, *,
    agent_version: str, as_of: date, sweep: str,
) -> Run:
    with tempfile.TemporaryDirectory(prefix="ai-bench-live-") as name:
        workdir = Path(name) / "workdir"
        shutil.copytree(task.repo_dir, workdir)
        initial = _commit_pristine(task, workdir)
        payload = claude_headless_json(
            task.id, task.prompt, model, workdir,
            tools=True, timeout_s=live_run_limit_s(task),
        )
        diff = _capture_workdir_diff(task, workdir, initial)
    base = run_from_claude_json(
        task.id, model, payload, agent_version=agent_version, as_of=as_of
    )
    # A v1 Run is v0's fields plus the diff and the sweep id, and the dump
    # keeps that coupling in one place. mypy cannot see through the **dump,
    # but Run's extra="forbid" turns any v0 field this model does not declare
    # into a loud runtime error rather than silent drift.
    return Run(**base.model_dump(), diff=diff, sweep=sweep)


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
