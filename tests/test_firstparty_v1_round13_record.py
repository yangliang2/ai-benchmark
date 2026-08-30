"""Round 13's record, pinned: what sections 119-127 of the design note publish.

The round swept nine cells over **three `performance-optimisation` tasks** —
heap 4's one action, the corpus's last unfilled cell, taken under the
complexity-proxy verdict shape §117.1 ruled and ADR-0006 records — and the
execution scored it **9 of 9**: the first of the corpus's five nine-cell
rounds to resolve every cell. The record's one new reading is the named-side
reading §123 registers — an unresolved cell fails on the behaviour suite or
on the complexity suite, read off the run's own grading — and this round it
had nothing to name, which the record says while reading the cells and never
as a score. The standing temptation is the fraction over assertions — "most
of the bounds met" — which ADR-0004 refused for mutants, ADR-0005 for points
and ADR-0006 inherits, so this file checks that no fraction over assertions
is quoted as a quality figure anywhere in the round's own sections, and —
§118.3's prohibition — that **no wall-clock figure appears** anywhere in
them: the only number-with-a-time-unit the nine sections may carry is the
registered 600 s limit.

Every figure is re-derived from the artifact that earned it: the checked-in
run logs (collected wholesale, selected by **sweep id `round-13`** and never
by a log's filename — the sweep protocol's rule), the tasks' own held-out
suites re-run over each logged diff, the lint's printed coverage table and
the readers' actual output. The design note's own tables are rebuilt from
those artifacts and compared whole, and each section is sliced **from its own
heading to the next heading** — never to `## Open questions` or any landmark
further down, the rule `docs/agents/runbook-grader-v2-gate.md:153` writes
down.

**Everything here is offline and no grader client is constructed — and,
unlike every record suite since round 9, there is nothing here for §80.5's
freezing line to freeze.** No test in this file reaches the live
`point_grader.GRADER_VERSION`, the prompt template or the span rule, because
the round's verdicts were computed by execution and no grader version exists
in their provenance: every verdict below is recomputed by running the two
held-out suites over the collected diff, replay is handed no factory by
construction, no rulings archive exists for any cell, and
`point_grader.deepseek_point_grader` is replaced by a detonator for the whole
module, so a construction anywhere in this file is a failure rather than a
silent live call.
"""

import json
import platform
import re
from pathlib import Path
from typing import Iterator

import pytest
import sweep_census
from note_reading import NOTE, REGISTER_LINE, fenced_blocks, prose, section

from ai_benchmark import (
    agents,
    firstparty,
    firstparty_v1,
    point_grader,
    pricing,
    reconcile_v1,
)
from ai_benchmark.cli import main
from ai_benchmark.schema import TaskCategory

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_RULINGS = _REPO / "data" / "first-party-v1-rulings"
_UNIFIED = _REPO / "data" / "unified.jsonl"
_CONTEXT = _REPO / "CONTEXT.md"
_RUNBOOK = _REPO / "docs" / "agents" / "runbook-round-13-sweep.md"

_SWEEP = "round-13"
_ANCHOR = "round-12"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-29"
_CATEGORY: TaskCategory = "performance-optimisation"

# The versions the rows carry — and this round crosses no version boundary:
# both harness versions are round 12's exactly, the second consecutive round
# with nothing to narrate, which §119 says in as many words.
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.246 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}

# The four logs the sweep's four invocations wrote, and what each replays to.
# Named only so that section 127's replay can be given one log at a time;
# nothing here selects runs by them.
_REPLAYED = {
    "2026-08-29-r13-a.jsonl": (1, 1),
    "2026-08-29-r13-b.jsonl": (2, 2),
    "2026-08-29-r13-c.jsonl": (3, 3),
    "2026-08-29-r13-d.jsonl": (3, 3),
}
_DRY_CELL = "cooperage-keep-the-quoting-quick-as-the-book-grows"
_CHEAPEST_CELL = "cloakroom-keep-the-handing-back-quick-as-the-queue-grows"

# Section 121's sweep spend, per combination and per cost source, and the
# registered range it is read against. This round the range was met — the
# total sits inside §118.11's band, just above its floor — so the assertions
# below hold the landing to that, not to a miss.
_SPEND = {_HAIKU: 0.1950, _SONNET: 0.4823, _TERRA: 0.2285}
_BILLED = 0.6772
_TOTAL = 0.9058
_PER_CELL = {_HAIKU: 0.0650, _SONNET: 0.1608, _TERRA: 0.0762}
_REGISTERED_RANGE = (0.9, 2.8)
_ABOVE_THE_FLOOR = 0.0058
_FLAT_EXTRAPOLATION = 0.9183
_FLAT_EXTRAPOLATION_RATIO = 0.99
_UNDER_THE_ANCHOR = 0.0126
_PER_TASK = 0.3019
_ANCHOR_PER_TASK = 0.3061
_ANCHOR_COLUMN = {_HAIKU: 0.2113, _SONNET: 0.4543, _TERRA: 0.2529}
_ANCHOR_PER_CELL = {_HAIKU: 0.0704, _SONNET: 0.1514, _TERRA: 0.0843}
_COLUMN_RATIO = {_HAIKU: 0.92, _SONNET: 1.06, _TERRA: 0.90}

# Section 121's token evidence: the two claude columns read more and wrote
# less than round 12's explain cells — the code-change-plus-tests loop — while
# the Codex column read and wrote *less* on both axes and still landed at
# 0.90x, kept apart from the action signature rather than merged with it.
_TOKENS_PER_CELL = {
    _HAIKU: (233_669, 3_419),
    _SONNET: (371_637, 3_134),
}
_ANCHOR_TOKENS_PER_CELL = {
    _HAIKU: (142_724, 5_259),
    _SONNET: (172_814, 5_044),
}

# Section 121's Codex bounds at the round's own tokens, and the effective rate.
_CODEX_TOKENS = (358_132, 6_128)
_ALL_CACHED = 0.1452
_ALL_UNCACHED = 0.7898
_EFFECTIVE_RATE = 0.4328
_ANCHOR_EFFECTIVE_RATE = 0.4385
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 119's resolution line: every cell of the round.
_RESOLVED = {_HAIKU: 3, _SONNET: 3, _TERRA: 3}

# Section 119's limits paragraph — a registered bound, never a reading.
_LIMIT_S = 600
_PYTHON_VERSION = "3.14.4"

# Section 122's turn line, quoted so section 126's refusal has an anchor.
_TURNS = {_HAIKU: 26, _SONNET: 31, _TERRA: 28}
_TURN_RANGE = {_HAIKU: (7, 11), _SONNET: (9, 12), _TERRA: (7, 11)}

# Section 127's archive line: the free-text archive across thirteen sweeps,
# and the registered split the A″ readings stay computed over.
_ARCHIVE_BEFORE = 333
_ARCHIVE_NOW = 342
_STRATUM_A = 63

