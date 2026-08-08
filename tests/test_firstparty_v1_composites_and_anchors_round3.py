"""Round 3's ceiling batch: two composites and two headroom anchors (#43).

Two rounds of evidence say this benchmark's upper scale is nearly empty: 7 of
45 constructed tasks have ever landed above haiku-solvable, sixteen of round
2's eighteen sat on the bottom rung, and nothing in round 2 reached unsolved
at all (design note sections 17 and 22.3). The round-3 spec's answer is to
build the top of the ladder on purpose — composites that stack the levers, and
anchors that are bet to be out of reach — and to make both of them
**counter-neutral**, so that populating the ceiling cannot also move a knob's
kill-discipline counter.

**Counter-neutrality is what this suite mostly checks, and it is structural
rather than promised.** Section 9's amended discipline counts a knob's rounds
off two things and nothing else: a family or pair whose varied knob it is, and
an effort claim registered on a task activating it and scored to it. None of
these four tasks declares a family or a pair, and none registers an effort
claim, so `registered_contrasts` cannot see them and `claim_knobs` returns
nothing for them — which this suite asserts using reconciliation's own
functions rather than by restating the rule. Clause 3 is the reason the claims
are absent rather than merely unregistered: a baseline claim on a task
activating three knobs is scored to *no* knob, so a cost claim on a composite
would be a bet nothing could ever be attributed to.

**What the composites are.** The round-3 spec calls "intent-level spec x
planted open decision x substrate terrain" the only recipe that ever produced
unsolved cells, and the record is narrower than that. `reconcile-v1` replays
every logged diff and finds four unsolved cells: `settings-merge-layers-l2`,
`duration-parse-written-l3`, `inventory-consume-lots-l3` — constructed,
hand-authored, K1 alone — and `calc-infix-evaluator`, a frozen zero-knob
control. (#43's first commits said three and cited section 14, which sorts
round 1's *prediction misses*; a control registers no prediction, so that
section could never have held the fourth.) So the constructed ingredient with
a record is K1 at intent, and what these two do is stack on it the two levers
with the largest measured *effort* effects, K7's terrain and K9's open
decision. The correction is registered in both task comments and in section
23.10 rather than left for a reader to notice, and this suite asserts it is
there.

**What the anchors are.** Calc-infix-class tasks whose whole spec is stated as
acceptance criteria and whose difficulty is the width of that spec — and the
fourth unsolved cell is `calc-infix-evaluator` itself, so the class they are
named for is the one class with a knob-free ceiling reading already on it.
They cannot follow it all the way, because its zero-knob declaration is the
*absence* of a construction block and `BASELINE_TASK_IDS` freezes that set at
22; so they declare `K1=acceptance`, which is honest and which pools them into
a calibration row with round 1's four `-l1` variants. That pooling is asserted
here so it cannot drift silently.

Every rung here is registered `unsolved`, which is a bet this corpus's ledger
says loses — upward rung bets outside K1 are nought for fourteen lifetime
(section 21) — and the pre-registered reading is that a beaten anchor is
ceiling data rather than a failure. The rest is what every checked-in task has
to prove: lints clean, reference resolves, empty diff does not, scale honest
to the reference diff, the repository green before and after, provenance
pinned where the tree is vendored, plus per task an answer written differently
that must still grade 1.0 and a careless one that must not.
"""

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    TASKS,
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
)
from test_firstparty_v1_k7_round3_pairs import replacing
from test_firstparty_v1_k9_round2_tasks import answer_of, authoring_comment

from ai_benchmark.firstparty_v1 import (
    BASELINE_TASK_IDS,
    EffortClaim,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)
from ai_benchmark.reconcile_v1 import Outcome, claim_knobs, registered_contrasts

# The one vendored tree the composites sit on, and the same snapshot #41's and
# #42's pairs use. Both composites are on it: what holds them apart is the
# machinery, the transition walks against the plain-data round trip, and what
# that gives up — the cross-substrate agreement section 10 wants — is recorded
# in section 23.10 rather than claimed away.
ORIGIN = "https://github.com/pgularski/pysm"
COMMIT = "0c47a5067974951c75a498ee4ed025cf881f48fd"
LICENCE_HOLDER = "Piotr Gularski"

CORE = "pysm/pysm.py"
SERIALIZATION = "pysm/serialization.py"
SIEVE = "sieve.py"
GAUGE = "gauge.py"

# The profile the two composites share, which is the row they make in
# `calibrate-v1`, sorted by knob number the way the view keys it.
COMPOSITE_PROFILE = {"K1": "intent", "K7": "dense", "K9": "single"}

# What an anchor declares, and the row it therefore lands in.
ANCHOR_PROFILE = {"K1": "acceptance"}

# Round 1's four `-l1` variants: the tasks already in the anchors' row.
ROUND_ONE_L1 = (
    "billing-split-by-weight-l1",
    "duration-parse-written-l1",
    "inventory-consume-lots-l1",
    "settings-merge-layers-l1",
)


