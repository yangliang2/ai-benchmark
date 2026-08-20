"""Round 7's three TypeScript `feature-dev` tasks (ticket #108): three fresh
hand-authored repositories, each with a capability that is not there yet, and
each graded by `node --test` through the same execution-verified pipeline a
real run goes through.

Parametrised over the three the way the Python `feature-dev` suite is
(`tests/test_firstparty_v1_feature_dev_tasks.py`): each lints clean, each
reference solution grades resolved and the empty diff unresolved, each declared
`scale` is honest against its solution's diff, and each visible suite passes on
the pristine repository — which is what makes the README's `node --test` a net
the agent actually inherits rather than a claim.

One of the three is a command-line tool over the filesystem, which is a
scenario the Python corpus does not have and part of what round 7 is buying.
Every path its held-out tests touch is under a directory those tests make and
remove themselves, so grading writes nowhere but its throwaway workdir and two
tests never collide over one path — asserted here, over the checked-in bytes,
because it is a rule about how the tests are written that no run can catch.
"""

import re

import pytest
from firstparty_v1_tasks import (
    run_for,
    solution_diff,
    task_by_id,
    visible_tests_pass,
)

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    _run_grading,
    evaluate,
    lint_task_set,
)
from ai_benchmark.language_runners import TYPESCRIPT

# Task id -> the scale its reference solution honestly has.
TS_FEATURE_DEV_TASKS: dict[str, str] = {
    "parishchest-seal-the-register-against-a-later-hand": "single-file",
    "seedbank-book-out-what-the-store-hands-over": "cross-file",
    "weighbridge-put-the-second-weighing-on-the-tape": "cross-file",
}

TASK_IDS = sorted(TS_FEATURE_DEV_TASKS)

# The one whose held-out tests touch the filesystem at all.
ON_THE_FILESYSTEM = "seedbank-book-out-what-the-store-hands-over"

# What a held-out test is allowed to name a path with: a directory it made
# itself. Anything else is a path some other run of some other task could be
# standing on at the same moment.
_MAKES_ITS_OWN = "mkdtempSync("

# ...and what it must do with it afterwards, in a `finally` so that a failing
# assertion still leaves the machine as it found it.
_TAKES_IT_AWAY = "rmSync("


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_task_is_declared_as_designed(task_id: str) -> None:
    """The declaration the round is defined by: a zero-knob TypeScript control
    with no construction block, whose scale is checked against its solution's
    diff below."""
    task = task_by_id(task_id)

    assert task.category == "feature-dev"
    assert task.language == "typescript"
    assert task.runner is TYPESCRIPT
    assert task.surface == "application"
    assert task.control is True
    assert task.construction is None
    assert task.scale == TS_FEATURE_DEV_TASKS[task_id]


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_task_lints_clean(task_id: str) -> None:
    assert lint_task_set([task_by_id(task_id)]) == []


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str,
) -> None:
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
def test_the_visible_suite_passes_on_the_pristine_repository(task_id: str) -> None:
    """The net the agent inherits is green before it starts: the repository's
    own `*.test.ts` files, run the way its README says to run them."""
    assert visible_tests_pass(task_by_id(task_id))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_repository_ships_a_visible_suite_and_a_readme_naming_node_test(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    visible = sorted(task.repo_dir.glob(TYPESCRIPT.grading_test_glob))

    assert visible, f"{task_id} ships no visible tests for the agent to inherit"
    readme = (task.repo_dir / "README.md").read_text(encoding="utf-8")
    assert "node --test" in readme


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_held_out_tests_fail_on_the_pristine_repository(task_id: str) -> None:
    """The feature is not there yet — which for these three is the held-out
    file failing to import or link at all, since the module and the methods it
    names do not exist. Asserted separately from the lint that also checks it,
    because it is the whole of what makes these `feature-dev` rather than
    `test-authoring`."""
    task = task_by_id(task_id)

    assert task.language_test_paths
    assert not _run_grading(
        task, "", list(task.language_test_paths), timeout_s=GRADE_TIMEOUT_S
    )


def test_every_held_out_test_that_writes_makes_and_removes_its_own_directory() -> None:
    """This ticket's own rule for the filesystem task, and the reason it is a
    rule: two tasks graded at once, or one graded twice, must not be standing
    on one path. A held-out test may only name a path under a directory it made
    itself with `mkdtempSync`, and must take that directory away again.
    """
    for task_id in TASK_IDS:
        task = task_by_id(task_id)
        for name in task.language_test_paths:
            source = (task.grading_dir / name).read_text(encoding="utf-8")
            writes = re.search(r"\b(mkdirSync|writeFileSync|appendFileSync)\b", source)
            names_a_path = "node:fs" in source
            if not (writes or names_a_path):
                continue
            assert _MAKES_ITS_OWN in source, (
                f"{task_id}: the held-out test {name} reaches the filesystem "
                "without making a directory of its own to reach it in"
            )
            assert _TAKES_IT_AWAY in source, (
                f"{task_id}: the held-out test {name} makes a directory and "
                "never takes it away"
            )
            assert "finally" in source, (
                f"{task_id}: the held-out test {name} takes its directory away "
                "outside a `finally`, so a failing assertion leaves it behind"
            )


def test_the_filesystem_task_is_the_one_that_reaches_the_filesystem() -> None:
    """The scenario claim, held to the bytes: exactly one of the three is a
    command-line tool over the filesystem, and the other two touch no disk at
    all — so the rule above is not quietly protecting nothing."""
    reaching = {
        task_id
        for task_id in TASK_IDS
        for name in task_by_id(task_id).language_test_paths
        if "node:fs" in (task_by_id(task_id).grading_dir / name).read_text("utf-8")
    }

    assert reaching == {ON_THE_FILESYSTEM}
