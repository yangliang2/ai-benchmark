"""Round 7's three TypeScript `refactor` tasks (ticket #109): three fresh
hand-authored repositories, each with one restructuring asked of it, graded by
`node --test` through the same execution-verified pipeline a real run goes
through.

Parametrised over the three the way the Python refactor suite is
(`tests/test_firstparty_v1_refactor_tasks.py`): each lints clean, each
reference solution grades resolved and the empty diff unresolved, each declared
`scale` is honest against its solution's diff, and each visible suite passes on
the pristine repository — which is what makes the README's `node --test` a net
the agent actually inherits rather than a claim.

What this suite adds to the feature-dev one, and the whole reason a refactor
task is a different shape, is the **split**: the behaviour half passes on the
pristine repository and the structural half fails on it, and each is asserted
on its own rather than through a verdict that runs the two together. A
behaviour-breaking restructure — the refactor acceptance criterion — is graded
here too, for two of the three: a diff that satisfies every structural
assertion and bends behaviour anyway must come out 0.0.

Every structural assertion these three ship is about **runtime shape** and none
is about a type, because nothing type-checks at grade time: `tsc` is not
installed and would be a dependency. That is asserted twice over — once as a
property of the bytes (no type-level device is reached for in a structural
file) and once as the property that actually matters, that the structural half
alone tells the pristine tree from the solved one.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    TASKS,
    run_for,
    solution_diff,
    structural_half_passes,
    task_by_id,
    visible_tests_pass,
)

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Task,
    _run_grading,
    evaluate,
    lint_task_set,
    load_task_set,
)
from ai_benchmark.language_runners import TYPESCRIPT

# Task id -> the scale its reference solution honestly has.
TS_REFACTOR_TASKS: dict[str, str] = {
    "courtleet-put-the-verdicts-on-one-table": "single-file",
    "gasworks-take-the-press-out-of-the-roll-room": "cross-file",
    "tollhouse-take-the-writing-of-a-pass-off-the-ticket": "cross-file",
}

TASK_IDS = sorted(TS_REFACTOR_TASKS)

# Task id -> a string out of the mechanism its scenario is built on. Each is
# this ticket's claim that the scenario is fresh, held to the bytes below: a
# compressed store, a pass carried as a URL, and a rule run in a context of its
# own — none of them a scenario tickets 08-11 took.
SCENARIO_MECHANISM: dict[str, str] = {
    "courtleet-put-the-verdicts-on-one-table": "node:vm",
    "gasworks-take-the-press-out-of-the-roll-room": "node:zlib",
    "tollhouse-take-the-writing-of-a-pass-off-the-ticket": "searchParams",
}

# What a structural assertion may not be reaching for. Every one of these is
# erased before anything runs, so an assertion resting on one would assert
# nothing at grade time — which is exactly the failure mode this ticket rules
# out by deciding that a structural test asserts on runtime shape.
TYPE_LEVEL_DEVICES = ("import type", "interface ", " satisfies ", " as unknown")


def structural_test_paths(task: Task) -> list[str]:
    """The half of the grading suite that says the restructuring happened."""
    return sorted(set(task.grading_test_paths) - set(task.behaviour_test_paths))


# --- the three tasks as declared ------------------------------------------------


def test_the_three_tasks_are_checked_in_and_annotated() -> None:
    """The declaration the round is defined by: zero-knob TypeScript controls
    with no construction block, each with a reference solution outside its own
    task directory."""
    tasks = [task for task in load_task_set(TASKS) if task.id in TS_REFACTOR_TASKS]

    assert sorted(task.id for task in tasks) == TASK_IDS
    for task in tasks:
        assert task.category == "refactor"
        assert task.language == "typescript"
        assert task.runner is TYPESCRIPT
        assert task.surface == "application"
        assert task.control is True
        assert task.construction is None
        assert task.scale == TS_REFACTOR_TASKS[task.id]
        assert (SOLUTIONS / task.id).is_dir()
    # Both scales are represented; per-task honesty is asserted mechanically
    # against each reference solution's diff below.
    assert {task.scale for task in tasks} == {"single-file", "cross-file"}


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_names_a_behaviour_half_and_ships_a_structural_one(
    task_id: str,
) -> None:
    """The shape that makes it a refactor task at all: `task.yaml` names the
    behaviour tests, and something in `grading/` is not one of them."""
    task = task_by_id(task_id)

    assert task.behaviour_test_paths
    assert structural_test_paths(task)
    for name in task.grading_test_paths:
        assert name.endswith(".test.ts"), (
            f"{task_id}: {name} is not a file this task's runner collects"
        )


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_lints_clean(task_id: str) -> None:
    assert lint_task_set([task_by_id(task_id)]) == []


# --- the stdlib-only repository the agent is handed -----------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_repository_ships_a_visible_suite_and_a_readme_naming_node_test(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    visible = sorted(task.repo_dir.glob(TYPESCRIPT.visible_test_glob))

    assert visible, f"{task_id} ships no visible tests for the agent to inherit"
    readme = (task.repo_dir / "README.md").read_text(encoding="utf-8")
    assert "node --test" in readme


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_repository_installs_nothing(task_id: str) -> None:
    """ADR-0003 held to the bytes, beside the lint that also refuses it: no
    manifest and no vendored dependency tree, at any depth of either tree the
    agent or the grader sees."""
    task = task_by_id(task_id)

    for tree in (task.repo_dir, task.grading_dir, SOLUTIONS / task.id):
        assert not sorted(tree.rglob("package.json"))
        assert not sorted(tree.rglob("node_modules"))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_visible_suite_passes_on_the_pristine_repository(task_id: str) -> None:
    """The net the agent inherits is green before it starts: the repository's
    own `*.test.ts` files, run the way its README says to run them."""
    assert visible_tests_pass(task_by_id(task_id))


def test_each_scenario_is_one_no_other_typescript_task_takes() -> None:
    """The freshness claim, held to the bytes rather than to the prose: the
    mechanism each scenario is built on appears in that task's repository and
    in no other TypeScript task's — so none of the three repeats a scenario
    tickets 08-11 already spent."""
    typescript = [task for task in load_task_set(TASKS) if task.runner is TYPESCRIPT]

    for task_id, mechanism in SCENARIO_MECHANISM.items():
        taking = {
            task.id
            for task in typescript
            for source in task.repo_dir.rglob(TYPESCRIPT.source_glob)
            if mechanism in source.read_text(encoding="utf-8")
        }
        assert taking == {task_id}, f"{mechanism} is not {task_id}'s alone"


# --- solved, untouched, and the split itself ------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_resolves_and_doing_nothing_does_not(task_id: str) -> None:
    """Through the real pipeline: the solved tree's diff resolves, and the diff
    a run that wrote nothing would log does not."""
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    """Scale is honest to the canonical solution: a single-file solution
    touches exactly one file, a cross-file one touches several."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    if task.scale == "single-file":
        assert len(touched) == 1
    else:
        assert len(touched) > 1


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_behaviour_half_passes_on_the_pristine_repository(task_id: str) -> None:
    """Half the split, asserted on its own: what the restructuring must not
    change already works, so the task starts from behaviour that is right."""
    task = task_by_id(task_id)

    assert _run_grading(
        task, "", list(task.behaviour_test_paths), timeout_s=GRADE_TIMEOUT_S
    )


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_structural_half_alone_rejects_pristine_and_accepts_the_solution(
    task_id: str,
) -> None:
    """The other half, and the assertion this suite exists for: the structural
    tests, run without the behaviour ones to carry them, fail on the pristine
    repository and pass on the reference solution. That is what says the
    restructuring happened, and it is also what proves those assertions are
    about runtime shape — a type-level claim could tell neither tree from the
    other, since nothing type-checks at grade time."""
    task = task_by_id(task_id)

    assert not structural_half_passes(task, "")
    assert structural_half_passes(task, solution_diff(task))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_no_structural_assertion_reaches_for_a_type(task_id: str) -> None:
    """The same rule read off the bytes: a structural test asserts on what
    exists and what is called at run time, and never on a declaration — every
    one of these devices is erased before anything runs, so an assertion
    resting on one would assert nothing at all."""
    task = task_by_id(task_id)

    for name in structural_test_paths(task):
        source = (task.grading_dir / name).read_text(encoding="utf-8")
        for device in TYPE_LEVEL_DEVICES:
            assert device not in source, (
                f"{task_id}: the structural test {name} reaches for {device!r}, "
                "which is erased before the verdict is read"
            )


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_says_what_its_structural_half_measures(task_id: str) -> None:
    """This ticket decided how a TypeScript structural assertion is written, so
    each task writes down what its own half actually measures — in the comment
    at the head of its `task.yaml`, which is the one place a reader of the task
    set meets it."""
    task = task_by_id(task_id)
    said = (task.directory / "task.yaml").read_text(encoding="utf-8")
    # The comment as prose: the leading `#`s, the emphasis and the wrapping are
    # how a yaml comment is written, and none of them is what is being read.
    heading = " ".join(said.split("id:")[0].replace("#", " ").replace("*", "").split())

    assert "runtime shape" in heading
    for name in structural_test_paths(task) + list(task.behaviour_test_paths):
        assert name in heading, f"{task_id}: nothing in task.yaml says what {name} is"


