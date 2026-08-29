"""Round 12's record, pinned: what sections 108-116 of the design note publish.

The round swept nine cells over **three explain-style `codebase-comprehension`
tasks** — heap 3's last action, the mechanical fill §103 licensed and §106
ruled, closing the heap — and the point gate scored it **7 of 9**: its first
round with more cells resolved than not. The record's one reading is §89's,
carried onto the new action with its shape reversed: **no planted point went
uncovered anywhere** — all 45 point-rulings are covered with verified spans —
so both red cells are read as the named disqualifier each claimed, spans
quotable, and the false-red shape §104's addendum found had no opportunity to
recur under §106.1's one-clause-tight keys and did not. The standing
temptation is the coverage fraction — "four of five covered" — which ADR-0004
refused for mutants and ADR-0005 refuses for points, so this file checks that
no fraction over planted points is quoted as a quality figure anywhere in the
round's own sections.

Every figure is re-derived from the artifact that earned it: the checked-in
run logs (collected wholesale, selected by **sweep id `round-12`** and never
by a log's filename — the sweep protocol's rule), the per-cell rulings
archives under `data/first-party-v1-rulings/`, the tasks' own `proofs/`
archives, the lint's printed coverage table and the readers' actual output.
The design note's own tables are rebuilt from those artifacts and compared
whole, and each section is sliced **from its own heading to the next
heading** — never to `## Open questions` or any landmark further down, the
rule `docs/agents/runbook-grader-v2-gate.md:153` writes down.

**Everything here is offline and no grader client is constructed.** Every
verdict is recomputed from archived rulings through `_point_verdict`, replay
is handed no factory by construction, and
`point_grader.deepseek_point_grader` is replaced by a detonator for the whole
module, so a construction anywhere in this file is a failure rather than a
silent live call.

§80.5's freezing rule, carried forward in one line: this suite reaches the
live `point_grader.GRADER_VERSION`, `point_grader.PROMPT` and the live span
rule (`span_in_deliverable`, via `_point_verdict` and `_the_span_holds`)
because v2 is the instrument the round's rulings were taken under; the next
time the instrument moves, this suite freezes to v2's literal tuple, the
template length and the archived rulings' own spans, with a comment naming
§108.
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
_RUNBOOK = _REPO / "docs" / "agents" / "runbook-round-12-proofs.md"

_SWEEP = "round-12"
_ANCHOR = "round-11"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-28"
_CATEGORY: TaskCategory = "codebase-comprehension"

# The versions the rows carry — and this round crosses no boundary at all:
# both harness versions are round 11's exactly, the first of the three
# point-gate sweeps with nothing to narrate, which §108 says in as many words.
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.246 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}

# The four logs the sweep's four invocations wrote, and what each replays to.
# Named only so that section 116's replay can be given one log at a time;
# nothing here selects runs by them.
_REPLAYED = {
    "2026-08-28-r12-a.jsonl": (1, 1),
    "2026-08-28-r12-b.jsonl": (2, 1),
    "2026-08-28-r12-c.jsonl": (3, 2),
    "2026-08-28-r12-d.jsonl": (3, 3),
}
_DRY_CELL = "ropewalk-explain-how-an-order-becomes-a-coil"
_CHEAPEST_CELL = "tramshed-explain-why-the-two-boards-disagree"
_RED_TASK = "grocers-explain-why-the-plain-hamper-carries-the-cordial"

# Section 110's sweep spend, per combination and per cost source, and the
# registered range it is read against. This round the range was missed on the
# low side — the miss §107.7 pre-read as the likelier, on both of the routes
# it named — so the floor below is asserted to sit above the total.
_SPEND = {_HAIKU: 0.2113, _SONNET: 0.4543, _TERRA: 0.2529}
_BILLED = 0.6656
_TOTAL = 0.9184
_COLUMN_SUM = 0.9185  # the printed columns' own sum, a ten-thousandth over
_PER_CELL = {_HAIKU: 0.0704, _SONNET: 0.1514, _TERRA: 0.0843}
_REGISTERED_RANGE = (1.3, 2.5)
_FLAT_EXTRAPOLATION = 1.3206
_FLAT_EXTRAPOLATION_RATIO = 0.70
_UNDER_THE_FLOOR = 0.38
_ROUND_11_COLUMN = {_HAIKU: 0.2385, _SONNET: 0.8253, _TERRA: 0.2568}
_ROUND_11_PER_CELL = {_HAIKU: 0.0795, _SONNET: 0.2751, _TERRA: 0.0856}
_COLUMN_RATIO = {_HAIKU: 0.89, _SONNET: 0.55, _TERRA: 0.98}
_SONNET_FALL = 0.3710
_TOTAL_FALL = 0.4022

# Section 110's token evidence: the action route sits on the two claude
# columns — sonnet wrote far less than a decomposition — while the Codex
# column read *more* than round 11's and still came in under, which is the
# cache route and not the action.
_TOKENS_PER_CELL = {
    _HAIKU: (142_724, 5_259),
    _SONNET: (172_814, 5_044),
    _TERRA: (120_599, 2_617),
}
_ROUND_11_TOKENS_PER_CELL = {
    _HAIKU: (213_250, 5_338),
    _SONNET: (240_069, 12_732),
    _TERRA: (104_273, 2_516),
}

# Section 110's Codex bounds at the round's own tokens, and the effective rate.
_CODEX_TOKENS = (361_796, 7_851)
_ALL_CACHED = 0.1666
_ALL_UNCACHED = 0.8178
_EFFECTIVE_RATE = 0.4385
_ROUND_11_EFFECTIVE_RATE = 0.5314
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 110's proofs: 42 metered calls against §107.6's registered 24-48,
# zero retries — the arithmetic's components are re-derived from checked-in
# text below, never trusted from these constants alone.
_METERED_LOW, _METERED_HIGH = 24, 48
_PROOF_CALLS = 42
_PROOF_RANGE = (0.05, 0.6)
_DEEPSEEK_INPUT_PER_MTOK = 1.32
_DEEPSEEK_OUTPUT_PER_MTOK = 3.96
_PROOF_ANSWER_CHAR_CAP = 8_000

# Section 108's resolution line: the point gate's first majority-green round.
_RESOLVED = {_HAIKU: 2, _SONNET: 2, _TERRA: 3}

# Section 108's limits paragraph.
_LONGEST_S = 92.3
_MEAN_S = 69.2
_PYTHON_VERSION = "3.14.4"

# Section 111's turn line, quoted so section 115's refusal has an anchor.
_TURNS = {_HAIKU: 27, _SONNET: 22, _TERRA: 25}
_TURN_RANGE = {_HAIKU: (9, 9), _SONNET: (4, 10), _TERRA: (7, 11)}

# Section 112's reading: the two red cells, both on the grocers task's second
# disqualifier, with every planted point of the round covered everywhere.
_RED_DISQUALIFIER = "an-extra-on-the-wrong-hamper"
_RED_CELLS = {(_RED_TASK, _HAIKU), (_RED_TASK, _SONNET)}
_POINT_RULINGS = 45
_GATE_RULINGS = 63

# Section 109's foils: each claims both of its key's disqualified claims; the
# grocers foil additionally drew one false-positive coverage on its own
# wrong-claim span, which the record discloses where the foil's failure is
# named both ways.
_FOIL_DISQUALIFIERS = {
    _DRY_CELL: ("cut-to-the-asked-length", "a-short-rack-makes-what-it-can"),
    _RED_TASK: ("a-copy-per-hamper", _RED_DISQUALIFIER),
    _CHEAPEST_CELL: (
        "two-separately-kept-lists", "listed-in-the-order-entered"
    ),
}
_FOIL_FALSE_POSITIVE = (_RED_TASK, "one-list-across-the-standard-hampers")
_FOIL_FALSE_POSITIVE_SPAN = (
    "each standard hamper starts from its own copy of the standard list"
)

# Section 116's archive line: the free-text archive across twelve sweeps, and
# the registered split the A″ readings stay computed over.
_ARCHIVE_BEFORE = 324
_ARCHIVE_NOW = 333
_STRATUM_A = 63

# Section 113's zero-exemplar sites, verified unmoved — no zero row became a
# filled one this round, so the round-11-era sentences stand as they were.
_CONTEXT_SENTENCE = (
    "(`performance-optimisation` today; `test-authoring` was one until "
    "round 8 authored its three Python tasks, `investigation` was one until "
    "round 10 filled its Python cell, and `requirement-decomposition` was "
    "one until round 11 filled its Python cell)"
)


@pytest.fixture(scope="module", autouse=True)
def no_grader_can_be_built() -> Iterator[None]:
    """The offline claim, made structural for the whole module.

    §116 says the round's rows replay with the network unplugged and no
    grader client constructed. Nothing below should reach the one factory
    there is, so the factory is replaced by a detonator: a construction
    anywhere in this file fails the suite instead of quietly asking for a
    key.
    """
    original = point_grader.deepseek_point_grader

    def refuse() -> point_grader.PointGrader:
        raise AssertionError(
            "the round-12 record is a recomputation over archived rulings — "
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
        "108. What the round measured",
        "109. The gate opened: every reference resolved, every foil failed",
        "110. Spend, by cost source, against both registered ranges",
        "111. The nine cells under three combinations",
        "112. The two red cells, read as the disqualifier each claimed",
        "113. The coverage table, as the lint prints it",
        "114. The false-red shape did not recur, and the loader's move is "
        "landed",
        "115. What this round cannot say",
        "116. Replay, the readers, and heap 3 closed",
    ]


_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def registered_cells() -> list[str]:
    """§107.8's filled register, read back out of the pre-registration, so
    what the round swept is compared against the register itself and never a
    copy."""
    for block in fenced_blocks(
        note_part("Round 12 cells and cost — registered 2026-08-28")
    ):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        matched = [
            match for line in lines if (match := _REGISTER_LINE.fullmatch(line))
        ]
        if len(matched) == len(lines) and all(
            match.group(2) for match in matched
        ):
            return [match.group(1) for match in matched]
    raise AssertionError("§107.8's filled register is not in the note")


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
def round_12(
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
    round_12: dict[tuple[str, str], firstparty_v1.Run],
) -> dict[tuple[str, str], tuple[bool, list[str], list[str]]]:
    """Every cell's verdict, uncovered points and present disqualifiers,
    recomputed from the archived rulings against the deliverable the diff
    collects — the very computation replay runs, with no grader anywhere.

    The verdict is taken from `_point_verdict` — the shipped gate — and the
    per-point reading beside it re-applies the same span rule, so this is a
    reading of the one grading pipeline and not a second one that happens to
    agree with it. Unlike round 11's fixture, which asserted exactly two
    demotions, this one asserts **none**: every one of the round's 63 rulings
    quotes a span its deliverable contains, so `covered` and `verified` agree
    everywhere and §76.6's rule checked 63 quotations and demoted nothing —
    a third state would be a fact the record does not tell (§112).
    """
    derived: dict[tuple[str, str], tuple[bool, list[str], list[str]]] = {}
    demoted: dict[tuple[str, str], str] = {}
    for (task_id, model), run in sorted(round_12.items()):
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
        # One instrument over the whole round: §107.1's stop never fired.
        assert archive.grader_version == point_grader.GRADER_VERSION
        questions = firstparty_v1._point_questions(key)
        assert len(archive.rulings) == len(questions) == 7, (task_id, model)
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
            # The archive's own word agrees with the recomputation: what the
            # sweep verified is what this suite re-verifies.
            assert covered == entry.verified, (task_id, model, planted.id)
            if covered != entry.covered:
                demoted[(task_id, model)] = planted.id
            if kind == "point" and not covered:
                uncovered.append(planted.id)
            if kind == "disqualifier" and covered:
                present.append(planted.id)
        derived[(task_id, model)] = (verdict, uncovered, present)
    assert demoted == {}, "zero demotions this round — §112's departure"
    return derived


def cell_table(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 111's table, rebuilt from the logs and the recomputed verdicts
    — byte for byte, headers and cost sources included."""
    ids = sorted({task_id for task_id, _ in round_12})
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
            columns.append(f"{verdict} ${round_12[task_id, model].cost_usd:.4f}")
        lines.append(
            (f"{task_id:<{width}}  "
             + "  ".join(f"{column:<18}" for column in columns)).rstrip()
        )
    return "\n".join(lines) + "\n"