# --- composite A: the route search, answered another way and answered badly ----

# The reference's search: breadth first over configurations, pruning any
# configuration already seen, returning the first run of events that lands on
# the target — which is therefore a shortest one.
_ROUTE_SHORTEST = """\
        seen = set([tuple([config[item] for item in machines] + [leaf])])
        pending = deque([(config, leaf, [])])
        while pending:
            config, leaf, names = pending.popleft()
            for name, from_state, to_state in root._certain_moves(config, leaf):
                moved, moved_leaf = root._configuration_after(
                    config, leaf, from_state, to_state)
                key = tuple([moved[item] for item in machines] + [moved_leaf])
                if key in seen:
                    continue
                seen.add(key)
                if moved_leaf is target:
                    return [Event(item) for item in names + [name]]
                pending.append((moved, moved_leaf, names + [name]))
        return None
"""
# A scenic route instead of a shortest one: the pruned search settles only
# whether the target is reachable and how far off it is, and the answer is then
# enumerated without pruning configurations at all and taken as the *longest*
# run within three steps of the shortest. The brief says any run of events that
# reaches the target is a correct answer and leaves the choice to the solver, so
# this has to grade 1.0 — and unlike swapping `popleft` for `pop`, which the
# seen-set makes return the reference's own routes on every graded call, it
# demonstrably answers differently, which
# `test_the_two_searches_really_do_hand_back_different_routes` shows before the
# grading assertion is allowed to mean anything.
_ROUTE_SCENIC = """\
        seen = set([tuple([config[item] for item in machines] + [leaf])])
        pending = deque([(config, leaf, [])])
        shortest = None
        while pending and shortest is None:
            walk, at, names = pending.popleft()
            for name, from_state, to_state in root._certain_moves(walk, at):
                moved, moved_leaf = root._configuration_after(
                    walk, at, from_state, to_state)
                key = tuple([moved[item] for item in machines] + [moved_leaf])
                if key in seen:
                    continue
                seen.add(key)
                if moved_leaf is target:
                    shortest = len(names) + 1
                    break
                pending.append((moved, moved_leaf, names + [name]))
        if shortest is None:
            return None
        reaching = []
        pending = deque([(config, leaf, [])])
        while pending:
            walk, at, names = pending.popleft()
            if len(names) >= shortest + 3:
                continue
            for name, from_state, to_state in root._certain_moves(walk, at):
                moved, moved_leaf = root._configuration_after(
                    walk, at, from_state, to_state)
                if moved_leaf is target:
                    reaching.append(names + [name])
                else:
                    pending.append((moved, moved_leaf, names + [name]))
        return [Event(item) for item in max(reaching, key=len)]
"""

# What the two searches are asked, run in a tree of each shape: every distinct
# `route` call the held-out suite makes, on the graphs it makes them on, so the
# difference the probe claims is measured over the graded surface rather than
# over a case chosen to show one.
_ROUTE_ANSWERS = '''\
from pysm import Event, State, StateMachine


def workshop():
    machine = StateMachine("workshop")
    idle, done = State("idle"), State("done")
    work, cutting = StateMachine("work"), State("cutting")
    sanding, rough, fine = StateMachine("sanding"), State("rough"), State("fine")
    machine.add_state(idle, initial=True)
    machine.add_state(work)
    machine.add_state(done)
    work.add_state(cutting, initial=True)
    work.add_state(sanding)
    sanding.add_state(rough, initial=True)
    sanding.add_state(fine)
    machine.add_transition(idle, work, events=["start"])
    work.add_transition(cutting, sanding, events=["next"])
    sanding.add_transition(rough, fine, events=["polish"])
    machine.add_transition(work, work, events=["restart"])
    machine.add_transition(work, done, events=["finish"])
    machine.initialize()
    return machine, {
        "idle": idle, "work": work, "cutting": cutting, "sanding": sanding,
        "rough": rough, "fine": fine, "done": done,
    }


def follow(machine, names):
    for name in names:
        machine.dispatch(Event(name))
    return machine


def route(target, walked=()):
    machine, states = workshop()
    follow(machine, walked)
    answer = machine.route(states[target])
    return None if answer is None else [event.name for event in answer]


for target, walked in (
    ("cutting", ()), ("fine", ()), ("idle", ()), ("done", ()),
    ("cutting", ("start", "next", "polish")),
    ("done", ("start", "next", "polish")),
    ("idle", ("start", "finish")), ("cutting", ("start", "finish")),
    ("done", ("start", "next")),
):
    print(target, walked, route(target, walked))

machine, states = workshop()
orphan = State("orphan")
machine.add_state(orphan)
print("orphan", machine.route(orphan))

ring = StateMachine("ring")
one, two, three, aside = (
    State("one"), State("two"), State("three"), State("aside"))
ring.add_state(one, initial=True)
for state in (two, three, aside):
    ring.add_state(state)
ring.add_transition(one, two, events=["step"])
ring.add_transition(two, three, events=["step"])
ring.add_transition(three, one, events=["step"])
ring.initialize()
for target in (three, aside):
    answer = ring.route(target)
    print(target.name, None if answer is None else [e.name for e in answer])
'''

