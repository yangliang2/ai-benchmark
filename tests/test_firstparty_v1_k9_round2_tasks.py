"""K9's round-2 pairs, whose cruxes no named algorithm resolves (ticket #33).

Round 1 swept three K9 pairs and the knob was silent on the rung: all six
tasks resolved on both models. It also carried a confound the verdicts named
— every one of those cruxes was a textbook problem wearing a domain costume
(bin packing, rearrange-k-apart, debt simplification), so a solver who
recognised the shape was handed the decision the task was built to withhold,
and what the pairs measured may have been recall. These three pairs are the
remaining sweep with that confound removed. Each plants a decision that is a
policy rather than a problem: how to split shared downtime between overlapping
faults, which of two systems a disputed address survives from, which entries a
digest keeps when a gap costs a place of its own. Every crux task's authoring
comment argues its own case, and the last test here holds it to doing so.

What a planted crux costs is a grading suite that cannot name the answer, and
the probes below prove both directions of that the only way that settles it:
for every crux task two genuinely different resolutions — different
constructions, and asserted to return different answers rather than merely to
be spelled differently — each grade 1.0, while the answer a reader arrives at
by never treating the open decision as one grades 0.0. Each non-answer here is
the reflex the domain suggests: charge every fault for all the downtime it was
over, take every field from the record seen more recently, drop entries until
the count fits. The controls are probed with the slip a careless reader of a
fully stated spec makes, so that "nothing left to invent" cannot quietly mean
"nothing left to get wrong" — and so is a crux, wherever a rule it does state
outright has a near reading that is wrong, since a crux's tolerance is meant
to reach one decision and no further.

A sibling of `test_firstparty_v1_k9_tasks.py` rather than an extension of it,
for two reasons that both come out of the round-1 verdicts. That suite pins
`test_every_pair_claims_the_crux_costs_a_rung` — every crux registered a rung
above its control — and round 2's calibration lesson is the opposite
instruction: bet at the bottom of the ladder unless there is a specific
mechanism, since the round's authors went 0 for 12 on "this knob makes it
harder" outside K1. Registering these six honestly means all six at
haiku-solvable, which that assertion refuses; weakening it would edit what
round 1 registered, and what round 1 registered is evidence. And these cruxes
carry effort claims, which round 1's do not: the difficulty bet has moved axis,
and pinning it needs tests of its own either way.

The assertion that every K9 pair in the task set is probed by one suite or
another was written here and now lives in the round-3 suite (#39), which is
the only one able to see all three registries: keeping a copy here would take
importing round 3's, which imports this module's, and a second answer to one
question is free to disagree with the first.
"""

import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    TASKS,
    copy_solution,
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
)

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    EffortClaim,
    Rung,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)

# --- the crux, resolved a second way -------------------------------------------

LEVEL_THE_BLAME_OUT = '''def blame(faults):
    """Level the blame: a contested minute goes to whichever of the faults
    covering it is carrying the least so far."""
    charged = {fault.name: 0 for fault in faults}
    for start, end in spans(faults):
        for minute in range(start, end):
            over = sorted(fault.name for fault in faults if minute in stretch(fault))
            charged[min(over, key=lambda name: (charged[name], name))] += 1
    return charged
'''

TAKE_THE_ADDRESS_FROM_THE_FULLER_RECORD = '''def merge(one, other):
    """The two dossiers as one record: field to a (value, source) pair.

    The policy chosen for a disputed address: the record that knows more about
    the customer overall supplies it, on the grounds that the fuller record is
    the better-kept one, with the more recently seen preferred where the two
    know as much as each other.
    """
    if one.seen == other.seen:
        raise ValueError("neither of them is the later record")
    later, earlier = sorted((one, other), key=lambda dossier: -dossier.seen)
    record = {}
    for field in FIELDS:
        for dossier in (later, earlier):
            if value(dossier, field) is not None:
                record[field] = (value(dossier, field), dossier.source)
                break
    if not disagree(one, other, ADDRESS):
        return record
    fullest = sorted(
        (later, earlier), key=lambda dossier: (-len(known(dossier)), -dossier.seen)
    )
    complete = [
        dossier
        for dossier in fullest
        if all(
            value(dossier, field) is not None for field in ADDRESS if field in record
        )
    ]
    if not complete:
        raise ValueError("neither of them holds the whole of the address")
    taken = complete[0]
    for field in ADDRESS:
        if field in record:
            record[field] = (value(taken, field), taken.source)
    return record
'''