def disqualifier_table(
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 112's table, rebuilt from the archived rulings: per cell, the
    present disqualifiers — never a count of anything and never a fraction."""
    ids = sorted({task_id for task_id, _ in rulings})
    labels = [(task_id, model) for task_id in ids for _, model in _COMBINATIONS]
    width = max(len(f"{task_id} x {model}") for task_id, model in labels)
    lines = [f"{'cell':<{width}}  present disqualifier(s)"]
    for task_id, model in labels:
        verdict, uncovered, present = rulings[task_id, model]
        assert not uncovered, "no planted point went uncovered anywhere"
        body = (
            ", ".join(present)
            if present
            else "none — every point covered, no disqualifier present"
        )
        assert bool(present) != verdict, (task_id, model)
        pad = width - len(task_id) - 3
        lines.append(f"{task_id} x {model:<{pad}}  {body}")
    return "\n".join(lines) + "\n"


def proof_block_chars(
    tasks: dict[str, firstparty_v1.Task], task_ids: list[str]
) -> tuple[int, int, int]:
    """Calls, input characters and quoted-whole characters for one selection
    of tasks, both sides, at the live template — §96.1's own convention."""
    template = len(point_grader.PROMPT)
    calls = input_chars = quoted = 0
    for task_id in task_ids:
        task = tasks[task_id]
        questions = firstparty_v1._point_questions(firstparty_v1.points_key(task))
        for side in firstparty_v1.PROOF_SIDES:
            answer = (task.proofs_dir / side.answer_file).read_text(
                encoding="utf-8"
            )
            for _, planted in questions:
                calls += 1
                input_chars += template + len(planted.text) + len(answer)
                quoted += len(answer)
    return calls, input_chars, quoted


def test_the_round_swept_exactly_the_cells_that_were_registered(
    tasks: dict[str, firstparty_v1.Task],
    runs: list[firstparty_v1.Run],
    round_12: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 108's sweep facts, off the rows themselves, against §107.8.

    The register is read out of the pre-registration rather than restated.
    One sweep id, one as-of date, one version per harness — and this round
    crosses no version boundary at all: both versions are round 11's exactly,
    checked against round 11's own rows rather than against a memory of them.
    """
    assert {run.sweep for run in round_12.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in round_12.values()} == {_AS_OF}
    assert {
        (run.agent, run.model) for run in round_12.values()
    } == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version
            for run in round_12.values()
            if run.agent == agent
        } == {version}, agent

    # No boundary: round 11's rows carry the same two versions, read off the
    # rows themselves rather than quoted from §97.
    round_11 = [run for run in runs if run.sweep == _ANCHOR]
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version for run in round_11 if run.agent == agent
        } == {version}, f"{agent}: no version boundary this round"

    registered = registered_cells()
    assert len(registered) == 3 == len(set(registered))
    assert {task_id for task_id, _ in round_12} == set(registered)
    assert {tasks[task_id].category for task_id in registered} == {_CATEGORY}
    assert {tasks[task_id].language for task_id in registered} == {"python"}
    assert {tasks[task_id].surface for task_id in registered} == {"application"}
    assert all(tasks[task_id].control for task_id in registered)
    assert set(registered) == {
        task.id
        for task in tasks.values()
        if task.category == _CATEGORY and firstparty_v1.is_point_keyed(task)
    }, "every point-keyed codebase-comprehension task the corpus holds"
    assert len(
        [task for task in tasks.values() if task.category == _CATEGORY]
    ) == 7, "the category's four locate-style tasks stand beside them"

    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(note_section("108. What the round measured"))
    assert "**Nine cells, and they are exactly the nine §107.8 registered.**" in measured
    assert "**9 of 9**" in measured
    assert "**heap 3's last action's cells**" in measured
    assert "**heap 3 closes with them**" in measured
    assert "**no second quality metric enters the table**" in measured
    assert "**crosses no version boundary**" in measured
    assert "**2.1.246**, round 11's exactly" in measured
    assert (
        "**codex-cli 0.147.0**, rounds 6, 7, 8, 10 and 11's exactly"
    ) in measured
    assert "the first of the three point-gate sweeps with no boundary" in measured


def test_the_dry_cell_and_the_four_logs_are_what_the_record_says(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 108's invocation paragraph, against the checked-in logs.

    The dry cell was one of the nine, run alone in its own invocation, graded
    alone before the other eight, and its verdict is the gate's first on this
    action's deliverable shape: resolved, every planted point covered and
    neither disqualifier claimed — the verdict shape arriving well-formed.
    The registration's word "cheapest" is checked against what the rows
    actually cost: this round the column half of the reading held and the
    cell half did not, which the record says rather than passes over.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 9
    assert min(counted.values()) > 0, "no invocation of this round logged nothing"

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-28-r12-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    verdict, uncovered, present = rulings[_DRY_CELL, _HAIKU]
    assert verdict is True and not uncovered and not present, (
        "the gate's first paid verdict on this action: resolved, every "
        "planted point covered, neither disqualifier claimed"
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

    # "Cheapest" held of the column and not of the cell: at round 11's anchor
    # the haiku column was the cheaper and in the event it was, but the dry
    # cell itself was not the round's cheapest cell.
    assert _ROUND_11_PER_CELL[_HAIKU] < _ROUND_11_PER_CELL[_TERRA]
    assert _PER_CELL[_HAIKU] < _PER_CELL[_TERRA]
    cheapest = min(round_12.items(), key=lambda item: item[1].cost_usd)
    assert cheapest[0] == (_CHEAPEST_CELL, _HAIKU)
    assert round(cheapest[1].cost_usd, 4) == 0.0655
    assert round(round_12[_DRY_CELL, _HAIKU].cost_usd, 4) == 0.0714

    measured = prose(note_section("108. What the round measured"))
    assert "**Four invocations, four logs, none of them empty.**" in measured
    assert "**graded alone before the other eight**" in measured
    assert (
        "**resolved**, every planted point covered by a span the gate "
        "verified and neither disqualifier claimed"
    ) in measured
    assert (
        "this round the column half of that reading held"
    ) in measured
    assert "**$0.0704** a cell against Codex's **$0.0843**" in measured
    assert "the dry cell itself cost **$0.0714**" in measured
    assert "`tramshed` on haiku at **$0.0655**" in measured
    assert "held of the column and not of the cell" in measured


def test_the_gate_opened_on_all_three_keys_before_the_first_sweep_dollar(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 109: the round's one gate, recomputed from the proof archives.

    §107.5's quantifier, checked as a quantifier: every planted point of every
    reference answer resolves and every foil fails, through the very
    `_point_verdict` a run is graded by. The foils' two-sided failure — both
    disqualified claims made *and* planted points left uncovered — is
    re-derived per task, along with the one proofs-side ruling the record
    discloses: the grocers foil's false-positive coverage on its own
    wrong-claim span, which the verdict absorbs.
    """
    for task_id, disqualifiers in _FOIL_DISQUALIFIERS.items():
        task = tasks[task_id]
        key = firstparty_v1.points_key(task)
        assert (len(key.points), len(key.disqualifiers)) == (5, 2)
        questions = firstparty_v1._point_questions(key)
        assert len(questions) * 2 == 14, "14 archived calls a task"
        assert 8 <= len(questions) * 2 <= 16, "§107.6's per-task range"
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
                assert not any(
                    covered[disqualifier] for disqualifier in disqualifiers
                ), f"{task_id}: the reference trips neither disqualifier"
            else:
                assert all(
                    covered[disqualifier] for disqualifier in disqualifiers
                ), f"{task_id}: the foil claims both disqualified claims"
                point_coverage = {
                    planted.id: covered[planted.id]
                    for kind, planted in questions
                    if kind == "point"
                }
                if task_id == _FOIL_FALSE_POSITIVE[0]:
                    # The disclosed ruling: one point covered off the foil's
                    # own wrong-claim span — a false positive the verdict
                    # absorbs, with the other four points uncovered.
                    assert point_coverage.pop(_FOIL_FALSE_POSITIVE[1]) is True
                    entry = by_question["point", _FOIL_FALSE_POSITIVE[1]]
                    assert entry.covered and entry.verified
                    assert entry.span is not None
                    assert _FOIL_FALSE_POSITIVE_SPAN in entry.span
                    # The span holds under the instrument's normalisation —
                    # that is what `verified` records and what the coverage
                    # popped above already re-checked through the span rule.
                assert not any(point_coverage.values()), (
                    f"{task_id}: the foil leaves the other planted points "
                    "uncovered"
                )

    # The rule the section names is the one the lint runs for this action,
    # dispatched by the key on disk — §107.5's shape-aware form.
    assert (
        firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].check
        is firstparty_v1._the_comprehension_proof_the_key_on_disk_asks_for
    )

    certified = prose(note_section(
        "109. The gate opened: every reference resolved, every foil failed"
    ))
    assert (
        "**The round's one hard gate was read before the first sweep dollar, "
        "and it opened.**"
    ) in certified
    assert "§98 is its form, a round on" in certified
    assert (
        "**every planted point of every task's reference answer resolved, "
        "and every foil answer failed**"
    ) in certified
    assert "no fraction met, no proportion computed, no threshold" in certified
    assert "**these three keys discriminate**" in certified
    assert "**five points and two disqualifiers**" in certified
    assert "**14 archived calls a task**" in certified
    assert "inside §107.6's registered 8–16 a task" in certified
    assert "every foil failed **both ways at once**" in certified
    assert "claimed **both** of its task's disqualified claims" in certified
    assert "**false-positive coverage on foil prose**" in certified
    assert f'"{_FOIL_FALSE_POSITIVE_SPAN}"' in certified
    assert "both disqualifiers claimed and four points uncovered" in certified
    assert (
        "no registered rule requires a foil to score zero per point"
    ) in certified
    assert "`_the_reference_resolves_and_the_foil_fails`" in certified
    assert "`_the_comprehension_proof_the_key_on_disk_asks_for`" in certified
    assert "the stop §107.5 kept armed did not fire" in certified


def test_the_sweep_cost_what_the_record_states_by_cost_source(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 110's sweep spend, pinned per cost source and per cell, and the
    registered range it landed under.

    The landing is the point this round: §107.7 registered $1.3-2.5 with the
    low miss named as the likelier on two routes, and both happened — the
    action route on the two claude columns, the cache route on the Codex
    column — so this test asserts the total sits under the floor and that
    both routes are checked open, with the per-cell token evidence re-derived
    beside them and the two kept separate.
    """
    ids = sorted({task_id for task_id, _ in round_12})
    for model, spend in _SPEND.items():
        actual = sum(round_12[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 3, 4) == _PER_CELL[model], model
        assert round(
            actual / _ROUND_11_COLUMN[model], 2
        ) == _COLUMN_RATIO[model], model

    billed = sum(
        run.cost_usd
        for run in round_12.values()
        if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED
    total = sum(run.cost_usd for run in round_12.values())
    assert round(total, 4) == _TOTAL
    # Summed before rounding — and this round the printed columns add to one
    # ten-thousandth over the rounded total, round 7's situation rather than
    # round 8's, which the record says rather than leaves to a checker.
    assert round(sum(_SPEND.values()), 4) == _COLUMN_SUM != _TOTAL

    low, high = _REGISTERED_RANGE
    assert total < low, "the registered range was missed on the low side"
    assert round(total / _FLAT_EXTRAPOLATION, 2) == _FLAT_EXTRAPOLATION_RATIO
    assert round(low - total, 2) == _UNDER_THE_FLOOR
    anchor = sum(_ROUND_11_COLUMN.values())
    assert round(anchor - total, 4) == _TOTAL_FALL
    sonnet_fall = _ROUND_11_COLUMN[_SONNET] - sum(
        round_12[task_id, _SONNET].cost_usd for task_id in ids
    )
    assert round(sonnet_fall, 4) == _SONNET_FALL

    # The token evidence, per cell, against round 11's — both re-derived.
    for model, (tokens_in, tokens_out) in _TOKENS_PER_CELL.items():
        assert round(sum(
            run.tokens_in for key, run in round_12.items() if key[1] == model
        ) / 3) == tokens_in, model
        assert round(sum(
            run.tokens_out for key, run in round_12.items() if key[1] == model
        ) / 3) == tokens_out, model
    # The two low-miss routes, checked open and kept separate: the claude
    # columns read and wrote less (sonnet's written column collapsing), while
    # the Codex column read and wrote *more* and still came in under — the
    # cache route, not the action.
    assert _TOKENS_PER_CELL[_SONNET][1] < _ROUND_11_TOKENS_PER_CELL[_SONNET][1]
    assert _TOKENS_PER_CELL[_SONNET][0] < _ROUND_11_TOKENS_PER_CELL[_SONNET][0]
    assert _TOKENS_PER_CELL[_HAIKU][0] < _ROUND_11_TOKENS_PER_CELL[_HAIKU][0]
    assert _TOKENS_PER_CELL[_TERRA][0] > _ROUND_11_TOKENS_PER_CELL[_TERRA][0]
    assert _TOKENS_PER_CELL[_TERRA][1] > _ROUND_11_TOKENS_PER_CELL[_TERRA][1]

    # Cost sources, on the rows and refused at load if contradicted.
    codex = {k: run for k, run in round_12.items() if run.agent == "codex"}
    claude = {
        k: run
        for k, run in round_12.items()
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
    assert _EFFECTIVE_RATE < _ROUND_11_EFFECTIVE_RATE, (
        "the cache-friendlier low-miss route happened"
    )

    read = prose(note_section(
        "110. Spend, by cost source, against both registered ranges"
    ))
    assert (
        "**The registered sweep range was $1.3–2.5. The round came to "
        "$0.9184, and the range was missed on the low side**"
    ) in read
    assert "$0.38 under the floor, at **0.70×** the flat extrapolation" in read
    assert "**summed before rounding**" in read
    assert (
        "the printed columns add to $0.9185, one ten-thousandth over the "
        "rounded total — round 7's situation rather than round 8's"
    ) in read
    assert (
        "**The miss is the one §107.7 pre-read as the likelier, and it "
        "arrived on both of the routes that section named**"
    ) in read
    assert "the $2.5 stop was never approached" in read
    assert "**What the account was actually billed for the sweep: $0.6656" in read
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read
    assert "**0.89×**, **0.55×** and **0.98×** round 11's" in read
    assert "$0.3710 of the round's $0.4022 fall" in read
    assert "a finding about the action and not an accounting surprise" in read
    assert "**$0.1666 all-cached** and **$0.8178 all-uncached**" in read
    assert "**$0.4385/M**" in read and "**$0.5314/M**" in read
    assert "a sixth point on one rate" in read
    assert "still not a separated cause" in read
    assert "**no new registration is opened**" in read

    blocks = fenced_blocks(note_section(
        "110. Spend, by cost source, against both registered ranges"
    ))
    assert blocks[0] == (
        "claude-code x haiku     $0.2113  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $0.4543  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $0.2529  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )
    for line in (
        "claude-code x haiku     $0.2385                $0.2113    $0.0704    $0.0795",
        "claude-code x sonnet    $0.8253                $0.4543    $0.1514    $0.2751",
        "codex x gpt-5.6-terra   $0.15-$0.72 (~$0.26)   $0.2529    $0.0843    $0.0856",
    ):
        assert line in blocks[1], line


def test_the_proofs_meter_met_the_registered_line_and_the_record_says_so(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 110's proofs: 42 metered calls against §107.6's 24-48, zero
    retries, and the arithmetic re-derived over text a reader holds.

    The input characters are recomputed from the six checked-in proof answers
    at the live template, the dollar bound is checked to sit inside the
    registered $0.05-0.6 at both ends, and §107.6's named price miss — an
    answer past 8,000 characters — is checked not to have happened on the
    checkable half.
    """
    template = len(point_grader.PROMPT)
    assert template == 1_461  # §80.5: freezes to this literal when v2 moves.

    calls, input_chars, quoted = proof_block_chars(
        tasks, sorted(_FOIL_DISQUALIFIERS)
    )
    assert calls == _PROOF_CALLS == 14 * 3
    assert _METERED_LOW <= calls <= _METERED_HIGH, "inside the registered line"
    assert input_chars == 227_954
    assert quoted == 7 * (4_373 + 4_389 + 4_804 + 2_871 + 3_133 + 3_598), (
        "quoted-whole characters are the six answers, once per question"
    )

    per_input = _DEEPSEEK_INPUT_PER_MTOK / 1e6
    per_output = _DEEPSEEK_OUTPUT_PER_MTOK / 1e6
    input_tokens = input_chars // 4
    assert input_tokens == 56_988
    low_out = calls * 100
    high_out = calls * 300 + quoted // 4
    assert (low_out, high_out) == (4_200, 53_144)
    total_low = round(input_tokens * per_input + low_out * per_output, 4)
    total_high = round(input_tokens * per_input + high_out * per_output, 4)
    assert (total_low, total_high) == (0.0919, 0.2857)
    range_low, range_high = _PROOF_RANGE
    assert range_low <= total_low and total_high <= range_high, (
        "the registered $0.05-0.6 holds at both ends"
    )

    # §107.6's named miss did not happen on the half that is checkable: no
    # proof answer of the round's three tasks is near 8,000 characters.
    lengths = {
        (task_id, side.name): len(
            (tasks[task_id].proofs_dir / side.answer_file).read_text(
                encoding="utf-8"
            )
        )
        for task_id in _FOIL_DISQUALIFIERS
        for side in firstparty_v1.PROOF_SIDES
    }
    assert set(lengths.values()) == {4_373, 4_389, 4_804, 2_871, 3_133, 3_598}
    assert all(
        length <= _PROOF_ANSWER_CHAR_CAP for length in lengths.values()
    )

    read = prose(note_section(
        "110. Spend, by cost source, against both registered ranges"
    ))
    assert (
        "**The proofs, against §107.6's registered 24–48 calls: the round "
        "metered 42, and the registered line was met with no operational "
        "overage.**"
    ) in read
    assert "**14 calls a task**" in read
    assert "one `--task`-selected invocation per task" in read
    assert "**zero retries**: no dead stream, no re-prove" in read
    assert "the meter and the archives counting the same calls" in read
    assert "**The registered $0.05–0.6 holds at both ends.**" in read
    assert (
        "reference answers of 4,373, 4,389 and 4,804 characters and foils of "
        "2,871, 3,133 and 3,598"
    ) in read
    assert "still the half with no anchor" in read
    assert "priced here at the registered peak-hour, cache-miss figures" in read
    assert "the console's figure can only sit at or under this arithmetic" in read
    assert "The sweep's own 63 grader calls (§108)" in read
    assert "one call per archived ruling and no retry" in read

    [block] = [
        block
        for block in fenced_blocks(note_section(
            "110. Spend, by cost source, against both registered ranges"
        ))
        if "proofs metered" in block
    ]
    for line in (
        f"proofs metered  {calls} calls x (template + point + answer)"
        f"          = {input_chars:,} chars / 4 =  {input_tokens:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(input_tokens * per_input, 4):.4f}",
        f"output low   {calls} x 100 tok thinking              =   "
        f"{low_out:,} tok  x ${_DEEPSEEK_OUTPUT_PER_MTOK}/M = "
        f"${round(low_out * per_output, 4):.4f}",
        f"output high  {calls} x 300 tok + every proof answer quoted whole  "
        f"=  {high_out:,} tok  x ${_DEEPSEEK_OUTPUT_PER_MTOK}/M = "
        f"${round(high_out * per_output, 4):.4f}",
        f"round total    ${total_low:.4f} - ${total_high:.4f}",
    ):
        assert line in block, line


def test_the_payment_path_is_disclosed_as_it_was_used() -> None:
    """Section 110's disclosure, and the runbook's same words: the DeepSeek
    key from the operator's session memory, supplied inline in the invoking
    environment by the owner's disclosed exception, and never printed."""
    read = prose(note_section(
        "110. Spend, by cost source, against both registered ranges"
    ))
    assert "**The payment path, disclosed where it was used.**" in read
    assert (
        "**supplied inline in the invoking command's environment from the "
        "operator's session memory**"
    ) in read
    assert "the owner's disclosed exception of 2026-08-23" in read
    assert "**never printed**" in read
    assert "committed to no file" in read

    runbook = _RUNBOOK.read_text(encoding="utf-8")
    assert "stored in the operator's session memory" in runbook
    assert "2026-08-23" in runbook
    assert "never printed" in runbook


def test_the_per_cell_table_is_what_the_logs_and_the_rulings_say(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 111's table, rebuilt from the artifacts and compared byte for
    byte — the only pin that cannot drift a cell at a time, headers and cost
    sources included."""
    quoted = fenced_blocks(
        note_section("111. The nine cells under three combinations")
    )[0]
    assert quoted == cell_table(round_12, rulings)

    resolved = {
        model: sum(
            1
            for (_, run_model), (verdict, _, _) in rulings.items()
            if run_model == model and verdict
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 7, "the first majority-green round"

    measured = prose(note_section("108. What the round measured"))
    assert "**Resolution: 7 of 9.**" in measured
    assert (
        "**2 of 3** on `claude-haiku-4-5`, **2 of 3** on `claude-sonnet-5` "
        "and **3 of 3** on `codex` × `gpt-5.6-terra`"
    ) in measured
    assert "first round with more cells resolved than not" in measured
    assert "**every planted point covered**" in measured

    said = prose(note_section("111. The nine cells under three combinations"))
    assert "There is no per-category block beside it" in said
    assert "no rate is quoted off it" in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 111's turn line, and the definition that makes it uncomparable
    across the harness boundary."""
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in round_12.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(note_section("111. The nine cells under three combinations"))
    assert (
        "Haiku took **27** turns over the three (9–9), sonnet **22** "
        "(4–10), Codex **25** (7–11)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_the_two_red_cells_are_read_as_the_disqualifier_each_claimed(
    tasks: dict[str, firstparty_v1.Task],
    round_12: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 112: §89's reading on the last action, with the shape
    reversed — every planted point covered everywhere, both reds a present
    disqualifier — and this round's departure from §101: zero demotions.

    The table is rebuilt from the archived rulings and compared byte for
    byte, so the record can never claim a disqualifier the archive does not.
    The two evidence spans the record quotes are checked against the archives
    and against the deliverables they must sit in, and the disqualifier's own
    key text is checked to be what the record says it is.
    """
    quoted = fenced_blocks(note_section(
        "112. The two red cells, read as the disqualifier each claimed"
    ))[0]
    assert quoted == disqualifier_table(rulings)

    point_rulings = 0
    for (task_id, model), (verdict, uncovered, present) in rulings.items():
        assert not uncovered, (task_id, model)
        point_rulings += len(firstparty_v1.points_key(tasks[task_id]).points)
        if (task_id, model) in _RED_CELLS:
            assert verdict is False and present == [_RED_DISQUALIFIER]
        else:
            assert verdict is True and not present
    assert point_rulings == _POINT_RULINGS, "45 point-rulings, all covered"
    assert point_rulings + 2 * 9 == _GATE_RULINGS

    said = prose(note_section(
        "112. The two red cells, read as the disqualifier each claimed"
    ))
    key = firstparty_v1.points_key(tasks[_RED_TASK])
    [disqualifier] = [
        planted for planted in key.disqualifiers
        if planted.id == _RED_DISQUALIFIER
    ]
    assert (
        "cordial reached Mrs Beech's hamper through a mix-up of orders or an "
        "extra applied to the wrong hamper"
    ) in disqualifier.text
    assert (
        "cordial reached Mrs Beech's hamper through a mix-up of orders or an "
        "extra applied to the wrong hamper"
    ) in said, "the disqualifier's key text, quoted in the section"

    for task_id, model in sorted(_RED_CELLS):
        run = round_12[task_id, model]
        archive = firstparty_v1.RunRulings.model_validate(
            json.loads(
                firstparty_v1.rulings_file(
                    _RULINGS, task_id, run.agent, model
                ).read_text(encoding="utf-8")
            )
        )
        [entry] = [
            e for e in archive.rulings if e.point_id == _RED_DISQUALIFIER
        ]
        assert entry.covered and entry.verified and entry.span
        deliverable = firstparty_v1._collect_the_answer_file(
            tasks[task_id], run.diff, key.answer_path
        )
        assert firstparty_v1._the_span_holds(
            entry.covered, entry.span, deliverable
        ), "the span is verbatim in the deliverable"
        assert prose(entry.span) in said, (
            f"{model}: the grader's evidence span, quoted in the section"
        )

    assert "**no planted point went uncovered anywhere**" in said
    assert "all 45 point-rulings across the nine answers are covered" in said
    assert (
        "**Zero demotions — the departure from §101, where there were "
        "two.**"
    ) in said
    assert "checked 63 quotations and demoted none" in said
    assert "no archive of this round carries `verified: false`" in said
    assert (
        "**That is the whole of the verdict reading, and no fraction is "
        "computed over it.**"
    ) in said
    assert "said here while reading the cells and never as a score" in said
    assert (
        "**What the collection rule archived: nothing, because there was "
        "nothing.**"
    ) in said
    assert "unexercised this round as it was in rounds 10 and 11" in said
    assert "**pointer prose is structurally impossible**" in said

    # The collection rule was unexercised: every diff touches the answer file
    # and nothing else, which the record says rather than claiming proof.
    for (task_id, model), run in round_12.items():
        touched = re.findall(r"^diff --git a/(\S+) b/", run.diff, re.MULTILINE)
        assert touched == ["ANSWER.md"], (task_id, model)


def test_no_fraction_over_points_is_quoted_as_a_quality_figure() -> None:
    """§107.5's registered refusal, honoured in the record's own prose.

    The shapes that would break it: a percentage, an `n of m` or `n/m` over a
    point-sized denominator (the keys plant five points each), and the
    English of a coverage rate. What the record is allowed to say is cell
    counts over three and nine — resolution lines — and the named
    disqualifiers and points themselves, which §112 checks are there.
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
    said = prose(note_section("115. What this round cannot say"))
    assert "**No coverage-fraction reading of any kind.**" in said
    assert '"four of five covered" as a score' in said


def test_the_coverage_table_and_the_zero_exemplar_sites_are_verified(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 113: the table as the lint prints it, whole, and the
    zero-exemplar sites verified rather than edited.

    No zero-exemplar moved this round — the category already carried tasks —
    so the `coverage_table` docstring, `CONTEXT.md`'s glossary entry and the
    earlier suites' exemplar pins all still name `performance-optimisation`
    as the category reading zero, and this test pins their unchanged form the
    way the quoted figures are pinned. The `codebase-comprehension ×
    typescript` zero is disclosed as zero by absence, and
    `performance-optimisation` still prints the `- - 0` shape a real zero
    prints.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))
    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python[_CATEGORY] == 7, "the round's acceptance figure"
    assert sum(python.values()) == 125
    assert not [
        row for row in coverage if row[0] == _CATEGORY and row[2] == "typescript"
    ], "the TypeScript zero is by absence"
    assert not [row for row in coverage if row[0] == _CATEGORY and row[3] == 0]
    assert ("performance-optimisation", "-", "-", 0) in coverage, (
        "the shape a real zero prints, and the docstring's example still"
    )

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed
    [quoted] = fenced_blocks(
        note_section("113. The coverage table, as the lint prints it")
    )
    for line in quoted.strip("\n").splitlines():
        assert line in printed, line
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  codebase-comprehension")
    ] == [["codebase-comprehension", "application", "python", "7"]]
    assert "  codebase-comprehension     application  typescript" not in printed
    assert "  performance-optimisation   -            -           0" in printed

    said = prose(note_section("113. The coverage table, as the lint prints it"))
    assert (
        "**`codebase-comprehension application python 7` is the round's "
        "acceptance figure**"
    ) in said
    assert "the line that read `4` in the table §102 quoted" in said
    assert "The row counts the category and not the shape" in said
    assert "zero by absence — which is all the table can express" in said
    assert "**the lint was not changed**" in said
    assert "heap 3 stays on Python until the grader has a record behind it" in said
    assert (
        "**`performance-optimisation` is still disclosed as a zero row**"
    ) in said
    assert "**No zero-exemplar moved this round" in said
    assert "**verified, not edited**" in said

    # The zero-exemplar sites, read off the live function and the live file —
    # unmoved by this round, verified here, re-edited nowhere.
    docstring = " ".join((firstparty_v1.coverage_table.__doc__ or "").split())
    assert (
        "`performance-optimisation` is one of the categories reading zero "
        "today"
    ) in docstring
    assert (
        "`requirement-decomposition` read zero until round 11 filled its "
        "Python cell"
    ) in docstring
    context = _CONTEXT.read_text(encoding="utf-8")
    assert _CONTEXT_SENTENCE in context
    for suite in (
        "test_firstparty_v1_round7_cells.py",
        "test_firstparty_v1_round7_record.py",
        "test_firstparty_v1_round8_record.py",
        "test_firstparty_v1_round10_record.py",
    ):
        assert "performance-optimisation" in (
            _REPO / "tests" / suite
        ).read_text(encoding="utf-8"), suite


def test_the_false_red_shape_did_not_recur_and_the_loader_move_is_landed(
    tasks: dict[str, firstparty_v1.Task],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 114: the sentence a future round planner reads, stated plainly
    and re-derived — no planted point refused anywhere, so §104's false-red
    shape had no opportunity to recur — and the loader's landed move, each
    clause checked against the code.
    """
    # The reading's ground: not one of the 45 point-rulings is a refusal.
    refused = [
        (task_id, model, point)
        for (task_id, model), (_, uncovered, _) in rulings.items()
        for point in uncovered
    ]
    assert refused == [], "no planted point was refused anywhere in the round"

    said = prose(note_section(
        "114. The false-red shape did not recur, and the loader's move is "
        "landed"
    ))
    assert (
        "across all nine production answers, no planted point was refused "
        "anywhere"
    ) in said
    assert (
        "the false-red shape §104's addendum found had no opportunity to "
        "recur, and did not"
    ) in said
    assert "**one-clause-tight**" in said
    assert "the first written under that discipline" in said
    assert (
        "consistent with §106.1's discipline doing what it was ruled to do"
    ) in said
    assert "**one round of evidence on the easy action**" in said
    assert "the owner's labels are the check's other half" in said
    assert "**Neither reading reopens §106.1 here**" in said

    # The loader's move, clause by clause, against the code it landed in.
    assert firstparty_v1._POINT_OPTIONAL_CATEGORY == _CATEGORY
    assert _CATEGORY in firstparty_v1._POINT_CATEGORIES
    assert _CATEGORY not in firstparty_v1._POINT_REQUIRED_CATEGORIES
    assert {"investigation", "requirement-decomposition"} <= set(
        firstparty_v1._POINT_REQUIRED_CATEGORIES
    )
    assert (
        firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].check
        is firstparty_v1._the_comprehension_proof_the_key_on_disk_asks_for
    )
    assert "locate-style" in firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].form
    assert firstparty_v1.TERRAIN_RULES == (
        "prompt-names-a-key-location",
        "prompt-word-narrows-to-the-accepted-module",
        "accepted-class-is-the-only-class",
    )
    assert _CATEGORY in firstparty_v1.TERRAIN_EXEMPT_ACTIONS

    # The four locate-style tasks kept their key shape: none is point-keyed,
    # every one still carries its accepted-answer key.
    locate = [
        task
        for task in tasks.values()
        if task.category == _CATEGORY
        and not firstparty_v1.is_point_keyed(task)
    ]
    assert len(locate) == 4
    assert all(firstparty_v1.carries_a_key(task) for task in locate)

    assert "`_POINT_CATEGORIES`' first **point-optional** member" in said
    assert (
        "a task shipping both an accepted-answer key and a points key is "
        "refused as two ground truths for one deliverable"
    ) in said
    assert "dispatched by the same key on disk" in said
    assert "an explain-style task alone" in said
    assert (
        "**the category's four locate-style tasks kept all three terrain "
        "rules**"
    ) in said
    assert "`prompt-names-a-key-location`" in said
    assert "`prompt-word-narrows-to-the-accepted-module`" in said
    assert "`accepted-class-is-the-only-class`" in said
    assert "**and their locate proof**" in said
    assert "every accepted location resolving in the starting repository" in said


def test_what_this_round_cannot_say_is_stated_and_true_of_the_corpus(
    tasks: dict[str, firstparty_v1.Task],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 115's refusals, each anchored to something checkable, and the
    disclosures the ticket wants in as many words: the covered-but-mediocre
    narrowing, the transfer gap, and the owner's ~9 labels — **given
    2026-08-29** in the dated-addendum form the section reserved, seven of
    nine agree and two disagree, the orchestrator-assistance provenance
    disclosed, the two disagreements the very cells §112 reads and the gap
    read as opened a second time, in the same direction, by a new mechanism
    (a disqualifier adjacent to the true mechanism, over-matched on
    production prose)."""
    swept = {task_id for task_id, _ in rulings}
    assert all(tasks[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if tasks[task_id].construction is not None
    ]
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS

    said = prose(note_section("115. What this round cannot say"))
    assert "**Covered is not brilliant — the narrowing, in as many words.**" in said
    assert (
        "Covering every planted point does not certify a good explanation"
    ) in said
    assert "an agent can cover every planted point with a mediocre one" in said
    assert "never as a certificate of quality beyond its key" in said
    assert (
        "a present disqualifier means the answer made the key's disqualified "
        "claim, not that its explanation was worthless"
    ) in said

    assert (
        "**The transfer gap, restated from §79.4, §81.4, §92 and §104.**"
    ) in said
    assert (
        "would have proved the grader judges argued prose against a known "
        "truth — not that it judges prose with no truth behind it"
    ) in said
    assert "The proofs' truth is still the author's planted truth" in said
    assert "found the gap open on two cells in one direction" in said

    # The labels: given 2026-08-29, the day after the record, in the dated
    # form the section reserved — provenance disclosed the way §104's was,
    # the table fenced once and exactly as given, its machine column agreeing
    # with the verdicts this suite re-derives from the archived rulings.
    assert (
        "**The owner's ~9 agree/disagree labels: given 2026-08-29, the day "
        "after this record — seven of nine agree, two disagree.**"
    ) in said
    assert "§76.2 ruled and §77.2 registered" in said
    assert (
        "**these labels were formed with the orchestrator's assistance and "
        "not by an unaided read**"
    ) in said
    assert "the owner adopted the recommendations" in said
    labels_block = [
        block
        for block in fenced_blocks(note_section("115. What this round cannot say"))
        if "agree" in block
    ]
    assert len(labels_block) == 1, "the labels table, fenced, once"
    assert labels_block[0].count("agree     (machine:") == 7
    assert labels_block[0].count("disagree  (machine:") == 2
    # The machine column repeats the verdicts this suite re-derived from the
    # archived rulings, cell for cell; the two disagreements are the two
    # grocers × claude cells §112 reads, and this section named in advance
    # as the ones a holistic read would most naturally contest.
    short = {
        "ropewalk-explain-how-an-order-becomes-a-coil": "ropewalk",
        "grocers-explain-why-the-plain-hamper-carries-the-cordial": "grocers",
        "tramshed-explain-why-the-two-boards-disagree": "tramshed",
    }
    verdicts = {
        (short[task_id], model): resolved
        for (task_id, model), (resolved, _, _) in rulings.items()
    }
    label_lines = [line for line in labels_block[0].splitlines() if " x " in line]
    assert len(label_lines) == 9, "one label line per swept cell"
    for line in label_lines:
        prefix, _, machine = line.partition("(machine: ")
        stem, _, rest = prefix.partition(" x ")
        model = rest.split()[0]
        assert verdicts[(stem.strip(), model)] == machine.startswith("resolved")
        if "disagree" in line:
            assert stem.strip() == "grocers"
            assert model in (_HAIKU, _SONNET)
    # The finding: the gap opened a second time, same direction, new
    # mechanism — the disqualifier side of §106.1's coin — with the
    # instrument's own asymmetry (the reference's clear ruling at the
    # proofs) named as what settles the reading, and the next round's
    # authoring rule priced in as many words.
    assert (
        "the transfer gap opened a second time, on two of nine and in the "
        "same direction"
    ) in said
    assert (
        "a **disqualifier whose text is semantically adjacent to the true "
        "mechanism**"
    ) in said
    assert "§114's zero refused points stands untouched by these labels" in said
    assert (
        "the same instrument ruled its disqualifier clear at the proofs"
    ) in said
    assert "The check gated nothing and the nine verdicts stand" in said
    assert (
        "surface-disjoint from the true mechanism's own"
    ) in said

    assert "**No cross-action difficulty comparison.**" in said
    assert (
        "7 of 9 here is not to be read against round 11's 0 of 9 or round "
        "10's 1 of 9"
    ) in said
    assert "§76.8 named this action the easy case in advance" in said
    assert (
        "**Nothing about `codebase-comprehension` × `typescript`.**"
    ) in said
    assert "**No Codex rung.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No multiplier.**" in said


def test_the_limits_and_toolchain_paragraphs_hold_against_the_code(
    round_12: dict[tuple[str, str], firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 108's limits and toolchain paragraphs, against the table the
    runner reads and the interpreter the suite runs on.

    Unlike round 11's action this one is registered: the category has carried
    its `LIVE_RUN_LIMITS_S` row at 600 since round 5, which is §46's
    distinction read the other way around.
    """
    assert firstparty_v1.LIVE_RUN_LIMITS_S[_CATEGORY] == 600
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    swept = {task_id for task_id, _ in round_12}
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in tasks.values()
        if task.id in swept
    } == {600} == {firstparty.RUN_TIMEOUT_S}

    latencies = [run.latency_s for run in round_12.values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600
    longest = max(round_12.items(), key=lambda item: item[1].latency_s)
    assert longest[0] == (_DRY_CELL, _SONNET), (
        "the longest run is the ropewalk on sonnet"
    )

    assert platform.python_version() == _PYTHON_VERSION

    measured = prose(note_section("108. What the round measured"))
    assert (
        "**The limits in force: the category's own registered 600 seconds, "
        "every cell.**"
    ) in measured
    assert (
        "**under the registration the category already carries** rather than "
        "at the bare flat default"
    ) in measured
    assert "**no cross-round caveat arises**" in measured
    assert f"the round's longest run was **{_LONGEST_S} s**" in measured
    assert f"the mean was **{_MEAN_S} s**" in measured
    assert f"Python {_PYTHON_VERSION}" in measured
    assert point_grader.GRADER_VERSION in note_section(
        "108. What the round measured"
    ), "the instrument, quoted from the code the round ran on"
    assert (
        "**63 archived rulings — seven a cell, one per planted question — "
        "taken in 63 metered grader calls with no retry**"
    ) in measured
    assert "**provenance and not a row field**" in measured
    assert "no `grader` field" in measured


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 116's replay, run rather than remembered — and offline.

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
    assert sum(float(record["quality_value"]) for record in merged) == 7

    printed_block = fenced_blocks(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed_block

    said = prose(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))
    assert (
        "**Every round-12 log replays to the verdicts this record quotes, "
        "with the network unplugged.**"
    ) in said
    assert "handed **no grader factory**" in said
    assert "9 rows and 7 resolved" in said
    assert "a table-derived cost is not recomputed on the way through" in said


def test_both_readers_count_the_round_and_print_what_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 116's readers: six of the nine rows inside the default view,
    the reconcile lines quoted as the reader prints them, the calibrate table
    exactly as printed — the category's standing table grown to seven tasks,
    not a new one — and the earlier rounds' published tables unmoved."""
    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    [quoted] = fenced_blocks(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))[1:2]
    for line in quoted.strip("\n").splitlines():
        assert line in printed, line
    assert printed.count(f"sweep {_SWEEP}") == 1
    assert _CATEGORY not in printed, (
        "the round declared no contrast, so it reaches the report as a "
        "label and nothing else"
    )
    assert "   67 constructed task(s): 67 swept, 0 unswept" in printed

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    [table] = fenced_blocks(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))[2:3]
    assert table.strip("\n") in calibrated, (
        "the calibration table the record quotes is not what the reader prints"
    )
    assert f"category {_CATEGORY}" in calibrated
    assert (
        "   (zero-knob)  7      1.00x (n=7)       1.00x (n=7)      "
        "haiku-solvable (n=7)"
    ) in calibrated

    said = prose(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))
    assert "**And the readers count the round with no flag at all.**" in said
    assert "**The prediction reconciliation is unmoved**" in said
    assert "a **denominator**" in said
    assert "The rung floor reads **haiku-solvable**" in said
    assert "The published tables of earlier rounds are unmoved" in said


def test_nothing_from_the_proofs_reached_the_unified_dataset(
    runs: list[firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 116's last claims: nothing of the proofs in the unified
    dataset (itself gitignored, round 8's standing rule), the free-text
    archive grown by exactly the nine answers, and the registered split the
    A″ readings are computed over unmoved."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        flat = json.dumps(json.loads(line))
        for needle in (
            "proofs", "reference-answer", "foil", "re-ask",
            "prove-points", "point-gate-calibration",
        ):
            assert needle not in flat, needle

    archived = [run for run in runs if run.output]
    assert len(archived) == _ARCHIVE_NOW
    assert len(
        [run for run in archived if run.sweep != _SWEEP]
    ) == _ARCHIVE_BEFORE
    stratum_a = [
        run
        for run in runs
        if run.sweep not in {"round-10", _ANCHOR, _SWEEP}
        and firstparty_v1.carries_a_key(tasks[run.task_id])
    ]
    assert len(stratum_a) == _STRATUM_A

    said = prose(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))
    assert "**Nothing from the proofs reached `data/unified.jsonl`.**" in said
    assert "a combination's result on a benchmark instance (§76.11)" in said
    assert "the dataset itself is gitignored, round 8's standing rule" in said
    assert (
        "**324 answers across eleven sweeps to 333 across twelve**"
    ) in said
    assert "**306 rows, 63 of them stratum A**" in said
    assert "out of that read rather than an error in it" in said


def test_the_record_takes_the_next_free_numbers_and_renumbers_nothing() -> None:
    """Sections 108-116 are the next free numbers after §107, contiguous,
    each spent once, landing before the note's trailing headings — and the
    last section names the next free number, which is the frontier sentence
    the round-9 suite's moved assertion reads."""
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(107) == 1
    assert all(numbered.count(number) == 1 for number in range(108, 117))
    # The live frontier is the round-9 suite's one moved assertion and is
    # deliberately not copied here; what this test owns is that the record's
    # nine numbers are spent once each and nothing above or below them was
    # renumbered — a claim the contiguity range extends over §117 (round
    # 13's rulings, 2026-08-29) to keep making.
    assert [number for number in numbered if number > 68] == list(range(69, 118))

    for heading in record_sections():
        assert f"### {heading}\n" in text, heading

    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    record_at = headings.index("## Round 12 record — 2026-08-28")
    assert headings[record_at - 1] == (
        "## Round 12 cells and cost — registered 2026-08-28"
    )
    # The heading after the record was `## Open questions` until round 13's
    # rulings landed there (2026-08-29); the claim that survives is that the
    # record sits inside the note's numbered run, before the trailing
    # headings — this adjacency pin moved in the commit that landed §117,
    # exactly as round 11's did when §106 landed.
    assert headings[record_at + 1].startswith("## Round 13 rulings"), (
        "round 13's rulings are what landed after it"
    )

    opening = prose(
        note_part("Round 12 record — 2026-08-28").split("\n### ")[0]
    )
    assert "**§108 is the next free number.**" in opening
    assert "this record opens at **108** and runs to **116**" in opening
    assert "Nothing above it is renumbered." in opening

    closing = prose(note_section(
        "116. Replay, the readers, and heap 3 closed"
    ))
    assert "**Heap 3 closes.**" in closing
    assert "**§117 is the next free section number**" in closing
    assert "nothing above is renumbered" in closing
