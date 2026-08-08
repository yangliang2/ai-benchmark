"""K10's and K4's round-3 pairs: the scale axis, turned for the first time (#42).

Two knobs have sat in the design note's section 9 since round 1 without ever
being built. K10 is coordination width — N consistent edit sites — and K4 is
the read-set/write-set ratio, the case where there is very little to write and
a great deal to read before you know where to write it. Section 16.2 named K10
a secondary candidate after round 1, section 23.9 recorded both still untouched
after round 2, and the round-3 spec commissioned them together as the intensity
batch. Everything in this suite is therefore a first reading: no prior sweep
has measured either knob at any level, which is what lets the effort factor be
registered at the house 1.25x without any risk of its being fitted.

Each knob gets one pair, and each pair holds its two members on the *same*
pgularski/pysm snapshot byte for byte, the way #41's K7 pairs do, so repository
size and library familiarity are identical rather than similar. Write volume is
matched inside each pair to 10% — 24 against 26 added lines for K10, 17 against
16 for K4 — because without it "the wide one cost more" and "the wide one was
bigger" would be a single measurement, which is the confound round 2's K9
result was rejected for.

**The two pairs are built to hold each other's knob still**, which is the part
worth reading twice, because K10 and K4 are adjacent and a reader is owed the
difference. The K10 pair varies the number of places one stated decision has to
be carried to — 14 hunks in 3 modules against 2 in 2 — while both prompts name
the modules to edit, so neither member has much to find. The K4 pair holds the
site count nearly still — 3 hunks against 2, in one and the same module — while
varying how far the author has to read before those lines can be written: the
wide member's three facts live in three modules it never touches, and the
narrow member's all live in the file being edited. Neither pair is a clean
instrument for the other knob and neither claims to be; what they are is two
contrasts that move different things.

**Fourteen is the reference's count and not the task's floor**, which belongs
in front of a reader of the numbers above. Both `pysm/pysm.py` and
`pysm/aio.py` funnel their entry and exit walks through an `_on`, so a solution
that records there instead of at each walk collects three sites into one in
each of those two modules and comes to **10 hunks** — checked, and it grades
every held-out test. Ten is still inside the band asserted below, so nothing
here is loosened by it; what the collapse shows is that the irreducibility is
*across* modules and not within them. `pysm/queued.py` and `pysm/aio.py` carry
their own copies of machinery `pysm/pysm.py` also has, and no spelling of the
change collects those, which is why the property that survives is the
three-module spread rather than any particular count above ten.

**The claims are the whole instrument, and that is registered rather than
discovered.** Neither K10 nor K4 has an enumerated ladder in `KNOB_LEVELS`, so
under section 9's amended clause 2 neither `wide` nor `narrow` is the harder
level and both pairs read *not assessable* on the rung axis however the runs
come out. Every rung here is registered at the floor — where round 1 actually
put both of its dense K7 cells after betting them a rung up, and where round 2's
sixteen bottom-rung bets went fourteen of sixteen — and what the round can win
or lose is the two cost claims, read against the pair partner on `cost` at
1.25x.

**Prompt length runs the favourable way in both pairs and is registered
anyway.** #39 made the brief's own length something a pair registers rather
than something a reader has to measure, and here the member holding the claim
is the *shorter* of the two in each pair: 324 words against 331 for K10, 299
against 307 for K4. So a cost hit cannot be read off a longer brief, and
neither pair enters the corpus ranking section 23.7 keeps of claims carried
across a wide prompt gap — that ranking is of claims held by the *longer*
member, and these two are held by the shorter one.

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

# The one substrate this round puts these two knobs on, and the same snapshot
# #41's K7 pairs sit on. The choice is argued in the design note's section 23.7
# entry for this ticket: RBQL is the other vendored tree available and its
# visible suite builds its fixtures with the unseeded global `random`
# (section 15.5), which is a poor foundation under a task whose whole evidence
# is a cost reading.
ORIGIN = "https://github.com/pgularski/pysm"
COMMIT = "0c47a5067974951c75a498ee4ed025cf881f48fd"
LICENCE_HOLDER = "Piotr Gularski"

# What every claim in this round is registered on. Cost, because turn counts
# quantize at these magnitudes (design note section 20).
METRIC: EffortMetric = "cost"

# Unfitted, and the same number #39, #40 and #41 register. Neither knob here
# has ever been swept at any level, so there is no measurement of either to fit
# a factor to even if an author wanted to.
FACTOR = 1.25

# The widest a pair's two reference solutions may differ in added lines, from
# section 23.3. A bound on the ratio either way round: the confound is a
# difference in how much there was to write, whichever side wrote more.
VOLUME_TOLERANCE = 1.10

# The band the ticket asks K10's wide member to sit in, counted as hunks of the
# reference diff. A hunk is the mechanical reading of "edit site": git starts a
# new one wherever changed lines are more than six apart, so two edits that
# would be one thought to a reader are one hunk here too.
WIDE_SITES = range(8, 16)

# What a "few-site control" is allowed to be. Not a band with a floor: the
# point of the control is that the work lands in as few places as the same
# change can land in, and two is what a mirroring across the package's two
# queued layers comes to.
FEW_SITES = 3

CORE = "pysm/pysm.py"
QUEUED = "pysm/queued.py"
AIO = "pysm/aio.py"
SERIALIZATION = "pysm/serialization.py"


def rewriting(*swaps: tuple[str, str, str]) -> Callable[[Path], None]:
    """Swap several passages of a solved tree, insisting each one is there.

    #41's `replacing` takes one passage in one module, which is all a
    four-site solution needs. A solution spread over fourteen sites in three
    modules cannot be bent in one place without saying which, so this takes a
    list — and still insists on exactly one match per passage, because a probe
    that silently changed nothing would pass every test for the wrong reason.
    """

    def rewrite(workdir: Path) -> None:
        for module, before, after in swaps:
            source = workdir / module
            text = source.read_text()
            assert text.count(before) == 1, (module, before)
            source.write_text(text.replace(before, after))

    return rewrite


# --- K10: the same recording, spelled through a helper --------------------------

# The reference appends inline at every site. This is the other shape the change
# comes in — one method on StateMachine that every site in `pysm/pysm.py` calls —
# applied to the core's four recording sites and to nothing else, so the solution
# graded here is a genuine mixture of the two spellings rather than a reskin.
_RECORD_METHOD = """\
    def _record(self, kind, name):
        self.root_machine.trace.append((kind, name))