# The entry walk descends a `.state` the exit walk has already reset. This is
# the same walk with the descent taken off the configuration as it stood
# *before* the exit walk, which is what an author who never read
# `_exit_states` writes, and it is wrong exactly where a transition re-enters
# a machine it is leaving.
_ROUTE_AFTER_THE_WALK = """\
        config = dict(config)
        state = leaf
"""
_ROUTE_BEFORE_THE_WALK = """\
        before = dict(config)
        config = dict(config)
        state = leaf
"""
_ROUTE_DESCEND_AFTER = """\
        state = to_state
        while isinstance(state, StateMachine) and config[state] is not None:
            state = config[state]
"""
_ROUTE_DESCEND_BEFORE = """\
        state = to_state
        while isinstance(state, StateMachine) and before[state] is not None:
            state = before[state]
"""


# --- composite B: the rebuild, answered another way and answered badly ---------

# The open decision, taken the other way: the last child in name order rather
# than the first. Nothing in the snapshot says which, the brief says any of a
# machine's own states will do, and the held-out tests only ask that the choice
# be legal — so this has to grade 1.0.
_REBUILD_FIRST_IS_INITIAL = "            parent.add_state(states[child_path], initial=(index == 0))"
_REBUILD_LAST_IS_INITIAL = (
    "            parent.add_state(\n"
    "                states[child_path],\n"
    "                initial=(index == len(children[parent_path]) - 1))"
)

# Which paths are machines is written in the snapshot. This infers it from the
# shape instead — anything with something under it is a machine — which is the
# obvious shortcut and is wrong for a machine with no states in it, a shape
# `_get_leaf_state` treats as a leaf and `snapshot` records as a machine.
_REBUILD_FROM_THE_MACHINE_LIST = """\
        states[path] = (StateMachine(path[-1]) if path in machine_paths
                        else State(path[-1]))
"""
_REBUILD_FROM_THE_SHAPE = """\
        states[path] = (StateMachine(path[-1])
                        if any(other[:-1] == path for other in paths)
                        else State(path[-1]))
"""


# --- anchor: the filter language, answered another way and answered badly ------

# The same three-valued combination, written as loops instead of membership
# tests. Behaviour for behaviour identical, and a suite pinning the reference's
# spelling would fail it.
_SIEVE_BY_MEMBERSHIP = '''\
def _all_of(held):
    if FALSE in held:
        return FALSE
    return UNKNOWN if UNKNOWN in held else TRUE


def _any_of(held):
    if TRUE in held:
        return TRUE
    return UNKNOWN if UNKNOWN in held else FALSE'''
_SIEVE_BY_LOOP = '''\
def _all_of(held):
    answer = TRUE
    for one in held:
        if one == FALSE:
            return FALSE
        if one == UNKNOWN:
            answer = UNKNOWN
    return answer


def _any_of(held):
    answer = FALSE
    for one in held:
        if one == TRUE:
            return TRUE
        if one == UNKNOWN:
            answer = UNKNOWN
    return answer'''

# NOT of the unknown is the unknown. This is Python's `not`, which turns it
# into true — the single most idiomatic way to lose three-valued logic, and
# invisible to any check that only ever looks at what was selected rather than
# at what its negation selects.
_SIEVE_NOT_KEEPS_THE_UNKNOWN = """\
        held = _hold(node[1], record)
        if held == UNKNOWN:
            return UNKNOWN
        return FALSE if held == TRUE else TRUE
"""
_SIEVE_NOT_FLIPS_EVERYTHING = """\
        held = _hold(node[1], record)
        return FALSE if held == TRUE else TRUE
"""


# --- anchor: the unit evaluator, answered another way and answered badly -------

# Dividing spelled as multiplying by the reciprocal, with the kind inverted
# and added rather than subtracted. The same arithmetic by another road.
_GAUGE_BY_SUBTRACTION = """\
            if right[0] == 0:
                raise ValueError("division by nothing")
            value = (value[0] / right[0], _added(value[1], right[1], -1))
"""
_GAUGE_BY_RECIPROCAL = """\
            if right[0] == 0:
                raise ValueError("division by nothing")
            flipped = dict(
                (name, -times) for name, times in right[1].items())
            value = (value[0] * (1.0 / right[0]), _added(value[1], flipped, 1))
"""

# Every unit here is worth some number of base units, so the arithmetic has to
# happen in base units. This carries the written number through instead, which
# is right for every expression in one unit and wrong by a factor of a thousand
# for `1 km / 1 m`.
_GAUGE_IN_BASE_UNITS = """\
        factor, dimension = _known(unit)
        return (size * factor, dict(dimension)), index + 1
"""
_GAUGE_IN_WRITTEN_UNITS = """\
        _factor, dimension = _known(unit)
        return (size, dict(dimension)), index + 1
"""


