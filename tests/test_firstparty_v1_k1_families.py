"""The K1 task families (tickets #17 and #18): several underlying changes,
each authored as three spec-completeness variants.

A family only isolates its knob if everything else is held constant, so that
is what these tests check first: each family's three variants ship
byte-identical starting repositories, grading suites and reference solutions,
and differ in their prompt and their declared K1 level alone. The first two of
those the task-set lint enforces for every family, so the per-family lint run
below carries them; the reference solutions live outside the task
directories, out of the lint's reach, and are compared here. The rest is what
every checked-in task has to prove — lints clean, reference solution grades
resolved, doing nothing grades unresolved — plus the pre-registration the
experiment rests on: each variant's difficulty prediction is pinned here, so
a sweep that disagrees is a visible miss rather than a quiet rewrite.

The families are deliberately unlike one another, because a knob that only
separates on one shape of decision has not been shown to be a knob. What they
share is the ladder: every one is written at all three K1 levels, over one
file, in one capability-matrix cell.
"""

from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    run_for,
    solution_diff,
    task_by_id,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import Rung, Task, evaluate, lint_task_set

# The K1 ladder, most complete spec first. A family's variants are named for
# their place on it: <stem>-l1 is written at LEVELS[0], and so on.
LEVELS = ("acceptance", "description", "intent")

# The operational difficulty ladder, easiest rung first, so that predictions
# can be compared as well as pinned.
RUNGS: tuple[Rung, ...] = ("haiku-solvable", "sonnet-only", "unsolved")

# The plausible-but-wrong answers, one per family: what a reader who took the
# obvious route and never opened the module would write. Each is appended to
# the same file that family's reference solution edits.
#
# Later layers win, and nothing else — no recursive section merge, no copying.
SHALLOW_MERGE = """

def merged(layers):
    settings = {}
    for layer in layers:
        settings.update(layer)
    return settings
"""

# Every count-and-unit found anywhere in the text, added up: the tolerances
# come out right and nothing whatever is refused.
FINDALL_SUM = r'''

import re


def parse(text):
    """How many seconds the duration written in `text` is worth."""
    return sum(
        int(count) * unit_seconds(unit)
        for count, unit in re.findall(r"(\d+)([A-Za-z])", text)
    )
'''

# Oldest lot first and the cost basis right, but a lot drawn down to nothing
# stays in the stock holding nothing, and an order larger than the stock is
# filled as far as it goes instead of being refused.
KEEP_EMPTY_LOTS = '''

def consume(lots, quantity):
    """The stock left after drawing `quantity` units, and what they cost."""
    remaining = []
    cost = 0
    left = quantity
    for lot in lots:
        drawn = min(left, lot.quantity)
        left -= drawn
        cost += drawn * lot.unit_cost
        remaining.append(lot._replace(quantity=lot.quantity - drawn))
    return tuple(remaining), cost
'''


class Family(NamedTuple):
    """One K1 family, and what is pinned about it here.

    `touched` is the single file its reference solution edits, which is also
    where `probe` — the plausible-but-wrong answer no variant may accept — is
    appended. `rungs` is the pre-registered prediction at each K1 level.
    """

    stem: str
    rungs: dict[str, Rung]
    touched: str
    probe: str


FAMILIES = (
    Family(
        stem="settings-merge-layers",
        rungs={
            "acceptance": "haiku-solvable",
            "description": "haiku-solvable",
            "intent": "sonnet-only",
        },
        touched="settings.py",
        probe=SHALLOW_MERGE,
    ),
    Family(
        stem="duration-parse-written",
        rungs={
            "acceptance": "haiku-solvable",
            "description": "haiku-solvable",
            "intent": "sonnet-only",
        },
        touched="duration.py",
        probe=FINDALL_SUM,
    ),
    Family(
        stem="inventory-consume-lots",
        rungs={
            "acceptance": "haiku-solvable",
            "description": "sonnet-only",
            "intent": "sonnet-only",
        },
        touched="inventory.py",
        probe=KEEP_EMPTY_LOTS,
    ),
)

BY_FAMILY = [pytest.param(family, id=family.stem) for family in FAMILIES]

