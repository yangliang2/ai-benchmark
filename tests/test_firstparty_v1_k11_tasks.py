"""The K11 detection-distance tasks of ticket #31.

The knob is how late a defect makes itself known. Each of these tasks plants
a change whose careless answer is *indistinguishable from a correct one on
the near path* — the run where nothing goes wrong, the input the caller
actually passed, the first few runs of a job that is keeping up — and only
comes apart somewhere else: a later call, a failure that has not happened
yet, an overrun several runs downstream. K8 tried to buy that by withholding
a warning and instead withheld a read set (section 12 of the design note);
K11 buys it by moving the failure, and leaves the read set alone.

What makes this a knob rather than a claim is the property the probes here
assert, which is the one thing every task has to have and nothing else in
the suite could show. For each task the careless edit must survive
*everything the agent can see*:

1. the repository's own tests go on passing;
2. the happy-path exercise a reader runs on their own change — the one in
   `probe.self_check` — prints exactly what the reference solution prints,
   character for character, so no amount of looking at it distinguishes the
   two;
3. and the held-out suite grades it 0.0 anyway.

Point 2 is the load-bearing one, and it is asserted as an equality between
the two trees rather than against a hand-written expectation alone: it says
the check is *blind*, not merely that the careless answer passes it. Round 1
found the models' own self-verification running exactly such a check —
sonnet's `settings-l2` message read "All checks pass", from a repository
suite that never imported the value it had just broken (section 14).

Every task is also probed the other way, with an answer written differently
but correctly that must grade 1.0, so the held-out suites are describing the
contract and not the reference solution's shape.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, doing nothing grades unresolved, scale honest to
the reference diff — plus the pre-registration. Round 1's authors went 0 for
12 on "this knob makes the task harder" bets, so every rung here is
registered at the bottom of the ladder and the difficulty claim is carried
by an effort claim instead; both are pinned below, before any paid run.
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
    BASELINE_TASK_IDS,
    GRADE_TIMEOUT_S,
    EffortClaim,
    Rung,
    Task,
    evaluate,
    lint_task_set,
    load_task_set,
)

# --- the careless answers: right on the near path, wrong further out -----------

SEND_EVERYTHING_THEN_MOVE_IT = '''def flush(outbox, send, size):
    """Send the messages waiting to go out, in batches of at most `size`."""
    waiting = pending(outbox)
    for batch in batches(waiting, size):
        send(batch)
    del outbox["pending"][: len(waiting)]
    outbox["sent"].extend(waiting)
    return len(waiting)
'''

COPY_THE_ROSTER_SHALLOWLY = '''def with_swap(roster, day, leaving, arriving):
    """A new roster with `arriving` standing where `leaving` stood on `day`."""
    swapped = dict(roster)
    shift = swapped[day]
    if leaving not in shift:
        raise ValueError(f"{leaving} is not on the {day} shift")
    if arriving in shift:
        raise ValueError(f"{arriving} is already on the {day} shift")
    shift[shift.index(leaving)] = arriving
    return swapped
'''

DRIVE_THE_STAND_IN_STRAIGHT_LINES = '''def run(stations, work):
    """Bring `stations` up, do `work`, and take the stand back down."""
    for station in stations:
        station.start()
    done = work()
    for station in reversed(stations):
        station.stop()
    return done
'''

COUNT_THE_INTERVAL_FROM_THE_RUN = '''def next_due(schedule, due_at, ran_at):
    """When the job is next due after a run due at `due_at` that finished at
    `ran_at`."""
    if not is_a_slot(schedule, due_at):
        raise ValueError(f"{due_at} is not one of {schedule.name}'s slots")
    if ran_at < due_at:
        raise ValueError(
            f"{schedule.name} cannot have finished at {ran_at}, before it was "
            f"due at {due_at}"
        )
    following = due_at + schedule.every
    if ran_at < following:
        return following
    return ran_at + schedule.every
'''


# --- the honest variants: the same contract, answered another way --------------

REBUILD_THE_QUEUES_A_BATCH_AT_A_TIME = '''def flush(outbox, send, size):
    """Send the messages waiting to go out, in batches of at most `size`."""
    posted = 0
    for batch in batches(pending(outbox), size):
        send(batch)
        posted += len(batch)
        outbox["sent"] = sent(outbox) + batch
        outbox["pending"] = pending(outbox)[len(batch) :]
    return posted
'''

BUILD_THE_ROSTER_OUT_OF_ITS_READERS = '''def with_swap(roster, day, leaving, arriving):
    """A new roster with `arriving` standing where `leaving` stood on `day`."""
    people = who_is_on(roster, day)
    if leaving not in people:
        raise ValueError(f"{leaving} is not on the {day} shift")
    if arriving in people:
        raise ValueError(f"{arriving} is already on the {day} shift")
    people[people.index(leaving)] = arriving
    return {
        name: people if name == day else who_is_on(roster, name)
        for name in days(roster)
    }
'''

STOP_WHAT_CAME_UP_ON_THE_WAY_OUT = '''def run(stations, work):
    """Bring `stations` up, do `work`, and take the stand back down."""
    up = []
    try:
        for station in stations:
            station.start()
            up.insert(0, station)
        done = work()
    except BaseException:
        for station in up:
            station.stop()
        raise
    for station in up:
        station.stop()
    return done
'''

COUNT_THE_SLOTS_THAT_HAVE_GONE_BY = '''def next_due(schedule, due_at, ran_at):
    """When the job is next due after a run due at `due_at` that finished at
    `ran_at`."""
    if not is_a_slot(schedule, due_at):
        raise ValueError(f"{due_at} is not one of {schedule.name}'s slots")
    if ran_at < due_at:
        raise ValueError(
            f"{schedule.name} cannot have finished at {ran_at}, before it was "
            f"due at {due_at}"
        )
    gone_by = (ran_at - schedule.first_due) // schedule.every
    return schedule.first_due + (gone_by + 1) * schedule.every
'''


# --- the check an agent runs on its own change ---------------------------------

# Deliberately the exercise a reader writes to convince themselves the change
# works: the ordinary case, driven through the module's own readers, printed.
# None of them constructs a failure, a second call on a queue that already
# failed, or a run that overruns — which is the whole of what K11 is about.

FLUSHED_AN_OUTBOX = """
from outbox import Message, describe, flush, hold, new_outbox, pending, sent

