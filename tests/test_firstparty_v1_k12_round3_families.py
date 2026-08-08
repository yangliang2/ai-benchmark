"""K12's round-3 family, built under the three conditions round 2 lacked (#40).

Round 2 gave K12 two families and eight variants, and the round could not read
them. Both came back at {haiku-solvable} x 4 on both models — every level of
an ordered ladder sitting on the bottom rung — and section 18's verdict is
that the instrument, not the knob, is what failed: "a ladder cannot show an
ordering when every rung is the floor". Two causes were named. The underlying
change was a five-line set intersection, so there was no room below the
ceiling for a conveyance to cost anything; and the withheld rule was written
out in the module's own docstring, because discoverability seemed to require
it, so for any docstring-reading agent `criterion` through `unmentioned` were
one variant differently worded (#32's recorded compression). Section 23.6
turns those into conditions on a second round, and this family is that round:
the change carries a real crux, the crux is nowhere in the module's prose,
and the effort claims run in the ladder's direction. Flat again under these
conditions is a result about K12 rather than about the material.

**Condition one: the floor.** The change is a printed running sheet — group
trips into workings, order each group on two keys, turn two moments per trip
into a clock counted from the start of the block's own date, pad, pluralise
and interleave heading, trip and total lines. Its reference solution adds 32
lines where the album family's adds 5 and the pricelist family's 9, and
`test_the_change_is_not_the_size_of_the_one_round_two_measured` holds the
ratio rather than leaving it as an author's impression. Write volume is not
difficulty and is not claimed to be; what round 2 had was a change with
nothing in it, and this is at least not that. The claim the volume stands in
for is checkable a second way: six of the grading suite's thirteen tests are
its near half, where the day boundary cannot be got wrong and the sheet's
shape is the whole of what is graded, so a solver handed the crux outright
still has most of the suite in front of them.

**Condition two: the crux is out of the prose.** `nightbus.py`'s docstring
says what a trip is; it does not say when a day's working begins, and neither
does the README, and neither does any function docstring — `operating_day`
says "the day's working a moment belongs to", which names the question and
does not answer it. Three tests hold that. The first reads every docstring out
of the module with `ast`, adds the README, and refuses the boundary in any
form a sentence could carry it. The second closes the same leak in the
prompts, where it would do the same damage by a different road: the four
variants share their acceptance block, so a boundary stated there is stated to
all four at once, and the test holds the block silent and exactly one
passage — `criterion`'s — speaking. The third shows that the channel replacing
prose actually carries: rewrite `operating_day` to take the calendar date and
the repository's *own* visible suite goes red, so the boundary is pinned by
tests the agent is invited to run rather than by a sentence it is told.

**Condition three: the claims run along the ladder.** Round 2 registered
K12's effort the other way — on reading burden, peaking at `unmentioned` —
and all eight of its readings missed, prose coming out costlier in six of
them and level in the other two (section 18). So the claim is now held by the
harder member of each pair: `repo-primitive` against `criterion`, and `prose`
against `unmentioned`. The metric is cost, per section 20's quantization
finding, and the factor is the round's standing 1.25x, which is not fitted to
the readings that suggested the direction: round 2's four prose-over-
unmentioned cost multiples were 1.30x, 1.01x, 1.20x and 1.20x, so this claim
registered against round 2's own sweep would have gone 1 of 4.

`test_the_direction_guard_refuses_the_order_round_two_registered` is what
keeps that from being decoration. The guard says a claim may only be held by
the member its pair ranks *higher on the ladder*, and the test proves it bites
by feeding it round 2's own claim assignment — imported from the round-2
suite, not retyped — and watching it fail. A later editor who "fixes" these
claims back into reading-burden order gets a red test rather than a quietly
inverted experiment.

**Why one family and not two.** Round 2 ran two, and the temptation is to
match it. The cell budget says otherwise: #36 expects the whole of round 3 to
buy 34-44 new cells across six authoring lanes at $15-25, and a K12 family is
4 tasks x 2 models = 8 of them. Two families would be over a third of the
round's cells spent on one knob that already stands at silent 1 of 2, ahead of
K10 and K4, which have never been built at all. What round 2 lacked was not sample but a
readable instrument, and the three conditions above are where this round's
effort went instead.

Everything else is the round-2 K12 design, deliberately unchanged so the two
rounds read against each other: four self-contained variants over one
byte-identical repository and grading suite, prompts sharing one acceptance
block verbatim with a single passage varying, two pairs, the careless answers
checked in and graded, and an answer composed from the module's own readers
graded 1.0 to show the withheld decision is recoverable at all. The
vocabulary — `Bend`, `Family`, `LADDER`, `variants`, `taken_apart`,
`answering` — is imported from that suite rather than written again, because
a second definition of a measurement is a second answer free to disagree with
the first.

The pointer this family's `repo-primitive` variant carries is a strong one,
recorded here because #32 asked every family to say so before the sweep reads
it. `operating_day` is the whole of the withheld decision and nothing else,
so a solver who follows the pointer has thereby decided the boundary — album's
asymmetry rather than pricelist's. If this variant misses, the level failed;
there is no weaker reading of the pointer to fall back on.
"""

