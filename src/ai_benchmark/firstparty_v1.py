"""First-party eval v1: task directories, execution-verified grading
(ticket #10) and the tools-enabled live runner (ticket #11). Sits beside v0
rather than replacing it — the two are separate benchmarks and must never
pool.

Where a v0 task is a prompt plus a check regex, a v1 task is a directory: the
prompt, a small hand-authored starting repository the agent works in, and
held-out grading tests the agent never sees. Grading runs those tests for
real — copy the pristine repo, apply the run's workdir diff, overlay the
canonical grading files over any same-path files the agent touched, run the
held-out tests through the task's **language runner** in a fresh temp dir
with a timeout — so `resolved` is execution-verified, the same standard as
SWE-bench, not pattern-verified.

That last step is the one half of grading that is not language-agnostic, and
it is a seam rather than a set of facts spread through this module:
`ai_benchmark.language_runners` says what a runner owns (how the tests are
invoked, how the verdict is read back, the test globs, the toolchain check,
the starting-repository naming invariant and the lint's source primitives),
what stays this module's, and what stays harness-side. Everything below
reaches it through the task's own declared `language` — `Task.runner` — and
never by naming a toolchain. Python is the first instance; the paragraphs
below describe its defences, which is what `python` registers.

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
that same pipeline and adds no seam to it. A fault-location task — and the
locate-style form of a codebase-comprehension one, which rides all of this
verbatim (`_KEYED_CATEGORIES`) — asks the agent to write a structured answer
file into the workdir; it lands in the workdir diff like anything else the
agent wrote, and a held-out grading test reads it back and compares it against
the accepted-answer key shipped beside that test in `grading/`. So the verdict
stays execution-verified rather than pattern-verified — the run log still
stores the agent's final message and the verdict still never reads it — and the
ground truth is a set of accepted (file, symbol) pairs, never a line number,
because lines shift under any edit and two equally correct answers land on
different ones.

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
there is a defect to find at all is the *existence proof*, and its form is
registered per action (`EXISTENCE_PROOFS`): for a fault-location task, the
partner `bug-fix` member's held-out tests failing on the same pristine
repository, which the lint now goes looking for and runs rather than trusting
to the convention the two were once authored under; for a code-review task, a
held-out test per planted finding that fails on the starting repository and
passes on the author's corrected tree; for a locate-style comprehension
task, which has no defect behind it, a location that resolves in the starting
repository — the key's own rule, registered as this action's form; and for a
test-authoring task, the author's own reference suite, which must pass on the
pristine repository and fail on every planted mutant, checked one mutant at a
time. No keyed action can be added without a registered form, which is the
whole reason the registry exists. A proof is checked by the lint and never by
grading: they live outside `grading/`, so nothing overlays them into a workdir
or collects them as verdict tests.

A fourth verdict shape grades the one action whose deliverable is the tests
themselves. A `test-authoring` task ships no held-out grading tests at all;
it ships planted mutants instead (`MUTANTS_DIR`), and its verdict is the
**mutation gate** (`_mutation_gate`): collect the prompt-named test subtree —
`Task.test_path` — out of the workdir diff and nothing else, then ask two
questions of it. Does that suite pass on the unmodified starting repository,
and does it fail on every planted mutant, each one a copy of that repository
carrying one deliberate behaviour change? `resolved` is the first and all of
the second, binary. What it does not do is score: the fraction of mutants a
suite killed is not computed, not stored and not reported, because a kill rate
under the name `resolved` would be a second quality metric on one action of a
corpus whose values are only comparable within one (design note §67.3). Nor
does it adjudicate anything outside the subtree — an agent that edits the code
under test commits no foul, its edits simply are not in the world the two
gates run in, and a suite that needed them goes red on gate 1 honestly.

What makes that verdict answerable is checked before any agent meets the task
(`_mutant_set_problems`): at least three mutants, every one of them patching a
file of `repo/` and none reaching into the collected test subtree, a starting
repository with no tests already at that path, and a prompt that names it. The
terrain rules are exempted for this action and the exemption is recorded with
its reason (`TERRAIN_EXEMPT_ACTIONS`), because what they guard against is a key
an agent could grep out of its workdir and this key is never in one.

A fifth verdict shape grades the actions whose deliverable is prose with no
code and no held-out test to run against it. A point-keyed task —
`investigation`, `requirement-decomposition` since §94.1 ruled it in, and an
explain-style `codebase-comprehension` task since §106.5 made that category
`_POINT_CATEGORIES`' first point-optional member — ships no grading tests and
no mutants; it ships a
**points key** instead (`points_key`), and its verdict is the **point gate**
(`_point_gate`):
collect the one prompt-named answer file out of the workdir diff — the
mutation gate's subtree rule narrowed to a single path — and ask a pinned,
versioned grader one narrow question per planted point and per optional
disqualifier, never "is this resolved?". A covered ruling must quote the
deliverable back verbatim; a span the gate cannot itself locate in the
deliverable is demoted, mechanically and archived, so an instrument grading
its own quotations is never the only thing standing behind them. `resolved`
is then computed rather than spoken: every planted point covered and no
disqualifier present, binary and universally quantified over points. What it
does not do is score: the fraction of points an answer covered is not
computed, not stored and not reported, for the same reason a mutation gate
never reports a kill rate — a coverage percentage under the name `resolved`
would be a second quality metric on one action of a corpus whose values are
only comparable within one (design note §67.3, pointed at points by §76.5).
The per-point rulings are archived and the verdict is a pure function of
them, so replay re-reads rulings rather than re-asking the grader — the one
non-hermetic surface this grading admits is confined to those archived
rulings and nothing past them.

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
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Literal, NamedTuple, Self, get_args
from urllib.parse import urlparse

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationError,
    model_validator,
)

from ai_benchmark import _answer, point_grader
from ai_benchmark.agents import DEFAULT_AGENT, AgentAdapter, adapter_for
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import (
    RUN_TIMEOUT_S,
    local_today,
)
from ai_benchmark.language_runners import (
    PYTHON,
    TYPESCRIPT,
    LanguageRunner,
    SourceUnreadable,
    runner_for,
    typescript_load_problems,
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

# The corrected tree of a `code-review` task: the author's fixed version of the
# starting repository, in its own subtree of the task directory beside REPO_DIR
# and deliberately *outside* GRADING_DIR. A review task's `repo/` ships the
# change under review already applied, so the corrected tree is what says which
# of those edits were defects; it is read only by the lint, never by grading and
# never by the agent. Outside `grading/` because that directory is overlaid into
# the workdir wholesale at grade time: source files placed there would land in
# the graded workdir, and test files there would be collected as verdict tests.
CORRECTED_DIR = "corrected"

# Where a task's existence proofs live: its own subtree of the task directory,
# beside REPO_DIR and CORRECTED_DIR and — for the same reason that one is —
# outside GRADING_DIR. A proof test is run by the lint and by nothing else. It
# is never overlaid into a workdir, so it cannot reach the agent; it is never
# collected, so it cannot decide a verdict. Both of those are properties of
# where it sits rather than of anyone's discipline: grading copies REPO_DIR and
# GRADING_DIR and nothing else, collection globs test files under GRADING_DIR
# only, and the loader refuses a proof subtree or a corrected tree found inside
# GRADING_DIR (see `_check_task_layout`).
PROOFS_DIR = "proofs"

# The planted mutant set of a `test-authoring` task: one file per mutant, a
# unified diff against REPO_DIR, in its own subtree of the task directory
# beside REPO_DIR, CORRECTED_DIR and PROOFS_DIR — and outside GRADING_DIR for
# exactly the reason those two are. A mutant is this action's held-out key: it
# is applied to a *copy* of the starting repository at grade time, never to the
# workdir the agent worked in, so a mutant overlaid into a workdir would hand
# the agent the answer, and one collected as a test would be run rather than
# planted. Kept as a diff rather than as a whole mutated tree because a mutant
# is one deliberate behaviour change and a diff is what says which change it
# is; it is applied the way a logged diff is (`_git`, `git apply`), so a patch
# git cannot apply is a broken task rather than a silent non-mutation.
MUTANTS_DIR = "mutants"

# The accepted-answer key of a fault-location or codebase-comprehension task,
# inside GRADING_DIR: held out with the grading tests, reaching the workdir by
# the overlay that copies that directory wholesale, and never collected,
# because collection globs test files only.
ANSWER_KEY_FILE = "accepted-answer.json"

# The answer comparison, inside GRADING_DIR beside the key and reaching the
# workdir the same way: `ai_benchmark._answer`, shipped byte for byte into
# every task of both actions below — and into every `code-review` task too,
# because the findings comparison imports its forgiveness rather than restating
# it (see `FINDINGS_MODULE`). Owned rather than hand-written per task because
# the half of the verdict that discriminates is the half worth not miscopying.
ANSWER_MODULE = "_answer.py"

# The held-out grading test that reads the answer comparison, shipped the same
# way and for the same reason: byte for byte into every task of both actions,
# so that nothing binds a task's *grading test* to `_answer.py` except that it
# is the very test this project owns, rather than a hand-written assertion
# that quietly stops calling `answer_problem()` while still shipping an
# unedited copy of the module beside it. A task may ship *additional* grading
# tests alongside this one — resolution requires every grading test to pass,
# so an extra test can only make a task harder to resolve, never let a wrong
# answer through, and nothing here should be tightened into a ban on that.
ANSWER_TEST_FILE = "test_answer.py"

# The two actions whose ground truth is an accepted-answer key, and so the only
# two that may ship one (design note §45.2). `code-review`'s deliverable is an
# answer file too, but what grades it is the set-shaped findings key below, not
# this one: it names the findings of a change rather than the one location of a
# defect, and the quantifier over its accepted half is "every", not "any". Said
# once here, because it is the one thing about these two worth not restating
# per gate:
#
# What they *share* is everything mechanical, verbatim — the key's shape, its
# forgiveness in `_answer.py`, the held-out grading test above, every lint
# rule that reads or runs the key, and the hash gate. There is no new file and
# no new field for the second action.
#
# What they do *not* share is the meaning of each half of the key. For
# `fault-location` the accepted set names where a planted defect lives, and
# the rejected set names the plausible wrong file the symptom points at. For
# `codebase-comprehension` — the locate-style form, "where is X handled", with
# no defect behind it — the accepted set names where correct code lives, and
# the rejected set names the plausible wrong place a related but different
# behaviour lives. That is a shift in what the author writes down, not in what
# is checked: the rejected-half rules (non-empty; names a file the accepted
# set does not already name; not the lint's own synthesised near-miss) apply
# to a comprehension key exactly as written, and are not softened for it.
#
# Which tasks of each action carry a key is where the two differ again. Every
# `fault-location` task does: the location *is* the deliverable, so a task of
# that action with no key has no ground truth at all and the loader refuses
# it. Only *some* `codebase-comprehension` tasks do — carrying a key is what
# makes one locate-style. What the other shape of that category is has since
# been settled the other way round from how this paragraph first read it: §103
# confirmed the point gate on a second action and §106.2 ruled the explain
# shape onto it, so an explain-this-module task is not graded by held-out tests
# of its own but by a **points key** (§106.5), and the category is now the
# point-optional member of `_POINT_CATEGORIES` below exactly as it is the
# optional member here. One category, two shapes, and the key on disk says
# which: an accepted-answer key makes a task locate-style, a points key makes
# it explain-style, and a task shipping both is refused at load. So this set
# is read at load, to say which actions may ship a key and which must; every
# gate after that reads `is_keyed()`, the key on disk, and never a category
# (design note §45.6: locate-style tasks are discovered from their keys, never
# from a hand-kept list). The two are named apart rather than only listed, so
# that the loader can say which of the two rules it is applying, and so that a
# typo in either is a type error rather than a category nothing matches.
_KEY_REQUIRED_CATEGORY: TaskCategory = "fault-location"
_KEY_OPTIONAL_CATEGORY: TaskCategory = "codebase-comprehension"
_KEYED_CATEGORIES = frozenset({_KEY_REQUIRED_CATEGORY, _KEY_OPTIONAL_CATEGORY})

# The one action the findings key belongs to, and the only one that may ship
# one. Mandatory there, the way the accepted-answer key is mandatory for
# fault-location and for the same reason: the findings *are* the deliverable of
# a review, so a review task with no key has no ground truth at all.
_FINDINGS_CATEGORY: TaskCategory = "code-review"

# The one action whose verdict is the mutation gate, and so the only one that
# may ship a mutant set — mandatory there, because the mutants *are* the ground
# truth of a suite-authoring task: one with none has nothing its tests could be
# checked against. Named apart rather than only tested for inline, the way
# `_KEY_REQUIRED_CATEGORY` is, so that a typo here is a type error rather than
# a category nothing matches. Read at load, to say which action may ship a
# mutant set and which must; every gate after that reads `is_mutation_keyed()`
# — the mutants on disk — and never a category.
_MUTATION_CATEGORY: TaskCategory = "test-authoring"

# A `code-review` task's ground truth, inside GRADING_DIR beside the
# accepted-answer key's precedent, and held out exactly as that one is: it
# reaches the workdir by the overlay that copies the grading directory
# wholesale, and is never collected, collection globbing test files only.
FINDINGS_KEY_FILE = "findings-key.json"

# The findings comparison, inside GRADING_DIR beside the key and reaching the
# workdir the same way: `ai_benchmark._findings`, shipped byte for byte into
# every `code-review` task. It imports the location forgiveness from
# ANSWER_MODULE rather than restating it — a review answer and a locate answer
# have to forgive the same spellings — so a review task ships that module
# beside this one, and what checks these bytes has to check those too.
FINDINGS_MODULE = "_findings.py"

# The held-out grading test that reads the findings comparison, shipped the
# same way and for the same reason ANSWER_TEST_FILE is: shipping the module
# byte-identical proves nothing about whether a task's grading test actually
# calls it. A task may ship *additional* grading tests beside this one —
# resolution requires every grading test to pass, so an extra test can only
# make a task harder to resolve, never let a wrong answer through.
FINDINGS_TEST_FILE = "test_findings.py"

# The change under review, inside REPO_DIR: a `code-review` task's starting
# repository ships that change already applied, plus this unified diff of it as
# a file the prompt names, so the agent reviews a diff without a second tree it
# would have to be given. Named here rather than per task so that what reads it
# — the lint, checking that the key's findings describe the change rather than
# the repository at large — finds it the way `REPO_DIR` is found.
REVIEW_DIFF_FILE = "review.diff"

# The actions whose verdict is the point gate, and so the only ones that may
# ship a points key. Two of them *must*, because the planted points are the
# ground truth of a prose deliverable and a task of those actions with none has
# nothing its prose could be graded against. Two rather than one since §94.1
# ruled `requirement-decomposition` into the corpus, which widens a category
# rule and decides nothing new — ADR-0005's Context names that action as one of
# the three this gate was built for, and the key, the gate and the two-sided
# proof are the same shape under both.
#
# The third *may*: §106.5 rules `codebase-comprehension` in as this set's first
# **point-optional** member, and it is optional here for the very reason it is
# optional in `_KEYED_CATEGORIES` above. That category carries two shapes of
# task and the key on disk says which — an accepted-answer key makes one
# locate-style, a points key makes one explain-style (§106.2) — so membership
# here cannot mean "must ship a points key" the way it does for the two above.
# The two rules are named apart rather than only listed, the way
# `_KEY_REQUIRED_CATEGORY` and `_KEY_OPTIONAL_CATEGORY` are and for the same two
# reasons: the loader can say which of the two it is applying, and a typo in
# either is a type error rather than a category nothing matches. It names the
# same category `_KEY_OPTIONAL_CATEGORY` does, and is spelled out again rather
# than aliased to it, because the two are separate facts about one action that
# happen to coincide — that they do is what makes a task shipping both keys
# reachable at all, and the loader refuses that below.
#
# The union keeps the name every existing consumer reads it by — the load-time
# refusal of a points key on an unregistered action and the set that refusal
# names, and `_unregistered_proof_form_problems`' union of the keyed actions.
# Read at load, to say which actions may ship a points key and which must;
# every gate after that reads `is_point_keyed()` — the key on disk — and never
# a category.
_POINT_REQUIRED_CATEGORIES: frozenset[TaskCategory] = frozenset(
    {"investigation", "requirement-decomposition"}
)
_POINT_OPTIONAL_CATEGORY: TaskCategory = "codebase-comprehension"
_POINT_CATEGORIES: frozenset[TaskCategory] = _POINT_REQUIRED_CATEGORIES | {
    _POINT_OPTIONAL_CATEGORY
}

# A point-keyed task's ground truth, inside GRADING_DIR beside the
# findings key's precedent and held out exactly as that one is: it stays on the
# machine, never reaches the workdir the agent works in, and is never disclosed
# by the prompt. Where it differs from the two keys beside it is that nothing
# at grade time reads it out of a workdir — a point-keyed task ships no test
# that runs and its `grading/` is never overlaid over anything — so the only
# reader is the gate, which opens it here in the task directory.
POINTS_KEY_FILE = "points-key.json"

# The two-sided existence proof of a point-keyed task, at the standing address
# every other action's proof lives at: inside PROOFS_DIR, beside REPO_DIR and
# outside GRADING_DIR, never overlaid into a workdir and never read by a
# verdict. The author's own answer to their own question, the plausible-but-
# wrong one beside it, and the rulings the grader gave each — written by
# `prove_points` and read back, offline, by the lint.
#
# Design note §76.10 fixes the subtree and leaves the filenames open; these are
# them, named here rather than spelled in two places so that the writer that
# produces the archive and the lint that reads it back cannot disagree about
# where it is. Markdown because the deliverable of an investigation is argued
# prose and the proof answers are that deliverable, written by the author.
REFERENCE_ANSWER_FILE = "reference-answer.md"
FOIL_ANSWER_FILE = "foil-answer.md"
PROOF_RULINGS_DIR = "rulings"

# Where a run's rulings are archived, one file per run row (see `_point_gate`).
# A module-level default rather than a required argument, and here rather than
# in `cli`, because `evaluate` has three production callers and only one of
# them is `eval-v1`: `reconcile_v1.observed_outcomes` and, through it,
# `calibrate-v1` both replay every logged row at the end of every sweep
# (`docs/agents/sweep-protocol.md`) and thread no rulings argument at all. With
# the default they replay a point-keyed row from the committed archive
# unchanged; with a required argument they would raise on the first one.
# `firstparty_v1` cannot import from `cli` — that is the cycle — so `cli`
# points its `--rulings` flag at this constant rather than owning a second copy
# of the path.
DEFAULT_RULINGS_DIR = Path("data/first-party-v1-rulings")

# The workdir's ignore file belongs to the live runner (which writes and owns
# it), so the loader refuses tasks that ship one of their own.
_IGNORE_FILE = ".gitignore"

GRADE_TIMEOUT_S = 300


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


# The terrain rules the task-set lint holds every task carrying an
# accepted-answer key to (design note 45.6), named one by one because a waiver
# names the single rule it waives: a waiver spelled loosely would waive more
# than its author meant, and a rule renamed under a waiver's feet would refuse
# to load rather than silently widening it.
TerrainRule = Literal[
    # The prompt names no file and no symbol from either half of the key.
    "prompt-names-a-key-location",
    # No content word or word pair of the prompt appears only in the module
    # the accepted answer names.
    "prompt-word-narrows-to-the-accepted-module",
    # An accepted class-level location comes from a file defining more than
    # one class, so answering at class level is not determined by the filename.
    "accepted-class-is-the-only-class",
]

TERRAIN_RULES: tuple[TerrainRule, ...] = get_args(TerrainRule)

# The actions the terrain rules do not apply to, each with the reason (design
# note §67.6). An entry here is an action-level exemption, which is a different
# thing from a `TerrainWaiver`: a waiver is per task, names the exact token it
# silences, and costs its author a reason of that task's own, so an action whose
# every task would carry one identical action-shaped reason would be
# counterfeiting the per-task mechanism rather than using it.
#
# Three of the four entries are their whole action; the fourth is an action's
# point-keyed half, because `codebase-comprehension` carries two shapes of task
# and only one of them keys nothing greppable. Which is why the consultation is
# `_terrain_exemption` and not a bare membership test.
#
# Recorded rather than inherited. A `test-authoring` task carries no
# accepted-answer key and no findings key, so `_ground_truth` returns None and
# the three rules would fire on nothing anyway — but "no rule fired" and "this
# action is exempt, for this reason" are different facts, and only the second
# survives someone later giving this action a key of some other shape.
TERRAIN_EXEMPT_ACTIONS: dict[TaskCategory, str] = {
    _MUTATION_CATEGORY: (
        "the terrain rules stop a key being grepped out of the workdir; a "
        "planted mutant is never in the workdir, and the prompt naming the "
        "module under test is the task's definition rather than a leak"
    ),
    # The two actions whose every task is point-keyed, whose keys are not
    # locations an answer names, so whose ground truth an agent could not grep
    # for however the prompt is worded. An entry each, written out rather than
    # iterated over `_POINT_CATEGORIES`, because a reason of its own is what an
    # entry costs
    # and one string keyed twice would be an action-shaped apology standing in
    # for two. Registered rather than left to fall out of `_ground_truth`
    # returning None for a points key: "no rule fired" and "this action is
    # exempt, for this reason" are different facts, and only the second
    # survives someone later teaching `_ground_truth` to read the points key.
    "investigation": (
        "the terrain rules stop a key being grepped out of the workdir; a "
        "planted point is never in the workdir, and the prompt naming the "
        "deliverable's path and its required sections is the task's definition "
        "rather than a leak"
    ),
    "requirement-decomposition": (
        "the terrain rules stop a key being grepped out of the workdir; the "
        "deliverable is a prose decomposition graded a planted point at a "
        "time, and a point planted about a requirement the prompt states in "
        "full leaves the grep surface those rules guard with nothing behind it"
    ),
    # The third point-keyed action, and the one whose entry is *not* its whole
    # action: `codebase-comprehension` also carries locate-style tasks, whose
    # accepted-answer key is a set of greppable locations and is precisely what
    # these rules exist for. So this entry is consulted by key shape
    # (`_terrain_exemption`) and reaches an explain-style task alone. Its own
    # reason, written out like the three above rather than borrowed from them,
    # because a reason of its own is what an entry costs.
    _POINT_OPTIONAL_CATEGORY: (
        "the terrain rules stop a key being grepped out of the workdir; a "
        "planted point is never in the workdir, and the prompt naming the "
        "deliverable's path and the sections the explanation must carry is the "
        "task's definition rather than a leak"
    ),
}


class TerrainWaiver(BaseModel):
    """A per-task declaration, with a reason, that one named terrain rule does
    not apply to some exact thing in this task.

    The only sanctioned way past a terrain rule: the rule itself is never
    loosened, because a loosened rule is loosened for the whole corpus and for
    every task authored after it, while a waiver costs its author a written
    reason and is visible in the one `task.yaml` it sits in.

    Two properties make it a declaration rather than a mute button, and both
    are the lint's (`_terrain_problems`): a waiver applies *only to what it
    names*, so waiving one word does not silence the rule for a different one;
    and a waiver naming something the rule does not in fact fire on is itself
    a lint problem, so a waiver cannot rot silently once the terrain it
    apologised for has been improved.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: TerrainRule
    # The exact words, or `file.py:Symbol` locations, this waiver covers —
    # spelled the way the rule's own report spells them, so what a waiver
    # names and what it silences cannot drift apart.
    covers: tuple[NonEmptyStr, ...]
    reason: NonEmptyStr

    @model_validator(mode="after")
    def a_waiver_names_what_it_covers(self) -> Self:
        if not self.covers:
            raise ValueError(
                f"the terrain waiver for {self.rule!r} covers nothing — a "
                "waiver applies only to what it names, so one naming nothing "
                "silences nothing and is a reason written down beside a rule "
                "that is still firing"
            )
        repeated = sorted(
            covered for covered, count in Counter(self.covers).items() if count > 1
        )
        if repeated:
            raise ValueError(
                f"the terrain waiver for {self.rule!r} names {repeated} more "
                "than once — what a waiver covers is a set, and a repeated "
                "entry waives nothing a single one would not"
            )
        return self


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
    # Required here too, and for a sharper reason than the coverage table: a
    # task's language is what selects the **language runner** that runs its
    # held-out tests (`Task.runner`), so an undeclared one would mean "graded
    # by whatever the harness falls back to". What runs a task's tests is
    # never implicit — a task carries its own grading mechanism, and a
    # language with no registered runner is refused at load rather than
    # discovered at the first paid run (`_check_task_layout`). A *record*'s
    # language stays optional (`ai_benchmark.schema.Record`) for the reason
    # its surface does: a second-hand row says whatever its source disclosed.
    language: LanguageStr
    prompt: NonEmptyStr
    # Where a `test-authoring` task's deliverable lands: the workdir-relative
    # directory the prompt names as the place to write the suite, and the one
    # subtree grading collects out of the workdir diff (`_mutation_gate`).
    # Declared here rather than inferred from a convention because it is what
    # the prompt promised — a convention mistyped in a prompt would collect a
    # different subtree than the agent was told to write in, and the task would
    # grade every agent unresolved for a reason that says nothing about the
    # agent. Required for that action and refused for every other, which is the
    # validator below: nothing else has a subtree to collect, and a task
    # declaring one that nothing reads is a claim about grading that grading
    # does not make. That it stays inside the workdir is the loader's
    # (`_check_task_layout`), where the refusal can name the task.
    test_path: NonEmptyStr | None = None
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
    # The domain nouns a prompt and a repository about the same subject cannot
    # help sharing — "walk", "round", "parcel" — declared per task because they
    # are per task: the closed-class function words English is built out of are
    # the same everywhere and are owned once in code (`FUNCTION_WORDS`), but
    # what counts as an unavoidable noun is a fact about *this* task's subject
    # and nothing else knows it. Read only by the narrowing terrain rule, which
    # treats these as vocabulary a prompt cannot be blamed for sharing.
    domain_nouns: tuple[NonEmptyStr, ...] = ()
    # Where this task says a named terrain rule does not apply to it, and why.
    # One waiver per rule: two waivers for one rule would be two reasons for
    # one exception, and which of them a given word was covered by would be
    # unanswerable.
    terrain_waiver: tuple[TerrainWaiver, ...] = ()
    directory: Path

    @property
    def runner(self) -> LanguageRunner:
        """The language runner that grades this task.

        Selected by the task's own declared `language` and by nothing an
        operator can pass: a task carries its own grading mechanism, and no
        flag may grade it with the wrong one. What a runner owns and what
        stays the grader's is written down in `ai_benchmark.language_runners`.
        """
        return runner_for(self.language)

    @property
    def repo_dir(self) -> Path:
        """The pristine starting repository, copied fresh for every run."""
        return self.directory / REPO_DIR

    @property
    def grading_dir(self) -> Path:
        """The held-out grading files, canonical at grade time."""
        return self.directory / GRADING_DIR

    @property
    def corrected_dir(self) -> Path:
        """A `code-review` task's corrected tree: the starting repository with
        the defects of the change under review put right.

        Beside `repo/` and outside `grading/`, so nothing about it is overlaid
        into a workdir or collected as a grading test — it is read by the lint
        and by nothing else. Empty for every other action, which is why this is
        a path rather than a check: what refuses a corrected tree in the wrong
        place is the layout, not this property.
        """
        return self.directory / CORRECTED_DIR

    @property
    def proofs_dir(self) -> Path:
        """This task's existence proofs: the held-out tests that say a planted
        truth is really there.

        Beside `repo/` and `corrected/` and outside `grading/`, so that nothing
        in it is overlaid into a workdir or collected as a grading test — the
        lint runs these against `repo/` and `corrected/` itself, and no other
        caller ever opens this directory. Empty for every action whose proof
        form runs no test, which is why this is a path rather than a check.
        """
        return self.directory / PROOFS_DIR

    @property
    def mutants_dir(self) -> Path:
        """This task's planted mutants: one patch per mutant, each a variant of
        the starting repository grading builds for itself.

        Beside `repo/`, `corrected/` and `proofs/` and outside `grading/`, so
        that nothing in it is overlaid into a workdir or collected as a test —
        the mutation gate applies these to its own throwaway copies, and no
        other caller opens this directory. Empty for every action but
        `test-authoring`, which is why this is a path rather than a check: what
        refuses a mutant set shipped by another action is the layout, not this
        property.
        """
        return self.directory / MUTANTS_DIR

    @property
    def harness_test_paths(self) -> tuple[str, ...]:
        """The harness-side half of the suite: the canonical Python checks.

        The answer-key test, the findings-key test and the generated hash gate
        read JSON and file digests out of the workdir and never the
        repository's language. They ship byte for byte into any task's grading
        directory and are run by pytest, which is the harness's own dependency
        and not the task's — so a TypeScript task's grading directory holds
        canonical Python beside its own held-out tests, and this half is found
        by the *Python* runner's glob whatever the task declares.
        """
        return self._grading_tests_matching(PYTHON.grading_test_glob)

    @property
    def language_test_paths(self) -> tuple[str, ...]:
        """The task's own held-out tests, found by its runner's glob rather
        than by a pytest name written here: which files these are is a question
        about the language that grades it."""
        return self._grading_tests_matching(self.runner.grading_test_glob)

    @property
    def grading_test_paths(self) -> tuple[str, ...]:
        """Every grading test the verdict reads, relative to the workdir it is
        overlaid into: both halves, and for a Python task the one set twice."""
        return tuple(sorted(set(self.harness_test_paths) | set(self.language_test_paths)))

    @property
    def grading_halves(self) -> tuple[tuple[LanguageRunner, tuple[str, ...]], ...]:
        """Each half present, with the runner that runs it.

        A task's verdict is "every half present passes": the harness-side pytest
        checks under pytest, the task's own held-out tests under its declared
        runner, and a half with no files in it is not run at all rather than run
        empty — an empty invocation collects nothing, and "no tests ran" is how
        every runner here spells unresolved. A Python task's two halves are the
        same files run by the same runner, so it keeps exactly one.
        """
        halves: list[tuple[LanguageRunner, tuple[str, ...]]] = []
        for runner, paths in (
            (PYTHON, self.harness_test_paths),
            (self.runner, self.language_test_paths),
        ):
            if paths and not any(seen is runner for seen, _ in halves):
                halves.append((runner, paths))
        return tuple(halves)

    def _grading_tests_matching(self, glob: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                str(path.relative_to(self.grading_dir))
                for path in self.grading_dir.rglob(glob)
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
    def only_the_mutation_gate_collects_a_test_path(self) -> Self:
        """A test path is the mutation gate's and no other action's.

        The field says one thing: *this* subtree of the workdir diff is the
        deliverable, and everything else in it is archived rather than scored.
        No other verdict shape in this module reads a subtree — the rest grade
        by overlaying held-out tests over whatever the agent wrote — so a task
        of any other action declaring one has written down a rule about its own
        grading that its grading never applies, which is the kind of claim this
        loader refuses rather than ignores.
        """
        if self.test_path is not None and self.category != _MUTATION_CATEGORY:
            raise ValueError(
                f"a {self.category} task declares test_path {self.test_path!r} "
                f"— the test path is the subtree {_MUTATION_CATEGORY}'s "
                "mutation gate collects out of the workdir diff, and every "
                "other action is graded by held-out tests laid over the whole "
                "workdir, so nothing here would ever read it"
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

    @model_validator(mode="after")
    def each_terrain_rule_is_waived_at_most_once(self) -> Self:
        repeated = sorted(
            rule
            for rule, count in Counter(
                waiver.rule for waiver in self.terrain_waiver
            ).items()
            if count > 1
        )
        if repeated:
            raise ValueError(
                f"terrain rule(s) {repeated} are waived more than once — a "
                "waiver carries the reason its rule does not apply here, and "
                "two waivers for one rule are two reasons for one exception "
                "with nothing saying which covers what. Name every word the "
                "rule is waived for in one waiver"
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


def _repeated_pairs(answers: Sequence[Answer]) -> list[tuple[str, str]]:
    """The (file, symbol) pairs this half of an accepted-answer key names more
    than once.

    Each half of that key is a *set* of locations, and a pair repeated in one
    claims nothing an unrepeated one would not. The findings key has its own
    rule (`_colliding_locations`) rather than sharing this one: there the same
    question has to be asked across both halves at once and across every
    alternative of every **planted finding**, and asked through the comparison
    rather than by equality, because a bare-symbol alternative that also answers
    another finding's qualified one would let one answer satisfy two findings.
    Equality is enough here, where the accepted half names one location per
    answer and the two halves are checked apart.
    """
    return sorted(
        pair
        for pair, count in Counter(
            (answer.file, answer.symbol) for answer in answers
        ).items()
        if count > 1
    )


class AnswerKey(BaseModel):
    """A keyed task's ground truth: where the agent writes its answer, every
    location that answer may name, and the near-misses it may not. One shape
    for both actions that carry one — see `_KEYED_CATEGORIES` for what
    fault-location and locate-style codebase-comprehension share (all of this)
    and what they do not (what each half *means*).

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
    responsible, or the module a related but different behaviour lives in —
    and that is what the author writes here.

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
            if repeated := _repeated_pairs(answers):
                raise ValueError(
                    f"{half} names the same (file, symbol) pair more than once: "
                    f"{repeated} — {half} is a set of locations, and a pair "
                    "repeated in it claims nothing an unrepeated one would not"
                )
        return self


def is_keyed(task: Task) -> bool:
    """Whether this task holds an answer to give away.

    One definition of "keyed", read by everything that applies a rule to the
    keyed corpus: the key's own rules (`_answer_key_problems`), the held-out
    grading test (`_answer_test_problems`), the discrimination gate the lint
    runs through the real pipeline (`_discrimination_problems`), the terrain
    rules (`_terrain_problems`) and the hash gate (`_hash_gate_problems`).
    Keyed on the *key*, never on `category` and never on a hand-kept list of
    task ids: `fault-location` is where the keys started, but a locate-style
    `codebase-comprehension` task is graded off the same file and is greppable
    in the same way, and a list would leave the seventh keyed task inheriting
    none of it.

    The one place `category` is still read is the loader, which says which
    actions may ship a key and which must ship one (`_KEYED_CATEGORIES`).
    """
    return (task.grading_dir / ANSWER_KEY_FILE).is_file()


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
    """The answer comparison, as every keyed task's `grading/_answer.py` has to
    be byte for byte — a fault-location task's and a locate-style
    codebase-comprehension task's alike, since neither the comparison nor its
    forgiveness differs between the two actions (`_KEYED_CATEGORIES`).

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
    """The held-out grading test, as every keyed task's
    `grading/test_answer.py` has to be byte for byte — see `ANSWER_TEST_FILE`
    and `_ANSWER_TEST_SOURCE`. Its own text still says "fault-location",
    because it is shipped bytes: rewording it would make the six checked-in
    copies drift from their source, and the second action rides this file
    unchanged, which is the point (`_KEYED_CATEGORIES`)."""
    return _ANSWER_TEST_SOURCE.encode("utf-8")


# --- code-review: the findings key and its set-shaped verdict ------------------
#
# The round's one new instrument (design note §45.2-45.3). A review task hands
# the agent a change that is already applied to its starting repository, plus a
# unified diff of that change (`REVIEW_DIFF_FILE`), and asks which of it is
# wrong; the deliverable is an answer file listing findings, one (file, symbol)
# location each, and the ground truth is a key whose two halves are *sets*.
#
# What it borrows, whole: the answer file reaching grading in the workdir diff
# with no new seam, the pair model and its refusals (`Answer`), the location
# forgiveness (`_answer.py`, imported by `_findings.py` rather than copied), and
# one owned comparison module plus one owned held-out test shipped byte for
# byte. What is genuinely new is the quantifier — a locate verdict asks whether
# the one answer is *in* the accepted set, a review verdict asks whether the
# answer's findings *cover* it — and that is the whole of why this is a second
# key rather than a second use of the first.


class PlantedFinding(BaseModel):
    """One defect the author put into the change under review, as the set of
    locations that legitimately describe it.

    A finding is not one location but several alternatives, and an answer
    matches the finding when it matches **any one** of them. That is the
    mitigation for this grading's expensive assumption — that an agent which
    correctly spots a defect describes it at a level the author anticipated —
    and it is the same mitigation the **accepted-answer key** carries, finally
    expressible here. Under the flat shape this replaced, a planted finding
    *was* one location and the accepted half was read under "every", so a key
    that wrote down both the defective method and the class enclosing it would
    have demanded that the answer report the same defect twice, once at each
    level. The one checked-in review task keyed each finding at a single level
    and said so in its comments; this is what that comment was working around.

    The **first alternative is the primary**: the most specific location,
    typically the defective function, and what the finding is named after
    wherever a name is needed — the file name of its **existence proof**, and
    every lint message about it. Named off the key rather than declared beside
    it, so there is no third place for the two to drift apart in.

    Non-empty, because a finding with no location is a finding no answer can
    match and every answer therefore fails.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Spelled `any` because that is the word the key file uses, and the key file
    # is what an author reads: `{"any": [...]}` says the quantifier over the
    # alternatives out loud, against the "every" the accepted half as a whole is
    # read under. Shadowing the builtin is confined to this class body — a
    # method's own body resolves `any` to the builtin as usual.
    any: tuple[Answer, ...]

    @property
    def primary(self) -> Answer:
        """The most specific of the alternatives, and the one this finding is
        named after."""
        return self.any[0]

    @model_validator(mode="before")
    @classmethod
    def a_planted_finding_is_a_set_of_alternatives(cls, data: Any) -> Any:
        if isinstance(data, dict) and "any" not in data:
            raise ValueError(
                f"planted finding {dict(data)} names one location flat — a "
                "planted finding is a set of alternative locations, written "
                '{"any": [{"file": ..., "symbol": ...}, ...]}, and it is matched '
                "when an answer matches any one of them. The first alternative "
                "is the primary: the most specific location, typically the "
                "defective function, and the one the finding is named after"
            )
        return data

    @model_validator(mode="after")
    def a_planted_finding_names_somewhere(self) -> Self:
        if not self.any:
            raise ValueError(
                "a planted finding names no location at all — 'any' is a "
                "non-empty list of the alternatives that legitimately describe "
                "one defect, so an empty one is a finding no answer can match "
                "and every answer therefore fails"
            )
        return self


class FindingsKey(BaseModel):
    """A `code-review` task's ground truth: where the agent writes its answer,
    every planted finding that answer has to report, and the non-findings it
    may not report.

    Both halves are sets of locations built out of the same `Answer` as
    `AnswerKey` — the same refusal of a line number, which shifts under any
    edit, and of a bare file, which on repositories this small is barely a
    location. A second pair model would be a second place for those refusals to
    be written and drift from.

    Where the two halves differ in shape: `rejected` is a flat set of locations,
    while `accepted` is a set of **planted findings**, each of them itself a set
    of alternative locations (`PlantedFinding`). That asymmetry is the verdict's
    own — a rejected location is one place a review may not point at, while a
    planted finding is one defect that several spellings legitimately describe.

    Where it differs from `AnswerKey` is not its shape but what the verdict does
    with it. `accepted` is read under "every ... at some alternative": each
    planted finding has to be matched by some finding of the answer, at any one
    of its alternatives, so a review that spots three of four defects is
    unresolved. `rejected` is read under "none": a finding matching one of them
    is a defect reported where the change is correct, which is what stops
    every-line-is-a-finding from passing. A finding matching neither half is
    ignored and archived — a real problem the author did not plant must not fail
    the run — and there is nothing between the two verdicts, because a partial
    recall rate would be a new quality metric.

    Either set may be empty as far as this model is concerned, for the reason
    `AnswerKey` gives: a task that cannot load cannot be linted, and an empty
    half is exactly the defect the loader and the lint exist to name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer_path: NonEmptyStr
    accepted: tuple[PlantedFinding, ...] = ()
    rejected: tuple[Answer, ...] = ()

    @model_validator(mode="after")
    def no_location_is_named_twice_anywhere_in_the_key(self) -> Self:
        if collisions := _colliding_locations(self):
            one, other = collisions[0]
            raise ValueError(
                f"{one} and {other} are the same location twice over — every "
                "location this key names, in either half and across every "
                "planted finding, has to be one an answer can match without "
                "also matching another. Two alternatives of one finding that "
                "collide claim nothing a single one would not; two findings "
                "sharing one let a single answer satisfy both, so a review "
                "spotting one defect covers two; and a location in both halves "
                "makes every answer unresolved whatever it says, since "
                "reporting it fails on the rejected half and leaving it out "
                "fails on the accepted one. Collision is judged through the "
                "comparison the verdict uses rather than by equality, because "
                "a bare symbol answers a key spelled `Class.method`"
            )
        return self


def _colliding_locations(
    key: FindingsKey,
) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """Every pair of this key's locations that one answer could match at once.

    Read through `matches()` in both directions rather than by equality,
    because the comparison forgives a description level: an answer of `add`
    matches an alternative spelled `Rota.add`, so an alternative spelled `add`
    elsewhere in the key is answered by the very same word. Equality would call
    those two distinct and let one finding of an answer cover two planted
    findings — a review that spotted one defect graded as having spotted both.

    Every pair is walked once, in the order the key writes them, and the
    refusal names the first — a key is repaired one collision at a time, and a
    message listing every pair a broken key produces buries the one to fix.
    """
    located: list[tuple[str, str]] = [
        (alternative.file, alternative.symbol)
        for planted in key.accepted
        for alternative in planted.any
    ] + [(answer.file, answer.symbol) for answer in key.rejected]
    return [
        (one, other)
        for index, one in enumerate(located)
        for other in located[index + 1 :]
        if _answer.matches(one, other) or _answer.matches(other, one)
    ]


def is_findings_keyed(task: Task) -> bool:
    """Whether this task ships a findings key.

    Read off the key on disk rather than off the category, the way `is_keyed`
    is, so that every gate over a review task's ground truth is gated on the
    ground truth being there. The one place `category` is read is the loader,
    which says which action may ship this key and must
    (`_FINDINGS_CATEGORY`).
    """
    return (task.grading_dir / FINDINGS_KEY_FILE).is_file()


def carries_a_key(task: Task) -> bool:
    """Whether this task's deliverable is an answer file of either shape — an
    **accepted-answer key** (`is_keyed`) or a **findings key**
    (`is_findings_keyed`).

    What the two have in common is the exposure the hash gate closes: the
    deliverable is a location or a list of them, never a repair, and a run that
    repaired the code and then answered correctly would grade resolved at
    answer-file cost. So the gate is discovered off *either* key. Everything
    that reads the key's contents keeps its own, narrower predicate.
    """
    return is_keyed(task) or is_findings_keyed(task)


def findings_key(task: Task) -> FindingsKey:
    """The findings key shipped inside this task's grading directory.

    One file read two ways, exactly as `answer_key` is: the lint reads it from
    the task directory, and the held-out grading test reads the very same bytes
    out of the workdir the overlay copied them into. The declared answer path
    lives here rather than in the grading test, so nothing can hardcode a path
    the prompt does not name.
    """
    path = task.grading_dir / FINDINGS_KEY_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{FINDINGS_KEY_FILE} is missing or "
            f"unreadable ({error}) — a {task.category} task is graded by "
            "comparing the findings the agent reports against the planted "
            "findings, which ship with the held-out grading tests"
        ) from error
    except json.JSONDecodeError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{FINDINGS_KEY_FILE} is not JSON ({error}) "
            "— the grading test reads it with the standard library alone"
        ) from error
    try:
        return FindingsKey.model_validate(raw)
    except ValidationError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{FINDINGS_KEY_FILE}: {error}"
        ) from error