KEEP_WHATEVER_IS_CHEAPEST = '''def digest(entries, budget):
    """The run cut down to `budget` places, gaps counting as places.

    The policy chosen: whatever is cheapest to keep. Keeping an entry beside
    one already kept costs a place, keeping one out of the middle of a stretch
    costs two, and keeping the only entry of a stretch costs nothing at all —
    so the digest takes the cheapest entry still going, over and over, until
    nothing more fits.
    """
    if not entries:
        return []
    kept = {0, len(entries) - 1}
    kept.update(position for position, entry in enumerate(entries) if entry.important)
    least = len(_laid_out(entries, kept))
    if least > budget:
        raise ValueError(
            f"a digest of these {len(entries)} entries needs at least {least} "
            f"places, and the budget is {budget}"
        )
    while True:
        affordable = sorted(
            (len(_laid_out(entries, kept | {position})), position)
            for position in range(len(entries))
            if position not in kept
        )
        going = [entry for entry in affordable if entry[0] <= budget]
        if not going:
            return _laid_out(entries, kept)
        kept.add(going[0][1])
'''


# --- the answer arrived at by not making the decision ---------------------------

CHARGE_EVERY_FAULT_FOR_ITS_OWN_STRETCH = '''def blame(faults):
    """What each fault is on the hook for: the minutes its own stretch
    covers."""
    return {fault.name: len(stretch(fault)) for fault in faults}
'''

TAKE_EVERY_FIELD_FROM_THE_LATER_RECORD = '''def merge(one, other):
    """The two dossiers as one record: every field from whichever of them saw
    the customer more recently and holds anything for it."""
    if one.seen == other.seen:
        raise ValueError("neither of them is the later record")
    later, earlier = sorted((one, other), key=lambda dossier: -dossier.seen)
    record = {}
    for field in FIELDS:
        for dossier in (later, earlier):
            if value(dossier, field) is not None:
                record[field] = (value(dossier, field), dossier.source)
                break
    return record
'''

DROP_ENTRIES_UNTIL_THE_COUNT_FITS = '''def digest(entries, budget):
    """The run cut down to `budget` places: keep what has to be kept, and drop
    the oldest of the rest until what is left fits."""
    if not entries:
        return []
    required = {0, len(entries) - 1}
    required.update(
        position for position, entry in enumerate(entries) if entry.important
    )
    if len(required) > budget:
        raise ValueError(
            f"a digest of these {len(entries)} entries needs at least "
            f"{len(required)} places, and the budget is {budget}"
        )
    kept = set(range(len(entries)))
    for position in range(len(entries)):
        if len(kept) <= budget:
            break
        if position not in required:
            kept.discard(position)
    return _laid_out(entries, kept)
'''


# --- the slip a careless reader of a rule the crux does state makes -------------