BY_VARIANT = [
    pytest.param(family, f"{family.stem}-l{index}", id=f"{family.stem}-l{index}")
    for family in FAMILIES
    for index in (1, 2, 3)
]


def variants(family: Family) -> list[Task]:
    """The family's three task directories, in ladder order."""
    return [task_by_id(f"{family.stem}-l{index}") for index in (1, 2, 3)]


def tree(root: Path) -> dict[str, str]:
    """Every file under root, by relative path, for comparing whole trees."""
    return {
        str(path.relative_to(root)): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


# --- each family holds everything but K1 constant -------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_is_three_variants_of_one_change(family: Family) -> None:
    tasks = variants(family)

    assert len(tasks) == 3
    assert [declared(task)["K1"] for task in tasks] == list(LEVELS)
    for task in tasks:
        assert task.construction is not None
        assert task.construction.family == family.stem
        assert set(declared(task)) == {"K1"}
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_variant_ships_the_same_reference_solution(family: Family) -> None:
    """Self-contained copies rather than shared directories, so no run can be
    shaped by another variant — but identical copies, or the family would be
    varying the diff target as well as the spec. The repo/ and grading/ halves
    are the task-set lint's job now (below); the reference solutions sit
    outside the task directories, where the lint cannot see them."""
    [first, *rest] = variants(family)

    for task in rest:
        assert tree(SOLUTIONS / task.id) == tree(SOLUTIONS / first.id)


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_spec_ladder_runs_from_stated_to_unstated(family: Family) -> None:
    """K1 is spec completeness, so the three prompts have to differ, and to
    differ in the right direction: a longer intent-only prompt than the
    acceptance-level one would mean the ladder is upside down."""
    by_level = {declared(task)["K1"]: task.prompt for task in variants(family)}

    assert len(by_level) == 3
    assert len(by_level["acceptance"]) > len(by_level["description"])
    assert len(by_level["description"]) > len(by_level["intent"])


# --- every variant is a well-formed, solvable task ------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_lints_clean_as_a_whole(family: Family) -> None:
    """Which covers the family invariants too: one knob varied, each of its
    levels used once, and byte-identical starting repositories and grading
    suites across the three variants."""
    assert lint_task_set(variants(family)) == []


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    family: Family, task_id: str
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_declared_scale_matches_the_reference_solution(
    family: Family, task_id: str
) -> None:
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {family.touched}


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_a_plausible_wrong_answer_resolves_no_variant(
    family: Family, task_id: str
) -> None:
    """The honest-variant probe. Each family's wrong answer is where the
    obvious route arrives, and it satisfies the obvious part of the change; a
    variant it passed would be measuring the function's name rather than the
    spec's completeness."""
    task = task_by_id(task_id)

    def write_wrong_answer(workdir: Path) -> None:
        source = workdir / family.touched
        source.write_text(source.read_text() + family.probe)

    [record] = evaluate(
        [task],
        [run_for(task, workdir_diff(task, write_wrong_answer))],
        source="run-log",
    )

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_registered_rungs_are_the_familys_k1_claim(family: Family) -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in. What
    the families claim differs, and deliberately: where a family expects the
    step depends on which decision its description-level prompt still leaves
    open, and on whether the obvious answer gets that one wrong."""
    rungs = {
        declared(task)["K1"]: task.construction.prediction.rung
        for task in variants(family)
        if task.construction is not None
    }

    assert rungs == family.rungs


@pytest.mark.parametrize("family", BY_FAMILY)
def test_no_family_predicts_that_withholding_the_spec_makes_it_easier(
    family: Family,
) -> None:
    """The ladder-direction guard on the predictions themselves. Pinning each
    family's rungs says what that family claims; this says what no K1 family
    may claim, so a rung mistyped into a later variant reads as the
    contradiction it is rather than as the theory quietly running backwards."""
    predicted = [RUNGS.index(family.rungs[level]) for level in LEVELS]

    assert predicted == sorted(predicted)


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_prediction_says_why(family: Family) -> None:
    """A rationale is what a missed prediction teaches: which knob level was
    misjudged, and on what reasoning."""
    for task in variants(family):
        assert task.construction is not None
        assert len(task.construction.prediction.rationale.split()) >= 10
