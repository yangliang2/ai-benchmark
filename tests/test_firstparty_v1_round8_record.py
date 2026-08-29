"""Round 8's record, pinned: what sections 69-75 of the design note publish.

The round swept nine cells over **three `test-authoring` tasks** — the corpus's
first, and the first graded by a verdict that is not "the held-out tests
passed". Its novelty is a *verdict shape*, the **mutation gate**, so its record
has one reading no earlier record could produce and one temptation no earlier
record faced. The reading is **which gate** an unresolved cell failed: a suite
that fails on the pristine starting repository is a false accusation, a suite
that passes pristine and lets a planted mutant live is a hole in coverage, and
those are different failures with the same `resolved: 0.0`. The temptation is
the kill rate — "five of six killed" — which §67.3 ruled out as a second
quality metric wearing `resolved`'s name, so this file checks that no fraction
over mutants is quoted anywhere in the round's own sections.

Every figure is pinned rather than derived, which is the point: a derived
expectation follows the corpus wherever it goes, and these numbers are quoted
in the design note and read by whoever is deciding what a round cost. The pins
come in two halves, as rounds 5, 6 and 7's do. The first is arithmetic over the
checked-in run logs and the verdicts re-grading their diffs produces — here
including the two gates run apart, which is the only way "which gate" is
derivable at all, since a run-log row carries the diff and no verdict and
`grade()` returns one bool. The second reads the design note itself — its
quoted tables against what the logs actually say, its quoted commands against
what they actually print — because a record whose numbers drift from the
artifacts that earned them is the defect this file exists to catch, and the
record is prose that nothing else checks.

The round's runs are selected by their **sweep id** and never by log filename:
the sweep protocol bans selecting run logs by name, having watched the first
pass of the round-1 analysis silently drop two paid cells that way. The four
filenames appear here only where a command has to be given a log to replay,
which is section 75's verification.
"""

import json
import platform
import re
import statistics
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest

from ai_benchmark import agents, firstparty, firstparty_v1, pricing, reconcile_v1
from ai_benchmark.cli import main

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_SWEEP = "round-8"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-20"
# Neither harness crosses a version boundary from round 7, which is why the
# record can read its columns against that round's without a caveat.
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.235 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}

# The four logs the sweep's four invocations wrote, and what each replays to.
# Named only so that section 75's replay can be given one log at a time;
# nothing here selects runs by them. None of the four is empty, which is the
# difference from round 7 and is asserted rather than assumed.
_REPLAYED = {
    "2026-08-20-r8-a.jsonl": (1, 1),
    "2026-08-20-r8-b.jsonl": (2, 2),
    "2026-08-20-r8-c.jsonl": (3, 3),
    "2026-08-20-r8-d.jsonl": (3, 2),
}
_DRY_CELL = "playbill-put-the-setting-of-the-bill-under-test"

# Section 70's spend, per combination and per cost source. Two of these are
# bills and one is an estimate, so they are pinned apart; the total below is
# pinned separately because it is the form section 68.4 registered the bound
# in and not a quantity with a single meaning.
_SPEND = {_HAIKU: 0.7237, _SONNET: 1.7679, _TERRA: 0.2698}
_BILLED = 2.4916
_TOTAL = 2.7614
_PER_CELL = {_HAIKU: 0.2412, _SONNET: 0.5893, _TERRA: 0.0899}

# Round 7's per-cell figures, which section 68.4 registered this round against
# and section 70 reports each column beside.
_ROUND_7_PER_CELL = {_HAIKU: 0.1038, _SONNET: 0.3025, _TERRA: 0.1146}
_REGISTERED_COLUMN = {_HAIKU: 0.3114, _SONNET: 0.9075}
_REGISTERED_CODEX_BAND = (0.17, 1.01)
_REGISTERED_RANGE = (1.5, 5.0)
_REGISTERED_ENVELOPE = (1.39, 2.23)
_REGISTERED_CLAUDE = 1.2189
_DEARER = {_HAIKU: 2.32, _SONNET: 1.95, _TERRA: 0.78}
_CLAUDE_DEARER = 2.04

# Section 70's output-token evidence for the lesson section 68.4 named and
# priced into one column only: a whole test suite is a larger write than a
# locate answer.
_OUTPUT_PER_CELL = {_HAIKU: 15_907, _SONNET: 12_754}
_ROUND_7_OUTPUT_PER_CELL = {_HAIKU: 5_388, _SONNET: 5_049}

# Section 70's Codex token totals and the two bounds a reader can recompute
# from the rows: all-cached below, all-uncached above, the logged figure
# between. The split the figure was actually priced from is not on the row,
# which is the paragraph's point.
_CODEX_TOKENS = (361_275, 8_122)
_CODEX_PROJECTED_TOKENS = (464_960, 6_513)
_ALL_CACHED = 0.1697
_ALL_UNCACHED = 0.8200
_EFFECTIVE_RATE = 0.4771
_ROUND_7_EFFECTIVE_RATE = 0.5714
_ROUND_6_EFFECTIVE_RATE = 0.3996
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 69's resolution line, and the one cell it turns on.
_RESOLVED = {_HAIKU: 3, _SONNET: 3, _TERRA: 2}
_UNRESOLVED = (_DRY_CELL, _TERRA)

# Section 69's limits paragraph: nothing came near the ceiling every cell ran
# under, and the ceiling is the flat default rather than a registered row.
_LONGEST_S = 289.7
_MEAN_S = 131.8
_LONGEST_CELL = "lido-put-the-admissions-desk-under-test"
_CATEGORY = "test-authoring"
_REGISTERED_LIMITS = {
    "bug-fix", "fault-location", "code-review", "codebase-comprehension"
}

# Registered after this round, and subtracted from the live table below rather
# than swallowed by it: round 13 (design note 118.9) registers
# `performance-optimisation` at the same 600. Every limit claim here is about
# the rows in force when this round ran, so the later entry is named explicitly
# and the next addition has to be a visible edit here too.
_LATER_LIMITS = {"performance-optimisation"}

# Section 71's turn line. Quoted so that section 74's refusal to compare across
# the harness boundary is anchored to numbers rather than to an assertion.
_TURNS = {_HAIKU: 57, _SONNET: 55, _TERRA: 24}
_TURN_RANGE = {_HAIKU: (12, 31), _SONNET: (15, 22), _TERRA: (5, 10)}

# Section 69's toolchain paragraph. Python only this round: no cell is a
# TypeScript task, so `node --test` graded nothing here.
_PYTHON_VERSION = "3.14.4"

# Section 72's gate reading. Gate 1 was passed by all nine; one cell failed
# gate 2, and the mutant that survived is named because a red cell with a
# locatable reason is what section 68.7 registered instead of a kill rate.
_SURVIVOR = "02-set-a-line-without-counting-the-space-between-words.diff"

# Section 72's collection disclosure: one diff wrote a file outside the
# collected subtree and it was archived, and no diff touched the module under
# test.
_ARCHIVED = ((_DRY_CELL, _SONNET), "pytest.ini")
_MODULES_UNDER_TEST = ("lido.py", "playbill.py", "register.py")