# A crux task states rules too, and one of the dossier crux's is a bar with a
# near reading that is wrong: a disputed address may only be taken from a
# record that holds every address field *either of them holds*, which is not
# the same as one that holds all three. Where neither record has a postcode,
# the bar is a street and a town, both of them clear it, and this reading
# refuses a merge the rules allow.
DEMAND_A_WHOLE_ADDRESS_OF_A_CANDIDATE = '''\
def merge(one, other):
    """The two dossiers as one record: field to a (value, source) pair.

    The reference's policy for a disputed address — the record seen more
    recently supplies it — with the bar a record has to clear to supply it
    read as all three address fields.
    """
    if one.seen == other.seen:
        raise ValueError("neither of them is the later record")
    later, earlier = sorted((one, other), key=lambda dossier: -dossier.seen)
    record = {}
    for field in FIELDS:
        for dossier in (later, earlier):
            if value(dossier, field) is not None:
                record[field] = (value(dossier, field), dossier.source)
                break
    if not disagree(one, other, ADDRESS):
        return record
    complete = [
        dossier
        for dossier in (later, earlier)
        if all(value(dossier, field) is not None for field in ADDRESS)
    ]
    if not complete:
        raise ValueError("neither of them holds the whole of the address")
    taken = complete[0]
    for field in ADDRESS:
        if field in record:
            record[field] = (value(taken, field), taken.source)
    return record
'''


# --- the slips a careless reader of a fully stated spec makes --------------------

WALK_STRAIGHT_PAST_THE_WINDOW = '''def quiet(faults, start, end):
    """The stretches of the window from `start` to `end` nothing was
    covering."""
    if end < start:
        raise ValueError(f"a window cannot end at {end}, before it starts at {start}")
    free = []
    at = start
    for down_from, down_to in spans(faults):
        if down_to <= at:
            continue
        if down_from > at:
            free.append((at, down_from))
        at = max(at, down_to)
    if at < end:
        free.append((at, end))
    return free
'''

RECORD_THE_BLANK_INSTEAD_OF_FORGETTING_IT = '''\
def apply_correction(dossier, corrections, seen):
    """What `dossier` holds with `corrections` applied, and what that
    changed."""
    if seen <= dossier.seen:
        raise ValueError(
            f"a correction seen at {seen} is no later than {dossier.source}'s "
            f"own {dossier.seen}"
        )
    for field in corrections:
        if field not in FIELDS:
            raise ValueError(f"{field} is not one of the fields a dossier holds")
    held = {field: value(dossier, field) for field in known(dossier)}
    corrected = dict(held)
    corrected.update(corrections)
    changes = [
        (field, held.get(field), corrected.get(field))
        for field in FIELDS
        if held.get(field) != corrected.get(field)
    ]
    return Dossier(dossier.source, seen, corrected), changes
'''

# A second slip on the same control, and a different one rather than a farther
# one: the correction is made in the mapping the dossier arrived with. The
# record that comes back is right in every particular, and the one that was
# handed in has been rewritten underneath its owner — and a field that was
# sitting there blank before the call is still sitting there afterwards.
WORK_IN_THE_DOSSIERS_OWN_MAPPING = '''def apply_correction(dossier, corrections, seen):
    """What `dossier` holds with `corrections` applied, and what that
    changed."""
    if seen <= dossier.seen:
        raise ValueError(
            f"a correction seen at {seen} is no later than {dossier.source}'s "
            f"own {dossier.seen}"
        )
    for field in corrections:
        if field not in FIELDS:
            raise ValueError(f"{field} is not one of the fields a dossier holds")
    held = {field: value(dossier, field) for field in known(dossier)}
    corrected = dossier.fields
    for field, recorded in corrections.items():
        if recorded:
            corrected[field] = recorded
        else:
            corrected.pop(field, None)
    changes = [
        (field, held.get(field), corrected.get(field))
        for field in FIELDS
        if held.get(field) != corrected.get(field)
    ]
    return Dossier(dossier.source, seen, corrected), changes
'''

