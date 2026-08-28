"""Round 10's record, pinned: what sections 85-93 of the design note publish.

The round swept nine cells over **three `investigation` tasks** — heap 3's
first, and the first graded by the **point gate**: prose judged per planted
point by a pinned instrument, `resolved` computed from archived rulings and
never spoken. Its record has one reading no earlier record could produce and
one temptation no earlier record faced in this form. The reading is **which
named planted point went uncovered** in each red cell, read off the archived
rulings where the grader's evidence spans sit quotable beside every covered
ruling. The temptation is the coverage fraction — "four of five covered" —
which ADR-0004 refused for mutants and ADR-0005 refuses for points, so this
file checks that no fraction over planted points is quoted as a quality figure
anywhere in the round's own sections.

Every figure is re-derived from the artifact that earned it: the checked-in
run logs (collected wholesale, selected by **sweep id `round-10`** and never by
a log's filename — the sweep protocol's rule), the per-cell rulings archives
under `data/first-party-v1-rulings/`, the tasks' own `proofs/` archives, the
lint's printed coverage table and the readers' actual output. The design
note's own tables are rebuilt from those artifacts and compared whole, and
each section is sliced **from its own heading to the next heading** — never to
`## Open questions` or any landmark further down, the rule
`docs/agents/runbook-grader-v2-gate.md:153` writes down.

**Everything here is offline and no grader client is constructed.** Every
verdict is recomputed from archived rulings through `_point_verdict`, replay
is handed no factory by construction, and
`point_grader.deepseek_point_grader` is replaced by a detonator for the whole
module, so a construction anywhere in this file is a failure rather than a
silent live call.

§80.5's freezing rule, carried forward in one line: this suite reaches the
live `point_grader.GRADER_VERSION`, `point_grader.PROMPT` and the live span
rule (`span_in_deliverable`, via `_point_verdict`) because v2 is the
instrument the round's rulings were taken under; the next time the instrument
moves, this suite freezes to v2's literal tuple, the template length and the
archived rulings' own spans, with a comment naming §85.
"""

import json
import platform
import re
import statistics
from pathlib import Path
from typing import Iterator

import pytest

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
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"
_UNIFIED = _REPO / "data" / "unified.jsonl"
_CONTEXT = _REPO / "CONTEXT.md"

_SWEEP = "round-10"
_ANCHOR = "round-8"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-24"
_CATEGORY: TaskCategory = "investigation"

# The versions the rows carry — and this round crosses a boundary: claude-code
# moved from round 8's 2.1.235 (round 9 never swept), which §85 narrates as a
# cross-round caveat; codex is rounds 6-8's exactly.
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.241 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}
_ROUND_8_CLAUDE_VERSION = "2.1.235 (Claude Code)"

# The four logs the sweep's four invocations wrote, and what each replays to.
# Named only so that section 93's replay can be given one log at a time;
# nothing here selects runs by them.
_REPLAYED = {
    "2026-08-24-r10-a.jsonl": (1, 0),
    "2026-08-24-r10-b.jsonl": (2, 0),
    "2026-08-24-r10-c.jsonl": (3, 1),
    "2026-08-24-r10-d.jsonl": (3, 0),
}
_DRY_CELL = "granary-decide-how-to-answer-for-a-past-day"

# Section 87's spend, per combination and per cost source, and both registered
# ranges it is read against. The sweep missed its range on the low side — the
# miss §83.6 registered as the likelier one and pre-read as a finding about
# the action — so the floor below is asserted *not* met, deliberately.
_SPEND = {_HAIKU: 0.2529, _SONNET: 0.7103, _TERRA: 0.2458}
_BILLED = 0.9632
_TOTAL = 1.2089
_PER_CELL = {_HAIKU: 0.0843, _SONNET: 0.2368, _TERRA: 0.0819}
_REGISTERED_RANGE = (2.5, 5.0)
_REGISTERED_COLUMN = {_HAIKU: 0.7236, _SONNET: 1.7679}
_REGISTERED_CODEX_BAND = (0.17, 0.82)
_ROUND_8_PER_CELL = {_HAIKU: 0.2412, _SONNET: 0.5893, _TERRA: 0.0899}
_CHEAPER = {_HAIKU: 0.35, _SONNET: 0.40, _TERRA: 0.91}
_FLAT_EXTRAPOLATION_RATIO = 0.44

# Section 87's token evidence for the low miss: a proposal is a smaller write
# and a smaller read than a test suite, per cell, on both claude columns.
_TOKENS_PER_CELL = {
    _HAIKU: (239_991, 5_619),
    _SONNET: (239_678, 10_057),
    _TERRA: (111_316, 2_457),
}
_ROUND_8_TOKENS_PER_CELL = {
    _HAIKU: (871_488, 15_907),
    _SONNET: (799_935, 12_754),
    _TERRA: (120_425, 2_707),
}

# Section 87's Codex bounds at the round's own tokens, and the effective rate.
_CODEX_TOKENS = (333_948, 7_370)
_ALL_CACHED = 0.1552
_ALL_UNCACHED = 0.7563
_EFFECTIVE_RATE = 0.4711
_ROUND_8_EFFECTIVE_RATE = 0.4771
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 86/87's proofs: the counted calls and the registered range they are
# priced against. Five points and one disqualifier per task, both sides.
_PROOF_CALLS = 36
_PROOF_CALLS_PER_TASK = 12
_PROOF_INPUT_CHARS = 205_974
_PROOF_INPUT_TOKENS = 51_493
_PROOF_RANGE = (0.05, 0.6)
_DEEPSEEK_INPUT_PER_MTOK = 1.32
_DEEPSEEK_OUTPUT_PER_MTOK = 3.96
_PROOF_ANSWER_CHAR_CAP = 8_000

# Section 85's resolution line, and the one cell it turns on.
_RESOLVED = {_HAIKU: 0, _SONNET: 1, _TERRA: 0}
_THE_RESOLVED_CELL = (_DRY_CELL, _SONNET)

# Section 85's limits paragraph.
_LONGEST_S = 170.9
_MEAN_S = 97.3
_PYTHON_VERSION = "3.14.4"

# Section 88's turn line, quoted so section 92's refusal has an anchor.
_TURNS = {_HAIKU: 29, _SONNET: 28, _TERRA: 21}
_TURN_RANGE = {_HAIKU: (9, 11), _SONNET: (8, 10), _TERRA: (7, 7)}

# Section 89's reading: the argument-shaped points of each key, which every
# one of the nine answers covered — every miss is a planted fact of the code.
_ARGUMENT_POINTS = {
    "granary-decide-how-to-answer-for-a-past-day": (
        "journal-against-snapshot", "a-recommendation-argued",
    ),
    "pumphouse-decide-who-catches-the-backwards-reading": (
        "two-owners-each-costed", "one-owner-argued",
    ),
    "ferryhouse-decide-whether-the-takings-drift-is-a-defect": (
        "a-ruling-argued",
    ),
}
_FOIL_DISQUALIFIERS = {
    "granary-decide-how-to-answer-for-a-past-day": "replay-suffices",
    "pumphouse-decide-who-catches-the-backwards-reading": "lower-is-always-wrong",
    "ferryhouse-decide-whether-the-takings-drift-is-a-defect":
        "the-box-can-be-recounted",
}