"""

# The two `enter` recordings in `pysm/pysm.py` are the same line, so each is
# quoted with the line beneath it — the initial-path walk builds its event with
# `source_event=None` and the transition walk with the event that caused it —
# and `rewriting` insists on exactly one match for each.
_APPEND_ENTER = "            self.root_machine.trace.append(('enter', state.name))\n"
_RECORD_ENTER = "            self._record('enter', state.name)\n"
_INITIAL_ENTER_EVENT = (
    "            enter_event = Event('enter', propagate=False, source_event=None)"
)
_TRANSITION_ENTER_EVENT = (
    "            enter_event = Event('enter', propagate=False, source_event=event)"
)
_APPEND_EXIT = "            self.root_machine.trace.append(('exit', state.name))\n"
_EXIT_EVENT = (
    "            exit_event = Event('exit', propagate=False, source_event=event)"
)
_ADD_STATE = "    def add_state(self, state, initial=False):"

TRACE_THROUGH_A_HELPER = (
    (CORE, _ADD_STATE, _RECORD_METHOD + _ADD_STATE),
    (
        CORE,
        _APPEND_ENTER + _INITIAL_ENTER_EVENT,
        _RECORD_ENTER + _INITIAL_ENTER_EVENT,
    ),
    (
        CORE,
        "        self.root_machine.trace.append(('event', event.name))",
        "        self._record('event', event.name)",
    ),
    (
        CORE,
        "            self.root_machine.trace.append(('exit', state.name))",
        "            self._record('exit', state.name)",
    ),
    (
        CORE,
        _APPEND_ENTER + _TRANSITION_ENTER_EVENT,
        _RECORD_ENTER + _TRANSITION_ENTER_EVENT,
    ),
)

# And the answer that did the core and the queued layer and stopped: one of the
# fourteen sites left out, the async exit walk. It is the whole point of the
# knob that one omission is a wrong answer, and the prompt says so outright —
# "one graph, initialized and sent the same events, comes out with the same
# trace whichever ran it".
TRACE_MISSING_ONE_ASYNC_SITE = (
    (AIO, _APPEND_EXIT + _EXIT_EVENT, _EXIT_EVENT),
)

# And the slip that used to go unpunished: `self` where the prompt says the
# root machine, in the one walk that can be started anywhere in the graph.
# Every other recording site is reached through a call made on the root, so
# there `self` and `self.root_machine` are the same object and the substitution
# is invisible; `initialize` is the exception, because any machine can be
# initialized. The held-out suite gained a case for it in the fix pass for #42,
# and this asserts the case bites.
_APPEND_ENTER_TO_SELF = "            self.trace.append(('enter', state.name))\n"

TRACE_RECORDED_ON_THE_MACHINE_INITIALIZED = (
    (
        CORE,
        _APPEND_ENTER + _INITIAL_ENTER_EVENT,
        _APPEND_ENTER_TO_SELF + _INITIAL_ENTER_EVENT,
    ),
)


# --- K10 control: the same two methods, built differently -----------------------

_PENDING_REFERENCE = """\
        return list(self._internal_queue) + list(self._external_queue)

    def drop_pending(self):
        '''Discard every waiting event, returning how many were discarded.'''
        dropped = len(self.pending())
        self._clear_queues()
        return dropped