import ast
import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
)
from test_firstparty_v1_k9_round2_tasks import added_lines, answer_of, authoring_comment
from test_firstparty_v1_k12_families import FAMILIES as ROUND_TWO_FAMILIES
from test_firstparty_v1_k12_families import (
    LADDER,
    RUNGS,
    SHARED_ONLY,
    Bend,
    Family,
    answering,
    declared,
    taken_apart,
    tree,
    variants,
)

from ai_benchmark.firstparty_v1 import (
    EffortClaim,
    EffortMetric,
    evaluate,
    lint_task_set,
)

# What every claim in this round is registered on. Cost rather than turns, for
# section 20's reason: turn counts here are small integers, so a factor is met
# or missed by quantization as much as by the knob.
METRIC: EffortMetric = "cost"

# Unfitted, and the same number round 3's K9 pairs register (#39). Round 2's
# prose-over-unmentioned cost multiples were 1.30x, 1.01x, 1.20x and 1.20x;
# registering any of those would be betting that the sweep which suggested the
# direction reproduces its size too.
FACTOR = 1.25

# How much bigger than round 2's the underlying change has to be. A crude
# proxy for "the criterion variant is not a transcription exercise", and named
# as one: write volume is not difficulty. What it rules out is the shape round
# 2 actually had, a change small enough that every conveyance of it lands on
# the same rung whatever the solver does.
FLOOR_OVER_ROUND_TWO = 3.0


# --- the careless answers: what transcribing the prose arrives at --------------

# The prose variant's passage, spelled out. "Filing each trip under the date it
# sets off on" is `trip.departs.date()`, and this is the reference solution
# with that one substitution and nothing else changed — which is what makes it
# the transcription rather than a strawman. Right for every trip that leaves
# before midnight, wrong for every one that leaves after it.
FILE_UNDER_THE_DEPARTURE_DATE = '''def running_sheet(trips):
    """The depot's running sheet: one block per date, in date order."""

    def clock(moment, day):
        hours = (moment.date() - day).days * 24 + moment.hour
        return f"{hours:02d}:{moment.minute:02d}"

    filed = {}
    for trip in trips:
        filed.setdefault(trip.departs.date(), []).append(trip)

    sheet = []
    for day in sorted(filed):
        running = sorted(filed[day], key=lambda trip: (trip.departs, trip.route))
        sheet.append(day.isoformat())
        for trip in running:
            sheet.append(
                f"  {trip.route}  {clock(trip.departs, day)}"
                f"  {clock(arrives(trip), day)}"
            )
        counted = "1 trip" if len(running) == 1 else f"{len(running)} trips"
        sheet.append(f"  {counted}, {running_time(running)} minutes")
    return sheet
'''

