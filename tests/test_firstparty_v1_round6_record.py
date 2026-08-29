"""Round 6's record, pinned: what sections 53-58 of the design note publish.

The round swept thirty already-answered cells under a **second harness** —
`codex` x `gpt-5.6-terra` at reasoning `medium`, one combination and no ladder
— so its readings are cross-agent ones and its one genuinely new hazard is a
dollar figure that is not a bill. Codex prints no cost of its own, so every
Codex row's `cost_usd` is this repository's arithmetic over a checked-in price
table (`cost_source: table-derived`) beside claude-code rows that carry the
vendor's own figure. A reader who joins the two without being told is joining
an estimate to a bill, which is why section 55's table prints the cost source
on the column and why this file pins the two spends apart.

Every figure is pinned rather than derived, which is the point: a derived
expectation follows the corpus wherever it goes, and these numbers are quoted
in the design note and read by whoever is deciding what a round cost. The pins
come in two halves, as round 5's do. The first is arithmetic over the
checked-in run logs and the verdicts re-grading their diffs produces. The
second reads the design note itself — its quoted tables against what the logs
actually say, its quoted commands against what they actually print — because a
record whose numbers drift from the artifacts that earned them is the defect
this file exists to catch, and the record is prose that nothing else checks.

The round's runs are selected by their **sweep id** and never by log filename:
the sweep protocol bans selecting run logs by name, having watched the first
pass of the round-1 analysis silently drop two paid cells that way. The two
filenames appear here only where a command has to be given a log to replay,
which is section 58's verification.
"""

import inspect
import json
import re
import statistics
from pathlib import Path

import pytest

from ai_benchmark import agents, firstparty, firstparty_v1, pricing, reconcile_v1
from ai_benchmark.cli import main

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_SWEEP = "round-6"
_AGENT = "codex"
_AGENT_VERSION = "codex-cli 0.147.0"
_AS_OF = "2026-08-18"
_MODEL = "gpt-5.6-terra"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_LADDER = (_HAIKU, _SONNET)

# The two logs the sweep's two invocations wrote: the dry cell alone, then the
# other twenty-nine. Named only so that section 58's replay can be given one
# log at a time; nothing here selects runs by them.
_LOG_NAMES = ("2026-08-18-r6-a.jsonl", "2026-08-18-r6-b.jsonl")
_DRY_CELL = "noticeboard-locate-the-lost-notice"

# Section 53's spend, and section 54's split of it by cost source. The Codex
# figure is a list-price estimate and the two claude-code figures are the
# vendor's own, over the same thirty cells; they are pinned apart because
# adding them would be the mistake the whole section exists to prevent.
_CODEX_SPEND = 2.1511
_LADDER_SPEND = {_HAIKU: 2.3481, _SONNET: 6.2572}

# Section 54's token totals and the two bounds a reader can recompute from a
# row: all-cached below, all-uncached above, the logged figure between. The
# split the figure was actually priced from is not on the row, which is the
# paragraph's point.
_TOKENS_IN = 3_892_528
_TOKENS_OUT = 49_636
_ALL_CACHED = 1.3741
_ALL_UNCACHED = 8.3807

# Section 52.4's registered range, and section 54's plain statement that the
# round landed under it.
_REGISTERED_RANGE = (5.0, 10.0)

# Section 53's resolution line, and the one cell it turns on: the review cell
# round 5's sonnet also failed, at the same location on the same argument.
_UNRESOLVED = "apiary-review-the-book-and-the-crop"
_RESOLVED = {"codex": 29, _HAIKU: 24, _SONNET: 27}

# Section 53's limits paragraph: nothing came near the ceiling every cell ran
# under.
_LONGEST_S = 92.8
_MEAN_S = 63.0

# Section 57's turn line. A Codex turn is a completed non-reasoning item and a
# claude-code turn is `num_turns`; these are Codex's own, quoted so that the
# section's refusal to compare them is anchored to a number.
_CODEX_TURNS = 248
_CODEX_TURN_RANGE = (6, 15)

# Section 58: what each log replays to, and what the corpus's two readers say
# once the Codex rows have been read out of the same directory and dropped.
_REPLAYED = {_LOG_NAMES[0]: (1, 1), _LOG_NAMES[1]: (29, 28)}
_CLAUDE_CODE_RUNS = 225

# Three readings that were one number on the day this was recorded, and are
# kept apart here because only one of them may move.
#
# `_TASKS_AS_RECORDED` is the corpus size the note's own fenced block printed:
# archived text, quoted back to prove the block says what the command said, and
# a literal that never moves however far the corpus grows afterwards.
#
# `_TASKS_THE_RUNS_MENTION` is how many tasks the checked-in logs actually
# swept, which is what reconcile's provenance header counts (`len(swept)` in
# `reconcile_v1.provenance_lines`). A fact about the logs and not about the
# corpus: authoring a task adds nothing to it, and only a further sweep can.
#
# `tasks_in_set()` is the corpus *now*, read off the checked-in task set the
# CLI is pointed at, because what `eval-v1 --replay` prints is today's count.
# Round 7 is the first round to grow the corpus past the recorded figure, and
# a pin that conflated these would go red on every task ticket after it for
# saying nothing about round 6.
_TASKS_AS_RECORDED = 113
_TASKS_THE_RUNS_MENTION = 113