# Section 93's archive line: the free-text archive across ten sweeps, and the
# registered split the A″ readings stay computed over.
_ARCHIVE_BEFORE = 306
_ARCHIVE_NOW = 315
_STRATUM_A = 63

# Section 90's updated CONTEXT.md sentence, pinned the way the quoted figures
# are; the docstring's is asserted off the live function's __doc__ below.
# Round 11 moved the sentence on when it filled
# `requirement-decomposition`'s Python cell — the "today" exemplar is now
# `performance-optimisation` and the filled category joined the record of
# past zeros in the same form — so the pin is on the caught-up sentence;
# §90's own quoted prose stays what round 10 wrote.
_CONTEXT_SENTENCE = (
    "(`performance-optimisation` today; `test-authoring` was one until "
    "round 8 authored its three Python tasks, `investigation` was one until "
    "round 10 filled its Python cell, and `requirement-decomposition` was "
    "one until round 11 filled its Python cell)"
)


@pytest.fixture(scope="module", autouse=True)
def no_grader_can_be_built() -> Iterator[None]:
    """The offline claim, made structural for the whole module.

    §93 says the round's rows replay with the network unplugged and no grader
    client constructed. Nothing below should reach the one factory there is,
    so the factory is replaced by a detonator: a construction anywhere in this
    file fails the suite instead of quietly asking for a key.
    """
    original = point_grader.deepseek_point_grader

    def refuse() -> point_grader.PointGrader:
        raise AssertionError(
            "the round-10 record is a recomputation over archived rulings — "
            "this suite builds no grader client and makes no paid call"
        )

    point_grader.deepseek_point_grader = refuse
    try:
        yield
    finally:
        point_grader.deepseek_point_grader = original


def note_section(heading: str) -> str:
    """One numbered section of the record, from its own heading to the next.

    Deliberately never sliced to `## Open questions` or any landmark further
    down (`docs/agents/runbook-grader-v2-gate.md:153`): a slice that runs to
    the note's trailing headings swallows whole sections silently.
    """
    body = _NOTE.read_text(encoding="utf-8").split(f"### {heading}\n")
    assert len(body) == 2, f"the note carries exactly one {heading!r}"
    return body[1].split("\n### ")[0].split("\n## ")[0]


def note_part(heading: str) -> str:
    """One top-level part of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"## {heading}\n")
    assert len(body) == 2, f"the note carries exactly one {heading!r}"
    return body[1].split("\n## ")[0]


def prose(text: str) -> str:
    """A passage with its wrapping collapsed: the sentence is the pin, the
    line break is not."""
    return " ".join(text.split())


def fenced_blocks(text: str) -> list[str]:
    """Every fenced code block of a passage, in order."""
    return text.split("```\n")[1::2]


def record_sections() -> list[str]:
    """The record's own sections, by heading, in order."""
    return [
        "85. What the round measured",
        "86. The proofs gate certified the instrument on production-shaped prose",
        "87. Spend, by cost source, against both registered ranges",
        "88. The nine cells under three combinations",
        "89. Which point went uncovered, and what the collection rule archived",
        "90. The coverage table, as the lint prints it",
        "91. The A″ readings, carried forward as readings",
        "92. What this round cannot say",
        "93. Replay, the readers, and heap 3 opened",
    ]


_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def registered_cells() -> list[str]:
    """§83.7's filled register, read back out of the pre-registration, so what
    the round swept is compared against the register itself and never a copy."""
    for block in fenced_blocks(
        note_part("Round 10 cells and cost — registered 2026-08-23")
    ):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        matched = [
            match for line in lines if (match := _REGISTER_LINE.fullmatch(line))
        ]
        if len(matched) == len(lines) and all(
            match.group(2) for match in matched
        ):
            return [match.group(1) for match in matched]
    raise AssertionError("§83.7's filled register is not in the note")


def tasks_in_set() -> int:
    """How many tasks the checked-in set holds, as `eval-v1` counts them —
    derived rather than pinned, because a later round authoring a task moves
    the replay block's `over N tasks` and this has to move with it."""
    return len(firstparty_v1.load_task_set(_TASKS))


@pytest.fixture(scope="module")
def tasks() -> dict[str, firstparty_v1.Task]:
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def runs() -> list[firstparty_v1.Run]:
    """Every run in the log directory, collected wholesale — a filename says
    nothing about which sweep a row belongs to."""
    return [
        run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    ]


@pytest.fixture(scope="module")
def round_10(
    runs: list[firstparty_v1.Run],
) -> dict[tuple[str, str], firstparty_v1.Run]:
    """The round's nine rows, keyed task x model, selected by sweep id."""
    swept = {
        (run.task_id, run.model): run for run in runs if run.sweep == _SWEEP
    }
    assert len(swept) == 9, "the round is nine cells, none repeated"
    return swept


@pytest.fixture(scope="module")
def rulings(
    tasks: dict[str, firstparty_v1.Task],
    round_10: dict[tuple[str, str], firstparty_v1.Run],
) -> dict[tuple[str, str], tuple[bool, list[str], list[str]]]:
    """Every cell's verdict, uncovered points and present disqualifiers,
    recomputed from the archived rulings against the deliverable the diff
    collects — the very computation replay runs, with no grader anywhere.

    The verdict is taken from `_point_verdict` — the shipped gate — and the
    per-point reading beside it re-applies the same span rule, so this is a
    reading of the one grading pipeline and not a second one that happens to
    agree with it.
    """
    derived: dict[tuple[str, str], tuple[bool, list[str], list[str]]] = {}
    for (task_id, model), run in sorted(round_10.items()):
        task = tasks[task_id]
        key = firstparty_v1.points_key(task)
        deliverable = firstparty_v1._collect_the_answer_file(
            task, run.diff, key.answer_path
        )
        assert deliverable.strip(), (task_id, model)
        archive = firstparty_v1.RunRulings.model_validate(
            json.loads(
                firstparty_v1.rulings_file(
                    _RULINGS, task_id, run.agent, model
                ).read_text(encoding="utf-8")
            )
        )
        # One instrument over the whole round: §83.2's stop never fired.
        assert archive.grader_version == point_grader.GRADER_VERSION
        questions = firstparty_v1._point_questions(key)
        verdict = firstparty_v1._point_verdict(questions, archive, deliverable)
        by_question = {
            (entry.kind, entry.point_id): entry for entry in archive.rulings
        }
        uncovered: list[str] = []
        present: list[str] = []
        for kind, planted in questions:
            entry = by_question[(kind, planted.id)]
            covered = firstparty_v1._the_span_holds(
                entry.covered, entry.span, deliverable
            )
            # No covered ruling of this round was demoted: every span the
            # grader quoted is really in the deliverable it quoted it from.
            assert covered == entry.covered, (task_id, model, planted.id)
            if kind == "point" and not covered:
                uncovered.append(planted.id)
            if kind == "disqualifier" and covered:
                present.append(planted.id)
        derived[(task_id, model)] = (verdict, uncovered, present)
    return derived