# Section 73's coverage figure, per language. The Python column is round 7's
# plus this round's three; the TypeScript rows are round 7's exactly. Rows
# joined after the round it records: round 10 authored its three
# `investigation` tasks and round 11 its three `requirement-decomposition`
# ones, Python controls all — round 12's three explain-style tasks then
# grew `codebase-comprehension`'s row, and round 13's ticket 04 opened
# `performance-optimisation`'s with its first task and its ticket 05 grew
# it to three — and this live read moves with the corpus while the note's
# own quoted table stays the snapshot it was.
_PYTHON_COVERAGE = {
    "bug-fix": 6, "fault-location": 6, "feature-dev": 71, "refactor": 18,
    "codebase-comprehension": 7, "code-review": 8, "test-authoring": 3,
    "investigation": 3, "requirement-decomposition": 3,
    "performance-optimisation": 3,
}
_TYPESCRIPT_COVERAGE = {
    "bug-fix": 3, "fault-location": 3, "feature-dev": 3, "refactor": 3,
    "code-review": 2,
}
_PYTHON_TASKS = 128
# What the runs line counts instead: the Python tasks that have rows. The two
# were one number until round 10 authored tasks after every sweep — a task
# with no rows joins the task-set line and not this one.
_PYTHON_TASKS_WITH_RUNS = 116
# What round 10 has authored: its three `investigation` tasks, Python
# controls all. Named so the reconcile line this record quotes can be
# rebuilt from the live figures rather than retyped. Its sweep then landed
# on 2026-08-24 — nine rows, six of them claude-code Python ones that
# survive both selections the way this round's six did.
_ROUND_10_TASKS = 3
_ROUND_10_ROWS = 9
_ROUND_10_CLAUDE_CODE_ROWS = 6
# And what round 11 has authored: its three `requirement-decomposition`
# tasks, Python controls all. Their own round's suites count them; this file
# only keeps the live arithmetic honest. Its sweep then landed on 2026-08-26
# — nine rows, six of them claude-code Python ones that survive both
# selections the way this round's six did.
_ROUND_11_TASKS = 3
_ROUND_11_ROWS = 9
_ROUND_11_CLAUDE_CODE_ROWS = 6
# And round 12's three explain-style `codebase-comprehension` tasks, Python
# controls graded by the point gate. Its sweep then landed on 2026-08-28 —
# nine rows, six of them claude-code Python ones that survive both selections
# the way this round's six did.
_ROUND_12_TASKS = 3
_ROUND_12_ROWS = 9
_ROUND_12_CLAUDE_CODE_ROWS = 6
# And round 13's three `performance-optimisation` tasks, Python controls
# graded by the complexity proxy (ADR-0006). Ticket 04 moved the live
# task-set arithmetic by one and ticket 05's two further tasks by two more;
# its sweep then landed on 2026-08-29 — nine rows, six of them claude-code
# Python ones that survive both selections the way this round's six did.
_ROUND_13_TASKS = 3
_ROUND_13_ROWS = 9
_ROUND_13_CLAUDE_CODE_ROWS = 6

# Section 75's reader counts. Unlike round 7's, this round's claude-code rows
# are Python, so the default reading picks them up with no flag at all.
_CLAUDE_CODE_PYTHON_RUNS = 231
_PYTHON_CONTROLS = 61
_PYTHON_CONSTRUCTED = 67
_ALL_ROWS = 306
_ROUND_8_ROWS = 9
_CLAUDE_CODE_ROUND_8_ROWS = 6
_CONSTRUCTED_TASKS = 67

# Section 75's archive line: what the heap-3 grader's calibration corpus stood
# at when §67.1 counted it, and what round 8's nine answers make it.
_ARCHIVE_BEFORE = 297
_ARCHIVE_NOW = 306


class Gates(NamedTuple):
    """One cell's two gates, run apart, beside the verdict `grade()` gives.

    A named shape rather than a dict because the whole point of section 72 is
    that these are three different facts: whether the suite accused correct
    code, which planted mutants it let live, and the one bool the shipped
    grader returns for both.
    """

    gate_1: bool
    survivors: list[str]
    verdict: bool


def note_section(heading: str) -> str:
    """One numbered section of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"### {heading}\n")[1]
    return body.split("\n### ")[0].split("\n## ")[0]


def note_part(heading: str) -> str:
    """One top-level part of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"## {heading}\n")[1]
    return body.split("\n## ")[0]


def prose(text: str) -> str:
    """A passage with its wrapping collapsed. What a sentence of the record
    says is the pin; where the line happens to break is not, and a pin on the
    break would fail the next time a word is added upstream of it."""
    return " ".join(text.split())


def fenced_blocks(text: str) -> list[str]:
    """Every fenced code block of a passage of the note, in order."""
    return text.split("```\n")[1::2]


def record_sections() -> list[str]:
    """The record's own sections, by heading, in order."""
    return [
        "69. What the round measured",
        "70. Spend, by cost source, against the range registered before it",
        "71. The nine cells under three combinations",
        "72. Which gate, and what the collection rule archived",
        "73. The coverage table, as the lint prints it",
        "74. What this round cannot say",
        "75. Replay, the readers, and heap 1 closed",
    ]


def registered_cells() -> list[str]:
    """Section 68.1's register, read back out of the pre-registration.

    The register is the fenced list in the note, written before the first paid
    run, so what the round swept is compared against the register itself and
    not against a copy of it made afterwards.
    """
    line = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)\s+\(.+\)$")
    for block in fenced_blocks(
        note_part("Round 8 cells and cost — registered 2026-08-20")
    ):
        lines = [text.strip() for text in block.splitlines() if text.strip()]
        matched = [match for text in lines if (match := line.fullmatch(text))]
        if len(matched) == len(lines) and matched:
            return [match.group(1) for match in matched]
    raise AssertionError("section 68.1's register is not in the note")


def tasks_in_set() -> int:
    """How many tasks the checked-in set holds, as `eval-v1` counts them.

    Derived rather than pinned: `eval-v1 --replay` has no language selection
    and prints today's count, so a later round authoring a task moves the
    number the replay block quotes and this pin has to move with it.
    """
    return len(firstparty_v1.load_task_set(_TASKS))


def round_8_runs() -> dict[tuple[str, str], firstparty_v1.Run]:
    """Every run the sweep logged, keyed task x model.

    Read out of every log in the run-log directory and selected on the sweep
    id, which is what identifies a round: a filename says nothing about which
    sweep a row belongs to.
    """
    logged = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    ]
    assert len(logged) == 9, "the round is nine cells"
    runs = {(run.task_id, run.model): run for run in logged}
    assert len(runs) == 9, "a cell was swept twice"
    return runs


def swept_tasks() -> list[str]:
    """The round's three task ids, in corpus order."""
    ids = sorted({task_id for task_id, _ in round_8_runs()})
    assert len(ids) == 3
    return ids


def tasks() -> dict[str, firstparty_v1.Task]:
    """The checked-in task set, by id."""
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def gates() -> dict[tuple[str, str], Gates]:
    """Both gates of every cell, run apart, plus the verdict `grade()` gives.

    This is section 72's whole subject and the one computation an earlier
    record's suite had no need of. `grade()` dispatches a mutation-keyed task
    to `_mutation_gate`, which returns one bool and stops at the first
    surviving mutant — so "which gate failed" is not readable off a verdict and
    has to be re-derived by running the pieces the gate runs: the collected
    suite against a fresh copy of the pristine repository, then against each
    planted mutant in turn. Every survivor is collected here rather than only
    the first, because the record names one and a silent second would be a
    number this file could not see.

    The verdict is taken from `grade()` beside them and reconciled with the two
    gates, so that this is a reading of the shipped grader and not a second
    grading pipeline that happens to agree with it.
    """
    declared = tasks()
    derived: dict[tuple[str, str], Gates] = {}
    for key, run in sorted(round_8_runs().items()):
        task = declared[key[0]]
        # The loader refuses a mutation-keyed task declaring no test path, so
        # this is unreachable — said out loud because the gate collects that
        # subtree and nothing else, and "the whole workdir" is the hole §67.4
        # exists to close.
        test_path = task.test_path
        assert test_path is not None, task.id
        with tempfile.TemporaryDirectory(prefix="round8-gates-") as name:
            root = Path(name)
            gate_1 = firstparty_v1._collected_suite_verdict(
                task, run.diff, root / "pristine", None,
                test_path=test_path, timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
            )
            survivors = [
                patch.name
                for index, patch in enumerate(firstparty_v1.mutant_patches(task))
                if firstparty_v1._collected_suite_verdict(
                    task, run.diff, root / f"mutant-{index}", patch,
                    test_path=test_path,
                    timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
                ) is not False
            ]
        verdict = firstparty_v1.grade(task, run.diff)
        assert verdict == (gate_1 is True and not survivors), (
            f"{key}: the two gates disagree with the shipped verdict"
        )
        derived[key] = Gates(gate_1 is True, survivors, verdict)
    return derived


