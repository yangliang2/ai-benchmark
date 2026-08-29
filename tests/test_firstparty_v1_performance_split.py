"""The behaviour/structural split reaching `performance-optimisation` (§117.6).

Round 13's one machinery move, at the loader's own seam. §117.1 ruled the truth
of an optimisation to be **asserted growth behaviour, not measured time**: a
task ships two held-out suites — a behaviour suite proving correctness
unchanged, and a complexity suite counting operations through seams the task
repository already owns — and `resolved` is both passing. ADR-0006 records the
shape. What the *loader* does about it is one thing and only one: the split
that has been `refactor`'s alone since round 3 admits a second category, and
the two standing pristine invariants then ride it unchanged.

That last clause is the point of this file. The split buys nothing by itself;
what makes it the whole of the machinery is that the two-sided proof of an
honest proxy is already checked by the lint:

- the **behaviour** side is `refactor`'s behaviour-tests-pass-on-pristine rule,
  reaching a second category — a task must start from behaviour that works;
- the **complexity** side is the standing grading-must-not-pass-on-pristine
  rule doing for a slow start exactly what it does for a buggy one — a proxy
  the unoptimised code already satisfies is a task with nothing left to do.

Both are asserted here **through the real lint**, on fixtures that trip them,
which is `tests/test_firstparty_v1_typescript_instruments.py`'s prior art for
observing those same two runs from the outside. The two loader negatives are
written in the form of the standing ones —
`tests/test_firstparty_v1_fault_location.py`'s and
`tests/test_firstparty_v1_code_review.py`'s "this action names no behaviour
tests" — so that the three refusals read as one rule with one shape.

Everything here is a synthetic Python task tree under `tmp_path`, put through
the real loader and the real lint. The live corpus holds no
`performance-optimisation` task until the round's authoring tickets land, which
is why the fixture exists at all; nothing here calls an agent, a grader or the
network.

The fixture's own question is the shape the round's tasks will take. `Ledger`
totals accounts by walking its entry log once per account; the log counts its
own reads, because a store that says how hard it is working is a seam a
repository owns rather than one a grader bolts on. The behaviour suite asserts
the totals, and passes on the pristine tree. The complexity suite asserts the
log is read no more than once over, and fails on it — an index built once is
what makes it pass, and that is the optimisation.
"""

from pathlib import Path
from typing import get_args

import pytest
import yaml

from ai_benchmark import firstparty
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    EXISTENCE_PROOFS,
    GRADING_DIR,
    LIVE_RUN_LIMITS_S,
    POINTS_KEY_FILE,
    REPO_DIR,
    Task,
    _SPLIT_CATEGORIES,
    lint_task_set,
    live_run_limit_s,
    load_task_set,
)
from ai_benchmark.schema import TaskCategory

CATEGORY: TaskCategory = "performance-optimisation"
FIXTURE_ID = "ledger-total-in-one-pass"

BEHAVIOUR_TEST_FILE = "test_ledger_behaviour.py"
COMPLEXITY_TEST_FILE = "test_ledger_complexity.py"

PROMPT = """\
`Ledger.totals` is slow when the entry log is long and many accounts are
asked for at once: the day's statement takes visibly longer as the log grows.

Make it stay fast as the log grows, without changing what it returns.
"""

LEDGER = '''\
"""An expense ledger over an entry log, and the log it reads from."""


class EntryLog:
    """The store a ledger reads its entries out of.

    It counts its reads because a caller has always wanted to know how hard
    the store is working; nothing here is for a test's benefit.
    """

    def __init__(self, entries):
        self._entries = list(entries)
        self.reads = 0

    def __iter__(self):
        for entry in self._entries:
            self.reads += 1
            yield entry

    def __len__(self):
        return len(self._entries)


class Ledger:
    """Totals per account, over whatever the log holds."""

    def __init__(self, log):
        self._log = log

    def total_for(self, account):
        total = 0
        for name, amount in self._log:
            if name == account:
                total += amount
        return total

    def totals(self, accounts):
        return {account: self.total_for(account) for account in accounts}
'''

VISIBLE_TEST = '''\
from ledger import EntryLog, Ledger


def test_totals_add_up_per_account():
    ledger = Ledger(EntryLog([("ann", 3), ("bob", 5), ("ann", 7)]))

    assert ledger.totals(["ann", "bob"]) == {"ann": 10, "bob": 5}
'''

README = """\
# ledger

`Ledger` reports totals per account over an `EntryLog`.
"""

BEHAVIOUR_TEST = '''\
"""Correctness, unchanged: passes on the pristine repository and on the
reference solution."""

from ledger import EntryLog, Ledger

ENTRIES = [("ann", 3), ("bob", 5), ("ann", 7), ("cid", 11)]


def test_totals_add_up_per_account():
    ledger = Ledger(EntryLog(ENTRIES))

    assert ledger.totals(["ann", "bob", "cid"]) == {"ann": 10, "bob": 5, "cid": 11}


def test_an_account_with_no_entries_totals_zero():
    assert Ledger(EntryLog(ENTRIES)).total_for("dee") == 0
'''