# What round 8 added to both of the moving numbers: three `test-authoring`
# tasks, each of them Python and a control, swept by six claude-code rows and
# three Codex ones. Named apart from the round-6 figures above so that the
# claim §58 makes — agent selection drops every round-6 row — stays readable
# beside the counts a later round moved.
_ROUND_8_TASKS = 3
_ROUND_8_CLAUDE_CODE_RUNS = 6

# And what round 10's sweep then added, on 2026-08-24: three `investigation`
# tasks — Python controls all — swept by six claude-code rows and three more
# Codex ones. The same shape as round 8's arrival, named apart for the same
# reason.
_ROUND_10_TASKS = 3
_ROUND_10_CLAUDE_CODE_RUNS = 6

# And round 11's, on 2026-08-26: three `requirement-decomposition` tasks —
# Python controls all — swept by six claude-code rows and three more Codex
# ones. The same shape a third time, named apart for the same reason.
_ROUND_11_TASKS = 3
_ROUND_11_CLAUDE_CODE_RUNS = 6

# And round 12's, on 2026-08-28: three explain-style `codebase-comprehension`
# tasks — Python controls all — swept by six claude-code rows and three more
# Codex ones. The same shape a fourth time, named apart for the same reason.
_ROUND_12_TASKS = 3
_ROUND_12_CLAUDE_CODE_RUNS = 6


def tasks_in_set() -> int:
    """How many tasks the checked-in set holds, as `eval-v1` counts them."""
    return len(firstparty_v1.load_task_set(_TASKS))


# The two fields of a calibration block a later round moves, and the only two.
#
# A block holds numbers of two kinds. The **measured** ones — the baseline
# means, every `(n=…)`, the multipliers, the rung floor — are the round that
# published them, and no task authored afterwards touches them. The **counted**
# ones — how many tasks the row holds, and the scope and substrate mix its
# denominator is drawn from — grow the moment a later round authors another
# control in the category: unswept, changing no measurement, and moving two
# digits in a block an earlier record quotes as printed. So a quoted block is
# compared with the counted ones written out; this suite's claim is that the
# earlier records' tables are *unmoved by the Codex rows*, and a count that
# round 7 moved says nothing about that either way.
_COUNTED_MIX = re.compile(
    r"^(   baseline mix +)\d+( single-file; )\d+( hand-authored)", re.MULTILINE
)
_COUNTED_ROW = re.compile(r"^(   \(zero-knob\)  )\d+ +", re.MULTILINE)


def counts_written_out(text: str) -> str:
    """This calibration output with its counted fields replaced by a mark."""
    return _COUNTED_ROW.sub(r"\1N ", _COUNTED_MIX.sub(r"\1N\2N\3", text))


def round_6_runs() -> dict[str, firstparty_v1.Run]:
    """Every run the sweep logged, keyed by task.

    Read out of every log in the run-log directory and selected on the sweep
    id, which is what identifies a round: the sweep took two invocations, and
    a filename says nothing about which sweep a row belongs to. Keyed by task
    alone because the round is one combination — thirty tasks, one model.
    """
    logged = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    ]
    assert len(logged) == 30, "the round is 30 cells"
    runs = {run.task_id: run for run in logged}
    assert len(runs) == 30, "a task was swept twice"
    return runs


def ladder_runs() -> dict[tuple[str, str], firstparty_v1.Run]:
    """The claude-code rows the round's thirty cells are read against.

    Nothing was re-run on Claude this round (section 52.2), so the comparison
    side is whatever the earlier rounds' logs already carry — found by task
    and model over the whole directory rather than by sweep, because these
    rows belong to rounds 2 through 5.
    """
    swept = set(round_6_runs())
    logged = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.agent == firstparty.CLAUDE_CODE and run.task_id in swept
    ]
    assert len(logged) == 60, "each of the thirty needs both ladder rows, once"
    return {(run.task_id, run.model): run for run in logged}