@pytest.fixture(scope="module")
def verdicts(gates: dict[tuple[str, str], Gates]) -> dict[tuple[str, str], bool]:
    """Every cell of section 71's table, keyed task x model.

    Taken from the `gates` fixture rather than graded a second time: the
    fixture calls `firstparty_v1.grade` on every cell already, and grading a
    mutation-keyed diff twice is nine pristine runs and up to fifty-one mutant
    runs for a bool this module already holds.
    """
    return {key: derived.verdict for key, derived in gates.items()}


def cost_column(task_id: str, model: str, resolved: bool) -> str:
    """One cell of section 71's table: its verdict and its cost."""
    verdict = "resolved  " if resolved else "unresolved"
    return f"{verdict} ${round_8_runs()[task_id, model].cost_usd:.4f}"


def cell_table(verdicts: dict[tuple[str, str], bool]) -> str:
    """Section 71's table, rebuilt from the logs and the graded verdicts.

    Byte for byte what the note quotes, including the three header lines that
    carry each column's cost source — the one piece of the table that is not a
    measurement and the one a reader most needs. The shape is round 7's §62
    table at three rows instead of fourteen.
    """
    ids = swept_tasks()
    width = max(len(task_id) for task_id in ids)
    lines = [
        (" " * (width + 2) + "  ".join(f"{cell:<18}" for cell in row)).rstrip()
        for row in (
            ("claude-code x", "claude-code x", "codex x"),
            (_HAIKU, _SONNET, _TERRA),
            ("vendor-reported", "vendor-reported", "table-derived"),
        )
    ]
    lines += [
        (
            f"{task_id:<{width}}  "
            + "  ".join(
                f"{cost_column(task_id, model, verdicts[task_id, model]):<18}"
                for _, model in _COMBINATIONS
            )
        ).rstrip()
        for task_id in ids
    ]
    return "\n".join(lines) + "\n"


def gate_table(gates: dict[tuple[str, str], Gates]) -> str:
    """Section 72's table, rebuilt from the two gates run apart.

    One row per cell, and the gate-2 column says whether a planted mutant
    survived and never how many did: the count is the kill rate §67.3 refuses,
    and a table that printed it would be the second quality metric arriving
    through a column header.
    """
    ids = swept_tasks()
    labels = [(task_id, model) for task_id in ids for _, model in _COMBINATIONS]
    width = max(len(f"{task_id} x {model}") for task_id, model in labels)
    lines = [f"{'cell':<{width}}  {'gate 1':<8}gate 2"]
    for task_id, model in labels:
        derived = gates[task_id, model]
        first = "passed" if derived.gate_1 else "failed"
        second = (
            "a planted mutant survived"
            if derived.survivors
            else "every planted mutant killed"
        )
        pad = width - len(task_id) - 3
        lines.append(f"{task_id} x {model:<{pad}}  {first:<8}{second}")
    return "\n".join(lines) + "\n"


def test_the_round_swept_exactly_the_cells_that_were_registered() -> None:
    """Section 69's sweep facts, off the rows themselves, against section 68.

    The register is read out of the pre-registration rather than restated, so
    this is the comparison the round exists to be judged by: three ids written
    down before the first paid run against nine cells that came back. One sweep
    id and one version per harness over all of them is the protocol's contract,
    and this round crosses no version boundary at all — both harnesses are at
    round 7's version, which is why the two rounds' columns can be read against
    each other in section 70 without a caveat.
    """
    runs = round_8_runs()

    assert {run.sweep for run in runs.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in runs.values()} == {_AS_OF}
    assert {(run.agent, run.model) for run in runs.values()} == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version for run in runs.values() if run.agent == agent
        } == {version}, agent

    # The same versions round 7 ran under, read off that round's own rows
    # rather than quoted from §60, which is what "crosses no boundary" means.
    round_7 = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == "round-7"
    ]
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version for run in round_7 if run.agent == agent
        } == {version}, agent

    registered = registered_cells()
    assert len(registered) == 3 == len(set(registered))
    assert set(swept_tasks()) == set(registered), (
        "the cells swept are not the cells registered before the sweep"
    )
    for task_id in registered:
        for agent, model in _COMBINATIONS:
            assert runs[task_id, model].agent == agent

    declared = tasks()
    assert {declared[task_id].category for task_id in registered} == {_CATEGORY}
    assert {declared[task_id].language for task_id in registered} == {"python"}
    assert {declared[task_id].surface for task_id in registered} == {"application"}
    assert all(declared[task_id].control for task_id in registered)
    # Every `test-authoring` task the corpus holds, which is what §68.1 claimed
    # the register was.
    assert set(registered) == {
        task.id for task in declared.values() if task.category == _CATEGORY
    }

    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(note_section("69. What the round measured"))
    assert "**Nine cells, and they are exactly the nine §68.1 registered.**" in measured
    assert "**9 of 9**" in measured
    assert (
        "**neither harness crosses a version boundary from round 7**"
    ) in measured
    assert "`claude-code` at **2.1.235**, which is round 7's exactly" in measured