MATCH_THE_MESSAGES_BY_TEXT = '''def merge_runs(left, right):
    """The two runs as one run in time order, and what the two had in
    common."""
    for name, run in (("left", left), ("right", right)):
        for earlier, later in zip(run, run[1:]):
            if later.at < earlier.at:
                raise ValueError(
                    f"the {name} run has an entry at {later.at} following one "
                    f"at {earlier.at}, so it is not in time order"
                )
    said_on_the_left = {entry.text for entry in left}
    said_on_the_right = {entry.text for entry in right}
    shared = [entry for entry in left if entry.text in said_on_the_right]
    waiting = [entry for entry in right if entry.text not in said_on_the_left]
    merged = []
    for entry in left:
        while waiting and waiting[0].at < entry.at:
            merged.append(waiting.pop(0))
        merged.append(entry)
    merged.extend(waiting)
    return merged, shared
'''


# --- what each resolution actually answers, run for real ------------------------

# Printed from inside a solution tree, on the case each pair's two resolutions
# were built to come apart on.
CHARGED = """
from outage import Fault, blame

faults = [Fault("power", 0, 6), Fault("net", 4, 10), Fault("dns", 8, 14)]
print(sorted(blame(faults).items()))
"""

MERGED = """
from dossier import Dossier, merge

crm = Dossier("crm", 300, {"owner": "ben", "street": "9 Mill Lane",
                           "town": "Wick", "postcode": "AB2 3EF"})
billing = Dossier("billing", 200, {"owner": "ben", "note": "pays late",
                                   "street": "4 Quay Road", "town": "Wick",
                                   "postcode": "AB9 9ZZ"})
print(sorted(merge(crm, billing).items()))
"""

DIGESTED = """
from digest import Entry, digest, render

run = [
    Entry(1, "started", False), Entry(2, "loaded config", False),
    Entry(3, "cache warm", False), Entry(4, "disk full", True),
    Entry(5, "retrying", False), Entry(6, "retrying again", False),
    Entry(7, "recovered", True), Entry(8, "steady", False),
    Entry(9, "steady still", False), Entry(10, "steady yet", False),
    Entry(11, "stopping", False), Entry(12, "done", False),
]
print(render(digest(run, 9)))
"""


class Bend(NamedTuple):
    """One careless answer, under the name a probe failure reports it by."""

    name: str
    answer: str


class Probes(NamedTuple):
    """How one pair is examined, which is the part no metadata could carry.

    `module` is the file both tasks' reference solutions add a function to,
    and `crux_definition` / `control_definition` are where those added
    functions start — which is what lets a probe swap one answer for another.
    `another_way` and `not_an_answer` are the crux task's two probes,
    `careless` holds the control's, `answers` prints the crux task's answer so
    two resolutions can be compared, and `rung` and `at_least_factor` are the
    pre-registered prediction. `misread` is the crux task's own careless
    reading, which is a different thing from `not_an_answer`: a rule the crux
    states outright, read wrongly, rather than the decision it leaves open
    never being treated as one.

    `careless` and `misread` are tuples for the reason the K11 suite's is: a
    slip found later was always possible, and once the held-out suite has been
    shown to catch one it is registered here so it goes on being asked about.
    """

    module: str
    crux_definition: str
    control_definition: str
    rung: Rung
    at_least_factor: float
    another_way: str
    not_an_answer: str
    careless: tuple[Bend, ...]
    answers: str
    misread: tuple[Bend, ...] = ()


