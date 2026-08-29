"""Round 11's record, pinned: what sections 97-105 of the design note publish.

The round swept nine cells over **three `requirement-decomposition` tasks** —
heap 3's second action, taken as the mechanical fill §86 licensed — and the
point gate scored it **0 of 9**: its first all-red round. The record's one
reading is §89's, carried onto the new action — **which named planted point
went uncovered** in each red cell, read off the archived rulings — plus the
one departure this round has from §89: **two covered rulings were demoted**
by §76.6's span rule, and the record names both. The standing temptation is
the coverage fraction — "four of five covered" — which ADR-0004 refused for
mutants and ADR-0005 refuses for points, so this file checks that no fraction
over planted points is quoted as a quality figure anywhere in the round's own
sections.

Every figure is re-derived from the artifact that earned it: the checked-in
run logs (collected wholesale, selected by **sweep id `round-11`** and never
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
§97.
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
_RUNBOOK = _REPO / "docs" / "agents" / "runbook-round-11-proofs.md"

_SWEEP = "round-11"
_ANCHOR = "round-10"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"
_TERRA = "gpt-5.6-terra"
_COMBINATIONS = (
    (firstparty.CLAUDE_CODE, _HAIKU),
    (firstparty.CLAUDE_CODE, _SONNET),
    ("codex", _TERRA),
)
_AS_OF = "2026-08-26"
_CATEGORY: TaskCategory = "requirement-decomposition"

# The versions the rows carry — and this round crosses a boundary again:
# claude-code moved from round 10's 2.1.241, one round back this time, which
# §97 narrates; codex is rounds 6-8 and 10's exactly.
_AGENT_VERSIONS = {
    firstparty.CLAUDE_CODE: "2.1.246 (Claude Code)",
    "codex": "codex-cli 0.147.0",
}
_ROUND_10_CLAUDE_VERSION = "2.1.241 (Claude Code)"

# The four logs the sweep's four invocations wrote, and what each replays to.
# Named only so that section 105's replay can be given one log at a time;
# nothing here selects runs by them.
_REPLAYED = {
    "2026-08-26-r11-a.jsonl": (1, 0),
    "2026-08-26-r11-b.jsonl": (2, 0),
    "2026-08-26-r11-c.jsonl": (3, 0),
    "2026-08-26-r11-d.jsonl": (3, 0),
}
_DRY_CELL = "turnpike-break-down-the-move-to-the-new-money"
_CHEAPEST_CELL = "maltings-break-down-the-hardening-of-the-log"

# Section 99's sweep spend, per combination and per cost source, and the
# registered range it is read against. This round the range was met — the
# first point-gate sweep to land inside its band — so the floor and ceiling
# below are asserted to hold the total, deliberately.
_SPEND = {_HAIKU: 0.2385, _SONNET: 0.8253, _TERRA: 0.2568}
_BILLED = 1.0638
_TOTAL = 1.3206
_PER_CELL = {_HAIKU: 0.0795, _SONNET: 0.2751, _TERRA: 0.0856}
_REGISTERED_RANGE = (1.2, 2.5)
_FLAT_EXTRAPOLATION = 1.2090
_FLAT_EXTRAPOLATION_RATIO = 1.09
_ROUND_10_COLUMN = {_HAIKU: 0.2529, _SONNET: 0.7103, _TERRA: 0.2458}
_ROUND_10_PER_CELL = {_HAIKU: 0.0843, _SONNET: 0.2368, _TERRA: 0.0819}
_COLUMN_RATIO = {_HAIKU: 0.94, _SONNET: 1.16, _TERRA: 1.04}

# Section 99's token evidence: the over-run sits where the deliverable is —
# sonnet wrote a decomposition's three sections at length; the other two
# columns read less than round 10's.
_TOKENS_PER_CELL = {
    _HAIKU: (213_250, 5_338),
    _SONNET: (240_069, 12_732),
    _TERRA: (104_273, 2_516),
}
_ROUND_10_TOKENS_PER_CELL = {
    _HAIKU: (239_991, 5_619),
    _SONNET: (239_678, 10_057),
    _TERRA: (111_316, 2_457),
}

# Section 99's Codex bounds at the round's own tokens, and the effective rate.
_CODEX_TOKENS = (312_819, 7_547)
_ALL_CACHED = 0.1531
_ALL_UNCACHED = 0.7162
_EFFECTIVE_RATE = 0.5314
_ROUND_10_EFFECTIVE_RATE = 0.4711
_PRICE_TABLE = "openai-pricing-2026-08-18.1"

# Section 99's proofs: the metered count against §96's re-registered 64-80,
# and the arithmetic's own components — each block's input re-derived from
# checked-in text below, never trusted from these constants alone.
_METERED_LOW, _METERED_HIGH = 64, 80
_TICKET_03_CALLS = 48       # 12 for the turnpike + 36 re-asks (§96)
_DEAD_CALLS = 12            # ~12: a vendor empty-content stream, nothing back
_FULL_CALLS = 24            # almshouse 12 + maltings 12
_REPROVE_CALLS = 12         # the revised maltings, both sides
_ARCHIVED_CONTENT_CALLS = 84  # every metered call that returned content
_PROOF_RANGE = (0.05, 0.6)
_DEEPSEEK_INPUT_PER_MTOK = 1.32
_DEEPSEEK_OUTPUT_PER_MTOK = 3.96
_PROOF_ANSWER_CHAR_CAP = 8_000

# Section 97's resolution line: the point gate's first all-red round.
_RESOLVED = {_HAIKU: 0, _SONNET: 0, _TERRA: 0}

# Section 97's limits paragraph.
_LONGEST_S = 195.0
_MEAN_S = 100.8
_PYTHON_VERSION = "3.14.4"

# Section 100's turn line, quoted so section 104's refusal has an anchor.
_TURNS = {_HAIKU: 31, _SONNET: 33, _TERRA: 21}
_TURN_RANGE = {_HAIKU: (8, 12), _SONNET: (11, 11), _TERRA: (7, 7)}

# Section 101's departure from §89: the two rulings §76.6's span rule
# demoted — the grader said covered, the quoted span is not in the
# deliverable under the instrument's normalisation, the archive records
# `verified: false`, and the point counts as uncovered.
_DEMOTED = {
    ("almshouse-break-down-the-taking-of-names-out-of-the-book", _HAIKU):
        "the-name-is-written-into-the-entry",
    ("turnpike-break-down-the-move-to-the-new-money", _HAIKU):
        "the-keeper-reads-money-through-the-cli",
}

# Section 101's cross-cell reading: the points every answer covered, and the
# points no combination covered.
_COVERED_EVERYWHERE = {
    ("turnpike-break-down-the-move-to-the-new-money",
     "the-rates-do-not-come-out-whole"),
    ("maltings-break-down-the-hardening-of-the-log",
     "the-month-end-reads-past-the-gate"),
}
_UNCOVERED_EVERYWHERE = {
    ("almshouse-break-down-the-taking-of-names-out-of-the-book",
     "the-name-is-written-into-the-entry"),
    ("almshouse-break-down-the-taking-of-names-out-of-the-book",
     "the-readers-match-on-the-exact-who"),
    ("almshouse-break-down-the-taking-of-names-out-of-the-book",
     "no-roll-of-numbers-exists-yet"),
    ("maltings-break-down-the-hardening-of-the-log",
     "a-line-is-the-unit-of-damage"),
    ("maltings-break-down-the-hardening-of-the-log",
     "bad-is-wider-than-broken-json"),
    ("turnpike-break-down-the-move-to-the-new-money",
     "the-audit-ties-the-roll-to-the-table"),
}
_FOIL_DISQUALIFIERS = {
    "turnpike-break-down-the-move-to-the-new-money":
        "swap-the-table-and-be-done",
    "almshouse-break-down-the-taking-of-names-out-of-the-book":
        "numbers-at-the-door-and-done",
    "maltings-break-down-the-hardening-of-the-log":
        "a-catch-all-at-the-command-line",
}

# Section 105's archive line: the free-text archive across eleven sweeps, and
# the registered split the A″ readings stay computed over.
_ARCHIVE_BEFORE = 315
_ARCHIVE_NOW = 324
_STRATUM_A = 63

# Section 102's two landed sentences, moved by the round's first task before
# the sweep and pinned here the way the quoted figures are. Round 13's
# ticket 04 moved the glossary sentence again when it filled
# `performance-optimisation`'s Python cell — the last authorable zero row,
# with no authorable successor category to re-point at: the only `- - 0` row
# left is `unclassified`'s, which survives by construction because the
# loader refuses any task declaring it (the plan-review ruling of
# 2026-08-29). So the sentence changed shape — no "today" exemplar remains —
# and the pin moves with it; §102's own quoted prose stays what round 11
# wrote.
_CONTEXT_SENTENCE = (
    "(`test-authoring` was one until round 8 authored its three Python "
    "tasks, `investigation` was one until round 10 filled its Python cell, "
    "`requirement-decomposition` was one until round 11 filled its Python "
    "cell, and `performance-optimisation` was one until round 13 filled its "
    "Python cell — the last authorable zero row, so the only `0` row still "
    "printed is **unclassified**'s, permanent and structural because the "
    "loader refuses any task declaring that category)"
)


@pytest.fixture(scope="module", autouse=True)
def no_grader_can_be_built() -> Iterator[None]:
    """The offline claim, made structural for the whole module.

    §105 says the round's rows replay with the network unplugged and no
    grader client constructed. Nothing below should reach the one factory
    there is, so the factory is replaced by a detonator: a construction
    anywhere in this file fails the suite instead of quietly asking for a
    key.
    """
    original = point_grader.deepseek_point_grader

    def refuse() -> point_grader.PointGrader:
        raise AssertionError(
            "the round-11 record is a recomputation over archived rulings — "
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
        "97. What the round measured",
        "98. The gate opened: every reference resolved, every foil failed",
        "99. Spend, by cost source, against both registered ranges",
        "100. The nine cells under three combinations",
        "101. Which point went uncovered, and the two rulings the span rule "
        "demoted",
        "102. The coverage table, as the lint prints it",
        "103. The second action confirmed the instrument's record",
        "104. What this round cannot say",
        "105. Replay, the readers, and heap 3's second cell filled",
    ]


_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def registered_cells() -> list[str]:
    """§95.7's filled register, read back out of the pre-registration, so
    what the round swept is compared against the register itself and never a
    copy."""
    for block in fenced_blocks(
        note_part("Round 11 cells and cost — registered 2026-08-26")
    ):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        matched = [
            match for line in lines if (match := _REGISTER_LINE.fullmatch(line))
        ]
        if len(matched) == len(lines) and all(
            match.group(2) for match in matched
        ):
            return [match.group(1) for match in matched]
    raise AssertionError("§95.7's filled register is not in the note")


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
def round_11(
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
    round_11: dict[tuple[str, str], firstparty_v1.Run],
) -> dict[tuple[str, str], tuple[bool, list[str], list[str]]]:
    """Every cell's verdict, uncovered points and present disqualifiers,
    recomputed from the archived rulings against the deliverable the diff
    collects — the very computation replay runs, with no grader anywhere.

    The verdict is taken from `_point_verdict` — the shipped gate — and the
    per-point reading beside it re-applies the same span rule, so this is a
    reading of the one grading pipeline and not a second one that happens to
    agree with it. Unlike round 10's fixture this one does not assert that
    every covered ruling survived the span check: two did not (§101), and
    exactly which two is asserted here — the demotion is §76.6 doing its
    job, recorded in the archive itself as `verified: false`, and any third
    demotion would be a fact the record does not tell.
    """
    derived: dict[tuple[str, str], tuple[bool, list[str], list[str]]] = {}
    demoted: dict[tuple[str, str], str] = {}
    for (task_id, model), run in sorted(round_11.items()):
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
        # One instrument over the whole round: §95.1's stop never fired.
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
    assert demoted == _DEMOTED, (
        "exactly the two demotions §101 names, and no third"
    )
    return derived


def cell_table(
    round_11: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 100's table, rebuilt from the logs and the recomputed verdicts
    — byte for byte, headers and cost sources included."""
    ids = sorted({task_id for task_id, _ in round_11})
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
            columns.append(f"{verdict} ${round_11[task_id, model].cost_usd:.4f}")
        lines.append(
            (f"{task_id:<{width}}  "
             + "  ".join(f"{column:<18}" for column in columns)).rstrip()
        )
    return "\n".join(lines) + "\n"