outbox = new_outbox()
for who in ("ana", "ben", "cal"):
    hold(outbox, Message(who, "hello"))
handed = []
print(flush(outbox, handed.append, 2))
print([[message.recipient for message in batch] for batch in handed])
print([message.recipient for message in sent(outbox)], pending(outbox))
print(describe(outbox))
"""

SWAPPED_A_SHIFT = """
from roster import add_shift, describe, new_roster, who_is_on, with_swap

roster = new_roster(["mon", "tue"])
for name in ("ana", "ben"):
    add_shift(roster, "mon", name)
add_shift(roster, "tue", "cal")
swapped = with_swap(roster, "mon", "ben", "dee")
print(who_is_on(swapped, "mon"))
print(describe(swapped))
"""

RAN_THE_STAND = """
from standrig import describe, run, stand, still_up

log = []
print(run(stand(["power", "pump", "probe"], log), lambda: "12.5 bar"))
print(log)
print(still_up(log), describe(log))
"""

ASKED_WHEN_IT_IS_NEXT_DUE = """
from cadence import make, next_due, slots

backup = make("backup", 1000, 60)
print(slots(backup, 4))
print(next_due(backup, 1000, 1000))
print(next_due(backup, 1060, 1090))
print(next_due(backup, 1120, 1175))
"""


class K11Task(NamedTuple):
    """One K11 task, and everything pinned about it here.

    `module` is the file the reference solution adds to and `definition` is
    where the added function starts, which is what lets a probe swap one
    answer for another. `careless` is the answer that is right on the near
    path, `differently` an answer that is right everywhere, `self_check` the
    exercise a reader runs on their own change and `self_check_shows` what it
    prints — written out here rather than read back from a run, so that a
    check which stopped exercising anything would fail rather than agree with
    itself. `rung` and `at_least_factor` are the pre-registered prediction.
    """

    task_id: str
    module: str
    definition: str
    rung: Rung
    at_least_factor: float
    careless: str
    differently: str
    self_check: str
    self_check_shows: str


K11_TASKS = (
    K11Task(
        task_id="outbox-flush-in-batches",
        module="outbox.py",
        definition="def flush(",
        rung="haiku-solvable",
        at_least_factor=1.2,
        careless=SEND_EVERYTHING_THEN_MOVE_IT,
        differently=REBUILD_THE_QUEUES_A_BATCH_AT_A_TIME,
        self_check=FLUSHED_AN_OUTBOX,
        self_check_shows=(
            "3\n"
            "[['ana', 'ben'], ['cal']]\n"
            "['ana', 'ben', 'cal'] []\n"
            "3 sent, 0 waiting\n"
        ),
    ),
    K11Task(
        task_id="roster-swap-shifts",
        module="roster.py",
        definition="def with_swap(",
        rung="haiku-solvable",
        at_least_factor=1.2,
        careless=COPY_THE_ROSTER_SHALLOWLY,
        differently=BUILD_THE_ROSTER_OUT_OF_ITS_READERS,
        self_check=SWAPPED_A_SHIFT,
        self_check_shows=(
            "['ana', 'dee']\n"
            "['mon: ana, dee', 'tue: cal']\n"
        ),
    ),
    K11Task(
        task_id="standrig-run-stations",
        module="standrig.py",
        definition="def run(",
        rung="haiku-solvable",
        at_least_factor=1.2,
        careless=DRIVE_THE_STAND_IN_STRAIGHT_LINES,
        differently=STOP_WHAT_CAME_UP_ON_THE_WAY_OUT,
        self_check=RAN_THE_STAND,
        self_check_shows=(
            "12.5 bar\n"
            "['start power', 'start pump', 'start probe', "
            "'stop probe', 'stop pump', 'stop power']\n"
            "[] 6 steps, nothing still up\n"
        ),
    ),
    K11Task(
        task_id="cadence-next-due",
        module="cadence.py",
        definition="def next_due(",
        rung="haiku-solvable",
        at_least_factor=1.2,
        careless=COUNT_THE_INTERVAL_FROM_THE_RUN,
        differently=COUNT_THE_SLOTS_THAT_HAVE_GONE_BY,
        self_check=ASKED_WHEN_IT_IS_NEXT_DUE,
        self_check_shows="[1000, 1060, 1120, 1180]\n1060\n1120\n1180\n",
    ),
)

BY_TASK = [pytest.param(entry, id=entry.task_id) for entry in K11_TASKS]


def tasks() -> list[Task]:
    return [task_by_id(entry.task_id) for entry in K11_TASKS]


def answering(entry: K11Task, answer: str) -> Callable[[Path], None]:
    """Replace the reference solution's added function with another answer.

    The added function is the last thing in its module — which is what an
    agent's diff looks like too — so everything from where it starts is the
    part a different answer replaces.
    """

    def edit(workdir: Path) -> None:
        source = workdir / entry.module
        head, marker, _ = source.read_text().partition(entry.definition)
        assert marker, f"{entry.module} has no {entry.definition}"
        source.write_text(head + answer, encoding="utf-8")

    return edit


def what_the_check_shows(task: Task, entry: K11Task, answer: str | None) -> str:
    """What the agent's own happy-path exercise prints, run for real.

    Run in a tree of its own with the module's added function optionally
    swapped for another answer, exactly as a reader would run it: no grading
    isolation, no held-out tests, just the module and a script.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-k11-") as name:
        tree = Path(name)
        copy_solution(task, tree)
        if answer is not None:
            answering(entry, answer)(tree)
        return subprocess.run(
            [sys.executable, "-c", entry.self_check],
            cwd=tree, capture_output=True, text=True, check=True,
            timeout=GRADE_TIMEOUT_S,
        ).stdout