# Farther out, and the answer somebody writes once the boundary has been
# pointed out to them and the clock has not: the trips are filed by the
# module's own reader, and the printed hour is then spelled as a rule about
# hours below four rather than as one about the block the trip is in. Right
# until a trip is still out when the working turns over.
ADD_A_DAY_TO_THE_SMALL_HOURS = '''def running_sheet(trips):
    """The depot's running sheet: one block per day's working, in date order."""

    def clock(moment):
        hours = moment.hour + 24 if moment.hour < 4 else moment.hour
        return f"{hours:02d}:{moment.minute:02d}"

    workings = {}
    for trip in trips:
        workings.setdefault(operating_day(trip.departs), []).append(trip)

    sheet = []
    for day in sorted(workings):
        running = sorted(workings[day], key=lambda trip: (trip.departs, trip.route))
        sheet.append(day.isoformat())
        for trip in running:
            sheet.append(
                f"  {trip.route}  {clock(trip.departs)}  {clock(arrives(trip))}"
            )
        counted = "1 trip" if len(running) == 1 else f"{len(running)} trips"
        sheet.append(f"  {counted}, {running_time(running)} minutes")
    return sheet
'''


# --- the honest variant: the same contract, with the boundary asked for --------

# Takes its day boundary from `runs_on` and `operating_day` and from no prompt
# at all, which is what makes it the discoverability probe: an answer a solver
# who had only the repository would write. Everything else about it — the
# clock, the columns, the total — comes from the acceptance block all four
# variants share, because that half was never withheld from anybody.
ASK_THE_MODULE_WHICH_WORKING_A_TRIP_IS_ON = '''def running_sheet(trips):
    """The depot's running sheet: one block per day's working, in date order."""

    def clock(moment, day):
        minutes = ((moment.date() - day).days * 24 + moment.hour) * 60 + moment.minute
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    sheet = []
    for day in sorted({operating_day(trip.departs) for trip in trips}):
        running = sorted(
            [trip for trip in trips if runs_on(trip, day)],
            key=lambda trip: (trip.departs, trip.route),
        )
        sheet.append(str(day))
        for trip in running:
            sheet.append(
                "  ".join(
                    ["", trip.route, clock(trip.departs, day), clock(arrives(trip), day)]
                )
            )
        counted = "trip" if len(running) == 1 else "trips"
        sheet.append(f"  {len(running)} {counted}, {running_time(running)} minutes")
    return sheet
'''


# --- three runs, and what a careless answer does to each ------------------------

# Printed one run per line so the three can be compared separately. The first
# stays inside a calendar date and every answer here agrees on it; the other
# two cross the boundary in the two ways the two careless answers come apart
# on — a trip departing in the small hours, and a trip still out at 04:00.
THREE_RUNS = '''\
from datetime import datetime

from nightbus import Trip, running_sheet

runs = {
    "inside one date": [
        Trip("N9", datetime(2026, 3, 2, 22, 40), 30),
        Trip("N1", datetime(2026, 3, 2, 21, 5), 42),
    ],
    "away in the small hours": [
        Trip("N1", datetime(2026, 3, 1, 23, 40), 42),
        Trip("N9", datetime(2026, 3, 2, 1, 20), 45),
    ],
    "still out at four": [Trip("N9", datetime(2026, 3, 2, 3, 30), 40)],
}
for name, trips in runs.items():
    print(name, "|", running_sheet(trips))
'''

INSIDE_ONE_DATE = "inside one date"


class Conditions(NamedTuple):
    """The three things round 3 adds to a K12 family, in checkable form.

    `boundary` is the withheld decision as a pattern — every form a sentence
    could state it in — and it is a pattern rather than a list of substrings
    for a reason the shared acceptance block supplies: that block prints
    `24:00`, and a plain search for "4:00" finds the hour inside it and fails
    a passage that says nothing about when a working begins. `guessed` is the
    crux line in `repo/` beside what a solver who never opened it would have
    written instead, which is how the visible suite is shown to pin the
    decision. `runs` prints one run the boundary cannot touch and two it can.
    """

    boundary: re.Pattern[str]
    guessed: tuple[str, str]
    runs: str


CONDITIONS: dict[str, Conditions] = {
    "nightbus-print-the-sheet": Conditions(
        boundary=re.compile(r"\b0?4[:.]00\b|\bfour\b|\b4\s?a\.?m\.?\b", re.IGNORECASE),
        guessed=(
            "return (moment - timedelta(hours=4)).date()",
            "return moment.date()",
        ),
        runs=THREE_RUNS,
    ),
}


