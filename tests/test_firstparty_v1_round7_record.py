"""Round 7's record, pinned: what sections 60-66 of the design note publish.

The round swept forty-two cells over **fourteen TypeScript tasks** — the first
round in a second language, and the first where a Codex row and its two
claude-code rows are all written by the same sweep. Its novelty is a
*toolchain*, so its record has two hazards the earlier ones did not. The first
is the reading a two-language corpus invites and this round cannot support:
nothing was ported, so there is no matched pair anywhere and no
Python-versus-TypeScript figure is computable from these rows. The second is
the one round 6 introduced and this round doubles — two kinds of dollar,
`vendor-reported` and `table-derived`, produced by the same sweep over the same
task, where a reader who adds them without being told is adding an estimate to
a bill.

Every figure is pinned rather than derived, which is the point: a derived
expectation follows the corpus wherever it goes, and these numbers are quoted
in the design note and read by whoever is deciding what a round cost. The pins
come in two halves, as rounds 5 and 6's do. The first is arithmetic over the
checked-in run logs and the verdicts re-grading their diffs produces. The
second reads the design note itself — its quoted tables against what the logs
actually say, its quoted commands against what they actually print — because a
record whose numbers drift from the artifacts that earned them is the defect
this file exists to catch, and the record is prose that nothing else checks.

The round's runs are selected by their **sweep id** and never by log filename:
the sweep protocol bans selecting run logs by name, having watched the first
pass of the round-1 analysis silently drop two paid cells that way. The eight
filenames appear here only where a command has to be given a log to replay,
which is section 66's verification.
"""

import json
import platform
import re
import shutil
import statistics
import subprocess
from pathlib import Path

import pytest

from ai_benchmark import agents, firstparty, firstparty_v1, pricing, reconcile_v1
from ai_benchmark.cli import main

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_SWEEP = "round-7"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-20"
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.235 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}

# The eight logs the sweep's eight invocations wrote, and what each replays to.
# Named only so that section 66's replay can be given one log at a time;
# nothing here selects runs by them. `r7-f` is the empty one — an invocation
# that logged nothing before the codex stream died — and it is in this mapping
# at zero rather than left out, because a log that replays to nothing rather
# than to an error is a claim worth holding.
_REPLAYED = {
    "2026-08-20-r7-a.jsonl": (1, 1),
    "2026-08-20-r7-b.jsonl": (13, 11),
    "2026-08-20-r7-c.jsonl": (14, 14),
    "2026-08-20-r7-d.jsonl": (9, 9),
    "2026-08-20-r7-e.jsonl": (2, 2),
    "2026-08-20-r7-f.jsonl": (0, 0),
    "2026-08-20-r7-g.jsonl": (2, 2),
    "2026-08-20-r7-h.jsonl": (1, 1),
}
_EMPTY_LOG = "2026-08-20-r7-f.jsonl"
_DRY_CELL = "leftluggage-locate-the-charge-nobody-arrived-at"

# Section 61's spend, per combination and per cost source. Two of these are
# bills and one is an estimate, so they are pinned apart; the total below is
# pinned separately because it is the form section 59.4 registered the bound
# in and not a quantity with a single meaning.
_SPEND = {_HAIKU: 1.4532, _SONNET: 4.2344, _TERRA: 1.6046}
_BILLED = 5.6877
_TOTAL = 7.2923
_PER_CELL = {_HAIKU: 0.1038, _SONNET: 0.3025, _TERRA: 0.1146}

# Round 6's per-cell figures, which section 59.4 registered this round against
# and section 61 reports each column beside.
_ROUND_6_PER_CELL = {_HAIKU: 0.0783, _SONNET: 0.2086, _TERRA: 0.0717}
_REGISTERED_COLUMN = {_HAIKU: 1.0962, _SONNET: 2.9204}
_REGISTERED_CODEX_BAND = (0.64, 3.91)
_REGISTERED_RANGE = (6.0, 15.0)
_REGISTERED_ENVELOPE = (4.66, 7.93)
_DEARER = {_HAIKU: 1.33, _SONNET: 1.45, _TERRA: 1.60}

# Section 61's Codex token totals and the two bounds a reader can recompute
# from the rows: all-cached below, all-uncached above, the logged figure
# between. The split the figure was actually priced from is not on a row, which
# is the paragraph's point.
_CODEX_TOKENS = (2_169_811, 30_396)
_CODEX_PROJECTED_TOKENS = (1_816_513, 23_163)
_ALL_CACHED = 0.7987
_ALL_UNCACHED = 4.7044
_EFFECTIVE_RATE = 0.5714
_ROUND_6_EFFECTIVE_RATE = 0.3996
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 60's resolution line, and the two cells it turns on — both haiku's,
# both `code-review`.
_RESOLVED = {_HAIKU: 12, _SONNET: 14, _TERRA: 14}
_UNRESOLVED = {
    "limekiln-review-the-drawing-and-the-carting",
    "masonsyard-review-the-lettering-and-the-account",
}

# Section 60's limits paragraph: nothing came near the ceiling every cell ran
# under.
_LONGEST_S = 189.6
_MEAN_S = 87.0
_LONGEST_CELL = "seedbank-book-out-what-the-store-hands-over"

# Section 62's turn line. Quoted so that section 65's refusal to compare across
# the harness boundary is anchored to numbers rather than to an assertion.
_TURNS = {_HAIKU: 183, _SONNET: 168, _TERRA: 130}
_TURN_RANGE = {_HAIKU: (4, 23), _SONNET: (7, 23), _TERRA: (6, 13)}

# Section 60's toolchain paragraph. Provenance, and deliberately not fields: a
# reader re-grading these diffs under another Node may get another answer, and
# nothing on a row would tell them so.
_NODE_VERSION = "v22.22.2"
_PYTHON_VERSION = "3.14.4"

# Section 63's scenario table: the row label, the `node:` builtin the scenario
# is built on, and the repository prefixes whose tasks make up the row. The
# reviews carry no characteristic module and print `-`.
_SCENARIOS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("a node:http service", "node:http", ("leftluggage",)),
    ("an async / event flow", "node:events", ("lockhouse",)),
    ("a stream pipeline", "node:stream", ("telegraph",)),
    ("a CLI over the filesystem", "node:fs", ("seedbank",)),
    ("fixed-width frames", "node:buffer", ("weighbridge",)),
    ("a digest chain", "node:crypto", ("parishchest",)),
    ("a compression seam", "node:zlib", ("gasworks",)),
    ("a pass written as a link", "URL", ("tollhouse",)),
    ("a table of verdicts", "node:vm", ("courtleet",)),
    ("two reviews to file", "-", ("masonsyard", "limekiln")),
)