PROBES: dict[str, Probes] = {
    "outage": Probes(
        module="outage.py",
        crux_definition="def blame(",
        control_definition="def quiet(",
        rung="haiku-solvable",
        at_least_factor=1.25,
        another_way=LEVEL_THE_BLAME_OUT,
        not_an_answer=CHARGE_EVERY_FAULT_FOR_ITS_OWN_STRETCH,
        careless=(
            Bend("walk-straight-past-the-window", WALK_STRAIGHT_PAST_THE_WINDOW),
        ),
        answers=CHARGED,
    ),
    "dossier": Probes(
        module="dossier.py",
        crux_definition="def merge(",
        control_definition="def apply_correction(",
        rung="haiku-solvable",
        at_least_factor=1.25,
        another_way=TAKE_THE_ADDRESS_FROM_THE_FULLER_RECORD,
        not_an_answer=TAKE_EVERY_FIELD_FROM_THE_LATER_RECORD,
        careless=(
            Bend(
                "record-the-blank-instead-of-forgetting-it",
                RECORD_THE_BLANK_INSTEAD_OF_FORGETTING_IT,
            ),
            Bend("work-in-the-dossiers-own-mapping", WORK_IN_THE_DOSSIERS_OWN_MAPPING),
        ),
        answers=MERGED,
        misread=(
            Bend(
                "demand-a-whole-address-of-a-candidate",
                DEMAND_A_WHOLE_ADDRESS_OF_A_CANDIDATE,
            ),
        ),
    ),
    "digest": Probes(
        module="digest.py",
        crux_definition="def digest(",
        control_definition="def merge_runs(",
        rung="haiku-solvable",
        at_least_factor=1.25,
        another_way=KEEP_WHATEVER_IS_CHEAPEST,
        not_an_answer=DROP_ENTRIES_UNTIL_THE_COUNT_FITS,
        careless=(Bend("match-the-messages-by-text", MATCH_THE_MESSAGES_BY_TEXT),),
        answers=DIGESTED,
    ),
}


class Pair(NamedTuple):
    """One planted-crux task, its zero-crux control, and how they are probed.

    Which two tasks those are is read off the task set rather than written
    down here: the pairing is construction metadata, and a table of it in the
    suite would be a second copy free to disagree with the tasks themselves.
    """

    crux_id: str
    control_id: str
    probes: Probes


def _pairs() -> tuple[Pair, ...]:
    """The pairs this suite probes, assembled from what each side knows.

    The task set says which tasks a pair id groups and which of them plants
    the crux — that is what its K9 level means — so nothing but the probes
    themselves is named here.
    """
    grouped: dict[str, dict[str, str]] = {}
    for task in load_task_set(TASKS):
        construction = task.construction
        if construction is None or construction.pair is None:
            continue
        grouped.setdefault(construction.pair, {})[
            construction.levels.get("K9", "")
        ] = task.id

    pairs = []
    for pair, probes in sorted(PROBES.items()):
        members = grouped.get(pair, {})
        assert set(members) == {"none", "single"}, (
            f"pair {pair!r} is not one K9 crux task and one control: {members}"
        )
        pairs.append(Pair(members["single"], members["none"], probes))
    return tuple(pairs)


PAIRS = _pairs()

BY_PAIR = [pytest.param(pair, id=pair.crux_id) for pair in PAIRS]

BY_BEND = [
    pytest.param(pair, bend, id=f"{pair.control_id}-{bend.name}")
    for pair in PAIRS
    for bend in pair.probes.careless
]

BY_MISREADING = [
    pytest.param(pair, bend, id=f"{pair.crux_id}-{bend.name}")
    for pair in PAIRS
    for bend in pair.probes.misread
]

TASK_IDS = tuple(
    task_id for pair in PAIRS for task_id in (pair.crux_id, pair.control_id)
)

BY_TASK = [pytest.param(task_id, id=task_id) for task_id in TASK_IDS]