def cost_against_the_partner(at_least_factor: float) -> EffortClaim:
    return EffortClaim(
        comparator="pair", metric=METRIC, at_least_factor=at_least_factor
    )


FAMILIES = (
    Family(
        stem="nightbus-print-the-sheet",
        module="nightbus.py",
        definition="def running_sheet(",
        rungs={
            "criterion": "haiku-solvable",
            "repo-primitive": "haiku-solvable",
            "unmentioned": "haiku-solvable",
            "prose": "sonnet-only",
        },
        effort={
            "repo-primitive": cost_against_the_partner(FACTOR),
            "prose": cost_against_the_partner(FACTOR),
        },
        pairs={
            "criterion": "nightbus-print-the-sheet-stated",
            "repo-primitive": "nightbus-print-the-sheet-stated",
            "unmentioned": "nightbus-print-the-sheet-withheld",
            "prose": "nightbus-print-the-sheet-withheld",
        },
        careless=(
            Bend("file-under-the-departure-date", FILE_UNDER_THE_DEPARTURE_DATE),
            Bend("add-a-day-to-the-small-hours", ADD_A_DAY_TO_THE_SMALL_HOURS),
        ),
        differently=ASK_THE_MODULE_WHICH_WORKING_A_TRIP_IS_ON,
    ),
)

BY_FAMILY = [pytest.param(family, id=family.stem) for family in FAMILIES]

BY_VARIANT = [
    pytest.param(family, f"{family.stem}-c{index}", id=f"{family.stem}-c{index}")
    for family in FAMILIES
    for index in (1, 2, 3, 4)
]

BY_BEND = [
    pytest.param(family, f"{family.stem}-c{index}", bend,
                 id=f"{family.stem}-c{index}-{bend.name}")
    for family in FAMILIES
    for index in (1, 2, 3, 4)
    for bend in family.careless
]


def conditions(family: Family) -> Conditions:
    return CONDITIONS[family.stem]


def prose_of(family: Family, repo: Path) -> str:
    """Every word of the starting repository a reader meets as prose.

    The module's own docstring, each function's, and the README — the three
    places round 2's families stated the rule, and the three the sweep showed
    compress the ladder. Deliberately not the code and not the tests: those
    are the channel this round moves discoverability into.
    """
    module = ast.parse((repo / family.module).read_text())
    docstrings = [ast.get_docstring(module) or ""] + [
        ast.get_docstring(node) or ""
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    return "\n".join([*docstrings, (repo / "README.md").read_text()]).casefold()


def guessing_the_boundary(family: Family) -> Callable[[Path], None]:
    """The edit a solver who never opened the module would have made."""
    written, guessed = conditions(family).guessed

    def edit(workdir: Path) -> None:
        source = workdir / family.module
        text = source.read_text()
        assert text.count(written) == 1, f"{family.module} no longer holds {written!r}"
        source.write_text(text.replace(written, guessed), encoding="utf-8")

    return edit


def sheets(printed: str) -> dict[str, str]:
    """The three runs' answers, by the name each was printed under."""
    return dict(
        line.split(" | ", maxsplit=1) for line in printed.splitlines() if line.strip()
    )


# --- each family is one change conveyed four ways -------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_is_four_variants_of_one_conveyance_ladder(
    family: Family,
) -> None:
    """The K12 levels run in ladder order across -c1 to -c4, and K1 is the
    same level in all four: the spec's other decisions are written as
    acceptance criteria everywhere, so the only thing moving is how the crux
    reaches the solver. Round 2's shape exactly, which is the point — the
    three conditions this round adds are conditions on the material, not on
    the design."""
    tasks = variants(family)

    assert len(tasks) == 4
    assert [declared(task)["K12"] for task in tasks] == list(LADDER)
    for task in tasks:
        assert task.construction is not None
        assert task.construction.family == family.stem
        assert set(declared(task)) == {"K1", "K12"}
        assert declared(task)["K1"] == "acceptance"
        assert task.category == "feature-dev"
        assert task.scale == "single-file"
        assert task.language == "python"


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_two_pairs_are_the_two_contrasts_the_claim_is_read_on(
    family: Family,
) -> None:
    """A family is four variants; a pair is two of them read against each
    other, which is what an effort claim can be settled against. The stated
    half is criterion against repo-primitive and the withheld half is
    unmentioned against prose — the contrast the ladder's whole claim is
    about."""
    declared_pairs = {
        declared(task)["K12"]: task.construction.pair
        for task in variants(family)
        if task.construction is not None
    }

    assert declared_pairs == family.pairs
    assert len(set(family.pairs.values())) == 2
    assert family.pairs["unmentioned"] == family.pairs["prose"]
    assert family.pairs["criterion"] == family.pairs["repo-primitive"]


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_variant_ships_the_same_reference_solution(family: Family) -> None:
    """Self-contained copies rather than shared directories, so no run can be
    shaped by another variant — but identical copies, or the family would be
    varying the diff target as well as the conveyance. The repo/ and grading/
    halves are the task-set lint's job (below); the reference solutions sit
    outside the task directories, where the lint cannot see them."""
    [first, *rest] = variants(family)

    for task in rest:
        assert tree(SOLUTIONS / task.id) == tree(SOLUTIONS / first.id)


