"""The vendored-substrate tasks of ticket #22.

The three of them start from one cold OSS repository — pgularski/pysm, a
hierarchical state machine, snapshotted at a pinned commit — rather than from
a repository we wrote. That is the whole point of the exercise, so the first
thing asserted here is the provenance: the pin is the full commit id, the
origin is followable, the licence travels with the code in `repo/`, and every
surgical edit made to the snapshot names a knob the task itself activates. An
edit answering to no declared knob is difficulty the task's profile does not
account for, and on a substrate nobody here wrote it is also the edit most
easily forgotten.

Two of the tasks set K8 to misleading and the lever is the same one #19 used,
except that here the tests being taken away are somebody else's: each
starting repository ships the upstream suite minus exactly the tests that
covered the graded contract, and it goes on passing — 136 of them — while the
careless restructuring quietly changes behaviour. The careless variant is
asserted to keep the repository green *and* to satisfy every structural
assertion before it is asserted to grade 0.0, because a net that caught the
mistake would say nothing about K8.

The third sets K7 — invariant density — and its snapshot carries no
knob-setting edit, so its modifications list is empty on purpose: the density
it is pitched on is the library's own. Empty is not the same as untouched:
what was left out of all three snapshots for reasons answering to no knob —
down to the two MicroPython-fallback import tests that reach for `pysm/pysm.py`
through the upstream `test/` layout — is recorded in
`docs/research/substrate-candidate-repos.md`, because `modifications` is not
the place for it.

Every task is also probed with an answer that solves the same prompt
differently and must grade 1.0, so the structural assertions describe the
change asked for rather than the reference solution. The rest is what every
checked-in task has to prove — lints clean, reference resolves, empty diff
does not, scale honest to the reference diff — plus the pre-registered rungs.
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    run_for,
    solution_diff,
    solved_tree,
    structural_half_passes,
    task_by_id,
)

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Rung,
    Task,
    evaluate,
    lint_task_set,
)

SUBSTRATE_ORIGIN = "https://github.com/pgularski/pysm"
SUBSTRATE_COMMIT = "0c47a5067974951c75a498ee4ed025cf881f48fd"


def rewrite(workdir: Path, replacements: dict[str, str]) -> None:
    """Replace each passage in pysm/pysm.py, insisting every one is found."""
    core = workdir / "pysm" / "pysm.py"
    source = core.read_text()
    for before, after in replacements.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    core.write_text(source)


# --- the careless refactors: the restructuring done as asked, bent once ---------


def hand_the_after_callback_the_state_it_left(workdir: Path) -> None:
    """The step extracted exactly as asked, and then made uniform: all three
    callbacks handed the leaf state the method was given — which is right for
    before and action, and hands `after` the state the machine has just left
    instead of the one it arrived at."""
    rewrite(workdir, {
        "        transition['after'](self.leaf_state, event)\n":
            "        transition['after'](leaf_state_before, event)\n",
    })


def drop_one_history_entry_per_revert(workdir: Path) -> None:
    """The move made explicit as asked, and the bookkeeping counted per state
    reverted: one pop for the one state gone back to — which leaves behind the
    entry the exit walk pushed on the way there, so every later revert lands a
    step short."""
    rewrite(workdir, {
        "        # Two entries go: the one _exit_states pushed on the way here, and the\n"
        "        # historical entry that was just consumed.\n"
        "        self.leaf_state_stack.pop()\n"
        "        self.leaf_state_stack.pop()\n":
            "        self.leaf_state_stack.pop()\n",
    })


# --- the honest variants: the same change, answered another way ----------------


def perform_the_transition_through_locals(workdir: Path) -> None:
    """The same step, spelled by binding the callbacks to locals first and
    reading the two states straight off the transition — same calls, same
    order, same arguments."""
    rewrite(workdir, {
        "        to_state = transition['to_state']\n"
        "        from_state = transition['from_state']\n"
        "\n"
        "        transition['before'](leaf_state_before, event)\n"
        "        top_state = self._exit_states(event, from_state, to_state)\n"
        "        transition['action'](leaf_state_before, event)\n"
        "        self._enter_states(event, top_state, to_state)\n"
        "        transition['after'](self.leaf_state, event)\n":
            "        before, action, after = (\n"
            "            transition['before'], transition['action'],\n"
            "            transition['after'])\n"
            "\n"
            "        before(leaf_state_before, event)\n"
            "        top_state = self._exit_states(\n"
            "            event, transition['from_state'], transition['to_state'])\n"
            "        action(leaf_state_before, event)\n"
            "        self._enter_states(event, top_state, transition['to_state'])\n"
            "        after(self.leaf_state, event)\n",
    })


def resume_history_on_the_way_in(workdir: Path) -> None:
    """Shallow history remembered rather than left in place: the exit walk
    goes on resetting every machine to its initial state and records the
    substate it left beside it, and the entry walk restores that before it
    works out where the path starts. A different place to keep the memory,
    and the same behaviour."""
    rewrite(workdir, {
        "        self.history = history\n":
            "        self.history = history\n"
            "        self.remembered_state = None\n",
        "            if not parent.history:\n"
        "                parent.state = parent.initial_state\n":
            "            if parent.history:\n"
            "                parent.remembered_state = state\n"
            "            parent.state = parent.initial_state\n",
        "        path = []\n"
        "        state = self._get_leaf_state(to_state)\n":
            "        path = []\n"
            "        self._resume_history(to_state)\n"
            "        state = self._get_leaf_state(to_state)\n",
        "    def set_previous_leaf_state(self, event=None):\n":
            "    def _resume_history(self, state):\n"
            "        while isinstance(state, StateMachine):\n"
            "            remembered = state.remembered_state\n"
            "            if state.history and remembered is not None:\n"
            "                state.state = remembered\n"
            "            state = state.state\n"
            "\n"
            "    def set_previous_leaf_state(self, event=None):\n",
    })


def revert_by_dropping_two_in_a_loop(workdir: Path) -> None:
    """The same two entries removed, counted out in a loop against the result
    of the step rather than by an early return."""
    rewrite(workdir, {
        "        if self._move_to_previous_leaf_state(event) is None:\n"
        "            return\n"
        "        # Two entries go: the one _exit_states pushed on the way here, and the\n"
        "        # historical entry that was just consumed.\n"
        "        self.leaf_state_stack.pop()\n"
        "        self.leaf_state_stack.pop()\n":
            "        if self._move_to_previous_leaf_state(event) is not None:\n"
            "            for _ in range(2):\n"
            "                self.leaf_state_stack.pop()\n",
    })


class SubstrateTask(NamedTuple):
    """One task on the vendored substrate, and what is pinned about it here.

    `touched` is the set of files the reference solution edits, `knobs` is the
    activation the task declares, `modifications` is how many surgical edits
    its snapshot carries, `bend` is a careless answer the repository's own
    tests do not catch (there is none where K8 is not the knob), `differently`
    is an alternative correct answer, and `rung` is the pre-registered
    prediction.
    """

    task_id: str
    touched: frozenset[str]
    knobs: dict[str, str]
    modifications: int
    rung: Rung
    differently: Callable[[Path], None]
    bend: Callable[[Path], None] | None = None


SUBSTRATE_TASKS = (
    SubstrateTask(
        task_id="pysm-extract-transition-step",
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K8": "misleading"},
        modifications=2,
        rung="sonnet-only",
        bend=hand_the_after_callback_the_state_it_left,
        differently=perform_the_transition_through_locals,
    ),
    SubstrateTask(
        task_id="pysm-remember-substate-history",
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K7": "dense"},
        modifications=0,
        rung="sonnet-only",
        differently=resume_history_on_the_way_in,
    ),
    SubstrateTask(
        task_id="pysm-revert-through-one-step",
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K8": "misleading"},
        modifications=2,
        rung="unsolved",
        bend=drop_one_history_entry_per_revert,
        differently=revert_by_dropping_two_in_a_loop,
    ),
)

BY_TASK = [pytest.param(entry, id=entry.task_id) for entry in SUBSTRATE_TASKS]
MISLEADING = [
    pytest.param(entry, id=entry.task_id)
    for entry in SUBSTRATE_TASKS
    if entry.bend is not None
]


def visible_tests_pass(task: Task, edit: Callable[[Path], None] | None = None) -> bool:
    """Whether the repository's own tests — the net the agent sees — pass.

    Run the way an agent would run them: plain pytest in the workdir, with
    none of the isolation grading applies, because the question here is what
    the agent is told rather than what the verdict reads.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-substrate-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        if edit is not None:
            edit(workdir)
        return (
            subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=False,
                timeout=GRADE_TIMEOUT_S,
            ).returncode
            == 0
        )