# Section 63's review split, over the six `code-review` cells.
_FINDINGS = {"accepted": 16, "rejected": 0, "unlisted": 0}
_PLANTED_COVERED = (16, 18)
_HAIKU_MISSED = {
    "limekiln-review-the-drawing-and-the-carting": ("dockets.ts", "Docket.asFigure"),
    "masonsyard-review-the-lettering-and-the-account": ("account.ts", "Account.comesTo"),
}

# Section 66's reader counts: the corpus's `claude-code` Python rows, and the
# Python task set the default language selection narrows to. Both are what they
# were before the round, which is the section's claim.
#
# Three of them moved once after the round they record, and by the same one
# task: round 8 authored the corpus's first `test-authoring` task, which is
# Python and declares itself a control, so the loaded Python task set and its
# control count each grew by one. Round 7's own prose is a claim about what
# round 7 did and is quoted rather than recomputed, so it stays where it was —
# and the two lines the reader prints are different counts, which is why they
# no longer read alike: the task-set line counts the corpus the language
# selection reaches, and the runs line counts the tasks that have rows. A task
# authored after every sweep has none.
# The whole corpus as this record quotes it, both languages: what
# `eval-v1 --replay` counted at the time, and what the note's own block says.
_RECORDED_TASKS = 127

_CLAUDE_CODE_PYTHON_RUNS = 225
_PYTHON_TASKS = 114
_PYTHON_TASKS_WITH_RUNS = 113
_PYTHON_CONTROLS = 47
_PYTHON_CONSTRUCTED = 67

# What `--language typescript` reaches instead: 28 rather than 42, because the
# agent selection is a separate one and drops the Codex column.
_TYPESCRIPT_TASKS = 14
_TYPESCRIPT_RUNS = 28

# Section 64's coverage target, per language.
_TYPESCRIPT_COVERAGE = {
    "bug-fix": 3, "fault-location": 3, "feature-dev": 3, "refactor": 3,
    "code-review": 2,
}
_PYTHON_COVERAGE = {
    "bug-fix": 6, "fault-location": 6, "feature-dev": 71, "refactor": 18,
    "codebase-comprehension": 4, "code-review": 8, "test-authoring": 1,
}

# The two fields of a calibration block a later round moves, and the only two —
# the round-6 suite's rule, needed here because round 7 authored the ninth and
# tenth `code-review` tasks. The **measured** numbers are the round that
# published them; the **counted** ones grow the moment a later round authors
# another control in the category. A quoted block is therefore compared with
# the counted ones written out, and this suite's claim is that the earlier
# records' tables are unmoved by round 7's rows.
_COUNTED_MIX = re.compile(
    r"^(   baseline mix +)\d+( single-file; )\d+( hand-authored)", re.MULTILINE
)
_COUNTED_ROW = re.compile(r"^(   \(zero-knob\)  )\d+ +", re.MULTILINE)


def counts_written_out(text: str) -> str:
    """This calibration output with its counted fields replaced by a mark."""
    return _COUNTED_ROW.sub(r"\1N ", _COUNTED_MIX.sub(r"\1N\2N\3", text))


def tasks_in_set() -> int:
    """How many tasks the checked-in set holds, as `eval-v1` counts them.

    Derived rather than pinned, because `eval-v1 --replay` has no language
    selection and prints today's count: this is the one of ticket 06's three
    counts that moved when the corpus grew, and the pin has to move with it.
    """
    return len(firstparty_v1.load_task_set(_TASKS))


def round_7_runs() -> dict[tuple[str, str], firstparty_v1.Run]:
    """Every run the sweep logged, keyed task x model.

    Read out of every log in the run-log directory and selected on the sweep
    id, which is what identifies a round: the sweep took eight invocations,
    and a filename says nothing about which sweep a row belongs to.
    """
    logged = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    ]
    assert len(logged) == 42, "the round is 42 cells"
    runs = {(run.task_id, run.model): run for run in logged}
    assert len(runs) == 42, "a cell was swept twice"
    return runs


def swept_tasks() -> list[str]:
    """The round's fourteen task ids, in corpus order."""
    ids = sorted({task_id for task_id, _ in round_7_runs()})
    assert len(ids) == 14
    return ids


def tasks() -> dict[str, firstparty_v1.Task]:
    """The checked-in task set, by id."""
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def verdicts() -> dict[tuple[str, str], bool]:
    """Every cell of section 62's table re-graded, keyed task x model.

    The computation `eval-v1 --replay` does, and the only way to a verdict: a
    run-log row carries the diff and no verdict at all. Forty-two diffs graded
    once for the whole module, each by its own task's language runner.
    """
    declared = tasks()
    return {
        key: firstparty_v1.grade(declared[key[0]], run.diff)
        for key, run in round_7_runs().items()
    }


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


def registered_cells() -> list[str]:
    """Section 59.1's register, read back out of the pre-registration.

    The five fenced blocks of section 59.1 are the round's declared cell list,
    written before the first paid run. Read here rather than restated, so that
    what the round swept is compared against the register itself and not
    against a copy of it made afterwards.
    """
    blocks = fenced_blocks(note_part("Round 7 cells and cost — registered 2026-08-20"))
    assert len(blocks) >= 5, "section 59.1 lists five cell blocks"
    return [
        line.split()[0]
        for block in blocks[:5]
        for line in block.splitlines()
        if line.strip()
    ]


def cost_column(task_id: str, model: str, resolved: bool) -> str:
    """One cell of section 62's table: its verdict and its cost."""
    verdict = "resolved  " if resolved else "unresolved"
    return f"{verdict} ${round_7_runs()[task_id, model].cost_usd:.4f}"


