"""The vendored-substrate tasks of tickets #22 and #23.

They start from cold OSS repositories — pgularski/pysm, a hierarchical state
machine, and mechatroner/RBQL, an SQL-like query engine over CSV, each
snapshotted at a pinned commit — rather than from repositories we wrote. That
is the whole point of the exercise, so the first thing asserted here is the
provenance: the pin is the full commit id, the origin is followable, the
licence travels with the code in `repo/`, and every surgical edit made to the
snapshot names a knob the task itself activates. An edit answering to no
declared knob is difficulty the task's profile does not account for, and on a
substrate nobody here wrote it is also the edit most easily forgotten.

Two substrates rather than one is what #23 was for, and what it buys is here:
the same gates are asserted over both, per task, so "the vendoring flow is
repeatable" is a property of the checked-in set rather than a claim in a
ticket. Which upstream a task came from is carried in its row, because the pin
and the copyright holder are the two things that must not be shared.

Three of the tasks set K8 to misleading and the lever is the same one #19
used, except that here the tests being taken away are somebody else's: each
starting repository ships the upstream suite minus exactly the tests that
covered the graded contract, and it goes on passing — 136 of them on pysm, 41
on RBQL — while the careless restructuring quietly changes behaviour. Each
careless variant is asserted to keep the repository green *and* to satisfy
every structural assertion before it is asserted to grade 0.0, because a net
that caught the mistake would say nothing about K8, and a slip the prompt
already rules out would say nothing either. A task carries as many of them as
have been found: a slip a review turned up and the grading suite was taught to
catch is registered here afterwards, so the suite goes on being asked the
question that caught it.

The other two set K7 — invariant density — and their snapshots carry no
knob-setting edit, so their modifications lists are empty on purpose: the
density they are pitched on is the library's own. Empty is not the same as
untouched: what was left out of the snapshots for reasons answering to no
knob — down to the two MicroPython-fallback import tests that reach for
`pysm/pysm.py` through the upstream `test/` layout, and RBQL's JS-comparison
test that wrote an artifact into the repository root — is recorded in
`docs/research/substrate-candidate-repos.md`, because `modifications` is not
the place for it.

Every task is also probed with an answer that solves the same prompt
differently and must grade 1.0, so the structural assertions describe the
change asked for rather than the reference solution. The rest is what every
checked-in task has to prove — lints clean, reference resolves, empty diff
does not, scale honest to the reference diff — plus the pre-registered rungs.
"""

import random
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    VISIBLE_SUITE_SEED,
    run_for,
    solution_diff,
    solved_tree,
    structural_half_passes,
    task_by_id,
    visible_tests_pass,
)

from ai_benchmark.firstparty_v1 import (
    Rung,
    Task,
    evaluate,
    lint_task_set,
)


class Upstream(NamedTuple):
    """One vendored repository, and the two things about it that a task's
    provenance block has to get right: what pins the snapshot, and whose
    licence travels with it."""

    origin: str
    commit: str
    licence_holder: str


PYSM = Upstream(
    origin="https://github.com/pgularski/pysm",
    commit="0c47a5067974951c75a498ee4ed025cf881f48fd",
    licence_holder="Piotr Gularski",
)
RBQL = Upstream(
    origin="https://github.com/mechatroner/RBQL",
    commit="4137027611f551591a1775d1d4c8f7fb8d163caa",
    licence_holder="Dmitry Ignatovich",
)


def edit(source_file: Path, replacements: dict[str, str]) -> None:
    """Replace each passage in one file, insisting every one is found."""
    source = source_file.read_text()
    for before, after in replacements.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    source_file.write_text(source)


def rewrite(workdir: Path, replacements: dict[str, str]) -> None:
    """Replace each passage in pysm/pysm.py, insisting every one is found."""
    edit(workdir / "pysm" / "pysm.py", replacements)


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


def hand_the_after_callback_the_transition_target(workdir: Path) -> None:
    """The step extracted exactly as asked, and `after` read off the local the
    line above it already binds. The same state as the machine's leaf whenever
    the transition names a leaf — and one level short of it whenever it names
    a composite state the entry walk goes on descending through."""
    rewrite(workdir, {
        "        transition['after'](self.leaf_state, event)\n":
            "        transition['after'](to_state, event)\n",
    })