def tasks() -> list[Task]:
    return [task_by_id(entry.task_id) for entry in SUBSTRATE_TASKS]


# --- the substrate: where the starting repositories came from -------------------


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_snapshot_records_where_it_came_from_and_what_pins_it(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)
    assert task.construction is not None
    substrate = task.construction.substrate

    assert substrate is not None
    assert substrate.origin == SUBSTRATE_ORIGIN
    assert substrate.commit == SUBSTRATE_COMMIT
    assert substrate.license == "MIT"


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_licence_travels_with_the_vendored_code(entry: SubstrateTask) -> None:
    """Redistribution is the reason: the snapshot is somebody else's code and
    is copied into every workdir, so its licence has to be in `repo/` and not
    only named in metadata."""
    task = task_by_id(entry.task_id)

    licence = (task.repo_dir / "LICENSE").read_text()

    assert "MIT License" in licence
    assert "Piotr Gularski" in licence


@pytest.mark.parametrize("entry", BY_TASK)
def test_every_edit_to_the_snapshot_answers_to_a_knob_the_task_sets(
    entry: SubstrateTask,
) -> None:
    """The task model refuses an edit naming a knob the task does not
    activate; what is pinned here is the count, so that an edit made to a
    substrate and left out of the list is a visible difference rather than
    silence."""
    task = task_by_id(entry.task_id)
    assert task.construction is not None and task.construction.substrate is not None
    modifications = task.construction.substrate.modifications

    assert len(modifications) == entry.modifications
    assert all(
        modification.knob in entry.knobs for modification in modifications
    )


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_snapshot_carries_no_version_control_metadata(
    entry: SubstrateTask,
) -> None:
    """A snapshot tree, not a clone: the pin lives in the metadata, and a
    `.git` copied into every workdir would be history the agent can read and
    the runner would have to fight."""
    task = task_by_id(entry.task_id)

    assert not any(path.name == ".git" for path in task.repo_dir.rglob("*"))
    assert not (task.repo_dir / ".gitignore").exists()


