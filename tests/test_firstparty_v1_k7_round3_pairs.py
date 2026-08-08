"""K7's round-3 pairs: dense terrain read against calm terrain (#41).

K7 has been the corpus's largest measured effort effect and its least
falsifiable knob at the same time. Round 1 put two tasks on vendored
substrates and measured 3.7x the turns and 5.1x the cost of the frozen
feature-dev baseline on haiku — and recorded, in the same verdict, that the
comparison could not be believed: those two cells are the only ones in the
corpus on a large vendored repository, so the effect conflates invariant
density with plain repository size, and section 12 asked for a size-matched
control. Round 2 gave K7 no tasks at all, which left it at `not assessable`
under the min-n guard, advancing no counter — section 18's ruling was
`stalled`, and the word it used for the position was **unfalsifiable**.

These four tasks are the contrast K7 never had. Each pair is one dense-terrain
task and one calm-terrain control that start from the *same* pgularski/pysm
snapshot, byte for byte, so repository size is matched exactly rather than
approximately and the only thing left between the two members is where in the
library the change lands. Dense is `pysm/pysm.py`'s transition machinery — the
exit walk that pushes two kinds of history and resets each parent, the entry
walk that descends a `.state` the exit walk has just reset, the root-only
`_leaf_state`, the three stacks a machine carries. Calm is `pysm/builder.py`,
a 105-line opt-in helper nothing else imports, whose whole state is one
dictionary and whose every invariant is written in the file being edited.

Write volume is matched within each pair to 10%, the axis #39 added to the
pair design, and `test_each_pair_is_matched_on_how_much_there_is_to_write`
holds them to it: without it "dense terrain costs more" and "the dense task
was bigger" would be the same measurement, which is the confound round 2's K9
result was rejected for.

**The claims are the whole instrument, and that is recorded rather than
discovered.** K7 has no enumerated ladder in `KNOB_LEVELS` and none in the
design note, so under section 9's amended clause 2 neither `dense` nor `calm`
is the harder level and both pairs read *not assessable* on the rung axis.
Every rung here is therefore registered at the floor — which is also where
round 1 actually put both dense K7 tasks after betting them a rung up — and
what the round can win or lose is the two cost claims, read against the pair
partner on `cost` at 1.25x. That factor is not fitted: round 1's K7 multiples
are 3.7x, 5.1x, 2.65x, 4.68x, 2.0x and 2.2x, section 18 names >=1.5x on turns
as the claim that would have gone 4/4 and forbids it, and 1.25x is the house
factor #39 and #40 carry into round 3, fixed before K7 had a pair to be read
against and below every multiple K7 has ever produced. The comparator is the
stronger half of the argument: not one of those multiples measures dense
terrain against calm terrain inside one library, so there is no prior reading
of this quantity at any factor to fit to.

The rest is what every checked-in task has to prove — provenance pinned and
followable, licence travelling with the code, lints clean, reference resolves,
empty diff does not, scale honest to the reference diff, the repository green
before and after — plus, per task, an answer written differently that must
still grade 1.0 and a careless answer that must not.
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
from test_firstparty_v1_k9_round2_tasks import added_lines, authoring_comment

from ai_benchmark.firstparty_v1 import (
    KNOB_LEVELS,
    EffortClaim,
    EffortMetric,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)

# The one substrate this round puts K7 on. Both pairs sit on it rather than
# one on each vendored tree, which buys a contrast replicated twice inside one
# library and gives up the cross-substrate agreement section 10 wants; the
# trade and its reason are recorded in section 23.7.
ORIGIN = "https://github.com/pgularski/pysm"
COMMIT = "0c47a5067974951c75a498ee4ed025cf881f48fd"
LICENCE_HOLDER = "Piotr Gularski"

# What every claim in this round is registered on. Cost, because turn counts
# quantize at these magnitudes (design note section 20).
METRIC: EffortMetric = "cost"

# Unfitted, and the same number #39 and #40 register. See the module docstring
# for the numbers a fitted claim would have used instead.
FACTOR = 1.25

# The widest a pair's two reference solutions may differ in added lines, from
# section 23.3. A bound on the ratio either way round: the confound is a
# difference in how much there was to write, whichever side wrote more.
VOLUME_TOLERANCE = 1.10


def replacing(module: str, before: str, after: str) -> Callable[[Path], None]:
    """Swap one passage of a solved tree for another, insisting it is there."""

    def rewrite(workdir: Path) -> None:
        source = workdir / module
        text = source.read_text()
        assert text.count(before) == 1, before
        source.write_text(text.replace(before, after))

    return rewrite


CORE = "pysm/pysm.py"
BUILDER = "pysm/builder.py"


# --- the same change, answered another way --------------------------------------

RESET_REFERENCE = """\
        root = self.root_machine
        state = root._require_initialized()
        if event is not None:
            event.state_machine = self
        while state.parent is not None:
            exit_event = Event('exit', propagate=False, source_event=event)
            exit_event.state_machine = self
            root._leaf_state = state
            state._on(exit_event)
            parent = state.parent
            parent.state = parent.initial_state
            state = parent
        for state in root._initial_entry_path():
            enter_event = Event('enter', propagate=False, source_event=event)
            enter_event.state_machine = self
            root._leaf_state = state
            state._on(enter_event)
            state.parent.state = state