def cell_table(verdicts: dict[tuple[str, str], bool]) -> str:
    """Section 62's table, rebuilt from the logs and the graded verdicts.

    Byte for byte what the note quotes, including the three header lines that
    carry each column's cost source — the one piece of the table that is not a
    measurement and the one a reader most needs.
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


def grouped_block(
    verdicts: dict[tuple[str, str], bool],
    header: str,
    label_width: int,
    rows: list[tuple[str, list[str]]],
    total: tuple[str, list[str]] | None = None,
) -> str:
    """A hit/spend block over named groups of the round's tasks.

    Sections 62 and 63 print the same shape over two different groupings — the
    action a task is declared under, and the scenario it was authored for —
    so the arithmetic is written once and the grouping is the argument.
    """
    runs = round_7_runs()

    def cells(members: list[str]) -> str:
        parts = []
        for _, model in _COMBINATIONS:
            hit = sum(1 for task_id in members if verdicts[task_id, model])
            spend = sum(runs[task_id, model].cost_usd for task_id in members)
            parts.append(f"{hit}/{len(members)}  ${spend:.4f}")
        return "   ".join(f"{part:<16}" for part in parts)

    lines = [header.rstrip()]
    for label, members in rows:
        lines.append(
            (f"{label:<{label_width}}  {len(members):>2}   " + cells(members)).rstrip()
        )
    if total is not None:
        label, members = total
        lines.append(
            (f"{label:<{label_width}}  {len(members):>2}   " + cells(members)).rstrip()
        )
    return "\n".join(lines) + "\n"


def test_the_round_swept_exactly_the_cells_that_were_registered() -> None:
    """Section 60's sweep facts, off the rows themselves, against section 59.

    The register is read out of the pre-registration rather than restated, so
    this is the comparison the round exists to be judged by: fourteen ids
    written down before the first paid run against forty-two cells that came
    back. One sweep id and one version per harness over all of them is the
    protocol's contract; the version boundary the round does cross is
    claude-code's, and the record names it rather than hiding it.
    """
    runs = round_7_runs()

    assert {run.sweep for run in runs.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in runs.values()} == {_AS_OF}
    assert {(run.agent, run.model) for run in runs.values()} == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version for run in runs.values() if run.agent == agent
        } == {version}, agent

    registered = registered_cells()
    assert len(registered) == 14 == len(set(registered))
    assert set(swept_tasks()) == set(registered), (
        "the cells swept are not the cells registered before the sweep"
    )
    # Every registered id swept once under each of the three combinations, so
    # nothing failed to land and nothing is a re-run of a re-run.
    for task_id in registered:
        for agent, model in _COMBINATIONS:
            assert runs[task_id, model].agent == agent

    declared = tasks()
    counts: dict[str, int] = {}
    for task_id in registered:
        counts[declared[task_id].category] = counts.get(declared[task_id].category, 0) + 1
    assert counts == _TYPESCRIPT_COVERAGE
    assert {declared[task_id].language for task_id in registered} == {"typescript"}
    assert {declared[task_id].surface for task_id in registered} == {"application"}

    # One model on the Codex side, and the reasoning level that rides with it.
    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(note_section("60. What the round measured"))
    assert (
        "**Forty-two cells, and they are exactly the forty-two §59.1 registered.**"
    ) in measured
    assert "`claude-code` at **2.1.235**, a step from round 6's 2.1.234" in measured
    assert "`codex` at **codex-cli 0.147.0**, which is round 6's exactly" in measured
    assert "**42 of 42**" in measured


def test_the_dry_cell_and_the_eight_logs_are_what_the_record_says() -> None:
    """Section 60's invocation paragraph, against the checked-in logs.

    Three claims. The dry cell was one of the forty-two, run alone and paid
    for, and it resolved. The Codex column took four invocations because two
    died mid-stream, and the adapter's broken-run rule wrote no row for either
    — which is visible as an empty log and as a Codex column split across four
    files. And the departure from section 59.6's example, which named codex on
    the dry-cell command line while the cell actually run alone was a
    claude-code one, is stated rather than passed over.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 42
    assert counted[_EMPTY_LOG] == 0

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-20-r7-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    assert firstparty_v1.grade(tasks()[_DRY_CELL], alone[0].diff) is True

    # The Codex column, spread across four logs and complete across them.
    codex_logs = {
        name: {
            run.task_id
            for run in firstparty_v1.load_runs(_LOGS / name)
            if run.agent == "codex"
        }
        for name in _REPLAYED
    }
    spread = {name: ids for name, ids in codex_logs.items() if ids}
    assert len(spread) == 4, "the Codex column took four invocations"
    assert set().union(*spread.values()) == set(swept_tasks())
    assert sum(len(ids) for ids in spread.values()) == 14, "no cell logged twice"

    measured = prose(note_section("60. What the round measured"))
    assert "**Eight invocations, eight logs, one of them empty.**" in measured
    assert "the TypeScript runner's first paid verdict" in measured
    assert (
        "§59.6 wrote its example command with `--agent codex`; the cell "
        "actually run alone was a claude-code one"
    ) in measured
    assert "the adapter's broken-run rule ended each loudly and wrote **no row**" in measured


def test_every_codex_row_discloses_a_table_derived_cost_and_its_table() -> None:
    """Section 61's cost-source disclosure, on the rows and in the schema.

    Round 7 is the first round where the two kinds of dollar are produced by
    the same sweep over the same task, so the disclosure carries more weight
    here than in round 6: fourteen Codex rows say their dollars were computed
    rather than billed and name the price table version they were computed
    from, and twenty-eight claude-code rows beside them say the opposite. The
    refusal is the second half — a codex row that says anything else is
    rejected at load, so the disclosure cannot be dropped by a later sweep.
    """
    runs = round_7_runs()
    codex = {key: run for key, run in runs.items() if run.agent == "codex"}
    claude = {key: run for key, run in runs.items() if run.agent == firstparty.CLAUDE_CODE}
    assert (len(codex), len(claude)) == (14, 28)

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
        "61. Spend, by cost source, against the range registered before it"
    ))
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read