class PlantedPoint(BaseModel):
    """One thing an investigation's answer has to say — or, as a
    disqualifier, one thing it may not.

    An id and the claim's text, and nothing else. The text is what the grader
    is asked about; the id is what the archive is keyed by, so an archived
    ruling stays readable against the key that produced it. One shape carries
    both halves because a disqualifier *is* a planted point asked of the same
    answer — "is this claim made?" — and only the verdict's polarity differs
    (`_point_gate`). A second model would be a second place for the id rule to
    be written and drift from.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    text: NonEmptyStr


class PointsKey(BaseModel):
    """An `investigation` task's ground truth: where the agent writes its
    answer, every planted point that answer has to cover, and the claims that
    disqualify it however much else it covered.

    Where it differs from the two keys above is what a match is made of. A
    locate key and a review key are read as (file, symbol) locations, because
    their deliverable names places; an investigation's deliverable is prose,
    so a point is matched by a **grader's ruling with a verbatim span**
    (`ai_benchmark.point_grader`) rather than by a comparison this module
    could write. What it shares with them is the quantifier: `points` is read
    under "every", `disqualifiers` under "none", and there is nothing between
    the two verdicts — a fraction of the points covered would be a second
    quality metric wearing `resolved`'s name (design note §67.3, pointed at
    points).

    Ids are unique across both halves, because the archive is keyed by id and
    two questions sharing one would archive as a single ruling — the second
    silently answering for the first. `disqualifiers` may be empty: not every
    investigation has a plausible wrong answer worth naming. `points` may be,
    as far as this model is concerned, for the reason `AnswerKey` gives — a
    task that cannot load cannot be told what is wrong with it — and the
    loader refuses that key by name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer_path: NonEmptyStr
    points: tuple[PlantedPoint, ...] = ()
    disqualifiers: tuple[PlantedPoint, ...] = ()

    @model_validator(mode="after")
    def no_id_is_used_twice(self) -> Self:
        seen: set[str] = set()
        for planted in (*self.points, *self.disqualifiers):
            if planted.id in seen:
                raise ValueError(
                    f"{planted.id!r} is the id of two of this key's questions "
                    "— a run's rulings are archived one per id, across the "
                    "points and the disqualifiers alike, so a shared id "
                    "archives one ruling where two were asked and lets the "
                    "second answer for the first"
                )
            seen.add(planted.id)
        return self


def is_point_keyed(task: Task) -> bool:
    """Whether this task's verdict is the point gate: it ships a points key.

    Read off the key on disk rather than off the category, the way `is_keyed`,
    `is_findings_keyed` and `is_mutation_keyed` are, so that the one gate whose
    ground truth is prose is reached only where that ground truth is there. The
    one place `category` is read is the loader, which says which actions may
    ship this key and must (`_POINT_CATEGORIES`).
    """
    return (task.grading_dir / POINTS_KEY_FILE).is_file()


def points_key(task: Task) -> PointsKey:
    """The points key shipped inside this task's grading directory.

    Read here and by the gate alone, which is the one way this key differs
    from the two above: those are read a second time by a held-out grading
    test out of the workdir the overlay copied them into, and a point-keyed
    task ships no test that runs. The declared answer path
    lives here for the same reason theirs does — nothing may hardcode a path
    the prompt does not name.
    """
    path = task.grading_dir / POINTS_KEY_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{POINTS_KEY_FILE} is missing or "
            f"unreadable ({error}) — a {task.category} task is graded by "
            "asking a grader, one planted point at a time, whether the "
            "answer covers it, and the planted points are that key"
        ) from error
    except json.JSONDecodeError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{POINTS_KEY_FILE} is not JSON ({error})"
        ) from error
    try:
        return PointsKey.model_validate(raw)
    except ValidationError as error:
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/{POINTS_KEY_FILE}: {error}"
        ) from error


# The two shapes a task's ground truth comes in, seen as the one thing a rule
# that reads *either* of them can read: an answer path, an accepted half and a
# rejected half, both made of (file, symbol) locations. Written as a union
# rather than as a base class because the two keys are deliberately separate
# models — what differs between them is the quantifier the accepted half is
# read under, and a shared base would invite a rule to be written once over
# something the two do not in fact share.
#
# What is written against this: the three terrain rules, which the design note
# applies to "every task that carries a key" and for a reason that does not
# distinguish the actions — a task carrying a key holds an answer it can give
# away — and the near-miss synthesis, which is a question about a file's
# symbols and not about how many locations the key names.
KeyedGroundTruth = AnswerKey | FindingsKey


def _accepted_locations(key: KeyedGroundTruth) -> tuple[Answer, ...]:
    """Every location either key's accepted half names, flat.

    The one place the two accepted halves are told apart, so that nothing else
    has to be: a locate key's is a set of locations and a review key's is a set
    of **planted findings**, each of them a set of alternatives, and every rule
    that asks "is this a location an agent could give?" wants all of them
    equally. Each alternative is a location the author declared legitimately
    correct, so a rule that read only the primaries would let an unreachable
    file or an undefined symbol through on any alternative but the first.

    What this deliberately loses is which alternatives belong to which finding.
    Rules that need that — the discrimination gate, the existence proof — read
    `key.accepted` themselves.
    """
    if isinstance(key, FindingsKey):
        return tuple(
            alternative for planted in key.accepted for alternative in planted.any
        )
    return key.accepted


def _ground_truth(task: Task) -> KeyedGroundTruth | None:
    """The key this task carries, whichever of the two it is, or None where it
    carries neither.

    Read off the keys on disk and never off the category, the way `is_keyed`
    and `is_findings_keyed` are, so that a `code-review` task inherited the
    terrain rules the day it shipped a key rather than the day someone
    remembered to add its category to a list. The two are mutually exclusive by
    the loader's own gates: an accepted-answer key may only be shipped by the
    two keyed actions and a findings key only by `code-review`, so the order
    they are tried in here decides nothing.
    """
    if is_keyed(task):
        return answer_key(task)
    if is_findings_keyed(task):
        return findings_key(task)
    return None


def _empty_accepted_findings_message(task: Task) -> str:
    """What is wrong with a review task whose findings key plants nothing,
    worded once so the loader and the lint say the same thing.

    The loader has to refuse this too, for the reason it refuses an empty
    accepted-answer key: `ai-bench run-live` loads a task set but never lints
    it, so a review task with nothing to find would otherwise reach a paid run
    — and it would grade every agent *resolved*, since "every planted finding
    is matched" is vacuously true of no planted findings.
    """
    return (
        f"{task.id}: the findings key plants no findings — a review verdict is "
        "that every planted finding was reported, which is satisfied by any "
        "answer at all when none were planted, so the task would grade every "
        "agent resolved without measuring anything"
    )


def findings_module_source() -> bytes:
    """The findings comparison, as every `code-review` task's
    `grading/_findings.py` has to be byte for byte.

    The project's own module read off disk rather than a string constant, so
    that the shipped copies are compared against code mypy type-checks and the
    tests exercise, and an author has one file to copy. Note that the file is
    read, never imported: it imports `_answer` flat, the way the two sit beside
    each other in a grading directory, which is the only place it runs.
    """
    return Path(__file__).with_name(FINDINGS_MODULE).read_bytes()


# The held-out grading test itself, canonical: a one-line assertion over
# `findings_problem()`, shipped byte for byte as `_ANSWER_TEST_SOURCE` is and
# for the same reason — a task shipping the comparison unedited proves nothing
# about whether its grading test still calls it. A plain string constant rather
# than a second file on disk: there is no logic here worth having mypy check,
# only the one assertion the held-out test is required to make.
_FINDINGS_TEST_SOURCE = '''\
"""Held out: whether the agent's answer file reports every planted finding.

Canonical — this project's own file, shipped byte for byte into every
code-review task's grading directory and read back that way by the task-set
lint, so that nothing in a task's grading directory can stop consulting
`_findings.py` while still shipping an unedited copy of it. A task may ship
additional grading tests beside this one: resolution requires every grading
test to pass, so an extra test can only make the task harder to resolve, never
let a wrong answer through.
"""

from _findings import findings_problem


def test_the_answer_reports_every_planted_finding():
    assert (problem := findings_problem()) is None, problem
'''


def findings_test_source() -> bytes:
    """The held-out grading test, as every `code-review` task's
    `grading/test_findings.py` has to be byte for byte — see
    `FINDINGS_TEST_FILE` and `_FINDINGS_TEST_SOURCE`."""
    return _FINDINGS_TEST_SOURCE.encode("utf-8")


# --- test-authoring: the planted mutants and the two-gate verdict --------------


def mutant_patches(task: Task) -> list[Path]:
    """This task's planted mutants, in the order the gate runs them: sorted by
    filename, one patch per mutant.

    Sorted rather than in directory order because a verdict must be
    reproducible and a directory listing is not ordered anywhere in
    particular; files only, because a mutant is one diff and a directory of
    them would be a set the gate could not name.
    """
    if not task.mutants_dir.is_dir():
        return []
    return sorted(path for path in task.mutants_dir.iterdir() if path.is_file())