def cell_table(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 88's table, rebuilt from the logs and the recomputed verdicts —
    byte for byte, headers and cost sources included."""
    ids = sorted({task_id for task_id, _ in round_10})
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
            verdict = "resolved  " if rulings[task_id, model][0] else "unresolved"
            columns.append(f"{verdict} ${round_10[task_id, model].cost_usd:.4f}")
        lines.append(
            (f"{task_id:<{width}}  "
             + "  ".join(f"{column:<18}" for column in columns)).rstrip()
        )
    return "\n".join(lines) + "\n"


def gate_table(
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 89's table, rebuilt from the archived rulings: per cell, the
    named uncovered points — never a count of them and never a fraction."""
    ids = sorted({task_id for task_id, _ in rulings})
    labels = [(task_id, model) for task_id in ids for _, model in _COMBINATIONS]
    width = max(len(f"{task_id} x {model}") for task_id, model in labels)
    lines = [f"{'cell':<{width}}  uncovered planted point(s)"]
    for task_id, model in labels:
        verdict, uncovered, present = rulings[task_id, model]
        assert not present, "no disqualifier fired anywhere in the round"
        body = (
            ", ".join(uncovered)
            if uncovered
            else "none — every point covered, no disqualifier present"
        )
        assert bool(uncovered) != verdict, (task_id, model)
        pad = width - len(task_id) - 3
        lines.append(f"{task_id} x {model:<{pad}}  {body}")
    return "\n".join(lines) + "\n"


def test_the_round_swept_exactly_the_cells_that_were_registered(
    tasks: dict[str, firstparty_v1.Task],
    runs: list[firstparty_v1.Run],
    round_10: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 85's sweep facts, off the rows themselves, against §83.7.

    The register is read out of the pre-registration rather than restated.
    One sweep id, one as-of date, one version per harness — and this round
    crosses a version boundary on the claude-code side, which the record
    narrates rather than hides: round 9 never swept, and the harness moved
    between round 8's sweep and this one.
    """
    assert {run.sweep for run in round_10.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in round_10.values()} == {_AS_OF}
    assert {
        (run.agent, run.model) for run in round_10.values()
    } == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version
            for run in round_10.values()
            if run.agent == agent
        } == {version}, agent

    # The boundary, read off round 8's own rows rather than quoted from §69.
    round_8 = [run for run in runs if run.sweep == _ANCHOR]
    assert {
        run.agent_version
        for run in round_8
        if run.agent == firstparty.CLAUDE_CODE
    } == {_ROUND_8_CLAUDE_VERSION}
    assert _ROUND_8_CLAUDE_VERSION != _AGENT_VERSIONS[firstparty.CLAUDE_CODE]
    assert {
        run.agent_version for run in round_8 if run.agent == "codex"
    } == {_AGENT_VERSIONS["codex"]}, "codex crossed no boundary"

    registered = registered_cells()
    assert len(registered) == 3 == len(set(registered))
    assert {task_id for task_id, _ in round_10} == set(registered)
    assert {tasks[task_id].category for task_id in registered} == {_CATEGORY}
    assert {tasks[task_id].language for task_id in registered} == {"python"}
    assert {tasks[task_id].surface for task_id in registered} == {"application"}
    assert all(tasks[task_id].control for task_id in registered)
    assert set(registered) == {
        task.id for task in tasks.values() if task.category == _CATEGORY
    }, "every investigation task the corpus holds, and no fourth"

    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(note_section("85. What the round measured"))
    assert "**Nine cells, and they are exactly the nine §83.7 registered.**" in measured
    assert "**9 of 9**" in measured
    assert "**heap 3's first cells**" in measured
    assert "**no second quality metric enters the table**" in measured
    assert "**does cross a version boundary**" in measured
    assert "**2.1.241** against round 8's 2.1.235" in measured
    assert "round 9 never swept" in measured
    assert "**codex-cli 0.147.0** is rounds 6, 7 and 8's exactly" in measured


def test_the_dry_cell_and_the_four_logs_are_what_the_record_says(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 85's invocation paragraph, against the checked-in logs.

    The dry cell was one of the nine, run alone in its own invocation, graded
    alone before the other eight, and it is the point gate's first paid
    production verdict — unresolved, with named uncovered points, which is
    the verdict shape arriving well-formed. And the registration's word
    "cheapest" is checked against what the rows actually cost, the departure
    stated rather than passed over — round 8's own honesty, repeated.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 9
    assert min(counted.values()) > 0, "no invocation of this round logged nothing"

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-24-r10-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    verdict, uncovered, present = rulings[_DRY_CELL, _HAIKU]
    assert verdict is False and len(uncovered) == 3 and not present, (
        "the gate's first paid production verdict: unresolved, three named "
        "points uncovered, nothing mis-shaped"
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

    # "Cheapest" was an ex-ante reading the anchor did not support: Codex was
    # the cheaper column at round 8's anchor and again in the event, and the
    # cheapest single cell was a Codex one.
    assert _ROUND_8_PER_CELL[_TERRA] < _ROUND_8_PER_CELL[_HAIKU]
    assert _PER_CELL[_TERRA] < _PER_CELL[_HAIKU]
    cheapest = min(round_10.items(), key=lambda item: item[1].cost_usd)
    assert cheapest[0] == (
        "ferryhouse-decide-whether-the-takings-drift-is-a-defect", _TERRA
    )
    assert round(cheapest[1].cost_usd, 4) == 0.0634
    assert round(round_10[_DRY_CELL, _HAIKU].cost_usd, 4) == 0.0798

    measured = prose(note_section("85. What the round measured"))
    assert "**Four invocations, four logs, none of them empty.**" in measured
    assert "**graded alone before the other eight**" in measured
    assert "**first paid production verdict**: **unresolved**" in measured
    assert (
        "**The dry cell was registered as the cheapest of the nine and was "
        "not**"
    ) in measured
    assert "**$0.0819** a cell against haiku's **$0.0843**" in measured
    assert (
        "`ferryhouse` on Codex at $0.0634 against the dry cell's $0.0798"
    ) in measured


def test_the_proofs_gate_certified_the_instrument_on_production_shaped_prose(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 86: the round's one gate, recomputed from the proof archives.

    §83.4's quantifier, checked as a quantifier: every planted point of every
    reference answer resolves and every foil fails, through the very
    `_point_verdict` a run is graded by. The foils' two-sided failure — the
    named disqualifier claimed *and* points uncovered — is re-derived per
    task, and the certification sentence the next round planner reads is
    pinned in as many words.
    """
    for task_id in _FOIL_DISQUALIFIERS:
        task = tasks[task_id]
        key = firstparty_v1.points_key(task)
        assert (len(key.points), len(key.disqualifiers)) == (5, 1)
        questions = firstparty_v1._point_questions(key)
        assert len(questions) * 2 == _PROOF_CALLS_PER_TASK
        for side in firstparty_v1.PROOF_SIDES:
            answer = (task.proofs_dir / side.answer_file).read_text(
                encoding="utf-8"
            )
            archive = firstparty_v1.ProofRulings.model_validate(
                json.loads(
                    firstparty_v1.proof_rulings_file(task, side).read_text(
                        encoding="utf-8"
                    )
                )
            )
            assert archive.grader_version == point_grader.GRADER_VERSION
            assert firstparty_v1._point_verdict(
                questions, archive, answer
            ) is side.resolves, (task_id, side.name)
            by_question = {
                (entry.kind, entry.point_id): entry for entry in archive.rulings
            }
            covered = {
                planted.id: firstparty_v1._the_span_holds(
                    by_question[kind, planted.id].covered,
                    by_question[kind, planted.id].span,
                    answer,
                )
                for kind, planted in questions
            }
            if side.resolves:
                assert all(
                    covered[planted.id]
                    for kind, planted in questions
                    if kind == "point"
                ), f"{task_id}: every reference point covered"
                assert not covered[_FOIL_DISQUALIFIERS[task_id]]
            else:
                assert covered[_FOIL_DISQUALIFIERS[task_id]], (
                    f"{task_id}: the foil claims its disqualifier"
                )
                assert [
                    planted.id
                    for kind, planted in questions
                    if kind == "point" and not covered[planted.id]
                ], f"{task_id}: the foil also leaves points uncovered"

    # The rule the section names is the one the lint runs for this action.
    assert (
        firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].check
        is firstparty_v1._the_reference_resolves_and_the_foil_fails
    )

    certified = prose(note_section(
        "86. The proofs gate certified the instrument on production-shaped "
        "prose"
    ))
    assert (
        "the proofs gate certified the instrument on production-shaped "
        "prose.**"
    ) in certified
    assert (
        "**every planted point of every task's reference answer resolved, "
        "and every foil answer failed**"
    ) in certified
    assert "no fraction met, no proportion computed, no threshold" in certified
    assert "**exactly the deliverable type production grades**" in certified
    assert (
        "**The sentence the next round planner reads: planted points "
        "survived contact with an open-ended proposal, so "
        "`requirement-decomposition` and explain-style "
        "`codebase-comprehension` can follow as mechanical fills**"
    ) in certified
    assert "**five points and one disqualifier**" in certified
    assert "**12 paid calls a task**" in certified
    assert "every foil failed **both ways at once**" in certified
    assert "`_the_reference_resolves_and_the_foil_fails`" in certified
    assert "no proof failed, so the stop §83.4 kept armed did not fire" in certified


def test_the_sweep_cost_what_the_record_states_by_cost_source(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 87's sweep spend, pinned per cost source and per cell, and the
    registered range it missed on the low side.

    The miss is the point: §83.6 registered $2.5-5 with the low miss named as
    the likelier and pre-read as a finding about the action, so this test
    asserts the round landed *under* the floor and that the record reads it
    as that finding — with the per-cell token evidence re-derived beside it.
    """
    ids = sorted({task_id for task_id, _ in round_10})
    for model, spend in _SPEND.items():
        actual = sum(round_10[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 3, 4) == _PER_CELL[model], model
        assert round(
            _PER_CELL[model] / _ROUND_8_PER_CELL[model], 2
        ) == _CHEAPER[model], model

    billed = sum(
        run.cost_usd
        for run in round_10.values()
        if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED
    total = sum(run.cost_usd for run in round_10.values())
    assert round(total, 4) == _TOTAL
    # Summed before rounding: the printed columns add to one last digit above
    # the true total, which the record says rather than leaves to a checker.
    assert round(sum(_SPEND.values()), 4) == 1.2090 != _TOTAL

    low, high = _REGISTERED_RANGE
    assert total < low, "the registered low miss is the miss the round has"
    assert round(total / 2.7614, 2) == _FLAT_EXTRAPOLATION_RATIO
    band_low, band_high = _REGISTERED_CODEX_BAND
    assert band_low < _SPEND[_TERRA] < band_high
    assert _SPEND[_TERRA] < 0.27, "just under the ~$0.27 the band expected"
    for model, registered in _REGISTERED_COLUMN.items():
        assert _SPEND[model] < registered, model

    # The token evidence, per cell, against round 8's — both re-derived.
    for model, (tokens_in, tokens_out) in _TOKENS_PER_CELL.items():
        assert round(sum(
            run.tokens_in for key, run in round_10.items() if key[1] == model
        ) / 3) == tokens_in, model
        assert round(sum(
            run.tokens_out for key, run in round_10.items() if key[1] == model
        ) / 3) == tokens_out, model
        round_8_in, round_8_out = _ROUND_8_TOKENS_PER_CELL[model]
        assert tokens_in < round_8_in and tokens_out < round_8_out, model

    # Cost sources, on the rows and refused at load if contradicted.
    codex = {k: run for k, run in round_10.items() if run.agent == "codex"}
    claude = {
        k: run
        for k, run in round_10.items()
        if run.agent == firstparty.CLAUDE_CODE
    }
    assert (len(codex), len(claude)) == (3, 6)
    assert {run.cost_source for run in codex.values()} == {"table-derived"}
    assert {run.price_table for run in codex.values()} == {_PRICE_TABLE}
    assert {run.cost_source for run in claude.values()} == {"vendor-reported"}
    assert {run.price_table for run in claude.values()} == {None}

    # The Codex bounds a reader can recompute, and the rate between them.
    tokens_in_total = sum(run.tokens_in for run in codex.values())
    tokens_out_total = sum(run.tokens_out for run in codex.values())
    assert (tokens_in_total, tokens_out_total) == _CODEX_TOKENS
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
    assert _EFFECTIVE_RATE < _ROUND_8_EFFECTIVE_RATE

    read = prose(note_section(
        "87. Spend, by cost source, against both registered ranges"
    ))
    assert (
        "**The registered sweep range was $2.5–5. The round came to $1.2089, "
        "and the range was missed on the low side"
    ) in read
    assert "pre-read as a finding about the action" in read
    assert "**summed before rounding**" in read
    assert (
        "the printed columns add to $1.2090, one last digit above the true "
        "total"
    ) in read
    assert "**0.44×** the flat extrapolation" in read
    assert "**What the account was actually billed for the sweep: $0.9632" in read
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read
    assert "**$0.1552 all-cached** and **$0.7563 all-uncached**" in read
    assert "**$0.4711/M**" in read
    assert "**0.35×** and **0.40×**" in read and "**0.91×**" in read
    assert "did not happen, and the $5 stop was never approached" in read
    assert (
        "version boundary (§85) is named beside these column readings and "
        "cannot carry them"
    ) in read

    blocks = fenced_blocks(note_section(
        "87. Spend, by cost source, against both registered ranges"
    ))
    assert blocks[0] == (
        "claude-code x haiku     $0.2529  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $0.7103  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $0.2458  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )
    for line in (
        "claude-code x haiku     $0.7236               $0.2529    $0.0843    $0.2412",
        "claude-code x sonnet    $1.7679               $0.7103    $0.2368    $0.5893",
        "codex x gpt-5.6-terra   $0.17-$0.82 (~$0.27)  $0.2458    $0.0819    $0.0899",
    ):
        assert line in blocks[1], line


def test_the_proofs_are_priced_over_counted_calls_inside_their_range(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 87's proofs arithmetic, recomputed from the checked-in answers.

    The calls are counted off the keys and the archives — 12 a task, 36 for
    the round, inside §83.5's registered 24-48 — and the input half is now
    arithmetic over text a reader holds: the six proof answers, the live
    template and each point's own text. The output half stays the bounded
    assumption §83.5 registered, because the archives hold rulings and not
    token counts, and both ends of the total sit inside $0.05-0.6.
    """
    calls = 0
    input_chars = 0
    answer_chars = 0
    lengths: dict[str, dict[str, int]] = {}
    template = len(point_grader.PROMPT)
    assert template == 1_461  # §80.5: freezes to this literal when v2 moves.
    for task_id in _FOIL_DISQUALIFIERS:
        task = tasks[task_id]
        questions = firstparty_v1._point_questions(firstparty_v1.points_key(task))
        lengths[task_id] = {}
        for side in firstparty_v1.PROOF_SIDES:
            answer = (task.proofs_dir / side.answer_file).read_text(
                encoding="utf-8"
            )
            lengths[task_id][side.name] = len(answer)
            assert len(answer) <= _PROOF_ANSWER_CHAR_CAP, (
                "§83.5's named miss did not happen"
            )
            for _, planted in questions:
                calls += 1
                input_chars += template + len(planted.text) + len(answer)
                answer_chars += len(answer)
    assert calls == _PROOF_CALLS
    assert input_chars == _PROOF_INPUT_CHARS
    input_tokens = input_chars // 4
    assert input_tokens == _PROOF_INPUT_TOKENS

    per_input = _DEEPSEEK_INPUT_PER_MTOK / 1e6
    per_output = _DEEPSEEK_OUTPUT_PER_MTOK / 1e6
    input_cost = input_tokens * per_input
    low_out = calls * 100
    high_out = answer_chars // 4 + calls * 300
    assert (low_out, high_out) == (3_600, 47_580)
    total_low = round(input_cost + low_out * per_output, 4)
    total_high = round(input_cost + high_out * per_output, 4)
    assert (total_low, total_high) == (0.0822, 0.2564)
    range_low, range_high = _PROOF_RANGE
    assert range_low <= total_low and total_high <= range_high

    # The registered per-task shape held: 12 calls is inside 8-16, and the
    # counted input sits between §83.5's own low and high token counts.
    assert 8 * 3 <= calls <= 16 * 3
    assert 33_966 < input_tokens < 115_932

    read = prose(note_section(
        "87. Spend, by cost source, against both registered ranges"
    ))
    assert "**12 a task, 36 for the round**" in read
    assert "the third-disqualifier stop never fired" in read
    assert (
        "reference answers of 5,449, 4,878 and 4,994 characters, foils of "
        "3,248, 2,633 and 3,318"
    ) in read
    assert {
        lengths[task_id][side.name]
        for task_id in lengths
        for side in firstparty_v1.PROOF_SIDES
    } == {5_449, 4_878, 4_994, 3_248, 2_633, 3_318}
    assert "no answer over the registered 8,000-character high" in read
    assert f"the live template's **{template:,}** characters" in read
    assert "**The output half is still the half with no anchor**" in read
    assert "inside the registered $0.05–0.6" in read
    assert "priced here at the registered peak-hour, cache-miss figures" in read
    assert "the console's figure can only sit at or under this arithmetic" in read

    [block] = [
        block
        for block in fenced_blocks(note_section(
            "87. Spend, by cost source, against both registered ranges"
        ))
        if "round total" in block
    ]
    for line in (
        f"proofs  input        {calls} calls x (template + point + answer) = "
        f"{input_chars:,} chars / 4 =  {input_tokens:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(input_cost, 4):.4f}",
        f"        output low   {calls} x 100 tok thinking"
        f"                                      =   {low_out:,} tok  x "
        f"${_DEEPSEEK_OUTPUT_PER_MTOK}/M = ${round(low_out * per_output, 4):.4f}",
        f"        output high  {calls} x 300 tok + every deliverable quoted "
        f"whole              =  {high_out:,} tok  x "
        f"${_DEEPSEEK_OUTPUT_PER_MTOK}/M = ${round(high_out * per_output, 4):.4f}",
        f"round total    ${total_low:.4f} - ${total_high:.4f}",
    ):
        assert line in block, line


def test_the_per_cell_table_is_what_the_logs_and_the_rulings_say(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 88's table, rebuilt from the artifacts and compared byte for
    byte — the only pin that cannot drift a cell at a time, headers and cost
    sources included."""
    quoted = fenced_blocks(
        note_section("88. The nine cells under three combinations")
    )[0]
    assert quoted == cell_table(round_10, rulings)

    resolved = {
        model: sum(
            1
            for (_, run_model), (verdict, _, _) in rulings.items()
            if run_model == model and verdict
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 1
    assert [
        key for key, (verdict, _, _) in rulings.items() if verdict
    ] == [_THE_RESOLVED_CELL]

    measured = prose(note_section("85. What the round measured"))
    assert "**Resolution: 1 of 9.**" in measured
    assert (
        "**0 of 3** on `claude-haiku-4-5`, **1 of 3** on `claude-sonnet-5`"
    ) in measured
    assert "**0 of 3** on `codex` × `gpt-5.6-terra`" in measured

    said = prose(note_section("88. The nine cells under three combinations"))
    assert "There is no per-category block beside it" in said
    assert "no rate is quoted off it" in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 88's turn line, and the definition that makes it uncomparable
    across the harness boundary."""
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in round_10.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(note_section("88. The nine cells under three combinations"))
    assert (
        "Haiku took **29** turns over the three (9–11), sonnet **28** "
        "(8–10), Codex **21** (7–7)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_each_red_cell_names_the_points_its_rulings_left_uncovered(
    tasks: dict[str, firstparty_v1.Task],
    round_10: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 89: the round's one new reading, re-derived whole.

    The table is rebuilt from the archived rulings and compared byte for
    byte, so the record can never claim a point the archive does not. Three
    claims ride with it: no disqualifier was present in any answer, no
    covered ruling was demoted (asserted inside the fixture, span by span),
    and every uncovered point anywhere is one of the keys' planted facts —
    the argument-shaped points were covered in all nine answers.
    """
    quoted = fenced_blocks(note_section(
        "89. Which point went uncovered, and what the collection rule archived"
    ))[0]
    assert quoted == gate_table(rulings)

    for (task_id, model), (verdict, uncovered, present) in rulings.items():
        assert not present, (task_id, model)
        for argued in _ARGUMENT_POINTS[task_id]:
            assert argued not in uncovered, (task_id, model, argued)
        # Every named point is a point of the task's own key.
        key_points = {
            planted.id
            for planted in firstparty_v1.points_key(tasks[task_id]).points
        }
        assert set(uncovered) <= key_points, (task_id, model)

    # The collection rule was unexercised: every diff touches the answer file
    # and nothing else, which the record says rather than claiming proof.
    for (task_id, model), run in round_10.items():
        touched = re.findall(r"^diff --git a/(\S+) b/", run.diff, re.MULTILINE)
        assert touched == ["ANSWER.md"], (task_id, model)

    said = prose(note_section(
        "89. Which point went uncovered, and what the collection rule archived"
    ))
    assert "**no disqualifier was present in any of the nine answers**" in said
    assert "**no covered ruling was demoted**" in said
    assert (
        "**That is the whole of the verdict reading, and no fraction is "
        "computed over it.**"
    ) in said
    assert "were covered in all nine answers" in said
    assert "**facts of the code and their consequences**" in said
    assert (
        "**What the collection rule archived: nothing, because there was "
        "nothing.**"
    ) in said
    assert "unexercised this round rather than proved" in said
    assert "**pointer prose is structurally impossible**" in said


def test_no_fraction_over_points_is_quoted_as_a_quality_figure() -> None:
    """§83.4's registered refusal, honoured in the record's own prose.

    The shapes that would break it: a percentage, an `n of m` or `n/m` over a
    point-sized denominator (the keys plant four to six points), and the
    English of a coverage rate. What the record is allowed to say is cell
    counts over three and nine — resolution lines — and the named points
    themselves, which §89 checks are there.
    """
    point_fraction = re.compile(
        r"\d+\s*(?:%|/\s*[456]\b|of\s+(?:four|five|six)\b|of\s+[456]\b)",
        re.IGNORECASE,
    )
    for heading in record_sections():
        text = note_section(heading)
        assert not point_fraction.search(text), heading
        assert "coverage rate" not in text, heading
        assert "kill rate" not in text, heading
    said = prose(note_section("92. What this round cannot say"))
    assert "**No coverage-fraction reading of any kind.**" in said
    assert '"four of five covered" as a score' in said


def test_the_coverage_table_and_the_two_updated_sentences(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 90: the table as the lint prints it, and the two checked-in
    sentences the round falsified, updated in round 8's recorded form.

    The quoted block is compared with the printed table line for line — no
    stale line when it was recorded, because the record was written after the
    fill it records; two lines have moved since — round 11's three
    `requirement-decomposition` tasks turning the row this record quotes as
    `- - 0` into a Python cell, and round 12's first explain-style task
    growing `codebase-comprehension`'s row — and each is named below in
    round 7's pattern rather than edited in the record. The
    `investigation × typescript` zero
    is disclosed as zero by absence, and the docstring and CONTEXT.md
    sentences are pinned here the way the quoted figures are — caught up as
    round 11 moved them, so they cannot quietly claim a zero again.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))
    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python[_CATEGORY] == 3, "the round's acceptance figure"
    # 119 when §90 was recorded; round 11's three `requirement-decomposition`
    # tasks moved the live column to 122, and round 12's first explain-style
    # `codebase-comprehension` task to 123.
    assert sum(python.values()) == 123
    assert not [
        row for row in coverage if row[0] == _CATEGORY and row[2] == "typescript"
    ], "the TypeScript zero is by absence"
    assert not [row for row in coverage if row[0] == _CATEGORY and row[3] == 0]
    assert ("performance-optimisation", "-", "-", 0) in coverage, (
        "the shape a real zero prints, and the docstring's example now"
    )

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed
    [quoted] = fenced_blocks(
        note_section("90. The coverage table, as the lint prints it")
    )
    # The two lines that have moved since §90 was recorded, each named in
    # round 7's pattern rather than edited in the record: round 11's first
    # `requirement-decomposition` task turned the zero row this record quotes
    # into a Python cell, and round 12's first explain-style task grew
    # `codebase-comprehension`'s row from 4 to 5.
    moved = {
        "  requirement-decomposition  -            -           0",
        "  codebase-comprehension     application  python      4",
    }
    quoted_lines = quoted.strip("\n").splitlines()
    for line in moved:
        assert line in quoted_lines, line
        assert line not in printed, line
    for line in quoted_lines:
        if line in moved:
            continue
        assert line in printed, line
    assert "  investigation              application  python      3" in quoted
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  requirement-decomposition")
    ] == [["requirement-decomposition", "application", "python", "3"]]
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  codebase-comprehension")
    ] == [["codebase-comprehension", "application", "python", "5"]]

    said = prose(note_section("90. The coverage table, as the lint prints it"))
    assert (
        "**`investigation application python 3` is the round's acceptance "
        "figure**"
    ) in said
    assert "zero by absence — which is all the table can express" in said
    assert "**the lint was not changed**" in said
    assert "heap 3 stays on Python until the grader has a record behind it" in said

    # The two updated sentences, pinned as checked-in text and quoted in the
    # record. The docstring first, read off the live function. Round 11 moved
    # each sentence's "today" exemplar on to `performance-optimisation` when
    # it filled `requirement-decomposition`'s Python cell; §90's own quoted
    # prose below is the record of what round 10 wrote and stays unmoved.
    docstring = firstparty_v1.coverage_table.__doc__ or ""
    assert "`investigation` read zero" in docstring
    assert "until round 10 filled its Python cell" in " ".join(docstring.split())
    assert (
        "`requirement-decomposition` read zero until round 11 filled its "
        "Python cell"
    ) in " ".join(docstring.split())
    assert (
        "`performance-optimisation` is one of the categories reading zero "
        "today"
    ) in " ".join(docstring.split())
    assert "`investigation` is one of the categories reading zero" not in (
        " ".join(docstring.split())
    )
    assert "`requirement-decomposition` is one of the categories reading" not in (
        " ".join(docstring.split())
    )
    context = _CONTEXT.read_text(encoding="utf-8")
    assert _CONTEXT_SENTENCE in context
    assert "(`investigation` today;" not in context
    assert (
        "\"`investigation` read zero until round 10 filled its Python cell; "
        "`requirement-decomposition` is one of the categories reading zero "
        "today\""
    ) in said
    assert (
        "\"`investigation` was one until round 10 filled its Python cell\""
    ) in said
    # The three older exemplar pins, verified and not re-edited: each names
    # the category that reads zero today. Round 10's ticket 05 pointed them
    # at `requirement-decomposition`; round 11's first task re-pointed them
    # at `performance-optimisation`, the next category with no task in any
    # language.
    for suite, needle in (
        ("test_firstparty_v1_round7_cells.py", "performance-optimisation"),
        ("test_firstparty_v1_round7_record.py", "performance-optimisation"),
        ("test_firstparty_v1_round8_record.py", "performance-optimisation"),
    ):
        assert needle in (_REPO / "tests" / suite).read_text(encoding="utf-8")


def test_the_a_double_prime_readings_are_carried_with_their_disclosure() -> None:
    """Section 91 carries §84's readings forward with the knowable-outcome
    disclosure restated beside them, and the counts it quotes are §84.2's own
    — read out of that section's table rather than retyped here."""
    table = next(
        block
        for block in fenced_blocks(
            note_part("Round 10 A″ readings — read 2026-08-23")
        )
        if "operationalisation" in block
    )
    folded = " ".join(table.split())
    assert "file-reference 17 46" in folded
    assert "file-or-symbol 15 48" in folded

    carried = prose(note_section("91. The A″ readings, carried forward as readings"))
    assert (
        "**The disclosure first, in as many words: the A″ read is a "
        "derivation over spent rulings, and its outcome is knowable at "
        "registration time.**"
    ) in carried
    assert "not a blind pre-registration and does not claim to be one" in carried
    assert "**They are readings and they gated nothing.**" in carried
    assert "catches 17 of stratum A's 63 rows" in carried
    assert "denominator of 46" in carried
    assert "catches 15 and leaves 48" in carried
    assert (
        "a gate whose verdict flips on tokenisation minutiae certifies "
        "nothing"
    ) in carried
    assert "read and not scored" in carried
    assert "the round's one gate was §86's proofs" in carried
    # No verdict furniture: a reading carried forward is still not a verdict.
    for verdict in ("NOT MET", " MET", "FAILED", "PASSED"):
        assert verdict not in note_section(
            "91. The A″ readings, carried forward as readings"
        ), verdict


def test_what_this_round_cannot_say_is_stated_and_true_of_the_corpus(
    tasks: dict[str, firstparty_v1.Task],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 92's refusals, each anchored to something checkable, and the
    two disclosures the ticket wants in as many words: the covered-but-
    mediocre narrowing and the transfer gap, with the owner's ~9 labels
    recorded as given 2026-08-25 — a disclosed, non-gating check whose result
    is stated rather than passed over."""
    swept = {task_id for task_id, _ in rulings}
    assert all(tasks[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if tasks[task_id].construction is not None
    ]
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS

    said = prose(note_section("92. What this round cannot say"))
    assert "**Covered is not brilliant — the narrowing, in as many words.**" in said
    assert (
        "Covering every planted point does not certify a brilliant proposal"
    ) in said
    assert "an agent can cover every planted point with a mediocre one" in said
    assert "never a certificate of quality beyond its key" in said

    assert "**The transfer gap, restated from §79.4 and §81.4.**" in said
    assert (
        "would have proved the grader judges argued prose against a known "
        "truth — not that it judges a proposal with no truth behind it"
    ) in said
    assert "narrows the gap without closing it" in said
    assert "the proofs' truth is still the author's planted truth" in said

    # Supplied 2026-08-25, the day after the record: nine of nine agree,
    # recorded beside the section exactly as given, per its own sentence.
    assert (
        "**The owner's ~9 agree/disagree labels: given 2026-08-25, one day "
        "after this record — nine of nine agree.**"
    ) in said
    labels_block = [
        block
        for block in fenced_blocks(note_section("92. What this round cannot say"))
        if "agree" in block
    ]
    assert len(labels_block) == 1, "the labels table, fenced, once"
    assert labels_block[0].count("agree   (machine:") == 9
    assert "disagree  " not in labels_block[0]
    assert "the transfer gap §79.4 named did not open" in said
    assert "§76.2 ruled and §77.2 registered" in said
    assert "a disclosed, non-gating check" in said
    assert "The check gated nothing and the nine verdicts stood regardless" in said
    assert "the owner held the universal quantifier both times" in said

    assert "**No cross-action difficulty comparison.**" in said
    assert "1 of 9 here is not to be read against round 8's 8 of 9" in said
    assert "**Nothing about `investigation` × `typescript`.**" in said
    assert "**No Codex rung.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No multiplier.**" in said


def test_the_limits_and_toolchain_paragraphs_hold_against_the_code(
    round_10: dict[tuple[str, str], firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 85's limits and toolchain paragraphs, against the table the
    runner reads and the interpreter the suite runs on."""
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    swept = {task_id for task_id, _ in round_10}
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in tasks.values()
        if task.id in swept
    } == {600} == {firstparty.RUN_TIMEOUT_S}

    latencies = [run.latency_s for run in round_10.values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600
    longest = max(round_10.items(), key=lambda item: item[1].latency_s)
    assert longest[0] == (_DRY_CELL, _SONNET)

    assert platform.python_version() == _PYTHON_VERSION

    measured = prose(note_section("85. What the round measured"))
    assert (
        "**The limits in force: the flat default of 600 seconds, every "
        "cell.**"
    ) in measured
    assert "ran **at the flat default** rather than under a registered 600 s" in measured
    assert "**no cross-round caveat arises**" in measured
    assert f"the round's longest run was **{_LONGEST_S} s**" in measured
    assert f"the mean was **{_MEAN_S} s**" in measured
    assert f"Python {_PYTHON_VERSION}" in measured
    assert point_grader.GRADER_VERSION in note_section(
        "85. What the round measured"
    ), "the instrument, quoted from the code the round ran on"
    assert "**provenance and not a row field**" in measured
    assert "no `grader` field" in measured


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 93's replay, run rather than remembered — and offline.

    Each of the four logs is replayed into a scratch dataset of its own, and
    all four into one merged dataset; the four together must be the merged
    one, record for record, and every record carries its log row's own
    measurements. The module's detonator fixture is what makes "no grader
    client is constructed" structural: `--replay` passes no factory, so a
    missing archive would raise, not re-grade.
    """
    per_log: list[dict[str, object]] = []
    merged_path = tmp_path / "merged.jsonl"
    for name, (evaluated, resolved) in _REPLAYED.items():
        log = _LOGS / name
        alone = tmp_path / name
        for data in (alone, merged_path):
            main(["eval-v1", "--tasks", str(_TASKS), "--replay", str(log),
                  "--data", str(data), "--rulings", str(_RULINGS)])
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
    assert sum(float(record["quality_value"]) for record in merged) == 1

    printed_block = fenced_blocks(note_section(
        "93. Replay, the readers, and heap 3 opened"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed_block

    said = prose(note_section("93. Replay, the readers, and heap 3 opened"))
    assert (
        "**Every round-10 log replays to the verdicts this record quotes, "
        "with the network unplugged.**"
    ) in said
    assert "handed **no grader factory**" in said
    assert "9 rows and 1 resolved" in said
    assert "a table-derived cost is not recomputed on the way through" in said


def test_both_readers_count_the_round_and_print_what_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 93's readers: six of the nine rows inside the default view, the
    reconcile lines it quoted named as moved by round 11's arrivals, the
    calibrate table exactly as printed, and the earlier rounds' published
    tables unmoved."""
    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    [quoted] = fenced_blocks(note_section(
        "93. Replay, the readers, and heap 3 opened"
    ))[1:2]
    # The whole block has moved since, in three arrivals: round 11's three
    # `requirement-decomposition` tasks, Python controls, grew the task-set
    # line by three tasks and three controls, the round's sweep (2026-08-26
    # — nine rows, six of them claude-code Python) then grew the runs line
    # and joined the round list, and round 12's first explain-style
    # `codebase-comprehension` task grew the task-set line once more. The
    # record is not edited for any of it — each line it quoted is named
    # here, round 7's own pattern, and what the readers print instead is
    # asserted beside it.
    recorded = [
        "  task set   tasks/first-party-v1 — 119 task(s): 52 control(s), "
        "67 constructed",
        "  runs       237 over 119 task(s)",
        "  rounds     8 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10",
        "             6 keyed on a sweep id, 2 on an as-of date",
    ]
    quoted_lines = quoted.strip("\n").splitlines()
    assert quoted_lines == recorded, (
        "the record no longer quotes the lines its own figures rebuild"
    )
    for line in recorded:
        assert line not in printed, line
    assert (
        "  task set   tasks/first-party-v1 — 123 task(s): 56 control(s), "
        "67 constructed"
    ) in printed
    assert "  runs       243 over 122 task(s)" in printed
    assert (
        "  rounds     9 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10, sweep round-11"
    ) in printed
    assert "             7 keyed on a sweep id, 2 on an as-of date" in printed
    assert printed.count(f"sweep {_SWEEP}") == 1
    assert _CATEGORY not in printed, (
        "the round declared no contrast, so it reaches the report as a "
        "label and nothing else"
    )
    assert "   67 constructed task(s): 67 swept, 0 unswept" in printed

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    [table] = fenced_blocks(note_section(
        "93. Replay, the readers, and heap 3 opened"
    ))[2:3]
    assert table.strip("\n") in calibrated, (
        "the calibration table the record quotes is not what the reader prints"
    )
    assert f"category {_CATEGORY}" in calibrated
    assert "   (zero-knob)  3      1.00x (n=3)       1.00x (n=3)" in calibrated

    said = prose(note_section("93. Replay, the readers, and heap 3 opened"))
    assert "**And the readers count the round with no flag at all.**" in said
    assert "**The prediction reconciliation is unmoved**" in said
    assert "a **denominator**" in said
    assert "The published tables of earlier rounds are unmoved" in said


def test_nothing_from_the_round_reached_the_unified_dataset(
    runs: list[firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 93's last claims: the unified dataset untouched, the free-text
    archive grown by exactly the nine answers, and the registered split the
    A″ readings are computed over unmoved."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        flat = json.dumps(json.loads(line))
        for needle in (
            "investigation", "granary", "pumphouse", "ferryhouse",
            "point-gate-calibration", "pointer-filtered", "proofs",
            _SWEEP,
        ):
            assert needle not in flat, needle

    # Round 11's sweep has since landed nine more answers (2026-08-26); §93's
    # claim is about the archive as this round left it, so they are scoped
    # back out by sweep id, never by a log filename, and the section's
    # figures stay unretyped.
    archived = [
        run for run in runs if run.output and run.sweep != "round-11"
    ]
    assert len(archived) == _ARCHIVE_NOW
    assert len(
        [run for run in archived if run.sweep != _SWEEP]
    ) == _ARCHIVE_BEFORE
    stratum_a = [
        run
        for run in runs
        if run.sweep not in {_SWEEP, "round-11"}
        and firstparty_v1.carries_a_key(tasks[run.task_id])
    ]
    assert len(stratum_a) == _STRATUM_A

    said = prose(note_section("93. Replay, the readers, and heap 3 opened"))
    assert (
        "**Nothing from the calibration, the readings or the proofs reached "
        "`data/unified.jsonl`.**"
    ) in said
    assert "a combination's result on a benchmark instance (§76.11)" in said
    assert (
        "**306 answers across nine sweeps to 315 across ten**"
    ) in said
    assert "**306 rows, 63 of them stratum A**" in said
    assert "out of that read rather than an error in it" in said


def test_the_record_takes_the_next_free_numbers_and_renumbers_nothing() -> None:
    """Sections 85-93 are the next free numbers after §84, contiguous, each
    spent once, landing before the note's trailing headings — and the last
    section names the next free number, which is the frontier sentence the
    round-9 suite's moved assertion reads."""
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(84) == 1
    assert all(numbered.count(number) == 1 for number in range(85, 94))
    # The frontier claim this test carried — §93 the frontier, §94 free — was
    # spent when round 11's rulings took §94 (2026-08-25); the frontier itself
    # is the round-9 suite's to assert (one assertion, moved deliberately,
    # never copied). What survives here is that the record's nine numbers are
    # spent once each and nothing above or below them was renumbered — a claim
    # the contiguity range extends over §95 (round 11's pre-registration), §96
    # (round 11's amendment, both 2026-08-26), §97-§105 (round 11's record,
    # 2026-08-27), §106 (round 12's rulings) and §107 (round 12's
    # pre-registration, both 2026-08-28) to keep making.
    assert [number for number in numbered if number > 68] == list(range(69, 108))

    for heading in record_sections():
        assert f"### {heading}\n" in text, heading

    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    record_at = headings.index("## Round 10 record — 2026-08-24")
    assert headings[record_at - 1].startswith("## Round 10 A″ readings")
    # The heading after the record was `## Open questions` until round 11's
    # rulings landed there (2026-08-25); the claim that survives is that the
    # record sits inside the note's numbered run, before the trailing headings.
    assert headings[record_at + 1].startswith("## Round 11 rulings")

    opening = prose(
        note_part("Round 10 record — 2026-08-24").split("\n### ")[0]
    )
    assert "**§85 is the next free number.**" in opening
    assert "this record opens at **85** and runs to **93**" in opening
    assert "Nothing above it is renumbered." in opening

    closing = prose(note_section("93. Replay, the readers, and heap 3 opened"))
    assert "**Heap 3 opens.**" in closing
    assert "**§94 is the next free section number**" in closing
    assert "nothing above is renumbered" in closing