def hand_the_action_callback_the_current_leaf_state(workdir: Path) -> None:
    """The mirror of the above on the other side of the exit walk: `action`
    read off the machine rather than off the argument it was handed. The same
    state whenever the walk stayed inside one machine — and the outermost
    state it exited whenever it climbed."""
    rewrite(workdir, {
        "        transition['action'](leaf_state_before, event)\n":
            "        transition['action'](self.leaf_state, event)\n",
    })


def quote_both_output_policies_the_plain_way(workdir: Path) -> None:
    """The choice moved into csv_utils exactly as asked, and then made one
    choice: both quoting policies handed the plain quoter, on the reading that
    two functions differing in one clause were a duplicate. Right for
    `quoted`, and it stops `quoted_rfc` quoting the fields it exists to
    quote — the ones carrying a line break."""
    edit(workdir / "rbql" / "csv_utils.py", {
        "    elif policy == 'quoted_rfc':\n"
        "        return lambda field: rfc_quote_field(field, dlm)\n":
            "    elif policy == 'quoted_rfc':\n"
            "        return lambda field: quote_field(field, dlm)\n",
    })


def hand_each_output_policy_the_other_ones_quoter(workdir: Path) -> None:
    """The mirror of the above, and the slip a table of two entries invites:
    the two policies keep their two quoters and swap them. `quoted_rfc` then
    writes what it always wrote minus the line breaks, so only the *other*
    policy is visibly wrong — and it is wrong by quoting more than it should,
    which reads as harmless."""
    edit(workdir / "rbql" / "csv_utils.py", {
        "    if policy == 'quoted':\n"
        "        return lambda field: quote_field(field, dlm)\n"
        "    elif policy == 'quoted_rfc':\n"
        "        return lambda field: rfc_quote_field(field, dlm)\n":
            "    if policy == 'quoted':\n"
            "        return lambda field: rfc_quote_field(field, dlm)\n"
            "    elif policy == 'quoted_rfc':\n"
            "        return lambda field: quote_field(field, dlm)\n",
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


def choose_the_quoter_from_a_table(workdir: Path) -> None:
    """The same decision, spelled as a lookup rather than a chain, and applied
    to the record by rebinding the list's contents instead of walking it by
    index — same quoter per policy, same text on the stream."""
    edit(workdir / "rbql" / "csv_utils.py", {
        "    if policy == 'quoted':\n"
        "        return lambda field: quote_field(field, dlm)\n"
        "    elif policy == 'quoted_rfc':\n"
        "        return lambda field: rfc_quote_field(field, dlm)\n"
        "    elif policy in ('simple', 'whitespace', 'monocolumn'):\n"
        "        return None\n"
        "    else:\n"
        "        raise ValueError('Unsupported quoting policy: {}'.format(policy))\n":
            "    quoters = {'quoted': quote_field, 'quoted_rfc': rfc_quote_field}\n"
            "    if policy in quoters:\n"
            "        chosen = quoters[policy]\n"
            "        return lambda field: chosen(field, dlm)\n"
            "    if policy in ('simple', 'whitespace', 'monocolumn'):\n"
            "        return None\n"
            "    raise ValueError('Unsupported quoting policy: {}'.format(policy))\n",
    })
    edit(workdir / "rbql" / "rbql_csv.py", {
        "    def quote_fields(self, fields):\n"
        "        for i in range(len(fields)):\n"
        "            fields[i] = self.polymorphic_quote(fields[i])\n":
            "    def quote_fields(self, fields):\n"
            "        fields[:] = [self.polymorphic_quote(f) for f in fields]\n",
    })


def translate_the_like_pattern_in_two_passes(workdir: Path) -> None:
    """Shallow escapes read by collecting the literal run as it goes rather
    than by slicing it out of the pattern afterwards: an escaped character is
    appended to the run being built, so it reaches re.escape with the rest of
    the run instead of on its own. A different place to keep the literal text,
    and the same translation."""
    edit(workdir / "rbql" / "rbql_engine.py", {
        "def like_to_regex(pattern):\n"
        "    p = 0\n"
        "    i = 0\n"
        "    converted = ''\n"
        "    while i < len(pattern):\n"
        "        if pattern[i] == '\\\\' and i + 1 < len(pattern) and "
        "pattern[i + 1] in ['_', '%', '\\\\']:\n"
        "            # The escaped character is matched literally, so it leaves the\n"
        "            # literal run it was in and comes back through re.escape "
        "on its own.\n"
        "            converted += re.escape(pattern[p:i])\n"
        "            converted += re.escape(pattern[i + 1])\n"
        "            i += 2\n"
        "            p = i\n"
        "            continue\n"
        "        if pattern[i] in ['_', '%']:\n"
        "            converted += re.escape(pattern[p:i])\n"
        "            p = i + 1\n"
        "            if pattern[i] == '_':\n"
        "                converted += '.'\n"
        "            else:\n"
        "                converted += '.*'\n"
        "        i += 1\n"
        "    converted += re.escape(pattern[p:i])\n"
        "    return '^' + converted + '$'\n":
            "def like_to_regex(pattern):\n"
            "    pieces = []\n"
            "    literal = ''\n"
            "    i = 0\n"
            "    while i < len(pattern):\n"
            "        char = pattern[i]\n"
            "        if char == '\\\\' and i + 1 < len(pattern) and "
            "pattern[i + 1] in ['_', '%', '\\\\']:\n"
            "            literal += pattern[i + 1]\n"
            "            i += 2\n"
            "            continue\n"
            "        if char in ['_', '%']:\n"
            "            pieces.append(re.escape(literal))\n"
            "            literal = ''\n"
            "            pieces.append('.' if char == '_' else '.*')\n"
            "        else:\n"
            "            literal += char\n"
            "        i += 1\n"
            "    pieces.append(re.escape(literal))\n"
            "    return '^' + ''.join(pieces) + '$'\n",
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

    `upstream` is the repository the snapshot came from, `touched` is the set
    of files the reference solution edits, `knobs` is the activation the task
    declares, `modifications` is how many surgical edits its snapshot carries,
    `bends` are careless answers the repository's own tests do not catch
    (there are none where K8 is not the knob), `differently` is an alternative
    correct answer, and `rung` is the pre-registered prediction.

    `bends` is a tuple because a slip found later is a slip that was always
    possible: once the grading suite has been taught to catch one, it is
    registered here so the suite goes on being asked about it.
    """

    task_id: str
    upstream: Upstream
    touched: frozenset[str]
    knobs: dict[str, str]
    modifications: int
    rung: Rung
    differently: Callable[[Path], None]
    bends: tuple[Callable[[Path], None], ...] = ()


SUBSTRATE_TASKS = (
    SubstrateTask(
        task_id="pysm-extract-transition-step",
        upstream=PYSM,
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K8": "misleading"},
        modifications=2,
        rung="sonnet-only",
        bends=(
            hand_the_after_callback_the_state_it_left,
            hand_the_after_callback_the_transition_target,
            hand_the_action_callback_the_current_leaf_state,
        ),
        differently=perform_the_transition_through_locals,
    ),
    SubstrateTask(
        task_id="pysm-remember-substate-history",
        upstream=PYSM,
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K7": "dense"},
        modifications=0,
        rung="sonnet-only",
        differently=resume_history_on_the_way_in,
    ),
    SubstrateTask(
        task_id="pysm-revert-through-one-step",
        upstream=PYSM,
        touched=frozenset({"pysm/pysm.py"}),
        knobs={"K8": "misleading"},
        modifications=2,
        rung="unsolved",
        bends=(drop_one_history_entry_per_revert,),
        differently=revert_by_dropping_two_in_a_loop,
    ),
    SubstrateTask(
        task_id="rbql-quote-fields-by-policy",
        upstream=RBQL,
        touched=frozenset({"rbql/csv_utils.py", "rbql/rbql_csv.py"}),
        knobs={"K8": "misleading"},
        modifications=3,
        rung="sonnet-only",
        bends=(
            quote_both_output_policies_the_plain_way,
            hand_each_output_policy_the_other_ones_quoter,
        ),
        differently=choose_the_quoter_from_a_table,
    ),
    SubstrateTask(
        task_id="rbql-like-escape-wildcards",
        upstream=RBQL,
        touched=frozenset({"rbql/rbql_engine.py"}),
        knobs={"K7": "dense"},
        modifications=0,
        rung="sonnet-only",
        differently=translate_the_like_pattern_in_two_passes,
    ),
)

BY_TASK = [pytest.param(entry, id=entry.task_id) for entry in SUBSTRATE_TASKS]
CARELESS = [
    pytest.param(entry, bend, id=f"{entry.task_id}-{bend.__name__}")
    for entry in SUBSTRATE_TASKS
    for bend in entry.bends
]


def tasks() -> list[Task]:
    return [task_by_id(entry.task_id) for entry in SUBSTRATE_TASKS]


# --- the substrate: where the starting repositories came from -------------------


def test_the_set_stands_on_more_than_one_upstream_repository() -> None:
    """What #23 was for. Every gate in this module is asserted per task, so
    holding more than one upstream is what turns them from a description of
    one lucky repository into a recipe that ran twice."""
    assert len({entry.upstream for entry in SUBSTRATE_TASKS}) > 1


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_snapshot_records_where_it_came_from_and_what_pins_it(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)
    assert task.construction is not None
    substrate = task.construction.substrate

    assert substrate is not None
    assert substrate.origin == entry.upstream.origin
    assert substrate.commit == entry.upstream.commit
    assert substrate.license == "MIT"


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_licence_travels_with_the_vendored_code(entry: SubstrateTask) -> None:
    """Redistribution is the reason: the snapshot is somebody else's code and
    is copied into every workdir, so its licence has to be in `repo/` and not
    only named in metadata — and it has to be the licence of the repository
    this task actually came from, which is the mistake a second substrate
    makes possible."""
    task = task_by_id(entry.task_id)

    licence = (task.repo_dir / "LICENSE").read_text()

    assert "MIT License" in licence
    assert entry.upstream.licence_holder in licence


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


# --- five standalone tasks, each declaring the knob it sets ---------------------


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
    # of the five carries its own copy of the snapshot and nothing here has
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


def test_the_visible_suite_runs_against_seeded_generators() -> None:
    """What makes every green verdict above an assertion rather than a draw.

    RBQL's own suite builds its tables, delimiters and line separators with
    the unseeded global `random`, which is round 1's leading candidate for the
    ~0.5% failure of `test_the_reference_solution_keeps_the_repository_green`
    on this very task (design note section 15, anomaly 5). The fix is in the
    harness's throwaway copy and nowhere near the checked-in tree, so this
    probe rides into the copy the same way — as an edit — and asks the one
    question that can only be answered yes if the seeding arrived: the first
    draw of a test is the first draw of the seeded stream. Unseeded, the
    probe fails with probability 1.
    """
    task = task_by_id("rbql-like-escape-wildcards")
    first_draw = random.Random(VISIBLE_SUITE_SEED).random()

    def plant_the_probe(workdir: Path) -> None:
        (workdir / "test_seeding_probe.py").write_text(
            "import random\n\n\n"
            "def test_the_stream_starts_where_the_harness_seeded_it():\n"
            f"    assert random.random() == {first_draw!r}\n"
        )

    assert visible_tests_pass(task, plant_the_probe)


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_keeps_the_repository_green(
    entry: SubstrateTask,
) -> None:
    task = task_by_id(entry.task_id)

    assert visible_tests_pass(task, solved_tree(task))


@pytest.mark.parametrize(("entry", "bend"), CARELESS)
def test_a_careless_refactor_stays_green_and_still_grades_unresolved(
    entry: SubstrateTask, bend: Callable[[Path], None]
) -> None:
    """The K8-misleading probe, and the reason all three things are asserted.

    The bent solution restructures exactly as the prompt asks — every
    structural assertion passes — and the repository's own tests go on
    passing, so nothing the agent can see says anything is wrong. Only the
    held-out behaviour tests do, and they are what makes the verdict 0.0.
    """
    task = task_by_id(entry.task_id)
    diff = solution_diff(task, mutate=bend)

    assert visible_tests_pass(task, solved_tree(task, bend))
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
    the thing it is betting on — the visible suite for the three K8 tasks, and
    the contracts around the edit for the two K7 ones."""
    for task in tasks():
        assert task.construction is not None
        rationale = task.construction.prediction.rationale
        assert len(rationale.split()) >= 15
        assert any(
            word in rationale
            for word in ("test", "visible", "suite", "read set", "stack")
        )