class Probes(NamedTuple):
    """The passage each task's alternative answer bends, and what it bends it
    into.

    `another_way` has to grade 1.0, or the suite would be grading whether the
    agent guessed our diff — which matters twice over here, once because two of
    these trees are somebody else's library and once because the composites
    label a decision open and a suite pinning one resolution of it would be
    taking the label back. The careless answers are in `CARELESS` below, since
    they bend a different passage and one of them bends two.
    """

    module: str
    reference: str
    another_way: str


class Ceiling(NamedTuple):
    """One task of the batch, and what it is here to do."""

    task_id: str
    kind: str
    levels: dict[str, str]
    probes: Probes


BATCH = (
    Ceiling(
        task_id="pysm-work-out-a-way-there",
        kind="composite",
        levels=COMPOSITE_PROFILE,
        probes=Probes(
            module=CORE,
            reference=_ROUTE_SHORTEST,
            another_way=_ROUTE_SCENIC,
        ),
    ),
    Ceiling(
        task_id="pysm-rebuild-a-graph-from-a-snapshot",
        kind="composite",
        levels=COMPOSITE_PROFILE,
        probes=Probes(
            module=SERIALIZATION,
            reference=_REBUILD_FIRST_IS_INITIAL,
            another_way=_REBUILD_LAST_IS_INITIAL,
        ),
    ),
    Ceiling(
        task_id="sieve-select-what-matches",
        kind="anchor",
        levels=ANCHOR_PROFILE,
        probes=Probes(
            module=SIEVE,
            reference=_SIEVE_BY_MEMBERSHIP,
            another_way=_SIEVE_BY_LOOP,
        ),
    ),
    Ceiling(
        task_id="gauge-evaluate-in-units",
        kind="anchor",
        levels=ANCHOR_PROFILE,
        probes=Probes(
            module=GAUGE,
            reference=_GAUGE_BY_SUBTRACTION,
            another_way=_GAUGE_BY_RECIPROCAL,
        ),
    ),
)

# The careless answers bend a different passage from the alternative ones, so
# they are kept beside the task rather than in `Probes`, which holds one
# passage per task.
CARELESS = {
    "pysm-work-out-a-way-there": (
        (CORE, _ROUTE_AFTER_THE_WALK, _ROUTE_BEFORE_THE_WALK),
        (CORE, _ROUTE_DESCEND_AFTER, _ROUTE_DESCEND_BEFORE),
    ),
    "pysm-rebuild-a-graph-from-a-snapshot": (
        (SERIALIZATION, _REBUILD_FROM_THE_MACHINE_LIST, _REBUILD_FROM_THE_SHAPE),
    ),
    "sieve-select-what-matches": (
        (SIEVE, _SIEVE_NOT_KEEPS_THE_UNKNOWN, _SIEVE_NOT_FLIPS_EVERYTHING),
    ),
    "gauge-evaluate-in-units": (
        (GAUGE, _GAUGE_IN_BASE_UNITS, _GAUGE_IN_WRITTEN_UNITS),
    ),
}

BY_TASK = [pytest.param(item, id=item.task_id) for item in BATCH]
COMPOSITES = [pytest.param(item, id=item.task_id)
              for item in BATCH if item.kind == "composite"]
ANCHORS = [pytest.param(item, id=item.task_id)
           for item in BATCH if item.kind == "anchor"]

TASK_IDS = tuple(item.task_id for item in BATCH)


def tasks() -> list[Task]:
    return [task_by_id(task_id) for task_id in TASK_IDS]


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


def rewriting(*swaps: tuple[str, str, str]) -> Callable[[Path], None]:
    """Bend several passages at once, insisting each one is there.

    `replacing` from #41's suite takes one passage, which is all three of these
    four tasks need; the route search's careless answer takes two, because the
    walk it gets wrong is written in two places.
    """

    def rewrite(workdir: Path) -> None:
        for module, before, after in swaps:
            source = workdir / module
            text = source.read_text()
            assert text.count(before) == 1, (module, before)
            source.write_text(text.replace(before, after))

    return rewrite


def unswept(task: Task) -> Outcome:
    """This task as reconciliation sees it before any run: no verdicts, no
    measurements, no round. Everything the counter-neutrality assertions read
    is declared in the task rather than measured, so an unswept outcome is the
    honest input and it keeps the check independent of what the logs hold."""
    return Outcome(task=task, resolved={}, effort={}, rung="unswept", round=None)


# --- counter-neutrality, read off reconciliation's own machinery ---------------