def test_the_dry_cell_and_the_four_logs_are_what_the_record_says() -> None:
    """Section 69's invocation paragraph, against the checked-in logs.

    Three claims. The dry cell was one of the nine, run alone and paid for, and
    it resolved — the mutation gate's first paid verdict. Four invocations
    wrote four logs and none of them is empty, which is the round-7 failure
    mode this round did not have. And the departure from section 68.6, which
    called the dry cell the cheapest of the nine off an anchor where haiku sat
    just under Codex, is stated rather than passed over: in the event Codex was
    the cheapest column and the cheapest of the nine cells was a Codex one.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 9
    assert min(counted.values()) > 0, "no invocation of this round logged nothing"

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-20-r8-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    assert firstparty_v1.grade(tasks()[_DRY_CELL], alone[0].diff) is True

    # Each further invocation is one column's remainder, and no cell appears
    # in two logs.
    by_log = {
        name: {
            (run.task_id, run.agent, run.model)
            for run in firstparty_v1.load_runs(_LOGS / name)
        }
        for name in _REPLAYED
    }
    assert len(set().union(*by_log.values())) == 9
    assert sum(len(cells) for cells in by_log.values()) == 9

    # The registration called the chosen column the cheapest of the nine, off
    # round 7's anchor where haiku sat just under Codex. In the event Codex was
    # the cheapest column and the cheapest single cell was a Codex one, which
    # the record states rather than passes over.
    assert _ROUND_7_PER_CELL[_HAIKU] < _ROUND_7_PER_CELL[_TERRA], (
        "the anchor the registration read"
    )
    assert min(_PER_CELL, key=lambda model: _PER_CELL[model]) == _TERRA
    runs = round_8_runs()
    cheapest = min(runs.items(), key=lambda item: item[1].cost_usd)
    assert cheapest[0] == _UNRESOLVED
    assert round(cheapest[1].cost_usd, 4) == 0.0585
    assert round(runs[_DRY_CELL, _HAIKU].cost_usd, 4) == 0.1138
    assert cheapest[1].cost_usd < runs[_DRY_CELL, _HAIKU].cost_usd

    measured = prose(note_section("69. What the round measured"))
    assert "**Four invocations, four logs, none of them empty.**" in measured
    assert "the mutation gate's first paid verdict" in measured
    assert (
        "**The dry cell was registered as the cheapest of the nine and was "
        "not**"
    ) in measured
    assert "**Codex was the cheapest column**" in measured
    assert (
        "the cheapest of the nine cells was `playbill` on Codex at $0.0585 "
        "against the dry cell's $0.1138"
    ) in measured
    assert "**graded alone before the other eight**" in measured


def test_every_codex_row_discloses_a_table_derived_cost_and_its_table() -> None:
    """Section 70's cost-source disclosure, on the rows and in the schema.

    Three Codex rows say their dollars were computed rather than billed and
    name the price table version they were computed from, and six claude-code
    rows beside them say the opposite. The refusal is the second half — a codex
    row that says anything else is rejected at load, so the disclosure cannot
    be dropped by a later sweep.
    """
    runs = round_8_runs()
    codex = {key: run for key, run in runs.items() if run.agent == "codex"}
    claude = {
        key: run for key, run in runs.items() if run.agent == firstparty.CLAUDE_CODE
    }
    assert (len(codex), len(claude)) == (3, 6)

    assert {run.cost_source for run in codex.values()} == {"table-derived"}
    assert {run.price_table for run in codex.values()} == {_PRICE_TABLE}
    assert _PRICE_TABLE == pricing.load_price_table(
        _REPO / "data" / "price-table.json"
    ).version

    assert {run.cost_source for run in claude.values()} == {"vendor-reported"}
    assert {run.price_table for run in claude.values()} == {None}
    assert agents.ClaudeCodeAdapter.cost_source == "vendor-reported"
    assert agents.ClaudeCodeAdapter.price_table is None

    with pytest.raises(ValueError, match="table-derived"):
        firstparty_v1.Run(
            **(
                codex[_DRY_CELL, _TERRA].model_dump()
                | {"cost_source": "vendor-reported", "price_table": None}
            )
        )

    read = prose(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read


def test_the_round_cost_what_the_record_states_by_cost_source() -> None:
    """Section 70's spend, pinned per cost source and per cell.

    Each column's own total first, because one of the three is an estimate and
    two are bills. Then the two figures that do have a single meaning: what the
    account was billed, which is the two vendor-reported columns and nothing
    else, and the total in the form section 68.4 registered the bound in. Round
    7's record had to warn that adding the printed columns gives a different
    last digit; this round's do not, and that is asserted rather than assumed
    so the sentence saying so cannot rot.
    """
    runs = round_8_runs()
    ids = swept_tasks()

    for model, spend in _SPEND.items():
        actual = sum(runs[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 3, 4) == _PER_CELL[model], model

    billed = sum(
        run.cost_usd for run in runs.values() if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED

    total = sum(run.cost_usd for run in runs.values())
    assert round(total, 4) == _TOTAL

    # Summed before rounding, and this round the printed columns add to the
    # same last digit either way.
    assert round(sum(_SPEND.values()), 4) == _TOTAL
    assert round(_SPEND[_HAIKU] + _SPEND[_SONNET], 4) == _BILLED

    read = prose(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))
    assert "**What the account was actually billed: $2.4916" in read
    assert "**summed before rounding**" in read
    assert (
        "this round the printed columns happen to add to the same last digit"
    ) in read

    [printed] = fenced_blocks(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))[:1]
    assert printed == (
        "claude-code x haiku     $0.7237  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $1.7679  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $0.2698  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )


def test_the_registered_range_was_honoured_and_each_column_read_against_it(
) -> None:
    """Section 70's range paragraph: the bound that held and the envelope that
    did not.

    Section 68.4 registered $1.5-5 and, inside it, a caching-aware envelope of
    $1.39-$2.23 built by holding the two Claude columns at round-7-equal token
    counts. The range held; the envelope did not, and the overshoot is the
    Claude columns alone, which is checkable by adding them. The registered
    one-way miss was the low side and did not happen.
    """
    runs = round_8_runs()
    total = sum(run.cost_usd for run in runs.values())
    low, high = _REGISTERED_RANGE
    assert low <= total <= high, "the round landed inside the registered range"
    assert total > low, "the registered downside — a round under the floor — did not happen"

    envelope_low, envelope_high = _REGISTERED_ENVELOPE
    assert total > envelope_high, "the envelope was overshot at the top"

    for model, registered in _REGISTERED_COLUMN.items():
        assert round(3 * _ROUND_7_PER_CELL[model], 4) == registered, model
        assert _SPEND[model] > registered, model
    assert round(sum(_REGISTERED_COLUMN.values()), 4) == _REGISTERED_CLAUDE
    claude = sum(
        run.cost_usd for run in runs.values() if run.agent == firstparty.CLAUDE_CODE
    )
    assert round(claude, 4) == _BILLED
    assert round(claude / _REGISTERED_CLAUDE, 2) == _CLAUDE_DEARER
    # The overshoot is the Claude columns and nothing else: put the Codex
    # column back at either end of its registered band and the round still
    # clears the envelope's top.
    band_low, band_high = _REGISTERED_CODEX_BAND
    assert claude + band_low > envelope_high

    # The Codex column landed inside its band and below the expectation.
    assert band_low < _SPEND[_TERRA] < band_high
    assert _SPEND[_TERRA] < 0.34, "below the ~$0.34 expectation section 68.4 named"

    for model, dearer in _DEARER.items():
        assert round(_PER_CELL[model] / _ROUND_7_PER_CELL[model], 2) == dearer, model

    # The lesson §68.4 named and priced into one column only, in the rows: a
    # suite is a much larger write than a locate answer.
    for model, per_cell in _OUTPUT_PER_CELL.items():
        written = sum(
            run.tokens_out for key, run in runs.items() if key[1] == model
        )
        assert round(written / 3) == per_cell, model
        assert per_cell > 2 * _ROUND_7_OUTPUT_PER_CELL[model], model

    [quoted] = fenced_blocks(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))[1:2]
    for model, label in ((_HAIKU, "haiku"), (_SONNET, "sonnet"), (_TERRA, _TERRA)):
        line = next(
            text for text in quoted.splitlines()
            if text.startswith(f"claude-code x {label}")
            or text.startswith(f"codex x {label}")
        )
        assert f"${_SPEND[model]:.4f}" in line, model
        assert f"${_PER_CELL[model]:.4f}" in line, model
        assert f"${_ROUND_7_PER_CELL[model]:.4f}" in line, model

    read = prose(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))
    assert (
        "**The registered range was $1.5–5. The round came to $2.7614, and it "
        "was honoured.**"
    ) in read
    assert (
        "**The one way §68.4 registered this round missing was the low side, "
        "and it did not happen**"
    ) in read
    assert (
        "**The envelope was overshot at the top, and the overshoot is entirely "
        "the Claude columns.**"
    ) in read
    assert "**$1.39 all-cached to $2.23 all-uncached**" in read
    assert (
        f"**{_OUTPUT_PER_CELL[_HAIKU]:,}** output tokens a cell on haiku and "
        f"**{_OUTPUT_PER_CELL[_SONNET]:,}** on sonnet, against round 7's "
        f"**{_ROUND_7_OUTPUT_PER_CELL[_HAIKU]:,}** and "
        f"**{_ROUND_7_OUTPUT_PER_CELL[_SONNET]:,}**"
    ) in read


def test_the_codex_column_sits_between_the_bounds_its_rows_can_reproduce(
) -> None:
    """Section 70's last paragraph: the two bounds, and the rate between them.

    A table-derived figure is arithmetic a reader can redo, but only to within
    the caching split — which is not on the row. Both bounds are recomputed
    here from the round's own Codex tokens at the checked-in table, the logged
    figure has to sit between them, and the effective rate the round paid is
    compared with round 7's and round 6's on the same model and the same table.
    This round's is between the two, which is why the record writes it down as
    a second observation rather than as a correction of section 61's.
    """
    runs = round_8_runs()
    codex = [run for run in runs.values() if run.agent == "codex"]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == _CODEX_TOKENS

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")

    def bound(cached: bool) -> float:
        return pricing.cost_usd(
            table, _TERRA,
            input_plain_tokens=0 if cached else tokens_in,
            input_cached_tokens=tokens_in if cached else 0,
            input_cache_write_tokens=0,
            output_tokens=tokens_out,
        )

    assert round(bound(cached=True), 4) == _ALL_CACHED
    assert round(bound(cached=False), 4) == _ALL_UNCACHED
    spend = sum(run.cost_usd for run in codex)
    assert _ALL_CACHED < spend < _ALL_UNCACHED, (
        "the logged figure must sit between the bounds a row can reproduce"
    )

    prices = table.models[_TERRA]
    effective = (spend - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1_000_000, 4) == _EFFECTIVE_RATE
    assert prices.input_cached_per_token < effective < prices.input_uncached_per_token
    assert _ROUND_6_EFFECTIVE_RATE < _EFFECTIVE_RATE < _ROUND_7_EFFECTIVE_RATE, (
        "this round cached better than round 7 and worse than round 6"
    )

    read = prose(note_section(
        "70. Spend, by cost source, against the range registered before it"
    ))
    assert (
        f"read **{_CODEX_TOKENS[0]:,}** input tokens and wrote "
        f"**{_CODEX_TOKENS[1]:,}**"
    ) in read
    assert (
        f"against the {_CODEX_PROJECTED_TOKENS[0]:,} and "
        f"{_CODEX_PROJECTED_TOKENS[1]:,} §68.4 projected"
    ) in read
    assert "**$0.1697 all-cached** and **$0.8200 all-uncached**" in read
    assert (
        "**$0.4771/M**, against round 7's **$0.5714/M** and round 6's "
        "**$0.3996/M**"
    ) in read
    assert "as a second observation and not as a correction" in read


def test_the_limits_in_force_were_the_flat_default_in_section_46s_sense(
) -> None:
    """Section 69's limits paragraph, against the table the runner reads.

    The claim this round makes is section 46's distinction used on a whole
    round: `test-authoring` is in no `LIVE_RUN_LIMITS_S` row, so every cell ran
    **at the flat default** rather than **under a registered 600 s** — a claim
    only a registered category can make. The two numbers are equal, which is
    exactly why the distinction has to be stated rather than shown, and why no
    cross-round caveat arises from it.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) - _LATER_LIMITS == _REGISTERED_LIMITS
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S, (
        "the round registered no limit and this record says so"
    )

    declared = tasks()
    swept = set(swept_tasks())
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in declared.values()
        if task.id in swept
    } == {600} == {firstparty.RUN_TIMEOUT_S}

    latencies = [run.latency_s for run in round_8_runs().values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600
    longest = max(round_8_runs().items(), key=lambda item: item[1].latency_s)
    assert longest[0] == (_LONGEST_CELL, _HAIKU)

    measured = prose(note_section("69. What the round measured"))
    assert (
        "**The limits in force: the flat default of 600 seconds, every cell.**"
    ) in measured
    assert (
        "all nine cells ran **at the flat default** rather than under a "
        "registered 600 s"
    ) in measured
    assert "**no cross-round caveat arises**" in measured
    assert f"the round's longest run was **{_LONGEST_S} s**" in measured
    assert f"the mean was **{_MEAN_S} s**" in measured
    assert "the two gates run afterwards" in measured


def test_the_toolchain_is_recorded_as_provenance_and_not_as_a_field() -> None:
    """Section 69's toolchain paragraph, and the fields it refuses to add.

    One version this round, because one runner graded it: every cell is a
    Python task, so `node --test` graded nothing here. The refusal is the other
    half — no `runner`, no `toolchain` and no `gate` field exists on a
    run-log row or on a record, so the round that introduced a second verdict
    shape introduced no field to say which one graded a row.
    """
    from ai_benchmark.schema import Record

    assert platform.python_version() == _PYTHON_VERSION
    declared = tasks()
    assert {declared[task_id].language for task_id in swept_tasks()} == {"python"}

    for field in ("runner", "toolchain", "gate"):
        assert field not in firstparty_v1.Run.model_fields, field
        assert field not in Record.model_fields, field
    schema = json.loads((_REPO / "record.schema.json").read_text(encoding="utf-8"))
    assert not {"runner", "toolchain", "gate"} & set(schema["properties"])

    measured = prose(note_section("69. What the round measured"))
    assert (
        f"**The toolchain the sweep graded under: Python {_PYTHON_VERSION}, "
        "and no Node.**"
    ) in measured
    assert (
        "no `runner` field, no `toolchain` field and no `gate` field"
    ) in measured


def test_the_per_cell_table_is_what_the_logs_and_the_grading_say(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 71's table, rebuilt from the artifacts and compared byte for byte.

    Three tasks times three combinations is nine verdicts and nine costs, and
    the note quotes all of them. Rebuilding the block and comparing it whole is
    the only pin that cannot drift a cell at a time — and it carries the header
    rows, so the cost source printed on each column is pinned with the numbers
    under it rather than beside them.
    """
    quoted = fenced_blocks(
        note_section("71. The nine cells under three combinations")
    )[0]
    assert quoted == cell_table(verdicts)

    resolved = {
        model: sum(
            1 for (_, run_model), ok in verdicts.items() if run_model == model and ok
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 8
    assert [key for key, ok in verdicts.items() if not ok] == [_UNRESOLVED]

    measured = prose(note_section("69. What the round measured"))
    assert "**Resolution: 8 of 9.**" in measured
    assert (
        "**3 of 3** on `claude-haiku-4-5`, **3 of 3** on `claude-sonnet-5`, "
        "**2 of 3** on `codex` × `gpt-5.6-terra`"
    ) in measured

    said = prose(note_section("71. The nine cells under three combinations"))
    assert "There is no per-category block beside it" in said
    assert "no rate is quoted off it" in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath() -> None:
    """Section 71's turn line, and the definition that makes it uncomparable.

    A Codex turn is a completed non-reasoning item; a claude-code turn is
    `num_turns`. The three totals are pinned so that section 74's refusal has
    something to refuse, and the Codex definition is pinned at its source so
    that the refusal's reason is not just an assertion in prose.
    """
    runs = round_8_runs()
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in runs.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(note_section("71. The nine cells under three combinations"))
    assert (
        "Haiku took **57** turns over the three (12–31), sonnet **55** "
        "(15–22), Codex **24** (5–10)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_each_cell_names_the_gate_it_cleared_and_the_one_it_did_not(
    gates: dict[tuple[str, str], Gates],
) -> None:
    """Section 72's table: the round's one new reading, re-derived.

    The block is rebuilt from the two gates run apart and compared whole, which
    is the only way a record can say *which* gate a cell failed — the shipped
    verdict is one bool. Three claims come with it: gate 1 was passed by all
    nine, the one unresolved cell failed gate 2, and the mutant it let live is
    the one the record names.
    """
    quoted = fenced_blocks(
        note_section("72. Which gate, and what the collection rule archived")
    )[0]
    assert quoted == gate_table(gates)

    assert all(derived.gate_1 for derived in gates.values()), (
        "no suite of this round accused correct code of a fault"
    )
    failed = {key for key, derived in gates.items() if derived.survivors}
    assert failed == {_UNRESOLVED}
    assert gates[_UNRESOLVED].survivors == [_SURVIVOR]

    # The mutant the record names is a real one of that task, and it is the
    # boundary the record describes: the `+ 1` that pays for the space.
    task = tasks()[_UNRESOLVED[0]]
    planted = [patch.name for patch in firstparty_v1.mutant_patches(task)]
    assert _SURVIVOR in planted
    patch = next(
        path for path in firstparty_v1.mutant_patches(task) if path.name == _SURVIVOR
    )
    body = patch.read_text(encoding="utf-8")
    assert "-        elif len(line) + 1 + len(word) <= measure:" in body
    assert "+        elif len(line) + len(word) <= measure:" in body

    said = prose(note_section(
        "72. Which gate, and what the collection rule archived"
    ))
    assert "**Gate 1 was passed by all nine.**" in said
    assert (
        "**The one unresolved cell failed gate 2, at a named mutant.**"
    ) in said
    assert "`02-set-a-line-without-counting-the-space-between-words`" in said
    assert "**That is the whole of the reading.**" in said


def test_no_kill_rate_is_quoted_anywhere_in_the_rounds_record(
    gates: dict[tuple[str, str], Gates],
) -> None:
    """Section 68.7's registered refusal, honoured in the record's own prose.

    "No fraction over mutants is computed anywhere" is the kind of claim a
    record breaks by accident, in a sentence written to be helpful — five of
    six killed, a 92% kill rate, four-fifths of a suite. So the record's seven
    sections are read for the shapes that would say it: a percentage, an
    `n/m` over a mutant count, and the English of a fraction. What the record
    is allowed to say is the universal quantifier and the survivor's name, and
    those are checked to be there in section 72.
    """
    # The kill counts exist and are deliberately not published: this is the
    # arithmetic the record refuses to do, done here to prove it could have
    # been done.
    killable = {
        key: len(firstparty_v1.mutant_patches(tasks()[key[0]]))
        - len(derived.survivors)
        for key, derived in gates.items()
    }
    assert killable[_UNRESOLVED] == 4, "four of playbill's five, and not a score"

    fraction = re.compile(r"\d+\s*(?:%|/\s*\d+\s+mutant|of (?:five|six) mutant)")
    for heading in record_sections():
        text = note_section(heading)
        assert not fraction.search(text), heading
        assert "kill rate" not in text or "not a score" in text
        assert "4 of 5" not in text and "5 of 6" not in text, heading

    said = prose(note_section("74. What this round cannot say"))
    assert "**No kill-rate reading of any kind.**" in said
    assert "No fraction over mutants is computed anywhere in this record" in said
    assert "it is not four-fifths of a result" in said


def test_the_collection_rule_archived_a_config_file_and_no_cell_edited_source(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 72's collection disclosure, over all nine diffs.

    Section 67.4 rules that grading collects the prompt-named test subtree and
    archives everything else. One diff of this round exercises it — a
    `pytest.ini` written at the workdir root, outside `tests/`, on a cell that
    resolved anyway — and eight touch nothing outside the subtree at all. The
    other half of the disclosure is what did *not* happen: no diff edits the
    module under test, so the hole the rule closes was never approached, and
    the record says that rather than claiming the rule was proved.
    """
    declared = tasks()
    outside: dict[tuple[str, str], list[str]] = {}
    for key, run in round_8_runs().items():
        test_path = declared[key[0]].test_path
        assert test_path == "tests"
        touched = re.findall(r"^diff --git a/(\S+) b/", run.diff, re.MULTILINE)
        assert touched, key
        outside[key] = [
            path for path in touched if not path.startswith(f"{test_path}/")
        ]
        assert not [
            path for path in touched if Path(path).name in _MODULES_UNDER_TEST
        ], f"{key} edited the module under test"

    archived = {key: paths for key, paths in outside.items() if paths}
    assert archived == {_ARCHIVED[0]: [_ARCHIVED[1]]}
    assert verdicts[_ARCHIVED[0]] is True, (
        "the cell resolved without the file that was archived"
    )
    # And the archived file really is the kind the grader refuses to read
    # `addopts` from — the config it runs under is pinned outside the workdir
    # and sets `addopts` to nothing — which is why it is worth the paragraph.
    from ai_benchmark import language_runners

    assert language_runners._GRADING_CONFIG == "[pytest]\naddopts =\n"
    assert _ARCHIVED[1] in (language_runners.PythonRunner.run_tests.__doc__ or "")

    said = prose(note_section(
        "72. Which gate, and what the collection rule archived"
    ))
    assert "**What the collection rule archived, on a real diff.**" in said
    assert "**archived, not scored**" in said
    assert "**No cell of the round edited the module under test**" in said
    assert "unexercised in that direction rather than proved in it" in said


def test_the_coverage_table_is_recorded_as_the_lint_prints_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 73's table, taken from the lint rather than from a task count.

    Acceptance is a figure the lint prints — `test-authoring application python
    3` — so the block the record quotes is compared with the printed table line
    for line. The TypeScript zero is read as section 64 registered the shape:
    zero by absence, which is all the table can express, and no per-language
    zero row exists for it because the lint was not changed to print one.

    Three lines of the block have moved since, each by a later round
    authoring tasks: round 10 authored its three `investigation` tasks and
    round 11 its three `requirement-decomposition` ones, so the rows this
    record quotes as `- - 0` now print the Python cells those tasks fill, and
    round 12's three explain-style tasks grew `codebase-comprehension`'s row
    from 4 to 7. The record is not edited for any of them — the page it
    quotes is what the page was — so the lines are named below, round 7's own
    pattern, and every other one is still held byte for byte.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))

    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python == _PYTHON_COVERAGE
    assert sum(python.values()) == _PYTHON_TASKS
    assert python[_CATEGORY] == 3, "the round's acceptance figure"

    typescript = {
        category: count
        for category, surface, language, count in coverage
        if language == "typescript" and surface == "application"
    }
    assert typescript == _TYPESCRIPT_COVERAGE
    assert _CATEGORY not in typescript

    # The zero is by absence: no row at all, and no `- - 0` row either, because
    # the category now has tasks in one language.
    assert not [
        row for row in coverage if row[0] == _CATEGORY and row[2] == "typescript"
    ]
    assert not [row for row in coverage if row[0] == _CATEGORY and row[3] == 0]
    # Round 13's first `performance-optimisation` task filled the last
    # authorable zero row, and there is no authorable successor category to
    # read the shape off: the one `- - 0` row left is `unclassified`'s, which
    # survives by construction — the loader refuses any task declaring it
    # (the plan-review ruling of 2026-08-29).
    assert ("unclassified", "-", "-", 0) in coverage, (
        "the shape a real zero prints, off the one structural row left"
    )
    assert not [row for row in coverage if row[3] == 0 and row[2] == "typescript"]

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed

    [quoted] = fenced_blocks(
        note_section("73. The coverage table, as the lint prints it")
    )
    recorded_zeros = {
        "investigation":
            "  investigation              -            -           0",
        "requirement-decomposition":
            "  requirement-decomposition  -            -           0",
        # Round 13's ticket 04 filled the last authorable zero row with the
        # category's first task; the record's quoted line stays what the page
        # was, and the printed table now carries the Python cell instead.
        "performance-optimisation":
            "  performance-optimisation   -            -           0",
    }
    # The row round 12's three explain-style tasks grew, no zero when this
    # was recorded: it read the four locate-style tasks and now reads seven.
    recorded_moved = {
        "codebase-comprehension":
            "  codebase-comprehension     application  python      4",
    }
    stale = recorded_zeros | recorded_moved
    quoted_lines = quoted.strip("\n").splitlines()
    for stale_line in stale.values():
        assert stale_line in quoted_lines
        assert stale_line not in printed
    for line in quoted_lines:
        if line in stale.values():
            continue
        assert line in printed, "the record quotes a line the lint does not print"
    for category in stale:
        assert [
            line.split()
            for line in printed.splitlines()
            if line.startswith(f"  {category}")
        ] == [
            [category, "application", "python", str(_PYTHON_COVERAGE[category])]
        ]

    said = prose(note_section("73. The coverage table, as the lint prints it"))
    assert (
        f"**`{_CATEGORY} application python 3` is the round's acceptance "
        "figure**"
    ) in said
    assert (
        "**Why `test-authoring × typescript` reads zero, in §64's own wording: "
        "it is zero by absence, which is all the table can express.**"
    ) in said
    assert (
        "plus a `(category, \"-\", \"-\", 0)` row for a category with no task "
        "in **any** language"
    ) in said
    assert "**The lint was not changed**" in said
    assert (
        "**This prose is where round 8's TypeScript zero is disclosed.**"
    ) in said
    assert "**mechanical follow-on for a later round**" in said