def answering(module: str, definition: str, resolution: str) -> Callable[[Path], None]:
    """Replace a solution's added function with another answer to it.

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
    with tempfile.TemporaryDirectory(prefix="ai-bench-k9r2-") as name:
        tree = Path(name)
        copy_solution(task, tree)
        if edit is not None:
            edit(tree)
        return subprocess.run(
            [sys.executable, "-c", snippet],
            cwd=tree, capture_output=True, text=True, check=True,
            timeout=GRADE_TIMEOUT_S,
        ).stdout


def added_lines(task: Task) -> int:
    """How much the reference solution writes, as a diff counts it."""
    return sum(
        1
        for line in solution_diff(task).splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def authoring_comment(task_id: str) -> str:
    """The comment block a task.yaml opens with, which is where a K9 author
    argues the case for the crux they planted."""
    lines = (TASKS / task_id / "task.yaml").read_text().splitlines()
    return "\n".join(
        line.lstrip("#").strip()
        for line in lines[: next(i for i, line in enumerate(lines) if line[:1] != "#")]
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
        # What does group them, and what this suite reads the pairing off.
        assert task.construction.pair in PROBES


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_pair_starts_from_the_same_repository(pair: Pair) -> None:
    """What makes the control a control: same terrain, same matrix cell, so a
    difference in outcome is a difference in what was asked, not in where it
    was asked. The pair lint checks it across the whole task set; it is
    checked here too, against these six directly."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    assert tree(crux.repo_dir) == tree(control.repo_dir)


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_two_prompts_ask_for_different_things(pair: Pair) -> None:
    """The other half of what the pair holds constant. Everything in the
    repository is identical between the two, so the prompt is the whole of
    what moved, and two members sharing one would be a pair with no
    contrast in it at all."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert crux.prompt != control.prompt


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_control_is_a_comparable_amount_of_work(pair: Pair) -> None:
    """Matching size is part of what a control controls for: a one-line
    control beside a thirty-line crux task would be measuring how much there
    was to write rather than how much had to be decided."""
    crux = added_lines(task_by_id(pair.crux_id))
    control = added_lines(task_by_id(pair.control_id))

    assert 0.5 <= control / crux <= 2.0


def test_the_tasks_lint_clean() -> None:
    """Linted on their own, which these can be: every effort claim registered
    here is read against a pair partner that is in this same set, so no rule
    the lint applies asks about tasks outside it."""
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


@pytest.mark.parametrize("task_id", BY_TASK)
def test_the_repository_starts_out_green_and_stays_green(task_id: str) -> None:
    """The net the agent inherits passes, and goes on passing once the change
    is made: a K9 crux withholds a decision, never a warning, so nothing the
    agent can run is misleading about the work it has already done."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


# --- the planted crux: several answers, and grading that accepts them -----------


@pytest.mark.parametrize("pair", BY_PAIR)
def test_a_second_resolution_of_the_crux_also_resolves(pair: Pair) -> None:
    """The K9 probe, and the one that decides whether the knob is what it says.

    A suite that accepted only the reference's policy would make the task a
    spec whose decision was made and never written down — unsolvable except by
    guessing the author — so a second, differently reasoned answer to the same
    open decision has to grade 1.0.
    """
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.another_way
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_two_resolutions_really_do_answer_differently(pair: Pair) -> None:
    """And the guard on the probe above. Two policies that happen to return
    the same thing would prove nothing about the grading suite's tolerance:
    what has to be shown is that it accepts two different answers, so both are
    run and their answers compared."""
    task = task_by_id(pair.crux_id)

    reference = answer_of(task, pair.probes.answers, None)
    another = answer_of(
        task,
        pair.probes.answers,
        answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.another_way
        ),
    )

    assert reference.strip() and reference != another