# --- the refactor acceptance criterion ------------------------------------------


def break_the_court_wording(workdir: Path) -> None:
    """The table built exactly as asked, with one entry's words quietly
    reworded — the verdicts are on a table and the court still says the wrong
    thing."""
    court = workdir / "court.ts"
    source = court.read_text(encoding="utf-8")
    said = "said: `amerced ${bylaw.pence}d`"
    assert said in source
    court.write_text(
        source.replace(said, "said: `amerced ${bylaw.pence} pence`"), encoding="utf-8"
    )


def break_the_shelf_order(workdir: Path) -> None:
    """The press taken out exactly as asked, plus one silent 'tidy-up': the
    shelf gives its days back in the order they were put away rather than
    earliest first."""
    roll_room = workdir / "rollroom.ts"
    source = roll_room.read_text(encoding="utf-8")
    sorted_days = "return [...this.shelf.keys()].sort();"
    assert sorted_days in source
    roll_room.write_text(
        source.replace(sorted_days, "return [...this.shelf.keys()];"), encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("task_id", "mutate"),
    [
        ("courtleet-put-the-verdicts-on-one-table", break_the_court_wording),
        ("gasworks-take-the-press-out-of-the-roll-room", break_the_shelf_order),
    ],
)
def test_a_behaviour_breaking_restructure_is_unresolved(
    task_id: str, mutate: Callable[[Path], None]
) -> None:
    """The refactor acceptance criterion: a diff that restructures exactly as
    asked but bends behaviour must grade 0.0 even though every structural
    assertion passes — the behaviour tests are what catch it."""
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=mutate)
    assert structural_half_passes(task, diff)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0
