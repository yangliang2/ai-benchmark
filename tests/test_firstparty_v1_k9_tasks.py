"""The K9 planted-crux tasks and their zero-crux controls (ticket #20).

The knob is crux depth. Each crux task states its acceptance rules in full and
then leaves exactly one decision unmade — which items travel together, what
order the tracks come back in, who pays whom — while every other step is
transcription. Each is paired with a control built on the same starting
repository, in the same matrix cell, at comparable size, whose every decision
is stated or derivable. Crux depth is then the only thing that moves between
a pair, which is what makes the pair a reading rather than two anecdotes.

What a planted crux costs is a grading suite that cannot name the answer. If
the held-out tests accepted one resolution, the task would not be a task with
an open decision at all — it would be one whose decision was made by an author
who never wrote it down, which is an unsolvable K1 wearing this knob's name.
So the suites grade the behaviour contract, and the probes here prove both
directions of that in the only way that settles it: for every crux task, two
genuinely different resolutions — different algorithms, and asserted to return
different answers, not merely to be spelled differently — each grade 1.0,
while the answer a reader arrives at by not making the decision at all grades
0.0.

The controls are probed too, with the slip a careless reader of a fully stated
spec makes, so that "nothing left to invent" cannot quietly mean "nothing left
to get wrong".

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, doing nothing grades unresolved — plus the
pre-registration the experiment rests on: each rung is pinned here, and the
claim the pairs make is that the crux costs exactly one rung.
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import SOLUTIONS, run_for, solution_diff, task_by_id
from pydantic import ValidationError

from ai_benchmark.firstparty_v1 import (
    KNOB_LEVELS,
    KnobActivation,
    Rung,
    Task,
    evaluate,
    lint_task_set,
)

# The operational difficulty ladder, easiest rung first, so a pair's claim can
# be compared and not only pinned.
RUNGS: tuple[Rung, ...] = ("haiku-solvable", "sonnet-only", "unsolved")

# Bytecode is a byproduct of having run something; these helpers copy solution
# trees directly, so they drop it rather than let it reach a diff.
_BYTECODE = shutil.ignore_patterns("__pycache__", "*.pyc")


# --- the crux, resolved a second way -------------------------------------------

BEST_FIT_DECREASING = '''def pack(items, capacity):
    """Heaviest item first, into the fullest carton that still has room."""
    cartons = []
    for item in sorted(items, key=lambda item: -item.weight):
        if item.weight > capacity:
            raise ValueError(f"{item.sku} is too heavy to despatch")
        roomy = [carton for carton in cartons if fits(carton, item, capacity)]
        if roomy:
            max(roomy, key=total_weight).append(item)
        else:
            cartons.append([item])
    return cartons
'''

SPREAD_OVER_SLOTS = '''def spread(tracks):
    """The busiest artists laid into every other slot, then the rest into the
    slots left between them."""
    grouped = by_artist(tracks)
    if any(len(group) > (len(tracks) + 1) // 2 for group in grouped.values()):
        raise ValueError("one artist holds too many tracks to be spaced out")
    ordered = [
        track
        for group in sorted(grouped.values(), key=len, reverse=True)
        for track in group
    ]
    queue = [None] * len(ordered)
    slots = list(range(0, len(ordered), 2)) + list(range(1, len(ordered), 2))
    for slot, track in zip(slots, ordered):
        queue[slot] = track
    return queue
'''

SETTLE_THROUGH_ONE_PERSON = '''def settle(net):
    """Everything routed through whoever is owed the most: the others who owe
    pay them, and they pay the others who are owed."""
    if sum(net.values()) != 0:
        raise ValueError("balances that do not add up to zero cannot be settled")
    left = {name: amount for name, amount in net.items() if amount != 0}
    if not left:
        return []
    hub = max(left, key=lambda name: (left[name], name))
    return [
        Transfer(name, hub, -amount)
        for name, amount in sorted(left.items())
        if amount < 0
    ] + [
        Transfer(hub, name, amount)
        for name, amount in sorted(left.items())
        if amount > 0 and name != hub
    ]
'''


# --- the answer arrived at by not making the decision ---------------------------

NEXT_FIT = '''def pack(items, capacity):
    """Fill the open carton until the next item does not fit, then open
    another one."""
    cartons = []
    for item in items:
        if item.weight > capacity:
            raise ValueError(f"{item.sku} is too heavy to despatch")
        if cartons and fits(cartons[-1], item, capacity):
            cartons[-1].append(item)
        else:
            cartons.append([item])
    return cartons
'''

DEAL_THE_ARTISTS_OUT = '''def spread(tracks):
    """One track from each artist in turn, busiest artist first, until every
    artist has run out."""
    grouped = by_artist(tracks)
    if any(len(group) > (len(tracks) + 1) // 2 for group in grouped.values()):
        raise ValueError("one artist holds too many tracks to be spaced out")
    groups = sorted(grouped.values(), key=len, reverse=True)
    queue = []
    while any(groups):
        for group in groups:
            if group:
                queue.append(group.pop(0))
    return queue
'''

PAY_EVERYBODY_PRO_RATA = '''def settle(net):
    """Everybody who owes pays everybody who is owed, in proportion to what
    they are owed."""
    if sum(net.values()) != 0:
        raise ValueError("balances that do not add up to zero cannot be settled")
    debtors = sorted((name, -a) for name, a in net.items() if a < 0)
    creditors = sorted((name, a) for name, a in net.items() if a > 0)
    owed = sum(amount for _, amount in creditors)
    transfers = []
    for name, debt in debtors:
        paid = 0
        for position, (creditor, credit) in enumerate(creditors):
            last = position == len(creditors) - 1
            share = debt - paid if last else debt * credit // owed
            paid += share
            if share:
                transfers.append(Transfer(name, creditor, share))
    return transfers
'''


# --- the slip a careless reader of a fully stated spec makes --------------------

LABELS_WITHOUT_PADDING = '''def labels(cartons, destination):
    """One despatch label per carton, in the order the cartons are given."""
    written = []
    for number, carton in enumerate(cartons, start=1):
        skus = ",".join(item.sku for item in carton) if carton else "(empty)"
        written.append(
            f"{destination.upper()}-{number} {skus} {labelled_weight(carton)}"
        )
    return written
'''

TRIM_BY_SKIPPING = '''def trimmed(tracks, seconds):
    """Everything from the queue that fits in a slot of `seconds` seconds."""
    if seconds < 0:
        raise ValueError(f"a slot cannot be {seconds} seconds long")
    kept = []
    running = 0
    for track in tracks:
        if running + track.seconds <= seconds:
            kept.append(track)
            running += track.seconds
    return kept
'''

APPLY_IN_PLACE = '''def applied(net, expense):
    """The balances that result from charging `expense` to `net`."""
    if not expense.shares:
        raise ValueError("an expense nobody shares cannot be charged")
    each, extra = divmod(expense.amount, len(expense.shares))
    net[expense.payer] = net.get(expense.payer, 0) + expense.amount
    for position, name in enumerate(expense.shares):
        net[name] = net.get(name, 0) - (each + (1 if position < extra else 0))
    return net
'''


# --- what each resolution actually answers, run for real ------------------------

# Printed from inside a solution tree. Where the answer is a set of things the
# order of which the prompt says nothing about, it is sorted first, so that two
# resolutions read as different only when they really answer differently.
PACKED = """
from cartons import Item, pack