"""

# The same reset, handed to the walks a dispatch performs its transition with
# rather than walked here — and then made to put back what they recorded,
# because `_exit_states` pushes the leaf it left and every state it climbed
# past. A different place to do the walking, and the same behaviour.
RESET_THROUGH_THE_TRANSITION_WALKS = """\
        root = self.root_machine
        leaf = root._require_initialized()
        if event is not None:
            event.state_machine = self
        if leaf.parent is not None:
            top_state = root._exit_states(event, leaf, root)
            root.leaf_state_stack.pop()
            state = leaf
            while state.parent is not None:
                state.parent.state_stack.pop()
                state = state.parent
            root._enter_states(event, top_state, root)
"""

# And the same answer with the three repairing lines left out: the reset does
# everything the prompt asks except leave the stacks of historical states
# alone, which is the one rule only reading `_exit_states` states.
RESET_AND_KEEP_WHAT_THE_WALK_RECORDED = """\
        root = self.root_machine
        leaf = root._require_initialized()
        if event is not None:
            event.state_machine = self
        if leaf.parent is not None:
            top_state = root._exit_states(event, leaf, root)
            root._enter_states(event, top_state, root)
"""

_POP_HEADING = """\
    def pop_state(self, event=None):
        '''Transition back to the state on top of the machine's
        :attr:`~.StateMachine.stack`, returning it or `None`.

        '''
"""

_POP_BODY = """\
        if event is not None:
            event.state_machine = self
        try:
            to_state = self.stack.pop()
        except IndexError:
            return None
        from_state = self._require_initialized()
        top_state = self._exit_states(event, from_state, to_state)
        self._enter_states(event, top_state, to_state)
        return to_state
"""

PUSHDOWN_REFERENCE = f"""\
        if event is not None:
            event.state_machine = self
        from_state = self._require_initialized()
        self.stack.push(from_state)
        top_state = self._exit_states(event, from_state, to_state)
        self._enter_states(event, top_state, to_state)

{_POP_HEADING}{_POP_BODY}"""

# The two moves spelled as one shared step that reports the state it left, and
# the pop reading the stack with `peek` so nothing is taken off it until the
# move has been made. Same states on the stack, same handlers, same order.
PUSHDOWN_THROUGH_A_SHARED_STEP = f"""\
        self.stack.push(self._move_to_state(to_state, event))

    def _move_to_state(self, to_state, event):
        if event is not None:
            event.state_machine = self
        from_state = self._require_initialized()
        top_state = self._exit_states(event, from_state, to_state)
        self._enter_states(event, top_state, to_state)
        return from_state

{_POP_HEADING}        try:
            to_state = self.stack.peek()
        except IndexError:
            return None
        self._move_to_state(to_state, event)
        self.stack.pop()
        return to_state
"""

# And the slip a stack of one entry never shows: the state being moved *to*
# put on the stack instead of the state being left, so every pop comes back to
# where the machine already is.
PUSH_THE_STATE_BEING_MOVED_TO = f"""\
        if event is not None:
            event.state_machine = self
        from_state = self._require_initialized()
        self.stack.push(to_state)
        top_state = self._exit_states(event, from_state, to_state)
        self._enter_states(event, top_state, to_state)