def test_none_of_these_tasks_can_join_a_registered_contrast() -> None:
    """The invariant the whole batch turns on, checked against the function
    that decides it rather than against a restatement of the rule.

    `registered_contrasts` groups outcomes by declared family and by declared
    pair. Four tasks declaring neither cannot appear in one, so no round can be
    counted for a knob on their account and no rung of theirs can separate
    anything. Read over the *whole* task set, because a contrast is a property
    of the set and a subset could hide a partner.
    """
    outcomes = [unswept(task) for task in load_task_set(TASKS)]

    members = {
        member.task.id
        for contrast in registered_contrasts(outcomes)
        for member in contrast.members
    }

    assert members & set(TASK_IDS) == set()


def test_none_of_these_tasks_scores_an_effort_claim_to_any_knob() -> None:
    """The other half of section 9's clause 1, and the one an author could
    break by accident.

    A registered effort claim is the second and last thing that advances a
    counter, and none of these four registers one, so `claim_knobs` returns
    nothing for all four. What that does *not* show is clause 3, which is a
    different question and is asked in the test below.
    """
    outcomes = [unswept(task) for task in load_task_set(TASKS)]
    contrasts = registered_contrasts(outcomes)
    mine = [outcome for outcome in outcomes if outcome.task.id in TASK_IDS]

    assert len(mine) == len(TASK_IDS)
    for outcome in mine:
        assert claim_knobs(outcome, contrasts) == frozenset(), outcome.task.id


def claiming(task: Task, factor: float = 1.25) -> Outcome:
    """This task as it would be if its author had registered the baseline cost
    claim they did not register. Synthetic on purpose: the claim exists in this
    process and in no `task.yaml`, which is the only way to ask what clause 3
    would do with one."""
    construction = task.construction
    assert construction is not None
    claim = EffortClaim(
        comparator="baseline", metric="cost", at_least_factor=factor)
    return unswept(
        task.model_copy(
            update={
                "construction": construction.model_copy(
                    update={
                        "prediction": construction.prediction.model_copy(
                            update={"effort": claim})
                    }
                )
            }
        )
    )


def test_a_baseline_claim_would_score_to_k1_on_an_anchor_and_nowhere_on_a_composite(
) -> None:
    """Clause 3 itself, exercised rather than described.

    The test above cannot reach it: `claim_knobs` returns early on a task whose
    prediction carries no effort claim, so four tasks that register none say
    nothing about how a claim *would* have been attributed. This registers one
    synthetically and reads the answer off `reconcile_v1.claim_knobs` — nothing
    for a composite, because one cost reading over K1, K7 and K9 names none of
    them, and `{"K1"}` for an anchor, because an anchor activates exactly one
    knob and a baseline claim on it is scored there.

    That second answer is the whole reason no claim was registered on the
    anchors: a claim would have handed K1 a counted round off a task built to
    measure the ceiling, which is the artifact verdict round 3's amendment
    exists to remove, arriving by the back door.
    """
    outcomes = [unswept(task) for task in load_task_set(TASKS)]
    contrasts = registered_contrasts(outcomes)

    scored = {
        item.task_id: claim_knobs(claiming(task_by_id(item.task_id)), contrasts)
        for item in BATCH
    }

    assert scored == {
        "pysm-work-out-a-way-there": frozenset(),
        "pysm-rebuild-a-graph-from-a-snapshot": frozenset(),
        "sieve-select-what-matches": frozenset({"K1"}),
        "gauge-evaluate-in-units": frozenset({"K1"}),
    }


@pytest.mark.parametrize("item", BY_TASK)
def test_the_task_declares_no_family_no_pair_and_no_effort_claim(
    item: Ceiling,
) -> None:
    """Said again at the task, because the two assertions above are read over
    the set and a reader meeting one of these four on its own is owed the
    property where it is declared."""
    task = task_by_id(item.task_id)

    assert task.construction is not None
    assert task.construction.family is None
    assert task.construction.pair is None
    assert task.construction.prediction.effort is None


def test_the_retired_knob_stays_at_the_four_tasks_it_already_has() -> None:
    """K11 was retired by #41 on the identifiability argument of section 23.5,
    and what makes a retirement effective is that nothing new declares it: a
    knob no round puts to a contrast has a counter that cannot advance. Four
    new tasks are four chances to undo that by accident."""
    declaring = {
        task.id for task in load_task_set(TASKS)
        if task.construction is not None and "K11" in task.construction.levels
    }

    assert len(declaring) == 4
    assert declaring & set(TASK_IDS) == set()


def test_the_frozen_baseline_is_still_the_twenty_two_it_was() -> None:
    """An anchor is a calc-infix-class task and calc-infix-evaluator is a
    baseline control, which is the one way this batch could have reached for
    the frozen set. It is frozen in code and none of these four is in it: an
    anchor declares its construction instead, and the reason is that absence of
    the block *is* the baseline's declaration."""
    baseline = {task.id for task in load_task_set(TASKS)
                if task.id in BASELINE_TASK_IDS}

    assert len(baseline) == 22
    assert baseline == set(BASELINE_TASK_IDS)
    assert baseline & set(TASK_IDS) == set()