"""

_PENDING_ANOTHER_WAY = """\
        waiting = []
        for queue in (self._internal_queue, self._external_queue):
            waiting.extend(queue)
        return waiting

    def drop_pending(self):
        '''Discard every waiting event, returning how many were discarded.'''
        dropped = len(self._internal_queue) + len(self._external_queue)
        self._clear_queues()
        return dropped
"""

# The order the events were dispatched in rather than the order the machine
# will take them in — the one queue a caller ever sees is the external one, so
# putting it first is the obvious move, and the prompt refuses it in as many
# words.
_PENDING_IN_ARRIVAL_ORDER = """\
        return list(self._external_queue) + list(self._internal_queue)

    def drop_pending(self):
        '''Discard every waiting event, returning how many were discarded.'''
        dropped = len(self.pending())
        self._clear_queues()
        return dropped
"""


def _pending_swaps(replacement: str) -> tuple[tuple[str, str, str], ...]:
    """The same rewrite in both queued layers, which is where both copies live."""
    return tuple(
        (module, _PENDING_REFERENCE, replacement) for module in (QUEUED, AIO)
    )


# --- K4: the same refusal, asked a different way --------------------------------

IN_FLIGHT_REFERENCE = """\
    for machine in _iter_machines(root):
        if getattr(machine, '_is_processing', False):
            raise StateMachineException(
                'Cannot {0} machine {1} while it is handling an event'.format(
                    verb, _state_path(machine)))
"""

# Every state rather than every machine, and the flag read off the instance
# dictionary rather than through getattr. Same graph, same question, same
# answer.
IN_FLIGHT_OVER_EVERY_STATE = """\
    for state in _iter_states(root):
        if state.__dict__.get('_is_processing'):
            raise StateMachineException(
                'Refusing to {0}: {1} is mid-event'.format(
                    verb, _state_path(state)))
"""

# And the answer an author who stopped at pysm/queued.py writes: the class they
# found there, asked by isinstance. AsyncQueuedStateMachine extends
# StateMachine and not QueuedStateMachine, so every async machine walks
# straight through it.
IN_FLIGHT_BY_THE_CLASS_QUEUED_PY_DEFINES = """\
    from .queued import QueuedStateMachine
    for machine in _iter_machines(root):
        if isinstance(machine, QueuedStateMachine) and machine._is_processing:
            raise StateMachineException(
                'Cannot {0} machine {1} while it is handling an event'.format(
                    verb, _state_path(machine)))
"""


# --- K4 control: the same check, walked instead of recursed ---------------------

PLAIN_REFERENCE = """\
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise StateMachineException('Metadata key is not a string')
            _require_plain(item)
    elif isinstance(value, list):
        for item in value:
            _require_plain(item)
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise StateMachineException('Metadata is not plain data')
"""

PLAIN_BY_WORKLIST = """\
    unchecked = [value]
    while unchecked:
        item = unchecked.pop()
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise StateMachineException('Metadata key is not a string')
            unchecked.extend(item.values())
        elif isinstance(item, list):
            unchecked.extend(item)
        elif not isinstance(item, (str, int, float, bool, type(None))):
            raise StateMachineException('Metadata is not plain data')
"""

# The top level and no further, which the prompt refuses in as many words:
# "all the way down ... one thing that is not plain data anywhere inside is
# enough to refuse the whole of it".
PLAIN_ONLY_AT_THE_TOP = """\
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise StateMachineException('Metadata key is not a string')
    elif not isinstance(value, (list, str, int, float, bool, type(None))):
        raise StateMachineException('Metadata is not plain data')