def gate_table(
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> str:
    """Section 101's table, rebuilt from the archived rulings: per cell, the
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
    round_11: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 97's sweep facts, off the rows themselves, against §95.7.

    The register is read out of the pre-registration rather than restated.
    One sweep id, one as-of date, one version per harness — and this round
    crosses a version boundary on the claude-code side again, one round back
    this time, which the record narrates rather than hides.
    """
    assert {run.sweep for run in round_11.values()} == {_SWEEP}
    assert {run.as_of.isoformat() for run in round_11.values()} == {_AS_OF}
    assert {
        (run.agent, run.model) for run in round_11.values()
    } == set(_COMBINATIONS)
    for agent, version in _AGENT_VERSIONS.items():
        assert {
            run.agent_version
            for run in round_11.values()
            if run.agent == agent
        } == {version}, agent

    # The boundary, read off round 10's own rows rather than quoted from §85.
    round_10 = [run for run in runs if run.sweep == _ANCHOR]
    assert {
        run.agent_version
        for run in round_10
        if run.agent == firstparty.CLAUDE_CODE
    } == {_ROUND_10_CLAUDE_VERSION}
    assert _ROUND_10_CLAUDE_VERSION != _AGENT_VERSIONS[firstparty.CLAUDE_CODE]
    assert {
        run.agent_version for run in round_10 if run.agent == "codex"
    } == {_AGENT_VERSIONS["codex"]}, "codex crossed no boundary"

    registered = registered_cells()
    assert len(registered) == 3 == len(set(registered))
    assert {task_id for task_id, _ in round_11} == set(registered)
    assert {tasks[task_id].category for task_id in registered} == {_CATEGORY}
    assert {tasks[task_id].language for task_id in registered} == {"python"}
    assert {tasks[task_id].surface for task_id in registered} == {"application"}
    assert all(tasks[task_id].control for task_id in registered)
    assert set(registered) == {
        task.id for task in tasks.values() if task.category == _CATEGORY
    }, "every requirement-decomposition task the corpus holds, and no fourth"

    assert agents.CODEX_REASONING_LEVELS == {_TERRA: "medium"}

    measured = prose(note_section("97. What the round measured"))
    assert "**Nine cells, and they are exactly the nine §95.7 registered.**" in measured
    assert "**9 of 9**" in measured
    assert "**heap 3's second action's cells**" in measured
    assert "**no second quality metric enters the table**" in measured
    assert "**does cross a version boundary**" in measured
    assert "**2.1.246** against round 10's 2.1.241" in measured
    assert "one round back this time" in measured
    assert (
        "**codex-cli 0.147.0** is rounds 6, 7, 8 and 10's exactly"
    ) in measured


def test_the_dry_cell_and_the_four_logs_are_what_the_record_says(
    round_11: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 97's invocation paragraph, against the checked-in logs.

    The dry cell was one of the nine, run alone in its own invocation, graded
    alone before the other eight, and its verdict is the gate's first on this
    action's deliverable shape: unresolved with four named uncovered points,
    one of them by mechanical demotion — the verdict shape arriving
    well-formed. And the registration's word "cheapest" is checked against
    what the rows actually cost, the departure stated rather than passed
    over — §85's own honesty, repeated.
    """
    counted = {
        name: len(firstparty_v1.load_runs(_LOGS / name)) for name in _REPLAYED
    }
    assert counted == {name: rows for name, (rows, _) in _REPLAYED.items()}
    assert sum(counted.values()) == 9
    assert min(counted.values()) > 0, "no invocation of this round logged nothing"

    alone = firstparty_v1.load_runs(_LOGS / "2026-08-26-r11-a.jsonl")
    assert [(run.task_id, run.agent, run.model) for run in alone] == [
        (_DRY_CELL, firstparty.CLAUDE_CODE, _HAIKU)
    ]
    assert alone[0].sweep == _SWEEP, "the dry cell is a cell of the round"
    verdict, uncovered, present = rulings[_DRY_CELL, _HAIKU]
    assert verdict is False and len(uncovered) == 4 and not present, (
        "the gate's first paid verdict on this action: unresolved, four "
        "named points uncovered, nothing mis-shaped"
    )
    assert _DEMOTED[(_DRY_CELL, _HAIKU)] in uncovered, (
        "one of the four is the demoted ruling §101 names"
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

    # "Cheapest" was an ex-ante reading the anchor did not support: at round
    # 10's anchor the Codex column was the cheaper; in the event the haiku
    # column came in cheapest after all, but the dry cell itself did not.
    assert _ROUND_10_PER_CELL[_TERRA] < _ROUND_10_PER_CELL[_HAIKU]
    assert _PER_CELL[_HAIKU] < _PER_CELL[_TERRA]
    cheapest = min(round_11.items(), key=lambda item: item[1].cost_usd)
    assert cheapest[0] == (_CHEAPEST_CELL, _HAIKU)
    assert round(cheapest[1].cost_usd, 4) == 0.0645
    assert round(round_11[_DRY_CELL, _HAIKU].cost_usd, 4) == 0.0854

    measured = prose(note_section("97. What the round measured"))
    assert "**Four invocations, four logs, none of them empty.**" in measured
    assert "**graded alone before the other eight**" in measured
    assert "**unresolved**, with four named points uncovered" in measured
    assert (
        "**The dry cell was registered as the cheapest of the nine and was "
        "not**"
    ) in measured
    assert "**$0.0795** a cell against Codex's **$0.0856**" in measured
    assert "the dry cell itself cost **$0.0854**" in measured
    assert "`maltings` on haiku at **$0.0645**" in measured
    assert "an ex-ante reading the anchor did not support" in measured


def test_the_gate_opened_on_all_three_keys_before_the_first_sweep_dollar(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 98: the round's one gate, recomputed from the proof archives.

    §95.4's quantifier, checked as a quantifier: every planted point of every
    reference answer resolves and every foil fails, through the very
    `_point_verdict` a run is graded by. The foils' two-sided failure — the
    named disqualifier claimed *and* every planted point uncovered — is
    re-derived per task, and the count the gate is read off (12 archived
    calls a task, inside §95.5's 8-16) is counted off the keys themselves.
    """
    for task_id in _FOIL_DISQUALIFIERS:
        task = tasks[task_id]
        key = firstparty_v1.points_key(task)
        assert (len(key.points), len(key.disqualifiers)) == (5, 1)
        questions = firstparty_v1._point_questions(key)
        assert len(questions) * 2 == 12, "12 archived calls a task"
        assert 8 <= len(questions) * 2 <= 16, "§95.5's per-task range"
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
                assert not any(
                    covered[planted.id]
                    for kind, planted in questions
                    if kind == "point"
                ), f"{task_id}: the foil leaves every planted point uncovered"

    # The rule the section names is the one the lint runs for this action.
    assert (
        firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].check
        is firstparty_v1._the_reference_resolves_and_the_foil_fails
    )

    certified = prose(note_section(
        "98. The gate opened: every reference resolved, every foil failed"
    ))
    assert (
        "**The round's one hard gate was read before the first sweep dollar, "
        "and it opened.**"
    ) in certified
    assert "the orchestrator's ruling of 2026-08-26" in certified
    assert "§86 is its form" in certified
    assert (
        "**every planted point of every task's reference answer resolved, "
        "and every foil answer failed**"
    ) in certified
    assert "no fraction met, no proportion computed, no threshold" in certified
    assert "**these three keys discriminate**" in certified
    assert "**five points and one disqualifier**" in certified
    assert "**12 archived calls a task**" in certified
    assert "inside §95.5's registered 8–16 a task" in certified
    assert "every foil failed **both ways at once**" in certified
    assert "**every planted point of its key uncovered**" in certified
    assert "`_the_reference_resolves_and_the_foil_fails`" in certified
    assert "the stop §95.4 kept armed did not fire" in certified


def test_the_sweep_cost_what_the_record_states_by_cost_source(
    round_11: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 99's sweep spend, pinned per cost source and per cell, and the
    registered range it landed inside.

    The landing is the point this round: §95.6 registered $1.2-2.5 with the
    low miss named as the likelier on two routes, and neither happened — the
    total sits inside the band, above the floor, so this test asserts the
    range was met and that both pre-read routes are checked shut, with the
    per-cell token evidence re-derived beside them.
    """
    ids = sorted({task_id for task_id, _ in round_11})
    for model, spend in _SPEND.items():
        actual = sum(round_11[task_id, model].cost_usd for task_id in ids)
        assert round(actual, 4) == spend, model
        assert round(actual / 3, 4) == _PER_CELL[model], model
        assert round(
            spend / _ROUND_10_COLUMN[model], 2
        ) == _COLUMN_RATIO[model], model

    billed = sum(
        run.cost_usd
        for run in round_11.values()
        if run.cost_source == "vendor-reported"
    )
    assert round(billed, 4) == _BILLED
    total = sum(run.cost_usd for run in round_11.values())
    assert round(total, 4) == _TOTAL
    # Summed before rounding — and this round the printed columns add to
    # exactly the rounded total, round 8's situation rather than round 7's,
    # which the record says rather than leaves to a checker.
    assert round(sum(_SPEND.values()), 4) == _TOTAL

    low, high = _REGISTERED_RANGE
    assert low < total < high, "the registered range was met"
    assert round(total / _FLAT_EXTRAPOLATION, 2) == _FLAT_EXTRAPOLATION_RATIO
    assert total - low < 0.13, "$0.12 above the floor, as the record reads it"

    # The token evidence, per cell, against round 10's — both re-derived.
    for model, (tokens_in, tokens_out) in _TOKENS_PER_CELL.items():
        assert round(sum(
            run.tokens_in for key, run in round_11.items() if key[1] == model
        ) / 3) == tokens_in, model
        assert round(sum(
            run.tokens_out for key, run in round_11.items() if key[1] == model
        ) / 3) == tokens_out, model
    # The two low-miss routes, checked shut: sonnet wrote more than round 10,
    # not less, and the Codex effective rate rose rather than falling.
    assert _TOKENS_PER_CELL[_SONNET][1] > _ROUND_10_TOKENS_PER_CELL[_SONNET][1]
    assert _TOKENS_PER_CELL[_HAIKU][0] < _ROUND_10_TOKENS_PER_CELL[_HAIKU][0]
    assert _TOKENS_PER_CELL[_TERRA][0] < _ROUND_10_TOKENS_PER_CELL[_TERRA][0]

    # Cost sources, on the rows and refused at load if contradicted.
    codex = {k: run for k, run in round_11.items() if run.agent == "codex"}
    claude = {
        k: run
        for k, run in round_11.items()
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
    assert _EFFECTIVE_RATE > _ROUND_10_EFFECTIVE_RATE, (
        "the cache-friendlier low-miss route did not happen"
    )

    read = prose(note_section(
        "99. Spend, by cost source, against both registered ranges"
    ))
    assert (
        "**The registered sweep range was $1.2–2.5. The round came to "
        "$1.3206, and the range was met**"
    ) in read
    assert "$0.12 above the floor at **1.09×** the flat extrapolation" in read
    assert "**summed before rounding**" in read
    assert (
        "the printed columns add to exactly the rounded total, round 8's "
        "situation rather than round 7's"
    ) in read
    assert "**Neither pre-read miss happened.**" in read
    assert "the $2.5 stop was never approached" in read
    assert "**What the account was actually billed for the sweep: $1.0638" in read
    assert "**list-price equivalent, not an invoice**" in read
    assert "authenticated by **ChatGPT login**" in read
    assert f"version **`{_PRICE_TABLE}`**" in read
    assert "**0.94×**, **1.16×** and **1.04×** round 10's" in read
    assert "**$0.1531 all-cached** and **$0.7162 all-uncached**" in read
    assert "**$0.5314/M**" in read and "**$0.4711/M**" in read
    assert "a fifth point on one rate" in read
    assert (
        "version boundary (§97) is named beside these column readings and "
        "cannot carry them"
    ) in read
    assert "the Codex column crossed none and still rose" in read

    blocks = fenced_blocks(note_section(
        "99. Spend, by cost source, against both registered ranges"
    ))
    assert blocks[0] == (
        "claude-code x haiku     $0.2385  vendor-reported "
        "(what the account was billed)\n"
        "claude-code x sonnet    $0.8253  vendor-reported "
        "(what the account was billed)\n"
        "codex x gpt-5.6-terra   $0.2568  table-derived   "
        "(list price, openai-pricing-2026-08-18.1)\n"
    )
    for line in (
        "claude-code x haiku     $0.2529                $0.2385    $0.0795    $0.0843",
        "claude-code x sonnet    $0.7104                $0.8253    $0.2751    $0.2368",
        "codex x gpt-5.6-terra   $0.16-$0.76 (~$0.25)   $0.2568    $0.0856    $0.0819",
    ):
        assert line in blocks[1], line


def test_the_proofs_meter_missed_the_reregistered_line_and_the_record_says_so(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 99's proofs: ~96 metered calls against §96's 64-80, the causes
    named, and the arithmetic re-derived over text a reader holds.

    Each block's input characters are recomputed from the checked-in answers
    at the live template — ticket 03's 48 over the four tasks proved by then
    (§96.1's own 270,238), the full invocation's 24 and the re-prove's 12
    over the two new tasks, the dead stream bounded at the almshouse's own
    block — and the dollar bound is checked to sit where the record says:
    the expectation inside the kept $0.05-0.6, the whole-deliverable bound
    $0.0011 over its ceiling, the overage being the call count's doing.
    """
    template = len(point_grader.PROMPT)
    assert template == 1_461  # §80.5: freezes to this literal when v2 moves.

    round_10_ids = [
        "granary-decide-how-to-answer-for-a-past-day",
        "pumphouse-decide-who-catches-the-backwards-reading",
        "ferryhouse-decide-whether-the-takings-drift-is-a-defect",
    ]
    t03_calls, t03_chars, t03_quoted = proof_block_chars(
        tasks, round_10_ids + [_DRY_CELL]
    )
    assert (t03_calls, t03_chars) == (_TICKET_03_CALLS, 270_238), (
        "§96.1's spent block, re-derived"
    )
    alms_calls, alms_chars, alms_quoted = proof_block_chars(
        tasks, ["almshouse-break-down-the-taking-of-names-out-of-the-book"]
    )
    malt_calls, malt_chars, malt_quoted = proof_block_chars(
        tasks, ["maltings-break-down-the-hardening-of-the-log"]
    )
    assert (alms_calls, malt_calls) == (12, 12)
    assert (alms_chars, malt_chars) == (65_174, 67_232)
    full_chars = alms_chars + malt_chars
    assert full_chars == 132_406

    metered = _TICKET_03_CALLS + _DEAD_CALLS + _FULL_CALLS + _REPROVE_CALLS
    assert metered == 96
    assert metered > _METERED_HIGH, "the re-registered range was missed high"
    assert metered - _DEAD_CALLS - _REPROVE_CALLS == 72 <= _METERED_HIGH, (
        "without the dead stream and the re-prove the meter reads 72, inside"
    )
    archived = _TICKET_03_CALLS - 36 + _FULL_CALLS + _REPROVE_CALLS
    assert archived == 24 + 12 + 12 == 48, (
        "the calls whose rulings were archived: the full invocation's, the "
        "re-prove's and ticket 03's turnpike dozen"
    )
    content_calls = _TICKET_03_CALLS + _FULL_CALLS + _REPROVE_CALLS
    assert content_calls == _ARCHIVED_CONTENT_CALLS

    per_input = _DEEPSEEK_INPUT_PER_MTOK / 1e6
    per_output = _DEEPSEEK_OUTPUT_PER_MTOK / 1e6
    input_tokens = (
        t03_chars // 4 + alms_chars // 4 + full_chars // 4 + malt_chars // 4
    )
    assert input_tokens == 67_559 + 16_293 + 33_101 + 16_808 == 133_761
    input_cost = input_tokens * per_input
    low_out = content_calls * 100
    quoted_whole = t03_quoted + alms_quoted + malt_quoted + malt_quoted
    assert quoted_whole == 328_014
    high_out = content_calls * 300 + quoted_whole // 4
    assert (low_out, high_out) == (8_400, 107_203)
    total_low = round(input_cost + low_out * per_output, 4)
    total_high = round(input_cost + high_out * per_output, 4)
    assert (total_low, total_high) == (0.2098, 0.6011)
    range_low, range_high = _PROOF_RANGE
    assert range_low <= total_low
    assert round(total_high - range_high, 4) == 0.0011, (
        "the whole-deliverable bound sits $0.0011 over the kept ceiling"
    )

    # §95.5's named miss did not happen on the half that is checkable: no
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
    assert set(lengths.values()) == {4_923, 2_390, 5_040, 2_318, 5_341, 2_398}
    assert all(
        length <= _PROOF_ANSWER_CHAR_CAP for length in lengths.values()
    )

    # §96's re-registered line, read out of the amendment's own slice rather
    # than retyped into the record.
    amendment = " ".join(note_part("Round 11 amendment — 2026-08-26").split())
    assert "48 spent + 16–32 selected = 64–80 calls" in amendment

    read = prose(note_section(
        "99. Spend, by cost source, against both registered ranges"
    ))
    assert (
        "**The proofs, against §96's re-registered 64–80 calls: the round "
        "metered ~96, and the re-registered range was missed on the high "
        "side.**"
    ) in read
    assert "**48 spent + 16–32 selected = 64–80 calls**" in read
    assert "ticket 03's selection-less run metered **48**" in read
    assert "36 re-asks of round 10's three tasks" in read
    assert "**three invocations**" in read
    assert "**empty-content stream** (~12 metered calls, nothing archived" in read
    assert "**full** (24: the almshouse's 12 and the maltings' 12)" in read
    assert "**12-call re-prove of the maltings task alone**" in read
    assert "a mechanical span miss on quote style" in read
    assert "**~96 calls against the re-registered 64–80**" in read
    assert "**24 + 12 + 12 = 48 calls' rulings archived**" in read
    assert "**36 rulings standing** in the three proofs subtrees" in read
    assert "the re-prove's maltings pair having replaced the full invocation's" in read
    assert "without which the meter reads 72, inside the range" in read
    assert "**no third registration is opened**" in read
    assert "$0.0011 over the kept ceiling** exactly because ~96 calls" in read
    assert "**an answer longer than 8,000 characters** — did not happen" in read
    assert (
        "reference answers of 4,923, 5,040 and 5,341 characters and foils of "
        "2,390, 2,318 and 2,398"
    ) in read
    assert "still the half with no anchor" in read
    assert "priced here at the registered peak-hour, cache-miss figures" in read
    assert "the console's figure can only sit at or under this arithmetic" in read

    [block] = [
        block
        for block in fenced_blocks(note_section(
            "99. Spend, by cost source, against both registered ranges"
        ))
        if "proofs metered" in block
    ]
    for line in (
        f"ticket 03  {t03_calls} calls x (template + point + answer)        "
        f"= {t03_chars:,} chars / 4 =  {t03_chars // 4:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(t03_chars // 4 * per_input, 4):.4f}",
        f"dead      ~{_DEAD_CALLS} calls, the almshouse's input, nothing back "
        f"=  {alms_chars:,} chars / 4 =  {alms_chars // 4:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(alms_chars // 4 * per_input, 4):.4f}",
        f"full       {_FULL_CALLS} calls, almshouse 12 + maltings 12          "
        f"= {full_chars:,} chars / 4 =  {full_chars // 4:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(full_chars // 4 * per_input, 4):.4f}",
        f"re-prove   {_REPROVE_CALLS} calls, the revised maltings, both sides    "
        f"=  {malt_chars:,} chars / 4 =  {malt_chars // 4:,} tok  x "
        f"${_DEEPSEEK_INPUT_PER_MTOK}/M = ${round(malt_chars // 4 * per_input, 4):.4f}",
        f"output low   {content_calls} x 100 tok thinking, none for the dead "
        f"stream         =   {low_out:,} tok  x "
        f"${_DEEPSEEK_OUTPUT_PER_MTOK}/M = ${round(low_out * per_output, 4):.4f}",
        f"output high  {content_calls} x 300 tok + every archived deliverable "
        f"quoted whole  = {high_out:,} tok  x "
        f"${_DEEPSEEK_OUTPUT_PER_MTOK}/M = ${round(high_out * per_output, 4):.4f}",
        f"round total    ${total_low:.4f} - ${total_high:.4f}",
    ):
        assert line in block, line


def test_the_payment_path_is_disclosed_as_it_was_used() -> None:
    """Section 99's disclosure, and the runbook's same words: the DeepSeek
    key from the operator's session memory, supplied inline in the invoking
    environment by the owner's disclosed exception, and never printed."""
    read = prose(note_section(
        "99. Spend, by cost source, against both registered ranges"
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
    round_11: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 100's table, rebuilt from the artifacts and compared byte for
    byte — the only pin that cannot drift a cell at a time, headers and cost
    sources included."""
    quoted = fenced_blocks(
        note_section("100. The nine cells under three combinations")
    )[0]
    assert quoted == cell_table(round_11, rulings)

    resolved = {
        model: sum(
            1
            for (_, run_model), (verdict, _, _) in rulings.items()
            if run_model == model and verdict
        )
        for _, model in _COMBINATIONS
    }
    assert resolved == _RESOLVED
    assert sum(resolved.values()) == 0, "the point gate's first all-red round"

    measured = prose(note_section("97. What the round measured"))
    assert "**Resolution: 0 of 9.**" in measured
    assert (
        "**0 of 3** on `claude-haiku-4-5`, **0 of 3** on `claude-sonnet-5` "
        "and **0 of 3** on `codex` × `gpt-5.6-terra`"
    ) in measured
    assert "first all-red round" in measured
    assert "`turnpike` on Codex, one named point short" in measured

    said = prose(note_section("100. The nine cells under three combinations"))
    assert "There is no per-category block beside it" in said
    assert "no rate is quoted off it" in said


def test_the_turn_counts_are_quoted_and_refused_in_the_same_breath(
    round_11: dict[tuple[str, str], firstparty_v1.Run],
) -> None:
    """Section 100's turn line, and the definition that makes it uncomparable
    across the harness boundary."""
    assert agents._NOT_A_TURN == frozenset({"reasoning"})
    for _, model in _COMBINATIONS:
        turns = [run.turns for key, run in round_11.items() if key[1] == model]
        assert sum(turns) == _TURNS[model], model
        assert (min(turns), max(turns)) == _TURN_RANGE[model], model

    said = prose(note_section("100. The nine cells under three combinations"))
    assert (
        "Haiku took **31** turns over the three (8–12), sonnet **33** "
        "(11–11), Codex **21** (7–7)."
    ) in said
    assert "**not** comparable across the harness boundary" in said


def test_each_red_cell_names_the_points_its_rulings_left_uncovered(
    tasks: dict[str, firstparty_v1.Task],
    round_11: dict[tuple[str, str], firstparty_v1.Run],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 101: §89's reading on the new action, re-derived whole, plus
    this round's departure — the two demoted rulings, named.

    The table is rebuilt from the archived rulings and compared byte for
    byte, so the record can never claim a point the archive does not. The
    demotions are asserted in the fixture (exactly two, exactly the named
    ones); here the claims around them are checked: each demoted ruling is
    archived `covered` with `verified: false`, each is counted uncovered,
    and neither decided a verdict — both cells have other points uncovered
    outright. The cross-cell reading is re-derived too: six points uncovered
    under all three combinations, two covered by every answer.
    """
    quoted = fenced_blocks(note_section(
        "101. Which point went uncovered, and the two rulings the span rule "
        "demoted"
    ))[0]
    assert quoted == gate_table(rulings)

    for (task_id, model), (verdict, uncovered, present) in rulings.items():
        assert not present, (task_id, model)
        assert verdict is False, "every cell of the round is red"
        key_points = {
            planted.id
            for planted in firstparty_v1.points_key(tasks[task_id]).points
        }
        assert set(uncovered) <= key_points, (task_id, model)

    for (task_id, model), point_id in _DEMOTED.items():
        archive = firstparty_v1.RunRulings.model_validate(
            json.loads(
                firstparty_v1.rulings_file(
                    _RULINGS, task_id, round_11[task_id, model].agent, model
                ).read_text(encoding="utf-8")
            )
        )
        [entry] = [e for e in archive.rulings if e.point_id == point_id]
        assert entry.covered is True and entry.verified is False, (
            "archived as covered, demoted by the span check"
        )
        _, uncovered, _ = rulings[task_id, model]
        assert point_id in uncovered, "the demoted point is counted uncovered"
        assert len([p for p in uncovered if p != point_id]) >= 1, (
            "the demotion decided no verdict: other points are uncovered "
            "outright"
        )

    # The cross-cell reading, re-derived from the fixture's per-cell lists.
    for task_id, point_id in _UNCOVERED_EVERYWHERE:
        for _, model in _COMBINATIONS:
            assert point_id in rulings[task_id, model][1], (task_id, model)
    for task_id, point_id in _COVERED_EVERYWHERE:
        for _, model in _COMBINATIONS:
            assert point_id not in rulings[task_id, model][1], (task_id, model)

    # The collection rule was unexercised: every diff touches the answer file
    # and nothing else, which the record says rather than claiming proof.
    for (task_id, model), run in round_11.items():
        touched = re.findall(r"^diff --git a/(\S+) b/", run.diff, re.MULTILINE)
        assert touched == ["ANSWER.md"], (task_id, model)

    said = prose(note_section(
        "101. Which point went uncovered, and the two rulings the span rule "
        "demoted"
    ))
    assert "**no disqualifier was present in any of the nine answers**" in said
    assert (
        "**Two covered rulings were demoted, and this record says which — "
        "the departure from §89, where none were.**"
    ) in said
    assert "**no quotable span, no coverage**" in said
    assert "`verified: false`" in said
    assert "Neither demotion decided a verdict" in said
    assert (
        "**That is the whole of the verdict reading, and no fraction is "
        "computed over it.**"
    ) in said
    assert "Six planted points went uncovered under **all three combinations**" in said
    assert "Two points were covered by **every** answer" in said
    assert "**fact of the code and its consequence for the decomposition**" in said
    assert (
        "**What the collection rule archived: nothing, because there was "
        "nothing.**"
    ) in said
    assert "unexercised this round as it was in round 10" in said
    assert "**pointer prose is structurally impossible**" in said


def test_no_fraction_over_points_is_quoted_as_a_quality_figure() -> None:
    """§95.4's registered refusal, honoured in the record's own prose.

    The shapes that would break it: a percentage, an `n of m` or `n/m` over a
    point-sized denominator (the keys plant five points each), and the
    English of a coverage rate. What the record is allowed to say is cell
    counts over three and nine — resolution lines — and the named points
    themselves, which §101 checks are there.
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
    said = prose(note_section("104. What this round cannot say"))
    assert "**No coverage-fraction reading of any kind.**" in said
    assert '"four of five covered" as a score' in said


def test_the_coverage_table_and_the_two_moved_sentences_are_verified(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 102: the table as the lint prints it, whole, and the two
    checked-in sentences the round falsified — moved by the round's first
    task before the sweep, verified here rather than re-edited.

    No stale line when it was recorded: the record was written after the
    fill it records. One line has moved since — round 12's three
    explain-style tasks growing `codebase-comprehension`'s row from 4 to 7 —
    and it is named below in round 7's pattern rather than edited in the
    record. The `requirement-decomposition × typescript` zero is disclosed
    as zero by absence, and `performance-optimisation` still prints the
    `- - 0` shape a real zero prints.
    """
    coverage = firstparty_v1.coverage_table(firstparty_v1.load_task_set(_TASKS))
    python = {
        category: count
        for category, surface, language, count in coverage
        if language == "python" and surface == "application"
    }
    assert python[_CATEGORY] == 3, "the round's acceptance figure"
    # 122 when §102 was recorded; round 12's three explain-style
    # `codebase-comprehension` tasks moved the live column to 125, and round
    # 13's three `performance-optimisation` ones to 128 (one by ticket 04,
    # two by ticket 05).
    assert sum(python.values()) == 128
    assert not [
        row for row in coverage if row[0] == _CATEGORY and row[2] == "typescript"
    ], "the TypeScript zero is by absence"
    assert not [row for row in coverage if row[0] == _CATEGORY and row[3] == 0]
    # Round 13's ticket 04 filled `performance-optimisation`'s row — the last
    # authorable zero — and no authorable successor exists to read the shape
    # off, so it is read off `unclassified`'s row, which survives by
    # construction: the loader refuses any task declaring it (the plan-review
    # ruling of 2026-08-29).
    assert ("unclassified", "-", "-", 0) in coverage, (
        "the shape a real zero prints, off the one structural row left"
    )

    main(["lint-v1", "--tasks", str(_TASKS)])
    printed = capsys.readouterr().out
    assert f"lint clean: {tasks_in_set()} task(s) in {_TASKS}" in printed
    [quoted] = fenced_blocks(
        note_section("102. The coverage table, as the lint prints it")
    )
    # Two lines have moved since §102 was recorded, named here in round 7's
    # pattern rather than edited in the record: round 12's three
    # explain-style tasks grew `codebase-comprehension`'s row from 4 to 7,
    # and round 13's ticket 04 turned the `performance-optimisation` zero row
    # this record quotes into the category's first Python cell — the last
    # authorable zero row, `unclassified`'s structural one staying by
    # construction.
    moved = {
        "  codebase-comprehension     application  python      4",
        "  performance-optimisation   -            -           0",
    }
    quoted_lines = quoted.strip("\n").splitlines()
    for moved_line in moved:
        assert moved_line in quoted_lines
        assert moved_line not in printed
    for line in quoted_lines:
        if line in moved:
            continue
        assert line in printed, line
    assert [
        line.split()
        for line in printed.splitlines()
        if line.startswith("  codebase-comprehension")
    ] == [["codebase-comprehension", "application", "python", "7"]]
    assert (
        "  requirement-decomposition  application  python      3"
    ) in quoted
    assert "  requirement-decomposition  -            -           0" not in printed

    said = prose(note_section("102. The coverage table, as the lint prints it"))
    assert (
        "**`requirement-decomposition application python 3` is the round's "
        "acceptance figure**"
    ) in said
    assert "the line that read `requirement-decomposition - - 0`" in said
    assert "zero by absence — which is all the table can express" in said
    assert "**the lint was not changed**" in said
    assert "heap 3 stays on Python until the grader has a record behind it" in said
    assert (
        "**`performance-optimisation` is still disclosed as a zero row**"
    ) in said

    # The two moved sentences, read off the live function and the live file —
    # moved by ticket 03's landing, verified here, re-edited nowhere.
    docstring = " ".join((firstparty_v1.coverage_table.__doc__ or "").split())
    assert (
        "`requirement-decomposition` read zero until round 11 filled its "
        "Python cell"
    ) in docstring
    # Round 13's ticket 04 filled `performance-optimisation`'s Python cell —
    # the last authorable zero row — so the docstring's series now ends with
    # no "today" exemplar at all: there is no authorable successor category
    # to re-point a prose exemplar at, and `unclassified`'s structural row
    # (the loader refuses the category) is named there instead.
    assert (
        "`performance-optimisation` read zero until round 13 filled its "
        "Python cell"
    ) in docstring
    assert "is one of the categories reading zero today" not in docstring
    assert (
        "`requirement-decomposition` is one of the categories reading zero"
    ) not in docstring
    context = _CONTEXT.read_text(encoding="utf-8")
    assert _CONTEXT_SENTENCE in context
    assert "(`requirement-decomposition` today;" not in context
    assert (
        "\"`requirement-decomposition` read zero until round 11 filled its "
        "Python cell; `performance-optimisation` is one of the categories "
        "reading zero today\""
    ) in said
    assert (
        "\"`requirement-decomposition` was one until round 11 filled its "
        "Python cell\""
    ) in said
    # The older exemplar pins' needle loop, verified and not re-edited: the
    # string `performance-optimisation` still stands in each of those files —
    # since round 13's ticket 04 as the filled cell their zero-shape reads
    # moved off (to `unclassified`'s structural row, the only `- - 0` row
    # left) and in their records' own quoted prose, not as a live "reads
    # zero today" claim, of which none remains.
    for suite in (
        "test_firstparty_v1_round7_cells.py",
        "test_firstparty_v1_round7_record.py",
        "test_firstparty_v1_round8_record.py",
        "test_firstparty_v1_round10_record.py",
    ):
        assert "performance-optimisation" in (
            _REPO / "tests" / suite
        ).read_text(encoding="utf-8"), suite


def test_the_second_action_confirmed_the_instruments_record() -> None:
    """Section 103: the sentence the next round planner reads, stated plainly
    (spec user story 16), and quoted against the licence it cashes."""
    said = prose(note_section(
        "103. The second action confirmed the instrument's record"
    ))
    assert (
        "**Confirmed — in as many words: the second heap-3 action confirmed "
        "the instrument's record and did not complicate it.**"
    ) in said
    assert (
        "**The sentence the next round planner reads: the instrument's "
        "record is confirmed, so explain-style `codebase-comprehension` "
        "follows as the last mechanical fill**"
    ) in said
    assert "§86's licence stands cashed a second time" in said
    assert "a finding about actions and not about the instrument" in said
    assert "never as a cross-action difficulty comparison" in said

    # The licence §103 says it cashes is §86's own sentence, still in round
    # 10's record where §95.2 quoted it from.
    record = " ".join(note_part("Round 10 record — 2026-08-24").split())
    assert (
        "planted points survived contact with an open-ended proposal, so "
        "`requirement-decomposition` and explain-style "
        "`codebase-comprehension` can follow as mechanical fills"
    ) in record


def test_what_this_round_cannot_say_is_stated_and_true_of_the_corpus(
    tasks: dict[str, firstparty_v1.Task],
    rulings: dict[tuple[str, str], tuple[bool, list[str], list[str]]],
) -> None:
    """Section 104's refusals, each anchored to something checkable, and the
    disclosures the ticket wants in as many words: the covered-but-mediocre
    narrowing, the transfer gap, and the owner's ~9 labels recorded as
    **given 2026-08-27** — seven of nine agree, two disagree, the
    orchestrator-assistance provenance disclosed, the transfer gap read as
    opened on two cells in one direction."""
    swept = {task_id for task_id, _ in rulings}
    assert all(tasks[task_id].control for task_id in swept)
    assert not [
        task_id for task_id in swept if tasks[task_id].construction is not None
    ]
    assert reconcile_v1.LADDER_MODELS == (_HAIKU, _SONNET)
    assert _TERRA not in reconcile_v1.LADDER_MODELS

    said = prose(note_section("104. What this round cannot say"))
    assert "**Covered is not brilliant — the narrowing, in as many words.**" in said
    assert (
        "Covering every planted point does not certify a good decomposition"
    ) in said
    assert "an agent can cover every planted point with a mediocre one" in said
    assert "never as a certificate of quality beyond its key" in said
    assert "uncovered means a planted fact went unsaid" in said

    assert (
        "**The transfer gap, restated from §79.4, §81.4 and §92.**"
    ) in said
    assert (
        "would have proved the grader judges argued prose against a known "
        "truth — not that it judges a proposal with no truth behind it"
    ) in said
    assert "The proofs' truth is still the author's planted truth" in said

    # The labels: supplied 2026-08-27, the day after the record — seven of
    # nine agree, two disagree — recorded beside the section exactly as
    # given, per its own sentence, with the assistance provenance disclosed.
    assert (
        "**The owner's ~9 agree/disagree labels: given 2026-08-27, the day "
        "after this record — seven of nine agree, two disagree.**"
    ) in said
    assert "chose to supply them later" in said
    assert (
        "**these labels were formed with the orchestrator's assistance and "
        "not by an unaided read**"
    ) in said
    assert "the owner adopted the recommendations" in said
    assert "§76.2 ruled and §77.2 registered" in said
    labels_block = [
        block
        for block in fenced_blocks(note_section("104. What this round cannot say"))
        if "agree" in block
    ]
    assert len(labels_block) == 1, "the labels table, fenced, once"
    assert labels_block[0].count("(machine: unresolved)") == 9
    assert labels_block[0].count("disagree  (machine:") == 2
    assert labels_block[0].count("agree     (machine:") == 7
    # The two disagreements are both sonnet cells, and the gap is read as
    # opened — on two of nine, in one direction, a recall shape the
    # two-sided proofs cannot catch.
    for line in labels_block[0].splitlines():
        if "disagree" in line:
            assert "claude-sonnet-5" in line
    assert (
        "the transfer gap §79.4 named opened, on two of nine and in one "
        "direction"
    ) in said
    assert "a recall shape the two-sided proofs cannot catch" in said
    assert "The check gated nothing and the nine verdicts stand regardless" in said
    assert "the owner held the universal quantifier" in said

    assert "**No cross-action difficulty comparison.**" in said
    assert "0 of 9 here is not to be read against round 10's 1 of 9" in said
    assert (
        "**Nothing about `requirement-decomposition` × `typescript`.**"
    ) in said
    assert "**No Codex rung.**" in said
    assert "**No cross-harness turn comparison.**" in said
    assert "**No multiplier.**" in said


def test_the_limits_and_toolchain_paragraphs_hold_against_the_code(
    round_11: dict[tuple[str, str], firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 97's limits and toolchain paragraphs, against the table the
    runner reads and the interpreter the suite runs on."""
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {600}
    swept = {task_id for task_id, _ in round_11}
    assert {
        firstparty_v1.live_run_limit_s(task)
        for task in tasks.values()
        if task.id in swept
    } == {600} == {firstparty.RUN_TIMEOUT_S}

    latencies = [run.latency_s for run in round_11.values()]
    assert round(max(latencies), 1) == _LONGEST_S
    assert round(statistics.mean(latencies), 1) == _MEAN_S
    assert max(latencies) < 600
    longest = max(round_11.items(), key=lambda item: item[1].latency_s)
    assert longest[0] == (_CHEAPEST_CELL, _SONNET), (
        "the longest run is the maltings on sonnet"
    )

    assert platform.python_version() == _PYTHON_VERSION

    measured = prose(note_section("97. What the round measured"))
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
        "97. What the round measured"
    ), "the instrument, quoted from the code the round ran on"
    assert "**provenance and not a row field**" in measured
    assert "no `grader` field" in measured


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 105's replay, run rather than remembered — and offline.

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
    assert sum(float(record["quality_value"]) for record in merged) == 0

    printed_block = fenced_blocks(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))[0]
    for name, (evaluated, resolved) in _REPLAYED.items():
        assert name in printed_block
        assert (
            f"evaluated {evaluated} runs over {tasks_in_set()} tasks "
            f"({resolved} resolved)"
        ) in printed_block

    said = prose(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))
    assert (
        "**Every round-11 log replays to the verdicts this record quotes, "
        "with the network unplugged.**"
    ) in said
    assert "handed **no grader factory**" in said
    assert "9 rows and 0 resolved" in said
    assert "a table-derived cost is not recomputed on the way through" in said


def test_both_readers_count_the_round_and_print_what_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 105's readers: six of the nine rows inside the default view,
    the reconcile lines quoted as the reader printed them when the record was
    written — the block has moved since, round 12's three tasks and then
    its sweep, and is named inside rather than edited — the calibrate table
    exactly as
    printed, its rung floor reading `unsolved`, and the earlier rounds'
    published tables unmoved."""
    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    reconciled = capsys.readouterr().out
    printed = reconciled.replace(str(_TASKS), "tasks/first-party-v1")
    [quoted] = fenced_blocks(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))[1:2]
    # The whole block has moved since the record was written, named here
    # in round 7's pattern rather than edited there: round 12's three
    # explain-style `codebase-comprehension` tasks, Python controls, grew
    # the task-set line by three tasks and three controls, and the round's
    # sweep (2026-08-28 — nine rows, six of them claude-code Python) then
    # grew the runs line and joined the round list.
    stale = {
        "  task set   tasks/first-party-v1 — 122 task(s): 55 control(s), "
        "67 constructed",
        "  runs       243 over 122 task(s)",
        "  rounds     9 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10, sweep round-11",
        "             7 keyed on a sweep id, 2 on an as-of date",
    }
    quoted_block_lines = quoted.strip("\n").splitlines()
    for line in stale:
        assert line in quoted_block_lines, line
        assert line not in printed, line
    for line in quoted_block_lines:
        if line in stale:
            continue
        assert line in printed, line
    # 125 task(s) and 58 control(s) until round 13 authored its three
    # `performance-optimisation` tasks, Python controls all — one by ticket
    # 04, two by ticket 05 — and that round's sweep (2026-08-29, six
    # claude-code Python rows of its nine) then grew the runs line and
    # joined the round list.
    assert (
        "  task set   tasks/first-party-v1 — 128 task(s): 61 control(s), "
        "67 constructed"
    ) in printed
    assert "  runs       255 over 128 task(s)" in printed
    assert (
        "  rounds     11 round(s): as-of 2026-08-04, as-of 2026-08-05, "
        "sweep round-2, sweep round-3, sweep round-4, sweep round-5, "
        "sweep round-8, sweep round-10, sweep round-11, sweep round-12, "
        "sweep round-13"
    ) in printed
    assert "             9 keyed on a sweep id, 2 on an as-of date" in printed
    assert printed.count(f"sweep {_SWEEP}") == 1
    assert _CATEGORY not in printed, (
        "the round declared no contrast, so it reaches the report as a "
        "label and nothing else"
    )
    assert "   67 constructed task(s): 67 swept, 0 unswept" in printed

    main(["calibrate-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    calibrated = capsys.readouterr().out
    [table] = fenced_blocks(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))[2:3]
    assert table.strip("\n") in calibrated, (
        "the calibration table the record quotes is not what the reader prints"
    )
    assert f"category {_CATEGORY}" in calibrated
    assert (
        "   (zero-knob)  3      1.00x (n=3)       1.00x (n=3)      "
        "unsolved (n=3)"
    ) in calibrated

    said = prose(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))
    assert "**And the readers count the round with no flag at all.**" in said
    assert "**The prediction reconciliation is unmoved**" in said
    assert "a **denominator**" in said
    assert "The rung floor reads **unsolved**" in said
    assert "The published tables of earlier rounds are unmoved" in said


def test_nothing_from_the_proofs_reached_the_unified_dataset(
    runs: list[firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 105's last claims: nothing of the proofs in the unified
    dataset, the free-text archive grown by exactly the nine answers, and
    the registered split the A″ readings are computed over unmoved."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        flat = json.dumps(json.loads(line))
        for needle in (
            "proofs", "reference-answer", "foil", "re-ask",
            "prove-points", "point-gate-calibration",
        ):
            assert needle not in flat, needle

    # Round 12's sweep has since landed nine more answers (2026-08-28) and
    # round 13's nine more (2026-08-29);
    # §105's claim is about the archive as this round left it, so they are
    # scoped back out by sweep id, never by a log filename, and the
    # section's figures stay unretyped.
    archived = [
        run for run in runs
        if run.output and run.sweep not in {"round-12", "round-13"}
    ]
    assert len(archived) == _ARCHIVE_NOW
    assert len(
        [run for run in archived if run.sweep != _SWEEP]
    ) == _ARCHIVE_BEFORE
    stratum_a = [
        run
        for run in runs
        if run.sweep not in {_ANCHOR, _SWEEP, "round-12", "round-13"}
        and firstparty_v1.carries_a_key(tasks[run.task_id])
    ]
    assert len(stratum_a) == _STRATUM_A

    said = prose(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))
    assert "**Nothing from the proofs reached `data/unified.jsonl`.**" in said
    assert "a combination's result on a benchmark instance (§76.11)" in said
    assert (
        "**315 answers across ten sweeps to 324 across eleven**"
    ) in said
    assert "**306 rows, 63 of them stratum A**" in said
    assert "out of that read rather than an error in it" in said


def test_the_record_takes_the_next_free_numbers_and_renumbers_nothing() -> None:
    """Sections 97-105 are the next free numbers after §96, contiguous, each
    spent once, landing before the note's trailing headings — and the last
    section names the next free number, which is the frontier sentence the
    round-9 suite's moved assertion reads."""
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(96) == 1
    assert all(numbered.count(number) == 1 for number in range(97, 106))
    # The live frontier is the round-9 suite's one moved assertion and is
    # deliberately not copied here; what this test owns is that the record's
    # nine numbers are spent once each and nothing above or below them was
    # renumbered — a claim the contiguity range extends over §106 (round 12's
    # rulings), §107 (round 12's pre-registration), §108-§116 (round 12's
    # record, all 2026-08-28), §117 (round 13's rulings), §118 (round 13's
    # pre-registration) and §119-§127 (round 13's record, all 2026-08-29) to
    # keep making.
    assert [number for number in numbered if number > 68] == list(range(69, 128))

    for heading in record_sections():
        assert f"### {heading}\n" in text, heading

    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    record_at = headings.index("## Round 11 record — 2026-08-27")
    assert headings[record_at - 1].startswith("## Round 11 amendment")
    # The heading after the record was `## Open questions` until round 12's
    # rulings landed there (2026-08-28); the claim that survives is that the
    # record sits inside the note's numbered run, before the trailing
    # headings — this adjacency pin moved in the commit that landed §106,
    # exactly as round 10's did when §94 landed.
    assert headings[record_at + 1].startswith("## Round 12 rulings")

    opening = prose(
        note_part("Round 11 record — 2026-08-27").split("\n### ")[0]
    )
    assert "**§97 is the next free number.**" in opening
    assert "this record opens at **97** and runs to **105**" in opening
    assert "Nothing above it is renumbered." in opening

    closing = prose(note_section(
        "105. Replay, the readers, and heap 3's second cell filled"
    ))
    assert "**Heap 3's second cell fills.**" in closing
    assert "**§106 is the next free section number**" in closing
    assert "nothing above is renumbered" in closing
