"""The pilot K1 task family (ticket #17): settings-merge-layers, one
underlying change authored as three spec-completeness variants.

A family only isolates its knob if everything else is held constant, so that
is what these tests check first: the three variants ship byte-identical
starting repositories, grading suites and reference solutions, and differ in
their prompt and their declared K1 level alone. The first two of those the
task-set lint now enforces for every family, so the lint run below carries
them; the reference solutions live outside the task directories, out of the
lint's reach, and are compared here. The rest is what every
checked-in task has to prove — lints clean, reference solution grades
resolved, doing nothing grades unresolved — plus the pre-registration the
experiment rests on: each variant's difficulty prediction is pinned here, so
a sweep that disagrees is a visible miss rather than a quiet rewrite.
"""

from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    run_for,
    solution_diff,
    task_by_id,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import Task, evaluate, lint_task_set

FAMILY = "settings-merge-layers"

# Task id -> the K1 level its prompt is written at.
VARIANTS = {
    f"{FAMILY}-l1": "acceptance",
    f"{FAMILY}-l2": "description",
    f"{FAMILY}-l3": "intent",
}

# What a reader who never opened the module would write: later layers win,
# and nothing else. Used as the honest-variant probe below.
SHALLOW_MERGE = (
    "\n\ndef merged(layers):\n"
    "    settings = {}\n"
    "    for layer in layers:\n"
    "        settings.update(layer)\n"
    "    return settings\n"
)


def variants() -> list[Task]:
    return [task_by_id(task_id) for task_id in sorted(VARIANTS)]


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


# --- the family holds everything but K1 constant --------------------------------


def test_the_family_is_three_variants_of_one_change() -> None:
    tasks = variants()

    assert len(tasks) == 3
    for task in tasks:
        assert task.construction is not None
        assert task.construction.family == FAMILY
        assert declared(task) == {"K1": VARIANTS[task.id]}
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"


def test_every_variant_ships_the_same_reference_solution() -> None:
    """Self-contained copies rather than shared directories, so no run can be
    shaped by another variant — but identical copies, or the family would be
    varying the diff target as well as the spec. The repo/ and grading/ halves
    are the task-set lint's job now (below); the reference solutions sit
    outside the task directories, where the lint cannot see them."""
    [first, *rest] = variants()

    for task in rest:
        assert tree(SOLUTIONS / task.id) == tree(SOLUTIONS / first.id)


def test_the_spec_ladder_runs_from_stated_to_unstated() -> None:
    """K1 is spec completeness, so the three prompts have to differ, and to
    differ in the right direction: a longer intent-only prompt than the
    acceptance-level one would mean the ladder is upside down."""
    by_level = {declared(task)["K1"]: task.prompt for task in variants()}

    assert len(by_level) == 3
    assert len(by_level["acceptance"]) > len(by_level["description"])
    assert len(by_level["description"]) > len(by_level["intent"])


# --- every variant is a well-formed, solvable task ------------------------------


def test_the_family_lints_clean_as_a_whole() -> None:
    """Which covers the family invariants too: one knob varied, each of its
    levels used once, and byte-identical starting repositories and grading
    suites across the three variants."""
    assert lint_task_set(variants()) == []


@pytest.mark.parametrize("task_id", sorted(VARIANTS))
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


@pytest.mark.parametrize("task_id", sorted(VARIANTS))
def test_the_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {"settings.py"}


@pytest.mark.parametrize("task_id", sorted(VARIANTS))
def test_a_shallow_merge_does_not_resolve_any_variant(task_id: str) -> None:
    """The honest-variant probe. The shallow answer satisfies "later layers
    win" and nothing else; a variant it passed would be measuring the
    function's name rather than the spec's completeness."""
    task = task_by_id(task_id)

    def write_shallow_merge(workdir: Path) -> None:
        source = workdir / "settings.py"
        source.write_text(source.read_text() + SHALLOW_MERGE)

    [record] = evaluate(
        [task],
        [run_for(task, workdir_diff(task, write_shallow_merge))],
        source="run-log",
    )

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_familys_k1_claim() -> None:
    """Taking the decisions out of the prompt is predicted to move the task
    up the ladder, and to do it between description and intent rather than
    between acceptance and description. Pinned so the claim cannot be
    reinterpreted once the sweep is in."""
    rungs = {
        declared(task)["K1"]: task.construction.prediction.rung
        for task in variants()
        if task.construction is not None
    }

    assert rungs == {
        "acceptance": "haiku-solvable",
        "description": "haiku-solvable",
        "intent": "sonnet-only",
    }


def test_every_prediction_says_why() -> None:
    """A rationale is what a missed prediction teaches: which knob level was
    misjudged, and on what reasoning."""
    for task in variants():
        assert task.construction is not None
        assert len(task.construction.prediction.rationale.split()) >= 10