# The proxy: reads of the log, counted through the log's own seam, across a
# held-out input size — ceiling-bounded at one pass. The pristine tree reads it
# once per account and fails; an index built once passes.
COMPLEXITY_TEST = '''\
"""Growth behaviour, asserted rather than timed: the log is read no more than
once over, however many accounts are asked for."""

from ledger import EntryLog, Ledger

ACCOUNTS = [f"a{index}" for index in range(8)]
ENTRIES = [(ACCOUNTS[index % len(ACCOUNTS)], index) for index in range(240)]


def test_totalling_every_account_reads_the_log_at_most_once_over():
    log = EntryLog(ENTRIES)

    Ledger(log).totals(ACCOUNTS)

    assert log.reads <= __CEILING__
'''

# Bent the one way the must-not-pass-on-pristine invariant is about: a ceiling
# the unoptimised walk already sits under. Nothing is left for an agent to do,
# and the lint says so before a sweep dollar is spent finding out.
SLACK_CEILING = "12 * len(ENTRIES)"
ONE_PASS_CEILING = "len(ENTRIES)"


def write_fixture(
    root: Path,
    *,
    category: str = CATEGORY,
    behaviour: str | None = BEHAVIOUR_TEST,
    ceiling: str = ONE_PASS_CEILING,
    names_behaviour_tests: bool = True,
    task_id: str = FIXTURE_ID,
    points_key: bool = False,
) -> Path:
    """The fixture performance-optimisation task, written ready to load.

    A coverage fixture rather than a knob experiment, so it declares itself a
    control — it claims nothing about difficulty, and saying so is the only way
    to say it.

    Every bend a test in this file needs is a parameter here rather than an
    edit afterwards, so that each fixture differs from the clean one in exactly
    the one way its test is about: the category it declares, whether it names
    its behaviour tests, whether the behaviour half passes on the pristine
    tree, and where the complexity half puts its ceiling.
    """
    task_dir = root / task_id
    (task_dir / REPO_DIR).mkdir(parents=True)
    (task_dir / GRADING_DIR).mkdir()
    spec: dict[str, object] = {
        "id": task_id,
        "category": category,
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "prompt": PROMPT,
    }
    if names_behaviour_tests:
        spec["grading"] = {"behaviour_tests": [BEHAVIOUR_TEST_FILE]}
    (task_dir / "task.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    (task_dir / REPO_DIR / "ledger.py").write_text(LEDGER)
    (task_dir / REPO_DIR / "test_ledger.py").write_text(VISIBLE_TEST)
    (task_dir / REPO_DIR / "README.md").write_text(README)
    if behaviour is not None:
        (task_dir / GRADING_DIR / BEHAVIOUR_TEST_FILE).write_text(behaviour)
    (task_dir / GRADING_DIR / COMPLEXITY_TEST_FILE).write_text(
        COMPLEXITY_TEST.replace("__CEILING__", ceiling)
    )
    if points_key:
        (task_dir / GRADING_DIR / POINTS_KEY_FILE).write_text("{}\n")
    return task_dir


def fixture_task(root: Path, **kwargs: object) -> Task:
    write_fixture(root, **kwargs)  # type: ignore[arg-type]
    [task] = load_task_set(root)
    return task


# --- the split, at the loader's seam --------------------------------------------


def test_a_performance_task_naming_its_behaviour_tests_loads(tmp_path: Path) -> None:
    """The positive: the split reaches a second category, and the behaviour
    half is readable back off the task exactly as a refactor's is."""
    task = fixture_task(tmp_path)

    assert task.category == CATEGORY
    assert task.behaviour_test_paths == (BEHAVIOUR_TEST_FILE,)
    # Something is left over to assert the optimisation actually happened —
    # the complexity half, which is what the structural side of the split means
    # for this action.
    assert set(task.grading_test_paths) > set(task.behaviour_test_paths)


def test_a_performance_task_naming_no_behaviour_tests_fails_loudly(
    tmp_path: Path,
) -> None:
    """The mirror of the refactor validator, and required for the same reason:
    the split is what carries §117.1's two-sided proof, so a task of this
    action with no behaviour half has no way to say the optimisation preserved
    what it optimised."""
    write_fixture(tmp_path, names_behaviour_tests=False, behaviour=None)

    with pytest.raises(IngestError, match=f"a {CATEGORY} task must name its"):
        load_task_set(tmp_path)


def test_the_split_reaches_exactly_two_categories(tmp_path: Path) -> None:
    """The third category stays refused, and which categories those are is read
    off the loader rather than listed here — a list in a test file is a second
    copy of the rule, and the copy is what goes stale when a fourth round
    widens the split.

    `unclassified` is skipped because the same validator refuses it one branch
    earlier and for a different reason: no task may declare it at all.
    """
    assert _SPLIT_CATEGORIES == frozenset({"refactor", CATEGORY})

    others = [
        category
        for category in get_args(TaskCategory)
        if category not in _SPLIT_CATEGORIES and category != "unclassified"
    ]
    assert others  # or the loop below proves nothing

    for category in others:
        with pytest.raises(IngestError, match="split grading") as refusal:
            fixture_task(tmp_path / category, category=category)
        assert category in str(refusal.value)
        assert "must-fail-on-pristine" in str(refusal.value)


def test_the_refusals_name_both_split_categories(tmp_path: Path) -> None:
    """Prose that says "refactor" where the code means two things is prose that
    misleads the next author, so the widened message names both — and names
    them off the loader's own set, so a third member could not be admitted
    without every message widening with it."""
    with pytest.raises(IngestError, match="split grading") as refusal:
        fixture_task(tmp_path, category="feature-dev")

    for category in _SPLIT_CATEGORIES:
        assert category in str(refusal.value)


# --- the two pristine invariants, through the real lint --------------------------


def test_the_clean_fixture_lints(tmp_path: Path) -> None:
    """The other end of the two negatives below: a task whose behaviour half
    passes on the pristine tree and whose complexity half fails on it has no
    problem to report, so neither invariant below is firing on everything."""
    assert lint_task_set([fixture_task(tmp_path)]) == []


def test_a_complexity_half_that_already_passes_on_pristine_is_refused(
    tmp_path: Path,
) -> None:
    """The complexity side of §117.1's two-sided proof, read from the outside.

    The standing grading-must-not-pass-on-pristine invariant, unchanged and
    unextended, doing for a slow start exactly what it has always done for a
    buggy one: a proxy the unoptimised code already satisfies is a task every
    agent resolves by doing nothing, and the lint catches it before the sweep
    rather than after it.
    """
    task = fixture_task(tmp_path, ceiling=SLACK_CEILING)

    [problem] = lint_task_set([task])
    assert "the grading tests already pass on the pristine repo" in problem


def test_a_behaviour_half_that_fails_on_pristine_is_refused(tmp_path: Path) -> None:
    """The behaviour side of the same proof: `refactor`'s
    behaviour-tests-pass-on-pristine invariant reaching a second category.

    A task whose behaviour half is already red has no baseline the
    optimisation could be said to preserve, and the message names both split
    categories now that both are held to it.
    """
    task = fixture_task(
        tmp_path,
        behaviour=BEHAVIOUR_TEST.replace('"bob": 5', '"bob": 9'),
    )

    [problem] = lint_task_set([task])
    assert "the behaviour tests fail on the pristine repo" in problem
    assert "must start from behaviour that already works" in problem
    for category in _SPLIT_CATEGORIES:
        assert category in problem


# --- the limit, registered before the sweep -------------------------------------


def test_the_live_run_limit_is_registered_at_the_flat_defaults_own_value(
    tmp_path: Path,
) -> None:
    """§118.9's entry, landed. It is registration and not tuning: the fallback
    would reach the same 600, so the entry buys no seconds and takes none
    away — what it buys is that the number is a considered commitment rather
    than an inherited convention, set before the sweep and never adjusted per
    cell."""
    assert LIVE_RUN_LIMITS_S[CATEGORY] == 600
    assert LIVE_RUN_LIMITS_S[CATEGORY] == firstparty.RUN_TIMEOUT_S
    assert live_run_limit_s(fixture_task(tmp_path)) == 600


# --- and what the move does not touch -------------------------------------------


def test_the_category_carries_no_key_and_registers_no_existence_proof() -> None:
    """The first of the two "does not move" claims, asserted rather than
    assumed. The action ships no key of any shape, and
    `_unregistered_proof_form_problems` computes the keyed actions minus the
    registered proofs — so `EXISTENCE_PROOFS` gains no entry and owes none
    (§117.6)."""
    assert CATEGORY not in EXISTENCE_PROOFS


def test_a_performance_task_shipping_a_points_key_fails_loudly(
    tmp_path: Path,
) -> None:
    """The second: the category joins no point machinery. It is not in
    `_POINT_CATEGORIES`, so the loader refuses a points key on it exactly as it
    refuses one on any other unregistered action — no points key is admitted
    for this action and no terrain exemption is granted for it."""
    write_fixture(tmp_path, points_key=True)

    with pytest.raises(IngestError, match=POINTS_KEY_FILE) as refusal:
        load_task_set(tmp_path)
    assert CATEGORY in str(refusal.value)