# Section 124's two changed zero-exemplar sentences, quoted in the record and
# pinned here as the checked-in text they are — the cascade §117.6 named in
# advance, landed at the first task's landing with no authorable successor
# category to re-point at.
_DOCSTRING_SENTENCE = (
    "`performance-optimisation` read zero until round 13 filled its Python "
    "cell — the last authorable zero row, so the series above ends with no "
    '"today" exemplar left: the one `- - 0` row still printed is '
    "`unclassified`'s, permanent and structural, because the loader refuses "
    "any task declaring that category"
)
_CONTEXT_SENTENCE = (
    "and `performance-optimisation` was one until round 13 filled its Python "
    "cell — the last authorable zero row, so the only `0` row still printed "
    "is **unclassified**'s, permanent and structural because the loader "
    "refuses any task declaring that category"
)


@pytest.fixture(scope="module", autouse=True)
def no_grader_can_be_built() -> Iterator[None]:
    """The offline claim, made structural for the whole module.

    §127 says the round's rows replay with the network unplugged, no grader
    client constructed and no rulings archive read — this round because there
    is none to read. Nothing below should reach the one factory there is, so
    the factory is replaced by a detonator: a construction anywhere in this
    file fails the suite instead of quietly asking for a key.
    """
    original = point_grader.deepseek_point_grader

    def refuse() -> point_grader.PointGrader:
        raise AssertionError(
            "the round-13 record is a recomputation by execution — this "
            "suite builds no grader client and makes no paid call"
        )

    point_grader.deepseek_point_grader = refuse
    try:
        yield
    finally:
        point_grader.deepseek_point_grader = original


def record_sections() -> list[str]:
    """The record's own sections, by heading, in order."""
    return [
        "119. What the round measured",
        "120. The gate opened: both pristine invariants, over all three "
        "tasks",
        "121. Spend, by cost source, against the one registered range",
        "122. The nine cells under three combinations",
        "123. What the shape bought, and the reading it refuses",
        "124. The coverage table, as the lint prints it",
        "125. The machinery, recorded as landed",
        "126. What this round cannot say",
        "127. Replay, the readers, and heap 4 closed",
    ]


def registered_cells() -> list[str]:
    """§118.10's filled register, read back out of the pre-registration, so
    what the round swept is compared against the register itself and never a
    copy."""
    for block in fenced_blocks(
        section("## Round 13 cells and cost — registered 2026-08-29")
    ):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        matched = [
            match for line in lines if (match := REGISTER_LINE.fullmatch(line))
        ]
        if len(matched) == len(lines) and all(
            match.group(2) for match in matched
        ):
            return [match.group(1) for match in matched]
    raise AssertionError("§118.10's filled register is not in the note")


def tasks_in_set() -> int:
    """How many tasks the checked-in set holds, as `eval-v1` counts them —
    derived rather than pinned, because a later round authoring a task moves
    the replay block's `over N tasks` and this has to move with it."""
    return len(firstparty_v1.load_task_set(_TASKS))


def complexity_paths(task: firstparty_v1.Task) -> list[str]:
    """The structural half of a split task's suite: everything in `grading/`
    that is not a named behaviour test — for this category, the complexity
    suite."""
    return sorted(
        set(task.grading_test_paths) - set(task.behaviour_test_paths)
    )


@pytest.fixture(scope="module")
def round_13(
    runs: list[firstparty_v1.Run],
) -> dict[tuple[str, str], firstparty_v1.Run]:
    """The round's nine rows, keyed task x model, selected by sweep id."""
    swept = {
        (run.task_id, run.model): run for run in runs if run.sweep == _SWEEP
    }
    assert len(swept) == 9, "the round is nine cells, none repeated"
    return swept


