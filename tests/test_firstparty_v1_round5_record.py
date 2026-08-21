"""Round 5's record, pinned: what sections 47-51 of the design note publish.

The round swept twelve tasks — eight `code-review` and four locate-style
`codebase-comprehension`, every one a declared control — over the two-model
ladder, and its one instrument is the set-shaped **findings key**: a verdict
that asks whether one set covers another rather than whether one answer is in
a set. So the round's readings are about a mechanism's first paid outing
rather than about a contrast between two actions, and section 49 records why
the locate-against-fix comparison round 4 could draw is not drawable here.

Every figure is pinned rather than derived, which is the point: a derived
expectation follows the corpus wherever it goes, and these numbers are quoted
in the design note and read by whoever is deciding what a round cost. The pins
come in two halves. The first is arithmetic over the four checked-in run logs
and the verdicts re-grading their diffs produces. The second reads the design
note itself — its quoted calibration rows against what `calibrate-v1` actually
prints, its resolution table against what the logs actually say — because a
record whose numbers drift from the artifacts that earned them is the defect
this file exists to catch, and the record is prose that nothing else checks.

The round's runs are selected by their **sweep id** and never by log filename:
the sweep protocol bans selecting run logs by name, having watched the first
pass of the round-1 analysis silently drop two paid cells that way. The four
filenames appear here only where a command has to be given a log to replay,
which is section 51's verification.
"""

import ast
import hashlib
import json
import re
import statistics
from pathlib import Path

import pytest

from ai_benchmark import firstparty, firstparty_v1, reconcile_v1
from ai_benchmark.cli import main

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_SWEEP = "round-5"
_AGENT_VERSION = "2.1.234 (Claude Code)"
_AS_OF = "2026-08-18"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"

# The four logs the sweep's four invocations wrote: the dry cell, haiku's other
# eleven, sonnet's twelve, and the rider — which timed out and wrote no row, so
# its log is empty and its cell is not one of the round's twenty-four. Named
# only so that section 51's replay can be given one log at a time; nothing here
# selects runs by them.
_LOG_NAMES = (
    "2026-08-18-r5-a.jsonl",
    "2026-08-18-r5-b.jsonl",
    "2026-08-18-r5-c.jsonl",
    "2026-08-18-r5-d.jsonl",
)

# The rider: one cell, its own invocation, and no row anywhere in the corpus.
# It is `feature-dev`, which no ticket registers, so it ran at the flat default
# rather than under a registered limit — the distinction section 47 draws and
# the reason the cell is recorded apart from round 3's readings instead of
# repairing them.
_RIDER = ("pysm-work-out-a-way-there", _SONNET)
_RIDER_LOG = "2026-08-18-r5-d.jsonl"

# The round's twelve tasks, by category. Every one is a declared control, and
# the eight and the four are the populations the two new calibration rows in
# section 48 are taken over.
_REVIEW: tuple[str, ...] = (
    "apiary-review-the-book-and-the-crop",
    "belfry-review-the-peals-and-the-board",
    "commonland-review-the-beasts-and-the-dues",
    "launderette-review-the-rate-and-the-card",
    "parishhall-review-the-hire-and-the-diary",
    "produceshow-review-the-points-and-the-sheet",
    "toolshed-review-the-lending-book",
    "watermill-review-the-grist-and-the-toll",
)
_COMPREHENSION: tuple[str, ...] = (
    "bandstand-where-the-poster-is-worded",
    "boatyard-where-a-lift-out-is-refused",
    "coalround-where-the-monthly-figure-is-worked-out",
    "pigeonloft-where-a-timed-in-bird-is-matched",
)

# Section 47's verdict table, cell by cell. Four of the twenty-four did not
# resolve, all four `code-review`, and which four is the whole of what section
# 50 has to read rather than drop.
_UNRESOLVED = {
    ("belfry-review-the-peals-and-the-board", _HAIKU),
    ("parishhall-review-the-hire-and-the-diary", _HAIKU),
    ("produceshow-review-the-points-and-the-sheet", _HAIKU),
    ("apiary-review-the-book-and-the-crop", _SONNET),
}