# --- three standalone tasks, each declaring the knob it sets --------------------


@pytest.mark.parametrize("entry", BY_TASK)
def test_each_task_declares_its_knob_and_stands_on_its_own(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)
    assert task.construction is not None

    assert task.construction.levels == entry.knobs
    assert task.language == "python"
    # Standalone: no family (a K8 family would have to vary its lever inside
    # repo/, which the family lint holds byte-identical) and no pair, so each
    # of the three carries its own copy of the snapshot and nothing here has
    # to stay byte-identical to anything else.
    assert task.construction.family is None
    assert task.construction.pair is None


def test_the_tasks_lint_clean() -> None:
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_declared_scale_matches_the_reference_solution(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == set(entry.touched)
    assert task.scale == ("single-file" if len(entry.touched) == 1 else "cross-file")


# --- the misleading net ---------------------------------------------------------


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_repository_starts_out_green(entry: SubstrateTask) -> None:
    """Misleading, not broken — and on a vendored substrate this is also what
    says the pruning left a working library behind: the upstream suite still
    passes over the code that was kept."""
    assert visible_tests_pass(task_by_id(entry.task_id))


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_keeps_the_repository_green(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)

    assert visible_tests_pass(task, solved_tree(task))


@pytest.mark.parametrize("entry", MISLEADING)
def test_a_careless_refactor_stays_green_and_still_grades_unresolved(
    entry: SubstrateTask,
) -> None:
    """The K8-misleading probe, and the reason all three things are asserted.

    The bent solution restructures exactly as the prompt asks — every
    structural assertion passes — and the repository's own tests go on
    passing, so nothing the agent can see says anything is wrong. Only the
    held-out behaviour tests do, and they are what makes the verdict 0.0.
    """
    task = task_by_id(entry.task_id)
    assert entry.bend is not None
    diff = solution_diff(task, mutate=entry.bend)

    assert visible_tests_pass(task, solved_tree(task, entry.bend))
    assert structural_half_passes(task, diff)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize("entry", BY_TASK)
def test_an_alternative_correct_answer_still_resolves(entry: SubstrateTask) -> None:
    """What keeps the assertions from describing the reference solution
    rather than the change asked for. It matters more on a substrate than on
    a repository we wrote: the graded contracts here are the library's, and a
    grading suite that pinned one implementation of them would be grading
    whether the agent guessed our diff."""
    task = task_by_id(entry.task_id)
    diff = solution_diff(task, mutate=entry.differently)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_pinned_before_the_sweep() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.
    Nothing here is registered haiku-solvable: a substrate task whose easiest
    rung solves it would say the organic mass changed nothing."""
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {entry.task_id: entry.rung for entry in SUBSTRATE_TASKS}
    assert "haiku-solvable" not in registered.values()


def test_every_prediction_says_which_mechanism_it_is_betting_on() -> None:
    """A rationale is what a missed prediction teaches, so each has to name
    the thing it is betting on — the visible suite for the two K8 tasks, and
    the contracts around the edit for the K7 one."""
    for task in tasks():
        assert task.construction is not None
        rationale = task.construction.prediction.rationale
        assert len(rationale.split()) >= 15
        assert any(
            word in rationale
            for word in ("test", "visible", "suite", "read set", "stack")
        )