@pytest.mark.parametrize("family", BY_FAMILY)
def test_only_the_crux_passage_varies_across_the_prompts(family: Family) -> None:
    """The isolation this family rests on, and the reading of K1 that lets it
    declare one level in all four members.

    The four prompts share a block verbatim — the change, its signature, and
    every decision but the crux, written as acceptance criteria — and each
    variant inserts one passage into it at one place. The `unmentioned`
    variant inserts nothing, so the shared block is exactly its whole prompt.
    """
    before, after, passages = taken_apart(family)
    by_level = {declared(task)["K12"]: task.prompt for task in variants(family)}

    for level in LADDER:
        assert by_level[level] == before + passages[level] + after

    assert passages[SHARED_ONLY] == ""
    shared = before + after
    assert shared == by_level[SHARED_ONLY]
    # Read with the line wrapping taken out: which line a criterion breaks on
    # is not what is being asserted about it.
    unwrapped = " ".join(shared.split())
    assert "It must satisfy all of the following:" in unwrapped
    assert "Keep the existing functions and their behaviour unchanged" in unwrapped

    inserted = [passages[level] for level in LADDER if level != SHARED_ONLY]
    assert all(passage.strip() for passage in inserted)
    assert len(set(inserted)) == len(inserted)


# --- every variant is a well-formed, solvable task ------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_family_lints_clean_as_a_whole(family: Family) -> None:
    """Which covers the family invariants — one knob varied, each of its
    levels used once, byte-identical starting repositories and grading suites,
    prompts that actually differ — and the pair invariants too, since both
    pairs are wholly inside the family. Nothing here needs the rest of the
    task set: both effort claims are read against a pair partner, not against
    a category baseline."""
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
    """`single-file` is pinned across the family further up; what is left is
    that the reference solution is in fact one file, and which one."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {family.module}


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_the_repository_starts_out_green(family: Family, task_id: str) -> None:
    """K12 withholds a decision, never a warning: the net the agent inherits
    passes before the change and goes on passing after it."""
    task = task_by_id(task_id)

    assert visible_tests_pass(task)
    assert visible_tests_pass(task, solved_tree(task))


# --- condition one: the family floor --------------------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_change_is_not_the_size_of_the_one_round_two_measured(
    family: Family,
) -> None:
    """Round 2's floor problem, made a number rather than an impression.

    Write volume is not difficulty and nothing here claims it is. What it
    rules out is the specific shape section 18 diagnosed: a change small
    enough that every conveyance of it lands on the bottom rung whatever the
    solver does, so the ladder has nowhere to show an ordering. Round 2's two
    families are read off the task set rather than quoted, so this comparison
    cannot go stale if either of them is ever re-authored.
    """
    round_two = [
        added_lines(task_by_id(f"{other.stem}-c1")) for other in ROUND_TWO_FAMILIES
    ]
    written = added_lines(task_by_id(f"{family.stem}-c1"))

    assert written >= FLOOR_OVER_ROUND_TWO * max(round_two), (
        f"{family.stem} writes {written} lines against round 2's {round_two}"
    )


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_criterion_variant_argues_its_own_floor(family: Family) -> None:
    """The half of the condition no measurement reaches. A reader meeting the
    criterion variant on its own has no way to see that its floor was designed
    rather than inherited, and the line count above cannot tell them what the
    remaining work is. Held to making the argument, as #39 holds a K9 crux to
    arguing against recall — not to the argument coming out any way."""
    comment = authoring_comment(f"{family.stem}-c1")

    assert "transcription" in comment
    assert "floor" in comment
    assert len(comment.split()) >= 80


# --- condition two: the crux is out of the module's prose -----------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_crux_is_nowhere_in_the_repositorys_prose(family: Family) -> None:
    """The channel #32 found and section 23.6 asked round 3 to close.

    Every docstring in the module, plus the README. Round 2's families stated
    the withheld rule in all three, on the reasoning that discoverability
    required it, and the consequence was that a docstring-reading agent met
    `criterion` and `unmentioned` as one variant. Nothing in this repository's
    prose says when a day's working begins, in any of the forms prose could
    say it in.
    """
    boundary = conditions(family).boundary

    for task in variants(family):
        said = boundary.search(prose_of(family, task.repo_dir))

        assert said is None, f"{task.id} states the crux in prose: {said}"


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_crux_is_stated_in_exactly_one_of_the_four_prompts(
    family: Family,
) -> None:
    """The other place a leak would compress the ladder, and the one a reader
    checks last because it looks like the prompts' own business.

    The four variants differ only in the passage the crux travels in, so
    anything the *shared* block says about the boundary is said to all four at
    once — and a shared block that stated it would leave `criterion` adding
    nothing and the whole family measuring one level four times, which is
    round 2's compression arriving through the prompt instead of the docstring.
    So the block must not state it and exactly one passage must: `criterion`'s,
    which is what that level *is*. `repo-primitive` points at the answer
    without giving it and `prose` describes a shape that leads away from it,
    and neither may state the hour.

    The shared block does say the printed clock can run past `24:00`, and that
    is deliberately not a leak: an arrival past midnight happens under the
    calendar-date reading too, so the sentence is equally true whatever the
    solver believes a working to be, and it settles the format question that
    would otherwise be a second withheld decision.
    """
    boundary = conditions(family).boundary
    before, after, passages = taken_apart(family)

    assert boundary.search(before + after) is None
    stated = [level for level in LADDER if boundary.search(passages[level])]

    assert stated == ["criterion"]


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_repositorys_own_tests_would_catch_a_guess_at_the_crux(
    family: Family,
) -> None:
    """The other half of condition two, and the one that matters: taking the
    rule out of the prose is only honest if the channel replacing it carries.

    Rewrite the crux line to what a solver who never opened the module would
    have assumed — the calendar date instead of the day's working — and the
    repository's *own* visible suite goes red. So the boundary is pinned by
    tests the agent is invited to run, not by a sentence it has to be told,
    which is what "discoverability carried by primitives and visible tests"
    has to mean if it is to mean anything.
    """
    for task in variants(family):
        assert visible_tests_pass(task)
        assert not visible_tests_pass(task, guessing_the_boundary(family))


# --- what the conveyance buys, and what it costs --------------------------------


@pytest.mark.parametrize("family, task_id, bend", BY_BEND)
def test_a_careless_answer_passes_the_visible_suite_and_still_grades_unresolved(
    family: Family, task_id: str, bend: Bend
) -> None:
    """The answers transcribing the prose and half-repairing it, graded against
    every variant — the grading suites are byte-identical, so what this shows
    is that no variant's held-out suite lets them through, including the one
    whose prompt described the shape the first came from.

    Nothing the agent can run says either is wrong. The repository's own tests
    pass: they passed before the change and the change did not touch what they
    cover. Only the held-out suite runs a night across the boundary, and it
    grades both 0.0.
    """
    task = task_by_id(task_id)
    careless = answering(family, bend.answer)

    assert visible_tests_pass(task, solved_tree(task, careless))

    [record] = evaluate(
        [task], [run_for(task, solution_diff(task, mutate=careless))], source="run-log"
    )

    assert record.quality_value == 0.0


@pytest.mark.parametrize("family, task_id, bend", BY_BEND)
def test_a_careless_answer_is_right_until_the_run_crosses_the_boundary(
    family: Family, task_id: str, bend: Bend
) -> None:
    """What makes these answers careless rather than broken, and the reason a
    solver has no reason to doubt one.

    A 0.0 says an answer failed the suite; it does not say the answer looked
    wrong. These two agree with the reference sheet line for line on a run
    that stays inside a calendar date — which is the run an author trying
    their own change writes — and part from it only where the night crosses
    over. That is the near half of the grading suite made a direct comparison
    rather than a count of passing tests.
    """
    task = task_by_id(task_id)
    printed = conditions(family).runs

    reference = sheets(answer_of(task, printed, None))
    careless = sheets(answer_of(task, printed, answering(family, bend.answer)))

    assert careless[INSIDE_ONE_DATE] == reference[INSIDE_ONE_DATE]
    assert [run for run in reference if careless[run] != reference[run]], (
        f"{bend.name} agrees with the reference on every run, so it is not the "
        "careless answer it is checked in as"
    )


@pytest.mark.parametrize("family, task_id", BY_VARIANT)
def test_an_answer_written_differently_but_correctly_still_resolves(
    family: Family, task_id: str
) -> None:
    """Two things at once, and the second is the one K12 needs.

    The ordinary one: an answer reaching the same contract by another route —
    filtering the whole run with `runs_on` for each day instead of grouping it
    once, counting the clock in minutes instead of hours — must grade 1.0, or
    the held-out suite is describing the reference solution's shape rather
    than the contract.

    The one this knob rests on: the answer takes its day boundary from the
    module and from no prompt. It is what a solver who had only the repository
    would write, so a variant that says nothing about the crux, and a variant
    that describes it misleadingly, are both solvable from the repository
    alone. A variant whose decision could not be recovered that way would be
    unsolvable by construction rather than hard, and would measure nothing
    about conveyance. The rest of what the answer knows — the columns, the
    clock, the total — comes from the acceptance block all four variants
    share, which was never withheld from anybody.
    """
    task = task_by_id(task_id)
    diff = solution_diff(task, mutate=answering(family, family.differently))

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


# --- pre-registered predictions -------------------------------------------------


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_registered_rungs_are_the_familys_k12_claim(family: Family) -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in.

    The same shape round 2 registered, and registered again on purpose: three
    levels at the bottom, which is round 1's calibration lesson applied, and
    `prose` one rung up because it has the mechanism that lesson makes the
    exception for. Round 2 made this bet twice and missed twice, and section
    18 says why that is not a reason to withdraw it — both misses were read
    under a floor the whole family sat on, and this family does not.
    """
    registered = {
        declared(task)["K12"]: task.construction.prediction.rung
        for task in variants(family)
        if task.construction is not None
    }

    assert registered == family.rungs