# --- four tasks, each declaring the one knob it sets ---------------------------


def test_every_task_is_a_feature_dev_task_setting_the_distance_knob_alone() -> None:
    """One level across all four, deliberately: K11 has no ladder in the
    design note — the loader records its level as written — and reconciliation
    groups outcomes by level, so four tasks at four free-text levels would be
    four groups of one and no reading at all."""
    for task in tasks():
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"
        assert task.construction is not None
        assert task.construction.levels == {"K11": "far"}
        # Standalone tasks: a K11 family would have to vary its lever inside
        # repo/, which the family lint holds byte-identical across variants,
        # and a pair would need a control these tasks do not have.
        assert task.construction.family is None
        assert task.construction.pair is None


def test_the_tasks_lint_clean() -> None:
    """Linted beside the controls their effort claims name.

    Every other content suite lints its own tasks alone, which these cannot
    be: the baseline comparator rule asks whether the *set* holds a zero-knob
    control of the task's category, so handing the lint these four on their
    own fails them for the absence of tasks they have nothing to do with.
    """
    controls = [
        task
        for task in load_task_set(TASKS)
        if task.id in BASELINE_TASK_IDS and task.category == "feature-dev"
    ]

    assert lint_task_set(tasks() + controls) == []


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    entry: K11Task,
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
def test_the_declared_scale_matches_the_reference_solution(entry: K11Task) -> None:
    task = task_by_id(entry.task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {entry.module}
    assert task.scale == "single-file"


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_repository_starts_out_green(entry: K11Task) -> None:
    """The net the agent inherits passes, and goes on passing once the change
    is made: K11 withholds no warning the repository was giving, it moves the
    failure to where no test of the repository was ever going to look."""
    task = task_by_id(entry.task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


# --- the distance: what the agent can see, and what the verdict reads ----------


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_agents_own_check_cannot_tell_the_careless_answer_apart(
    entry: K11Task,
) -> None:
    """The K11 property, and the probe that decides whether the knob is what
    it says it is.

    Not "the careless answer passes a check" — that would be satisfied by a
    check which exercises nothing. What is asserted is that the *same*
    exercise, run against a correct solution and against the careless one,
    prints the same thing, and that the thing it prints is the answer the
    task actually calls for. The near path is blind by construction.
    """
    task = task_by_id(entry.task_id)

    correct = what_the_check_shows(task, entry, None)
    careless = what_the_check_shows(task, entry, entry.careless)

    assert correct == entry.self_check_shows
    assert careless == entry.self_check_shows


@pytest.mark.parametrize("entry", BY_TASK)
def test_a_careless_answer_passes_the_visible_suite_and_still_grades_unresolved(
    entry: K11Task,
) -> None:
    """The other half of the same claim: nothing the agent can run says the
    change is wrong. The repository's own tests pass — they passed before the
    change and the change did not touch what they cover — and the held-out
    suite, which is the only thing that exercises the far path, grades it
    0.0."""
    task = task_by_id(entry.task_id)
    careless = answering(entry, entry.careless)

    assert visible_tests_pass(task, solved_tree(task, careless))

    [record] = evaluate(
        [task], [run_for(task, solution_diff(task, mutate=careless))], source="run-log"
    )

    assert record.quality_value == 0.0


@pytest.mark.parametrize("entry", BY_TASK)
def test_an_answer_written_differently_but_correctly_still_resolves(
    entry: K11Task,
) -> None:
    """The probe pointing the other way, and what keeps the held-out suites
    from being descriptions of the reference solution: an answer that reaches
    the same contract by another route — rebuilding the queues instead of
    trimming them, unwinding by hand instead of in a `finally`, counting the
    slots that went by instead of walking them — must still grade 1.0."""
    task = task_by_id(entry.task_id)
    diff = solution_diff(task, mutate=answering(entry, entry.differently))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_k11_claim() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    All four sit at the bottom of the ladder, which is the round-1 calibration
    lesson applied rather than an author's confidence: every "this knob makes
    the task harder" bet outside K1 missed, 0 for 12, and the misses were good
    mechanism descriptions attached to bad difficulty estimates. The mechanism
    claim these tasks make is registered on the effort axis below instead.
    """
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {entry.task_id: entry.rung for entry in K11_TASKS}
    assert set(registered.values()) == {"haiku-solvable"}


def test_the_registered_effort_claims_carry_the_difficulty_bet() -> None:
    """What these tasks actually bet, and the half a sweep can take off them.

    Against the zero-knob feature-dev controls rather than a partner, because
    these are standalone tasks; on turns rather than cost, because turns is
    what the runner measures without a price list in it. The factor is a real
    bet and not a formality: round 1's constructed feature-dev cells mostly
    came in *below* the baseline's 9.8 haiku turns, so a task has to cost
    something for this to come out a hit.
    """
    registered = {
        task.id: task.construction.prediction.effort
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {
        entry.task_id: EffortClaim(
            comparator="baseline",
            metric="turns",
            at_least_factor=entry.at_least_factor,
        )
        for entry in K11_TASKS
    }


@pytest.mark.parametrize("entry", BY_TASK)
def test_every_prediction_names_the_distance_it_turns_on(entry: K11Task) -> None:
    """A rationale is what a missed prediction teaches, and for K11 what it
    has to teach is where the failure was expected to surface — a call later,
    a failure that has not happened yet, several runs downstream."""
    task = task_by_id(entry.task_id)

    assert task.construction is not None
    rationale = task.construction.prediction.rationale
    assert len(rationale.split()) >= 15
    assert any(
        word in rationale
        for word in ("distance", "away", "later", "downstream", "drift")
    )