@pytest.mark.parametrize("pair", BY_PAIR)
def test_not_making_the_decision_does_not_resolve(pair: Pair) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference: the answer a reader arrives at by taking the route the
    domain suggests and never treating the open decision as one satisfies
    everything about the change except the rule the decision exists to
    meet."""
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.crux_definition, pair.probes.not_an_answer
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize(("pair", "bend"), BY_MISREADING)
def test_a_careless_reading_of_the_crux_does_not_resolve(
    pair: Pair, bend: Bend
) -> None:
    """The crux tasks state rules too, and everything a crux states outright
    its grading suite has to hold it to. A suite that let a stated rule through
    would be a suite tolerating more than the one decision the task leaves
    open, and the tolerance the K9 probes above demonstrate would be that much
    less evidence that what the crux withholds is a decision rather than a
    reading."""
    task = task_by_id(pair.crux_id)
    diff = solution_diff(
        task,
        mutate=answering(pair.probes.module, pair.probes.crux_definition, bend.answer),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize(("pair", "bend"), BY_BEND)
def test_a_careless_reading_of_the_control_does_not_resolve(
    pair: Pair, bend: Bend
) -> None:
    """Nothing left to invent is not nothing left to get wrong: each control
    is probed with the slip a reader who skimmed one stated rule would make,
    so a control that graded anything would not be a control at all."""
    task = task_by_id(pair.control_id)
    diff = solution_diff(
        task,
        mutate=answering(
            pair.probes.module, pair.probes.control_definition, bend.answer
        ),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_k9_round_two_claim() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    All six sit at the bottom of the ladder, and that is the round-1
    calibration lesson applied rather than an author's modesty: outside K1 the
    round's record on "this knob makes the task harder" was 0 for 12, and K9's
    own three pairs all resolved on both models. What round 1 did find on
    these pairs was an effort difference, so that is where the difficulty
    claim is registered instead — below.
    """
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: pair.probes.rung
        for pair in PAIRS
        for task_id in (pair.crux_id, pair.control_id)
    }
    assert set(registered.values()) == {"haiku-solvable"}


def test_the_registered_effort_claims_carry_the_difficulty_bet() -> None:
    """What these pairs actually bet, and the half a sweep can take off them.

    Against the pair partner rather than the baseline, because a partner is a
    version-matched within-round contrast and the frozen baseline is the
    weakest comparator this experiment has — round 1's own anomaly 2. On turns
    rather than cost, because turns is what the runner measures without a
    price list in it.

    The factor is grounded in what round 1 measured on exactly this contrast,
    and deliberately below it: matched K9 pairs came in at 1.80x haiku turns
    and 1.36x sonnet, and one pair of the three was flat on both. Registering
    1.80 would be betting that a mean of three reproduces per model on new
    tasks; registering 1.25 bets the direction and the smaller of the two
    measured multiples, which the flat pair says can still lose.
    """
    registered = {
        task.id: task.construction.prediction.effort
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: claim
        for pair in PAIRS
        for task_id, claim in (
            (
                pair.crux_id,
                EffortClaim(
                    comparator="pair",
                    metric="turns",
                    at_least_factor=pair.probes.at_least_factor,
                ),
            ),
            (pair.control_id, None),
        )
    }


@pytest.mark.parametrize("pair", BY_PAIR)
def test_the_effort_claim_is_held_by_the_member_with_the_crux_in_it(
    pair: Pair,
) -> None:
    """A direction guard, so that a claim registered on the wrong member reads
    as the contradiction it is rather than as the theory quietly running the
    other way. A pair comparator is symmetric — either member could name the
    other — and a control claiming to cost more turns than the crux beside it
    would be K9 registered upside down."""
    crux, control = task_by_id(pair.crux_id), task_by_id(pair.control_id)

    assert crux.construction is not None and control.construction is not None
    claim = crux.construction.prediction.effort
    assert claim is not None and claim.at_least_factor > 1.0
    assert control.construction.prediction.effort is None


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


@pytest.mark.parametrize("pair", BY_PAIR)
def test_every_crux_argues_why_recalling_an_algorithm_would_not_resolve_it(
    pair: Pair,
) -> None:
    """The requirement that distinguishes round 2's K9 pairs from round 1's,
    held to where an author would otherwise be trusted for it.

    Round 1's three cruxes were bin packing, rearrange-k-apart and debt
    simplification, so the decision each withheld was one a solver could be
    handed by recognising the shape, and the round could not tell invention
    from recall. A crux registered here has to make the case in its own
    task.yaml that no named algorithm resolves it — which the sweep cannot
    check and a reader of the task alone would have to take on trust.
    """
    comment = authoring_comment(pair.crux_id)

    assert "recall" in comment
    assert "textbook" in comment
    assert len(comment.split()) >= 80