@pytest.mark.parametrize("family", BY_FAMILY)
def test_no_family_predicts_that_prose_is_easier_than_saying_nothing(
    family: Family,
) -> None:
    """The ladder-direction guard on the rungs. Pinning each family's rungs
    says what that family claims; this says what no K12 family may claim, so a
    rung mistyped into another variant reads as the contradiction it is rather
    than as the ladder quietly running backwards. It bites hardest at the last
    step: prose sits below unmentioned because prose displaces the module, and
    a family predicting otherwise would be denying the finding it was built
    from."""
    predicted = [RUNGS.index(family.rungs[level]) for level in LADDER]

    assert predicted == sorted(predicted)
    assert RUNGS.index(family.rungs["prose"]) >= RUNGS.index(
        family.rungs["unmentioned"]
    )


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_registered_effort_claims_run_along_the_ladder(family: Family) -> None:
    """What this family bets on price, and the round's third condition.

    Round 2 bet the other direction — effort peaking at `unmentioned`, on
    reading burden — and all eight readings missed, in the ladder's direction
    (section 18). So each pair's claim is held by its harder member, on cost
    rather than turns, at the round's standing 1.25x.

    Two levels register nothing, and it is the two round 2's claims sat on
    minus one: `criterion` has nothing to recover and is the floor both pairs
    are read up from, and `unmentioned` is now the comparator its prose
    partner claims against rather than a claimant itself. Absence claims
    nothing either way.
    """
    registered = {
        declared(task)["K12"]: task.construction.prediction.effort
        for task in variants(family)
        if task.construction is not None
    }

    assert {
        level: claim for level, claim in registered.items() if claim is not None
    } == family.effort
    assert registered["criterion"] is None
    assert registered["unmentioned"] is None
    for claim in family.effort.values():
        assert claim.comparator == "pair"
        assert claim.metric == METRIC
        assert claim.at_least_factor == FACTOR