{_POP_HEADING}{_POP_BODY}"""

CHAIN_REFERENCE = """\
        names = list(names)
        if len(names) < 2:
            raise StateMachineException(
                'A chain needs at least two states: {0}'.format(names))
        if len(set(names)) != len(names):
            raise StateMachineException(
                'A chain cannot repeat a state name: {0}'.format(names))
        parent = self._resolve_machine(parent_path)
        under = self._path_for(parent)
        for name in names:
            self._ensure_new_path(under + (name,))
        for position, name in enumerate(names):
            self.state(name, initial=initial and position == 0,
                       parent_path=under)
        for before, after in zip(names, names[1:]):
            self.transition(under + (before,), under + (after,), events)
        return self
"""

# The same chain, refusing what it refuses off a list of the paths it means to
# take rather than off the builder's own path guard, and laying the
# transitions by index instead of by pairing the run with its own tail.
CHAIN_OFF_THE_PATHS_IT_MEANS_TO_TAKE = """\
        names = tuple(names)
        parent = self._resolve_machine(parent_path)
        under = self._path_for(parent)
        wanted = [under + (name,) for name in names]
        if len(names) < 2 or len(set(names)) != len(names):
            raise StateMachineException(
                'Unsupported chain: {0}'.format(list(names)))
        taken = [path for path in wanted if path in self._states]
        if taken:
            raise StateMachineException(
                'State path already exists: {0}'.format(taken[0]))
        first = True
        for name in names:
            self.state(name, initial=initial and first, parent_path=under)
            first = False
        for index in range(len(names) - 1):
            self.transition(wanted[index], wanted[index + 1], events)
        return self
"""

# And the chain built as it goes, leaving behind whatever it managed to add
# before the name that was already taken stopped it — which is the rule the
# prompt states outright and the reason the reference checks every name first.
CHAIN_ADDING_AS_IT_GOES = """\
        names = list(names)
        if len(names) < 2:
            raise StateMachineException(
                'A chain needs at least two states: {0}'.format(names))
        if len(set(names)) != len(names):
            raise StateMachineException(
                'A chain cannot repeat a state name: {0}'.format(names))
        parent = self._resolve_machine(parent_path)
        under = self._path_for(parent)
        for position, name in enumerate(names):
            self.state(name, initial=initial and position == 0,
                       parent_path=under)
        for before, after in zip(names, names[1:]):
            self.transition(under + (before,), under + (after,), events)
        return self
"""

RENAME_REFERENCE = """\
        if not name or '/' in name:
            raise StateMachineException(
                'Unsupported state name: {0}'.format(name))
        state = self._resolve_state(path)
        old_path = self._path_for(state)
        new_path = old_path[:-1] + (name,)
        if new_path != old_path and new_path in self._states:
            raise StateMachineException(
                'State path already exists: {0}'.format(new_path))
        depth = len(old_path)
        renamed = {}
        for key, item in self._states.items():
            if key[:depth] == old_path:
                renamed[new_path + key[depth:]] = item
            else:
                renamed[key] = item
        self._states = renamed
        state.name = name
        return self
"""

# The same rename, moving the keys that have to move out of the dictionary and
# back into it rather than building a replacement, and telling a collision
# from a rename to the state's own name by what the key holds instead of by
# comparing the paths.
RENAME_BY_MOVING_THE_KEYS = """\
        state = self._resolve_state(path)
        if not name or name.find('/') != -1:
            raise StateMachineException(
                'Unsupported state name: {0}'.format(name))
        old_path = self._path_for(state)
        new_path = old_path[:-1] + (name,)
        if new_path in self._states and self._states[new_path] is not state:
            raise StateMachineException(
                'State path already exists: {0}'.format(new_path))
        depth = len(old_path)
        moving = [key for key in self._states if key[:depth] == old_path]
        for key in moving:
            self._states[new_path + key[depth:]] = self._states.pop(key)
        state.name = name
        return self
"""

# And the rename that moves the state and forgets what was built underneath
# it: every path running *through* the renamed state is a key made of names,
# and the prompt says they move with it.
RENAME_ONLY_THE_STATE_ITSELF = """\
        if not name or '/' in name:
            raise StateMachineException(
                'Unsupported state name: {0}'.format(name))
        state = self._resolve_state(path)
        old_path = self._path_for(state)
        new_path = old_path[:-1] + (name,)
        if new_path != old_path and new_path in self._states:
            raise StateMachineException(
                'State path already exists: {0}'.format(new_path))
        del self._states[old_path]
        self._states[new_path] = state
        state.name = name
        return self