# --- what each task declares ---------------------------------------------------


@pytest.mark.parametrize("item", BY_TASK)
def test_the_task_declares_the_profile_this_batch_was_built_around(
    item: Ceiling,
) -> None:
    task = task_by_id(item.task_id)

    assert declared(task) == item.levels
    assert task.category == "feature-dev"
    assert task.scale == "single-file"
    assert task.language == "python"


def test_the_composites_activate_the_three_levers_of_the_recipe() -> None:
    """K1 at intent is the ingredient with a record — two of the corpus's three
    *constructed* unsolved cells sit at that level; the fourth unsolved cell
    declares no knob at all — and K7 and K9 are the two levers with the largest
    measured effort effects. Pinned as a set, because the calibration view keys
    a row on exactly this."""
    composites = [item for item in BATCH if item.kind == "composite"]

    assert len(composites) == 2
    for item in composites:
        assert declared(task_by_id(item.task_id)) == {
            "K1": "intent", "K7": "dense", "K9": "single"}


def test_the_anchors_declare_the_level_their_specs_are_written_at() -> None:
    anchors = [item for item in BATCH if item.kind == "anchor"]

    assert len(anchors) == 2
    for item in anchors:
        assert declared(task_by_id(item.task_id)) == {"K1": "acceptance"}


def test_the_row_the_anchors_land_in_is_shared_with_round_ones_l1_variants(
) -> None:
    """The cost of declaring `K1=acceptance`, asserted so it cannot drift
    silently into being a surprise at reconcile time.

    `calibrate-v1` keys a row on category x sorted profile, so an anchor lands
    beside round 1's four `-l1` variants — 26-to-36-line changes that all came
    back haiku-solvable — and if the rung bet lands the row's floor moves to
    `unsolved` with no way for the key to say which task put it there. All six
    are single-file and hand-authored, so #38's mix disclosure prints one line
    over all of them, `6 single-file; 6 hand-authored`, which separates the row
    from its denominator and an anchor from nothing. This is #40's pooling
    problem in a second place and it gets #40's answer: recorded where the
    reader is, here and in both task comments and in section 23.10.
    """
    sharing = {
        task.id for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.levels == {"K1": "acceptance"}
        and task.category == "feature-dev"
    }

    assert sharing == set(ROUND_ONE_L1) | {
        item.task_id for item in BATCH if item.kind == "anchor"}


def test_the_composites_make_a_calibration_row_of_their_own() -> None:
    """The other side of the same reading: `K1=intent,K7=dense,K9=single` is a
    key nothing else in the corpus has, so the composites are a cell of two
    rather than a contribution to somebody else's."""
    sharing = {
        task.id for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.levels == COMPOSITE_PROFILE
    }

    assert sharing == {item.task_id for item in BATCH
                       if item.kind == "composite"}


# --- the pre-registered predictions --------------------------------------------


def test_every_rung_in_the_batch_is_registered_unsolved() -> None:
    """What the batch is for, and a bet the ledger says loses.

    Upward rung bets outside K1 stand at nought for fourteen lifetime (section
    21) and these are the fifteenth through eighteenth. Registered anyway,
    because the spec commissioned the ceiling to be *measured* rather than
    assumed and an unsolved bet is the only bet that measures it — and because
    a beaten one is ceiling data, which the rationales say in those words.
    """
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks() if task.construction is not None
    }

    assert registered == dict.fromkeys(TASK_IDS, "unsolved")


