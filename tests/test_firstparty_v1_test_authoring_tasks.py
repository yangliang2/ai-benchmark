"""Round 8's `test-authoring` tasks: what one of them is, and that it works.

The action the mutation gate exists for (ADR-0004, design note §67), and the
corpus's registered zero until this round. A task of it ships no held-out
grading tests at all: the deliverable is the suite the agent writes at the
prompt-named test path, and the ground truth is a set of hand-planted
behaviour changes the agent never sees.

Parametrised over every `test-authoring` task in the checked-in corpus rather
than over a list written here, so that the round's later tasks are covered by
being authored and not by somebody remembering to add them. The mechanism
itself — the gate's two questions, the loader's refusals, the lint over a
mutant set — is proved on synthetic tasks in
`tests/test_firstparty_v1_mutation_gate.py` and
`tests/test_firstparty_v1_mutation_lint.py`. What is proved here is the real
thing: that the tasks as authored declare what the action is, tell the agent
everything the suite has to detect and nothing about how it is measured, and
actually discriminate — the author's own suite resolves them and an empty one
does not.

The end-to-end pair is the point of the file. The lint's existence proof runs
the reference suite from `proofs/`, laid beside the repository; a *run* reaches
the verdict through the workdir diff it logged, which is a different path
through the same task. So the reference suite is offered here the way a run
would offer it — a new file under the test path, in a diff built with real git
— and graded by `grade`, the call replay grades a logged run through.
"""

import re
import shutil
from pathlib import Path

import pytest
from firstparty_v1_tasks import TASKS, task_by_id, workdir_diff

from ai_benchmark.firstparty_v1 import (
    Task,
    grade,
    load_task_set,
    mutant_patches,
)

# The words a prompt of this action may not contain. A smoke check and not the
# ruling: what actually keeps the mechanism undisclosed is the author writing a
# prompt that is a behavioural specification and nothing else, and no word list
# can check that. This one catches the obvious slip — a sentence explaining how
# the suite will be measured — and is worth its three lines for that alone.
UNDISCLOSED = ("mutant", "mutation", "kill")

# What §67.7 allows a task to plant: below four the quantifier binds too little
# to be worth authoring, above six hand-planting plus the per-mutant proof buys
# repetition. The lint's own floor is three, deliberately lower — it refuses
# what is unusable, this asserts what round 8 said it would ship.
PLANTED_RANGE = (4, 6)


def authoring_task_ids() -> list[str]:
    """The corpus's `test-authoring` tasks, in a stable order."""
    return sorted(
        task.id for task in load_task_set(TASKS) if task.category == "test-authoring"
    )


TASK_IDS = authoring_task_ids()


def names_as_a_token(prompt: str, path: str) -> bool:
    """Whether the prompt names this path as a whole token rather than as a
    substring of some longer word.

    Written out here rather than borrowed from the lint that reads the same
    question: a pin that calls the implementation it is pinning agrees with it
    by construction.
    """
    token = rf"(?<![A-Za-z0-9_-]){re.escape(path)}(?![A-Za-z0-9_-])"
    return bool(re.search(token, prompt))


def source_files(task: Task) -> list[str]:
    """The starting repository's Python modules, outside the test path."""
    assert task.test_path is not None
    return [
        str(path.relative_to(task.repo_dir))
        for path in sorted(task.repo_dir.rglob("*.py"))
        if not str(path.relative_to(task.repo_dir)).startswith(f"{task.test_path}/")
    ]


def suite_at_the_test_path(task: Task, files: dict[str, str]) -> str:
    """The workdir diff a run that wrote these test files would log."""

    def edit(workdir: Path) -> None:
        assert task.test_path is not None
        for name, source in files.items():
            written = workdir / task.test_path / name
            written.parent.mkdir(parents=True, exist_ok=True)
            written.write_text(source, encoding="utf-8")

    return workdir_diff(task, edit)


def the_reference_suite(task: Task) -> str:
    """The workdir diff a run that wrote the author's own suite would log.

    The suite is copied out of `proofs/`, which holds it at the shape the
    prompt asks for, so what lands in the workdir is what the prompt asked for
    and the diff is a run's diff in every respect but who wrote it.
    """

    def edit(workdir: Path) -> None:
        shutil.copytree(
            task.proofs_dir,
            workdir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    return workdir_diff(task, edit)


# --- the round shipped some ----------------------------------------------------


def test_the_round_checked_in_at_least_one_test_authoring_task() -> None:
    """Everything below is parametrised over the corpus, so an empty corpus
    would pass the whole file by having nothing to run."""
    assert TASK_IDS


# --- what a task of this action declares ---------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_declares_the_action_and_where_the_deliverable_lands(
    task_id: str,
) -> None:
    """The five declarations the gate and the coverage table read.

    `control: true` is not decoration: this action registers no difficulty
    prediction, and a task declaring neither a construction block nor itself a
    control is refused as a control by omission.
    """
    task = task_by_id(task_id)

    assert task.category == "test-authoring"
    assert task.language == "python"
    assert task.surface == "application"
    assert task.control is True
    assert task.construction is None
    assert task.test_path


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_names_the_test_path_and_the_module_under_test(
    task_id: str,
) -> None:
    """An agent cannot write a suite for a module it was not told about, or
    write it where the verdict looks, unless the prompt says both."""
    task = task_by_id(task_id)
    assert task.test_path is not None

    assert names_as_a_token(task.prompt, task.test_path)
    named = [name for name in source_files(task) if names_as_a_token(task.prompt, name)]
    assert named, f"the prompt names none of {source_files(task)}"


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_discloses_nothing_about_the_mechanism(task_id: str) -> None:
    """§67.6: the prompt is a complete behavioural specification and says
    nothing at all about how the suite is measured — the planted set has
    exactly the held-out status grading tests have always had."""
    prompt = task_by_id(task_id).prompt.lower()

    assert [word for word in UNDISCLOSED if word in prompt] == []


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_starting_repository_holds_no_test_where_the_suite_is_to_go(
    task_id: str,
) -> None:
    """A suite already sitting at the test path is a crib: it hands over which
    behaviours are worth asserting, which is what this action measures."""
    task = task_by_id(task_id)
    assert task.test_path is not None

    assert (task.repo_dir / task.test_path).is_dir()
    assert not list((task.repo_dir / task.test_path).rglob("test_*.py"))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_ships_a_planted_set_and_no_second_ground_truth(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    low, high = PLANTED_RANGE

    assert low <= len(mutant_patches(task)) <= high
    assert not task.grading_dir.exists()
    assert task.proofs_dir.is_dir()


# --- the verdict on the real task ----------------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_authors_own_suite_resolves_the_task(task_id: str) -> None:
    """The task is solvable exactly as the prompt words it: the suite the
    prompt asks for, offered as a run's diff, passes on the starting
    repository and catches every planted behaviour change."""
    task = task_by_id(task_id)

    assert grade(task, the_reference_suite(task)) is True


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_a_suite_that_asserts_nothing_does_not_resolve_the_task(
    task_id: str,
) -> None:
    """And the task discriminates rather than merely linting: a green suite is
    not an effective one, which is the whole reason this action needed a
    verdict shape of its own."""
    task = task_by_id(task_id)
    empty = suite_at_the_test_path(
        task, {"test_nothing.py": "def test_nothing():\n    assert True\n"}
    )

    assert grade(task, empty) is False