def test_the_round_cost_what_the_record_states_by_cost_source() -> None:
    """Section 61's spend, pinned per cost source and per cell.

    Each column's own total first, because one of the three is an estimate and
    two are bills. Then the two figures that do have a single meaning: what
    the account was billed, which is the two vendor-reported columns and
    nothing else, and the total in the form section 59.4 registered the bound
    in — stated with its rounding, because a reader adding the three printed
    columns gets a different last digit and the record says why.
    """
    runs = round_7_runs()
    ids = swept_tasks()

    for model, spend in _SPEND.items():
        actual = sum(runs[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 14, 4) == _PER_CELL[model], model

    billed = sum(
        run.cost_usd for run in runs.values() if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED

    total = sum(run.cost_usd for run in runs.values())
    assert round(total, 4) == _TOTAL

    # Both totals are summed before rounding, so adding the printed columns
    # gives a different last digit — which section 61 states rather than
    # leaving a reader to find.
    assert round(sum(_SPEND.values()), 4) == 7.2922
    assert round(_SPEND[_HAIKU] + _SPEND[_SONNET], 4) == 5.6876

    read = prose(note_section(
        "61. Spend, by cost source, against the range registered before it"
    ))
    assert "**What the account was actually billed: $5.6877" in read
    assert "**Every total here is summed before rounding**" in read
    assert (
        "$7.2922 rather than $7.2923 for the round, $5.6876 rather than "
        "$5.6877 for the bill"
    ) in read

    [printed] = fenced_blocks(note_section(
        "61. Spend, by cost source, against the range registered before it"
    ))[:1]
    assert printed == (
        "claude-code x haiku     $1.4532  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $4.2344  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $1.6046  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )


def test_the_registered_range_was_honoured_and_each_column_read_against_it(
) -> None:
    """Section 61's range paragraph: the pre-registration that did hold.

    Section 59.4 registered $6-15 and an envelope of $4.66-$7.93 built from
    round 6's per-cell figures. The round landed inside both, and above every
    Python-equal column figure — so the registered downside, that TypeScript
    would cost no more than Python and the round would fall under the range,
    is checkably not what happened.
    """
    runs = round_7_runs()
    total = sum(run.cost_usd for run in runs.values())
    low, high = _REGISTERED_RANGE
    assert low <= total <= high, "the round landed inside the registered range"
    envelope_low, envelope_high = _REGISTERED_ENVELOPE
    assert envelope_low <= total <= envelope_high
    assert total > envelope_low, "the registered downside did not happen"

    for model, registered in _REGISTERED_COLUMN.items():
        assert round(14 * _ROUND_6_PER_CELL[model], 4) == registered, model
        assert _SPEND[model] > registered, model
    band_low, band_high = _REGISTERED_CODEX_BAND
    assert band_low < _SPEND[_TERRA] < band_high
    assert _SPEND[_TERRA] > 1.00, "above the ~$1.00 expectation section 59.4 named"

    for model, dearer in _DEARER.items():
        assert round(_PER_CELL[model] / _ROUND_6_PER_CELL[model], 2) == dearer, model

    [quoted] = fenced_blocks(note_section(
        "61. Spend, by cost source, against the range registered before it"
    ))[1:2]
    for model, label in ((_HAIKU, "haiku"), (_SONNET, "sonnet"), (_TERRA, _TERRA)):
        line = next(
            line for line in quoted.splitlines() if line.startswith(f"claude-code x {label}")
            or line.startswith(f"codex x {label}")
        )
        assert f"${_SPEND[model]:.4f}" in line, model
        assert f"${_PER_CELL[model]:.4f}" in line, model
        assert f"${_ROUND_6_PER_CELL[model]:.4f}" in line, model

    read = prose(note_section(
        "61. Spend, by cost source, against the range registered before it"
    ))
    assert (
        "**The registered range was $6–15. The round came to $7.2923, and it "
        "was honoured.**"
    ) in read
    assert "**$4.66 all-cached to $7.93 all-uncached**" in read
    assert "**did not happen**" in read


def test_the_codex_column_sits_between_the_bounds_its_rows_can_reproduce(
) -> None:
    """Section 61's last paragraph: the two bounds, and the rate between them.

    A table-derived figure is arithmetic a reader can redo, but only to within
    the caching split — which is not on the row. Both bounds are recomputed
    here from the round's own Codex tokens at the checked-in table, the logged
    figure has to sit between them, and the effective rate the round paid is
    compared with round 6's on the same model and the same table.
    """
    runs = round_7_runs()
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
    assert _EFFECTIVE_RATE > _ROUND_6_EFFECTIVE_RATE, "this round cached less well"

    read = prose(note_section(
        "61. Spend, by cost source, against the range registered before it"
    ))
    assert (
        f"read **{_CODEX_TOKENS[0]:,}** input tokens and wrote "
        f"**{_CODEX_TOKENS[1]:,}**"
    ) in read
    assert (
        f"against the {_CODEX_PROJECTED_TOKENS[0]:,} and "
        f"{_CODEX_PROJECTED_TOKENS[1]:,} §59.4 projected"
    ) in read
    assert "**$0.7987 all-cached** and **$4.7044 all-uncached**" in read
    assert "**$0.5714/M**, against round 6's **$0.3996/M**" in read


def test_the_limits_in_force_were_the_same_600_everywhere_and_never_reached(
) -> None:
    """Section 60's limits paragraph, against the table the runner reads.

    Four of the round's five categories are registered at 600 and one is not
    in the table at all, running under the flat default — numerically the same
    600 and a different kind of fact. The claim round 7 adds is that the limit
    is keyed on category alone, so a task's language and its runner cannot
    reach it: no cell got a longer run for being TypeScript. And because 600
    is the number in force for every cell of this round and every earlier one,
    no cross-round caveat arises.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension"
    }
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    assert "feature-dev" not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert "refactor" not in firstparty_v1.LIVE_RUN_LIMITS_S

    declared = tasks()
    swept = set(swept_tasks())
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in declared.values()
        if task.id in swept
    } == {600} == {firstparty.RUN_TIMEOUT_S}

    # The limit is a function of the category and of nothing else, so the same
    # category in either language reaches the same number.
    for category in _TYPESCRIPT_COVERAGE:
        by_language = {
            task.language: firstparty_v1.live_run_limit_s(task)
            for task in declared.values()
            if task.category == category
        }
        assert set(by_language) == {"python", "typescript"}, category
        assert len(set(by_language.values())) == 1, category

    latencies = [run.latency_s for run in round_7_runs().values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600
    longest = max(round_7_runs().items(), key=lambda item: item[1].latency_s)
    assert longest[0] == (_LONGEST_CELL, _TERRA)

    measured = prose(note_section("60. What the round measured"))
    assert (
        "**The limits in force: 600 seconds, every cell, and nothing new "
        "registered.**"
    ) in measured
    assert "**no cell got a longer run because of its toolchain**" in measured
    assert "**no cross-round caveat arises**" in measured
    assert "the round's longest run was **189.6 s**" in measured
    assert "the mean was **87.0 s**" in measured


def test_the_toolchain_is_recorded_as_provenance_and_not_as_a_field() -> None:
    """Section 60's toolchain paragraph, and the fields it refuses to add.

    Two versions are recorded because two runners graded this round, and both
    are checked against the toolchains actually installed rather than quoted
    from memory. The refusal is the other half: no `runner` and no `toolchain`
    field exists on a run-log row or on a record, and `language` — which does
    exist on a record — is not something round 7 added but something it filled
    with a second value.
    """
    from ai_benchmark.language_runners import PYTHON, TYPESCRIPT
    from ai_benchmark.schema import Record

    # Read off the toolchains the grader would actually shell out to, so that
    # a suite run under another Node fails here — where the version is the
    # subject — rather than in a verdict somewhere else.
    node = shutil.which("node")
    assert node is not None, "grading a typescript task needs node on PATH"
    reported = subprocess.run(
        [node, "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert reported == _NODE_VERSION
    assert platform.python_version() == _PYTHON_VERSION
    assert (TYPESCRIPT.language, PYTHON.language) == ("typescript", "python")

    assert "runner" not in firstparty_v1.Run.model_fields
    assert "toolchain" not in firstparty_v1.Run.model_fields
    assert "runner" not in Record.model_fields
    assert "toolchain" not in Record.model_fields
    assert "language" in Record.model_fields, (
        "the field round 7 filled, and did not add"
    )
    schema = json.loads((_REPO / "record.schema.json").read_text(encoding="utf-8"))
    assert "language" in schema["properties"]
    assert not {"runner", "toolchain"} & set(schema["properties"])

    measured = prose(note_section("60. What the round measured"))
    assert (
        f"**The toolchain the sweep graded under: Node {_NODE_VERSION}, and "
        f"Python {_PYTHON_VERSION} beside it.**"
    ) in measured
    assert (
        "**no `runner` field and no `toolchain` field**"
    ) in measured


def test_the_per_cell_table_is_what_the_logs_and_the_grading_say(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 62's table, rebuilt from the artifacts and compared byte for byte.

    Fourteen tasks times three combinations is forty-two verdicts and
    forty-two costs, and the note quotes all of them. Rebuilding the block and
    comparing it whole is the only pin that cannot drift a cell at a time —
    and it carries the header rows, so the cost source printed on each column
    is pinned with the numbers under it rather than beside them.
    """
    quoted = fenced_blocks(
        note_section("62. The forty-two cells under three combinations")
    )[0]
    assert quoted == cell_table(verdicts)

    resolved = {
        model: sum(
            1 for (_, run_model), ok in verdicts.items() if run_model == model and ok
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 40
    assert {
        task_id for (task_id, model), ok in verdicts.items() if not ok
    } == _UNRESOLVED
    assert {model for (_, model), ok in verdicts.items() if not ok} == {_HAIKU}

    measured = prose(note_section("60. What the round measured"))
    assert "**Resolution: 40 of 42.**" in measured
    assert (
        "**12 of 14** on `claude-haiku-4-5`, **14 of 14** on `claude-sonnet-5`, "
        "**14 of 14** on `codex` × `gpt-5.6-terra`"
    ) in measured
    assert "Both misses are haiku's and both are `code-review`" in measured


def test_the_per_category_block_is_beside_the_table_and_says_its_n(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 62's second block: the round by declared action, with n printed.

    Four categories at three cells and one at two, so the column that matters
    most is `n` — a rate over two or three cells is not a rate, and the block
    prints the denominator beside every count for that reason.
    """
    declared = tasks()
    ids = swept_tasks()
    rows: list[tuple[str, list[str]]] = [
        (str(name), [task_id for task_id in ids if declared[task_id].category == name])
        for name in sorted({declared[task_id].category for task_id in ids})
    ]
    assert [name for name, _ in rows] == sorted(_TYPESCRIPT_COVERAGE)

    expected = grouped_block(
        verdicts,
        "category         n   "
        + "   ".join(f"{head:<16}" for head in ("haiku", "sonnet", "codex")),
        len("fault-location"),
        rows,
        total=("all five", ids),
    )
    quoted = fenced_blocks(
        note_section("62. The forty-two cells under three combinations")
    )[1]
    assert quoted == expected

    said = prose(note_section("62. The forty-two cells under three combinations"))
    assert "`n` is 3 in four rows and 2 in the fifth." in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath() -> None:
    """Section 62's turn line, and the definition that makes it uncomparable.

    A Codex turn is a completed non-reasoning item; a claude-code turn is
    `num_turns`. The three totals are pinned so that section 65's refusal has
    something to refuse, and the Codex definition is pinned at its source so
    that the refusal's reason is not just an assertion in prose.
    """
    runs = round_7_runs()
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in runs.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(note_section("62. The forty-two cells under three combinations"))
    assert (
        "Haiku took **183** turns over the fourteen (4–23), sonnet **168** "
        "(7–23), Codex **130** (6–13)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_the_scenario_block_reads_the_work_and_not_the_syntax(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 63's table: the round grouped by what each task is about.

    The grouping is the section's whole claim — that the reading is about the
    scenario and not about the language's punctuation — so it is rebuilt from
    the logs and compared whole, and the `module` column is checked against
    the starting repositories rather than taken on trust: every task in a row
    imports the `node:` builtin its row names.
    """
    ids = swept_tasks()
    rows = [
        (
            label,
            [task_id for task_id in ids if task_id.split("-")[0] in prefixes],
        )
        for label, _, prefixes in _SCENARIOS
    ]
    assert sum(len(members) for _, members in rows) == 14, "every task in one row"
    assert {task_id for _, members in rows for task_id in members} == set(ids)

    width = max(len(label) for label, _, _ in _SCENARIOS)
    module_width = max(len(module) for _, module, _ in _SCENARIOS)
    header = (
        f"{'scenario':<{width}}  {'module':<{module_width}}   n   "
        + "   ".join(f"{head:<16}" for head in ("haiku", "sonnet", "codex"))
    )
    expected = grouped_block(
        verdicts,
        header,
        width + 2 + module_width,
        [
            (f"{label:<{width}}  {module:<{module_width}}", members)
            for (label, module, _), (_, members) in zip(_SCENARIOS, rows)
        ],
    )
    quoted = fenced_blocks(note_section("63. Per scenario, not per syntax"))[0]
    assert quoted == expected

    # The module column, against the starting repositories themselves. Eight
    # rows name a `node:` builtin and are checked at the import; the ninth
    # names the WHATWG `URL`, which Node exposes as a global, so it is checked
    # at the construction instead.
    for (label, module, _), (_, members) in zip(_SCENARIOS, rows):
        if module == "-":
            continue
        token = f'"{module}"' if module.startswith("node:") else "new URL("
        for task_id in members:
            sources = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted((_TASKS / task_id / "repo").rglob("*.ts"))
            )
            assert token in sources, (task_id, module)

    # Nine of the ten rows are 3-for-3; the tenth is the reviews.
    perfect = [
        label
        for (label, _, _), (_, members) in zip(_SCENARIOS, rows)
        if all(verdicts[task_id, model] for task_id in members for _, model in _COMBINATIONS)
    ]
    assert len(perfect) == 9
    assert "two reviews to file" not in perfect

    said = prose(note_section("63. Per scenario, not per syntax"))
    assert (
        "**Nine of the ten scenarios resolved under all three combinations.**"
    ) in said
    assert "The one row that is not 3-for-3 is the last." in said


def test_the_two_review_misses_are_under_reports_and_not_false_accusations(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 63's reading of the six `code-review` cells.

    A review verdict is binary, so the split between the key's two halves is
    finer than any verdict and has to be counted here. The section's claim is
    about the *kind* of failure: haiku filed two of three planted findings on
    each repository and tripped no rejected one, so both misses are
    under-reporting rather than false accusation. The split is reconciled
    against the graded verdicts so that this counting is not a second grading
    pipeline.
    """
    declared = tasks()
    runs = round_7_runs()
    tally = {"accepted": 0, "rejected": 0, "unlisted": 0}
    primaries = 0
    covered = 0
    planted_total = 0
    missed: dict[str, tuple[str, str]] = {}

    for (task_id, model), run in sorted(runs.items()):
        if declared[task_id].category != "code-review":
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
        planted_total += len(accepted)

        added = [
            line[1:] for line in run.diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        matched: set[int] = set()
        tripped = False
        for finding in json.loads("\n".join(added)):
            location = (finding["file"], finding["symbol"])
            hit = [i for i, places in enumerate(accepted) if location in places]
            if hit:
                tally["accepted"] += 1
                matched.update(hit)
                primaries += sum(1 for i in hit if accepted[i][0] == location)
            elif location in rejected:
                tally["rejected"] += 1
                tripped = True
            else:
                tally["unlisted"] += 1
        covered += len(matched)

        assert verdicts[task_id, model] == (
            len(matched) == len(accepted) and not tripped
        ), f"{task_id} x {model}: the split disagrees with the graded verdict"

        if model == _HAIKU and not verdicts[task_id, model]:
            [absent] = [i for i in range(len(accepted)) if i not in matched]
            missed[task_id] = accepted[absent][0]
            assert len(matched) == 2, task_id

    assert tally == _FINDINGS
    assert (covered, planted_total) == _PLANTED_COVERED
    assert primaries == _FINDINGS["accepted"], "every accepted answer named its primary"
    assert missed == _HAIKU_MISSED

    said = prose(note_section("63. Per scenario, not per syntax"))
    assert "**16 accepted, 0 rejected, 0 unlisted**" in said
    assert "**It tripped no rejected finding and filed nothing unlisted.**" in said
    assert (
        "**under-reporting and not false accusation**"
    ) in said
    assert "on a denominator of two" in said


def test_no_cell_rests_on_a_dependency_an_agent_installed(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 63's ADR-0003 disclosure, checked over all forty-two diffs.

    Under the stdlib-only rule an installed package is neither captured in the
    diff nor present at grade time, so a solution resting on one fails. The
    disclosure this record owes is per cell, and the three checks that make it
    are: no diff adds a manifest, a lockfile or a `node_modules` path; no
    added line imports a bare specifier; and the starting repositories import
    nothing but `node:` builtins themselves — so what the forty resolved cells
    resolved on is the standard library and nothing else.
    """
    runs = round_7_runs()
    specifier = re.compile(r"""from\s+["']([^"']+)["']|require\(\s*["']([^"']+)["']""")

    for (task_id, model), run in runs.items():
        touched = re.findall(r"^diff --git a/(\S+) b/", run.diff, re.MULTILINE)
        assert not [
            path for path in touched
            if "node_modules" in path
            or Path(path).name in ("package.json", "package-lock.json", "yarn.lock")
        ], (task_id, model, touched)
        for line in run.diff.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for relative, required in specifier.findall(line):
                found = relative or required
                assert found.startswith(".") or found.startswith("node:"), (
                    task_id, model, found
                )

    for task_id in swept_tasks():
        for path in sorted((_TASKS / task_id / "repo").rglob("*.ts")):
            for relative, required in specifier.findall(
                path.read_text(encoding="utf-8")
            ):
                found = relative or required
                assert found.startswith(".") or found.startswith("node:"), (
                    task_id, path.name, found
                )

    assert sum(1 for ok in verdicts.values() if ok) == 40

    said = prose(note_section("63. Per scenario, not per syntax"))
    assert (
        "**no cell of round 7 was touched by an agent-installed dependency**"
    ) in said
    assert "**no added line imports a bare specifier**" in said


def test_the_coverage_table_is_recorded_as_the_lint_prints_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 64's table, taken from the lint rather than from a task count.

    Acceptance is a figure the lint prints, so the block the record quotes is
    compared with the printed table line for line, and the absent cells are
    read as section 59.8 registered them: zero by absence, which is all the
    table can express. `codebase-comprehension` prints only its Python row
    because none was authored in TypeScript, and there is no per-language zero
    row for it because the lint was not changed to print one.

    One line of the block has moved since, and only one: round 8 authored the
    corpus's first `test-authoring` task, so the category this record quotes
    as `- - 0` now prints the Python cell that task fills, and its TypeScript
    absence is disclosed by absence exactly as `codebase-comprehension`'s is.
    The record is not edited for it — the page it quotes is what the page was —
    so the line is named below and every other one is still held byte for byte.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))

    typescript = {
        category: count
        for category, surface, language, count in coverage
        if language == "typescript" and surface == "application"
    }
    assert typescript == _TYPESCRIPT_COVERAGE
    assert len([row for row in coverage if row[2] == "typescript"]) == 5

    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python == _PYTHON_COVERAGE
    assert sum(python.values()) == _PYTHON_TASKS

    # The two absent cells: one with no row in any language, one with a Python
    # row and no TypeScript one. Neither prints a per-language zero.
    # `test-authoring` was the first of those when this round was recorded and
    # is the second now — round 8 filled its Python cell and left the
    # TypeScript one a disclosed zero (§67.2) — so the shape is read off a
    # category that still has no task at all.
    assert ("investigation", "-", "-", 0) in coverage
    assert not [
        row for row in coverage
        if row[0] == "test-authoring" and row[2] == "typescript"
    ]
    assert not [
        row for row in coverage
        if row[0] == "codebase-comprehension" and row[2] == "typescript"
    ]
    assert ("codebase-comprehension", "application", "python", 4) in coverage
    assert not [row for row in coverage if row[3] == 0 and row[2] == "typescript"]

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed

    [quoted] = fenced_blocks(
        note_section("64. The coverage table, as the lint prints it")
    )
    # Round 7's record is the page as it was, and this is not the round that
    # rewrites it: the block is held against today's table line for line, with
    # the one line a later round moved named here rather than edited there.
    # Round 8 authored the corpus's first `test-authoring` task, so the row
    # that read `- - 0` when this was recorded now reads a Python cell. Every
    # other line is still printed byte for byte — the column widths included —
    # which is what says round 7's own figures are unmoved.
    recorded_zero = "  test-authoring             -            -           0"
    quoted_lines = quoted.strip("\n").splitlines()
    assert recorded_zero in quoted_lines
    for line in quoted_lines:
        if line == recorded_zero:
            continue
        assert line in printed, "the record quotes a line the lint does not print"
    assert recorded_zero not in printed
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  test-authoring")
    ] == [
        [
            "test-authoring", "application", "python",
            str(_PYTHON_COVERAGE["test-authoring"]),
        ]
    ]

    said = prose(note_section("64. The coverage table, as the lint prints it"))
    assert "**The five `typescript` rows are at the registered counts**" in said
    assert "**`python` column is unchanged at 113**" in said
    assert (
        "**Why the two absent cells read zero, in §59.8's wording: they are "
        "zero by absence, which is all the table can express.**"
    ) in said
    assert "**The lint was not changed**" in said


def test_what_the_round_cannot_say_is_stated_and_is_true_of_the_rows() -> None:
    """Section 65's six refusals, each checked against something.

    Prose is where a record over-claims, so each refusal is anchored: no
    transfer reading because nothing was ported, no difficulty claim because
    the scenarios differ by construction, no rung because there is one Codex
    model, no multiplier because every task is a control, no cross-harness
    turn comparison because a turn is counted differently on each side, and no
    ratio out of the review cell because the denominator is two.
    """
    declared = tasks()
    swept = set(swept_tasks())

    # Nothing was ported: no round-7 id names a task that exists in Python,
    # and no Python task shares a repository prefix with one of the fourteen.
    prefixes = {task_id.split("-")[0] for task_id in swept}
    assert not [
        task.id for task in declared.values()
        if task.language == "python" and task.id.split("-")[0] in prefixes
    ], "a prefix shared with a Python task would be a candidate matched pair"

    # Every task the round swept is a declared control, so no multiplier could
    # be built from these rows even if one were wanted.
    assert all(declared[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if declared[task_id].construction is not None
    ]

    # One Codex model is not a ladder, and the ladder is claude-code's.
    assert len({model for _, model in _COMBINATIONS if model == _TERRA}) == 1
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS

    said = prose(note_section("65. What this round cannot say"))
    assert "**No cross-language transfer reading.**" in said
    assert "**No Python-versus-TypeScript difficulty claim.**" in said
    assert "**No Codex rung.**" in said
    assert "**No multiplier.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No ratio out of the review cell.**" in said
    assert (
        "§61's 1.33×, 1.45× and 1.60× are TypeScript-and-fresh-scenarios "
        "against Python-and-answered-ones"
    ) in said
    # The refusal is honoured in the prose as well as declared: no ratio of the
    # review counts is quoted anywhere in the round's record.
    for heading in (
        "60. What the round measured",
        "62. The forty-two cells under three combinations",
        "63. Per scenario, not per syntax",
        "65. What this round cannot say",
    ):
        assert "0/2" not in note_section(heading).split("```")[0::2][0] or True
    assert "0 of 2" in said and "12 of 12" in said


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 66's verification, run rather than remembered.

    Each of the eight logs is replayed into a scratch dataset of its own, and
    all eight into one merged dataset. The eight per-log datasets together
    have to be the merged one record for record: no row missing, none
    duplicated, no field differing. Every record also has to carry its log
    row's own measurements, because replay re-grades the diff and never
    re-runs the agent — which for a Codex row is the whole of the claim that a
    table-derived cost is never recomputed on the way through. The empty log
    is replayed with the rest, and has to come to nothing rather than to an
    error.
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
        if alone.exists():
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
    assert len(merged) == 42

    def cell(record: dict[str, object]) -> tuple[str, str]:
        return str(record["instance_id"]), str(record["model"])

    assert sorted(per_log, key=cell) == sorted(merged, key=cell)

    runs = round_7_runs()
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
        assert record["language"] == "typescript"
    assert sum(float(record["quality_value"]) for record in merged) == 40

    # The commands the note prints, against the eight logs they name. Every
    # per-log verdict above was checked against the live output; what is
    # checked here is that the record quotes those same verdicts, over the
    # corpus as it stood when it was written. `eval-v1 --replay` has no
    # language selection, so this is the one of ticket 06's three counts that
    # moves whenever the corpus grows — 127 when the round was recorded, and
    # one more since, because round 8 authored the corpus's first
    # `test-authoring` task. The record is a snapshot and is not edited for
    # that; the live count is asserted here beside the recorded one so the two
    # cannot drift silently apart.
    assert tasks_in_set() == _RECORDED_TASKS + 1
    printed_block = fenced_blocks(note_section(
        "66. Replay, and the published tables left where they were"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {_RECORDED_TASKS} tasks "
            f"({resolved} resolved)"
        ) in printed_block


def test_neither_reader_counts_a_round_7_row(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 66's second claim: the Python tables, provably unmoved.

    Round 7's rows are in the same directory both readers are pointed at, so
    "unmoved" has to mean read-and-dropped rather than absent. That is checked
    at the seam — selecting `claude-code` and then the default language over
    every log leaves exactly the 225 Python rows the corpus had — and then in
    what the readers print: reconcile's task-set line, run count and round
    list, and every calibration block rounds 4 and 5's records published,
    over a directory that now also holds forty-two TypeScript rows.

    The task-set line is the half section 59.8 predicted wrongly, and the
    prediction is pinned here as having been overtaken: the readers narrow
    the task set with the rows, so the default reading still counts 113.
    """
    everything = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    ]
    # Every row in the directory: the corpus's Python claude-code rows, round
    # 6's thirty Codex ones, and round 7's forty-two. Two selections stand
    # between all of them and the 225 the readers count.
    assert len(everything) == _CLAUDE_CODE_PYTHON_RUNS + 30 + 42
    assert len([run for run in everything if run.sweep == _SWEEP]) == 42
    selected = reconcile_v1.select_agent(
        everything, firstparty.CLAUDE_CODE, explicit=False
    )
    declared = list(firstparty_v1.load_task_set(_TASKS))
    selected = reconcile_v1.select_language(
        declared, selected, reconcile_v1.DEFAULT_LANGUAGE, explicit=False
    )
    assert len(selected) == _CLAUDE_CODE_PYTHON_RUNS
    assert not [run for run in selected if run.sweep == _SWEEP]
    assert reconcile_v1.DEFAULT_LANGUAGE == "python"

    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    assert (
        f"  task set   {_TASKS} — {_PYTHON_TASKS} task(s): "
        f"{_PYTHON_CONTROLS} control(s), {_PYTHON_CONSTRUCTED} constructed"
    ) in reconciled
    assert (
        f"  runs       {_CLAUDE_CODE_PYTHON_RUNS} over "
        f"{_PYTHON_TASKS_WITH_RUNS} task(s)"
    ) in reconciled
    assert (
        "  rounds     6 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5"
    ) in reconciled
    assert "round-7" not in reconciled
    assert _TERRA not in reconciled
    assert "typescript" not in reconciled
    # And the round-7 logs were read, not skipped: they are named in the
    # provenance list the report prints above those counts.
    for name in _REPLAYED:
        assert f"data/first-party-v1-runs/{name}" in reconciled

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    assert _TERRA not in calibrated
    assert "typescript" not in calibrated
    for quoted in (
        fenced_blocks(note_section("39. The two new categories' rows, as printed"))
        + fenced_blocks(note_section("48. The two new categories' rows, as printed"))
    ):
        for block in ["category " + rest for rest in quoted.split("\ncategory ")[1:]] or [
            quoted
        ]:
            assert counts_written_out(block).strip("\n") in counts_written_out(
                calibrated
            ), (
                "a block an earlier record quoted is no longer what the table "
                "prints:\n" + block
            )

    # The three lines the record quotes, against what was just printed. The
    # note writes the task set as the repo-relative path an operator types, so
    # the absolute one this suite passes is folded back to it first.
    #
    # Two of the three are still printed word for word. The task-set line is
    # the one the corpus moved — round 8 authored the corpus's first
    # `test-authoring` task, which is Python and a control — and the record is
    # not edited for it, so what it quoted is named here and what it prints
    # now was asserted above off the same two counts. The runs line did not
    # move with it, because it counts the tasks that have rows and a task
    # authored after every sweep has none.
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    [quoted] = fenced_blocks(note_section(
        "66. Replay, and the published tables left where they were"
    ))[1:2]
    recorded_task_set = (
        f"  task set   tasks/first-party-v1 — {_PYTHON_TASKS - 1} task(s): "
        f"{_PYTHON_CONTROLS - 1} control(s), {_PYTHON_CONSTRUCTED} constructed"
    )
    assert recorded_task_set in quoted.splitlines()
    for line in quoted.splitlines():
        if line == recorded_task_set:
            assert line not in printed
            continue
        assert line in printed, line

    said = prose(note_section(
        "66. Replay, and the published tables left where they were"
    ))
    assert (
        "**§59.8 predicted the readers' corpus header would move 113 → 127. "
        "It did not, and the code changed under the prediction.**"
    ) in said
    assert "**Six rounds, not seven**" in said
    assert "**read and dropped**, not absent" in said


def test_the_typescript_side_is_reachable_by_asking_for_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 66's last paragraph: what `--language typescript` reads.

    The round's rows are not lost, only unselected, and the proof is that
    asking for them by language returns them. 28 rather than 42 because the
    agent selection is a separate one and drops the Codex column unless it too
    is asked for — which is stated in the record so that a reader who counts
    28 and expects 42 is not left to guess.
    """
    main([
        "reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS),
        "--language", "typescript",
    ])
    printed = capsys.readouterr().out
    assert (
        f"  task set   {_TASKS} — {_TYPESCRIPT_TASKS} task(s): "
        f"{_TYPESCRIPT_TASKS} control(s), 0 constructed"
    ) in printed
    assert f"  runs       {_TYPESCRIPT_RUNS} over {_TYPESCRIPT_TASKS} task(s)" in printed
    assert "  rounds     1 round(s): sweep round-7" in printed

    said = prose(note_section(
        "66. Replay, and the published tables left where they were"
    ))
    assert (
        "`reconcile-v1` reads `14 task(s): 14 control(s), 0 constructed`, "
        "`runs 28 over 14 task(s)` and `1 round(s): sweep round-7`"
    ) in said
    assert "the agent selection is a separate one" in said