def holder_outranks_partner(family: Family) -> None:
    """The direction guard itself, lifted out so it can be run on a family it
    is meant to refuse as well as on the one it is meant to accept.

    An effort claim says its own task costs at least a multiple of its
    partner's, so it may only be held by the member of a pair that the ladder
    ranks higher. That is the whole of what "registered in the ladder's
    direction" means, and it is where round 3 and round 2 differ.
    """
    for level in family.effort:
        [partner] = [
            other
            for other, pair in family.pairs.items()
            if pair == family.pairs[level] and other != level
        ]
        assert LADDER.index(level) > LADDER.index(partner), (
            f"{level} claims a multiple of its partner {partner}'s cost while "
            "sitting below it on the ladder"
        )


@pytest.mark.parametrize("family", BY_FAMILY)
def test_no_effort_claim_runs_against_the_ladder(family: Family) -> None:
    """The direction guard, run on this round's families."""
    holder_outranks_partner(family)


@pytest.mark.parametrize("family", ROUND_TWO_FAMILIES, ids=lambda f: f.stem)
def test_the_direction_guard_refuses_the_order_round_two_registered(
    family: Family,
) -> None:
    """The guard proved non-vacuous, against the only arrangement that has
    ever actually been registered instead.

    A guard nobody can fail guards nothing, and this one would pass on any
    family whose claims happened to be written the way its author meant them.
    So it is run here on round 2's own families, imported rather than retyped:
    their claims are held by `repo-primitive` and `unmentioned`, the second of
    which sits *below* its `prose` partner on the ladder, and the guard says
    so. That arrangement was not a mistake — it was the reading-burden order
    section 9 registered and section 18 falsified — which is exactly why it is
    the right thing to test the guard with. An editor who quietly restores it
    gets this test's mirror image in red.
    """
    with pytest.raises(AssertionError, match="sitting below it on the ladder"):
        holder_outranks_partner(family)


@pytest.mark.parametrize("family", BY_FAMILY)
def test_every_prediction_says_why(family: Family) -> None:
    """A rationale is what a missed prediction teaches, and for K12 what it
    has to teach is how the crux reached the solver in that variant — stated,
    pointed at, left in the module, or described."""
    for task in variants(family):
        assert task.construction is not None
        assert len(task.construction.prediction.rationale.split()) >= 15


@pytest.mark.parametrize("family", BY_FAMILY)
def test_the_withheld_variants_record_the_walk_and_the_trap(family: Family) -> None:
    """Where the two conditions no measurement reaches are argued.

    `unmentioned` has to say how a solver gets from the prompt to the boundary
    with nothing pointing at it, because "recoverable from the repository" is
    a claim about a walk somebody has to have taken. `prose` has to say that
    its passage was checked rather than believed — #32's lesson was that a
    prose variant can hand over the crux it was built to withhold, and the
    only defence is the transcription being checked in and graded.
    """
    walk = authoring_comment(f"{family.stem}-c3")
    trap = authoring_comment(f"{family.stem}-c4")

    assert "docstring" in walk
    assert "discoverability" in walk
    assert "glossary" in trap
    assert "0.0" in trap