def categories() -> dict[str, str]:
    """Each of the round's tasks against the category it declares."""
    return {task.id: task.category for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def verdicts() -> dict[tuple[str, str], bool]:
    """Every cell of section 55's table re-graded, keyed task x model.

    The computation `eval-v1 --replay` does, and the only way to a verdict: a
    run-log row carries the diff and no verdict at all. Ninety diffs — the
    round's thirty and the sixty ladder rows they are read against — graded
    once for the whole module.
    """
    tasks = {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}
    graded = {
        (task_id, _MODEL): firstparty_v1.grade(tasks[task_id], run.diff)
        for task_id, run in round_6_runs().items()
    }
    graded.update(
        {key: firstparty_v1.grade(tasks[key[0]], run.diff)
         for key, run in ladder_runs().items()}
    )
    return graded


def note_section(heading: str) -> str:
    """One numbered section of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"### {heading}\n")[1]
    return body.split("\n### ")[0].split("\n## ")[0]


def note_part(heading: str) -> str:
    """One top-level part of the design note, by its heading line.

    Section 52 is written as bold-numbered paragraphs under a `##` heading
    rather than as `###` sections, so the registered cell list has to be read
    this way rather than through `note_section`.
    """
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


def registered_cells() -> dict[str, list[str]]:
    """Ticket 08's register, read back out of section 52.

    The five fenced blocks of section 52.1 are the round's declared cell list,
    written before the first paid run. Read here rather than restated, so that
    what the round swept is compared against the register itself and not
    against a copy of it made afterwards.
    """
    blocks = fenced_blocks(note_part("Round 6 cells and cost — registered 2026-08-18"))
    assert len(blocks) == 6, "section 52 lists five cell blocks and one command"
    return {
        name: [line.split()[0] for line in block.splitlines() if line.strip()]
        for name, block in zip(
            ("round-4", "code-review", "codebase-comprehension",
             "feature-dev", "refactor"),
            blocks,
        )
    }


def cell_table(verdicts: dict[tuple[str, str], bool]) -> str:
    """Section 55's table, rebuilt from the logs and the graded verdicts.

    Byte for byte what the note quotes, including the three header lines that
    carry each column's cost source — the one piece of the table that is not a
    measurement and the one a reader most needs.
    """
    runs = round_6_runs() | {
        key: run for key, run in ladder_runs().items()
    }
    ids = sorted(round_6_runs())
    width = max(len(task_id) for task_id in ids)

    def column(task_id: str, model: str) -> str:
        run = runs[task_id] if model == _MODEL else runs[task_id, model]
        verdict = "resolved  " if verdicts[task_id, model] else "unresolved"
        return f"{verdict} ${run.cost_usd:.4f}"

    lines = [
        (" " * (width + 2) + "  ".join(f"{cell:<18}" for cell in row)).rstrip()
        for row in (
            ("claude-code x", "claude-code x", "codex x"),
            (_HAIKU, _SONNET, _MODEL),
            ("vendor-reported", "vendor-reported", "table-derived"),
        )
    ]
    lines += [
        (f"{task_id:<{width}}  "
         + "  ".join(f"{column(task_id, model):<18}"
                     for model in (_HAIKU, _SONNET, _MODEL))).rstrip()
        for task_id in ids
    ]
    return "\n".join(lines) + "\n"


def test_the_round_swept_exactly_the_cells_that_were_registered() -> None:
    """Section 53's sweep facts, off the rows themselves, against section 52.

    The register is read out of the pre-registration rather than restated, so
    this is the comparison the round exists to be judged by: thirty ids
    written down before the first paid run against thirty cells that came
    back. One sweep id, one agent, one model and one harness version over all
    of them is the protocol's contract and what keeps the round free of a
    version boundary.
    """
    runs = round_6_runs()

    assert {run.sweep for run in runs.values()} == {_SWEEP}
    assert {run.agent for run in runs.values()} == {_AGENT}
    assert {run.model for run in runs.values()} == {_MODEL}
    assert {run.agent_version for run in runs.values()} == {_AGENT_VERSION}
    assert {run.as_of.isoformat() for run in runs.values()} == {_AS_OF}

    register = registered_cells()
    registered = {task_id for ids in register.values() for task_id in ids}
    assert len(registered) == 30
    assert set(runs) == registered, (
        "the cells swept are not the cells registered before the sweep"
    )

    # And the register's own counts, per category, against what the task set
    # declares: section 53 quotes them as the shape of the round.
    category = categories()
    counts: dict[str, int] = {}
    for task_id in registered:
        counts[category[task_id]] = counts.get(category[task_id], 0) + 1
    assert counts == {
        "bug-fix": 6, "fault-location": 6, "code-review": 4,
        "codebase-comprehension": 2, "feature-dev": 6, "refactor": 6,
    }
    assert set(register["round-4"]) == {
        task_id for task_id in registered
        if category[task_id] in ("bug-fix", "fault-location")
    }

    # The one Codex combination, and the reasoning level that rides with the
    # model rather than with the operator: no invocation could have asked for
    # another.
    assert agents.CODEX_REASONING_LEVELS == {_MODEL: "medium"}

    measured = prose(note_section("53. What the round measured"))
    assert "**the thirty are exactly the thirty §52.1 registered**" in measured
    assert "The version is `codex-cli 0.147.0`" in measured
    assert "**it held across both**" in measured


def test_every_codex_row_discloses_a_table_derived_cost_and_its_table() -> None:
    """Section 54's cost-source disclosure, on the rows and in the schema.

    Two claims travel together. Every row of the round says its dollars were
    computed rather than billed, and names the price table version they were
    computed from — and that version is the checked-in table's own, so the
    name is traceable rather than decorative. The second is the refusal: a
    codex row that says anything else is rejected at load, so the disclosure
    cannot be dropped by a later sweep.
    """
    runs = round_6_runs()
    assert {run.cost_source for run in runs.values()} == {"table-derived"}
    assert {run.price_table for run in runs.values()} == {
        pricing.load_price_table(_REPO / "data" / "price-table.json").version
    }

    with pytest.raises(ValueError, match="table-derived"):
        firstparty_v1.Run(
            **(
                runs[_DRY_CELL].model_dump()
                | {"cost_source": "vendor-reported", "price_table": None}
            )
        )

    # The claude-code rows this round is read against were written before the
    # field existed, so they carry none — vendor-reported by construction, and
    # section 54 says so rather than pretending the field is on them.
    ladder = ladder_runs()
    assert {run.cost_source for run in ladder.values()} == {None}
    assert agents.ClaudeCodeAdapter.cost_source == "vendor-reported"
    assert agents.ClaudeCodeAdapter.price_table is None

    read = prose(note_section(
        "54. Spend, by cost source, against the range registered before it"
    ))
    assert "**What the account was billed: nothing per token.**" in read
    assert "It is not an invoice" in read
    assert "they carry **no `cost_source` at all**" in read


def test_the_round_cost_what_the_record_states_by_cost_source() -> None:
    """Section 54's spend, pinned per cost source rather than in total.

    There is deliberately no combined figure here, and none in the note: one
    of these three numbers is an estimate and two are bills, so their sum
    would be a quantity with no meaning. What is checked is each column's own
    total, the per-cell figures the section quotes, and the block the note
    prints them in.
    """
    codex = round_6_runs()
    ladder = ladder_runs()

    assert round(sum(run.cost_usd for run in codex.values()), 4) == _CODEX_SPEND
    for model, spend in _LADDER_SPEND.items():
        actual = sum(
            run.cost_usd for (_, run_model), run in ladder.items()
            if run_model == model
        )
        assert round(actual, 4) == spend, model

    assert round(_CODEX_SPEND / 30, 4) == 0.0717
    assert round(_LADDER_SPEND[_HAIKU] / 30, 4) == 0.0783
    assert round(_LADDER_SPEND[_SONNET] / 30, 4) == 0.2086

    [printed] = fenced_blocks(note_section(
        "54. Spend, by cost source, against the range registered before it"
    ))
    assert printed == (
        "codex x gpt-5.6-terra     $2.1511  table-derived  "
        "(list price, openai-pricing-2026-08-18.1)\n"
        "claude-code x haiku       $2.3481  vendor-reported "
        "(the same thirty cells, already logged)\n"
        "claude-code x sonnet      $6.2572  vendor-reported "
        "(the same thirty cells, already logged)\n"
    )


def test_the_registered_range_was_missed_low_and_the_record_says_so() -> None:
    """Section 54's range paragraph: the pre-registration that did not hold.

    Section 52.4 registered $5-10 before anyone spent, and the round came to
    less than half the low end. The record has to say that plainly rather than
    quietly, and it has to say why: the estimate priced every input token as
    though none of it were cached, which is checkable — the all-uncached bound
    over the round's own tokens lands inside the registered range.
    """
    runs = round_6_runs()
    spend = sum(run.cost_usd for run in runs.values())
    low, high = _REGISTERED_RANGE
    assert spend < low, "the round landed under the registered range"

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    tokens_in = sum(run.tokens_in for run in runs.values())
    tokens_out = sum(run.tokens_out for run in runs.values())
    assert (tokens_in, tokens_out) == (_TOKENS_IN, _TOKENS_OUT)

    def bound(cached: bool) -> float:
        return pricing.cost_usd(
            table, _MODEL,
            input_plain_tokens=0 if cached else tokens_in,
            input_cached_tokens=tokens_in if cached else 0,
            input_cache_write_tokens=0,
            output_tokens=tokens_out,
        )

    assert round(bound(cached=True), 4) == _ALL_CACHED
    assert round(bound(cached=False), 4) == _ALL_UNCACHED
    assert _ALL_CACHED < spend < _ALL_UNCACHED, (
        "the logged figure must sit between the bounds a row can reproduce"
    )
    assert low <= _ALL_UNCACHED <= high, (
        "the registration's mistake is that it priced the round at its "
        "all-uncached bound, which is what puts that bound inside the range"
    )

    # What the row cannot reproduce: the split it was priced from. `tokens_in`
    # is the input total, and the effective rate the round paid is neither the
    # cached nor the uncached one.
    prices = table.models[_MODEL]
    effective = (spend - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1_000_000, 4) == 0.3996
    assert (
        prices.input_cached_per_token
        < effective
        < prices.input_uncached_per_token
    )

    read = prose(note_section(
        "54. Spend, by cost source, against the range registered before it"
    ))
    assert (
        "**The registered range was $5–10. The round came to $2.1511. "
        "It was not honoured**"
    ) in read
    assert "it missed low by a factor of 2.3" in read
    assert "$1.3741 all-cached and $8.3807 all-uncached" in read
    assert "cannot reproduce $2.1511 itself" in read


def test_the_limits_in_force_were_the_same_600_everywhere_and_never_reached(
) -> None:
    """Section 53's limits paragraph, against the table the runner reads.

    Four of the round's six categories are registered at 600 and two are not
    in the table at all, running under the flat default — numerically the same
    600 and a different kind of fact. Because the number in force is 600 for
    every cell and 600 is what every earlier round ran at, no cross-round
    caveat arises. The second half is the round's own evidence that no verdict
    is a timeout in disguise.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension"
    }
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    assert "feature-dev" not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert "refactor" not in firstparty_v1.LIVE_RUN_LIMITS_S

    swept = set(round_6_runs())
    limits = {
        firstparty_v1.live_run_limit_s(task)
        for task in firstparty_v1.load_task_set(_TASKS)
        if task.id in swept
    }
    assert limits == {600} == {firstparty.RUN_TIMEOUT_S}

    latencies = [run.latency_s for run in round_6_runs().values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600

    measured = prose(note_section("53. What the round measured"))
    assert "**The limits in force: 600 seconds, every cell.**" in measured
    assert "**no cross-round caveat arises**" in measured
    assert "the round's longest run was **92.8 s**" in measured


def test_the_per_cell_table_is_what_the_logs_and_the_grading_say(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 55's table, rebuilt from the artifacts and compared byte for byte.

    Thirty cells times three combinations is ninety verdicts and ninety costs,
    and the note quotes all of them. Rebuilding the block and comparing it
    whole is the only pin that cannot drift a cell at a time — and it carries
    the header rows, so the cost source printed on each column is pinned with
    the numbers under it rather than beside them.
    """
    quoted = fenced_blocks(
        note_section("55. The thirty cells under three combinations")
    )[0]
    assert quoted == cell_table(verdicts)

    # The resolution counts the record states, read off the same verdicts.
    resolved = {
        model: sum(
            1 for (task_id, run_model), ok in verdicts.items()
            if run_model == model and ok
        )
        for model in (_MODEL, _HAIKU, _SONNET)
    }
    assert resolved == {
        _MODEL: _RESOLVED["codex"],
        _HAIKU: _RESOLVED[_HAIKU],
        _SONNET: _RESOLVED[_SONNET],
    }
    assert {
        task_id for (task_id, model), ok in verdicts.items()
        if model == _MODEL and not ok
    } == {_UNRESOLVED}
    # The same cell round 5's sonnet failed, which is what section 55 reads.
    assert verdicts[_UNRESOLVED, _SONNET] is False

    measured = prose(note_section("53. What the round measured"))
    assert "**Resolution: 29 of 30.**" in measured
    assert (
        "24 of 30 on `claude-haiku-4-5` and 27 of 30 on `claude-sonnet-5`"
    ) in measured


def test_the_per_category_sample_is_beside_the_table_and_says_its_n(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 55's second block: the sample, per category, with n printed.

    Two of the six categories are sampled at four cells and two, so the row
    that matters most is the `n` column — a rate over two cells is not a rate,
    and the block prints the denominator beside every count for that reason.
    """
    runs = round_6_runs()
    ladder = ladder_runs()
    category = categories()

    rows = []
    for name in sorted({category[task_id] for task_id in runs}):
        members = [task_id for task_id in runs if category[task_id] == name]
        parts = []
        for model in (_HAIKU, _SONNET, _MODEL):
            hit = sum(1 for task_id in members if verdicts[task_id, model])
            spend = sum(
                (runs[task_id] if model == _MODEL else ladder[task_id, model]).cost_usd
                for task_id in members
            )
            parts.append(f"{hit}/{len(members)}  ${spend:.4f}")
        rows.append((name, len(members), parts))

    quoted = fenced_blocks(note_section("55. The thirty cells under three combinations"))[1]
    for name, n, parts in rows:
        line = next(
            line for line in quoted.splitlines() if line.startswith(name + " ")
        )
        assert line.split()[1] == str(n), name
        for part in parts:
            assert " ".join(part.split()) in " ".join(line.split()), (name, part)

    assert "all six                 30" in quoted
    for model, count in ((_HAIKU, 24), (_SONNET, 27), (_MODEL, 29)):
        spend = _CODEX_SPEND if model == _MODEL else _LADDER_SPEND[model]
        assert f"{count}/30  ${spend:.4f}" in quoted


def test_the_review_findings_land_where_section_55_says(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 55's arithmetic over the four `code-review` cells.

    A review verdict is binary, so the split between the key's two halves is
    finer than any verdict and has to be counted here: 13 answers matched a
    planted finding, one matched a rejected one, and two were unlisted and
    archived. The thirteenth accepted answer is a duplicate — `Book.owed`
    written twice — which costs nothing because the verdict asks whether a set
    covers another, and the split is reconciled against the graded verdicts so
    that this counting is not a second grading pipeline.
    """
    runs = round_6_runs()
    category = categories()
    tally = {"accepted": 0, "rejected": 0, "unlisted": 0}
    primaries = 0
    covered = 0
    planted_total = 0

    for task_id, run in runs.items():
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

        assert verdicts[task_id, _MODEL] == (
            len(matched) == len(accepted) and not tripped
        ), f"{task_id}: the split disagrees with the graded verdict"

    assert tally == {"accepted": 13, "rejected": 1, "unlisted": 2}
    assert primaries == 13, "every accepted answer named its finding's primary"
    assert (covered, planted_total) == (12, 12), "every planted finding covered"

    read = prose(note_section("55. The thirty cells under three combinations"))
    assert (
        "13 matched a planted one, all 13 at its primary; one matched a "
        "rejected one; two were unlisted and archived"
    ) in read
    assert (
        "**A second harness and a different vendor's model, given the same "
        "repository, filed the identical pair of extra findings**"
    ) in read


def test_the_same_two_extra_findings_were_filed_by_sonnet_and_by_codex(
) -> None:
    """Section 55's replication claim, compared answer to answer.

    The claim is not that two runs failed the same cell but that they named
    the same locations: the three planted findings, plus `Roll.keeping` (the
    rejected one) and `Book.off_hive` (unlisted). Compared as sets of
    locations, because that is all a verdict reads — the notes beside them are
    archived and never inspected.
    """
    def locations(run: firstparty_v1.Run) -> set[tuple[str, str]]:
        added = [
            line[1:] for line in run.diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        return {
            (finding["file"], finding["symbol"])
            for finding in json.loads("\n".join(added))
        }

    codex = locations(round_6_runs()[_UNRESOLVED])
    sonnet = locations(ladder_runs()[_UNRESOLVED, _SONNET])
    assert codex == sonnet
    assert ("keepers.py", "Roll.keeping") in codex
    assert ("harvest.py", "Book.off_hive") in codex

    # And the belfry near-miss, filed by all three combinations.
    belfry = "belfry-review-the-peals-and-the-board"
    near_miss = ("peals.py", "Book.rung_by")
    assert near_miss in locations(round_6_runs()[belfry])
    assert all(
        near_miss in locations(ladder_runs()[belfry, model]) for model in _LADDER
    )


def test_locating_against_fixing_under_all_three_combinations(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 56's table: round 4's six defects, both actions, three columns.

    The haiku and sonnet columns are section 40's and are recomputed here from
    the same rows rather than copied, so a change to either round's logs fails
    both records at once. The Codex column is new, and its six unstarred pairs
    are the reading the section takes.
    """
    runs = round_6_runs()
    ladder = ladder_runs()
    category = categories()
    fixes = sorted(t for t in runs if category[t] == "bug-fix")
    locates = sorted(t for t in runs if category[t] == "fault-location")
    pairs = [
        (fix.split("-")[0], fix, locate)
        for fix, locate in zip(fixes, locates)
    ]
    assert [name for name, _, _ in pairs] == [
        "allotments", "ferry", "lostproperty", "noticeboard", "paperround",
        "postoffice",
    ]
    for name, fix, locate in pairs:
        assert locate.startswith(name), (fix, locate)

    def run_for(task_id: str, model: str) -> firstparty_v1.Run:
        return runs[task_id] if model == _MODEL else ladder[task_id, model]

    lines = [(
        f"{'defect':<14}"
        + "".join(f"{head:>13}" for head in (
            "haiku cost", "haiku turns", "sonnet cost", "sonnet turns",
            "codex cost", "codex turns"))
    ).rstrip()]
    ratios: dict[str, list[tuple[float, float]]] = {}
    for name, fix, locate in pairs:
        cells = []
        for model in (_HAIKU, _SONNET, _MODEL):
            fixed, located = run_for(fix, model), run_for(locate, model)
            both = verdicts[fix, model] and verdicts[locate, model]
            star = "" if both else "*"
            cost = located.cost_usd / fixed.cost_usd
            turns = located.turns / fixed.turns
            cells += [f"{cost:.2f}x{star}", f"{turns:.2f}x{star}"]
            if both:
                ratios.setdefault(model, []).append((cost, turns))
        lines.append((f"{name:<14}" + "".join(f"{c:>13}" for c in cells)).rstrip())

    [quoted] = fenced_blocks(note_section(
        "56. Locating against fixing, with a second harness beside the ladder"
    ))
    assert quoted == "\n".join(lines) + "\n"

    # The reading: every combination cheaper on locating in every pair whose
    # both members resolved, and Codex the first with all six.
    assert [len(ratios[model]) for model in (_HAIKU, _SONNET, _MODEL)] == [4, 5, 6]
    for model, pinned in (
        (_HAIKU, (0.70, 0.93, 0.89)),
        (_SONNET, (0.57, 0.90, 0.72)),
        (_MODEL, (0.59, 0.78, 0.70)),
    ):
        costs = [cost for cost, _ in ratios[model]]
        assert (
            round(min(costs), 2), round(max(costs), 2),
            round(statistics.median(costs), 2),
        ) == pinned, model
        assert max(costs) < 1.0, "no both-resolved pair reached parity"

    read = prose(note_section(
        "56. Locating against fixing, with a second harness beside the ladder"
    ))
    assert (
        "**0.59×–0.78× on cost, median 0.70×**, and 0.47×–0.82× on turns, "
        "median 0.59×"
    ) in read


def test_what_the_round_cannot_say_is_stated_and_is_true_of_the_rows() -> None:
    """Section 57's four refusals, each checked against something.

    Prose is where a record over-claims, so each refusal is anchored: no rung
    because there is one model, no Codex baseline because the calibration view
    reads one agent, no cross-harness turn comparison because a turn is
    counted differently on each side, and no claim about the harness apart
    from the model because a combination is what was swept.
    """
    runs = round_6_runs()
    assert len({run.model for run in runs.values()}) == 1, "one model is not a ladder"
    assert len(agents.CODEX_REASONING_LEVELS) == 1
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _MODEL not in reconcile_v1.LADDER_MODELS

    # Every task the round swept is a control or a frozen baseline member, so
    # no multiplier could be built from these rows even if one were wanted.
    swept = set(runs)
    declared = {
        task.id: task for task in firstparty_v1.load_task_set(_TASKS)
        if task.id in swept
    }
    assert not [task for task in declared.values() if task.construction is not None]

    # A Codex turn: completed items that are not reasoning items. Pinned at
    # the definition, which is what section 57 quotes.
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    turns = [run.turns for run in runs.values()]
    assert sum(turns) == _CODEX_TURNS
    assert (min(turns), max(turns)) == _CODEX_TURN_RANGE

    said = prose(note_section("57. What this round cannot say"))
    assert "**No rung.**" in said
    assert "**No multiplier, and no Codex baseline.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No claim about the harness apart from the model.**" in said
    assert "Round 6's Codex cells ran 6–15 of those, 248 in all" in said


def test_the_expensive_assumption_is_held_by_the_runner_not_by_the_adapter(
) -> None:
    """Section 57's last paragraph: what the two harnesses were asked.

    The reading dies if the runner introduced an inequality, so each of the
    five things the section lists as held equal is checked where it is held.
    Four of them live in one place — the runner hands the adapter a prompt, a
    prepared workdir and a limit, and takes the diff back — and the fifth is
    the grant, which is the one thing each adapter spells for itself and the
    reason the argv assertions exist.
    """
    prompt = "one prompt, both harnesses"
    argv = agents.codex_argv(prompt, _MODEL)
    assert argv[-1] == prompt, "the prompt is passed through, not rewritten"
    assert argv[argv.index("-m") + 1] == _MODEL
    assert argv[argv.index("-c") + 1] == "model_reasoning_effort=medium"
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert "--ignore-user-config" in argv
    assert not {"-s", "--sandbox", "--approve-for-me"} & set(argv)

    # claude-code's side of the same two stances. Its command is built inside
    # the function that runs it rather than by an argv helper, so it is read
    # at the source here; the runtime argv assertion for it is
    # `tests/test_firstparty_v1.py`'s, against a fake `claude` on PATH.
    built = inspect.getsource(firstparty.claude_headless_json)
    assert '"--setting-sources", ""' in built
    assert '"--permission-mode", "bypassPermissions"' in built

    # The limit is the task's, not the invocation's and not the harness's: the
    # adapter is handed one and has no way to ask for another.
    swept = {
        task.id: task for task in firstparty_v1.load_task_set(_TASKS)
        if task.id in set(round_6_runs())
    }
    assert {firstparty_v1.live_run_limit_s(task) for task in swept.values()} == {600}

    said = prose(note_section("57. What this round cannot say"))
    assert "**the same prompt bytes**" in said
    assert "**the same grant**" in said
    assert "**the same grading**" in said
    assert "**What stands against the failure mode is the live seam's argv assertions**" in said


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 58's verification, run rather than remembered.

    Each of the two logs is replayed into a scratch dataset of its own, and
    both into one merged dataset. The two per-log datasets together have to be
    the merged one record for record: no row missing, none duplicated, no
    field differing. Every record also has to carry its log row's own
    measurements, because replay re-grades the diff and never re-runs the
    agent — which for a Codex row is the whole of the claim that a
    table-derived cost is never recomputed on the way through.
    """
    per_log: list[dict[str, object]] = []
    merged_path = tmp_path / "merged.jsonl"
    for name in _LOG_NAMES:
        log = _LOGS / name
        alone = tmp_path / name
        for data in (alone, merged_path):
            main(["eval-v1", "--tasks", str(_TASKS), "--replay", str(log),
                  "--data", str(data)])
        printed = capsys.readouterr().out
        evaluated, resolved = _REPLAYED[name]
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed
        per_log.extend(
            json.loads(line) for line in alone.read_text().splitlines() if line.strip()
        )

    merged = [
        json.loads(line)
        for line in merged_path.read_text().splitlines()
        if line.strip()
    ]
    assert len(merged) == 30

    def cell(record: dict[str, object]) -> tuple[str, str]:
        return str(record["instance_id"]), str(record["model"])

    assert sorted(per_log, key=cell) == sorted(merged, key=cell)

    runs = round_6_runs()
    for record in merged:
        run = runs[str(record["instance_id"])]
        assert record["model"] == _MODEL
        assert record["agent"] == _AGENT
        assert record["cost_usd"] == run.cost_usd
        assert record["turns"] == run.turns
        assert record["tokens_in"] == run.tokens_in
        assert record["tokens_out"] == run.tokens_out
        assert record["latency_s"] == run.latency_s
        assert record["agent_version"] == run.agent_version
        assert record["as_of"] == run.as_of.isoformat()
        assert record["benchmark"] == "first-party-v1"

    # The commands the note prints, against the two logs they name.
    printed_block = fenced_blocks(note_section(
        "58. Replay, and the published tables left where they were"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert f"--replay data/first-party-v1-runs/{name}" in printed_block
        assert (
            f"  evaluated {evaluated} runs over {_TASKS_AS_RECORDED} tasks "
            f"({resolved} resolved)"
        ) in printed_block
        assert len(firstparty_v1.load_runs(_LOGS / name)) == evaluated, name


def test_neither_reader_counts_a_codex_row(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 58's second claim: the published tables, provably unmoved.

    The Codex rows are in the same directory both readers are pointed at, so
    "unmoved" has to mean read-and-dropped rather than absent. That is checked
    at the seam — selecting `claude-code` over every log drops every one of the
    round's thirty rows — and then in what the readers print: reconcile's run
    count and round list, and calibrate's baselines for the categories rounds
    3, 4 and 5 published, over a directory that now also holds thirty
    `gpt-5.6-terra` rows.

    The printed totals are no longer the ones section 58 published, and the
    reason is not this round: rounds 8, 10, 11 and 12 each swept six claude-code
    Python rows, which survive both selections. Section 58's claim is about
    round 6's rows and it still holds exactly; the later rounds' arrivals are
    named in the body rather than written back into a record of what the
    readers printed that day.
    """
    everything = [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    ]
    # Since section 58 was pinned, five rounds have added rows to the same
    # directory: round 7's forty-two — twenty-eight claude-code TypeScript ones
    # and fourteen more Codex ones — round 8's nine, six of them claude-code
    # *Python* ones, round 10's nine of the same shape (its sweep landed
    # 2026-08-24), round 11's nine of it again (2026-08-26), and round 12's
    # nine (2026-08-28). Section 58's own claim is unchanged and is what this
    # test checks: agent selection drops every round-6 row. What has moved is
    # the printed total, because round 8's six, round 10's six, round 11's
    # six and round 12's six survive both
    # selections where round 7's twenty-eight did not. That is those rounds'
    # truth, pinned in their own suites and named here rather than edited into
    # a record of what round 6 printed on the day.
    assert len(everything) == _CLAUDE_CODE_RUNS + 30 + 42 + 9 + 9 + 9 + 9
    assert len([run for run in everything if run.sweep == _SWEEP]) == 30
    selected = reconcile_v1.select_agent(
        everything, firstparty.CLAUDE_CODE, explicit=False
    )
    assert not [run for run in selected if run.sweep == _SWEEP]
    declared = list(firstparty_v1.load_task_set(_TASKS))
    selected = reconcile_v1.select_language(
        declared, selected, reconcile_v1.DEFAULT_LANGUAGE, explicit=False
    )
    assert len(selected) == (
        _CLAUDE_CODE_RUNS + _ROUND_8_CLAUDE_CODE_RUNS
        + _ROUND_10_CLAUDE_CODE_RUNS + _ROUND_11_CLAUDE_CODE_RUNS
        + _ROUND_12_CLAUDE_CODE_RUNS
    )
    assert not [run for run in selected if run.sweep == _SWEEP]

    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    assert (
        f"  runs       "
        f"{_CLAUDE_CODE_RUNS + _ROUND_8_CLAUDE_CODE_RUNS + _ROUND_10_CLAUDE_CODE_RUNS + _ROUND_11_CLAUDE_CODE_RUNS + _ROUND_12_CLAUDE_CODE_RUNS}"
        f" over "
        f"{_TASKS_THE_RUNS_MENTION + _ROUND_8_TASKS + _ROUND_10_TASKS + _ROUND_11_TASKS + _ROUND_12_TASKS} "
        "task(s)"
    ) in reconciled
    # `sweep round-10` joined the round list when its sweep landed, and
    # `sweep round-11` and `sweep round-12` after it; round 6's rows are
    # still not in it, which is the claim.
    assert (
        "  rounds     10 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10, sweep round-11, sweep round-12"
    ) in reconciled
    assert "sweep round-6" not in reconciled
    assert "sweep round-7" not in reconciled
    # And the Codex logs were read, not skipped: they are named in the
    # provenance list the report prints above those counts.
    for name in _LOG_NAMES:
        assert f"data/first-party-v1-runs/{name}" in reconciled

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    assert _MODEL not in calibrated
    # Rounds 4 and 5's baselines, quoted where those records published them.
    # Round 12's sweep (2026-08-28) re-priced `codebase-comprehension` over
    # seven controls, so §48's block for it is the first of these quotes the
    # table no longer prints. It is named stale here rather than the record
    # being edited; the other quoted blocks still print as published, and
    # the moved category's own suites pin what prints instead.
    for quoted in (
        fenced_blocks(note_section("39. The two new categories' rows, as printed"))
        + fenced_blocks(note_section("48. The two new categories' rows, as printed"))
    ):
        for block in ["category " + rest for rest in quoted.split("\ncategory ")[1:]] or [
            quoted
        ]:
            if block.strip("\n").startswith("category codebase-comprehension"):
                assert counts_written_out(block).strip("\n") not in (
                    counts_written_out(calibrated)
                ), "the moved block is back: round 12's re-pricing was undone"
                continue
            assert counts_written_out(block).strip("\n") in counts_written_out(
                calibrated
            ), (
                "a block an earlier record quoted is no longer what the table "
                "prints:\n" + block
            )

    said = prose(note_section(
        "58. Replay, and the published tables left where they were"
    ))
    assert (
        "**`calibrate-v1` and `reconcile-v1` print for `claude-code` exactly "
        "what they printed before the round.**"
    ) in said
    assert "Six rounds, not seven" in said
    assert (
        "The Codex rows are visibly *read* and provably *not counted*"
    ) in said