shipment = [Item("a", 300), Item("b", 600), Item("c", 400), Item("d", 500)]
print(sorted(sorted(item.sku for item in carton) for carton in pack(shipment, 1000)))
"""

SPREAD_OUT = """
from playlist import Track, spread

artists = ["ora", "ora", "ora", "vek", "vek", "kip", "raz"]
queue = [Track(f"t{n}", artist, 200) for n, artist in enumerate(artists)]
print([track.title for track in spread(queue)])
"""

SETTLED = """
from settleup import settle

print(sorted(tuple(t) for t in settle({"ana": 700, "ben": 300,
                                       "cal": -400, "dee": -600})))
"""


class Pair(NamedTuple):
    """One planted-crux task, its zero-crux control, and what is pinned here.

    `module` is the file both tasks' reference solutions add a function to,
    and `crux_definition` / `control_definition` are where those functions
    start — which is what lets a probe swap one resolution for another.
    `another_way` and `not_an_answer` are the crux task's two probes,
    `careless` is the control's, `answers` prints the crux task's answer so
    two resolutions can be compared, and the two rungs are the pre-registered
    predictions.
    """

    crux_id: str
    control_id: str
    module: str
    crux_definition: str
    control_definition: str
    crux_rung: Rung
    control_rung: Rung
    another_way: str
    not_an_answer: str
    careless: str
    answers: str


PAIRS = (
    Pair(
        crux_id="cartons-pack-shipments",
        control_id="cartons-label-shipments",
        module="cartons.py",
        crux_definition="def pack(",
        control_definition="def labels(",
        crux_rung="sonnet-only",
        control_rung="haiku-solvable",
        another_way=BEST_FIT_DECREASING,
        not_an_answer=NEXT_FIT,
        careless=LABELS_WITHOUT_PADDING,
        answers=PACKED,
    ),
    Pair(
        crux_id="playlist-space-out-artists",
        control_id="playlist-trim-to-length",
        module="playlist.py",
        crux_definition="def spread(",
        control_definition="def trimmed(",
        crux_rung="sonnet-only",
        control_rung="haiku-solvable",
        another_way=SPREAD_OVER_SLOTS,
        not_an_answer=DEAL_THE_ARTISTS_OUT,
        careless=TRIM_BY_SKIPPING,
        answers=SPREAD_OUT,
    ),
    Pair(
        crux_id="settleup-settle-debts",
        control_id="settleup-apply-expense",
        module="settleup.py",
        crux_definition="def settle(",
        control_definition="def applied(",
        crux_rung="sonnet-only",
        control_rung="haiku-solvable",
        another_way=SETTLE_THROUGH_ONE_PERSON,
        not_an_answer=PAY_EVERYBODY_PRO_RATA,
        careless=APPLY_IN_PLACE,
        answers=SETTLED,
    ),
)

BY_PAIR = [pytest.param(pair, id=pair.crux_id) for pair in PAIRS]

TASK_IDS = tuple(
    task_id for pair in PAIRS for task_id in (pair.crux_id, pair.control_id)
)

BY_TASK = [pytest.param(task_id, id=task_id) for task_id in TASK_IDS]


def answering(module: str, definition: str, resolution: str) -> Callable[[Path], None]:
    """Replace a solution's added function with another resolution of it.

    The added function is the last thing in the module — that is what an
    agent's diff looks like too — so everything from where it starts is the
    part a different answer replaces.
    """

    def edit(workdir: Path) -> None:
        source = workdir / module
        head, marker, _ = source.read_text().partition(definition)
        assert marker, f"{module} has no {definition}"
        source.write_text(head + resolution, encoding="utf-8")

    return edit


def answer_of(task: Task, snippet: str, edit: Callable[[Path], None] | None) -> str:
    """What a resolution actually returns, run in a tree of its own.

    Grading says whether an answer is acceptable; this says what it is, which
    is the only way to show that two acceptable answers are two answers rather
    than one written twice.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-k9-") as name:
        tree = Path(name)
        shutil.copytree(SOLUTIONS / task.id, tree, dirs_exist_ok=True,
                        ignore=_BYTECODE)
        if edit is not None:
            edit(tree)
        return subprocess.run(
            [sys.executable, "-c", snippet],
            cwd=tree, capture_output=True, text=True, check=True, timeout=60,
        ).stdout