# Section 47's spend, per model and in total, to the fourth decimal the run log
# carries. The record states $3.96 against the $3-6 stated in section 46 before
# the first paid run, and against round 4's $3.2748.
_SPEND = {_HAIKU: 0.9794, _SONNET: 2.9836}
_TOTAL = 3.9631

# Section 47's per-action split of that spend: what the sixteen review cells
# took against the eight comprehension ones, which is where the range's
# headroom went.
_SPEND_BY_CATEGORY = {"code-review": 3.2095, "codebase-comprehension": 0.7535}

# Section 50's arithmetic over the sixteen review cells' answer files: every
# finding reported, split by which half of the key it lands in. The three
# numbers are the reading the section takes, and the fourth is their total.
_FINDINGS = {"accepted": 45, "rejected": 2, "unlisted": 4}
_FINDINGS_TOTAL = 51

# Section 51's archive paragraph: the free text the logs carry and no verdict
# reads. Pinned as the two counts the record quotes.
_OUTPUT_WORDS = 2373
_NOTED_FINDINGS = 51

# How many repositories carried two actions on the day this was recorded:
# round 4's six locate-against-fix pairs, and nothing else. Archived as a
# floor, because a later round authoring another such pair grows the number
# without changing the claim section 49 makes about it.
_LOCATE_FIX_REPOSITORIES_AS_RECORDED = 6

# The corpus size section 51's own fenced block printed on the day round 5 was
# recorded. Archived text, quoted back to prove the block says what the command
# said — a literal that never moves, however far the corpus grows afterwards.
# Where a record suite reads what a reader prints *today*, it derives the count
# from the checked-in task set instead (`tasks_in_set` in the round-6 suite).
_TASKS_AS_RECORDED = 113

# The two fields of a calibration block a later round moves, and the only two —
# the round-6 suite's rule, needed here the moment round 7 authored the ninth
# and tenth `code-review` tasks. A block holds numbers of two kinds. The
# **measured** ones — the baseline means, every `(n=…)`, the multipliers, the
# rung floor — are the round that published them, and no task authored
# afterwards touches them. The **counted** ones — how many tasks the row holds,
# and the mix its denominator is drawn from — grow the moment a later round
# authors another control in the category: unswept, changing no measurement,
# and moving two digits in a block section 48 quotes as printed. So the quoted
# block is compared with the counted ones written out. Rewriting the note
# instead would falsify it, because what it quotes is what the table printed
# that day.
_COUNTED_MIX = re.compile(
    r"^(   baseline mix +)\d+( single-file; )\d+( hand-authored)", re.MULTILINE
)
_COUNTED_ROW = re.compile(r"^(   \(zero-knob\)  )\d+ +", re.MULTILINE)


def counts_written_out(text: str) -> str:
    """This calibration output with its counted fields replaced by a mark."""
    return _COUNTED_ROW.sub(r"\1N ", _COUNTED_MIX.sub(r"\1N\2N\3", text))


def round_5_runs() -> dict[tuple[str, str], firstparty_v1.Run]:
    """Every run the sweep logged, keyed task x model.

    Read out of every log in the run-log directory and selected on the sweep
    id, which is what identifies a round: the sweep took four invocations, and
    a filename says nothing about which sweep a row belongs to.
    """
    runs = {
        (run.task_id, run.model): run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    }
    assert len(runs) == 24, "the round is 24 cells"
    return runs