"""


class Probes(NamedTuple):
    """What a task is asked beyond resolving: one more correct answer, and one
    careless one.

    `another_way` has to grade 1.0 — a suite that only accepted the reference
    would be grading whether the agent guessed our diff, which matters most on
    a substrate whose contracts are somebody else's. `careless` has to grade
    0.0, and each one here fails a rule the prompt states outright, so a task
    whose careless answer passed would be a task tolerating more than it said.
    """

    module: str
    reference: str
    another_way: str
    careless: str


class Contrast(NamedTuple):
    """One pair: the task pitched on dense terrain, its calm control, and the
    file each of them edits."""

    pair: str
    dense_id: str
    calm_id: str
    dense: Probes
    calm: Probes


CONTRASTS = (
    Contrast(
        pair="pysm-reset",
        dense_id="pysm-reset-to-initial-states",
        calm_id="pysm-chain-and-outline-states",
        dense=Probes(
            module=CORE,
            reference=RESET_REFERENCE,
            another_way=RESET_THROUGH_THE_TRANSITION_WALKS,
            careless=RESET_AND_KEEP_WHAT_THE_WALK_RECORDED,
        ),
        calm=Probes(
            module=BUILDER,
            reference=CHAIN_REFERENCE,
            another_way=CHAIN_OFF_THE_PATHS_IT_MEANS_TO_TAKE,
            careless=CHAIN_ADDING_AS_IT_GOES,
        ),
    ),
    Contrast(
        pair="pysm-pushdown",
        dense_id="pysm-push-and-pop-states",
        calm_id="pysm-rename-and-list-states",
        dense=Probes(
            module=CORE,
            reference=PUSHDOWN_REFERENCE,
            another_way=PUSHDOWN_THROUGH_A_SHARED_STEP,
            careless=PUSH_THE_STATE_BEING_MOVED_TO,
        ),
        calm=Probes(
            module=BUILDER,
            reference=RENAME_REFERENCE,
            another_way=RENAME_BY_MOVING_THE_KEYS,
            careless=RENAME_ONLY_THE_STATE_ITSELF,
        ),
    ),
)

BY_PAIR = [pytest.param(contrast, id=contrast.pair) for contrast in CONTRASTS]

MEMBERS = tuple(
    (task_id, probes)
    for contrast in CONTRASTS
    for task_id, probes in (
        (contrast.dense_id, contrast.dense),
        (contrast.calm_id, contrast.calm),
    )
)

BY_TASK = [pytest.param(task_id, probes, id=task_id) for task_id, probes in MEMBERS]


def tasks() -> list[Task]:
    return [task_by_id(task_id) for task_id, _ in MEMBERS]


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


# --- what the pair holds constant, and what it varies ---------------------------


def test_the_knob_this_round_asks_has_no_ladder_to_be_asked_on() -> None:
    """Registered here because it decides what the round can say.

    Section 9's amended separation criterion orders a contrast's levels on the
    knob's ladder and reads `not assessable` where there is no ladder to order
    them on. K7 has none, so neither pair can separate upward however its runs
    come out, and the two cost claims are the whole of K7's round-3 evidence.
    Enumerating a K7 ladder is an upstream decision nobody has taken; this
    assertion fails the day somebody takes it, which is the point — the round's
    reading would change and this suite's docstring would be wrong.
    """
    assert KNOB_LEVELS["K7"] == ()


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_pair_varies_the_terrain_and_holds_the_matrix_cell(
    contrast: Contrast,
) -> None:
    dense, calm = task_by_id(contrast.dense_id), task_by_id(contrast.calm_id)

    assert declared(dense) == {"K7": "dense"}
    assert declared(calm) == {"K7": "calm"}
    for task in (dense, calm):
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"
        assert task.construction is not None
        # Not a family: a family varies the prompt over one byte-identical
        # repository, and these two ask for different functions in different
        # modules. What groups them is the pair.
        assert task.construction.family is None
        assert task.construction.pair == contrast.pair


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_pair_starts_from_the_same_repository(contrast: Contrast) -> None:
    """The whole of what makes this the control section 12 asked for. Round
    1's K7 cells were read against hand-authored repositories a fraction of
    the substrate's size, so "dense terrain" and "large repository" were one
    variable; here the two members hold the same bytes and only the site of
    the change moves."""
    dense, calm = task_by_id(contrast.dense_id), task_by_id(contrast.calm_id)

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    assert tree(dense.repo_dir) == tree(calm.repo_dir)


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_two_members_ask_for_different_things(contrast: Contrast) -> None:
    dense, calm = task_by_id(contrast.dense_id), task_by_id(contrast.calm_id)

    assert dense.prompt != calm.prompt


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_each_pair_is_matched_on_how_much_there_is_to_write(
    contrast: Contrast,
) -> None:
    """The confound this round removes, and the reason these tasks exist in
    pairs rather than as two more standalone K7 tasks.

    A dense-terrain task that also happened to be the longer write would
    reproduce round 2's K9 fault exactly: "the crux is harder" and "the crux is
    bigger" not separated by the design. Asserted rather than recorded, because
    the match is a property of two files edited independently and would drift
    the first time either reference solution was rewritten.
    """
    dense = added_lines(task_by_id(contrast.dense_id))
    calm = added_lines(task_by_id(contrast.calm_id))

    assert dense and calm
    assert max(dense, calm) / min(dense, calm) <= VOLUME_TOLERANCE, (
        f"{contrast.dense_id} adds {dense} lines against "
        f"{contrast.calm_id}'s {calm}"
    )


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_dense_member_edits_the_core_and_the_calm_member_the_helper(
    contrast: Contrast,
) -> None:
    """What "dense" and "calm" name here, pinned so the level is not free text
    all the way down. K7's ladder is unenumerated, so nothing in the task model
    can check that two tasks setting `dense` mean the same thing; this suite
    can, for the four it owns."""
    assert contrast.dense.module == CORE
    assert contrast.calm.module == BUILDER
    for task_id, probes in (
        (contrast.dense_id, contrast.dense),
        (contrast.calm_id, contrast.calm),
    ):
        touched = {
            line.split(" b/")[-1]
            for line in solution_diff(task_by_id(task_id)).splitlines()
            if line.startswith("diff --git ")
        }
        assert touched == {probes.module}


def test_every_k7_task_in_the_set_declaring_a_pair_is_probed_here() -> None:
    """A pair added to the task set is a change to a directory rather than to
    any suite, so an unprobed pair would sweep looking exactly like a probed
    one — its dense side never shown to accept a second answer or refuse a
    careless one."""
    declared_pairs = {
        task.construction.pair
        for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.pair is not None
        and "K7" in task.construction.levels
    }

    assert declared_pairs == {contrast.pair for contrast in CONTRASTS}


# --- the substrate: where the starting repositories came from -------------------


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_the_snapshot_records_where_it_came_from_and_what_pins_it(
    task_id: str, probes: Probes
) -> None:
    task = task_by_id(task_id)
    assert task.construction is not None
    substrate = task.construction.substrate

    assert substrate is not None
    assert (substrate.origin, substrate.commit, substrate.license) == (
        ORIGIN, COMMIT, "MIT",
    )
    # No knob-setting edit: the density these tasks are pitched on is the
    # library's own, as round 1's two K7 tasks were. An edit here would also
    # break the pair, which holds repo/ byte-identical across both members.
    assert substrate.modifications == ()


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_the_licence_travels_with_the_vendored_code(
    task_id: str, probes: Probes
) -> None:
    licence = (task_by_id(task_id).repo_dir / "LICENSE").read_text()

    assert "MIT License" in licence
    assert LICENCE_HOLDER in licence


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_the_snapshot_carries_no_version_control_metadata(
    task_id: str, probes: Probes
) -> None:
    task = task_by_id(task_id)

    assert not any(path.name == ".git" for path in task.repo_dir.rglob("*"))
    assert not (task.repo_dir / ".gitignore").exists()


# --- the gates every checked-in task passes -------------------------------------


def test_the_tasks_lint_clean() -> None:
    """Linted on their own, which these can be: every effort claim registered
    here names a pair partner that is in this same set."""
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str, probes: Probes
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_the_repository_starts_out_green_and_stays_green(
    task_id: str, probes: Probes
) -> None:
    """The 138 tests the snapshot ships pass before the change and after it.
    K7 withholds no warning — that is K8's lever — so nothing the agent can
    run is misleading about the work it has done; what the visible suite does
    not do is say anything about the contracts these tasks are graded on."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_an_alternative_correct_answer_still_resolves(
    task_id: str, probes: Probes
) -> None:
    """What keeps the grading suites describing the change asked for rather
    than the reference solution. It matters more on a substrate than on a
    repository we wrote: the contracts graded here are the library's, and a
    suite pinning one spelling of them would be grading whether the agent
    guessed our diff."""
    task = task_by_id(task_id)
    diff = solution_diff(
        task,
        mutate=replacing(probes.module, probes.reference, probes.another_way),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_a_careless_answer_does_not_resolve(task_id: str, probes: Probes) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference. Each careless answer here makes the change asked for and
    breaks one rule the prompt states outright — the dense ones a rule only the
    surrounding code explains, the calm ones a rule the module being edited
    explains — so a control that graded anything would not be a control, and a
    crux that graded anything would not be measuring terrain."""
    task = task_by_id(task_id)
    diff = solution_diff(
        task,
        mutate=replacing(probes.module, probes.reference, probes.careless),
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_all_sit_at_the_floor() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    Not modesty. Both round-1 K7 tasks were registered `sonnet-only` and both
    resolved on haiku, and upward rung bets outside K1 stand at nought for
    fourteen lifetime (section 21). Registering four more of them would be
    spending the round's falsification record on a bet this corpus has never
    won. What the round bets instead is below.
    """
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert set(registered.values()) == {"haiku-solvable"}
    assert len(registered) == 4


def test_the_registered_effort_claims_are_on_cost_at_the_unfitted_factor() -> None:
    """What these pairs actually bet, and the half a sweep can take off them.

    Against the pair partner, because a partner is a within-round contrast
    matched on repository and on write volume where the frozen baseline is
    matched on neither — and, for K7 specifically, because the baseline is the
    comparator whose confound this round exists to remove. On cost rather than
    turns, the round's standing metric. At 1.25x, which is #39's and #40's
    factor rather than anything K7 has measured: registering 1.5x, the number
    section 18 says would have gone 4/4 against the baseline, would be a
    description of round 1 rather than a bet.
    """
    registered = {
        task.id: task.construction.prediction.effort
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        task_id: claim
        for contrast in CONTRASTS
        for task_id, claim in (
            (
                contrast.dense_id,
                EffortClaim(
                    comparator="pair", metric=METRIC, at_least_factor=FACTOR
                ),
            ),
            (contrast.calm_id, None),
        )
    }


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_claim_is_held_by_the_member_on_the_dense_terrain(
    contrast: Contrast,
) -> None:
    """A direction guard. A pair comparator is symmetric — either member could
    name the other — so a claim registered on the calm side would be K7 bet
    upside down, and would read as a theory quietly running the other way
    rather than as the contradiction it is."""
    dense, calm = task_by_id(contrast.dense_id), task_by_id(contrast.calm_id)

    assert dense.construction is not None and calm.construction is not None
    claim = dense.construction.prediction.effort
    assert claim is not None and claim.at_least_factor > 1.0
    assert calm.construction.prediction.effort is None


@pytest.mark.parametrize(("task_id", "probes"), BY_TASK)
def test_every_prediction_names_the_terrain_it_turns_on(
    task_id: str, probes: Probes
) -> None:
    """A rationale is what a missed prediction teaches, and for K7 what it has
    to teach is which reading was expected to cost the money."""
    task = task_by_id(task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale
    assert len(rationale.split()) >= 15
    assert any(word in rationale for word in ("read", "terrain", "module"))


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_each_member_records_that_its_pair_was_matched_on_volume(
    contrast: Contrast,
) -> None:
    """The confound this round removes, argued where the task is read rather
    than only where it is tested: a reader meeting one of these four on its own
    has no way to see that the task beside it was written to the same length on
    purpose. Recorded on both members, because either of them can be the one
    that is read."""
    for task_id in (contrast.dense_id, contrast.calm_id):
        comment = authoring_comment(task_id)

        assert "volume" in comment
        assert "matched" in comment


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_each_dense_member_argues_why_its_terrain_is_the_dense_one(
    contrast: Contrast,
) -> None:
    """K7's level is free text, so "dense" is an authorial claim and nothing in
    the task model can check it. What can be checked is that the claim was
    argued in the place a reader of the task alone would look: the dense
    member's own task.yaml has to name the contracts it is pitched on and say
    that the prompt does not restate them."""
    comment = authoring_comment(contrast.dense_id)

    assert "read set" in comment or "read" in comment
    assert "prompt" in comment
    assert len(comment.split()) >= 120