def added_lines(task: Task) -> int:
    """How much the reference solution writes, as a diff counts it."""
    return sum(
        1
        for line in solution_diff(task).splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def tasks() -> list[Task]:
    return [task_by_id(task_id) for task_id in TASK_IDS]


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


# --- three pairs, differing in crux depth and nothing else ----------------------


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_crux_task_plants_one_and_its_control_plants_none(pair: Pair) -> None:
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert declared(crux) == {"K9": "single"}
    assert declared(control) == {"K9": "none"}
    for task in (crux, control):
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"
        # Standalone tasks, not a family: a family holds repo/ byte-identical
        # and varies the prompt, and these two ask for different functions.
        assert task.construction is not None
        assert task.construction.family is None


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_pair_starts_from_the_same_repository(pair: Pair) -> None:
    """What makes the control a control: same terrain, same matrix cell, so a
    difference in outcome is a difference in what was asked, not in where it
    was asked. The family lint would check this if these were a family; they
    are not, so it is checked here."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    assert tree(crux.repo_dir) == tree(control.repo_dir)


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_control_is_a_comparable_amount_of_work(pair: Pair) -> None:
    """Matching size is part of what a control controls for: a one-line
    control beside a thirty-line crux task would be measuring how much there
    was to write rather than how much had to be decided."""
    crux = added_lines(task_by_id(pair.crux_id))
    control = added_lines(task_by_id(pair.control_id))

    assert 0.5 <= control / crux <= 2.0


def test_the_tasks_lint_clean() -> None:
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert len(touched) == 1
    assert task.scale == "single-file"


# --- the planted crux: several answers, and grading that accepts them -----------


@pytest.mark.parametrize("pair", BY_PAIR)
def test_a_second_resolution_of_the_crux_also_resolves(pair: Pair) -> None:
    """The K9 probe, and the one that decides whether the knob is what it says.

    A suite that accepted only the reference's algorithm would make the task a
    spec whose decision was made and never written down — unsolvable except by
    guessing the author — so a second, differently reasoned answer to the same
    open decision has to grade 1.0.
    """
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task, mutate=answering(pair.module, pair.crux_definition, pair.another_way)
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_two_resolutions_really_do_answer_differently(pair: Pair) -> None:
    """And the guard on the probe above. Two algorithms that happen to return
    the same thing would prove nothing about the grading suite's tolerance:
    what has to be shown is that it accepts two different answers, so both are
    run and their answers compared."""
    task = task_by_id(pair.crux_id)

    reference = answer_of(task, pair.answers, None)
    another = answer_of(
        task,
        pair.answers,
        answering(pair.module, pair.crux_definition, pair.another_way),
    )

    assert reference.strip() and reference != another


@pytest.mark.parametrize("pair", BY_PAIR)
def test_not_making_the_decision_does_not_resolve(pair: Pair) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference: the answer a reader arrives at by taking the obvious route
    and never treating the open decision as one satisfies everything about the
    change except the rule the decision exists to meet."""
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task, mutate=answering(pair.module, pair.crux_definition, pair.not_an_answer)
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize("pair", BY_PAIR)
def test_a_careless_reading_of_the_control_does_not_resolve(pair: Pair) -> None:
    """Nothing left to invent is not nothing left to get wrong: each control
    is probed with the slip a reader who skimmed one stated rule would make,
    so a control that graded anything would not be a control at all."""
    task = task_by_id(pair.control_id)
    diff = solution_diff(
        task, mutate=answering(pair.module, pair.control_definition, pair.careless)
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_k9_claim() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in."""
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: rung
        for pair in PAIRS
        for task_id, rung in (
            (pair.crux_id, pair.crux_rung),
            (pair.control_id, pair.control_rung),
        )
    }


@pytest.mark.parametrize("pair", BY_PAIR)
def test_every_pair_claims_the_crux_costs_a_rung(pair: Pair) -> None:
    """What the pairs jointly predict, stated once so a rung mistyped into a
    task reads as the contradiction it is. A crux task predicted no harder
    than its control would be claiming the knob does nothing, which is a
    result the sweep may deliver but not one an author may register."""
    assert RUNGS.index(pair.crux_rung) > RUNGS.index(pair.control_rung)


@pytest.mark.parametrize("task_id", BY_TASK)
def test_every_prediction_names_the_decision_it_turns_on(task_id: str) -> None:
    """A rationale is what a missed prediction teaches, and for K9 what it has
    to teach is which decision was expected to be the hard one — for a crux
    task the one left open, for a control the fact that none is."""
    task = task_by_id(task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale
    assert len(rationale.split()) >= 15
    assert any(word in rationale for word in ("open", "stated", "decision"))


# --- the ladder this knob is set on ---------------------------------------------


def test_the_k9_ladder_is_the_two_levels_the_design_note_names() -> None:
    """K9 got an enumerated ladder with these tasks, so a level off it is
    refused rather than recorded — reconciliation groups outcomes by level,
    and a free-text level is a group of one."""
    assert KNOB_LEVELS["K9"] == ("none", "single")

    with pytest.raises(ValidationError, match="not one of"):
        KnobActivation(id="K9", level="planted")