def is_mutation_keyed(task: Task) -> bool:
    """Whether this task's verdict is the mutation gate: it ships planted
    mutants.

    Read off the mutants on disk, the way `is_keyed` and `is_findings_keyed`
    are read off their keys and for the same reason (design note §45.6): the
    loader alone reads the category, to say which action may ship a mutant set
    and which must, and every gate after it asks this. So which verdict shape
    grades a task is a fact about what the task ships, and a task can never be
    graded by a shape whose ground truth is not there.
    """
    return bool(mutant_patches(task))


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


CostSource = Literal["vendor-reported", "table-derived"]


def _cost_source_problem(
    agent: str, cost_source: CostSource | None, price_table: str | None
) -> str | None:
    """What is wrong with this row's cost-source disclosure, if anything."""
    if agent == "codex" and (
        cost_source != "table-derived" or price_table is None
    ):
        return (
            f"agent {agent!r} needs cost_source='table-derived' and a "
            "price_table version — codex reports no dollar figure of its own, "
            "so its cost_usd is always computed from a price table"
        )
    if cost_source == "vendor-reported" and price_table is not None:
        return (
            "cost_source='vendor-reported' rows name no price_table — the "
            "vendor's own figure was not computed from one"
        )
    if cost_source == "table-derived" and price_table is None:
        return (
            "cost_source='table-derived' rows must name the price_table "
            "version cost_usd was computed from"
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
    # How cost_usd was obtained (CONTEXT.md's "cost source"), and, for a
    # table-derived figure, the price_table version it was computed from.
    # v1-only: no Codex row is ever written to a v0 log, and firstparty's v0
    # Run is a different log's shape, so v0 stays untouched. Both optional
    # and defaulting to absent — every row written before this ticket has
    # neither, and stays valid and replays unchanged. Nothing here recomputes
    # cost_usd, on load or on replay: it is whatever the row says, and a later
    # price_table version reprices nothing already logged.
    cost_source: CostSource | None = None
    price_table: str | None = None

    @model_validator(mode="after")
    def sweep_id_is_a_usable_round_key(self) -> Self:
        if self.sweep is not None and (problem := _sweep_id_problem(self.sweep)):
            raise ValueError(f"{problem} — {_SWEEP_ID_RULE}")
        return self

    @model_validator(mode="after")
    def cost_source_is_not_self_contradictory(self) -> Self:
        if problem := _cost_source_problem(
            self.agent, self.cost_source, self.price_table
        ):
            raise ValueError(problem)
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
    # First, because everything below reads the task through its runner — the
    # glob that finds its held-out tests, its starting-repository naming
    # invariant — and because a language nothing can run is the one problem
    # here that no amount of correct layout would rescue. Reported with the
    # task id in front of the registry's own message, which names the
    # registered runners: an author who declared `js` should be told what the
    # spelling is rather than that something went wrong.
    try:
        task.runner
    except IngestError as error:
        raise IngestError(f"{task.id}: {error}") from error
    if not task.repo_dir.is_dir() or not any(task.repo_dir.iterdir()):
        raise IngestError(
            f"{task.id}: {REPO_DIR}/ is missing or empty — a v1 task gives the "
            "agent a starting repository"
        )
    # The naming invariant is the runner's: what a top-level name may not
    # collide with is a fact about how that language's toolchain resolves an
    # import, and the runner says both whether it is broken and why.
    if naming := task.runner.starting_repository_problem(task.repo_dir):
        raise IngestError(f"{task.id}: {naming}")
    if (task.repo_dir / _IGNORE_FILE).exists():
        raise IngestError(
            f"{task.id}: {REPO_DIR}/ ships a {_IGNORE_FILE} — the live runner "
            "owns the workdir's ignore file and would silently replace this "
            "one, so the agent would see a repository that differs from the "
            "pristine one grading applies the diff to"
        )
    if misplaced := _held_out_of_the_workdir_but_not_of_grading(task):
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/ holds {misplaced} — the corrected tree, "
            "the existence proofs and the planted mutants are read by the lint "
            "and by the mutation gate's own throwaway copies, never by the "
            f"workdir, and {GRADING_DIR}/ is overlaid into the workdir wholesale "
            "at grade time, so a corrected tree or a mutant kept there would "
            "hand the agent the answers and a proof test kept there would be "
            f"collected as a verdict test. All three live beside {REPO_DIR}/ in "
            f"the task directory ({CORRECTED_DIR}/, {PROOFS_DIR}/ and "
            f"{MUTANTS_DIR}/), which is what makes 'never overlaid, never "
            "collected, read by the lint and the gate only' a property of the "
            "layout rather than of an author remembering it"
        )
    if is_mutation_keyed(task) and task.category != _MUTATION_CATEGORY:
        raise IngestError(
            f"{task.id}: a {task.category} task ships {MUTANTS_DIR}/ — a "
            f"planted mutant is the ground truth of {_MUTATION_CATEGORY}, the "
            "one action whose deliverable is a test suite rather than a change "
            "to the code under test, and which verdict shape grades a task is "
            "read off the mutants being there, so a mutant set shipped by any "
            "other action would swap this task's whole verdict for one its "
            "grading directory was never authored for"
        )
    if is_point_keyed(task) and task.category not in _POINT_CATEGORIES:
        raise IngestError(
            f"{task.id}: a {task.category} task ships {GRADING_DIR}/"
            f"{POINTS_KEY_FILE} — the points key is the ground truth of "
            f"{sorted(_POINT_CATEGORIES)}, the registered actions whose "
            "deliverable is prose graded a point at a time, and which verdict "
            "shape grades a task is read off the key being there, so a points "
            "key shipped by any other action would swap this task's whole "
            "verdict for one its grading directory was never authored for"
        )
    if is_keyed(task) and is_point_keyed(task):
        # Two ground truths for one deliverable. Only reachable for
        # `codebase-comprehension`, the one action that stands in both key
        # registries — the refusals above and below have already turned away
        # either key on any other action — and it stands beside those two
        # wrong-action refusals because it is the same kind of refusal: which
        # verdict shape grades a task is read off the key on disk, so a task
        # carrying both keys names no single ground truth for its answer file
        # and there is nothing to choose between them by. Raised here, ahead of
        # the branch below, so that what the author is told is the both-keys
        # fault rather than whichever of the two keys happened to be parsed
        # first.
        raise IngestError(
            f"{task.id}: a {task.category} task ships both {GRADING_DIR}/"
            f"{ANSWER_KEY_FILE} and {GRADING_DIR}/{POINTS_KEY_FILE} — the "
            "accepted-answer key is a locate-style task's ground truth and the "
            "points key is an explain-style task's, which verdict shape grades "
            "a task is read off the key on disk, and a task carrying both "
            "names no single ground truth for the one answer file its prompt "
            "asks for. Ship the key of the shape this task is and no other"
        )
    if task.category == _MUTATION_CATEGORY:
        # Every check here is a load-time one and not the lint's, for the reason
        # the keys above are read at load: `ai-bench run-live` loads a task set
        # and never lints it, so a task the mutation gate could not grade would
        # otherwise reach a paid run and come back unresolved for a reason that
        # says nothing about the agent. What the *set* of mutants has to satisfy
        # — a minimum count, disjointness from the test path, the registered
        # existence proof — is the lint's, and stays there.
        _check_mutation_gate_layout(task)
    elif is_point_keyed(task) or task.category in _POINT_REQUIRED_CATEGORIES:
        # The tasks that ship no held-out grading test at all: a point-keyed
        # `grading/` holds the key and nothing that runs, because what grades
        # it is a grader's rulings over one prose file rather than a suite.
        # Read off the key on disk, plus the actions whose key is mandatory,
        # exactly as the accepted-answer key's branch below is read — §45.6's
        # rule and already this file's own sentence: the key on disk decides
        # the shape, so a `codebase-comprehension` task shipping no points key
        # is simply not the explain-style form and falls through to the
        # held-out-suite branch, while an `investigation` or
        # `requirement-decomposition` task shipping none is refused by
        # `points_key()` right here.
        # Read at load and not left to the lint, for the reason the two
        # keys above are read at load — `ai-bench run-live` loads a task set
        # and never lints it, so a task the point gate could not grade would
        # otherwise reach a paid run and come back unresolved for a reason
        # that says nothing about the agent. A key that is missing,
        # unparseable or malformed is refused by `points_key()` right here.
        points = points_key(task)
        if not points.points:
            raise IngestError(
                f"{task.id}: {GRADING_DIR}/{POINTS_KEY_FILE} plants no points "
                "— the verdict is every planted point covered, so a key with "
                "none resolves every answer that is not empty, whatever it "
                "says"
            )
    elif not task.grading_test_paths:
        # Read per runner glob *plus* the canonical harness-side checks, which
        # is what `grading_test_paths` collects: the task's own held-out tests
        # are found by its language runner's glob, and the answer-key test, the
        # findings-key test and the hash gate by pytest's, whatever the task
        # declares. So a typescript task holding only `.test.ts` files, or
        # holding only its key's canonical Python test, has a suite — and one
        # spelling is named here per glob rather than twice, because a python
        # task's two halves are the same files.
        globs = " and no ".join(
            dict.fromkeys((task.runner.grading_test_glob, PYTHON.grading_test_glob))
        )
        raise IngestError(
            f"{task.id}: {GRADING_DIR}/ holds no {globs} — a v1 task is graded by "
            "running held-out tests, and neither half of the suite is there"
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
    if is_keyed(task) and task.category not in _KEYED_CATEGORIES:
        raise IngestError(
            f"{task.id}: a {task.category} task ships {GRADING_DIR}/"
            f"{ANSWER_KEY_FILE} — the accepted-answer key is the ground truth "
            "of the two actions whose deliverable is an answer file rather "
            f"than a code change ({', '.join(sorted(_KEYED_CATEGORIES))}), and "
            "every rule that reads it is gated on the key being there, so a "
            "key shipped by any other action would hold this task to the "
            "terrain rules and the hash gate while its own grading never "
            "consulted the key at all"
        )
    if is_keyed(task) or task.category == _KEY_REQUIRED_CATEGORY:
        # The ground truth of a task whose deliverable is prose: where a
        # fault-location task's defect lives, or where a locate-style
        # codebase-comprehension task's asked-about behaviour lives. Read here
        # so that a key which is missing, unparseable, or written in line
        # numbers fails at load rather than at the first paid run — and read
        # off the key on disk, plus the one action whose key is mandatory, so
        # that a `fault-location` task shipping none is refused by
        # `answer_key()` right here while a `codebase-comprehension` task
        # shipping none is simply not the locate-style form. The empty-
        # accepted-set check is read here too, and not left to the lint alone:
        # `ai-bench run-live` loads a task set but never lints it, so an
        # unsolvable key would otherwise reach a paid run.
        key = answer_key(task)
        if not key.accepted:
            raise IngestError(_empty_accepted_set_message(task))
    if is_findings_keyed(task) and task.category != _FINDINGS_CATEGORY:
        raise IngestError(
            f"{task.id}: a {task.category} task ships {GRADING_DIR}/"
            f"{FINDINGS_KEY_FILE} — the findings key is the ground truth of "
            f"{_FINDINGS_CATEGORY}, the one action that judges a whole change "
            "rather than naming one location, and every rule that reads it is "
            "gated on the key being there, so a key shipped by any other "
            "action would hold this task to the review rules while its own "
            "grading never consulted the key at all"
        )
    if is_findings_keyed(task) or task.category == _FINDINGS_CATEGORY:
        # The ground truth of a review: which of the change under review is
        # wrong. Read here, and not left to the lint alone, for the reason the
        # accepted-answer key is read here — `ai-bench run-live` loads a task
        # set but never lints it, so a key that is missing, unparseable, or
        # written in line numbers would otherwise reach a paid run. Read off
        # the key on disk *or* the category, so that a review task shipping no
        # key is refused by `findings_key()` right here rather than swept as a
        # task with no ground truth.
        findings = findings_key(task)
        if not findings.accepted:
            raise IngestError(_empty_accepted_findings_message(task))


def _check_mutation_gate_layout(task: Task) -> None:
    """What a `test-authoring` task has to have on disk before the mutation
    gate can grade it: a subtree to collect, mutants to plant, a proof that
    they are killable, and no second ground truth.

    The four are the gate's own preconditions rather than authoring taste. A
    task with no declared test path has no deliverable grading could find; one
    with no mutants has a gate 2 that quantifies over nothing and would resolve
    every suite that compiles; one with no proofs has nothing saying its
    mutants are killable at all; and one shipping a grading directory has a
    second ground truth that nothing in this verdict shape ever runs.
    """
    if task.test_path is None:
        raise IngestError(
            f"{task.id}: a {_MUTATION_CATEGORY} task declares no test_path — "
            "the mutation gate collects the prompt-named test subtree out of "
            "the workdir diff and grades that alone, so a task that never says "
            "which subtree that is has no deliverable for the gate to find"
        )
    if _escapes_workdir(task.test_path):
        raise IngestError(
            f"{task.id}: test_path {task.test_path!r} climbs out of the workdir "
            "— the test path is where the agent is told to write, and a run's "
            "diff only ever carries what was written inside the workdir, so no "
            "suite could ever land there and the gate would collect nothing"
        )
    if not is_mutation_keyed(task):
        raise IngestError(
            f"{task.id}: a {_MUTATION_CATEGORY} task ships no {MUTANTS_DIR}/ — "
            "the planted mutants are this action's ground truth and the whole "
            "of its second gate, so a task with none asks nothing of the suite "
            "it grades beyond passing on code that already works"
        )
    if not task.proofs_dir.is_dir() or not any(task.proofs_dir.iterdir()):
        raise IngestError(
            f"{task.id}: a {_MUTATION_CATEGORY} task ships no {PROOFS_DIR}/ — "
            "the author's own reference suite is this action's registered "
            "existence proof, and without it nothing says the planted mutants "
            "are killable, so a mutant no test can kill would make the task "
            "unresolvable for every agent and look like a hard task"
        )
    if task.grading_dir.exists():
        raise IngestError(
            f"{task.id}: a {_MUTATION_CATEGORY} task ships {GRADING_DIR}/ — its "
            "verdict is the mutation gate, which runs the agent's own collected "
            "suite against the starting repository and against each mutant and "
            "never overlays a held-out test at all, so a grading directory here "
            "is a second ground truth that nothing would ever run. The author's "
            f"reference suite belongs in {PROOFS_DIR}/, where every other "
            "action's existence proof lives"
        )


def _held_out_of_the_workdir_but_not_of_grading(task: Task) -> list[str]:
    """Corrected trees, proof subtrees and mutant sets found inside the grading
    directory.

    The three are the parts of a task that are held out of the *workdir* as
    well as of the agent: grading copies the grading directory over the workdir
    wholesale, so a corrected tree or a mutant there lands in the graded workdir
    and a proof test there is collected as a verdict test. Read at any depth,
    because a nested `grading/extras/corrected/` is overlaid exactly as a
    top-level one is.
    """
    if not task.grading_dir.is_dir():
        return []
    return sorted(
        str(path.relative_to(task.grading_dir)) + "/"
        for path in task.grading_dir.rglob("*")
        if path.is_dir() and path.name in (CORRECTED_DIR, PROOFS_DIR, MUTANTS_DIR)
    )


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


def grade(
    task: Task,
    diff: str,
    *,
    timeout_s: int = GRADE_TIMEOUT_S,
    rulings_path: Path | None = None,
    grader_factory: Callable[[], point_grader.PointGrader] | None = None,
) -> bool:
    """Whether the run that produced this diff resolved the task.

    The whole grading suite runs against a fresh copy of the pristine repo
    with the diff applied and the canonical grading files laid over the top.
    Resolved means every grading test ran and passed, as far as a grader that
    shares a process tree with the code it is grading can tell: a failure, a
    collection error, a skip, a run that ended early and a timeout all mean
    unresolved, but a deliberately adversarial diff can still forge a pass
    from inside that process (see the module docstring). A diff git cannot
    apply is not a verdict at all — it is a broken run log, and fails loudly.
    A task's verdict is *every half present passes*: the harness-side pytest
    checks and the task's own held-out tests are both grading tests, run by the
    runner each belongs to, and a task resolves only if every half it has
    passes and at least one test ran overall. For a Python task the two halves
    are the same files under the same runner, and there is only ever one.

    Two actions are graded by a different shape entirely, and both dispatches
    are here so that nothing above this line has to know: a task shipping
    planted mutants is graded by the mutation gate, which collects the agent's
    own test subtree out of the diff and runs it against the starting
    repository and against each mutant; a task shipping a points key is graded
    by the point gate, which collects one prose file out of the diff and
    computes a verdict from a grader's per-point rulings. `evaluate` and the
    replay path call this function and are unchanged by either — a verdict is
    still one boolean.

    The last two arguments belong to the point gate and to nothing else, which
    is why they default to nothing: `rulings_path` is where this run row's
    rulings are archived and read back from, and `grader_factory` is the seam
    that decides live from replay — passed on `--live`, absent on `--replay`,
    called only where a ruling is missing. Every other shape ignores both, and
    a caller grading a task of any other action never has to know they exist.
    """
    if is_mutation_keyed(task):
        return _mutation_gate(task, diff, timeout_s=timeout_s)
    if is_point_keyed(task):
        return _point_gate(
            task, diff, rulings_path=rulings_path, grader_factory=grader_factory
        )
    return _run_halves(task, diff, task.grading_halves, timeout_s=timeout_s)


def _run_grading(
    task: Task, diff: str, targets: Sequence[str], *, timeout_s: int
) -> bool:
    """One named slice of a task's grading suite, run by the task's own runner.

    What a caller reaches for when the question is about *part* of the suite —
    the behaviour half of a refactor task, an existence proof's own test — and
    never what `grade` uses, because a verdict is every half of the whole.
    """
    return _run_halves(task, diff, ((task.runner, tuple(targets)),), timeout_s=timeout_s)


def _run_halves(
    task: Task,
    diff: str,
    halves: Sequence[tuple[LanguageRunner, Sequence[str]]],
    *,
    timeout_s: int,
) -> bool:
    """Build the throwaway tree a verdict is read from, and hand each half of
    the suite to the runner that runs it.

    The division is the seam's: everything here — the root, the workdir
    beneath it, the copy of `repo/`, the applied diff, the overlay of
    `grading/` last, the timeout — is the grader's and is the same whatever
    grades the tests. How those tests are invoked and how their verdict is
    read back is the runner's, and is reached through the task's declaration
    rather than by name.

    A suite with no halves at all is unresolved rather than vacuously true:
    nothing ran, so nothing was verified.
    """
    if not halves:
        return False
    # Before the tree is built and before anything runs: a verdict must never
    # be a toolchain artefact, and a task graded by two runners needs both.
    for runner, _ in halves:
        runner.require_toolchain()
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
        return all(
            runner.run_tests(root, workdir, targets, timeout_s=timeout_s)
            for runner, targets in halves
        )


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


# --- the mutation gate: a `test-authoring` task's two-gate verdict --------------


def _mutation_gate(task: Task, diff: str, *, timeout_s: int) -> bool:
    """Whether the suite this run wrote passes on the starting repository and
    kills every planted mutant.

    Two gates, both run over trees this function builds for itself and neither
    over the workdir the agent worked in. Gate 1 is the collected suite against
    a fresh copy of `repo/`: a suite that accuses correct code of a fault is
    unresolved here, with no exception (design note §67.3). Gate 2 is the same
    collected suite against each mutant in turn — a fresh copy of `repo/` with
    one planted patch applied — and a mutant is killed when the runner's
    verdict on it is False, which is to say at least one test failed. Resolved
    is gate 1 and every mutant killed, binary: what fraction of the mutants a
    suite kills is not a score and is not reported anywhere (§67.3 again — a
    kill rate would be a second quality metric wearing `resolved`'s name).

    Mutants run in `mutant_patches()` order and the gate stops at the first
    survivor, which costs nothing a reader needs: the order is sorted and the
    trees are built the same way every time, so running this again on the same
    task and the same diff fails at the same mutant.
    """
    if task.test_path is None:
        # Unreachable through the loader, which refuses a mutation-keyed task
        # declaring no test path. Said out loud anyway rather than asserted
        # away, because a gate that collected "the whole workdir" instead is
        # precisely the hole §67.4 exists to close.
        raise IngestError(
            f"{task.id}: the mutation gate has no test_path to collect — the "
            "task ships planted mutants and never says which subtree of the "
            "workdir diff is the deliverable"
        )
    task.runner.require_toolchain()
    with tempfile.TemporaryDirectory(prefix="ai-bench-mutate-") as name:
        root = Path(name)
        # Gate 1. Anything but a pass — a failure, a collection error, a
        # timeout, or nothing collected at all — is unresolved.
        if _collected_suite_verdict(
            task, diff, root / "pristine", None,
            test_path=task.test_path, timeout_s=timeout_s,
        ) is not True:
            return False
        # Gate 2. Killed is the runner saying False on that mutant; a suite
        # that passes has let the mutation through, and a suite that collected
        # nothing there has killed nothing either.
        for index, patch in enumerate(mutant_patches(task)):
            verdict = _collected_suite_verdict(
                task, diff, root / f"mutant-{index}", patch,
                test_path=task.test_path, timeout_s=timeout_s,
            )
            if verdict is not False:
                return False
    return True


def _collected_suite_verdict(
    task: Task,
    diff: str,
    root: Path,
    mutant: Path | None,
    *,
    test_path: str,
    timeout_s: int,
) -> bool | None:
    """Run the collected suite over one copy of the starting repository —
    pristine, or carrying one planted mutant — and say what it did.

    True where every collected test passed, False where the run said anything
    else, and None where *no test file was collected at all*. The third answer
    is not the second: nothing ran, so nothing was verified, and both gates
    read it that way rather than as a pass (the "no halves" sentence of
    `_run_halves`, one level down).

    The tree is built the way `_run_halves` builds its own and for the same
    reasons — a throwaway root with the workdir beneath it, so that the pinned
    config, the plugin and the report all sit somewhere the applied diff cannot
    write — with the one difference this action is: nothing is overlaid over
    the workdir afterwards, because the tests being run are the agent's.
    """
    workdir = root / "workdir"
    workdir.mkdir(parents=True)
    shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
    # A repository of its own, so neither patch below can resolve its paths
    # against a checkout this temp dir happens to sit inside — `_apply_diff`'s
    # reason, and it holds for a mutant exactly as it does for a logged diff.
    _git(task, ["init", "-q", "."], workdir, doing="preparing a graded copy")
    if mutant is not None:
        _apply_mutant(task, mutant, workdir)
    _collect_the_test_subtree(task, diff, workdir, test_path)
    targets = sorted(
        str(path.relative_to(workdir))
        for path in (workdir / test_path).rglob(task.runner.grading_test_glob)
    )
    if not targets:
        return None
    return task.runner.run_tests(root, workdir, targets, timeout_s=timeout_s)


def _apply_mutant(task: Task, mutant: Path, workdir: Path) -> None:
    """Plant one mutant in a copy of the starting repository.

    A patch git cannot apply fails loudly, the way a logged diff git cannot
    apply does: the run log is not the only artefact that can be broken, and a
    mutant that quietly did not land is a gate 2 that quantifies over one
    fewer behaviour change than the task claims — which is the failure mode
    this verdict shape has no other guard against.
    """
    try:
        patch = mutant.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise IngestError(
            f"{task.id}: cannot read planted mutant {mutant.name}: {error}"
        ) from error
    _git(
        task,
        ["apply", "--whitespace=nowarn"],
        workdir,
        stdin=patch,
        doing=f"on planted mutant {mutant.name}",
    )


def _collect_the_test_subtree(
    task: Task, diff: str, workdir: Path, test_path: str
) -> None:
    """Apply the hunks of this run's diff that land under the declared test
    path, and no others.

    The collection rule of design note §67.4, and the whole of what keeps the
    two gates honest: applied whole, a diff's source edits could bend the code
    under test toward a wrong suite (gate 1 dies) or overwrite a planted
    mutation (gate 2 dies). Everything outside the subtree is archived by the
    run log and scored by nothing.

    Ridden on `git apply --include` rather than on a diff parser written here:
    which hunks belong to a path is git's own question, and a hand-rolled
    splitter would be a second, weaker implementation of it. The pattern is
    `<test_path>/*` and it covers every depth — git matches these patterns
    without a path-separator rule, so one `*` spans `tests/test_a.py` and
    `tests/deep/test_b.py` alike (checked against a real `git apply`, not
    remembered). A diff whose hunks all fall outside the subtree applies
    nothing and exits 0, which is the answer this wants: nothing collected,
    and gate 1 reads that as nothing verified.
    """
    if not diff.strip():
        return
    _git(
        task,
        ["apply", "--whitespace=nowarn", f"--include={test_path.rstrip('/')}/*"],
        workdir,
        stdin=diff,
        doing="collecting the test subtree from the logged diff",
    )


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


# --- the point gate: an `investigation` task's computed verdict ----------------


# Which half of the key a ruling answers. Carried on the archived ruling rather
# than inferred from the key at read time, so that an archive stays readable
# against a key whose halves were later re-cut, and so that a question moved
# from one half to the other is a ruling the archive no longer answers rather
# than one silently re-read under the opposite polarity.
PointKind = Literal["point", "disqualifier"]


class PointRuling(BaseModel):
    """One archived ruling: what the grader said about one planted point or one
    disqualifier, and what the gate made of the span it quoted.

    `covered` and `span` are the grader's, verbatim; `verified` is the gate's —
    whether that span was really in the collected deliverable. The two are
    archived apart rather than folded together because a **demotion** (a
    covered ruling quoting a span the deliverable does not contain) is a fact
    about the instrument worth reading back off the archive rather than losing.
    Nothing downstream trusts `verified`: a replay re-verifies every span
    against the deliverable it collected for itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    point_id: NonEmptyStr
    kind: PointKind
    covered: bool
    span: str | None
    verified: bool


class RunRulings(BaseModel):
    """Every ruling of one run row, as the archive holds it.

    The grader version and the deliverable's hash are here rather than per
    ruling because they are properties of the grading, not of one question: a
    row is graded by one instrument over one collected file, and rulings taken
    under a second instrument or against a second deliverable are a different
    archive. The hash is what makes a replay honest — rulings archived for some
    other run's answer are refused rather than recomputed over this one's.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    grader_version: NonEmptyStr
    deliverable_sha256: NonEmptyStr
    rulings: tuple[PointRuling, ...]


class ProofRulings(BaseModel):
    """One half of a point-keyed task's two-sided existence proof, as the
    archive holds it: what the grader said about the author's own answer, and
    the three facts that say what it was said about.

    The rulings are `RunRulings`' own shape, because a proof is the very
    computation a run is graded by pointed at the author instead of at an agent
    — one call per question, a span the gate checked, a verdict computed from
    the archive. What it carries beside them is where the two archives differ.
    A run's rulings are keyed to the deliverable a run's diff happened to
    collect, and go stale when nothing but that run could make them so; a
    proof's are the *authoring* artefact the lint holds a task to before any
    agent meets it, and go stale the moment the author edits either input or
    the instrument is re-versioned.

    So this records all three: the grader version, the answer these rulings
    were taken against, and the key they answer. **That is the whole mechanism
    behind "re-proof triggers on edit, not on every lint run"** (§76.10) — the
    lint recomputes the three hashes from what is on disk and refuses until the
    proof is re-run, and on an unedited task it is a hash comparison and no
    call at all.

    The key is hashed over its canonical JSON rather than its file bytes
    (`points_key_sha256`), so re-indenting the key costs nothing while any
    change to what it asks costs a re-proof.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    grader_version: NonEmptyStr
    points_key_sha256: NonEmptyStr
    answer_sha256: NonEmptyStr
    rulings: tuple[PointRuling, ...]


def rulings_file(rulings: Path, task_id: str, agent: str, model: str) -> Path:
    """Where one run row's rulings are archived: one file per task x agent x
    model.

    That triple is the key `evaluate` already treats as unique — it refuses two
    runs of one cell outright, because their verdicts would have to be silently
    picked between — so an archive keyed by it holds exactly one row's rulings
    and a second run of the same cell cannot quietly overwrite a first's
    without `evaluate` having refused the log first.
    """
    return rulings / f"{task_id}__{agent}__{model}.json"


def _point_gate(
    task: Task,
    diff: str,
    *,
    rulings_path: Path | None,
    grader_factory: Callable[[], point_grader.PointGrader] | None,
) -> bool:
    """Whether the prose this run wrote covers every planted point and makes no
    disqualifying claim.

    One file is collected out of the workdir diff — the prompt-named answer
    file and nothing else (§67.4's rule narrowed to a single path) — and one
    call goes to the grader per planted point and per disqualifier. `resolved`
    is every point covered and no disqualifier present, binary: what fraction
    of the points an answer covered is not computed here, not stored in the
    archive and not reported anywhere, because a coverage rate under the name
    `resolved` would be a second quality metric on one action of a corpus whose
    values are only comparable within one (§67.3, pointed at points).

    Coverage is not the grader's word alone. A ruling counts only if it quotes
    a span the collected deliverable really contains, checked here by
    `point_grader.span_in_deliverable`; a covered ruling whose span is absent
    or unquotable is demoted mechanically, and the demotion is archived. That
    check is the gate's rather than the instrument's on purpose — an instrument
    that graded its own quotations would be the only thing standing behind
    them.

    **An absent, empty or whitespace-only answer file is unresolved with zero
    grader calls and nothing written.** That is a property the whole lint
    depends on and not an optimisation: `lint_task_set` grades every task
    pristine (`grade(task, "")`) to check that doing nothing does not resolve
    it, and on a point-keyed task that call has to stay offline and free.

    Live and replay are the same computation and differ only in where the
    rulings come from. The factory is called on the first missing ruling and
    never otherwise, so a sweep holding no point-keyed task and every replay of
    one stay keyless; with no factory — which is what `--replay` passes — a row
    with no usable archive is refused loudly rather than silently re-graded.
    """
    key = points_key(task)
    deliverable = _collect_the_answer_file(task, diff, key.answer_path)
    if not deliverable.strip():
        return False
    questions = _point_questions(key)
    if rulings_path is None:
        # Unreachable from `evaluate`, which always names a file, and from the
        # lint, whose pristine call returns above. Said out loud rather than
        # asserted away: a gate that graded without archiving would produce a
        # verdict nothing could recompute.
        raise IngestError(
            f"{task.id}: the point gate was given no rulings archive to read "
            "or write — a point-keyed verdict is recomputed from its rulings, "
            "so a run graded without one could never be replayed"
        )
    archive, unusable = _archived_rulings(task, rulings_path, deliverable, questions)
    if archive is None:
        if grader_factory is None:
            raise IngestError(
                f"{task.id}: {unusable} ({rulings_path}) — a replay recomputes "
                "a point-keyed verdict from the archived rulings and never "
                "re-grades one, because a second grading is a second "
                "measurement of a cell that has already been measured. Grade "
                "this row once with a grader and commit the archive"
            )
        archive = _fresh_rulings(task, deliverable, questions, grader_factory())
        _write_rulings(task, rulings_path, archive)
    return _point_verdict(questions, archive, deliverable)


def _point_questions(key: PointsKey) -> tuple[tuple[PointKind, PlantedPoint], ...]:
    """Every question this key asks of an answer, each tagged with the half it
    came from: the planted points first, then the disqualifiers.

    One sequence rather than two loops, because everything downstream — the
    calls, the archive, the completeness check on a replayed archive and the
    verdict — walks the same questions in the same order, and the only thing
    that differs between the halves is what a covered ruling means.
    """
    return tuple(
        [("point", planted) for planted in key.points]
        + [("disqualifier", planted) for planted in key.disqualifiers]
    )


def _collect_the_answer_file(task: Task, diff: str, answer_path: str) -> str:
    """Apply the hunks of this run's diff that land on the prompt-named answer
    file, and no others; return what that file then holds.

    The mutation gate's collection rule (§67.4) narrowed from a subtree to a
    single path, and ridden on `git apply --include` for the same reason: which
    hunks belong to a path is git's own question. Everything else in the diff —
    scratch notes, source explorations, a repository the agent rearranged while
    reading it — is archived by the run log and scored by nothing.

    The empty string is returned where the diff wrote no answer file at all,
    where its hunks all fall outside the path (`git apply` applies nothing and
    exits 0, which is the answer this wants), and where what landed there is
    not readable UTF-8 text. All three are the same thing to the gate: no prose
    to grade, and unresolved without a grader call.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-points-") as name:
        workdir = Path(name) / "workdir"
        workdir.mkdir(parents=True)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        # A repository of its own, so the patch below cannot resolve its paths
        # against a checkout this temp dir happens to sit inside —
        # `_apply_diff`'s reason, unchanged by collecting one path instead of
        # a whole diff.
        _git(task, ["init", "-q", "."], workdir, doing="preparing a graded copy")
        if diff.strip():
            _git(
                task,
                ["apply", "--whitespace=nowarn", f"--include={answer_path}"],
                workdir,
                stdin=diff,
                doing="collecting the answer file from the logged diff",
            )
        collected = workdir / answer_path
        if not collected.is_file():
            return ""
        try:
            return collected.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""


def _sha256(deliverable: str) -> str:
    """The collected deliverable's hash, as the archive records it."""
    return hashlib.sha256(deliverable.encode("utf-8")).hexdigest()


def _the_span_holds(covered: bool, span: str | None, deliverable: str) -> bool:
    """Whether a ruling of covered survives the gate's own check on its span.

    §76.6: no quotable span, no coverage. A ruling that says covered and quotes
    nothing, or quotes something the deliverable does not contain under the
    instrument's normalisation, is not a covered ruling — and the demotion is
    mechanical here rather than an appeal back to the grader, which would be
    the instrument marking its own quotations.
    """
    return (
        covered
        and span is not None
        and point_grader.span_in_deliverable(span, deliverable)
    )


def _fresh_rulings(
    task: Task,
    deliverable: str,
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
    grader: point_grader.PointGrader,
) -> RunRulings:
    """One call per question, in key order, archived with what the gate made of
    each span.

    One grader version over the whole row, because a row graded half under one
    instrument and half under another is a verdict no version could stand
    behind. A grader answering about a question other than the one it was asked
    is refused rather than archived under the id it was meant to answer.
    """
    entries: list[PointRuling] = []
    versions: set[str] = set()
    for kind, planted in questions:
        ruling = grader(deliverable, {"id": planted.id, "text": planted.text})
        if ruling.point_id != planted.id:
            raise IngestError(
                f"{task.id}: the grader was asked about {planted.id!r} and "
                f"ruled on {ruling.point_id!r} — a ruling archived under the "
                "wrong question answers for a point nobody asked about"
            )
        versions.add(ruling.grader_version)
        entries.append(
            PointRuling(
                point_id=planted.id,
                kind=kind,
                covered=ruling.covered,
                span=ruling.span,
                verified=_the_span_holds(ruling.covered, ruling.span, deliverable),
            )
        )
    if len(versions) != 1:
        raise IngestError(
            f"{task.id}: this row was graded under {sorted(versions)} — one "
            "row is one measurement and carries one grader version, so an "
            "archive spanning two of them says nothing about either"
        )
    return RunRulings(
        grader_version=versions.pop(),
        deliverable_sha256=_sha256(deliverable),
        rulings=tuple(entries),
    )


def _archived_rulings(
    task: Task,
    path: Path,
    deliverable: str,
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
) -> tuple[RunRulings | None, str]:
    """This row's archived rulings, or None and why they cannot be used.

    Three things make an archive usable: it is there, it was taken against the
    very deliverable this run collected (by hash), and it answers exactly the
    questions this key asks. Anything else is not a stale detail to work
    around — it is rulings about some other measurement — so the caller either
    grades the row afresh (live) or refuses it (replay), and never mixes the
    two. An archive that is there but unreadable, not JSON, or not this shape
    is a broken artefact rather than a missing one, and fails loudly in both
    modes: silently re-grading over it would overwrite the very file whose
    breakage wants looking at.
    """
    if not path.is_file():
        return None, "no rulings are archived for this run"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise IngestError(
            f"{task.id}: the archived rulings at {path} are unreadable ({error})"
        ) from error
    except json.JSONDecodeError as error:
        raise IngestError(
            f"{task.id}: the archived rulings at {path} are not JSON ({error})"
        ) from error
    try:
        archive = RunRulings.model_validate(raw)
    except ValidationError as error:
        raise IngestError(f"{task.id}: the archived rulings at {path}: {error}") from error
    if archive.deliverable_sha256 != _sha256(deliverable):
        return None, (
            "the archived rulings were taken against a different deliverable "
            "than this run's diff collected"
        )
    asked = {(kind, planted.id) for kind, planted in questions}
    ruled = {(entry.kind, entry.point_id) for entry in archive.rulings}
    if asked != ruled:
        return None, (
            "the archived rulings do not answer this task's planted points "
            "and disqualifiers"
        )
    return archive, ""


def _point_verdict(
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
    archive: RunRulings | ProofRulings,
    deliverable: str,
) -> bool:
    """Every planted point covered by a verified ruling, and no disqualifier
    present — computed from the archive, live and replay alike.

    Every span is re-verified here rather than read off `verified`, so that a
    replay is a recomputation and not a reprint: the archive says what the
    grader said, and what that is worth against this deliverable is decided
    again every time the verdict is.

    One function over both archives, which is the whole point of the lint's
    existence-proof form taking this one: what the author's reference answer is
    proved to do is exactly what an agent's answer will be graded by, rather
    than a restatement of it that could drift.
    """
    by_question = {(entry.kind, entry.point_id): entry for entry in archive.rulings}
    for kind, planted in questions:
        entry = by_question[(kind, planted.id)]
        covered = _the_span_holds(entry.covered, entry.span, deliverable)
        if kind == "point" and not covered:
            return False
        if kind == "disqualifier" and covered:
            return False
    return True


def _write_rulings(task: Task, path: Path, archive: RunRulings | ProofRulings) -> None:
    """Archive these rulings, so that every later reading of the verdict — a
    run's, or a proof's — is a recomputation over them rather than a second
    paid grading.

    One writer for both archives: what is written is the same JSON of the same
    per-point rulings, and two writers would be two places for the indentation,
    the encoding and the failure message to drift.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(archive.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise IngestError(
            f"{task.id}: cannot write the rulings archive at {path}: {error}"
        ) from error


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

    A task carrying an accepted-answer key — a fault-location task, or the
    locate-style form of a codebase-comprehension one (`_KEYED_CATEGORIES`) —
    is run against more than the pristine repository, because for those
    actions the pristine run proves nothing: see `_discrimination_problems`.
    Every gate here reads the key on disk (`is_keyed`) rather than the
    category, so the second action inherited all of it unchanged.

    A `code-review` task is run against more than the pristine repository too,
    and for the same reason: its findings key is read by
    `_findings_key_problems` and then put to the negatives of
    `_findings_discrimination_problems`, two of which — every planted finding
    but one, and every planted finding plus a rejected one — are what make the
    two quantifiers of a set-shaped verdict real rather than declared, plus the
    one positive that makes a **planted finding**'s alternatives real: reporting
    a finding at any of them has to grade resolved.

    A `test-authoring` task carries a third shape of key — its planted mutants
    — and is held to what that set has to be (`_mutant_set_problems`): at least
    three mutants, every one of them patching a file of `repo/` and none of them
    reaching into the declared test path, a starting repository with no tests
    already sitting at that path, and a prompt that names it. All four are read
    rather than run, and all four gate the expensive proof below.

    An `investigation` task carries the fourth shape — its **planted points** —
    and is held to what that key has to be (`_points_key_problems`): at least
    three points, an id and a question in each, no id used twice, a prompt that
    names the answer path, and neither the key nor either proof answer shipped
    inside `repo/`. All of it is read rather than run, and all of it gates that
    action's proof below.

    A task carrying a key of any of the four shapes is also held to its
    action's registered **existence proof** (`EXISTENCE_PROOFS`), which asks the
    prior question none of the negatives can: whether the truth the task is
    keyed on is in the repository at all. The five forms are a partner
    `bug-fix` task's pristine failure, a held-out test per planted finding run
    against two trees, an accepted location that resolves, a reference suite
    that passes pristine and dies on each planted mutant in turn, and — the one
    form that runs nothing and asks nothing — the archived rulings saying the
    author's reference answer resolves under the point gate and their foil
    answer does not. An action carrying a key with no registered form is
    refused rather than exempt.

    **Nothing here calls an LLM.** The point-keyed form is checked by reading
    the rulings `ai-bench prove-points-v1` archived at authoring time, and the
    pristine grade of a point-keyed task collects an empty answer file and
    returns unresolved without a grader call. That is a property of this whole
    command and not of its default flags, which is why the one affordance that
    does call the grader is a subcommand beside it rather than a flag in it.

    It is held to the three terrain rules as well
    (`_terrain_problems`): whether it gives its own answer away is an
    authoring invariant like any other, and one that used to be proved per
    task, in six copies, so that a seventh keyed task inherited none of it.
    The hash gate (`_hash_gate_problems`) is here for the same reason and was
    moved here from the same place: a keyed task asks for a location and not a
    repair, and it used to be four tasks' own suites that said so. Four actions
    are exempt from the terrain rules at the action level and with their reason
    recorded (`TERRAIN_EXEMPT_ACTIONS`) rather than exempt by the accident of
    having no greppable key — one of the four by key shape rather than
    wholesale, because `codebase-comprehension`'s locate-style tasks key
    exactly the greppable locations those rules exist for.

    The construction invariants are read rather than run, but belong here for
    the same reason: an undeclared knob, an unregistered prediction, a family
    whose variants differ in more than the knob they vary, or an effort claim
    naming a comparator the task set does not hold costs nothing to catch now
    and cannot be repaired afterwards — a prediction registered once the
    outcome is known is not a prediction, and a sweep is only paid for once.
    """
    problems = (
        _unregistered_proof_form_problems()
        + _family_problems(tasks)
        + _effort_claim_problems(tasks)
        + _pair_problems(tasks)
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
        # The findings key's own read rules and its canonical held-out test,
        # gated and independent exactly as the two above are and for the same
        # reasons: a review task's key is read here, and the byte comparison
        # over its grading test says nothing about whether the key is sound.
        findings_problems = _findings_key_problems(task)
        problems.extend(findings_problems)
        problems.extend(_findings_test_problems(task))
        # Independent of both keys' problems, and read rather than run: the
        # three terrain rules are about the prompt and the repository the agent
        # is handed, which are as readable when the key names a file that is
        # not there as when it does not.
        problems.extend(_terrain_problems(task))
        # Independent for the same reason, and unrunnable by construction: the
        # gate hashes the pristine repository, so running the grading tests on
        # that repository is the one thing that can never fail it.
        problems.extend(_hash_gate_problems(task))
        # What the stdlib-only rule and the shape of Node's module resolution
        # refuse about a typescript task's files. Empty for every other
        # language, read rather than run, and independent of every gate above:
        # a task shipping a dependency it cannot have is as readable when its
        # key is unreadable as when it is not.
        problems.extend(_typescript_problems(task))
        # What a planted mutant set and the terrain around it have to be, read
        # rather than run, and independent of everything above: a task shipping
        # mutants carries neither key the gates above read.
        mutant_problems = _mutant_set_problems(task) if is_mutation_keyed(task) else []
        problems.extend(mutant_problems)
        # What a points key and the terrain around it have to be, read rather
        # than run, gating this action's proof the way the mutant rules gate
        # theirs — and independent of everything above, because a task shipping
        # planted points carries none of the other three keys.
        points_problems = _points_key_problems(task)
        problems.extend(points_problems)
        if is_keyed(task) and not key_problems:
            # Only once the key reads clean: the negatives are graded through
            # the real pipeline, which is the expensive half of this lint, and
            # a key that names a file the repository does not hold has nothing
            # to say about whether the grading test discriminates.
            problems.extend(_discrimination_problems(task, timeout_s=timeout_s))
        if is_findings_keyed(task) and not findings_problems:
            # The same gate over the set-shaped key, and gated for the same
            # reason: a dozen answers graded through the real pipeline is the
            # expensive half of linting a review task, and a key whose findings
            # do not describe the change under review has nothing to say about
            # whether its held-out test discriminates.
            problems.extend(
                _findings_discrimination_problems(task, timeout_s=timeout_s)
            )
        if (
            is_keyed(task)
            or is_findings_keyed(task)
            or is_mutation_keyed(task)
            or is_point_keyed(task)
        ) and not (
            key_problems or findings_problems or mutant_problems or points_problems
        ):
            # The prior question the negatives above cannot ask: whether the
            # truth this task is keyed on is in the repository at all. Gated on
            # whichever key this task carries reading clean, for the reason the
            # negatives are — a key naming a file the repository does not hold
            # says nothing about whether a defect exists at that location, and
            # the review form runs tests against two trees, which is expensive.
            # The mutation form is gated on the cheap mutant-set rules above for
            # that same reason and more so: it runs a whole suite once per
            # mutant, and a mutant patching a file that is not there has nothing
            # to say about whether the behaviour change it claims is killable.
            problems.extend(
                _existence_proof_problems(task, tasks, timeout_s=timeout_s)
            )
        # The whole suite, every half of it, exactly as a run is graded.
        if grade(task, "", timeout_s=timeout_s):
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


def coverage_table(tasks: list[Task]) -> list[tuple[str, str, str, int]]:
    """Task counts over `category x surface x language`, for `ai-bench
    lint-v1` to print. Reports only — nothing here gates the lint.

    Every `TaskCategory` appears at least once, so a category with no task in
    any language reads as a `- - 0` row rather than as an omission — which is
    the whole of what a zero can be said here, a populated category's missing
    *language* being disclosed by the absence of its row and by the round that
    left it empty. `test-authoring` was the registered-empty cell (design note
    45.12) until round 8 filled its Python cell; `investigation` read zero
    until round 10 filled its Python cell; `requirement-decomposition` read
    zero until round 11 filled its Python cell; `performance-optimisation` is
    one of the categories reading zero today. `scale` and substrate are
    disclosed on a task but not gridded here (design note 45.10).
    """
    # There is no undeclared-language column: the loader now refuses a task
    # that declares none, so no input reaches this grid without a language.
    counts: Counter[tuple[str, str, str]] = Counter(
        (task.category, task.surface, task.language) for task in tasks
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
    """What is wrong with a keyed task's accepted-answer key.

    Gated on the key being on disk rather than on the category, so it reads a
    locate-style `codebase-comprehension` key by exactly these rules and not a
    softened set of them (`_KEYED_CATEGORIES` says what the two actions do and
    do not share). A `fault-location` task shipping no key never reaches here:
    the loader refuses it.

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
    if not is_keyed(task):
        return []
    key = answer_key(task)
    problems = []
    if not key.accepted:
        problems.append(_empty_accepted_set_message(task))
    if not key.rejected:
        problems.append(
            f"{task.id}: the accepted-answer key declares no rejected answers — "
            "must-fail-on-pristine proves nothing about a keyed task, because "
            "a pristine repository carries no answer file at all, so "
            "the near-miss the lint cannot invent is what stands between this "
            "task and a grading test that would resolve anything: name the "
            "plausible wrong file — the caller of the defective function or "
            "the module that looks responsible where a defect is what is being "
            "located, the module holding a related but different behaviour "
            "where the question is where a behaviour is handled"
        )
    else:
        # `rejected` being non-empty is not the same as it saying anything:
        # §36.3 names the one negative the lint cannot invent as the
        # plausible wrong *file*, so a rejected set confined to files the
        # accepted set already names never supplies it, however many entries
        # it carries. That holds for a comprehension key as written: only the
        # meaning of "plausible wrong file" shifts, from the module the
        # symptom points at to the module a related but different behaviour
        # lives in. And a rejected answer that happens to equal the
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
                "function, the module that looks responsible, or the module "
                "a related but different behaviour lives in), and a "
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
    problems.extend(
        _answer_path_problems(
            task,
            "the accepted-answer key's answer_path",
            key.answer_path,
            "however correctly it located the fault",
        )
    )
    for half, answers in (("accepted", key.accepted), ("rejected", key.rejected)):
        problems.extend(
            _key_location_problems(
                task, f"the accepted-answer key's {half} answers", answers
            )
        )
    return problems


def _answer_path_problems(
    task: Task, whose: str, answer_path: str, however: str
) -> list[str]:
    """Whether the answer file a key declares can reach the verdict at all.

    Three ways it cannot, and none of them turns on which key declared it or
    what the answer means, which is why both keys are held to these by one
    implementation: a path outside the workdir never lands in the diff a run
    logs; a path a grading file already occupies is overwritten by the overlay
    before the verdict reads it; and a path the prompt never names leaves the
    agent with nowhere correct to write. `however` is the clause that says what
    the wasted work was — locating the fault, reviewing the change — because
    that is the one part of this a reader wants said in the task's own terms.
    """
    problems: list[str] = []
    if _escapes_workdir(answer_path):
        problems.append(
            f"{task.id}: {whose} {answer_path!r} is absolute or climbs out of "
            "the workdir with '..' — the workdir diff a run is graded from can "
            "only ever hold paths inside the workdir, so the agent's answer "
            f"would never reach the diff {however}"
        )
    elif answer_path in _tree_bytes(task.grading_dir):
        problems.append(
            f"{task.id}: {whose} {answer_path!r} collides with a file grading "
            "overlays over the workdir — the agent's answer file would be "
            "silently overwritten by the held-out grading files before the "
            "verdict ever reads it"
        )
    if not _prompt_names_path(task.prompt, answer_path):
        problems.append(
            f"{task.id}: the prompt never names the answer file "
            f"{answer_path!r} — the answer file is the whole deliverable, so "
            "an agent that is not told where to write it cannot solve the task "
            f"{however}"
        )
    return problems


def _key_location_problems(
    task: Task, whose: str, answers: Sequence[Answer]
) -> list[str]:
    """Whether every location this half of a key names is one an agent could
    actually give: a file of the starting repository, matched case-exactly, and
    a symbol that file defines, spelled the way the comparison can match it.

    One implementation for both keys and for both halves of each. Every rule
    here is a fact about one (file, symbol) pair read against the repository
    the agent is handed, and none of them turns on the quantifier the accepted
    half is read under — so a findings key's findings are checked by exactly
    these and not by a softened set of them. `whose` is only how a message
    names the half that is wrong.
    """
    problems: list[str] = []
    for answer in answers:
        source = _repo_file(task, answer.file)
        if source is None:
            problems.append(
                f"{task.id}: {whose} name {answer.file!r}, which is not in the "
                "starting repository — no agent can answer with a file it was "
                "never given"
            )
            continue
        try:
            defined = task.runner.defined_symbols(source.read_text(encoding="utf-8"))
        except (OSError, SourceUnreadable, UnicodeDecodeError) as error:
            problems.append(
                f"{task.id}: {whose} name {answer.file!r}, whose definitions "
                f"cannot be read ({error}) — the key is checked against what "
                "the file actually defines"
            )
            continue
        if answer.symbol not in defined:
            problems.append(
                f"{task.id}: {whose} name symbol {answer.symbol!r}, which "
                f"{answer.file} does not define — it defines {sorted(defined)}, "
                "and a method is written 'Class.method'"
            )
        elif "." not in answer.symbol:
            # matches() is deliberately one-directional: an *answer* spelled
            # bare matches a key spelled qualified, never the reverse — a key
            # spelled bare would let `Other.method` answer it too, which is a
            # false positive rather than a forgiven spelling. So where a
            # qualified spelling of this symbol exists, the key has to use it.
            qualified = sorted(
                candidate
                for candidate in defined
                if candidate != answer.symbol
                and candidate.endswith(f".{answer.symbol}")
            )
            if qualified:
                problems.append(
                    f"{task.id}: {whose} name bare symbol {answer.symbol!r} in "
                    f"{answer.file!r}, which is also defined as "
                    f"{qualified[0]!r} — a bare answer matches a qualified key, "
                    "never the reverse, so a key spelled bare refuses the "
                    "qualified spelling an agent would most naturally give. "
                    f"Write the key as {qualified[0]!r}"
                )
    return problems


def _answer_module_problems(task: Task) -> list[str]:
    """Whether this task ships the answer comparison, unedited.

    The comparison is the half of the verdict that discriminates, so it is one
    owned module copied identically into every task of both keyed actions
    (fault-location and codebase-comprehension) rather than hand-written per
    task — and the copies are read byte for byte against the bytes this
    package itself owns (`answer_module_source()`). This is a *stronger* check
    than the one the family lint runs on a family's starting repositories and
    grading suites: the family lint compares each member's tree against the
    alphabetically-first member's, peer to peer, because that is the only
    source a family lint has — a lone keyed task has no sibling to compare
    against. Here there is a privileged source instead,
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
            "identically into every keyed task, and a copy that has drifted "
            "grades this task by rules no other task is graded by"
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

    Applies to every task carrying a key — both keyed actions — and is not
    gated on `_answer_key_problems`: unlike a broken key, a drifted copy of
    this file says nothing about whether the *key* is sound, so it does not
    stop `_discrimination_problems` from running (see `lint_task_set`).
    """
    if not is_keyed(task):
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
            "identically into every keyed task, so that its grading test is "
            "always the one-line assertion over `answer_problem()` that "
            "binds the verdict to `_answer.py`, and never a hand-written "
            "test that quietly stops consulting it. A task may ship "
            "*additional* grading tests beside it — resolution requires "
            "every one of them to pass, so an extra test can only make the "
            "task harder to resolve, never let a wrong answer through"
        )]
    return []


# --- code-review: what the findings key has to say, read rather than run -------
#
# The findings analogue of `_answer_key_problems` and of the two byte
# comparisons beside it. Most of it is the same rule read over a set of findings
# instead of over one location — a file of the starting repository, a symbol
# that file defines, a spelling the comparison can match, an answer path that
# reaches the verdict — which is why that half is shared code
# (`_key_location_problems`, `_answer_path_problems`) and only what the
# quantifier changes is written again here.
#
# One rule is this key's own: every location it names sits in a file the change
# under review actually touches. A review task's `repo/` ships that change
# already applied, so the shipped diff is the only thing that says which of the
# repository is the change, and a key that wandered outside it would either
# plant a defect the agent was not asked to judge or fail a run for reporting a
# real problem the author did not plant — which the verdict archives everywhere
# else. (The other rule that used to live here, that no location is in both
# halves, is now the load-time set rule on `FindingsKey`, widened to every
# alternative of every planted finding and judged through the comparison.)
#
# All of it reads every **alternative** of every planted finding. A finding is a
# set of locations that legitimately describe one defect, and an alternative the
# repository does not hold is one an answer can never reach: the mitigation
# would silently be one entry shorter than the key reads.
#
# What is deliberately *not* here is the accepted-answer key's rule that the
# rejected half must name a file the accepted half does not. That rule exists
# because a locate key accepts one location, so a rejected answer in the same
# file is a wrong *symbol* the lint already synthesises for itself. A review's
# accepted half already spans the files of the change, so the same rule would
# refuse the most natural non-finding there is: the correct line next to the
# defective one.


# The two lines of a unified diff that name a file, with git's `a/` and `b/`
# prefixes stripped. Read rather than applied: the question is only which paths
# the change under review touches, and `git apply --numstat` would be a
# subprocess for something three characters of regex answer.
_DIFF_FILE_HEADER = re.compile(r"^(?:---|\+\+\+) (?:[ab]/)?(\S+)")


def _files_a_diff_names(diff: str) -> set[str]:
    """Every path a unified diff touches, as the diff itself names them.

    `/dev/null` is dropped rather than reported: it is how a unified diff spells
    the absent side of an added or deleted file, and no caller could name it.

    Written once for the two kinds of patch this project reads — the change a
    `code-review` task ships under review, and a `test-authoring` task's planted
    mutants — because "which files does this patch touch" is one question, and a
    second reader of the same headers would be a second answer to it.
    """
    touched: set[str] = set()
    for line in diff.splitlines():
        header = _DIFF_FILE_HEADER.match(line)
        if header is not None:
            touched.add(header.group(1))
    return touched - {"/dev/null"}


def _reviewed_files(task: Task) -> set[str]:
    """Every path the change under review touches, as the unified diff the
    starting repository ships names them — empty where that diff is missing,
    unreadable, or names nothing.
    """
    try:
        diff = (task.repo_dir / REVIEW_DIFF_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return _files_a_diff_names(diff)


def _findings_key_problems(task: Task) -> list[str]:
    """What is wrong with a `code-review` task's findings key.

    Gated on the key being on disk (`is_findings_keyed`) rather than on the
    category, the way every gate over the accepted-answer key is: a review task
    shipping no key never reaches here, because the loader refuses it.

    Read rather than run, and for the reason every other read invariant is
    checked here: none of it is repairable once the sweep is paid for, and each
    defect makes a task that grades every agent unresolved — or, for an empty
    accepted set, every agent resolved — while looking exactly like a hard one.

    What the key is checked against is the starting repository and the change
    under review shipped inside it: both halves say something at all; every file
    either half names is in that repository, matched case-exactly, and is one
    the change actually touches; every symbol is defined in the file it names,
    spelled so the comparison can match it; the findings comparison and the
    answer comparison it imports are this project's own bytes; and the declared
    answer path reaches the verdict and is named by the prompt. What no check
    can reach is whether the author planted every defect the change in fact
    contains — a defect nobody wrote down is one the verdict archives, which is
    the direction this grading is deliberately forgiving in.

    Every location rule here runs per **alternative** and not per finding: each
    alternative is a location the author declared legitimately correct, so one
    naming a file the repository does not hold, or a symbol it does not define,
    is an alternative no answer can reach — and the mitigation the alternatives
    exist to be would be one entry shorter than it reads.

    Two things are *not* here. The rule that no location is named twice — in one
    finding, across two, or in both halves — is refused at load (`FindingsKey`),
    because `ai-bench run-live` loads a task set and never lints it. And the
    half that has to be run rather than read is
    `_findings_discrimination_problems`, which the lint runs once this returns
    nothing.
    """
    if not is_findings_keyed(task):
        return []
    key = findings_key(task)
    problems: list[str] = []
    if not key.accepted:
        problems.append(_empty_accepted_findings_message(task))
    if not key.rejected:
        problems.append(
            f"{task.id}: the findings key declares no rejected findings — "
            "must-fail-on-pristine proves nothing about a review task, because "
            "a pristine repository carries no answer file at all, and the "
            "accepted half on its own is survived by an answer reporting every "
            "line of the change as a defect. Name at least one plausible "
            "non-finding: the place a reviewer points at where the change is in "
            "fact correct — the caller that returns the wrong number, the "
            "constant the change introduced and got right"
        )
    problems.extend(_findings_module_problems(task))
    problems.extend(
        _answer_path_problems(
            task,
            "the findings key's answer_path",
            key.answer_path,
            "however completely it reviewed the change",
        )
    )
    touched = _reviewed_files(task)
    if not touched:
        problems.append(
            f"{task.id}: {REPO_DIR}/{REVIEW_DIFF_FILE} is missing, unreadable, "
            "or names no file — a review task's starting repository ships the "
            "change under review already applied, so that diff is the only "
            "thing saying which of the repository is the change, and without it "
            "the key cannot be held to describing the change rather than the "
            "repository at large"
        )
    for half, findings in (
        ("accepted", _accepted_locations(key)),
        ("rejected", key.rejected),
    ):
        problems.extend(
            _key_location_problems(
                task, f"the findings key's {half} findings", findings
            )
        )
        problems += [
            f"{task.id}: the findings key's {half} findings name the finding "
            f"({answer.file!r}, {answer.symbol!r}), and the change under review "
            f"does not touch {answer.file!r} — {REPO_DIR}/{REVIEW_DIFF_FILE} "
            f"changes {sorted(touched)}. A review judges a change: a planted "
            "finding outside it is a defect the agent was never asked to look "
            "at, and a rejected one outside it fails a run for reporting a real "
            "problem of the repository the author did not plant"
            for answer in findings
            if touched and answer.file not in touched
        ]
    return problems


def _findings_module_problems(task: Task) -> list[str]:
    """Whether this review task ships the findings comparison, unedited — and
    the answer comparison it imports its forgiveness from, unedited too.

    `_answer_module_problems`'s reasoning, over two files instead of one. The
    comparison is the half of the verdict that discriminates, so it is owned
    rather than hand-written per task and the shipped copies are read byte for
    byte against the bytes this package owns; six review authors cannot
    hand-copy six comparisons that quietly disagree about what a finding is. It
    covers `_answer.py` as well because `_findings.py` imports `matches`,
    `one_location` and `resolve` from it rather than restating them — a review
    answer and a locate answer have to forgive the same spellings — so an
    edited copy of *that* file changes this task's verdict just as surely.
    """
    problems: list[str] = []
    for module, canonical in (
        (FINDINGS_MODULE, findings_module_source()),
        (ANSWER_MODULE, answer_module_source()),
    ):
        shipped = task.grading_dir / module
        try:
            copy = shipped.read_bytes()
        except OSError as error:
            problems.append(
                f"{task.id}: {GRADING_DIR}/{module} is missing or unreadable "
                f"({error}) — the findings comparison is what the held-out "
                "grading test asserts over, and it imports its location "
                f"forgiveness from {ANSWER_MODULE}, so without both the task "
                "grades every agent unresolved"
            )
            continue
        if copy != canonical:
            problems.append(
                f"{task.id}: {GRADING_DIR}/{module} is not the comparison this "
                "project ships — it is one owned module copied identically into "
                "every review task, and a copy that has drifted grades this "
                "task by rules no other task is graded by"
            )
    return problems


def _findings_test_problems(task: Task) -> list[str]:
    """Whether this review task ships the held-out grading test, unedited.

    `_answer_test_problems` from the other side of the same hole, and the same
    hole it is: shipping `_findings.py` byte for byte proves nothing about what
    a task's grading test actually *does* with it, and a hand-written assertion
    that checked "some finding matched" would lint clean under the module
    comparison alone while turning a set verdict into an any verdict.

    A task may ship *additional* grading tests beside this one. Resolution
    requires every grading test to pass, so an extra test can only make a task
    harder to resolve, never let a wrong answer through — this is a requirement
    that the canonical test is among them, unedited, and never a ban on others.

    Not gated on `_findings_key_problems`: a drifted copy of this file says
    nothing about whether the *key* is sound, so it does not stop the
    discrimination gate from running (see `lint_task_set`).
    """
    if not is_findings_keyed(task):
        return []
    shipped = task.grading_dir / FINDINGS_TEST_FILE
    try:
        copy = shipped.read_bytes()
    except OSError as error:
        return [(
            f"{task.id}: {GRADING_DIR}/{FINDINGS_TEST_FILE} is missing or "
            f"unreadable ({error}) — this is the held-out grading test that "
            "asserts over the findings comparison; without it nothing binds "
            "this task's grading to `_findings.py`, and a hand-written grading "
            "test that never calls findings_problem() would lint clean"
        )]
    if copy != findings_test_source():
        return [(
            f"{task.id}: {GRADING_DIR}/{FINDINGS_TEST_FILE} is not the held-out "
            "grading test this project ships — it is one owned file copied "
            "identically into every review task, so that its grading test is "
            "always the one-line assertion over `findings_problem()` that binds "
            "the verdict to `_findings.py`, and never a hand-written test that "
            "quietly stops consulting it. A task may ship *additional* grading "
            "tests beside it — resolution requires every one of them to pass, "
            "so an extra test can only make the task harder to resolve, never "
            "let a wrong answer through"
        )]
    return []


# --- test-authoring: what a planted mutant set has to be -----------------------


# The floor on a planted mutant set (design note §67.7): below three, the
# universal quantifier of the mutation gate's second half barely binds and one
# lucky assertion clears it. There is deliberately **no maximum**. Four to six
# is the spec's *authoring guidance*, not a lint rule, and so is spreading the
# mutants across distinct specified behaviours — neither is a refusal here, and
# neither should be turned into one: one test killing two mutants is legal,
# because the quantifier binds mutants and not tests.
_MINIMUM_MUTANTS = 3


def _mutant_set_problems(task: Task) -> list[str]:
    """What is wrong with this `test-authoring` task's planted mutant set, and
    with the terrain the agent is asked to write its suite into.

    Four rules, every one of them read rather than run, which is what lets them
    gate the expensive half: `lint_task_set` runs this action's registered
    existence proof only once these are clean, because that proof runs a whole
    suite once per mutant.

    - **At least three mutants** (`_MINIMUM_MUTANTS`).
    - **Disjointness.** Every file a mutant patch touches is a file of `repo/`,
      and none of them falls under the declared test path. This is what makes
      §67.4's promise — no agent edit and no mutation can ever collide — true by
      construction rather than by the author having been careful: grading
      collects the test subtree out of the workdir diff and plants mutants
      outside it, so a mutant reaching into that subtree would be overwritten by
      the very suite it is meant to catch out.
    - **The starting repository's test path holds no tests.** An existing suite
      there is a crib: the agent's deliverable is a suite for behaviour nothing
      tests yet. §67.6 words this as "no existing tests for the module under
      test"; nothing decides where one module's tests stop and another's begin,
      so what is refused here is *any* test under the declared test path, which
      is the same rule with nothing left to interpret.
    - **The prompt names the test path**, as a whole token (`_prompt_names_path`,
      the same check the terrain rules read paths with). A task whose agent
      cannot locate its own deliverable grades every run unresolved for a reason
      no verdict would ever explain.
    """
    problems: list[str] = []
    patches = mutant_patches(task)
    if len(patches) < _MINIMUM_MUTANTS:
        problems.append(
            f"{task.id}: {MUTANTS_DIR}/ holds {len(patches)} planted mutant(s), "
            f"and the minimum is {_MINIMUM_MUTANTS} — the verdict is 'every "
            "planted mutant is killed', so a set this small is a quantifier over "
            "almost nothing and a suite that asserted one boundary by luck would "
            "clear it. Plant more behaviour changes, each of a different "
            "specified behaviour"
        )
    for patch in patches:
        problems += _one_mutant_problems(task, patch)
    if task.test_path is not None:
        problems += _test_path_terrain_problems(task, task.test_path)
    return problems


def _one_mutant_problems(task: Task, patch: Path) -> list[str]:
    """What is wrong with one planted mutant: the files it touches, read out of
    the patch itself with the reader the change-under-review side already uses
    (`_files_a_diff_names`)."""
    try:
        diff = patch.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [(
            f"{task.id}: the planted mutant {MUTANTS_DIR}/{patch.name} cannot be "
            f"read ({error}) — a mutant is a unified diff against {REPO_DIR}/, "
            "and one nothing can read is a behaviour change the gate would fail "
            "to plant at grade time"
        )]
    touched = sorted(_files_a_diff_names(diff))
    if not touched:
        return [(
            f"{task.id}: the planted mutant {MUTANTS_DIR}/{patch.name} names no "
            f"file — a mutant is one deliberate behaviour change to {REPO_DIR}/, "
            "and a patch that changes nothing is a mutant no suite could ever "
            "kill, so it would grade every agent unresolved"
        )]
    problems: list[str] = []
    for name in touched:
        if task.test_path is not None and _under_the_test_path(name, task.test_path):
            problems.append(
                f"{task.id}: the planted mutant {MUTANTS_DIR}/{patch.name} "
                f"touches {name}, which is under the declared test path "
                f"{task.test_path!r} — the mutants and the agent's suite have to "
                "be disjoint by construction, because grading applies the test "
                "subtree of the run's diff over the mutated copy: a mutation in "
                "there is either overwritten by the suite meant to catch it or "
                "hands the agent the mechanism. Mutate the code under test"
            )
        elif _repo_file(task, name) is None:
            problems.append(
                f"{task.id}: the planted mutant {MUTANTS_DIR}/{patch.name} "
                f"touches {name}, which is not a file of {REPO_DIR}/ — a mutant "
                "is applied to a copy of the starting repository, so a patch "
                "against a file that is not there fails to apply and the gate "
                "quantifies over one fewer behaviour change than the task claims"
            )
    return problems


def _under_the_test_path(name: str, test_path: str) -> bool:
    """Whether this path falls inside the declared test subtree — the same
    prefix question `git apply --include=<test_path>/*` answers when grading
    collects that subtree, asked here over path components so that a `tests2/`
    beside a `tests/` is not read as being under it."""
    prefix = Path(test_path.rstrip("/")).parts
    return Path(name).parts[: len(prefix)] == prefix


def _test_path_terrain_problems(task: Task, test_path: str) -> list[str]:
    """The two rules about the place the suite is to be written: the starting
    repository has no tests there, and the prompt says where there is."""
    problems: list[str] = []
    existing = sorted(
        str(path.relative_to(task.repo_dir))
        for path in (task.repo_dir / test_path).rglob(task.runner.visible_test_glob)
        if path.is_file()
    )
    if existing:
        problems.append(
            f"{task.id}: {REPO_DIR}/{test_path} already holds {existing} — the "
            "deliverable is a suite for behaviour nothing tests yet, so a suite "
            "shipped where the agent is told to write one is a crib: it hands "
            "over which behaviours are worth asserting, which is the whole of "
            "what this action measures. Start the repository with that path "
            "empty of tests"
        )
    if not _prompt_names_path(task.prompt, test_path):
        problems.append(
            f"{task.id}: the prompt never names the test path {test_path!r} as a "
            "whole token — that path is where grading collects the deliverable "
            "from and nowhere else, so an agent that writes a perfect suite "
            "somewhere else grades unresolved for a reason no verdict would "
            "explain. Name it in the prompt exactly as task.yaml declares it"
        )
    return problems


# --- investigation: what a points key has to be --------------------------------


# The floor on a planted point set (design note §76.10), and the mutant
# minimum's own sentence pointed at points: the verdict is "every planted point
# is covered", so below three the universal quantifier binds over almost
# nothing and an answer that gestured at one consideration would clear it.
# There is deliberately **no maximum**. Four to six is the spec's *authoring
# guidance*, not a lint rule, exactly as it is for mutants — and neither should
# be turned into one, because what the guidance is about is how much of a
# question a key covers, which nothing here can read.
_MINIMUM_POINTS = 3


def _points_key_problems(task: Task) -> list[str]:
    """What is wrong with an `investigation` task's points key, read rather
    than run.

    Gated on the key being on disk (`is_point_keyed`) rather than on the
    category, the way every gate over the other three keys is. Every rule here
    is a fact about the key and the terrain around it that costs nothing to
    read, which is what lets them gate the expensive half: `lint_task_set` runs
    this action's registered existence proof only once these are clean, exactly
    as `_mutant_set_problems` gates its own — a key whose points are not there
    to be covered has nothing to say about whether an archive covers them.

    - **At least three planted points** (`_MINIMUM_POINTS`), with no maximum.
    - **An id and a question in every point and every disqualifier.** The model
      already refuses an empty string on either (`NonEmptyStr`), so what is
      left to this is the blank that gets past `min_length=1`: an id of spaces
      is an archive key nothing can be read against, and a question of spaces
      is one the grader is asked about nothing.
    - **No id used twice across the two halves.** Refused at load as well
      (`PointsKey.no_id_is_used_twice`), because `ai-bench run-live` loads a
      task set and never lints it — and stated here anyway, for the reason the
      empty-accepted-set rule is stated in `_findings_key_problems`: a rule
      that lives only at load is a rule the lint's account of this action does
      not contain.
    - **The `answer_path` rules**, through `_answer_path_problems`, which both
      other answer-file actions are already held to. Above all the third of
      them: an investigation's whole deliverable is the prose at that path, so
      a task whose agent cannot locate it grades every run unresolved for a
      reason no verdict would ever explain. That function's middle check —
      an answer path a held-out grading file would be overlaid onto — is
      inherited rather than restated, and its clause about the overlay is the
      one thing in it that is not this action's: a point-keyed task's
      `grading/` is never overlaid over anything. It is still a mistake worth
      refusing, an answer path pointed at the task's own held-out key.
    - **Nothing of the answer is in `repo/`.** The loader refuses a proofs
      subtree kept inside `grading/`; this is the other direction, and the one
      that matters to an agent: the key and the two proof answers are held out
      of the workdir, and a copy of any of them in the starting repository is
      the whole answer handed over.
    """
    if not is_point_keyed(task):
        return []
    key = points_key(task)
    problems: list[str] = []
    if len(key.points) < _MINIMUM_POINTS:
        problems.append(
            f"{task.id}: {GRADING_DIR}/{POINTS_KEY_FILE} plants "
            f"{len(key.points)} point(s), and the minimum is "
            f"{_MINIMUM_POINTS} — the verdict is 'every planted point is "
            "covered', so a key this small is a quantifier over almost nothing "
            "and an answer that named one consideration in passing would clear "
            "it. Plant more required elements, each a different consideration, "
            "trade-off or recommendation the question turns on"
        )
    seen: set[str] = set()
    for kind, planted in _point_questions(key):
        whose = f"the points key's {kind} {planted.id!r}"
        if not planted.id.strip():
            problems.append(
                f"{task.id}: {whose} has a blank id — the archive is keyed by "
                "id, so a ruling filed under one nobody can name is a ruling "
                "no later reading of this verdict could match to a question"
            )
        if not planted.text.strip():
            problems.append(
                f"{task.id}: {whose} has no text — the text is the whole of "
                "the narrow question the grader is asked about this point, and "
                "a blank one is a question about nothing that every answer "
                "covers or none does, depending on the mood of the instrument"
            )
        if planted.id in seen:
            problems.append(
                f"{task.id}: {whose} is the id of two of this key's questions "
                "— the rulings are archived one per id, across the points and "
                "the disqualifiers alike, so a shared id archives one ruling "
                "where two were asked and lets the second answer for the first"
            )
        seen.add(planted.id)
    problems.extend(
        _answer_path_problems(
            task,
            "the points key's answer_path",
            key.answer_path,
            "however well it investigated the question",
        )
    )
    problems.extend(_held_out_of_the_repository_problems(task))
    return problems


def _held_out_of_the_repository_problems(task: Task) -> list[str]:
    """The points key, or either proof answer, found inside the starting
    repository.

    Read at any depth, because a `docs/points-key.json` is handed to the agent
    exactly as a top-level one is. Named by filename rather than by content,
    which is the same mechanical reading
    `_held_out_of_the_workdir_but_not_of_grading` gives the other direction:
    what a copy of the answer is worth to an agent does not depend on where the
    author put it.
    """
    held_out = {POINTS_KEY_FILE, REFERENCE_ANSWER_FILE, FOIL_ANSWER_FILE}
    shipped = sorted(
        str(path.relative_to(task.repo_dir))
        for path in task.repo_dir.rglob("*")
        if path.is_file() and path.name in held_out
    )
    if not shipped:
        return []
    return [(
        f"{task.id}: {REPO_DIR}/ holds {shipped} — the points key and the two "
        f"answers it was proved with live in {GRADING_DIR}/ and {PROOFS_DIR}/, "
        "held out of the workdir the agent works in. A copy of any of them in "
        "the starting repository is not a terrain problem to be waived: it is "
        "the required elements of the answer, or an answer itself, handed over "
        "with the question"
    )]


# --- the hash gate: the repository is as it was handed over --------------------
#
# The deliverable of a keyed task is the location, not a repair, and the prompt
# says so — but an agent that does the fix work and then writes a correct
# answer would grade resolved at fix-member cost with nothing in the run log to
# show it. So the starting repository is hashed into a held-out grading test
# and compared at grade time.
#
# Round 4 wrote those digests with a script outside the repository and proved
# them per task, in four copies of the same assertion, which meant the gate was
# a property of the four tasks whose author remembered it rather than of the
# corpus. Generation is `write_hash_gates` below (reached by `ai-bench lint-v1
# --write-hash-gates`) and the proof is `_hash_gate_problems`, applied to every
# keyed task.

HASH_GATE_FILE = "test_the_repository_is_as_it_was.py"

# The table inside it, by the name the generated file gives it.
_HASH_GATE_TABLE = "AS_HANDED_OVER"

# The flag that writes the gate, named here because the generated file's own
# docstring has to tell a reader how it was made and how to remake it.
HASH_GATE_FLAG = "ai-bench lint-v1 --write-hash-gates"

# The two round-4 fault-location tasks authored before the gate existed, which
# ship none and never will. Adding one retroactively would change what a replay
# of round 4's logs computes — a run that answered correctly and also edited the
# code is recorded resolved, and gating it now would turn that recorded verdict
# over, which the spec puts out of scope.
#
# Frozen, and frozen in the direction that matters: a task authored from here on
# has no way into this set, because the only way in is to be one of these two
# names, and `tests/test_firstparty_v1_fault_location.py` pins the membership
# exactly so that widening it is an edit to a test that says why it is closed.
HASH_GATE_EXEMPT: frozenset[str] = frozenset({
    "ferry-locate-the-idle-boat",
    "noticeboard-locate-the-lost-notice",
})

# How the generated docstring counts the files it hashes. Words rather than
# numerals because it is prose, and a table rather than a library because the
# corpus is small and the alternative is a dependency for eight words. A count
# outside it falls back to the numeral: ungainly to read, but never wrong, and
# it cannot silently drop a file from the table itself.
_COUNTED = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}

_HASH_GATE_HEADER = '''\
"""Held out: whether the repository is exactly as the agent was handed it.

The deliverable of a task that carries a key — a located fault, a review's
findings, a located behaviour — is an answer file and never a repair, and this
task's prompt says so outright: do not put anything right, leave every file as
you found it. Unenforced, that would not matter for a task read on its own. It
matters because these tasks are read against the ones that ask for the edit —
what locating a defect costs, as against fixing it; what reviewing a change
costs, as against making it — and an agent that does the fix work and then
writes a correct answer would grade resolved at answer-file cost, with nothing
in the run log to show that it happened.

So the files the agent was handed are hashed here, and a run that changed,
deleted or replaced any of them grades unresolved however well it answered.
What it does not forbid is what a reader leaves behind: a scratch file, a
note, __pycache__ from running the repository's own tests. Only the {counted}
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`{flag}` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

{table} = {{
'''

_HASH_GATE_FOOTER = '''}


def test_the_repository_is_exactly_as_it_was_handed_over():
    changed = {}
    for name, digest in sorted(AS_HANDED_OVER.items()):
        found = Path.cwd() / name
        if not found.is_file():
            changed[name] = "gone"
        elif hashlib.sha256(found.read_bytes()).hexdigest() != digest:
            changed[name] = "edited"
    assert not changed, (
        f"the repository was not left as it was handed over: {changed} — this "
        "task asks for the location of the defect and not a repair"
    )
'''


def repo_digests(repo_dir: Path) -> dict[str, str]:
    """The sha256 of every file of a starting repository, by name.

    Top-level files only, which is what a v1 starting repository is: the gate
    compares each name against `Path.cwd() / name` in the workdir, so a name
    that is not a bare filename is not something it could check anyway.
    """
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(repo_dir.iterdir())
        if path.is_file()
    }


def hash_gate_source(repo_dir: Path) -> bytes:
    """This starting repository's hash gate, as the task has to ship it.

    A pure function of the repository's bytes, so re-running the generator over
    an unchanged corpus rewrites every gate identically and the result of the
    flag is reviewable in a diff.
    """
    digests = repo_digests(repo_dir)
    header = _HASH_GATE_HEADER.format(
        counted=_COUNTED.get(len(digests), str(len(digests))),
        flag=HASH_GATE_FLAG,
        table=_HASH_GATE_TABLE,
    )
    table = "".join(
        f'    "{name}": "{digest}",\n' for name, digest in sorted(digests.items())
    )
    return (header + table + _HASH_GATE_FOOTER).encode("utf-8")


def write_hash_gates(tasks: list[Task]) -> list[Path]:
    """Write every keyed task's hash gate from its `repo/` bytes, and return
    the gates whose contents actually changed.

    Which tasks get one is discovered from their keys (`carries_a_key`: an
    accepted-answer key or a findings key alike, because the exposure is the
    deliverable's and not the action's) and never from a list, so a keyed task
    authored tomorrow is generated for without anyone remembering to add it. `HASH_GATE_EXEMPT` is the one thing skipped,
    and it is skipped rather than merely not required: writing a gate for those
    two would change what a replay of round 4 computes.

    Untouched files are not rewritten, so an unchanged corpus is a no-op down
    to the mtimes as well as the bytes.
    """
    written: list[Path] = []
    for task in tasks:
        if not carries_a_key(task) or task.id in HASH_GATE_EXEMPT:
            continue
        gate = task.grading_dir / HASH_GATE_FILE
        source = hash_gate_source(task.repo_dir)
        if not gate.is_file() or gate.read_bytes() != source:
            gate.write_bytes(source)
            written.append(gate)
    return written


def _declared_digests(source: str) -> dict[str, str] | None:
    """The digest table a shipped hash gate declares, or None if it declares
    none that can be read.

    Read out of the shipped file rather than restated, because the shipped file
    is what grading runs: a check against a table this module reconstructed
    would prove the reconstruction and not the gate.

    Parsed as Python, and that is not the task's language leaking in: the gate is
    canonical Python this project generates and pytest runs, shipped into every
    keyed task's grading directory whatever language the repository it hashes is
    written in (`harness_test_paths`).
    """
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None
    for node in module.body:
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == _HASH_GATE_TABLE
            for target in node.targets
        ):
            continue
        try:
            table = ast.literal_eval(node.value)
        except ValueError:
            return None
        if isinstance(table, dict) and all(
            isinstance(name, str) and isinstance(digest, str)
            for name, digest in table.items()
        ):
            return {str(name): str(digest) for name, digest in table.items()}
        return None
    return None


def _hash_gate_problems(task: Task) -> list[str]:
    """Whether this keyed task ships the hash gate, and whether its digests
    still describe the repository that is checked in.

    Both ways round, because each direction misses what the other catches: a
    table whose digests are all correct still gates nothing about a file it
    does not name, and a table naming a file the repository no longer holds
    grades every run unresolved on a file that is not there. Neither shows up
    in a lint that only ran the grading tests on the pristine repository —
    the gate passes there by construction, since the pristine repository is
    what it was hashed from.

    Read rather than run, and held against the corpus rather than proved per
    task: this is the round-4 per-suite assertion moved to where a keyed task
    authored tomorrow inherits it.
    """
    if not carries_a_key(task) or task.id in HASH_GATE_EXEMPT:
        return []
    gate = task.grading_dir / HASH_GATE_FILE
    try:
        source = gate.read_text(encoding="utf-8")
    except OSError as error:
        return [(
            f"{task.id}: {GRADING_DIR}/{HASH_GATE_FILE} is missing or unreadable "
            f"({error}) — a task that ships an accepted-answer key asks for a "
            "location and not a repair, and without this gate a run that "
            "repaired the code and then answered correctly grades resolved at "
            f"fix-member cost. Generate it with `{HASH_GATE_FLAG}`"
        )]
    declared = _declared_digests(source)
    if declared is None:
        return [(
            f"{task.id}: {GRADING_DIR}/{HASH_GATE_FILE} declares no readable "
            f"{_HASH_GATE_TABLE} table of digests — the gate is generated and "
            f"not typed, so regenerate it with `{HASH_GATE_FLAG}` rather than "
            "repairing it by hand"
        )]
    handed_over = repo_digests(task.repo_dir)
    problems: list[str] = []
    for name in sorted(declared):
        if name not in handed_over:
            problems.append(
                f"{task.id}: {GRADING_DIR}/{HASH_GATE_FILE} hashes {name!r}, "
                "which the starting repository does not hold — the gate would "
                "grade every run unresolved over a file no agent was handed. "
                f"Regenerate it with `{HASH_GATE_FLAG}`"
            )
        elif declared[name] != handed_over[name]:
            problems.append(
                f"{task.id}: {GRADING_DIR}/{HASH_GATE_FILE} records a digest for "
                f"{name!r} that is not the digest of the checked-in file — "
                "`repo/` was edited after the gate was written, which leaves "
                "the task lint-clean and its reference solution resolving "
                "while grading every real run unresolved. Regenerate it with "
                f"`{HASH_GATE_FLAG}`"
            )
    problems += [
        f"{task.id}: {GRADING_DIR}/{HASH_GATE_FILE} does not hash {name!r}, "
        "which is a file of the starting repository — an agent may edit it and "
        "still grade resolved, which is the whole of what the gate is for. "
        f"Regenerate it with `{HASH_GATE_FLAG}`"
        for name in sorted(set(handed_over) - set(declared))
    ]
    return problems


# --- typescript: what a task in that language may ship -------------------------
#
# The authoring half of admitting TypeScript, read rather than run. Every rule
# here is about what a task's *files* are, and each exists because the thing it
# refuses would otherwise be found at grade time or not at all — which, for a
# task set that is swept once and paid for once, is the same as never.
#
# Two of the four are ADR-0003 enforced rather than merely stated: a TypeScript
# task installs nothing. Grading runs `node --test` with the standard library,
# the task's own files and no package manager, so a dependency is not a harder
# task but an ungradable one — declared or vendored in the starting repository
# (`_stdlib_only_problems`), or named by a held-out test
# (`_held_out_specifier_problems`). The module system the workdir runs under is
# the runner's to pin (`run_tests` writes the canonical package.json last) and
# not the task's to declare, which is the other half of why a manifest is
# refused.
#
# The third is that a `.ts` file which does not load is a task that cannot do
# its job (`_typescript_load_problems`), and the fourth that a keyed task's
# starting repository is flat, because that is the shape its hash gate can
# actually gate (`_keyed_repo_flatness_problems`).

# A manifest declares dependencies and decides the module system; a
# node_modules is a dependency tree checked in. Both are refused at any depth
# of `repo/`, which is the tree the agent is handed and the one grading copies.
_PACKAGE_MANIFEST = "package.json"
_INSTALLED_DEPENDENCIES = "node_modules"

# What a held-out TypeScript test may name: a Node builtin under its explicit
# `node:` prefix, or a file of the task, relatively and with the extension Node
# actually resolves. Anything else is a package specifier, and there is no
# package.
_BUILTIN_PREFIX = "node:"
_RELATIVE_PREFIXES = ("./", "../")
_TYPESCRIPT_SOURCE_SUFFIX = ".ts"

# The specifiers a TypeScript file names, read as text rather than parsed: this
# is a rule over files an author wrote, not an import graph, and the shapes are
# `from "x"`, `import "x"`, `import("x")` and `require("x")`. The lookbehind is
# what keeps `Array.from("abc")` from reading as an import of "abc".
_SPECIFIER = re.compile(
    r"""(?<![.\w$])(?:from|import|require)\s*\(?\s*(['"])(?P<specifier>[^'"\n]*)\1"""
)


def _typescript_problems(task: Task) -> list[str]:
    """What the lint refuses about a TypeScript task's files, and nothing at
    all about a task in any other language.

    Dispatched on the registered runner rather than on the declared string, so
    that a language admitted later inherits none of this by having a name that
    looks like it: these are Node's rules, and they belong to the tasks the
    TypeScript runner grades.
    """
    if task.runner is not TYPESCRIPT:
        return []
    return (
        _stdlib_only_problems(task)
        + _typescript_load_problems(task)
        + _held_out_specifier_problems(task)
        + _keyed_repo_flatness_problems(task)
    )


def _stdlib_only_problems(task: Task) -> list[str]:
    """A manifest or an installed dependency tree anywhere in the starting
    repository — the stdlib-only rule (ADR-0003) refused on the author.

    A dependency tree is reported as the one thing it is: what is *inside* a
    `node_modules` is not a second problem an author could fix separately, and
    a vendored tree holds hundreds of manifests that would otherwise bury the
    one line that says to delete it.
    """
    return [
        f"{task.id}: {REPO_DIR}/ holds {path.relative_to(task.repo_dir)} — a "
        "typescript task installs nothing (ADR-0003): grading runs `node --test` "
        "with the standard library, the task's own files and no package manager, "
        "so a dependency declared or vendored here is not there at grade time, "
        "and the module system the workdir runs under is pinned by the runner "
        f"rather than by the task. Write the task against `{_BUILTIN_PREFIX}` "
        "builtins"
        for name in (_PACKAGE_MANIFEST, _INSTALLED_DEPENDENCIES)
        for path in sorted(task.repo_dir.rglob(name))
        if _INSTALLED_DEPENDENCIES
        not in path.relative_to(task.repo_dir).parent.parts
    ]


def _typescript_load_problems(task: Task) -> list[str]:
    """Every `.ts` file the task ships that does not load under the Node that
    grades it, in Node's own words.

    All four trees, because all four are read by something: `repo/` is handed
    to the agent, `grading/` decides the verdict, and `proofs/` and
    `corrected/` are run and read by this lint. A file in any of them that
    cannot be imported is a task that cannot do its job, and — this being the
    point of importing rather than checking — `node --check` says nothing
    about it (see `typescript_load_problems`).
    """
    return [
        f"{task.id}: {directory.name}/{relative} does not load under the Node "
        f"that grades it: {reason}. Every `{TYPESCRIPT.source_glob}` file a task "
        "ships is imported for real by this lint, because `node --check` passes "
        "syntax that type stripping then refuses — and because a module must be "
        "side-effect-free at import, which is what makes a CLI entry point a "
        "guarded one: Node 22 has no `import.meta.main`, so the idiom is "
        "`if (process.argv[1] === fileURLToPath(import.meta.url))`"
        for directory in (
            task.repo_dir,
            task.grading_dir,
            task.proofs_dir,
            task.corrected_dir,
        )
        if directory.is_dir()
        for relative, reason in sorted(typescript_load_problems(directory).items())
    ]


def _held_out_specifier_problems(task: Task) -> list[str]:
    """What a held-out test imports that grading cannot give it.

    A grading test runs in a workdir holding the repository, the overlay and
    nothing else — no install has happened and none will — so the only things
    it can name are `node:` builtins and the task's own files, relatively and
    with the extension Node resolves. A bare package specifier is not a
    dependency this task forgot to declare; it is one it may not have, and a
    test naming one grades every run unresolved on a module error.
    """
    problems: list[str] = []
    for name in task.language_test_paths:
        source = (task.grading_dir / name).read_text(encoding="utf-8")
        for specifier in sorted(set(_typescript_specifiers(source))):
            if specifier.startswith(_BUILTIN_PREFIX):
                continue
            if specifier.startswith(_RELATIVE_PREFIXES) and specifier.endswith(
                _TYPESCRIPT_SOURCE_SUFFIX
            ):
                continue
            problems.append(
                f"{task.id}: the held-out test {GRADING_DIR}/{name} imports "
                f"{specifier!r} — a typescript task installs nothing (ADR-0003), "
                f"so a held-out test may name a builtin under its explicit "
                f"`{_BUILTIN_PREFIX}` prefix or a file of the task relatively and "
                f"with its `{_TYPESCRIPT_SOURCE_SUFFIX}` extension, and nothing "
                "else. Anything else is a package specifier, and there is no "
                "package: the test would fail on a module error whatever the "
                "agent wrote"
            )
    return problems


def _typescript_specifiers(source: str) -> list[str]:
    """Every module specifier this source names."""
    return [match.group("specifier") for match in _SPECIFIER.finditer(source)]


def _keyed_repo_flatness_problems(task: Task) -> list[str]:
    """A directory under a keyed TypeScript task's starting repository.

    The hash gate is what makes a keyed task ask for a location rather than a
    repair, and it hashes top-level files only: `repo_digests` iterates with
    `iterdir()`, and the generated gate compares each name against
    `Path.cwd() / name`. So a file nested under `repo/` is ungated — an agent
    could repair it and still grade resolved, at answer-file cost, with nothing
    in the run log to show it. Every keyed Python task is flat already, so the
    cheapest rule that closes this is that a keyed TypeScript one is too: a
    refusal here rather than a wider gate, because widening the gate would
    change what a replay of every keyed task computes.
    """
    if not carries_a_key(task):
        return []
    return [
        f"{task.id}: {REPO_DIR}/{entry.name}/ is a directory, and a keyed "
        "typescript task's starting repository must be flat — the hash gate that "
        "holds a keyed task to answering rather than repairing hashes top-level "
        "files only, so anything nested under it is ungated and an agent could "
        "repair it and still grade resolved. Flatten the repository rather than "
        "widening the gate"
        for entry in sorted(task.repo_dir.iterdir())
        if entry.is_dir()
    ]


# --- terrain: the three rules a keyed task's prompt and repository hold to -----
#
# Terrain is what makes locating a fault work rather than a grep. Round 4
# proved all three of these per task, in six copies of the same assertions
# spread across six suites, which meant a seventh keyed task inherited none of
# them and a drift in one copy was invisible from the other five. They are
# rules of the task-set lint now: applied to *every* task carrying an
# accepted-answer key, so a task cannot be authored without them, and so that
# the one declared exception is a `terrain_waiver` in a `task.yaml` — read
# beside the task it apologises for — rather than a pinned frozenset in a test
# file nobody reads until it turns red.

# The words a prompt cannot be blamed for sharing with the repository it is
# about: the closed-class words English sentences are built out of. Owned here,
# once and in code, because they are the same list for every task in every
# domain — the *domain* nouns that a prompt and a repository about one subject
# unavoidably share are the half that varies, and those are declared per task
# as `domain_nouns`. Everything a prompt says that is in neither list is
# distinctive, and distinctive vocabulary is grep bait.
FUNCTION_WORDS = frozenset("""
    a about after all also an and any are as at be been being both but by can
    could did do does each either few for from get given goes had has have he
    her his how i if in into is it its just like made make many may me might
    more most much must my no nor not now of off on once one only or other our
    out over own per same she should since so some such than that the their
    them then there these they this those through to too under until up us
    very was we well were what when where whether which while who whom why
    will with within would you your s t
""".split())


def _prompt_terms(prompt: str, domain_nouns: Sequence[str]) -> set[str]:
    """The distinctive vocabulary of one prompt.

    Every content word, and every adjacent pair of words at least one of which
    is a content word — a pair as well as a word because "every ask" and "left
    over" narrow as hard as any single word does and neither half of either
    narrows on its own.

    One prompt and never two. Round 4's suites read both members of a
    locate/fix pair together, which made a word the *fix* task's prompt
    happened to use count as bait in the locate task that never said it; the
    agent solving a task sees that task's prompt, so that is the input the rule
    reads.
    """
    unrevealing = FUNCTION_WORDS | {noun.lower() for noun in domain_nouns}
    words = re.findall(r"[a-z]+", prompt.lower())
    terms = {word for word in words if word not in unrevealing}
    terms |= {
        f"{first} {second}"
        for first, second in zip(words, words[1:], strict=False)
        if not (first in unrevealing and second in unrevealing)
    }
    return terms


def _repo_lines(task: Task) -> list[tuple[str, str, int, str]]:
    """Every line of the starting repository's code, as
    (module, file, number, lowercased text).

    A test file counts as part of the module it tests, because `test_paging.py`
    points at `paging.py` as surely as `paging.py` does. Anything that is not a
    top-level source file of the task's own language — `README.md` above all —
    counts as no module at all: the README is the index that names every
    module, so a word found only there has selected the whole repository rather
    than one file, and cannot rescue a word that otherwise narrows. Which files
    those are is the runner's `source_glob` and not a `.py` written here, or a
    repository in a second language would read as empty and every terrain rule
    would pass vacuously.
    """
    lines: list[tuple[str, str, int, str]] = []
    for path in sorted(task.repo_dir.glob(task.runner.source_glob)):
        module = _module_a_file_is_part_of(path.name, task.runner.visible_test_glob)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            lines.append((module, path.name, number, line.lower()))
    return lines


def _module_a_file_is_part_of(name: str, test_glob: str) -> str:
    """Which module of the starting repository this file belongs to.

    A test file belongs to the module it tests, and which files those are is the
    runner's own spelling of a test rather than a `test_` prefix written here:
    `test_paging.py` under pytest and `paging.test.ts` under `node --test` are
    one convention read twice, and a rule that knew only the first would file
    every TypeScript test under a module of its own — where a prompt word found
    in a test alone would narrow to nothing rather than to the module the test
    is about, which is the direction that lets grep bait through.
    """
    prefix, _, suffix = test_glob.partition("*")
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix) : len(name) - len(suffix)]
    return Path(name).stem


def _key_locations_the_prompt_names(
    task: Task, key: KeyedGroundTruth
) -> dict[str, str]:
    """Terrain rule 1: where the prompt names a location out of the key.

    Either half of it. An accepted location in the prompt hands the agent the
    answer; a *rejected* one in the prompt hands it the near-miss the key
    exists to refuse, which is the same task made unfair from the other side.

    Matched on whole tokens the way `_prompt_names_path` matches the answer
    path, and for the same reason: "Line" must not be found inside "Lines".
    The key's own spellings are what is checked — an author writes down every
    description level that is legitimately correct, so a class the prompt must
    not name is in the key under its own name already.

    The declared answer path is never bait, however it is spelled: the prompt
    is *required* to name it (`_answer_key_problems`), so a task that declared
    its answer path equal to one of its own key locations would otherwise be
    caught coming and going.
    """
    named: dict[str, str] = {}
    for half, answers in (
        ("accepted", _accepted_locations(key)),
        ("rejected", key.rejected),
    ):
        for answer in answers:
            for what, token in (("file", answer.file), ("symbol", answer.symbol)):
                if token == key.answer_path or token in named:
                    continue
                if _prompt_names_path(task.prompt, token):
                    named[token] = (
                        f"the prompt names {token!r}, the {what} of one of the "
                        f"key's {half} answers — the location is the whole "
                        "deliverable, so a prompt that names a location out of "
                        "the key hands the agent the reading it was supposed "
                        "to do"
                    )
    return named


def _narrowing_prompt_terms(task: Task, key: KeyedGroundTruth) -> dict[str, str]:
    """Terrain rule 2: where a content word of the prompt selects the accepted
    module and nothing else.

    A word the prompt uses that appears in exactly the module(s) the accepted
    answer names is one grep from the answer, and the task then measures
    whether the agent greps rather than whether it locates. Matched on word
    boundaries and never as a substring: substring matching reads "night" as
    narrowing to a docstring that says "tonight", which is an artifact of the
    matcher and not a path any solver could walk.
    """
    accepted_modules = {
        Path(answer.file).stem for answer in _accepted_locations(key)
    }
    if not accepted_modules:
        return {}
    lines = _repo_lines(task)
    narrowing: dict[str, str] = {}
    for term in sorted(_prompt_terms(task.prompt, task.domain_nouns)):
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        found = [line for line in lines if pattern.search(line[3])]
        if not found or not {line[0] for line in found} <= accepted_modules:
            continue
        where = [f"{line[1]}:{line[2]}" for line in found]
        narrowing[term] = (
            f"the prompt's {term!r} appears only in the module the accepted "
            f"answer names ({', '.join(where)}) — one grep of the prompt's own "
            "vocabulary lands in the file the agent was asked to find, so the "
            "task measures grepping rather than reading. Say it in the "
            "prompt's words and the repository's own, differently; or, where "
            "the word is one a prompt and a repository about this subject "
            "cannot help sharing, declare it in `domain_nouns`"
        )
    return narrowing


def _lone_accepted_classes(task: Task, key: KeyedGroundTruth) -> dict[str, str]:
    """Terrain rule 3: where an accepted class is the only class in its file.

    An agent electing to answer at class level answers with the class, and if
    the module defines exactly one, that answer is determined by the filename
    alone: one grep to the file, the only class there, resolved, with the
    defective method never read. So wherever a key accepts a class, that class
    is one of at least two the file defines, and telling them apart takes
    reading both.

    Read over every alternative of every **planted finding**, not over the
    primaries alone: the class level is exactly what a review key's second
    alternative usually is, so a rule that skipped it would fire on none of the
    locations it exists for.
    """
    lone: dict[str, str] = {}
    for answer in _accepted_locations(key):
        source = _repo_file(task, answer.file)
        if source is None:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Reported by `_answer_key_problems`, which reads the same file
            # for the same reason; saying it twice adds nothing.
            continue
        if not task.runner.loads(text):
            continue
        classes = task.runner.defined_classes(text)
        if answer.symbol in classes and len(classes) < 2:
            token = f"{answer.file}:{answer.symbol}"
            lone[token] = (
                f"the accepted class-level location {token!r} is the "
                f"only class {answer.file} defines — an agent answering at "
                "class level would have that answer determined by the filename "
                "alone, without ever reading the defective method"
            )
    return lone


def _terrain_exemption(task: Task) -> str | None:
    """This task's action-level exemption from the terrain rules, and the reason
    it is exempt — or None, which is every task the rules apply to.

    A registry lookup for three of the four entries, and a lookup gated on the
    key on disk for the fourth. `codebase-comprehension` is registered because
    an explain-style task of it keys planted points, which are nowhere in the
    workdir to be grepped; but the category's locate-style tasks key accepted
    *locations*, which is the very thing these rules guard, so reading the
    category's entry for them would silence all three rules on the four live
    tasks that most need them. Which shape a task is is read off its key, never
    off a list (§45.6, §106.5), which is what keeps this right for the
    explain-style task authored after this was written.
    """
    reason = TERRAIN_EXEMPT_ACTIONS.get(task.category)
    if reason is None:
        return None
    if task.category == _POINT_OPTIONAL_CATEGORY and not is_point_keyed(task):
        return None
    return reason


def _terrain_problems(task: Task) -> list[str]:
    """The three terrain rules, applied to every task carrying a key of either
    shape, and the waivers a task declares against them.

    Keyed on "the task carries a key" rather than on the category or on which
    key it is: `fault-location` is where these started, but a locate-style
    `codebase-comprehension` task is graded off the same file, and a
    `code-review` task's findings key names the very locations its answer file
    has to report — all three are greppable in exactly the same way, and the
    design note applies the rules to every task that carries a key. So a review
    task's prompt may not name a file or a symbol out of either half of its
    findings key, and its distinctive vocabulary may not select the module a
    planted finding lives in, on pain of measuring grepping rather than
    reviewing.

    A waiver silences a rule only for what it names, and a waiver naming
    something the rule does not fire on is itself reported: those two together
    are what stop a waiver from quietly widening as a prompt is edited, or
    from surviving the terrain improvement that made it unnecessary. Both
    properties reach a review task unchanged, because the waiver is read
    against what the rule fired on and never against the key it fired over.

    Four actions are exempt from all three at the action level rather than by
    waiver (`TERRAIN_EXEMPT_ACTIONS`, design note §67.6, §76.10 and §106.5),
    and the exemption is consulted here rather than left to fall out of those
    actions having no key to grep for: what these rules protect is a key an
    agent could read out of the workdir, and neither a `test-authoring` task's
    key — its planted mutants — nor a point-keyed task's — its planted points —
    is in the workdir at all.

    One of those four exemptions is read by key shape rather than by category
    (`_terrain_exemption`): `codebase-comprehension` carries locate-style tasks
    whose accepted-answer key *is* a set of greppable locations, and taking the
    category's entry wholesale would lift all three rules off exactly the tasks
    they were written for.
    """
    if _terrain_exemption(task) is not None:
        return []
    fired: dict[TerrainRule, dict[str, str]] = {rule: {} for rule in TERRAIN_RULES}
    try:
        key = _ground_truth(task)
    except IngestError:
        # A key that cannot be read is reported where it is read; terrain is
        # not judgeable without one, and a second complaint about the same file
        # would only bury the first.
        return []
    if key is not None:
        fired["prompt-names-a-key-location"] = _key_locations_the_prompt_names(
            task, key
        )
        fired["prompt-word-narrows-to-the-accepted-module"] = _narrowing_prompt_terms(
            task, key
        )
        fired["accepted-class-is-the-only-class"] = _lone_accepted_classes(task, key)

    problems: list[str] = []
    for rule in TERRAIN_RULES:
        violations = fired[rule]
        waived = {
            covered
            for waiver in task.terrain_waiver
            if waiver.rule == rule
            for covered in waiver.covers
        }
        problems += [
            f"{task.id}: terrain rule {rule!r}: {violations[token]}"
            for token in sorted(violations)
            if token not in waived
        ]
        problems += [
            f"{task.id}: the terrain waiver for {rule!r} covers {token!r}, which "
            "the rule does not fire on — a waiver applies only to what it names, "
            "so this one silences nothing and is a written-down apology for "
            "terrain that is no longer there. Drop it, or correct what it names"
            for token in sorted(waived - set(violations))
        ]
    return problems


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
    """What is wrong with a keyed task whose accepted-answer key accepts
    nothing, worded once so the loader and the lint say the same thing: the
    loader has to refuse this too, because `ai-bench run-live` loads a task
    set but never lints it, so an unsolvable key would otherwise reach a paid
    run."""
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


def _missing_answer_edit_target(key: KeyedGroundTruth) -> str:
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
    """Whether this keyed task's grading test tells a correct answer from a
    wrong one — which is the half of the verdict must-fail-on-pristine cannot
    reach.

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
    That is the task's registered **existence proof** (`EXISTENCE_PROOFS`), run
    by the lint beside these negatives: for a fault-location task, the partner
    `bug-fix` member's held-out tests failing on the starting repository the two
    share, which the lint discovers by those repositories' bytes — the two
    members are deliberately neither a task family nor a pair, so there is no
    declared link to read — and runs, rather than leaving it to the convention
    they were once authored under. A locate-style `codebase-comprehension` task
    owes a different proof, having no defect behind it: what has to exist there
    is the behaviour the question asks after, and its form is that the accepted
    answer resolves in the starting repository (design note §45.4).
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

    Walks the accepted files in order and moves on from one that leaves no
    unaccepted symbol behind, so a key naming a one-symbol module beside a
    richer one still gets its negative.
    """
    for file in dict.fromkeys(answer.file for answer in key.accepted):
        symbol = _symbol_the_key_does_not_name(task, file, key.accepted)
        if symbol is not None:
            return file, symbol
    return None


def _symbol_the_key_does_not_name(
    task: Task, file: str, named: Sequence[Answer]
) -> str | None:
    """The first symbol this file defines that none of these locations name, or
    None where every one of them is named.

    Not named is read through the very comparison the grading test uses, not
    through set membership: with the bare spelling of an accepted method
    accepted too, a candidate picked by string difference alone could be a
    correct answer the lint then demanded be graded wrong.

    What is passed as `named` differs by key, and deliberately. A fault-location
    near-miss avoids the *accepted* set only, because a rejected answer equal to
    it is a lint problem in its own right — the author's judgement belongs on
    the plausible wrong file. A review near-miss avoids every location the key
    registers — every alternative of every planted finding, and every rejected
    location — because a candidate that is an alternative is an answer the
    verdict is meant to resolve, and one the key rejects would grade unresolved
    on the rejected half and so prove nothing about whether the comparison read
    the symbol at all.
    """
    source = _repo_file(task, file)
    if source is None:
        return None
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not task.runner.loads(text):
        return None
    defined = task.runner.defined_symbols(text)
    candidates = sorted(
        symbol
        for symbol in defined
        if not any(
            _answer.matches((file, symbol), (location.file, location.symbol))
            for location in named
        )
    )
    return candidates[0] if candidates else None


def _findings_discrimination_problems(task: Task, *, timeout_s: int) -> list[str]:
    """Whether this review task's held-out test tells a review from an answer
    file that reviewed nothing — the half of the verdict must-fail-on-pristine
    cannot reach, for a set-shaped key.

    A pristine repository carries no answer file, so the grading test fails
    there whatever it asserts and the invariant is unconditionally satisfied.
    So this runs answers it expects to *fail* through the real pipeline — the
    diff built by the live runner's own capture, graded by `grade`, exactly as
    replay grades a logged run — and requires each to come out unresolved.

    Three of them are `_discrimination_problems`' own, unchanged: no answer file
    at all, an empty one, a malformed one. Four more are what a *set* verdict
    has to earn, and the first of them is the load-bearing one:

    - every planted finding but one, which is precisely what a comparison
      asking "did some finding match" cannot survive, and what makes the
      accepted half's quantifier real rather than declared. A whole **finding**
      is dropped, every alternative of it with it: dropping one alternative and
      leaving another would leave an answer the verdict is *supposed* to
      resolve;
    - every planted finding with one of them described by a symbol of the right
      file that the key registers on neither side — the synthesised near-miss,
      which kills a comparison that reads the file and not the symbol. Built per
      finding **per alternative's file**, because a finding whose alternatives
      span two files is read the file way in two places, and a near-miss in only
      the primary's file would leave the second unchecked;
    - every planted finding *plus* one rejected finding, which is the half that
      stops every-line-is-a-finding from passing, and which an answer missing
      no planted finding at all would otherwise sail through;
    - each author-declared rejected finding on its own.

    Where a near-miss cannot be constructed for a finding in one of its files —
    every symbol that file defines is itself an alternative or rejected — that
    is reported as the lint problem it is rather than one check quietly not run.

    And one **positive**, which is the point of the alternatives and the only
    thing here that has to grade *resolved*: for every planted finding and every
    alternative of it, the answer reporting that finding at that alternative
    (and every other finding at its primary) is required to resolve. Each
    alternative is the author's written claim that a review describing the
    defect *there* is correct, and until this ran that claim was trusted rather
    than checked — a second alternative naming a location the verdict cannot in
    fact match would read as a mitigation and be none. The answers are
    deduplicated by their bytes, since "every finding at its primary" is one
    answer however many findings there are.
    """
    key = findings_key(task)
    alternatives = [
        [(answer.file, answer.symbol) for answer in planted.any]
        for planted in key.accepted
    ]
    primaries = [locations[0] for locations in alternatives]
    problems: list[str] = []
    negatives: list[tuple[str, Callable[[Path], None]]] = [
        (
            "a run that wrote no answer file at all",
            _writing(
                _missing_answer_edit_target(key),
                "read the change under review, reported no findings\n",
            ),
        ),
        ("an empty answer file", _writing(key.answer_path, "")),
        (
            "a malformed answer file",
            _writing(key.answer_path, "the overtime one, and the rest gap\n"),
        ),
    ]
    registered = [
        answer for planted in key.accepted for answer in planted.any
    ] + list(key.rejected)
    for index, locations in enumerate(alternatives):
        finding = primaries[index]
        others = primaries[:index] + primaries[index + 1 :]
        negatives.append((
            f"every planted finding but {finding}",
            _writing(key.answer_path, _findings_payload(others)),
        ))
        for file in dict.fromkeys(named for named, _ in locations):
            near_miss = _symbol_the_key_does_not_name(task, file, registered)
            if near_miss is None:
                problems.append(
                    f"{task.id}: no near-miss can be constructed for the planted "
                    f"finding {finding} in {file} — every symbol {file} defines "
                    "is itself one of this key's alternatives or rejected, so "
                    "the negative that kills a comparison reading the file and "
                    "not the symbol cannot be run there. Plant it in a file that "
                    "holds somewhere else the reviewer could plausibly have "
                    "pointed"
                )
                continue
            missed = (file, near_miss)
            negatives.append((
                f"the planted finding {finding} reported as {missed}, a symbol "
                "of the same file the key registers on neither side",
                _writing(
                    key.answer_path,
                    _findings_payload(
                        primaries[:index] + [missed] + primaries[index + 1 :]
                    ),
                ),
            ))
    for answer in key.rejected:
        rejected = (answer.file, answer.symbol)
        negatives.append((
            f"every planted finding, and the rejected finding {rejected} "
            "reported beside them",
            _writing(key.answer_path, _findings_payload([*primaries, rejected])),
        ))
        negatives.append((
            f"the rejected finding {rejected}, on its own",
            _writing(key.answer_path, _findings_payload([rejected])),
        ))
    for description, edit in negatives:
        if grade(task, _negative_diff(task, edit), timeout_s=timeout_s):
            problems.append(
                f"{task.id}: {description} grades resolved — the grading test "
                "does not tell a review of this change from an answer that "
                "reviewed nothing, so a verdict on this task would measure "
                "whether the agent wrote a file rather than what it found in "
                "the change"
            )
    # Keyed on the answer file's bytes, so that "every finding at its primary" —
    # which every finding's first alternative produces — is run once rather than
    # once per finding.
    positives: dict[str, str] = {}
    for index, locations in enumerate(alternatives):
        for alternative in locations:
            reported = primaries[:index] + [alternative] + primaries[index + 1 :]
            positives.setdefault(
                _findings_payload(reported),
                f"the planted finding {primaries[index]} reported at its "
                f"alternative {alternative}, the others at their primary",
            )
    for payload, description in positives.items():
        # `_negative_diff` builds the diff, not the verdict: it is the live
        # runner's own capture of a workdir one edit was made in, which is what
        # a positive has to travel through as much as a negative does.
        diff = _negative_diff(task, _writing(key.answer_path, payload))
        if not grade(task, diff, timeout_s=timeout_s):
            problems.append(
                f"{task.id}: {description} grades unresolved — every alternative "
                "of a planted finding is a location the author wrote down as a "
                "legitimately correct description of that defect, so an answer "
                "reporting it there has to resolve. One that does not is not a "
                "mitigation for the assumption this grading rests on, only a "
                "line in the key that reads like one"
            )
    return problems


def _findings_payload(findings: Sequence[tuple[str, str]]) -> str:
    """One review answer file's contents: a list with one object per finding,
    shaped the way a review task's prompt asks for."""
    return (
        json.dumps(
            [{"file": file, "symbol": symbol} for file, symbol in findings], indent=2
        )
        + "\n"
    )


# --- the existence proof: that the planted truth is there at all ---------------
#
# Every gate above asks whether a task's grading *discriminates*: whether the
# held-out test can tell a correct answer from a wrong one. None of them asks
# the prior question — whether there is anything to find. A key naming a
# location no defect lives at, a review whose "planted" findings are correct
# code, a question about behaviour the repository does not have: each of those
# lints clean under everything above and grades every agent unresolved for a
# reason that says nothing about the agent.
#
# Round 4 answered it for `fault-location` by convention: the locate member was
# authored beside a `bug-fix` partner whose held-out tests fail on the same
# pristine repository, and that failure is the defect's existence proof. The
# convention named its own trigger to revisit — the first fault-location-style
# task with no partner — and round 5 authors exactly that, so it is a rule here,
# with a registry of proof forms per action that the lint reads.
#
# What the registry buys is that a fourth keyed action cannot be added without
# saying what would prove its truth exists: an action carrying a key and
# registering no form is refused, rather than inheriting silence.

# The action whose held-out tests are a `fault-location` task's existence proof.
# Named apart so the refusal can say which action it went looking for.
_PARTNER_CATEGORY: TaskCategory = "bug-fix"


class ExistenceProof(NamedTuple):
    """One action's registered proof form: what says its planted truth exists.

    `form` states in one line what the proof is, so that the registry reads as
    the rules it is rather than as a list of function names — the refusals
    themselves are written where each check is, in the terms that check failed
    in. `check` runs it, and is handed the whole task set because one of the
    forms is a relation between two tasks rather than a property of one.
    """

    form: str
    check: Callable[[Task, Sequence[Task], int], list[str]]


def _partner_pristine_failure(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """`fault-location`'s proof form: the partner `bug-fix` task exists, and its
    held-out tests fail on the starting repository the two share.

    Partner discovery is by shared starting-repository *bytes*, and has to be:
    the two members are deliberately neither a task family nor a pair — both
    constructs require one varied knob and an agreed category, and a locate/fix
    contrast varies no knob and differs in category — so there is no declared
    link to read. What there is instead is the thing the contrast is built on,
    that the two start from one repository byte for byte, which `_tree_bytes`
    already compares for a family.

    The partner's failure is run rather than taken from its own must-fail-on-
    pristine check, because the proof is a property of *this* task: the partner
    is graded on its own repository, which the byte comparison above has just
    established is this one. A set holding several partners is proved by the
    first of them, the rest being tasks of the set in their own right and held
    to the same invariant anyway.
    """
    pristine = _tree_bytes(task.repo_dir)
    partners = sorted(
        (
            other
            for other in tasks
            if other.id != task.id
            and other.category == _PARTNER_CATEGORY
            and _tree_bytes(other.repo_dir) == pristine
        ),
        key=lambda other: other.id,
    )
    if not partners:
        return [(
            f"{task.id}: no {_PARTNER_CATEGORY} task in the set starts from this "
            f"task's {REPO_DIR}/ byte for byte, so nothing proves there is a "
            "defect here to find. Everything else the lint runs on a keyed task "
            "asks whether its grading tells a right answer from a wrong one; "
            "this asks the prior question, and a locate task authored alone has "
            "no answer to it — a key naming a location no defect lives at lints "
            "clean under every other rule and grades every agent unresolved. "
            f"Author the partner beside it, sharing {REPO_DIR}/ byte for byte"
        )]
    partner = partners[0]
    if grade(partner, "", timeout_s=timeout_s):
        return [(
            f"{task.id}: its existence proof is {partner.id}, whose held-out "
            "tests pass on the starting repository the two share — so the "
            "repository has nothing wrong with it, and this task asks where a "
            "defect lives that its own partner cannot demonstrate. The proof is "
            "the partner's pristine *failure*: fix the partner's tests, or the "
            "defect the two were built around"
        )]
    return []


def _proof_test_per_planted_finding(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """`code-review`'s proof form: per planted finding, a held-out test that
    fails on the starting repository and passes on the author's corrected tree.

    A review task's `repo/` ships the change under review already applied, so
    "the finding is really a defect" is exactly "this test fails here and passes
    once the author's correction is in". Both directions are required and for
    different reasons: a proof test that passes on the starting repository
    proves nothing was wrong, and one that fails on the corrected tree proves
    the author's own correction does not fix what the finding claims — a finding
    the verdict would then demand of every agent while the task's own author
    could not satisfy it.

    One proof per **finding**, not per alternative: a finding is one defect
    however many locations legitimately describe it, and a second proof for the
    class enclosing the defective method would demonstrate the same failure
    twice. Every message names the finding by its **primary** alternative, the
    way `proof_test_name` names the file, because a review plants several and
    "a proof test failed" would leave the author to work out which.

    Nothing here is ever run by grading. The proofs sit outside `grading/`,
    which the loader enforces (`_held_out_of_the_workdir_but_not_of_grading`),
    so they are neither overlaid into a workdir nor collected as verdict tests.
    """
    del tasks  # a review task's proof is a property of the task alone
    key = findings_key(task)
    if not task.corrected_dir.is_dir() or not any(task.corrected_dir.iterdir()):
        return [(
            f"{task.id}: {CORRECTED_DIR}/ is missing or empty — the corrected "
            "tree is the repository with every planted finding put right, and it "
            "is the half of each finding's existence proof that says the finding "
            "is a defect rather than a preference. Without it nothing can be "
            "shown to have been fixed"
        )]
    problems: list[str] = []
    proved: dict[str, tuple[str, str]] = {}
    for finding in key.accepted:
        planted = (finding.primary.file, finding.primary.symbol)
        name = proof_test_name(finding, task.runner)
        if name in proved:
            problems.append(
                f"{task.id}: the planted findings {proved[name]} and {planted} "
                f"are both proved by {PROOFS_DIR}/{name} — a proof test is named "
                "after the finding it proves, so two findings sharing a name "
                "leaves one of them with no proof of its own. Rename one of the "
                "symbols, or plant them in different files"
            )
            continue
        proved[name] = planted
        proof = task.proofs_dir / name
        if not proof.is_file():
            problems.append(
                f"{task.id}: the planted finding {planted} has no existence "
                f"proof — {PROOFS_DIR}/{name} is missing. Each planted finding "
                "carries a held-out test that fails on the starting repository "
                "and passes on the corrected tree, because a 'finding' nothing "
                "demonstrates is a preference the verdict would grade every "
                "agent against"
            )
            continue
        if _proof_test_passes(
            task.repo_dir, proof, runner=task.runner, timeout_s=timeout_s
        ):
            problems.append(
                f"{task.id}: the existence proof of the planted finding "
                f"{planted} ({PROOFS_DIR}/{name}) passes on the starting "
                "repository — the change under review ships applied there, so a "
                "proof that passes shows the finding is not a defect at all, and "
                "the verdict would fail every agent that declined to report it"
            )
        if not _proof_test_passes(
            task.corrected_dir, proof, runner=task.runner, timeout_s=timeout_s
        ):
            problems.append(
                f"{task.id}: the existence proof of the planted finding "
                f"{planted} ({PROOFS_DIR}/{name}) fails on the corrected tree — "
                f"so {CORRECTED_DIR}/ does not in fact put this finding right, "
                "and what the proof demonstrates is a defect the author has not "
                "shown how to fix rather than one the change introduced"
            )
    return problems


def _accepted_locations_resolve(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """The locate-style half of `codebase-comprehension`'s proof form, and the
    whole of it for a task keyed on accepted answers: every accepted (file,
    symbol) resolves in the starting repository. Which half a task takes is
    `_the_comprehension_proof_the_key_on_disk_asks_for`'s.

    The one form that runs nothing, and the one that was already a rule before
    this registry existed — `_answer_key_problems` reads it over both halves of
    every accepted-answer key. It is registered here anyway, and deliberately as
    the very same check rather than a second copy of it: what the registry is
    for is that a keyed action cannot be added without saying what proves its
    truth exists, and an action whose answer is "the rule you already run" has
    to say so rather than be silently exempt.

    Why this is the whole of it for a locate-style comprehension task: there is
    no defect behind it, so there is nothing a partner could fail on. What has
    to exist is the behaviour the question asks after, and a location that
    resolves in the repository the agent is handed is that.
    """
    del tasks, timeout_s  # a location resolving is a property of one task, read
    return _key_location_problems(
        task, "the accepted-answer key's accepted answers", answer_key(task).accepted
    )


def _reference_suite_kills_every_mutant(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """`test-authoring`'s proof form: the author's reference suite passes on the
    pristine starting repository and fails on every planted mutant, checked one
    mutant at a time (design note §67.5).

    The task's own verdict, run against the author instead of against an agent —
    a task's reference solution has always been the author being their task's
    first perfect agent, and here that solution is a suite. What it proves is
    the prior question no other gate asks: that each planted mutant is killable
    at all. The failure it exists to refuse is the *equivalent mutant*, a change
    no behaviour distinguishes, which under the gate's universal quantifier
    makes the task permanently unresolvable for every agent while looking merely
    hard.

    **Per mutant, never over the set.** A set-level check — "the suite fails
    somewhere across the mutants" — is exactly where an equivalent mutant hides,
    because one killable neighbour would carry it. Each report names the mutant
    file for the same reason a review's proof names its finding: "a proof
    failed" leaves the author to work out which.

    A suite that fails on the pristine repository is reported alone and stops
    the per-mutant work: every mutant would then "fail" for that reason rather
    than for the mutation, so the per-mutant reports would be noise laid over
    the one real problem — and this is the expensive half of linting one of
    these tasks, a whole suite run once per mutant.
    """
    del tasks  # a suite killing this task's mutants is a property of one task
    targets = _reference_suite_targets(task)
    if not targets:
        return [(
            f"{task.id}: {PROOFS_DIR}/ holds no file this task's runner would "
            f"collect as a test ({task.runner.grading_test_glob}) — the author's "
            "reference suite is this action's existence proof, and without a "
            "test in it nothing says the planted mutants can be killed by "
            "anything at all"
        )]
    if not _reference_suite_passes(task, None, targets=targets, timeout_s=timeout_s):
        return [(
            f"{task.id}: the reference suite in {PROOFS_DIR}/ fails on the "
            f"pristine {REPO_DIR}/ — the first gate of this task's own verdict "
            "is that the agent's suite passes on the starting repository with no "
            "exception, so a reference suite that cannot do it either is either "
            "wrong about the specification or reading a repository that does not "
            "match the prompt. Nothing about the mutants is judged until this "
            "passes"
        )]
    return [
        (
            f"{task.id}: the planted mutant {MUTANTS_DIR}/{patch.name} survives "
            f"the reference suite in {PROOFS_DIR}/ — no test tells that mutation "
            "from the original, so as far as anything here can show it is an "
            "*equivalent mutant*, a change no behaviour distinguishes. The "
            "verdict demands every mutant be killed, so this one would make the "
            "task unresolvable for every agent and read as a hard task. Plant a "
            "change the specification's own behaviour rules out, or add the test "
            "that catches this one"
        )
        for patch in mutant_patches(task)
        if _reference_suite_passes(task, patch, targets=targets, timeout_s=timeout_s)
    ]


def _reference_suite_targets(task: Task) -> list[str]:
    """The reference suite's test files, as paths relative to `proofs/`.

    Found by the runner's own held-out-test glob at any depth, the way
    `proof_test_name` names a single-file proof by that same glob: a proof is a
    test of the task's own language, and a suite is that plural. Anything else
    in `proofs/` — a helper module, a README — travels with it and is simply not
    a target.
    """
    return sorted(
        str(path.relative_to(task.proofs_dir))
        for path in task.proofs_dir.rglob(task.runner.grading_test_glob)
        if path.is_file()
    )


def _reference_suite_passes(
    task: Task, mutant: Path | None, *, targets: Sequence[str], timeout_s: int
) -> bool:
    """Whether the author's reference suite passes on one copy of the starting
    repository — pristine, or carrying one planted mutant.

    Built the way `_proof_test_passes` builds its own and for the same reasons:
    the tree is copied rather than run in place, the proof laid beside it, the
    run going through the runner with its report written outside the workdir.
    The two differences are this form's: the whole suite is the targets rather
    than one file, and one copy carries a mutation.

    Both copies are `git init`-ed, including the pristine one that has nothing to
    apply. The two runs must differ in the mutation and in nothing else — a
    repository root present in one and absent in the other is exactly the kind of
    difference a test runner notices — so the tree is built identically and then
    mutated.
    """
    task.runner.require_toolchain()
    with tempfile.TemporaryDirectory(prefix="ai-bench-reference-") as name:
        root = Path(name)
        workdir = root / "workdir"
        workdir.mkdir()
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        _git(task, ["init", "-q", "."], workdir, doing="preparing a proof copy")
        if mutant is not None:
            _apply_mutant(task, mutant, workdir)
        shutil.copytree(task.proofs_dir, workdir, dirs_exist_ok=True)
        return task.runner.run_tests(root, workdir, list(targets), timeout_s=timeout_s)


# --- investigation: the two-sided proof, archived and checked offline ----------


class ProofSide(NamedTuple):
    """One half of a point-keyed task's existence proof: an answer the author
    wrote, the rulings the grader gave it, and what the point gate has to say
    about it.

    Two sides rather than one because the proof runs in both directions
    (§76.10). The positive half is `_reference_suite_kills_every_mutant`'s own
    move, mapped onto prose — the author as their task's first perfect agent,
    refusing the *unmeetable point*, the equivalent mutant's analog. The
    negative half is what the mapping exposes and the mutation gate got for
    free: a suite is proved to discriminate by the mutants dying, and nothing
    corresponds to that here unless the author also writes an answer that must
    fail. Without it an always-covered grader passes every positive proof.

    Held as data rather than as two code paths so that the writer that takes
    the proof and the lint that reads it back walk one list: a third side, or a
    renamed file, moves both at once or neither.
    """

    name: str
    answer_file: str
    rulings_file: str
    # What `_point_verdict` must come out as, computed from this side's
    # archived rulings against this side's own answer.
    resolves: bool


PROOF_SIDES: tuple[ProofSide, ...] = (
    ProofSide("reference answer", REFERENCE_ANSWER_FILE, "reference.json", True),
    ProofSide("foil answer", FOIL_ANSWER_FILE, "foil.json", False),
)


def points_key_sha256(key: PointsKey) -> str:
    """The hash a proof archive records its key by.

    Taken over the key's canonical JSON rather than over the file's bytes, so
    that re-indenting the key or reordering nothing costs a paid re-proof while
    every change to what the key *asks* does. Public because the writer stamps
    it and the lint recomputes it, and a second implementation of "what counts
    as an edit" would be the one place this mechanism could quietly stop
    triggering.
    """
    return _sha256(json.dumps(key.model_dump(mode="json"), sort_keys=True))


def proof_rulings_file(task: Task, side: ProofSide) -> Path:
    """Where one side's rulings are archived, inside the task's proofs
    subtree — the standing address of an existence proof, never overlaid, never
    collected, never read by a verdict."""
    return task.proofs_dir / PROOF_RULINGS_DIR / side.rulings_file


def _the_reference_resolves_and_the_foil_fails(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """`investigation`'s proof form: the author's reference answer resolves
    under the point gate, per point, and the foil answer fails it — read from
    the archived rulings and never re-asked (design note §76.10).

    **This check is offline.** It calls no grader, opens no client and needs no
    key: the rulings were taken by `ai-bench prove-points-v1` at authoring
    time, and everything here is a recomputation over them. That is the
    property the whole command rests on — `ai-bench lint-v1` never calls the
    LLM — and it is why the affordance that *can* reach the network is a
    subcommand beside the lint rather than a flag inside it.

    What it holds each side to, in the order a failure is worth reading in:

    - the author's answer is there and says something;
    - its rulings are archived, are this shape, and answer **exactly** the
      questions this key asks — every planted point and every disqualifier,
      and nothing the key does not name, because a ruling about a question that
      is no longer in the key is a ruling about a task that no longer exists;
    - the archive was taken under the pinned `GRADER_VERSION`, against this
      answer's bytes, and against this key. The three hashes are the whole of
      "re-proof triggers on edit, not on every lint run": edit the points,
      either answer, or bump the instrument, and this refuses until the proof
      is re-run;
    - and only then the verdict, `_point_verdict` over the archived rulings —
      the very function a run's verdict is computed by, so what the proof
      proves is the computation the sweep will perform and not a re-statement
      of it. Every span is re-checked against the answer's own bytes here, as
      it is there.

    A side whose archive is stale or incomplete is reported and its verdict is
    not computed: a verdict over rulings taken against some other text is not a
    weaker claim, it is a claim about something else.
    """
    del tasks, timeout_s  # a proof read from an archive runs nothing
    key = points_key(task)
    questions = _point_questions(key)
    return [
        problem
        for side in PROOF_SIDES
        for problem in _one_proof_side_problems(task, key, questions, side)
    ]


def _one_proof_side_problems(
    task: Task,
    key: PointsKey,
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
    side: ProofSide,
) -> list[str]:
    """One half of the two-sided proof, checked against what is on disk."""
    answer_path = task.proofs_dir / side.answer_file
    try:
        answer = answer_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [(
            f"{task.id}: the author's {side.name} is missing or unreadable at "
            f"{PROOFS_DIR}/{side.answer_file} ({error}) — this action's "
            "existence proof runs in both directions, and the two answers are "
            "what it runs on: the reference answer says every planted point "
            "can be covered at all, and the foil says the key can tell a "
            "plausible wrong answer from a right one"
        )]
    if not answer.strip():
        return [(
            f"{task.id}: the author's {side.name} at {PROOFS_DIR}/"
            f"{side.answer_file} is empty — the point gate rules an empty "
            "deliverable unresolved without a single grader call, so an empty "
            "answer proves nothing in either direction"
        )]
    archive, unreadable = _archived_proof(task, side)
    if archive is None:
        return [unreadable]
    problems = _stale_proof_problems(task, key, questions, answer, side, archive)
    if problems:
        return problems
    resolved = _point_verdict(questions, archive, answer)
    if resolved == side.resolves:
        return []
    if side.resolves:
        uncovered, present = _what_the_gate_held_against(questions, archive, answer)
        return [(
            f"{task.id}: the author's reference answer does not resolve under "
            f"the point gate — {_and_what_it_held(uncovered, present)}. A point "
            "the author's own answer cannot cover is the *unmeetable point*, "
            "the equivalent mutant's analog: it makes the task unresolvable "
            "for every agent while reading as merely a hard one. Re-word the "
            "point, or argue it in the reference answer, and re-run "
            "`ai-bench prove-points-v1`"
        )]
    return [(
        f"{task.id}: the author's foil answer resolves under the point gate — "
        "the foil is the plausible-but-wrong answer this key has to tell from "
        "a right one, so a foil that resolves says the key does not "
        "discriminate. Calibration proves the instrument discriminates in "
        "general; this half proves *this key* does, and without it an "
        "always-covered grader passes every positive proof. Plant the "
        "load-bearing point the foil misses, or write a foil that misses one, "
        "and re-run `ai-bench prove-points-v1`"
    )]


def _archived_proof(task: Task, side: ProofSide) -> tuple[ProofRulings | None, str]:
    """One side's archived rulings, or None and what is wrong with them.

    Reported rather than raised, unlike a *run*'s archive: a broken run archive
    is a measurement nobody can recompute and fails the whole replay loudly,
    while a broken proof archive is an authoring defect like any other and
    belongs in the list the lint prints beside the rest of them.
    """
    path = proof_rulings_file(task, side)
    where = f"{PROOFS_DIR}/{PROOF_RULINGS_DIR}/{side.rulings_file}"
    if not path.is_file():
        return None, (
            f"{task.id}: the author's {side.name} has no archived rulings — "
            f"{where} is missing. The lint checks this action's existence "
            "proof by reading the rulings the grader gave the two answers at "
            "authoring time and never by asking the grader itself, so an "
            "unproved task is one the lint cannot pass rather than one it "
            "would prove for you. Run `ai-bench prove-points-v1`"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        return None, f"{task.id}: {where} is unreadable ({error})"
    except json.JSONDecodeError as error:
        return None, f"{task.id}: {where} is not JSON ({error})"
    try:
        return ProofRulings.model_validate(raw), ""
    except ValidationError as error:
        return None, f"{task.id}: {where}: {error}"


def _stale_proof_problems(
    task: Task,
    key: PointsKey,
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
    answer: str,
    side: ProofSide,
    archive: ProofRulings,
) -> list[str]:
    """Everything that makes an archive rulings about some other measurement:
    a retired instrument, an edited answer, an edited key, or a set of
    questions that is not this key's.

    Every one of them is reported in the same shape and for the same reason —
    the proof is out of date and has to be taken again — but each is named
    apart, because which of the four moved is the whole of what an author needs
    to know to decide whether re-running the proof is all that is owed.
    """
    where = f"{PROOFS_DIR}/{PROOF_RULINGS_DIR}/{side.rulings_file}"
    problems: list[str] = []
    if archive.grader_version != point_grader.GRADER_VERSION:
        problems.append(
            f"{task.id}: {where} was taken under grader "
            f"{archive.grader_version!r} and the pinned instrument is now "
            f"{point_grader.GRADER_VERSION!r} — the grader is a versioned "
            "instrument (model id + prompt hash), and a version change is an "
            "edit like any other: what the retired instrument said about this "
            "answer is not what the pinned one would say. Re-run "
            "`ai-bench prove-points-v1`"
        )
    if archive.answer_sha256 != _sha256(answer):
        problems.append(
            f"{task.id}: {where} was taken against a different {side.name} "
            f"than {PROOFS_DIR}/{side.answer_file} now holds — the answer has "
            "been edited since it was proved, so the archived rulings are "
            "about text nobody will ever be graded against. Re-run "
            "`ai-bench prove-points-v1`"
        )
    if archive.points_key_sha256 != points_key_sha256(key):
        problems.append(
            f"{task.id}: {where} was taken against a different "
            f"{GRADING_DIR}/{POINTS_KEY_FILE} than this task now ships — the "
            "key has been edited since it was proved, and a proof of the "
            "questions it used to ask says nothing about the ones it asks now. "
            "Re-run `ai-bench prove-points-v1`"
        )
    asked = {(kind, planted.id) for kind, planted in questions}
    ruled = {(entry.kind, entry.point_id) for entry in archive.rulings}
    if missing := sorted(f"{kind} {point_id!r}" for kind, point_id in asked - ruled):
        problems.append(
            f"{task.id}: {where} does not rule on {missing} — the proof is "
            "read per planted point, never over the set, because a set-level "
            "reading is exactly where the point no answer could cover hides "
            "behind its coverable neighbours. Every point and every "
            "disqualifier this key names is proved, or the task is not proved"
        )
    if extra := sorted(f"{kind} {point_id!r}" for kind, point_id in ruled - asked):
        problems.append(
            f"{task.id}: {where} rules on {extra}, which this key does not "
            "name — a ruling about a question that has been retired or renamed "
            "is a ruling about a task that no longer exists, and an archive "
            "holding one was taken before an edit nothing else here would "
            "catch. Re-run `ai-bench prove-points-v1`"
        )
    return problems


def _what_the_gate_held_against(
    questions: tuple[tuple[PointKind, PlantedPoint], ...],
    archive: ProofRulings,
    answer: str,
) -> tuple[list[str], list[str]]:
    """Which planted points this answer failed to cover, and which
    disqualifiers it made — the same computation `_point_verdict` performs,
    reported instead of reduced to a boolean.

    Only reached once the verdict has already come out wrong, so that the
    verdict itself stays the one function a run is graded by and this is the
    explaining of it, not a second implementation with its own opinion.
    """
    by_question = {(entry.kind, entry.point_id): entry for entry in archive.rulings}
    uncovered, present = [], []
    for kind, planted in questions:
        entry = by_question[(kind, planted.id)]
        if _the_span_holds(entry.covered, entry.span, answer):
            if kind == "disqualifier":
                present.append(planted.id)
        elif kind == "point":
            uncovered.append(planted.id)
    return uncovered, present


def _and_what_it_held(uncovered: list[str], present: list[str]) -> str:
    """The reference answer's failure, said in the terms of whichever half it
    failed on. A covered ruling whose span the answer does not contain counts
    as uncovered here exactly as it does in the verdict, so "not covered" means
    "not covered by a ruling this gate could stand behind"."""
    said = []
    if uncovered:
        said.append(
            f"the planted point(s) {uncovered} are not covered by a ruling "
            "quoting a span the answer contains"
        )
    if present:
        said.append(f"the disqualifier(s) {present} are present in it")
    return ", and ".join(said)


def _tasks_to_prove(
    tasks: Sequence[Task], select: Sequence[str] | None
) -> list[Task]:
    """Which tasks this invocation proves: every point-keyed one by default,
    or exactly the ones `--task` names.

    **Why selection exists at all.** The writer has no resume and never had
    one — it re-asks whatever it is pointed at, every point and every
    disqualifier, both sides, every invocation — so pointing it at the whole
    corpus re-asks, and re-pays for, every archive already taken (§96). A
    round proving its tasks one ticket at a time therefore names them, and the
    default is left exactly as it was for the corpus-wide proof run that
    wanted it.

    Both refusals are raised here, before the caller's factory is reached, so
    that a mistyped id costs nothing: an id naming no task in the set, and an
    id naming a task that ships no points key and so has no existence proof to
    take.

    Corpus order, not flag order — `eval-v1 --task`'s own reason: two
    operators naming the same ids in different orders prove the same sequence.
    """
    keyed = [task for task in tasks if is_point_keyed(task)]
    if select is None:
        return keyed
    wanted = set(select)
    if unknown := sorted(wanted - {task.id for task in tasks}):
        raise IngestError(
            f"--task names unknown task id(s) {unknown} — no task of that id "
            "is in the task set, and nothing was proved"
        )
    if unkeyed := sorted(wanted - {task.id for task in keyed}):
        raise IngestError(
            f"--task names task(s) {unkeyed} that ship no {POINTS_KEY_FILE} — "
            "only a point-keyed task has a two-sided existence proof to take, "
            "and nothing was proved"
        )
    return [task for task in keyed if task.id in wanted]


def prove_points(
    tasks: Sequence[Task],
    grader_factory: Callable[[], point_grader.PointGrader],
    select: Sequence[str] | None = None,
) -> list[Path]:
    """Take each selected point-keyed task's two-sided existence proof, live,
    and archive it: one grader call per planted point and per disqualifier
    against the author's reference answer, and again against the foil.

    **The one affordance in this project that calls the grader outside a run,
    and the reason it is a command of its own.** `ai-bench lint-v1` never calls
    the LLM — that is what the spec and the glossary both rest on, and a
    property worth having of the whole command rather than of its default
    flags — so the writer lives beside the lint and not inside it. What the
    lint then does with what this wrote is `_the_reference_resolves_and_the_
    foil_fails`, offline.

    **There is no resume here and there never was one.** Every task this is
    pointed at is re-asked in full and its archive rewritten, whatever is
    already on disk; `select` — `--task`, repeatable — is how an invocation is
    kept to the tasks whose proofs it means to pay for (`_tasks_to_prove`,
    §96). `None` means the standing every-point-keyed-task behaviour.

    `DEEPSEEK_API_KEY` has to be exported in the invoking shell: the factory
    constructs a live client, so a proof run without it fails at auth
    resolution rather than at the bar.

    The grader is built once across every task and both sides rather than per
    call, and only if there is a point-keyed task to prove at all — so a corpus
    holding none constructs no client and needs no key, the way a sweep with no
    point-keyed row does.

    What is written is what the lint will hold it to: the rulings, the pinned
    grader version, and the hashes of the key and of the answer they were taken
    against. Nothing is checked here — a foil that resolves is archived exactly
    as one that does not, because the writer's job is to record what the
    instrument said and the lint's is to decide what it was worth. One reader
    of a verdict, not two.
    """
    grader: point_grader.PointGrader | None = None
    written: list[Path] = []
    for task in _tasks_to_prove(tasks, select):
        key = points_key(task)
        questions = _point_questions(key)
        for side in PROOF_SIDES:
            answer = _proof_answer(task, side)
            if grader is None:
                grader = grader_factory()
            fresh = _fresh_rulings(task, answer, questions, grader)
            path = proof_rulings_file(task, side)
            _write_rulings(
                task,
                path,
                ProofRulings(
                    grader_version=fresh.grader_version,
                    points_key_sha256=points_key_sha256(key),
                    answer_sha256=fresh.deliverable_sha256,
                    rulings=fresh.rulings,
                ),
            )
            written.append(path)
    return written


def _proof_answer(task: Task, side: ProofSide) -> str:
    """One side's answer, read for grading — refused loudly if it is not there
    or says nothing.

    Loudly, and before any call goes out, because this is the writer: the lint
    reports a missing answer as one authoring problem among many, but grading
    an answer that is not there would archive a proof of nothing and charge for
    it.
    """
    path = task.proofs_dir / side.answer_file
    try:
        answer = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise IngestError(
            f"{task.id}: the author's {side.name} is missing or unreadable at "
            f"{PROOFS_DIR}/{side.answer_file} ({error}) — both halves of this "
            "action's existence proof are written by the author before it can "
            "be taken"
        ) from error
    if not answer.strip():
        raise IngestError(
            f"{task.id}: the author's {side.name} at {PROOFS_DIR}/"
            f"{side.answer_file} is empty — there is nothing to grade, and an "
            "archive taken over it would prove nothing in either direction"
        )
    return answer


# The proof both point-keyed actions take, registered under both their keys as
# one object rather than copied: §94.2 rules the key's shape identical for
# `requirement-decomposition`, and the rule that reads it back
# (`_the_reference_resolves_and_the_foil_fails`) is deliberately shared, so a
# second value here could only ever drift from this one. Nothing in the form
# names an action, which is what makes the one object right rather than merely
# convenient.
_POINT_EXISTENCE_PROOF = ExistenceProof(
    form=(
        "the author's reference answer resolving under the point gate, per "
        "point, and the foil answer failing it, read from archived rulings"
    ),
    check=_the_reference_resolves_and_the_foil_fails,
)


def _the_comprehension_proof_the_key_on_disk_asks_for(
    task: Task, tasks: Sequence[Task], timeout_s: int
) -> list[str]:
    """`codebase-comprehension`'s proof form, which of two it is being decided
    by the key the task ships (§106.5).

    The category carries two shapes of task and what proves each one's planted
    truth exists is not the same thing: a locate-style task's accepted
    locations have to resolve in the starting repository, and an explain-style
    one's reference answer has to resolve under the point gate per planted
    point with its foil failing. Neither proof means anything about the other
    shape — there are no accepted locations in a points key to resolve, and no
    archived rulings beside a locate-style task to read.

    **Why the dispatch is here and not in `_existence_proof_problems`.** That
    reader takes the whole registry as its one list of forms, and a second
    shape-aware lookup beside it would be a form nobody could find by reading
    `EXISTENCE_PROOFS` — while `_unregistered_proof_form_problems` refuses a
    keyed action the registry does not *name*, which is a rule about the keys
    of that dict and not about how many shapes one entry covers. So the
    category keeps exactly one entry, its `form` names both shapes, and the
    branch is this function: the registry stays the whole of what is
    registered, and the dispatch is read at the one address the registry
    points at.

    The point-keyed side is `investigation`'s registered check, called through
    the object it registers rather than copied, for the reason that object is
    shared in the first place: a second value could only ever drift from it.
    """
    if is_point_keyed(task):
        return _POINT_EXISTENCE_PROOF.check(task, tasks, timeout_s)
    return _accepted_locations_resolve(task, tasks, timeout_s)


# One entry per action that carries a key. A seventh cannot be added without
# one: `_unregistered_proof_form_problems` refuses a keyed action this dict does
# not name, and `_existence_proof_problems` refuses the task that would have
# been swept under it.
EXISTENCE_PROOFS: dict[TaskCategory, ExistenceProof] = {
    "fault-location": ExistenceProof(
        form=(
            f"the partner {_PARTNER_CATEGORY} task's held-out tests failing on "
            "the starting repository the two share"
        ),
        check=_partner_pristine_failure,
    ),
    "code-review": ExistenceProof(
        form=(
            "a held-out test per planted finding, failing on the starting "
            "repository and passing on the author's corrected tree"
        ),
        check=_proof_test_per_planted_finding,
    ),
    # One entry covering the category's two shapes, because one action gets one
    # entry: the locate-style form first, still readable as the whole sentence
    # it was, then the point-keyed form quoted off `investigation`'s own
    # registration rather than restated, so the two cannot come to differ.
    _POINT_OPTIONAL_CATEGORY: ExistenceProof(
        form=(
            "for a locate-style task, every accepted (file, symbol) resolving "
            "in the starting repository; for a point-keyed one, "
            f"{_POINT_EXISTENCE_PROOF.form}"
        ),
        check=_the_comprehension_proof_the_key_on_disk_asks_for,
    ),
    _MUTATION_CATEGORY: ExistenceProof(
        form=(
            "the author's reference suite passing on the pristine starting "
            "repository and failing on every planted mutant, checked per mutant"
        ),
        check=_reference_suite_kills_every_mutant,
    ),
    "investigation": _POINT_EXISTENCE_PROOF,
    "requirement-decomposition": _POINT_EXISTENCE_PROOF,
}

# What a proof test may not be named after: the characters a finding's file and
# symbol carry that a module name cannot. Collapsed to underscores rather than
# dropped, so `Rota.add` and `Rotaadd` cannot name one file.
_NOT_IN_A_MODULE_NAME = re.compile(r"[^0-9A-Za-z]+")


def proof_test_name(finding: PlantedFinding, runner: LanguageRunner) -> str:
    """The proof test a planted finding is proved by, by name.

    Derived from the finding rather than declared in the key, so that a proof
    test and the finding it proves cannot drift apart: there is no third place
    saying which is which. Case is kept, because the key's symbols are matched
    case-exactly and lowercasing here would let two findings that differ only in
    case claim one proof — which `_proof_test_per_planted_finding` reports
    rather than lets pass, for the residual case two spellings still collide.

    Named after the **primary** alternative and no other. A finding is one
    defect however many locations legitimately describe it, so it owes one
    proof, not one per alternative; and naming it after the most specific
    location is what keeps a proof file's name readable as the thing it
    demonstrates. Adding an alternative to a finding therefore renames nothing.

    What kind of file that name is is the runner's, and is the very glob its
    held-out tests are found by (responsibility 3) with the finding's name in
    place of the `*`: a proof test is a test of the task's own language — the
    lint runs it through that runner against two trees — so `test_x.py` under
    pytest and `x.test.ts` under `node --test` are one rule read twice, and a
    `.py` proof beside a TypeScript task would be a file its runner could not
    run at all.
    """
    primary = finding.primary
    slug = _NOT_IN_A_MODULE_NAME.sub("_", f"{primary.file}_{primary.symbol}")
    return runner.grading_test_glob.replace("*", slug.strip("_"))


def _proof_test_passes(
    tree: Path, proof: Path, *, runner: LanguageRunner, timeout_s: int
) -> bool:
    """Whether this proof test passes when run against this tree.

    The tree is copied rather than run in place and the proof laid beside it,
    the way grading copies the starting repository and overlays the held-out
    files — same invocation, same isolation, same report read from outside the
    workdir, because it goes through the same seam `_run_grading` does. The
    proof is run alone: what it says about one planted finding must not depend
    on another proof test in the same session.

    The runner is passed rather than assumed: this function is handed a bare
    tree — a task's `repo/` or its `corrected/` — and there is nothing in a
    path to say what grades it, so the caller carries the task's declaration
    down. Defaulting to Python here is exactly the path that would grade a
    task with the wrong mechanism.
    """
    runner.require_toolchain()
    with tempfile.TemporaryDirectory(prefix="ai-bench-proof-") as name:
        root = Path(name)
        workdir = root / "workdir"
        workdir.mkdir()
        shutil.copytree(tree, workdir, dirs_exist_ok=True)
        shutil.copyfile(proof, workdir / proof.name)
        return runner.run_tests(root, workdir, [proof.name], timeout_s=timeout_s)


def _unregistered_proof_form_problems() -> list[str]:
    """Keyed actions this project can grade and cannot prove.

    Read off the sets that say which actions may ship a key of some shape — an
    accepted-answer key, a findings key, a planted mutant set, a points key —
    so that adding another without registering what proves its truth exists is
    refused by the lint rather than discovered by a sweep that measured
    nothing. The mutation and point actions are counted here for exactly that
    reason: their mutants and their planted points are keys like the others,
    and an action left out of this union would go unnoticed by the one check
    whose whole job is noticing.
    """
    unregistered = sorted(
        (
            _KEYED_CATEGORIES
            | {_FINDINGS_CATEGORY, _MUTATION_CATEGORY}
            | _POINT_CATEGORIES
        )
        - set(EXISTENCE_PROOFS)
    )
    if not unregistered:
        return []
    return [(
        f"the action(s) {unregistered} carry a key and register no existence "
        "proof — every gate the lint runs on a keyed task asks whether its "
        "grading tells a right answer from a wrong one, and none of them asks "
        "whether there is anything to find. Register the form that answers it "
        "in EXISTENCE_PROOFS, beside "
        f"{sorted(EXISTENCE_PROOFS)}"
    )]


def _existence_proof_problems(
    task: Task, tasks: Sequence[Task], *, timeout_s: int
) -> list[str]:
    """Whether this keyed task's planted truth is shown to be there at all.

    Dispatched off the registry rather than off a chain of category tests, so
    that the forms are one list a reader can see the whole of, and so that
    a task of an action with no registered form is refused here rather than
    passing through a final `else` that checked nothing.
    """
    proof = EXISTENCE_PROOFS.get(task.category)
    if proof is None:
        return [(
            f"{task.id}: a {task.category} task carries a key, and that action "
            "registers no existence proof — so nothing says the truth this task "
            "is keyed on is in the repository at all, and the task would grade "
            "every agent against a claim no mechanism ever checked"
        )]
    return proof.check(task, tasks, timeout_s)


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
    rulings: Path = DEFAULT_RULINGS_DIR,
    grader_factory: Callable[[], point_grader.PointGrader] | None = None,
) -> list[Record]:
    """Grade each run's diff by execution and emit first-party records.

    Runs for unknown tasks and duplicate runs fail loudly — either would
    otherwise vanish or overwrite silently at merge time.

    The last two arguments reach the point gate and nothing else, and both have
    a default so that a caller with no point-keyed row in its log never has to
    know they exist. `rulings` is the archive a point-keyed row's per-point
    rulings are read back from — defaulted rather than required because this
    function's other production callers (`reconcile_v1.observed_outcomes`, and
    `calibrate-v1` through it) thread no such argument and replay every logged
    row at the end of every sweep. `grader_factory` is the live seam: passed on
    `--live`, absent on `--replay`, and called only where a ruling is missing,
    so a replay never constructs a client and a sweep with no point-keyed task
    never reaches for a key.
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
        resolved = grade(
            task,
            run.diff,
            timeout_s=timeout_s,
            rulings_path=rulings_file(rulings, run.task_id, run.agent, run.model),
            grader_factory=grader_factory,
        )
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
#
# `node_modules/` is here for a different reason than the cache patterns
# above: it is the stdlib-only rule's consequence for the agent rather than
# for a task's author. A TypeScript starting repository ships nothing to
# install, so a package the agent installs mid-run is neither committed to
# the pristine baseline nor captured in the workdir diff — and at grade time
# the module is not there, so a held-out test importing it fails. That is the
# rule working as designed, not a capture bug.
_WORKDIR_IGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\nnode_modules/\n"

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
#
# Round 5 (design note §46) registers `code-review` and `codebase-comprehension`
# the same way and for the same reason: both at 600, the flat default's own
# value, so registration is a considered commitment rather than an inherited
# convention and no cell of the round runs under a ceiling different from the
# one it would have had unregistered. No cross-round caveat arises against
# round 4.
LIVE_RUN_LIMITS_S: dict[TaskCategory, int] = {
    "bug-fix": 600,
    "fault-location": 600,
    "code-review": 600,
    "codebase-comprehension": 600,
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
    agent: str = DEFAULT_AGENT,
) -> list[Run]:
    """Run every task through one tools-enabled agent headless per model.

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

    Which agent runs is the caller's to say, by name: `agent` selects the
    registered adapter (`ai_benchmark.agents.ADAPTERS`) that drives the
    harness and parses its output, and an unregistered name — or a `--model`
    the named harness is not registered to drive — is refused before any
    workdir is prepared. Nothing else about the run is the adapter's —
    the fresh workdir, the pristine commit, the diff capture, the sweep id
    and the log append all stay here.

    How long each run gets is the one thing neither the caller nor the
    adapter may say: the limit comes from `LIVE_RUN_LIMITS_S`, keyed on the
    task's class, so that it is a property of the task rather than of the
    invocation, or the harness, that happened to run it.
    """
    if problem := _sweep_id_problem(sweep):
        raise IngestError(f"{problem} — {_SWEEP_ID_RULE}")
    adapter = adapter_for(agent)
    # Which combinations this harness is registered to run is settled here,
    # before the first workdir is prepared and before the first paid
    # invocation: a sweep named with a model its harness does not run is a
    # reading nobody chose, and finding that out from a half-written log is
    # finding it out too late.
    adapter.check_models(models)
    if log_path.exists():
        raise IngestError(
            f"run log {log_path} already exists — replay it, or pass a fresh --log"
        )
    version = adapter.version()
    today = local_today()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    runs = []
    with log_path.open("x", encoding="utf-8") as log:
        for model in models:
            for task in tasks:
                run = _run_task_live(
                    task, model, adapter=adapter,
                    agent_version=version, as_of=today, sweep=sweep,
                )
                log.write(json.dumps(run.model_dump(mode="json"), sort_keys=True) + "\n")
                log.flush()
                runs.append(run)
    return runs


def _run_task_live(
    task: Task, model: str, *,
    adapter: AgentAdapter, agent_version: str, as_of: date, sweep: str,
) -> Run:
    with tempfile.TemporaryDirectory(prefix="ai-bench-live-") as name:
        workdir = Path(name) / "workdir"
        shutil.copytree(task.repo_dir, workdir)
        initial = _commit_pristine(task, workdir)
        # The limit is handed to the adapter, never asked of it: it is the
        # task's class limit, registered before the sweep that reads it.
        base = adapter.run(
            task.id, task.prompt, model, workdir,
            agent_version=agent_version, as_of=as_of,
            limit_s=live_run_limit_s(task),
        )
        diff = _capture_workdir_diff(task, workdir, initial)
    # A v1 Run is v0's fields plus the diff, the sweep id, and the adapter's
    # own cost-source disclosure, and the dump keeps that coupling in one
    # place. mypy cannot see through the **dump, but Run's extra="forbid"
    # turns any v0 field this model does not declare into a loud runtime
    # error rather than silent drift.
    return Run(
        **base.model_dump(), diff=diff, sweep=sweep,
        cost_source=adapter.cost_source, price_table=adapter.price_table,
    )


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