@pytest.mark.parametrize("item", BY_TASK)
def test_every_rationale_registers_the_mechanism_and_what_would_defeat_it(
    item: Ceiling,
) -> None:
    """A rationale is what a missed prediction teaches, and four bets against a
    ledger this poor have to say in advance what a miss would mean.

    Both phrases required, not either. "ceiling data" is the reading the spec
    fixes for a beaten bet and it has to be in the registration rather than
    only in the ticket; "would defeat" is the falsification condition, and a
    rationale that named a mechanism without one would be an explanation
    rather than a bet.
    """
    task = task_by_id(item.task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale
    assert len(rationale.split()) >= 60
    assert "ceiling data" in rationale
    assert "would defeat" in rationale


@pytest.mark.parametrize("item", COMPOSITES)
def test_each_composite_argues_the_recipe_it_instantiates(item: Ceiling) -> None:
    """The composites' comment has to carry the correction, because the spec's
    phrasing is wider than the record supports and a reader of the task alone
    would otherwise inherit the wider claim.

    All three phrases, not any: the recipe named, the unsolved cells the record
    actually holds, and the word for what stacking two more levers onto K1 is.
    """
    comment = authoring_comment(item.task_id)

    assert "recipe" in comment
    assert "unsolved cells" in comment
    assert "mechanism-based bet" in comment
    assert len(comment.split()) >= 150


@pytest.mark.parametrize("item", ANCHORS)
def test_each_anchor_argues_why_it_declares_a_knob_at_all(item: Ceiling) -> None:
    """An anchor was commissioned as a calc-infix-class task and
    calc-infix-evaluator declares nothing. Why this one cannot do the same, and
    what declaring costs the calibration table, belongs where a reader of the
    task looks."""
    comment = authoring_comment(item.task_id)

    assert "BASELINE_TASK_IDS" in comment
    assert "calibration" in comment
    assert len(comment.split()) >= 150


@pytest.mark.parametrize("item", COMPOSITES)
def test_the_composite_prompt_does_not_give_the_terrain_away(
    item: Ceiling,
) -> None:
    """K7 is terrain: the invariants the change turns on live in the library
    and not in the brief, and a prompt that restated them would be setting a
    different knob. Two phrases per task, each naming something the brief would
    have given away by saying it. Route's two are exactly what its careless
    probe gets wrong; rebuild's are two of the several invariants its
    prediction rests on, and its careless probe turns on a different one — the
    snapshot's own list of which paths are machines — which no phrase here
    stands in for.
    """
    prompt = task_by_id(item.task_id).prompt.lower()

    if item.task_id == "pysm-work-out-a-way-there":
        assert "initial state" not in prompt
        assert "exit" not in prompt
    else:
        assert "_leaf_state" not in prompt
        assert "prefix" not in prompt


@pytest.mark.parametrize("item", COMPOSITES)
def test_the_composite_prompt_labels_the_decision_it_leaves_open(
    item: Ceiling,
) -> None:
    """K9 at `single`, as this corpus uses the level: a *labelled* open
    decision, announced in the brief and admitting several correct answers
    (section 23.3). The label is what the alternative-answer probe below
    honours, so a prompt that lost it would leave that probe grading a
    resolution nobody was promised."""
    prompt = task_by_id(item.task_id).prompt

    assert "yours to choose" in prompt


# --- the substrate, where there is one ------------------------------------------


@pytest.mark.parametrize("item", COMPOSITES)
def test_the_snapshot_records_where_it_came_from_and_what_pins_it(
    item: Ceiling,
) -> None:
    task = task_by_id(item.task_id)

    assert task.construction is not None
    substrate = task.construction.substrate
    assert substrate is not None
    assert (substrate.origin, substrate.commit, substrate.license) == (
        ORIGIN, COMMIT, "MIT")
    # No knob-setting edit: the density these tasks are pitched on is the
    # library's own, as round 1's two K7 tasks and #41's four were.
    assert substrate.modifications == ()


@pytest.mark.parametrize("item", COMPOSITES)
def test_the_licence_travels_with_the_vendored_code(item: Ceiling) -> None:
    licence = (task_by_id(item.task_id).repo_dir / "LICENSE").read_text()

    assert "MIT License" in licence
    assert LICENCE_HOLDER in licence


@pytest.mark.parametrize("item", COMPOSITES)
def test_the_two_composites_start_from_the_same_snapshot(item: Ceiling) -> None:
    """Not a pair — they ask for different things in different modules and
    neither is the other's control — but the same bytes, which is what lets
    section 23.10 say that what differs between them is the machinery."""

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    other = "pysm-rebuild-a-graph-from-a-snapshot"
    assert tree(task_by_id(item.task_id).repo_dir) == tree(
        task_by_id(other).repo_dir)


@pytest.mark.parametrize("item", ANCHORS)
def test_an_anchor_is_hand_authored_and_says_so_by_declaring_no_substrate(
    item: Ceiling,
) -> None:
    task = task_by_id(item.task_id)

    assert task.construction is not None
    assert task.construction.substrate is None


@pytest.mark.parametrize("item", BY_TASK)
def test_the_starting_tree_carries_no_version_control_metadata(
    item: Ceiling,
) -> None:
    task = task_by_id(item.task_id)

    assert not any(path.name == ".git" for path in task.repo_dir.rglob("*"))
    assert not (task.repo_dir / ".gitignore").exists()


# --- the gates every checked-in task passes -------------------------------------


def test_the_tasks_lint_clean() -> None:
    """Linted on their own, which these can be: none of the four registers an
    effort claim, so no rule the lint applies asks about a task outside the
    set."""
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize("item", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    item: Ceiling,
) -> None:
    """Solvable by construction, which is what makes `unsolved` a bet about
    models rather than about the task."""
    task = task_by_id(item.task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("item", BY_TASK)
def test_the_scale_is_honest_to_the_reference_diff(item: Ceiling) -> None:
    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task_by_id(item.task_id)).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {item.probes.module}


@pytest.mark.parametrize("item", BY_TASK)
def test_the_repository_starts_out_green_and_stays_green(item: Ceiling) -> None:
    """Nothing here withholds a warning — that is K8's lever — so the visible
    suite says the truth about the code it covers. What it does not do is say
    anything about the contracts these tasks are graded on, which is the whole
    of why the predictions are what they are."""
    task = task_by_id(item.task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


@pytest.mark.parametrize("item", BY_TASK)
def test_an_alternative_correct_answer_still_resolves(item: Ceiling) -> None:
    """What keeps the grading suites describing the change asked for rather
    than the reference solution. It carries extra weight on the composites,
    whose briefs label a decision open: a suite that only accepted our
    resolution of it would have taken the label back."""
    task = task_by_id(item.task_id)
    diff = solution_diff(
        task,
        mutate=replacing(
            item.probes.module, item.probes.reference, item.probes.another_way),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


def test_the_two_searches_really_do_hand_back_different_routes() -> None:
    """The guard on the probe above, for the one task where the probe could
    have been vacuous — and, for one revision of this suite, was.

    `route`'s open decision is *which* run of events comes back, so an
    alternative that grades 1.0 proves nothing unless it hands back a different
    run. The first version of this probe swapped the search's `popleft` for a
    `pop`, breadth first for depth first, and the seen-set pruning collapsed the
    two: every one of the graded suite's route calls came back byte-identical,
    so the assertion above was passing on the reference's own answers. The
    scenic search replaces it, and this runs both and compares, the way #39's
    K9 probes prove their two resolutions are two.
    """
    task = task_by_id("pysm-work-out-a-way-there")

    shortest = answer_of(task, _ROUTE_ANSWERS, None)
    scenic = answer_of(
        task,
        _ROUTE_ANSWERS,
        replacing(CORE, _ROUTE_SHORTEST, _ROUTE_SCENIC),
    )

    assert shortest.strip() and shortest != scenic
    differing = sum(
        1 for one, other in zip(shortest.splitlines(), scenic.splitlines())
        if one != other
    )
    # Four of the twelve distinct calls the graded suite makes, which is the
    # honest figure rather than a round one. Of the other eight, four have no
    # route at all, and the four that do have only one, since both searches
    # stop where they arrive and every way of reaching those targets goes
    # through the same run of events.
    assert differing == 4


@pytest.mark.parametrize("item", BY_TASK)
def test_a_careless_answer_does_not_resolve(item: Ceiling) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference. Each careless answer makes the change that was asked for and
    then loses one thing the task is about — the transition walk's reset, the
    snapshot's own list of which paths are machines, `NOT` of the unknown, and
    arithmetic in base units — and each is the idiomatic wrong move rather than
    an invented mistake."""
    task = task_by_id(item.task_id)
    diff = solution_diff(task, mutate=rewriting(*CARELESS[item.task_id]))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize("item", BY_TASK)
def test_a_careless_answer_still_leaves_the_visible_suite_green(
    item: Ceiling,
) -> None:
    """Why the rung bets are what they are, made checkable rather than
    asserted in prose. Every careless answer above passes everything the agent
    can run inside its own workdir, so nothing distinguishes it from a finished
    one until the held-out tests do."""
    task = task_by_id(item.task_id)

    assert visible_tests_pass(
        task, solved_tree(task, mutate=rewriting(*CARELESS[item.task_id])))


# The two counter-neutral tasks that were already in the set when #43 arrived,
# and the reason this guard names them instead of subtracting them. Both are
# round 1's standalone K8 refactors predicted `unsolved` and observed
# haiku-solvable — two of the misses §14 sorts under "model stronger than the
# bet" — so both declare a knob, form no family and no pair, and register no
# effort claim, which is the same predicate this batch satisfies. Each is
# probed by the suite that owns it — the hand-authored one by
# test_firstparty_v1_k8_tasks.py, the vendored one by
# test_firstparty_v1_substrate_tasks.py.
COUNTER_NEUTRAL_BEFORE_THIS_ROUND = (
    "leaderboard-extract-rank-key",
    "pysm-revert-through-one-step",
)


def test_every_counter_neutral_task_is_probed_by_the_suite_that_owns_it() -> None:
    """A task added to the set is a change to a directory rather than to any
    suite, so an unprobed one would sweep looking exactly like a probed one.

    Asserted as an exact equality against a named older set, which is the
    convention #33's K9 guard set and is the only version that can fail:
    `TASK_IDS` is derived from `BATCH`, so "`BATCH`'s ids equal `TASK_IDS`" is
    a tautology, and "`TASK_IDS` is a subset of the counter-neutral tasks"
    cannot notice a fifth. Naming the two older members is what costs
    something — a fifth counter-neutral task, from this round or any later
    one, fails here until somebody decides which suite probes it.
    """
    counter_neutral = {
        task.id for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.family is None
        and task.construction.pair is None
        and task.construction.prediction.rung == "unsolved"
        and task.construction.prediction.effort is None
    }

    assert not set(COUNTER_NEUTRAL_BEFORE_THIS_ROUND) & set(TASK_IDS)
    assert counter_neutral == set(TASK_IDS) | set(
        COUNTER_NEUTRAL_BEFORE_THIS_ROUND)