"""


class Probes(NamedTuple):
    """What a task is asked beyond resolving: one more correct answer, and one
    careless one.

    `another_way` has to grade 1.0 — a suite that only accepted the reference
    would be grading whether the agent guessed our diff, which matters most on
    a substrate whose contracts are somebody else's. `careless` has to grade
    0.0, and each one here breaks a rule its prompt states outright, so a task
    whose careless answer passed would be a task tolerating more than it said.
    """

    another_way: tuple[tuple[str, str, str], ...]
    careless: tuple[tuple[str, str, str], ...]


class Contrast(NamedTuple):
    """One pair: the task pitched wide, the narrow control beside it, the knob
    they vary, and the files each of them is expected to touch."""

    knob: str
    pair: str
    wide_id: str
    narrow_id: str
    wide_files: frozenset[str]
    narrow_files: frozenset[str]
    wide: Probes
    narrow: Probes


CONTRASTS = (
    Contrast(
        knob="K10",
        pair="pysm-trace",
        wide_id="pysm-trace-what-the-machine-did",
        narrow_id="pysm-list-the-waiting-events",
        wide_files=frozenset({CORE, QUEUED, AIO}),
        narrow_files=frozenset({QUEUED, AIO}),
        wide=Probes(
            another_way=TRACE_THROUGH_A_HELPER,
            careless=TRACE_MISSING_ONE_ASYNC_SITE,
        ),
        narrow=Probes(
            another_way=_pending_swaps(_PENDING_ANOTHER_WAY),
            careless=_pending_swaps(_PENDING_IN_ARRIVAL_ORDER),
        ),
    ),
    Contrast(
        knob="K4",
        pair="pysm-snapshot",
        wide_id="pysm-refuse-a-snapshot-in-flight",
        narrow_id="pysm-keep-snapshot-metadata-plain",
        wide_files=frozenset({SERIALIZATION}),
        narrow_files=frozenset({SERIALIZATION}),
        wide=Probes(
            another_way=(
                (SERIALIZATION, IN_FLIGHT_REFERENCE, IN_FLIGHT_OVER_EVERY_STATE),
            ),
            careless=(
                (
                    SERIALIZATION,
                    IN_FLIGHT_REFERENCE,
                    IN_FLIGHT_BY_THE_CLASS_QUEUED_PY_DEFINES,
                ),
            ),
        ),
        narrow=Probes(
            another_way=((SERIALIZATION, PLAIN_REFERENCE, PLAIN_BY_WORKLIST),),
            careless=((SERIALIZATION, PLAIN_REFERENCE, PLAIN_ONLY_AT_THE_TOP),),
        ),
    ),
)

BY_PAIR = [pytest.param(contrast, id=contrast.pair) for contrast in CONTRASTS]

MEMBERS = tuple(
    (task_id, probes, files)
    for contrast in CONTRASTS
    for task_id, probes, files in (
        (contrast.wide_id, contrast.wide, contrast.wide_files),
        (contrast.narrow_id, contrast.narrow, contrast.narrow_files),
    )
)

BY_TASK = [
    pytest.param(task_id, probes, files, id=task_id)
    for task_id, probes, files in MEMBERS
]

# What each side's rationale has to point at, and why the two phrases differ. A
# pair is read from either end, so each member has to name the other: the wide
# ones the control they are priced against, the narrow ones the member whose
# price they are the baseline for.
#
# "The wide member" rather than "the crux" on the narrow side. Neither of these
# knobs has an enumerated ladder, and a pair on an unenumerated ladder names no
# crux (CONTEXT.md, on upward separation) — the two levels are `wide` and
# `narrow` and neither is the harder one, so the level is the only vocabulary
# that is true here. #41 reached the same place from the other direction with
# `dense` and `calm`.
POINTS_AT = {"wide": "the control beside it", "narrow": "the wide member beside it"}

BY_SIDE = [
    pytest.param(task_id, POINTS_AT[level], id=task_id)
    for contrast in CONTRASTS
    for task_id, level in (
        (contrast.wide_id, "wide"),
        (contrast.narrow_id, "narrow"),
    )
]


def tasks() -> list[Task]:
    return [task_by_id(task_id) for task_id, _, _ in MEMBERS]


def declared(task: Task) -> dict[str, str]:
    assert task.construction is not None
    return task.construction.levels


def edit_sites(task: Task) -> int:
    """How many places the reference solution changes, as a diff counts them."""
    return sum(
        1 for line in solution_diff(task).splitlines() if line.startswith("@@")
    )


def touched(task: Task) -> frozenset[str]:
    """Which files the reference solution changes."""
    return frozenset(
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    )


def prompt_words(task: Task) -> int:
    return len(task.prompt.split())


def prose(task_id: str) -> str:
    """A task's opening authoring comment, case-folded.

    The phrase checks below ask what a comment says, and a required phrase
    that happened to start a sentence would otherwise have to be written with
    its capital baked into the test — which would make the assertion about
    where the sentence break fell rather than about what was argued.
    """
    return authoring_comment(task_id).lower()


# --- neither knob has a ladder, which decides what the round can say ------------


def test_neither_knob_this_ticket_asks_has_a_ladder_to_be_asked_on() -> None:
    """Registered here because it decides what the round can say.

    Section 9's amended separation criterion orders a contrast's levels on the
    knob's ladder and reads `not assessable` where there is no ladder to order
    them on. Neither of these two has one, so neither pair can separate upward
    however its runs come out, and the two cost claims are the whole of the
    round's K10 and K4 evidence. Enumerating a ladder for either is an upstream
    decision nobody has taken; this assertion fails the day somebody takes one,
    which is the point — the round's reading would change and this suite's
    docstring would be wrong.
    """
    assert KNOB_LEVELS["K10"] == ()
    assert KNOB_LEVELS["K4"] == ()


# --- what each pair holds constant, and what it varies --------------------------


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_pair_varies_its_own_knob_and_holds_the_matrix_cell(
    contrast: Contrast,
) -> None:
    wide, narrow = task_by_id(contrast.wide_id), task_by_id(contrast.narrow_id)

    assert declared(wide) == {contrast.knob: "wide"}
    assert declared(narrow) == {contrast.knob: "narrow"}
    for task in (wide, narrow):
        assert task.category == "feature-dev"
        assert task.language == "python"
        assert task.construction is not None
        # Not a family: a family varies the prompt over one byte-identical
        # repository, and these two ask for different functions. What groups
        # them is the pair.
        assert task.construction.family is None
        assert task.construction.pair == contrast.pair
    assert wide.scale == narrow.scale


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_pair_starts_from_the_same_repository(contrast: Contrast) -> None:
    """What makes each of these a control rather than a second task. The two
    members hold the same bytes, so repository size, library and whatever
    familiarity a model has with pysm are identical and not merely similar;
    only what is asked for moves."""
    wide, narrow = task_by_id(contrast.wide_id), task_by_id(contrast.narrow_id)

    def tree(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }

    assert tree(wide.repo_dir) == tree(narrow.repo_dir)


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_two_members_ask_for_different_things(contrast: Contrast) -> None:
    wide, narrow = task_by_id(contrast.wide_id), task_by_id(contrast.narrow_id)

    assert wide.prompt != narrow.prompt


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_each_pair_is_matched_on_how_much_there_is_to_write(
    contrast: Contrast,
) -> None:
    """The confound this round removes, and the reason these tasks exist in
    pairs rather than as four more standalone tasks.

    A wide task that also happened to be the longer write would reproduce round
    2's K9 fault exactly: "the wide one is harder" and "the wide one is bigger"
    not separated by the design. Asserted rather than recorded, because the
    match is a property of two files edited independently and would drift the
    first time either reference solution was rewritten.
    """
    wide = added_lines(task_by_id(contrast.wide_id))
    narrow = added_lines(task_by_id(contrast.narrow_id))

    assert wide and narrow
    assert max(wide, narrow) / min(wide, narrow) <= VOLUME_TOLERANCE, (
        f"{contrast.wide_id} adds {wide} lines against "
        f"{contrast.narrow_id}'s {narrow}"
    )


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_reference_solution_touches_the_files_the_task_is_pitched_on(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    """Pinned so that "wide" and "narrow" are not free text all the way down.
    Neither knob has an enumerated ladder, so nothing in the task model can
    check that two tasks setting `wide` mean the same thing; this suite can,
    for the four it owns.

    How much this settles differs by knob. For K10 the file set *is* the
    contrast — three modules against two — so this pins the level. For K4 both
    members declare the same single-module frozenset by design, and the check
    is only that neither wandered; what makes that pair's levels mean anything
    is the module facts asserted at
    `test_the_k4_wide_member_reads_three_modules_it_never_writes_to`."""
    assert touched(task_by_id(task_id)) == files


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_declared_scale_matches_the_reference_solution(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    task = task_by_id(task_id)

    assert task.scale == ("single-file" if len(files) == 1 else "cross-file")


def test_every_task_in_the_set_declaring_one_of_these_pairs_is_probed_here() -> None:
    """A pair added to the task set is a change to a directory rather than to
    any suite, so an unprobed pair would sweep looking exactly like a probed
    one — its wide side never shown to accept a second answer or refuse a
    careless one."""
    declared_pairs = {
        task.construction.pair
        for task in load_task_set(TASKS)
        if task.construction is not None
        and task.construction.pair is not None
        and {"K4", "K10"} & set(task.construction.levels)
    }

    assert declared_pairs == {contrast.pair for contrast in CONTRASTS}


# --- K10: the coordination width is real, and counted ---------------------------


def test_the_k10_wide_member_spreads_over_the_band_the_ticket_asks_for() -> None:
    """The knob's whole claim, as a number rather than as a description.

    K10 is "N consistent edit sites", and a task asserting a wide N without
    counting it would be an authorial claim nothing checks — the same gap
    section 23.7 records for K7's free-text `dense`. Hunks are the mechanical
    reading: git opens a new one wherever changed lines are more than six
    apart, so this is a lower bound on what a reader would call separate
    places, never an inflated one.

    What is measured here is the *reference* diff, which is 14. A solver is
    not held to 14, and this assertion should not be read as saying they are:
    routing the entry and exit walks through the `_on` each of the two large
    modules already has collects three sites into one in each of them and
    comes to 10, which grades. So the floor this task actually imposes is
    ten — comfortably inside the band either way, which is why the assertion
    passes on the reference and would pass on the collapse too.
    """
    [k10] = [contrast for contrast in CONTRASTS if contrast.knob == "K10"]
    wide = edit_sites(task_by_id(k10.wide_id))
    narrow = edit_sites(task_by_id(k10.narrow_id))

    assert wide in WIDE_SITES, f"{k10.wide_id} changes {wide} places"
    assert narrow <= FEW_SITES, f"{k10.narrow_id} changes {narrow} places"
    assert wide >= narrow * 4


def test_the_k10_wide_member_spreads_its_sites_over_more_than_one_module() -> None:
    """Across files, as the ticket asks, and this is the part of the width
    that no spelling of the solution can take away.

    Fourteen sites in one file would be a long function to edit rather than a
    decision to carry. *Within* a module the recordings do collect: both
    `pysm/pysm.py` and `pysm/aio.py` route their entry and exit walks through
    an `_on`, and a solution recording there is three sites shorter in each.
    What does not collect is the spread across modules — `pysm/aio.py` carries
    its own copies of the core's walks rather than inheriting them, and
    `pysm/queued.py` its own copy of the draining — so the decision has to be
    written out once per module however tidily each module writes it. That is
    what this asserts, and it is the claim that holds at 10 sites as well as
    at 14."""
    [k10] = [contrast for contrast in CONTRASTS if contrast.knob == "K10"]

    assert len(touched(task_by_id(k10.wide_id))) >= 3


def test_the_k4_pair_does_not_vary_the_coordination_width_as_well() -> None:
    """K10 and K4 are adjacent, and this is what keeps the K4 reading from
    being a second K10 reading: both members write into the same module, at
    within one hunk of each other. What is left between them is the reading."""
    [k4] = [contrast for contrast in CONTRASTS if contrast.knob == "K4"]
    wide = edit_sites(task_by_id(k4.wide_id))
    narrow = edit_sites(task_by_id(k4.narrow_id))

    assert abs(wide - narrow) <= 1
    assert touched(task_by_id(k4.wide_id)) == touched(task_by_id(k4.narrow_id))


# --- K4: the read really does leave the module being written in -----------------


def test_the_k4_wide_member_reads_three_modules_it_never_writes_to() -> None:
    """The documented walk, pinned to the substrate rather than to the prose.

    The wide member's guard turns on one fact, `_is_processing`, and on the
    shape of the classes that carry it. This asserts the three things that
    make the walk unavoidable, each in the module that holds it: the queued
    layer defines the flag; the async layer defines it too and does **not**
    inherit from the queued one, so reading either module alone answers for at
    most half the package; and the core defines it nowhere, so it cannot be
    read off the class the write is about. If any of the three stopped being
    true the walk would be shorter than the task claims, and this fails rather
    than the claim going quietly stale.
    """
    [k4] = [contrast for contrast in CONTRASTS if contrast.knob == "K4"]
    repo = task_by_id(k4.wide_id).repo_dir
    written_in, = touched(task_by_id(k4.wide_id))
    queued = (repo / QUEUED).read_text()
    aio = (repo / AIO).read_text()
    core = (repo / CORE).read_text()

    assert written_in == SERIALIZATION
    assert "_is_processing" in queued
    assert "_is_processing" in aio
    assert "_is_processing" not in core
    assert "class AsyncQueuedStateMachine(StateMachine)" in aio
    assert "class QueuedStateMachine(StateMachine)" in queued
    # And the module the change is written in says none of it: the fact cannot
    # be recovered from the file being edited, which is the whole of `wide`.
    assert "_is_processing" not in (repo / SERIALIZATION).read_text()


def test_the_k4_narrow_member_reads_nothing_outside_the_module_it_writes_in() -> None:
    """The other half of the contrast, and the half that could quietly rot: a
    control whose facts drifted into another module would stop being narrow
    without anything failing. Everything its rule turns on — the promise, the
    function guarded, the exception raised — is in the file being edited."""
    [k4] = [contrast for contrast in CONTRASTS if contrast.knob == "K4"]
    written_in, = touched(task_by_id(k4.narrow_id))
    source = (task_by_id(k4.narrow_id).repo_dir / SERIALIZATION).read_text()

    assert written_in == SERIALIZATION
    assert "plain-data snapshot" in source
    assert "def snapshot(machine, metadata=None):" in source
    assert "raise StateMachineException" in source


# --- the substrate: where the starting repositories came from -------------------


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_snapshot_records_where_it_came_from_and_what_pins_it(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    task = task_by_id(task_id)
    assert task.construction is not None
    substrate = task.construction.substrate

    assert substrate is not None
    assert (substrate.origin, substrate.commit, substrate.license) == (
        ORIGIN, COMMIT, "MIT",
    )
    # No knob-setting edit: the width and the scatter these pairs are pitched
    # on are the library's own, as round 1's and #41's K7 tasks were. An edit
    # here would also break the pair, which holds repo/ byte-identical across
    # both members.
    assert substrate.modifications == ()


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_licence_travels_with_the_vendored_code(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    licence = (task_by_id(task_id).repo_dir / "LICENSE").read_text()

    assert "MIT License" in licence
    assert LICENCE_HOLDER in licence


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_snapshot_carries_no_version_control_metadata(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    task = task_by_id(task_id)

    assert not any(path.name == ".git" for path in task.repo_dir.rglob("*"))
    assert not (task.repo_dir / ".gitignore").exists()


# --- the gates every checked-in task passes -------------------------------------


def test_the_tasks_lint_clean() -> None:
    """Linted on their own, which these can be: every effort claim registered
    here names a pair partner that is in this same set."""
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_the_repository_starts_out_green_and_stays_green(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    """The 138 tests the snapshot ships pass before the change and after it.
    Neither knob here withholds a warning — that is K8's lever — so nothing the
    agent can run is misleading about the work it has done; what the visible
    suite does not do is say anything about the behaviour these tasks are
    graded on, which is why a wide change can be left half-carried and still
    look finished from inside the workdir."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_an_alternative_correct_answer_still_resolves(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    """What keeps the grading suites describing the change asked for rather
    than the reference solution. It matters more on a substrate than on a
    repository we wrote: the contracts graded here are the library's, and a
    suite pinning one spelling of them would be grading whether the agent
    guessed our diff."""
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=rewriting(*probes.another_way))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


@pytest.mark.parametrize(("task_id", "probes", "files"), BY_TASK)
def test_a_careless_answer_does_not_resolve(
    task_id: str, probes: Probes, files: frozenset[str]
) -> None:
    """The other direction, and what keeps the tolerance above from being
    indifference. Each careless answer here makes the change asked for and then
    breaks a rule its own prompt states outright — the two wide ones by failing
    to carry the rule where it had to go, which is the failure each knob is
    named after, and the two narrow ones by getting a local rule wrong, which
    is what keeps a control from being a control only because it was easy."""
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=rewriting(*probes.careless))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_the_k10_wide_member_refuses_a_trace_kept_on_the_wrong_machine() -> None:
    """One probe of its own, for the one rule the held-out suite used to state
    without checking.

    The prompt gives the trace to the root machine — "a nested machine's own
    trace stays empty however often its states are entered and left" — and
    every recording site but one is reached through a call made on the root, so
    writing `self.trace` instead is a distinction without a difference
    everywhere the rest of the suite drives the machine. `initialize` is the
    exception, and until #42's fix pass added a held-out case that initializes
    a nested machine, this answer graded 1.0 with a stated rule broken. This
    asserts it no longer does, which is the only way that gap stays shut.
    """
    [k10] = [contrast for contrast in CONTRASTS if contrast.knob == "K10"]
    task = task_by_id(k10.wide_id)
    diff = solution_diff(
        task, mutate=rewriting(*TRACE_RECORDED_ON_THE_MACHINE_INITIALIZED)
    )

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_all_sit_at_the_floor() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    Not modesty. Both of round 1's dense K7 cells — one of them on this very
    snapshot — were registered `sonnet-only` and both resolved on haiku, and
    upward rung bets outside K1 stand at nought for fourteen lifetime
    (section 21). Registering four more of them would be spending the round's
    falsification record on a bet this corpus has never won. What the round
    bets instead is below.
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
    matched on neither. On cost rather than turns, the round's standing metric.
    At 1.25x, which is the factor #39, #40 and #41 all carry into round 3 —
    and which for these two knobs cannot be fitted to anything even in
    principle, because no sweep has ever measured K10 or K4 at any level.
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
                contrast.wide_id,
                EffortClaim(
                    comparator="pair", metric=METRIC, at_least_factor=FACTOR
                ),
            ),
            (contrast.narrow_id, None),
        )
    }


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_claim_is_held_by_the_member_on_the_wide_side(
    contrast: Contrast,
) -> None:
    """A direction guard. A pair comparator is symmetric — either member could
    name the other — so a claim registered on the narrow side would be the knob
    bet upside down, and would read as a theory quietly running the other way
    rather than as the contradiction it is."""
    wide, narrow = task_by_id(contrast.wide_id), task_by_id(contrast.narrow_id)

    assert wide.construction is not None and narrow.construction is not None
    claim = wide.construction.prediction.effort
    assert claim is not None and claim.at_least_factor > 1.0
    assert narrow.construction.prediction.effort is None


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_the_claim_is_not_carried_across_a_longer_brief(
    contrast: Contrast,
) -> None:
    """The confound #39 made a pair register and #41 measured at its widest.

    A longer prompt is a direct alternative explanation for a cost hit, so what
    matters is not the size of the gap but which member the gap favours. Here
    it favours neither: in both pairs the member holding the claim is the
    shorter of the two, so the gap cuts against the claim rather than for it,
    and neither pair joins the corpus ranking of claims carried across a wide
    gap. Asserted rather than recorded, because a later edit to either prompt
    could turn that around silently.
    """
    wide = prompt_words(task_by_id(contrast.wide_id))
    narrow = prompt_words(task_by_id(contrast.narrow_id))

    assert wide <= narrow, (
        f"{contrast.wide_id} holds the claim and now runs {wide} words "
        f"against {contrast.narrow_id}'s {narrow}"
    )


@pytest.mark.parametrize(("task_id", "points_at"), BY_SIDE)
def test_every_prediction_names_the_mechanism_it_turns_on(
    task_id: str, points_at: str
) -> None:
    """A rationale is what a missed prediction teaches, and for these two knobs
    what it has to teach is which reading was expected to cost the money.

    Phrases rather than words, following the correction #41 made to its own
    version of this test: an any-of-three over short words was met by any one
    of them arriving incidentally, and its loosest disjunct matched inside an
    unrelated word. What every member here has to say is how much there is to
    write and how far the work reaches — the wide members because that is the
    price they bet on, the narrow ones because being small in both is the whole
    of their job.

    Required per side rather than as a disjunction, which is the fault this
    replaces: `A or B` over all four members was satisfied by four rationales
    that all pointed the same way, and a control that never named the member it
    is the baseline for would have passed it. Each side now has to point at the
    other, and only at the other.
    """
    task = task_by_id(task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale.lower()
    assert len(rationale.split()) >= 15
    assert points_at in rationale
    assert "module" in rationale


@pytest.mark.parametrize("contrast", BY_PAIR)
def test_each_member_records_that_its_pair_was_matched_on_volume(
    contrast: Contrast,
) -> None:
    """The confound this round removes, argued where the task is read rather
    than only where it is tested: a reader meeting one of these four on its own
    has no way to see that the task beside it was written to the same length on
    purpose. Recorded on both members, because either can be the one read."""
    for task_id in (contrast.wide_id, contrast.narrow_id):
        comment = prose(task_id)

        assert "volume" in comment
        assert "matched" in comment


def test_the_k10_wide_member_argues_why_its_sites_cannot_be_collected() -> None:
    """A count on its own would not settle it: fourteen sites that a competent
    author could have written as one would be a badly factored reference
    solution rather than a wide task. So the task.yaml has to say, where a
    reader of the task alone would look, why the library forces the repetition,
    and — since three sites per module *can* be collected — how far the
    argument actually reaches.

    Phrases from the argument rather than from the vocabulary. "Edit site",
    which this checked before, is the knob's own definition and arrives in any
    comment that says what K10 is; "counted rather than described" is a claim
    only a comment making the argument would make.
    """
    [k10] = [contrast for contrast in CONTRASTS if contrast.knob == "K10"]
    comment = prose(k10.wide_id)

    assert "counted rather than described" in comment
    assert "copies" in comment
    assert "inheritance cannot collect them" in comment
    # And the limit, so the argument above cannot be read wider than it is. A
    # phrase and not the bare word: "ten" is inside "written", which this
    # comment says a dozen times, and that is the fault #41 corrected.
    assert "ten sites" in comment
    assert len(comment.split()) >= 120


def test_the_k4_wide_member_walks_the_read_its_write_set_depends_on() -> None:
    """The ticket's "documented walk". K4's level is free text, so `wide` is an
    authorial claim and nothing in the task model can check it; what can be
    checked is that the walk was written down in the place a reader of the task
    alone would look, naming each module it passes through.

    And that the two shortcuts round it are written down beside it, which is
    the harder half. The prompt has to say what it says to be an honest brief,
    and what it says supplies two of the walk's three steps outright, leaving
    one identifier to be found; a defensive `getattr` skips the third module
    altogether. Neither shortcut can be closed without making the task
    dishonest, so both are registered — and a comment that made the walk sound
    unavoidable would be the overstatement this asserts against.
    """
    [k4] = [contrast for contrast in CONTRASTS if contrast.knob == "K4"]
    comment = prose(k4.wide_id)

    for module in (QUEUED, AIO, CORE):
        assert module in comment
    assert "read set" in comment
    assert "wide and shallow" in comment
    assert "the prompt supplies" in comment
    assert "getattr" in comment
    assert len(comment.split()) >= 120