@pytest.fixture(scope="module")
def verdicts(
    tasks: dict[str, firstparty_v1.Task],
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> dict[tuple[str, str], tuple[bool, bool, bool]]:
    """Every cell's verdict and its two named sides, recomputed by execution
    from the logged diff — the very computation replay runs, with no grader,
    no factory and no archive anywhere.

    The verdict is taken from `grade` — the shipped gate — and the two sides
    beside it re-run the same suites through `_run_grading`, so this is a
    reading of the one grading pipeline and not a second one that happens to
    agree with it. §123's named-side reading is what the triple carries: the
    behaviour suite (correctness unchanged) and the complexity suite (the
    bound met), and `resolved` is both passing. And the round's structural
    negative is asserted per cell: **no rulings archive exists for any of the
    nine** — the verdict is execution, not an instrument's ruling.
    """
    derived: dict[tuple[str, str], tuple[bool, bool, bool]] = {}
    for (task_id, model), run in sorted(round_13.items()):
        task = tasks[task_id]
        assert task.behaviour_test_paths, "the split names the behaviour half"
        assert complexity_paths(task), "and the complexity half is the rest"
        verdict = firstparty_v1.grade(task, run.diff)
        behaviour = firstparty_v1._run_grading(
            task, run.diff, task.behaviour_test_paths,
            timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
        )
        complexity = firstparty_v1._run_grading(
            task, run.diff, complexity_paths(task),
            timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
        )
        assert verdict == (behaviour and complexity), (task_id, model)
        assert not firstparty_v1.rulings_file(
            _RULINGS, task_id, run.agent, model
        ).is_file(), (
            f"{task_id} x {model}: no rulings archive — the verdict is "
            "execution"
        )
        derived[(task_id, model)] = (verdict, behaviour, complexity)
    return derived


def cell_table(
    round_13: dict[tuple[str, str], firstparty_v1.Run],
    verdicts: dict[tuple[str, str], tuple[bool, bool, bool]],
) -> str:
    """Section 122's table, rebuilt from the logs and the recomputed verdicts
    — byte for byte, headers and cost sources included."""
    ids = sorted({task_id for task_id, _ in round_13})
    width = max(len(task_id) for task_id in ids)
    lines = [
        (" " * (width + 2) + "  ".join(f"{cell:<18}" for cell in row)).rstrip()
        for row in (
            ("claude-code x", "claude-code x", "codex x"),
            (_HAIKU, _SONNET, _TERRA),
            ("vendor-reported", "vendor-reported", "table-derived"),
        )
    ]
    for task_id in ids:
        columns = []
        for _, model in _COMBINATIONS:
            verdict = (
                "resolved  " if verdicts[task_id, model][0] else "unresolved"
            )
            columns.append(f"{verdict} ${round_13[task_id, model].cost_usd:.4f}")
        lines.append(
            (f"{task_id:<{width}}  "
             + "  ".join(f"{column:<18}" for column in columns)).rstrip()
        )
    return "\n".join(lines) + "\n"


def test_the_round_swept_exactly_the_cells_that_were_registered(
    tasks: dict[str, firstparty_v1.Task],
    runs: list[firstparty_v1.Run],
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 119's sweep facts, off the rows themselves, against §118.10.

    The register is read out of the pre-registration rather than restated.
    One sweep id, one as-of date, one version per harness — and this round
    crosses no version boundary at all: both versions are round 12's exactly,
    checked against round 12's own rows rather than against a memory of them.
    """
    assert {run.sweep for run in round_13.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in round_13.values()} == {_AS_OF}
    assert {
        (run.agent, run.model) for run in round_13.values()
    } == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version
            for run in round_13.values()
            if run.agent == agent
        } == {version}, agent

    # No boundary: round 12's rows carry the same two versions, read off the
    # rows themselves rather than quoted from §108.
    round_12 = [run for run in runs if run.sweep == _ANCHOR]
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version for run in round_12 if run.agent == agent
        } == {version}, f"{agent}: no version boundary this round"

    registered = registered_cells()
    assert len(registered) == 3 == len(set(registered))
    assert {task_id for task_id, _ in round_13} == set(registered)
    assert {tasks[task_id].category for task_id in registered} == {_CATEGORY}
    assert {tasks[task_id].language for task_id in registered} == {"python"}
    assert {tasks[task_id].surface for task_id in registered} == {"application"}
    assert all(tasks[task_id].control for task_id in registered)
    assert set(registered) == {
        task.id
        for task in tasks.values()
        if task.category == _CATEGORY
    }, "every performance-optimisation task the corpus holds"

    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(section("### 119. What the round measured"))
    assert (
        "**Nine cells, and they are exactly the nine §118.10 registered.**"
    ) in measured
    assert "**9 of 9**" in measured
    assert "**heap 4's one action's cells**" in measured
    assert "**complexity-proxy verdict shape**" in measured
    assert "`resolved` being **both suites passing**" in measured
    assert "**no grader in the verdict path**" in measured
    assert "no rulings archive exists for any of the nine" in measured
    assert (
        "first round since round 9 whose verdict path spent no grader dollar"
    ) in measured
    assert "**no second quality metric enters the table**" in measured
    assert "**crosses no version boundary**" in measured
    assert "**2.1.246**, rounds 11 and 12's exactly" in measured
    assert (
        "**codex-cli 0.147.0**, rounds 6, 7, 8, 10, 11 and 12's exactly"
    ) in measured
    assert "the second consecutive round with no boundary" in measured


def test_the_dry_cell_and_the_four_logs_are_what_the_record_says(
    round_13: dict[tuple[str, str], firstparty_v1.Run],
    verdicts: dict[tuple[str, str], tuple[bool, bool, bool]],
) -> None:
    """Section 119's invocation paragraph, against the checked-in logs.

    The dry cell was one of the nine, run alone in its own invocation, graded
    alone before the other eight, and its verdict is the new shape's first
    paid verdict: resolved, both held-out suites passing on the collected
    diff — the verdict shape arriving well-formed. The registration's word
    "cheapest" is checked against what the rows actually cost: this round the
    column half of the reading held and the cell half did not, which the
    record says rather than passes over.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 9
    assert min(counted.values()) > 0, "no invocation of this round logged nothing"

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-29-r13-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    verdict, behaviour, complexity = verdicts[_DRY_CELL, _HAIKU]
    assert verdict and behaviour and complexity, (
        "the shape's first paid verdict: resolved, both suites passing"
    )

    by_log = {
        name: {
            (run.task_id, run.model)
            for run in firstparty_v1.load_runs(_LOGS / name)
        }
        for name in _REPLAYED
    }
    assert len(set().union(*by_log.values())) == 9
    assert sum(len(cells) for cells in by_log.values()) == 9

    # "Cheapest" held of the column and not of the cell: the haiku column was
    # the cheaper per cell, but the dry cell itself was haiku's dearest and
    # the round's cheapest cell was the cloakroom on haiku.
    assert _PER_CELL[_HAIKU] < _PER_CELL[_TERRA]
    cheapest = min(round_13.items(), key=lambda item: item[1].cost_usd)
    assert cheapest[0] == (_CHEAPEST_CELL, _HAIKU)
    assert round(cheapest[1].cost_usd, 4) == 0.0534
    assert round(round_13[_DRY_CELL, _HAIKU].cost_usd, 4) == 0.0833
    assert round_13[_DRY_CELL, _HAIKU].cost_usd == max(
        run.cost_usd for key, run in round_13.items() if key[1] == _HAIKU
    ), "the dry cell was the dearest of haiku's three"

    measured = prose(section("### 119. What the round measured"))
    assert "**Four invocations, four logs, none of them empty.**" in measured
    assert "**graded alone before the other eight**" in measured
    assert (
        "**resolved**, both held-out suites passing on the collected diff"
    ) in measured
    assert "the verdict shape arriving well-formed" in measured
    assert "**$0.0650** a cell against Codex's **$0.0762**" in measured
    assert "the dry cell itself cost **$0.0833**" in measured
    assert "`cloakroom` on haiku at **$0.0534**" in measured
    assert "held of the column and not of the cell" in measured


def test_the_gate_opened_on_all_three_tasks_before_the_first_sweep_dollar(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 120: the round's one gate, recomputed from the corpus by
    execution.

    §118.4's quantifier, checked as a quantifier: for every one of the three
    tasks, the whole grading suite does not pass on the pristine repository
    and the named behaviour half does — through the very `grade` and
    `_run_grading` a run is graded by. The complexity half's failure on
    pristine is re-derived too: the slow start is real, which is what makes
    §118.5's refusal of an already-satisfied proxy mechanical. Both invariant
    messages the record quotes are checked against the live lint source.
    """
    registered = registered_cells()
    for task_id in registered:
        task = tasks[task_id]
        assert firstparty_v1.grade(task, "") is False, (
            f"{task_id}: the whole grading suite must not pass on pristine"
        )
        assert firstparty_v1._run_grading(
            task, "", task.behaviour_test_paths,
            timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
        ) is True, f"{task_id}: the behaviour half must pass on pristine"
        assert firstparty_v1._run_grading(
            task, "", complexity_paths(task),
            timeout_s=firstparty_v1.GRADE_TIMEOUT_S,
        ) is False, f"{task_id}: the complexity half fails on the start"

    # Both quoted messages are the live lint's own, read out of the source.
    source = " ".join(
        (_REPO / "src" / "ai_benchmark" / "firstparty_v1.py")
        .read_text(encoding="utf-8")
        .split()
    )
    assert hasattr(firstparty_v1, "lint_task_set")

    certified = prose(section(
        "### 120. The gate opened: both pristine invariants, over all three "
        "tasks"
    ))
    assert (
        "**The round's one hard gate was read before the first sweep dollar, "
        "and it opened.**"
    ) in certified
    assert "the only gate round 13 has" in certified
    assert (
        "for **every one of the three `performance-optimisation` tasks**, "
        "the **whole grading suite did not pass** on the pristine repository, "
        "and the **named behaviour half did pass** on it"
    ) in certified
    assert (
        "every task, both invariants, no fraction met, no proportion "
        "computed, no threshold anywhere in the clause"
    ) in certified
    assert "the failing half is the complexity suite" in certified
    assert "§118.5's refusal made mechanical" in certified
    assert (
        "**Both invariants are the lint's own, and neither was added for "
        "this round.**"
    ) in certified
    for message in (
        "the grading tests already pass on the pristine repo — there is "
        "nothing left for an agent to do",
        "the behaviour tests fail on the pristine repo — a refactor or "
        "performance-optimisation task must start from behaviour that "
        "already works",
    ):
        assert f'"{message}"' in certified, message
        assert message.split(" — ")[0] in source, message
    assert "**standing machinery**" in certified
    assert (
        "no proofs archive, no foil, no grader call and no LLM anywhere in "
        "its path"
    ) in certified
    assert "read for nothing, offline, as often as anyone likes" in certified
    assert (
        "The kill discipline's one standing sentence was never needed"
    ) in certified
    assert "`performance-optimisation` opened instead of staying absent" in certified


def test_the_sweep_cost_what_the_record_states_by_cost_source(
    runs: list[firstparty_v1.Run],
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 121's sweep spend, pinned per cost source and per cell, and
    the registered range it landed inside.

    The landing is the point this round: §118.11 registered $0.9-2.8 with
    both miss directions pre-read, and neither arrived — the total sits
    inside the band, $0.0058 above its floor and under the anchor's own
    landed total, so the anchor's honest caveat (a perf cell may run longer
    and dearer than an explain cell) is asserted *not* to have priced in,
    with the per-cell token evidence re-derived beside it and the Codex cache
    reading kept separate.
    """
    ids = sorted({task_id for task_id, _ in round_13})
    for model, spend in _SPEND.items():
        actual = sum(round_13[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 3, 4) == _PER_CELL[model], model
        assert round(
            actual / _ANCHOR_COLUMN[model], 2
        ) == _COLUMN_RATIO[model], model

    # The anchor's own columns, re-derived from the round-12 rows by sweep id
    # so the comparison never rests on a retyped figure.
    anchor_rows = [run for run in runs if run.sweep == _ANCHOR]
    assert len(anchor_rows) == 9
    for model, column in _ANCHOR_COLUMN.items():
        actual = sum(run.cost_usd for run in anchor_rows if run.model == model)
        assert round(actual, 4) == column, model
        assert round(actual / 3, 4) == _ANCHOR_PER_CELL[model], model
    assert round(sum(_ANCHOR_PER_CELL.values()), 4) == _ANCHOR_PER_TASK
    assert round(_ANCHOR_PER_CELL[_HAIKU] * 3, 4) == 0.2112
    assert round(_ANCHOR_PER_CELL[_SONNET] * 3, 4) == 0.4542

    billed = sum(
        run.cost_usd
        for run in round_13.values()
        if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED
    total = sum(run.cost_usd for run in round_13.values())
    assert round(total, 4) == _TOTAL
    # Summed before rounding — and this round the printed columns add to the
    # same rounded total: round 8's situation rather than round 7's, which
    # the record says rather than leaves to a checker.
    assert round(sum(_SPEND.values()), 4) == _TOTAL

    low, high = _REGISTERED_RANGE
    assert low < total < high, "inside the registered band"
    assert round(total - low, 4) == _ABOVE_THE_FLOOR
    assert round(total / _FLAT_EXTRAPOLATION, 2) == _FLAT_EXTRAPOLATION_RATIO
    anchor_total = sum(run.cost_usd for run in anchor_rows)
    assert round(anchor_total, 4) == 0.9184
    assert round(anchor_total - total, 4) == _UNDER_THE_ANCHOR
    assert round(total / 3, 4) == _PER_TASK
    assert _PER_TASK < _ANCHOR_PER_TASK, (
        "the anchor's caveat did not price in: an optimisation cost a hair "
        "less than an explanation"
    )

    # The token evidence, per cell, against round 12's — both re-derived.
    for model, (tokens_in, tokens_out) in _TOKENS_PER_CELL.items():
        assert round(sum(
            run.tokens_in for key, run in round_13.items() if key[1] == model
        ) / 3) == tokens_in, model
        assert round(sum(
            run.tokens_out for key, run in round_13.items() if key[1] == model
        ) / 3) == tokens_out, model
    for model, (tokens_in, tokens_out) in _ANCHOR_TOKENS_PER_CELL.items():
        rows = [run for run in anchor_rows if run.model == model]
        assert round(sum(run.tokens_in for run in rows) / 3) == tokens_in
        assert round(sum(run.tokens_out for run in rows) / 3) == tokens_out
    # Read more, wrote less — both claude columns; the Codex column read and
    # wrote *less* than round 12's on both axes and is kept separate.
    for model in (_HAIKU, _SONNET):
        assert _TOKENS_PER_CELL[model][0] > _ANCHOR_TOKENS_PER_CELL[model][0]
        assert _TOKENS_PER_CELL[model][1] < _ANCHOR_TOKENS_PER_CELL[model][1]

    # Cost sources, on the rows and refused at load if contradicted.
    codex = {k: run for k, run in round_13.items() if run.agent == "codex"}
    claude = {
        k: run
        for k, run in round_13.items()
        if run.agent == firstparty.CLAUDE_CODE
    }
    assert (len(codex), len(claude)) == (3, 6)
    assert {run.cost_source for run in codex.values()} == {"table-derived"}
    assert {run.price_table for run in codex.values()} == {_PRICE_TABLE}
    assert {run.cost_source for run in claude.values()} == {"vendor-reported"}
    assert {run.price_table for run in claude.values()} == {None}

    # The Codex bounds a reader can recompute, and the rate between them —
    # against round 12's rate, itself re-derived from the anchor rows.
    tokens_in_total = sum(run.tokens_in for run in codex.values())
    tokens_out_total = sum(run.tokens_out for run in codex.values())
    assert (tokens_in_total, tokens_out_total) == _CODEX_TOKENS
    anchor_codex = [run for run in anchor_rows if run.agent == "codex"]
    assert sum(run.tokens_in for run in anchor_codex) == 361_796
    assert sum(run.tokens_out for run in anchor_codex) == 7_851
    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    assert table.version == _PRICE_TABLE
    prices = table.models[_TERRA]
    output_cost = tokens_out_total * prices.output_per_token
    cached = tokens_in_total * prices.input_cached_per_token + output_cost
    uncached = tokens_in_total * prices.input_uncached_per_token + output_cost
    assert round(cached, 4) == _ALL_CACHED
    assert round(uncached, 4) == _ALL_UNCACHED
    logged = sum(run.cost_usd for run in codex.values())
    assert cached < logged < uncached
    effective = (logged - output_cost) / tokens_in_total
    assert round(effective * 1e6, 4) == _EFFECTIVE_RATE
    anchor_logged = sum(run.cost_usd for run in anchor_codex)
    anchor_effective = (
        anchor_logged - 7_851 * prices.output_per_token
    ) / 361_796
    assert round(anchor_effective * 1e6, 4) == _ANCHOR_EFFECTIVE_RATE
    assert _EFFECTIVE_RATE < _ANCHOR_EFFECTIVE_RATE

    read = prose(section(
        "### 121. Spend, by cost source, against the one registered range"
    ))
    assert (
        "**The registered sweep range was $0.9–2.8. The round came to "
        "$0.9058, inside the band and $0.0058 above its floor**"
    ) in read
    assert "at **0.99×** the flat extrapolation ($0.9183)" in read
    assert "**$0.0126 under** round 12's own landed $0.9184" in read
    assert "**summed before rounding**" in read
    assert (
        "the printed columns add to the same $0.9058 — round 8's situation "
        "rather than round 7's"
    ) in read
    assert "**Neither of §118.11's pre-read misses arrived**" in read
    assert "**$0.3019 a task** where round 12's three explanations cost $0.3061" in read
    assert (
        "**the anchor's honest caveat — that a perf cell makes a real code "
        "change and runs tests and may run longer and dearer than an explain "
        "cell — did not price in**"
    ) in read
    assert "the $2.8 stop was never approached" in read
    assert "**What the account was actually billed for the sweep: $0.6772" in read
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read
    assert (
        "**There is no third cost source this round, because there was no "
        "metered call of any kind**"
    ) in read
    assert "**No grader spend is reported because none was made**" in read
    assert "**0.92×**, **1.06×** and **0.90×** round 12's" in read
    assert "haiku read **233,669** input tokens a cell" in read
    assert "sonnet read **371,637** against 172,814" in read
    assert "writes a diff, which is shorter than an essay" in read
    assert "which this record does not claim to separate" in read
    assert "read **358,132** input tokens and wrote **6,128**" in read
    assert "**$0.1452 all-cached** and **$0.7898 all-uncached**" in read
    assert "**$0.4328/M**" in read and "**$0.4385/M**" in read
    assert "a seventh point on one rate" in read
    assert "still not a separated cause" in read
    assert "**no new registration is opened**" in read

    blocks = fenced_blocks(section(
        "### 121. Spend, by cost source, against the one registered range"
    ))
    assert blocks[0] == (
        "claude-code x haiku     $0.1950  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $0.4823  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $0.2285  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )
    for line in (
        "claude-code x haiku     $0.2112                $0.1950    $0.0650    $0.0704",
        "claude-code x sonnet    $0.4542                $0.4823    $0.1608    $0.1514",
        "codex x gpt-5.6-terra   $0.17-$0.82 (~$0.25)   $0.2285    $0.0762    $0.0843",
    ):
        assert line in blocks[1], line


def test_the_payment_path_is_disclosed_by_its_absence() -> None:
    """Section 121's closing disclosure, and the runbook's same stance: no
    key was supplied to any column, no cell was point-graded, and the
    standing session-memory disclosure is not owed by this round."""
    read = prose(section(
        "### 121. Spend, by cost source, against the one registered range"
    ))
    assert "**The payment path, stated by its absence.**" in read
    assert "No `DEEPSEEK_API_KEY` was supplied to any column" in read
    assert "no cell was point-graded" in read
    assert "the round's whole spend is the nine agent runs above" in read
    assert "the owner's ruling of 2026-08-23" in read
    assert "**not owed by this round**" in read
    assert (
        "stays where it was used, in the round-10, round-11 and round-12 "
        "runbooks and records"
    ) in read

    runbook = _RUNBOOK.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY is needed by no column" in runbook
    assert "no grader dollar" in runbook


def test_the_per_cell_table_is_what_the_logs_and_the_execution_say(
    round_13: dict[tuple[str, str], firstparty_v1.Run],
    verdicts: dict[tuple[str, str], tuple[bool, bool, bool]],
) -> None:
    """Section 122's table, rebuilt from the artifacts and compared byte for
    byte — the only pin that cannot drift a cell at a time, headers and cost
    sources included."""
    quoted = fenced_blocks(
        section("### 122. The nine cells under three combinations")
    )[0]
    assert quoted == cell_table(round_13, verdicts)

    resolved = {
        model: sum(
            1
            for (_, run_model), (verdict, _, _) in verdicts.items()
            if run_model == model and verdict
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 9, "every cell of the round"

    measured = prose(section("### 119. What the round measured"))
    assert "**Resolution: 9 of 9.**" in measured
    assert (
        "**3 of 3** on `claude-haiku-4-5`, **3 of 3** on `claude-sonnet-5` "
        "and **3 of 3** on `codex` × `gpt-5.6-terra`"
    ) in measured
    assert (
        "the first of the corpus's five nine-cell rounds (8, 10, 11, 12 and "
        "this one) to resolve all nine"
    ) in measured
    assert "There is no red cell to read" in measured

    said = prose(section("### 122. The nine cells under three combinations"))
    assert "There is no per-category block beside it" in said
    assert "no rate is quoted off it" in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath(
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 122's turn line, and the definition that makes it uncomparable
    across the harness boundary."""
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in round_13.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(section("### 122. The nine cells under three combinations"))
    assert (
        "Haiku took **26** turns over the three (7–11), sonnet **31** "
        "(9–12), Codex **28** (7–11)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_the_shape_bought_sentence_and_the_named_side_reading(
    verdicts: dict[tuple[str, str], tuple[bool, bool, bool]],
) -> None:
    """Section 123: the sentence a future round planner reads, and the
    reading the shape makes possible — which this round had nothing to name,
    re-derived: in every one of the nine cells both suites pass, so there is
    no failed side for the record to have read."""
    for (task_id, model), (verdict, behaviour, complexity) in verdicts.items():
        assert verdict and behaviour and complexity, (task_id, model)

    said = prose(section(
        "### 123. What the shape bought, and the reading it refuses"
    ))
    assert (
        "**The sentence a future round planner reads, asking whether this "
        "shape should carry a second language or a second action.**"
    ) in said
    assert "**binary, execution-verified and replayable offline**" in said
    assert "no network, no client, no key, no archive" in said
    assert (
        "**immune to shared-hardware noise because wall-clock is nowhere in "
        "the path**"
    ) in said
    assert "nothing in it can re-time, so nothing in it can flip on replay" in said
    assert "What the shape cost is authoring, not dollars" in said
    assert '"agent-run prices alone" cashed as registered' in said
    assert (
        "An unresolved cell under this verdict fails on a **named side**"
    ) in said
    assert "the behaviour suite — the change broke correctness" in said
    assert "the complexity suite — the bound was not met" in said
    assert "This round the reading had **nothing to name**" in said
    assert (
        "in every one of the nine both suites pass on the collected diff — "
        "said here while reading the cells, and never as a score"
    ) in said
    assert "**fraction over assertions**" in said
    assert "the kill-rate move ADR-0004 refused for mutants" in said
    assert "ADR-0006 inherits the refusal" in said
    assert (
        "**no wall-clock figure appears anywhere in this record**"
    ) in said
    assert "not a longest run, not a mean" in said


def test_no_fraction_over_assertions_and_no_wall_clock_figure_anywhere() -> None:
    """The two mechanical refusals over the record's own nine sections.

    No fraction over assertions is quoted as a quality figure — no
    percentage, no digit-over-digit ratio, no "N of the bounds" — and no
    wall-clock figure appears anywhere: the only number a time unit follows
    in the whole record is the registered 600 s limit, which is a bound the
    runner enforces and not a reading anyone took.
    """
    fraction = re.compile(
        r"\d+\s*(?:%|/\s*\d)|\d+\s+of\s+(?:the\s+)?(?:bounds|assertions|counters)",
        re.IGNORECASE,
    )
    timed = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|secs?|seconds?|s|minutes?|hours?)\b"
    )
    for heading in record_sections():
        text = section(f"### {heading}")
        assert not fraction.search(text), heading
        assert "coverage rate" not in text, heading
        assert "kill rate" not in text, heading
        readings = set(timed.findall(text))
        assert readings <= {"600"}, (heading, readings)


def test_the_coverage_table_and_the_changed_exemplar_sentences(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 124: the table as the lint prints it, whole, the structural
    zero pinned as the only zero, and the two changed sentences read as
    checked-in text.

    The load-bearing claim is quantified: the last *authorable* zero row is
    gone, and the only `- - 0` row left is `unclassified`'s — pinned
    mechanically as `zeros == {"unclassified"}` off the live table, never as
    "no zero row at all", because the loader makes that row permanent.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))
    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python[_CATEGORY] == 3, "the round's acceptance figure"
    assert sum(python.values()) == 128
    zeros = {row[0] for row in coverage if row[3] == 0}
    assert zeros == {"unclassified"}, (
        "the last authorable zero row is gone; the structural one survives"
    )
    assert ("unclassified", "-", "-", 0) in coverage
    assert not [
        row for row in coverage if row[0] == _CATEGORY and row[2] != "python"
    ], "the non-Python cells are zeros by the absence of their rows"
    # Every authorable category now holds at least one task: every heap swept.
    assert all(count > 0 for category, count in python.items())

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed
    [quoted] = fenced_blocks(
        section("### 124. The coverage table, as the lint prints it")
    )
    for line in quoted.strip("\n").splitlines():
        assert line in printed, line
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  performance-optimisation")
    ] == [["performance-optimisation", "application", "python", "3"]]
    assert "  unclassified               -            -           0" in printed

    said = prose(section("### 124. The coverage table, as the lint prints it"))
    assert (
        "**`performance-optimisation application python 3` is the round's "
        "acceptance figure**"
    ) in said
    assert "the line that read `- - 0` in the table §113 quoted" in said
    assert "**The last authorable zero row is gone" in said
    assert "**`unclassified`'s**" in said
    assert "(`src/ai_benchmark/schema.py:37`)" in said
    assert "`classified_and_split_by_category`" in said
    assert "quantified over **authorable** categories" in said
    assert 'never stated as "the table is zero-row-free"' in said
    assert "the plan-review ruling of 2026-08-29" in said
    assert "**every heap is swept**" in said
    assert "heaps 3 and 4 are Python-only" in said
    assert "zeros **by the absence of their rows**" in said

    # The structural claim's ground, checked against the schema and loader:
    # `unclassified` is a category no task may declare.
    assert "unclassified" in (
        (_REPO / "src" / "ai_benchmark" / "schema.py")
        .read_text(encoding="utf-8")
        .splitlines()[36]
    )

    # The two changed sentences, in the live files and quoted in the record.
    docstring = " ".join((firstparty_v1.coverage_table.__doc__ or "").split())
    assert _DOCSTRING_SENTENCE in docstring
    assert "is one of the categories reading zero today" not in docstring
    context = _CONTEXT.read_text(encoding="utf-8")
    assert _CONTEXT_SENTENCE in context
    assert _DOCSTRING_SENTENCE in said, "quoted as checked-in text"
    assert _CONTEXT_SENTENCE in said, "quoted as checked-in text"
    assert "**changed shape**" in said
    assert "no authorable successor category to point at" in said
    for suite, needle in (
        ("test_firstparty_v1_round7_record.py", "last authorable"),
        ("test_firstparty_v1_round8_record.py", "last authorable"),
        ("test_firstparty_v1_round10_record.py", "until round 13"),
        ("test_firstparty_v1_round12_record.py", "until round 13"),
    ):
        assert needle in (
            _REPO / "tests" / suite
        ).read_text(encoding="utf-8"), suite


def test_the_machinery_is_recorded_as_landed(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 125: each landed clause checked against the code the round
    swept under — the split's two categories, the two registries that gained
    nothing, the one limits entry, ADR-0006 beside its two predecessors, and
    §117.4 recorded forward-only."""
    assert firstparty_v1._SPLIT_CATEGORIES == frozenset(
        {"refactor", _CATEGORY}
    ), "the split admits exactly two categories"
    for task_id in registered_cells():
        task = tasks[task_id]
        assert task.behaviour_test_paths, task_id
        assert complexity_paths(task), task_id

    assert _CATEGORY not in firstparty_v1.EXISTENCE_PROOFS
    assert _CATEGORY not in firstparty_v1._POINT_CATEGORIES
    assert _CATEGORY not in firstparty_v1._POINT_REQUIRED_CATEGORIES
    assert _CATEGORY != firstparty_v1._POINT_OPTIONAL_CATEGORY
    assert _CATEGORY not in firstparty_v1.TERRAIN_EXEMPT_ACTIONS
    assert firstparty_v1._unregistered_proof_form_problems() == []

    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension",
        _CATEGORY,
    }
    assert firstparty_v1.LIVE_RUN_LIMITS_S[_CATEGORY] == _LIMIT_S
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S
    swept = {
        firstparty_v1.live_run_limit_s(task)
        for task in tasks.values()
        if task.category == _CATEGORY
    }
    assert swept == {_LIMIT_S}

    adr = (
        _REPO / "docs" / "adr" / "0006-the-complexity-proxy-verdict-shape.md"
    ).read_text(encoding="utf-8")
    for alternative in (
        "Measured wall-clock", "Point-keyed explain-the-optimisation",
        "hybrid rider",
    ):
        assert alternative in adr, alternative
    for number, slug in (
        ("0004", "the-mutation-gate-verdict-shape"),
        ("0005", "the-point-gate-verdict-shape"),
    ):
        assert (_REPO / "docs" / "adr" / f"{number}-{slug}.md").is_file()

    said = prose(section("### 125. The machinery, recorded as landed"))
    assert "admits **exactly two categories**" in said
    assert "`refactor`, whose it has been since round 3" in said
    assert "(`_SPLIT_CATEGORIES`, `src/ai_benchmark/firstparty_v1.py`)" in said
    assert "that half is the **complexity suite**" in said
    assert "The split's semantics are untouched" in said
    assert "**gained no entry and owes none**" in said
    assert "`_unregistered_proof_form_problems`" in said
    assert "neither refused nor exempt" in said
    assert "**joined no point machinery**" in said
    assert "not `_POINT_CATEGORIES`, no points key, no terrain exemption" in said
    assert "No new subcommand, no new flag" in said
    assert "`performance-optimisation: 600` is the dict's fifth row" in said
    assert "registration, not tuning" in said
    assert "**three rejected alternatives**" in said
    assert "`docs/adr/0006-the-complexity-proxy-verdict-shape.md`" in said
    assert (
        "**And §117.4's disqualifier rule stands registered forward-only.**"
    ) in said
    assert "**this round authored no point key**" in said
    assert (
        "rounds 10, 11 and 12's keys, proofs, records and labels stand as "
        "written"
    ) in said


def test_what_this_round_cannot_say_is_stated_and_true_of_the_corpus(
    tasks: dict[str, firstparty_v1.Task],
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 126's refusals, each anchored to something checkable, and the
    disclosures the ticket wants in as many words: the two narrowings
    (covered growth behaviour is not elegant code; an asserted bound is not a
    measured speedup), the honest-proxy discipline, the transfer gap in its
    standing form, and the owner's ~9 labels — recorded as **not yet given**
    when the record was written, and caught up here to the dated addendum of
    2026-08-30 that gave them: nine of nine agree, recorded exactly as given,
    the way §115's addendum moved this suite's round-12 counterpart."""
    swept = {task_id for task_id, _ in round_13}
    assert all(tasks[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if tasks[task_id].construction is not None
    ]
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS

    said = prose(section("### 126. What this round cannot say"))
    assert (
        "**Covered growth behaviour is not elegant code — the narrowing, in "
        "as many words.**"
    ) in said
    assert "`resolved` is **both suites passing**, and nothing more" in said
    assert (
        "the operation's growth behaviour changed as the held-out counters "
        "demanded and that correctness survived"
    ) in said
    assert "an agent can meet both with a graceless change" in said
    assert (
        "**never as a certificate of code quality beyond its two suites**"
    ) in said

    assert "**An asserted growth bound is not a measured speedup.**" in said
    assert "**no wall-clock was read anywhere**" in said
    assert (
        "nothing in this round says how much faster anything got on any "
        "machine"
    ) in said

    assert (
        "**The honest-proxy rule is an authoring discipline, and no machine "
        "asserts it.**"
    ) in said
    assert "A resolved cell certifies the planted proxy was met" in said
    assert (
        "rests on the authoring and the spec review"
    ) in said
    assert (
        "A dishonest proxy that survived both would grade something else "
        "without any machine saying so"
    ) in said

    assert (
        "**The transfer gap, restated from §79.4, §81.4, §92, §104 and §115 "
        "— and untouched by this round.**"
    ) in said
    assert "This round's verdicts never asked the grader anything" in said
    assert "neither tests the gap nor moves it" in said
    assert "the next point-keyed round is where evidence lands" in said

    # The addendum of 2026-08-30 replaced the not-yet-given form with the
    # given one — §115's addendum is the precedent, and this catch-up is its
    # round-12 counterpart's move made here: the absence assertions retire
    # and the given form is pinned instead, labels block included.
    assert (
        "**The owner's ~9 agree/disagree labels: given 2026-08-30, the day "
        "after this record — nine of nine agree.**"
    ) in said
    assert "§76.2 ruled and §77.2 registered" in said
    assert "the first holistic read of a brand-new verdict shape" in said
    assert "asked for in the orchestrator session" in said
    assert (
        "**formed with the orchestrator's assistance and not by an unaided "
        "read**"
    ) in said
    assert "recommended a label per cell with the borderline cell named" in said
    assert "The labels are recorded exactly as given" in said
    assert "No cell was found to evade its counter" in said
    assert "the label is agree and the choice is recorded" in said
    assert (
        "no false green — no gamed proxy and no behaviour break"
    ) in said
    assert (
        "the nine verdicts stand on their own execution"
    ) in said
    assert "they read execution verdicts, not grader rulings" in said

    # The labels block itself: nine lines, one per registered cell, every one
    # of them agree beside a machine resolved — parsed from the section's own
    # fenced block rather than retyped as a table here.
    label_block = next(
        block
        for block in section("### 126. What this round cannot say").split(
            "```"
        )[1::2]
        if "agree" in block
    )
    label_lines = [line for line in label_block.splitlines() if line.strip()]
    assert len(label_lines) == 9
    for line in label_lines:
        assert "agree     (machine: resolved)" in line
    for task_word in ("cooperage", "cloakroom", "cornexchange"):
        for model_word in ("claude-haiku-4-5", "claude-sonnet-5",
                           "gpt-5.6-terra"):
            assert any(
                task_word in line and model_word in line
                for line in label_lines
            )

    assert "**No cross-action difficulty comparison.**" in said
    assert (
        "9 of 9 here is not to be read against round 12's 7 of 9, round 11's "
        "0 of 9 or round 10's 1 of 9"
    ) in said
    assert "nine cells is not a rate's denominator" in said
    assert (
        "**Nothing about `performance-optimisation` in any non-Python "
        "language.**"
    ) in said
    assert "**No Codex rung.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No multiplier.**" in said
    assert "the controls divided by themselves at **1.00×** on three tasks" in said


def test_the_limits_paragraph_holds_and_quotes_no_reading(
    tasks: dict[str, firstparty_v1.Task],
    round_13: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 119's limits and toolchain paragraphs, against the table the
    runner reads and the interpreter the suite runs on — with the departure
    pinned: no run-time reading is quoted, where every record since §85
    quoted a longest run and a mean."""
    assert firstparty_v1.LIVE_RUN_LIMITS_S[_CATEGORY] == _LIMIT_S
    swept = {task_id for task_id, _ in round_13}
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in tasks.values()
        if task.id in swept
    } == {_LIMIT_S} == {firstparty.RUN_TIMEOUT_S}

    assert platform.python_version() == _PYTHON_VERSION

    measured = prose(section("### 119. What the round measured"))
    assert (
        "**The limits in force: the category's own registered 600 s, every "
        "cell.**"
    ) in measured
    assert "**under the registration the category carries**" in measured
    assert "**no cross-round caveat arises**" in measured
    assert "**never adjusted per cell**" in measured
    assert "**no run-time reading appears here**" in measured
    assert "registered wall-clock out of the round as a prohibition" in measured
    assert "the record carries no measured duration of any kind" in measured
    assert f"Python {_PYTHON_VERSION}" in measured
    assert "**no grader version to quote**" in measured
    assert "GRADER_VERSION" not in section("### 119. What the round measured")


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 127's replay, run rather than remembered — and offline.

    Each of the four logs is replayed into a scratch dataset of its own, and
    all four into one merged dataset; the four together must be the merged
    one, record for record, and every record carries its log row's own
    measurements. The module's detonator fixture is what makes "no grader
    client is constructed" structural, and this round there is nothing for a
    factory to do anyway: `--replay` passes none, no rulings archive exists,
    and every verdict is two held-out suites re-run over the logged diff.
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

    runs = {
        (run.task_id, run.model): run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    }
    for record in merged:
        run = runs[cell(record)]
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
    assert sum(float(record["quality_value"]) for record in merged) == 9

    printed_block = fenced_blocks(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed_block

    said = prose(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))
    assert (
        "**Every round-13 log replays to the verdicts this record quotes, "
        "with the network unplugged — and with no rulings archive, because "
        "there is none.**"
    ) in said
    assert "the verdict is recomputed from execution" in said
    assert "**no rulings archive was read, because this round wrote none**" in said
    assert "9 rows and 9 resolved" in said
    assert "a table-derived cost is not recomputed on the way through" in said


def test_both_readers_count_the_round_and_print_what_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 127's readers: six of the nine rows inside the default view,
    the reconcile lines quoted as the reader prints them, the calibrate table
    exactly as printed — the category priced off its three declared controls
    at 1.00x, n=3, rung floor haiku-solvable — and the earlier rounds'
    published tables unmoved."""
    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    [quoted] = fenced_blocks(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))[1:2]
    for line in quoted.strip("\n").splitlines():
        assert line in printed, line
    # The task-set line is the live corpus; the two reader lines under it are
    # rebuilt from `tests/sweep_census.py` rather than retyped, so the sweep
    # that lands after this one moves them there and not here.
    assert (
        "  task set   tasks/first-party-v1 — 128 task(s): 61 control(s), "
        "67 constructed"
    ) in printed
    assert sweep_census.reconcile_runs_line() in printed
    assert sweep_census.reconcile_keys_line() in printed
    assert printed.count(f"sweep {_SWEEP}") == 1
    assert _CATEGORY not in printed, (
        "the round declared no contrast, so it reaches the report as a "
        "label and nothing else"
    )
    assert "   67 constructed task(s): 67 swept, 0 unswept" in printed

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    [table] = fenced_blocks(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))[2:3]
    assert table.strip("\n") in calibrated, (
        "the calibration table the record quotes is not what the reader prints"
    )
    assert f"category {_CATEGORY}" in calibrated
    assert (
        "   (zero-knob)  3      1.00x (n=3)       1.00x (n=3)      "
        "haiku-solvable (n=3)"
    ) in calibrated

    said = prose(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))
    assert "**And the readers count the round with no flag at all.**" in said
    assert "**The prediction reconciliation is unmoved**" in said
    assert "**three declared controls**" in said
    assert "**1.00×, n=3**" in said
    assert "a **denominator**" in said
    assert "The rung floor reads **haiku-solvable**" in said
    assert "The published tables of earlier rounds are unmoved" in said


def test_nothing_but_the_nine_graded_records_and_the_archive_grew_by_nine(
    runs: list[firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 127's last claims before the close: the unified dataset still
    means one thing (and is gitignored — the records replay from the
    committed logs), the free-text archive grew by exactly the nine final
    messages, and the registered split the A″ readings are computed over is
    unmoved."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        flat = json.dumps(json.loads(line))
        for needle in (
            "proofs", "reference-answer", "foil", "re-ask",
            "prove-points", "point-gate-calibration", "rulings",
        ):
            assert needle not in flat, needle

    # Nothing has landed after this round yet, so the scope-out
    # `tests/sweep_census.py` enumerates is empty today. It is written all the
    # same: §127's claim is about the archive as this round left it, and this
    # is what keeps round 14's rows from silently joining it — scoped out by
    # sweep id, never by a log filename, with the section's figures unretyped.
    archived = [
        run for run in runs
        if run.output and run.sweep not in sweep_census.sweeps_after(_SWEEP)
    ]
    assert len(archived) == _ARCHIVE_NOW
    assert len(
        [run for run in archived if run.sweep != _SWEEP]
    ) == _ARCHIVE_BEFORE
    # The four point-gate rounds stay written out: §127's split is this
    # record's claim about which of them stratum A excludes, and only the
    # tail after this round — empty today — is the census's to keep.
    stratum_a = [
        run
        for run in runs
        if run.sweep not in {
            "round-10", "round-11", _ANCHOR, _SWEEP,
            *sweep_census.sweeps_after(_SWEEP),
        }
        and firstparty_v1.carries_a_key(tasks[run.task_id])
    ]
    assert len(stratum_a) == _STRATUM_A

    said = prose(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))
    assert (
        "**`data/unified.jsonl` still means one thing, and nothing but the "
        "nine graded records entered it.**"
    ) in said
    assert "a combination's result on a benchmark instance (§76.11)" in said
    assert "gitignored, round 8's standing rule" in said
    assert "they **replay from it**, from the committed logs alone" in said
    assert (
        "**333 answers across twelve sweeps to 342 across thirteen**"
    ) in said
    assert "**306 rows, 63 of them stratum A**" in said
    assert "out of that read rather than an error in it" in said


def test_the_record_takes_the_next_free_numbers_and_renumbers_nothing() -> None:
    """Sections 119-127 are the next free numbers after §118, contiguous,
    each spent once, landing before the note's trailing headings — and the
    last section names the next free number, which is the frontier sentence
    the round-9 suite's moved assertion reads."""
    text = NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(117) == 1
    assert numbered.count(118) == 1
    assert all(numbered.count(number) == 1 for number in range(119, 128))
    # The live frontier is the round-9 suite's one moved assertion and is
    # deliberately not copied here; what this test owns is that the record's
    # nine numbers are spent once each and nothing above or below them was
    # renumbered.
    assert [number for number in numbered if number > 68] == list(range(69, 128))

    for heading in record_sections():
        assert f"### {heading}\n" in text, heading

    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    record_at = headings.index("## Round 13 record — 2026-08-29")
    assert headings[record_at - 1] == (
        "## Round 13 cells and cost — registered 2026-08-29"
    )
    assert headings[record_at + 1].startswith("## Open questions"), (
        "nothing has landed after the record yet"
    )

    opening = prose(
        section("## Round 13 record — 2026-08-29").split("\n### ")[0]
    )
    assert "**§119 is the next free number.**" in opening
    assert "this record opens at **119** and runs to **127**" in opening
    assert "Nothing above it is renumbered." in opening

    closing = prose(section(
        "### 127. Replay, the readers, and heap 4 closed"
    ))
    assert "**Heap 4 closes.**" in closing
    assert "**every heap is swept**" in closing
    assert "**§128 is the next free section number**" in closing
    assert "nothing above is renumbered" in closing