def categories() -> dict[str, str]:
    """Each of the round's tasks against the category it declares."""
    return {task.id: task.category for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def verdicts() -> dict[tuple[str, str], bool]:
    """Each logged diff re-graded by its task's held-out tests.

    The computation `eval-v1 --replay` does, and the only way to a verdict: a
    run-log row carries the diff and no verdict at all. Module-scoped because
    grading twenty-four diffs is twenty-four pytest sessions and three tests
    below read the same answer.
    """
    tasks = {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}
    return {
        key: firstparty_v1.grade(tasks[key[0]], run.diff)
        for key, run in round_5_runs().items()
    }


def note_section(heading: str) -> str:
    """One numbered section of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"### {heading}\n")[1]
    return body.split("\n### ")[0].split("\n## ")[0]


def prose(text: str) -> str:
    """A passage with its wrapping collapsed. What a sentence of the record
    says is the pin; where the line happens to break is not, and a pin on the
    break would fail the next time a word is added upstream of it."""
    return " ".join(text.split())


def fenced_block(text: str) -> str:
    """The first fenced code block of a passage of the note."""
    return text.split("```\n")[1]


def strings(source: bytes) -> set[str]:
    """Every string literal a shipped grading module evaluates, docstrings
    left out: what a module says about a field in its own prose is not what it
    reads at grade time, and only the second is a claim about the verdict."""
    module = ast.parse(source.decode("utf-8"))
    docstrings = {
        ast.get_docstring(node, clean=False)
        for node in ast.walk(module)
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        )
    }
    return {
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    } - docstrings


def answer_file(run: firstparty_v1.Run) -> list[dict[str, str]]:
    """The answer file a run's workdir diff wrote, parsed.

    Every diff of this round creates exactly one file and nothing else — the
    deliverable — so the added lines of the diff are that file. Read here
    rather than by re-running grading because section 50 counts findings by
    which half of the key they land in, which is finer than the verdict.
    """
    added = [
        line[1:]
        for line in run.diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    parsed = json.loads("\n".join(added))
    assert isinstance(parsed, list)
    return parsed


def test_the_round_is_one_sweep_of_twenty_four_cells_under_one_agent_version(
) -> None:
    """Section 47's sweep facts, off the rows themselves.

    One sweep id over the invocations that logged rows and one agent version
    across all of them is the protocol's contract, and it is the only thing
    that makes the round's within-round comparisons free of a version
    boundary. A cell swept twice is schema-forbidden rather than checked here;
    what is checked is that each of the twelve tasks ran on each of the two
    ladder models, and that the twelve are the eight and the four the record
    names.
    """
    runs = round_5_runs()

    assert {run.sweep for run in runs.values()} == {_SWEEP}
    assert {run.agent_version for run in runs.values()} == {_AGENT_VERSION}
    assert {run.agent for run in runs.values()} == {"claude-code"}
    assert {run.as_of.isoformat() for run in runs.values()} == {_AS_OF}

    tasks = {task_id for task_id, _ in runs}
    assert tasks == set(_REVIEW) | set(_COMPREHENSION)
    assert len(tasks) == 12
    for task_id in tasks:
        assert {(task_id, _HAIKU), (task_id, _SONNET)} <= set(runs), task_id

    # What the twelve declare, which is the other half of section 47's first
    # paragraph: all controls, one surface, one language, one scale.
    declared = {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}
    for task_id in tasks:
        task = declared[task_id]
        assert task.control is True, task_id
        assert (task.surface, task.language, task.scale) == (
            "application", "python", "single-file"
        ), task_id
    assert {declared[task_id].category for task_id in _REVIEW} == {"code-review"}
    assert {declared[task_id].category for task_id in _COMPREHENSION} == {
        "codebase-comprehension"
    }


def test_the_round_cost_what_the_record_states() -> None:
    """Section 47's spend line, and the design note's own statement of it.

    The expectation was stated before the first paid run and the comparison is
    against round 4, so all three numbers travel together: what was expected,
    what it came to, and what the last round cost. The per-action split is
    pinned beside them because the range's headroom was asked for on
    `code-review`'s account and the record says that is where it went.
    """
    runs = round_5_runs()

    for model, spend in _SPEND.items():
        actual = sum(
            run.cost_usd for (_, run_model), run in runs.items() if run_model == model
        )
        assert round(actual, 4) == spend, model
    assert round(sum(run.cost_usd for run in runs.values()), 4) == _TOTAL

    category = categories()
    for name, spend in _SPEND_BY_CATEGORY.items():
        actual = sum(
            run.cost_usd
            for (task_id, _), run in runs.items()
            if category[task_id] == name
        )
        assert round(actual, 4) == spend, name

    measured = prose(note_section("47. What the round measured"))
    assert "Expected **$3–6**, stated in §46" in measured
    assert (
        "Actual **$3.96** — $0.9794 on haiku and $2.9836 on sonnet, "
        "$3.9631 in total — against round 4's **$3.2748**"
    ) in measured
    assert "**The estimate was honoured**" in measured


def test_the_limits_in_force_were_registered_before_the_sweep_and_never_reached(
) -> None:
    """Section 47's limits paragraph, against the table the runner reads.

    Both of the round's categories are registered, both at the flat default's
    own value, which is what makes the round's two new actions free of a
    ceiling difference and the round free of a cross-round caveat of its own.
    The second half is the round's own evidence that no verdict is a timeout
    in disguise: the longest run is well under the limit it ran under.
    """
    assert firstparty_v1.LIVE_RUN_LIMITS_S["code-review"] == 600
    assert firstparty_v1.LIVE_RUN_LIMITS_S["codebase-comprehension"] == 600
    # Round 4's two are still registered beside them, at the same value: the
    # table carries four entries and all four read the flat default.
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension"
    }
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}

    latencies = [run.latency_s for run in round_5_runs().values()]
    assert round(max(latencies), 1) == 265.2
    assert round(statistics.mean(latencies), 1) == 77.6

    measured = prose(note_section("47. What the round measured"))
    assert (
        "`code-review` and `codebase-comprehension` in `LIVE_RUN_LIMITS_S`, "
        "both at **600 seconds**"
    ) in measured
    assert "**No cross-round caveat arises for this round's own cells**" in measured
    assert "the round's longest run was **265.2 s**" in measured


def test_the_rider_ran_at_the_flat_default_and_is_recorded_apart() -> None:
    """Section 47's rider paragraph: the cell that logged nothing.

    Three claims, and each is checkable. The rider's category is not in the
    limits table, so what it ran under is the flat default and not a
    registration — numerically the same 600 and a different kind of fact. Its
    log is empty, so the cell is not among the round's twenty-four and it did
    not repair round 3's incomplete cell: `pysm-work-out-a-way-there` has a
    haiku row and no sonnet row anywhere in the corpus, exactly as section 29.4
    left it.
    """
    assert _RIDER[0] not in {task_id for task_id, _ in round_5_runs()}
    assert "feature-dev" not in firstparty_v1.LIVE_RUN_LIMITS_S
    task = next(
        t for t in firstparty_v1.load_task_set(_TASKS) if t.id == _RIDER[0]
    )
    assert task.category == "feature-dev"
    assert firstparty_v1.live_run_limit_s(task) == firstparty.RUN_TIMEOUT_S == 600

    assert (_LOGS / _RIDER_LOG).read_text(encoding="utf-8").strip() == ""

    every_run = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.task_id == _RIDER[0]
    ]
    assert {run.model for run in every_run} == {_HAIKU}, (
        "the rider logged no sonnet row in any round; round 3's cell stands"
    )

    measured = prose(note_section("47. What the round measured"))
    assert "**timed out again**" in measured
    assert "**flat default of 600 seconds**" in measured
    assert "**it is not merged into round 3's readings**" in measured
    assert "`3.73x (n=1)`" in measured


def test_which_cells_resolved_per_category_and_model(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 47's resolution table: 20 of 24, and which four did not.

    Pinned per cell rather than as two counts, because the counts are the same
    under several different stories about which cells failed and section 50
    turns on which ones they were.
    """
    assert {key for key, resolved in verdicts.items() if not resolved} == _UNRESOLVED

    category = categories()
    counts = {
        (name, model): sum(
            1
            for (task_id, run_model), resolved in verdicts.items()
            if category[task_id] == name and run_model == model and resolved
        )
        for name in ("code-review", "codebase-comprehension")
        for model in (_HAIKU, _SONNET)
    }
    assert counts == {
        ("code-review", _HAIKU): 5,
        ("code-review", _SONNET): 7,
        ("codebase-comprehension", _HAIKU): 4,
        ("codebase-comprehension", _SONNET): 4,
    }
    assert sum(counts.values()) == 20

    printed = fenced_block(note_section("47. What the round measured"))
    assert printed == (
        "                  code-review  codebase-comprehension\n"
        "claude-haiku-4-5  5/8          4/4\n"
        "claude-sonnet-5   7/8          4/4\n"
    )


def test_the_rungs_the_round_landed_on() -> None:
    """Section 47's rung line, through the code the reports read rungs with.

    Three `sonnet-only`, all `code-review`, and nothing `unsolved` — so the
    corpus's unsolved census is unmoved by this round. Taken from
    `observed_outcomes` over the round's own tasks and runs rather than from
    the verdicts above, so that the record's rungs are the reports' rungs and
    not this file's arithmetic about them.

    Selected by the round's own task ids and not by its two actions: a later
    round authoring another `code-review` task adds an unswept one to the
    census, whose rung is `unswept` and whose presence says nothing about what
    round 5 landed on — which is what round 7 did.
    """
    own = set(_REVIEW + _COMPREHENSION)
    tasks = [task for task in firstparty_v1.load_task_set(_TASKS) if task.id in own]
    assert len(tasks) == len(own)
    outcomes = reconcile_v1.observed_outcomes(
        tasks, list(round_5_runs().values()), source="round-5 record"
    )

    sonnet_only = {
        task_id for task_id, outcome in outcomes.items()
        if outcome.rung == "sonnet-only"
    }
    assert sonnet_only == {task_id for task_id, model in _UNRESOLVED if model == _HAIKU}
    assert sonnet_only <= set(_REVIEW)
    assert {outcome.rung for outcome in outcomes.values()} == {
        "haiku-solvable", "sonnet-only"
    }
    assert sum(1 for o in outcomes.values() if o.rung == "haiku-solvable") == 9


def test_every_finding_reported_lands_where_section_50_says(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 50's arithmetic over the sixteen review cells.

    A review verdict is binary, so the split between the key's two halves is
    finer than any verdict and has to be counted here: 45 answers matched a
    planted finding, two matched a rejected one, and four were unlisted and
    archived. Compared by exact (file, symbol) rather than through
    `_answer.matches`, which is sound only because every answer of this round
    spells its location exactly as the key does — asserted by reconciling the
    split against the graded verdicts, which do go through the real
    comparison: a cell is resolved iff every planted finding of its key was
    matched and no rejected one was.
    """
    runs = round_5_runs()
    category = categories()
    tally = {"accepted": 0, "rejected": 0, "unlisted": 0}
    noted = 0
    primaries = 0

    for (task_id, model), run in runs.items():
        if category[task_id] != "code-review":
            continue
        key = json.loads(
            (_TASKS / task_id / "grading" / "findings-key.json").read_text(
                encoding="utf-8"
            )
        )
        accepted = [
            [(place["file"], place["symbol"]) for place in planted["any"]]
            for planted in key["accepted"]
        ]
        rejected = {(place["file"], place["symbol"]) for place in key["rejected"]}

        matched: set[int] = set()
        tripped = False
        for finding in answer_file(run):
            location = (finding["file"], finding["symbol"])
            noted += 1 if finding.get("note") else 0
            hit = [i for i, places in enumerate(accepted) if location in places]
            if hit:
                tally["accepted"] += 1
                matched.update(hit)
                # Which alternative it landed on: section 50 reads that every
                # accepted answer of the round named the primary, so the
                # class-level alternatives #85 added were never needed.
                primaries += sum(1 for i in hit if accepted[i][0] == location)
            elif location in rejected:
                tally["rejected"] += 1
                tripped = True
            else:
                tally["unlisted"] += 1

        assert verdicts[task_id, model] == (
            len(matched) == len(accepted) and not tripped
        ), f"{task_id} {model}: the split disagrees with the graded verdict"

    assert tally == _FINDINGS
    assert sum(tally.values()) == _FINDINGS_TOTAL
    assert noted == _NOTED_FINDINGS, "every finding of the round carries a note"
    assert primaries == _FINDINGS["accepted"], (
        "an accepted answer landed on an alternative rather than the primary"
    )

    read = prose(note_section("50. The four cells that did not resolve, read"))
    assert (
        "51 findings reported, of which 45 matched a planted finding, "
        "two matched a rejected one and four were unlisted and archived"
    ) in read
    # The reading the section takes about the key rather than about the model,
    # and the qualifier that keeps it a reading: the accepted half's
    # description levels held everywhere.
    assert "That is a reading about the key's description levels" in read
    assert (
        "all 45 accepted answers of the round named their finding's "
        "**primary**"
    ) in read


def test_no_repository_carries_two_of_the_round_s_actions() -> None:
    """Section 49's claim, which is about the corpus and not a number.

    Round 4's locate-against-fix reading was drawable only because one
    repository carried two actions — byte for byte the same starting tree
    under a `fault-location` task and a `bug-fix` one. Grouping every task's
    `repo/` by the bytes it ships found exactly six such repositories on the
    day this was recorded, all of them round 4's, and none of them carrying
    either action this round measured. So the three-way comparison is quoted
    nowhere, and what would have to change for it to be quotable is checked
    here rather than asserted in prose.

    What is held is the *shape* and not the six: a later round authoring
    another locate/fix pair adds a seventh such repository without touching
    what this section says, so the recorded six is a floor and every shared
    repository still has to be a locate-against-fix pair carrying neither of
    this round's two actions.
    """
    shipped: dict[str, set[str]] = {}
    tree_of: dict[str, str] = {}
    for task in firstparty_v1.load_task_set(_TASKS):
        repo = _TASKS / task.id / "repo"
        if not repo.is_dir():
            continue
        digest = hashlib.sha256()
        for path in sorted(path for path in repo.rglob("*") if path.is_file()):
            digest.update(str(path.relative_to(repo)).encode("utf-8"))
            digest.update(path.read_bytes())
        shipped.setdefault(digest.hexdigest(), set()).add(task.category)
        tree_of[task.id] = digest.hexdigest()

    shared = [actions for actions in shipped.values() if len(actions) > 1]
    assert shared == [{"bug-fix", "fault-location"}] * len(shared), (
        "a repository carrying two actions is a locate-against-fix pair, which "
        "is the only construct in this corpus that shares one"
    )
    assert len(shared) >= _LOCATE_FIX_REPOSITORIES_AS_RECORDED
    assert not any(
        {"code-review", "codebase-comprehension"} & actions for actions in shared
    )

    # And the round's own twelve sit on twelve distinct trees: one action each,
    # which is the sentence section 49 opens with. Read off the round's own task
    # ids rather than off its two actions, because a later round authoring
    # another review task adds a thirteenth tree carrying one of them and says
    # nothing about what round 5 sat on — which is what round 7 did.
    signatures = {tree_of[task_id] for task_id in _REVIEW + _COMPREHENSION}
    assert len(signatures) == 12
    assert all(len(shipped[digest]) == 1 for digest in signatures)

    quoted = prose(
        note_section(
            "49. Review against locating against fixing: what this round "
            "cannot quote"
        )
    )
    assert "**Round 5's twelve repositories carry one action each**" in quoted
    assert (
        "**not quoted here, because there is nothing to quote it over**"
    ) in quoted
    assert (
        "the round was not authored to produce it and this is not a headline"
    ) in quoted


def test_calibrate_v1_prints_the_two_new_rows_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 48's quoted rows, against what the command actually prints.

    Both rows are their own category's denominator, so both multipliers read
    1.00x by construction and what the round publishes is the baseline mean
    each carries with the n it was taken over. The note quotes the two blocks
    as printed, which is a claim about bytes: it is checked as one, block by
    block, because their adjacency in the printed table is not a claim the
    note makes.

    With the two counted fields written out on both sides (`counts_written_out`
    and the comment over it). How many tasks a category holds is not something
    round 5 measured, and round 7's ninth and tenth `code-review` tasks moved
    it; every figure the section actually reads — the means, the n each was
    taken over, the multipliers, the rung floor — is still compared as printed.
    """
    main([
        "calibrate-v1",
        "--tasks", str(_TASKS),
        "--replay", str(_LOGS),
    ])
    out = capsys.readouterr().out

    quoted = fenced_block(note_section("48. The two new categories' rows, as printed"))
    for block in quoted.split("\ncategory ")[0:1] + [
        "category " + rest for rest in quoted.split("\ncategory ")[1:]
    ]:
        assert counts_written_out(block.strip("\n")) in counts_written_out(out), (
            "a quoted block of the note is not what the table prints:\n" + block
        )
    # Named again here, so that a note edited to match a changed table still
    # has to face the numbers the round actually published.
    assert (
        "   baseline mean cost   claude-haiku-4-5 $0.0923 (n=8), "
        "claude-sonnet-5 $0.3089 (n=8)"
    ) in quoted
    assert (
        "   baseline mean cost   claude-haiku-4-5 $0.0603 (n=4), "
        "claude-sonnet-5 $0.1281 (n=4)"
    ) in quoted
    assert (
        "   (zero-knob)  8      1.00x (n=8)       1.00x (n=8)      "
        "haiku-solvable (n=8)"
    ) in quoted
    assert (
        "   (zero-knob)  4      1.00x (n=4)       1.00x (n=4)      "
        "haiku-solvable (n=4)"
    ) in quoted

    # The model gap the section reads off those denominators, computed from
    # the table rather than pinned twice: one ratio per category, and the claim
    # that `code-review`'s is the widest is a claim about all of them.
    gaps: dict[str, float] = {}
    unpriced: set[str] = set()
    category = ""
    for line in out.splitlines():
        if line.startswith("category "):
            category = line.split()[1]
        elif line.startswith("   baseline mean cost") and category:
            figures = [float(figure) for figure in re.findall(r"\$([\d.]+)", line)]
            if not figures:
                # A category whose tasks are authored but unswept prints "-"
                # for both means — round 8's `test-authoring`, which arrived in
                # the table before its sweep did. There is no ratio to take,
                # and leaving it out is what keeps this a reading over the
                # categories that have priced controls behind them.
                unpriced.add(category)
                continue
            haiku, sonnet = figures
            gaps[category] = round(sonnet / haiku, 2)
    # Round 8's sweep priced `test-authoring`, so nothing prints "-" today;
    # the mechanism above stays for the next category that arrives unswept.
    assert unpriced == set()
    assert gaps == {
        "bug-fix": 2.64,
        "code-review": 3.35,
        "codebase-comprehension": 2.12,
        "fault-location": 2.58,
        "feature-dev": 2.60,
        "refactor": 2.87,
        "test-authoring": 2.44,
    }
    assert max(gaps, key=lambda name: gaps[name]) == "code-review"

    read = prose(note_section("48. The two new categories' rows, as printed"))
    assert (
        "Sonnet costs 3.35× haiku on this category's controls, against 2.87× on "
        "`refactor`, 2.64× on `bug-fix`, 2.60× on `feature-dev`, 2.58× on "
        "`fault-location` and 2.12× on `codebase-comprehension`"
    ) in read


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 51's verification, run rather than remembered.

    Each of the four logs is replayed into a scratch dataset of its own, and
    all four into one merged dataset. The four per-log datasets together have
    to be the merged one record for record: no row missing, none duplicated,
    no field differing. Every record also has to carry its log row's own
    measurements, because replay re-grades the diff and never re-runs the
    agent. The fourth log is the rider's and is empty; it has to replay to
    nothing rather than to an error, which is the whole of what an invocation
    that logged no row can be shown to do.
    """
    per_log: list[dict[str, object]] = []
    merged_path = tmp_path / "merged.jsonl"
    for name in _LOG_NAMES:
        log = _LOGS / name
        alone = tmp_path / name
        for data in (alone, merged_path):
            main(["eval-v1", "--tasks", str(_TASKS), "--replay", str(log),
                  "--data", str(data)])
        capsys.readouterr()
        per_log.extend(
            json.loads(line) for line in alone.read_text().splitlines() if line.strip()
        )

    merged = [
        json.loads(line)
        for line in merged_path.read_text().splitlines()
        if line.strip()
    ]
    assert len(merged) == 24

    def cell(record: dict[str, object]) -> tuple[str, str]:
        return str(record["instance_id"]), str(record["model"])

    assert sorted(per_log, key=cell) == sorted(merged, key=cell)

    runs = round_5_runs()
    for record in merged:
        run = runs[record["instance_id"], record["model"]]
        assert record["cost_usd"] == run.cost_usd
        assert record["turns"] == run.turns
        assert record["tokens_in"] == run.tokens_in
        assert record["tokens_out"] == run.tokens_out
        assert record["latency_s"] == run.latency_s
        assert record["agent_version"] == run.agent_version
        assert record["as_of"] == run.as_of.isoformat()
        assert record["benchmark"] == "first-party-v1"

    # The commands the note prints, against the four logs they name: what each
    # replay evaluated and resolved is quoted, and the rider's empty log is
    # quoted at zero rather than left out.
    printed = fenced_block(
        note_section("51. Replay, the archive, and how each was shown")
    )
    for name, evaluated, resolved in (
        (_LOG_NAMES[0], 1, 1), (_LOG_NAMES[1], 11, 8),
        (_LOG_NAMES[2], 12, 11), (_LOG_NAMES[3], 0, 0),
    ):
        assert f"--replay data/first-party-v1-runs/{name}" in printed
        assert (
            f"  evaluated {evaluated} runs over {_TASKS_AS_RECORDED} tasks "
            f"({resolved} resolved)"
        ) in printed
        assert len(firstparty_v1.load_runs(_LOGS / name)) == evaluated, name


def test_the_free_text_is_archived_in_the_logs_and_no_verdict_reads_it() -> None:
    """Section 51's archive paragraph, counted off the logs.

    The claim is two-sided and both sides are checkable here: the free text is
    in the checked-in logs, and nothing that decides a verdict looks at it. The
    second side is checked at the source — the shipped comparison module reads
    a finding's location and the key, and a note is tolerated beside a location
    and never inspected — rather than by asserting it in prose.
    """
    runs = round_5_runs()
    assert sum(len(run.output.split()) for run in runs.values()) == _OUTPUT_WORDS
    assert all(run.output.strip() for run in runs.values()), (
        "every cell of the round left prose behind"
    )

    # The module that grades a review answer never names the note: every
    # string it evaluates is checked, and its docstrings — which discuss the
    # note at length — are excluded, because what a module says about a field
    # is not what it reads.
    evaluated = strings(firstparty_v1.findings_module_source())
    assert "note" not in evaluated
    assert "output" not in evaluated
    # And the two fields a verdict does read are read where the forgiveness
    # lives, which is the module this one imports rather than restates.
    assert {"file", "symbol"} <= strings(firstparty_v1.answer_module_source())

    read = prose(note_section("51. Replay, the archive, and how each was shown"))
    assert "**the verdict does not read a word of it**" in read
    assert "2,373 words of agent `output`" in read