def test_what_the_round_cannot_say_is_stated_and_is_true_of_the_rows(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 74's six refusals, each checked against something.

    Prose is where a record over-claims, so each refusal is anchored: no
    TypeScript reading because no row of the round is a TypeScript row, no kill
    rate because the verdict is binary, no cross-action comparison because the
    gates differ, no Codex rung because there is one Codex model, no
    cross-harness turn comparison because a turn is counted differently on each
    side, and no multiplier because every task is a control.
    """
    declared = tasks()
    swept = set(swept_tasks())

    assert {declared[task_id].language for task_id in swept} == {"python"}
    assert all(declared[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if declared[task_id].construction is not None
    ]

    # One Codex model is not a ladder, and the ladder — which the rung floor
    # section 75 quotes is read off — is claude-code's.
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS
    # The refusal doing visible work: the Codex miss is on a task both ladder
    # models resolved, so the rung floor cannot see it.
    assert not verdicts[_UNRESOLVED]
    assert verdicts[_UNRESOLVED[0], _HAIKU] and verdicts[_UNRESOLVED[0], _SONNET]

    said = prose(note_section("74. What this round cannot say"))
    assert "**Nothing about `test-authoring` × `typescript`.**" in said
    assert "**No kill-rate reading of any kind.**" in said
    assert "**No cross-action difficulty comparison.**" in said
    assert "**No Codex rung.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No multiplier.**" in said
    assert "8 of 9 here is not to be read against round 7's 40 of 42" in said


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 75's verification, run rather than remembered.

    Each of the four logs is replayed into a scratch dataset of its own, and
    all four into one merged dataset. The four per-log datasets together have
    to be the merged one record for record: no row missing, none duplicated, no
    field differing. Every record also has to carry its log row's own
    measurements, because replay re-grades the diff and never re-runs the
    agent — which for a Codex row is the whole of the claim that a
    table-derived cost is not recomputed on the way through.
    """
    per_log: list[dict[str, object]] = []
    merged_path = tmp_path / "merged.jsonl"
    for name, (evaluated, resolved) in _REPLAYED.items():
        log = _LOGS / name
        alone = tmp_path / name
        for data in (alone, merged_path):
            main(["eval-v1", "--tasks", str(_TASKS), "--replay", str(log),
                  "--data", str(data)])
        printed = capsys.readouterr().out
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed
        per_log.extend(
            json.loads(line)
            for line in alone.read_text().splitlines()
            if line.strip()
        )

    merged = [
        json.loads(line)
        for line in merged_path.read_text().splitlines()
        if line.strip()
    ]
    assert len(merged) == 9

    def cell(record: dict[str, object]) -> tuple[str, str]:
        return str(record["instance_id"]), str(record["model"])

    assert sorted(per_log, key=cell) == sorted(merged, key=cell)

    runs = round_8_runs()
    for record in merged:
        run = runs[str(record["instance_id"]), str(record["model"])]
        assert record["agent"] == run.agent
        assert record["cost_usd"] == run.cost_usd
        assert record["turns"] == run.turns
        assert record["tokens_in"] == run.tokens_in
        assert record["tokens_out"] == run.tokens_out
        assert record["latency_s"] == run.latency_s
        assert record["agent_version"] == run.agent_version
        assert record["as_of"] == run.as_of.isoformat()
        assert record["benchmark"] == "first-party-v1"
        assert record["language"] == "python"
        assert record["category"] == _CATEGORY
    assert sum(float(record["quality_value"]) for record in merged) == 8

    # The commands the note prints, against the four logs they name. The
    # `over N tasks` count is derived, not pinned: `eval-v1 --replay` has no
    # language selection and prints today's corpus, so a later round authoring
    # a task moves this block and the pin has to move with it.
    printed_block = fenced_blocks(note_section(
        "75. Replay, the readers, and heap 1 closed"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed_block

    said = prose(note_section("75. Replay, the readers, and heap 1 closed"))
    assert "**Every round-8 log replays to the verdicts this record quotes.**" in said
    assert "9 rows and 8 resolved" in said


def test_both_readers_count_the_round_and_print_what_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 75's second claim: the first round since 5 inside the default view.

    Round 7's rows were read and dropped, because the default language
    selection is Python. Round 8's claude-code rows are Python, so both readers
    pick them up with no flag — six of the nine, since the agent selection is a
    separate one and drops the Codex column. What that moves is checked at the
    seam and then in what the readers print: reconcile's run count and round
    list, and the `test-authoring` table calibrate gains, whose only row is the
    controls divided by themselves.
    """
    everything = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    ]
    # `_ALL_ROWS` was every row in the directory when §75 was recorded;
    # round 10's sweep landed nine more on 2026-08-24, round 11's nine on
    # 2026-08-26, round 12's nine on 2026-08-28 and round 13's nine on
    # 2026-08-29, the only rows since.
    assert len(everything) == (
        _ALL_ROWS + _ROUND_10_ROWS + _ROUND_11_ROWS + _ROUND_12_ROWS
        + _ROUND_13_ROWS
    )
    assert len([run for run in everything if run.sweep == _SWEEP]) == _ROUND_8_ROWS
    selected = reconcile_v1.select_agent(
        everything, firstparty.CLAUDE_CODE, explicit=False
    )
    declared = list(firstparty_v1.load_task_set(_TASKS))
    selected = reconcile_v1.select_language(
        declared, selected, reconcile_v1.DEFAULT_LANGUAGE, explicit=False
    )
    # Round 10's, round 11's, round 12's and round 13's six claude-code
    # Python rows each
    # now survive both selections exactly as this round's six do; §75's own
    # figure stays unretyped.
    assert len(selected) == (
        _CLAUDE_CODE_PYTHON_RUNS + _ROUND_10_CLAUDE_CODE_ROWS
        + _ROUND_11_CLAUDE_CODE_ROWS + _ROUND_12_CLAUDE_CODE_ROWS
        + _ROUND_13_CLAUDE_CODE_ROWS
    )
    assert len([run for run in selected if run.sweep == _SWEEP]) == (
        _CLAUDE_CODE_ROUND_8_ROWS
    )
    assert reconcile_v1.DEFAULT_LANGUAGE == "python"

    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    assert (
        f"  task set   {_TASKS} — {_PYTHON_TASKS} task(s): "
        f"{_PYTHON_CONTROLS} control(s), {_PYTHON_CONSTRUCTED} constructed"
    ) in reconciled
    assert (
        f"  runs       "
        f"{_CLAUDE_CODE_PYTHON_RUNS + _ROUND_10_CLAUDE_CODE_ROWS + _ROUND_11_CLAUDE_CODE_ROWS + _ROUND_12_CLAUDE_CODE_ROWS + _ROUND_13_CLAUDE_CODE_ROWS}"
        f" over "
        f"{_PYTHON_TASKS_WITH_RUNS + _ROUND_10_TASKS + _ROUND_11_TASKS + _ROUND_12_TASKS + _ROUND_13_TASKS} "
        "task(s)"
    ) in reconciled
    # `sweep round-10` joined the round list when its sweep landed, the
    # second round after 5 the default reading counts, and `sweep round-11`,
    # `sweep round-12` and `sweep round-13` followed it as the third, fourth
    # and fifth.
    assert (
        "  rounds     11 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10, sweep round-11, sweep round-12, "
        "sweep round-13"
    ) in reconciled
    assert "             9 keyed on a sweep id, 2 on an as-of date" in reconciled
    # The round declared no contrast, so it reaches the report as a label and
    # nothing else, and the prediction reconciliation is where it was.
    assert reconciled.count(f"sweep {_SWEEP}") == 1
    assert _CATEGORY not in reconciled
    assert (
        f"   {_CONSTRUCTED_TASKS} constructed task(s): {_CONSTRUCTED_TASKS} "
        "swept, 0 unswept"
    ) in reconciled

    [quoted] = fenced_blocks(note_section(
        "75. Replay, the readers, and heap 1 closed"
    ))[1:2]
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    # When §75 was recorded, one line of the block had moved and only one:
    # round 10's three authored `investigation` tasks had grown the task-set
    # line. Round 10's sweep (2026-08-24) has since moved the rest — six
    # claude-code Python rows survive both selections, so the runs line, the
    # round list and its keyed count grew too — and round 11's first
    # `requirement-decomposition` task then grew the task-set line again, as
    # round 12's three explain-style `codebase-comprehension` tasks did
    # after it. The
    # record is not edited for any of that: every line it quoted is rebuilt
    # here from the live figures minus the later rounds', required to be
    # exactly what the note says, and what the reader prints instead was
    # asserted above off the same counts plus theirs.
    recorded = [
        "  task set   tasks/first-party-v1 — "
        f"{_PYTHON_TASKS - _ROUND_10_TASKS - _ROUND_11_TASKS - _ROUND_12_TASKS - _ROUND_13_TASKS} "
        f"task(s): "
        f"{_PYTHON_CONTROLS - _ROUND_10_TASKS - _ROUND_11_TASKS - _ROUND_12_TASKS - _ROUND_13_TASKS} "
        f"control(s), "
        f"{_PYTHON_CONSTRUCTED} constructed",
        f"  runs       {_CLAUDE_CODE_PYTHON_RUNS} over "
        f"{_PYTHON_TASKS_WITH_RUNS} task(s)",
        "  rounds     7 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8",
        "             5 keyed on a sweep id, 2 on an as-of date",
    ]
    assert quoted.strip("\n").splitlines() == recorded, (
        "the record no longer quotes the lines its own figures rebuild"
    )
    for line in recorded:
        assert line not in printed, line

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    [table] = fenced_blocks(note_section(
        "75. Replay, the readers, and heap 1 closed"
    ))[2:3]
    assert table.strip("\n") in calibrated, (
        "the calibration table the record quotes is not what the reader prints"
    )
    assert f"category {_CATEGORY}" in calibrated
    # One row, and it is the denominator: the controls divided by themselves.
    assert "   (zero-knob)  3      1.00x (n=3)       1.00x (n=3)" in calibrated

    said = prose(note_section("75. Replay, the readers, and heap 1 closed"))
    assert "**And this time the readers count the round.**" in said
    assert "**Six claude-code rows, not nine**" in said
    assert "**The prediction reconciliation is unmoved**" in said
    assert "One row, and it is the controls divided by themselves." in said


def test_heap_one_closes_and_the_archive_round_nine_waits_on_has_grown() -> None:
    """Section 75's last two paragraphs: the heap, and what round 9 meets.

    `test-authoring` was the capability matrix's only registered zero and the
    last heap-1 action with no tasks in any language. Both halves are checked
    against the corpus rather than asserted: the four heap-1 actions all have
    tasks now, and the categories still printing a zero row are heap 3's and
    heap 4's. The other half is the argument section 67.1 deferred the heap-3
    grader on — that waiting pays it — and the archive it waits on is counted
    here, at every log rather than at this round's.
    """
    declared = list(firstparty_v1.load_task_set(_TASKS))
    coverage = firstparty_v1.coverage_table(declared)
    populated = {row[0] for row in coverage if row[3] > 0}
    heap_1 = {"bug-fix", "feature-dev", "refactor", "test-authoring"}
    heap_2 = {"fault-location", "code-review", "codebase-comprehension"}
    assert heap_1 <= populated and heap_2 <= populated
    empty = {row[0] for row in coverage if row[3] == 0}
    # `investigation` printed in this set when the round was recorded and left
    # it when round 10 authored heap 3's first task; `requirement-decomposition`
    # left it when round 11 authored heap 3's second action's first;
    # `performance-optimisation` left it when round 13's ticket 04 authored
    # heap 4's first. That was the last authorable zero row, so what remains
    # is `unclassified`'s alone — permanent and structural, because the
    # loader refuses any task declaring it (the plan-review ruling of
    # 2026-08-29). The heap-1/heap-2 claim this test records is untouched.
    assert empty == {"unclassified"}
    assert not empty & (heap_1 | heap_2)

    # The ground truth behind the new cell is planted and machine-checked:
    # every one of the three ships mutants and a proof subtree, and the lint
    # has run them (this suite's acceptance command runs the lint).
    for task in declared:
        if task.category != _CATEGORY:
            continue
        assert firstparty_v1.is_mutation_keyed(task)
        assert len(firstparty_v1.mutant_patches(task)) >= 3
        assert firstparty_v1.EXISTENCE_PROOFS[_CATEGORY]

    archive = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    ]
    # The archive has grown again since §75 counted it — round 10's sweep
    # landed nine more answers on 2026-08-24, round 11's nine more on
    # 2026-08-26, round 12's nine more on 2026-08-28 and round 13's nine
    # more on 2026-08-29 — so §75's own count
    # is re-derived over the rows that
    # existed then, scoped by sweep id and never by a log filename; the
    # section's figures stay unretyped.
    assert len([
        run for run in archive
        if run.output
        and run.sweep not in {"round-10", "round-11", "round-12", "round-13"}
    ]) == _ARCHIVE_NOW
    assert _ARCHIVE_NOW == _ARCHIVE_BEFORE + _ROUND_8_ROWS

    said = prose(note_section("75. Replay, the readers, and heap 1 closed"))
    assert "**Heap 1 closes.**" in said
    assert (
        "the last heap-1 action with no tasks in any language"
    ) in said
    assert "**planted and machine-checked**" in said
    assert "**What round 9 meets.**" in said
    assert (
        f"**{_ARCHIVE_BEFORE} answers across eight sweeps** §67.1 counted to "
        f"**{_ARCHIVE_NOW} across nine**"
    ) in said


def test_the_record_takes_the_next_free_numbers_and_renumbers_nothing() -> None:
    """Sections 69-75 are the next free numbers, and 68 is still spent once.

    The note numbers its sections once and never renumbers them, so a record
    taking a number already spent is a citation collision every later reference
    inherits. Section 68 said the record would open at 69; this checks that it
    did and that the seven are contiguous.

    It used to check a third thing — that nothing above 75 existed — which was
    true until round 9 opened at 76 (its rulings) and 77 (its registration).
    That clause was the record's own frontier claim and it has been spent; what
    survives it is the claim that outlasts the frontier, that the record's seven
    are still exactly 69-75 and that every later section took a number above
    them rather than one of theirs.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(68) == 1
    assert [number for number in numbered if 68 < number < 76] == list(range(69, 76))
    assert all(numbered.count(number) == 1 for number in range(69, 76))

    for heading in record_sections():
        assert f"### {heading}\n" in text, heading

    opening = prose(note_part("Round 8 verdicts — 2026-08-20").split("\n### ")[0])
    assert "**§69 is the next free number.**" in opening
    assert "this record opens at **69** and runs to **75**" in opening
    assert "Nothing above it is renumbered." in opening
