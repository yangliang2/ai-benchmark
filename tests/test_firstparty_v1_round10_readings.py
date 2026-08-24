"""Round 10's A″ readings, pinned: §84 against the archive that earned it.

§82.5 took the gate off A″ the day §82.3 gave it one, so what §84 reports is a
**reading and not a verdict**: two mechanical operationalisations of the
pointer-prose filter, both applied to the committed v2 rulings archive, both
disclosed, neither compared with a bar. This file is that section's pin suite,
in the shape of `tests/test_firstparty_v1_round9_v2_calibration.py`: every
count §84 quotes is re-derived here from the artifacts that produced it — the
archive under `data/point-gate-calibration/` joined against the same replay
split `calibrate-grader-v1` computes — and the section's prose is then read
against the derivation rather than the other way round.

**Everything here is offline and no grader client is constructed.** The
archive is read, machine verdicts are replayed from the checked-in run logs,
and `point_grader.deepseek_point_grader` is monkeypatched to raise for the
whole module, so a construction anywhere in this file is a failure and not a
silent live call. The read the section reports cost zero new paid calls and so
does checking it.

**The row set is scoped to the registered split**, the stratum-A rows the
archive holds rulings for, exactly as `--pointer-filtered-read` scopes it. A
run-log row the archive does not name is out of the read, so this suite stays
green after the round's own sweep lands its nine `round-10` rows: they are new
cells the archive never registered, the denominator does not move, and §84's
counts re-derive identically before and after. Logs are collected wholesale
and **no run log is selected by filename**.

Two standing rules of this corpus's pin suites, kept here. §80.5's **freezing
rule**: this suite reaches the live `point_grader.GRADER_VERSION` because v2 is
the instrument §84's readings were taken under, and the next time the
instrument moves it freezes here to v2's literal tuple. And the **slice rule**:
§84 is sliced from its own heading to the **next top-level heading**, never to
a landmark further down such as `## Open questions`, which would silently
swallow whatever section lands between them.
"""

import json
import re
from inspect import signature
from pathlib import Path
from typing import Iterator

import pytest

from ai_benchmark import firstparty_v1, point_grader, reconcile_v1
from ai_benchmark import grader_calibration_v1 as calibration
from ai_benchmark.firstparty_v1 import load_runs

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"
_UNIFIED = _REPO / "data" / "unified.jsonl"

_ARCHIVE = (
    _REPO
    / "data"
    / "point-gate-calibration"
    / f"{point_grader.GRADER_VERSION}.json"
)

# The registered split, as §83.9 registered it and §84.1 quotes it.
_REGISTERED_ROWS = 306
_STRATUM_A = 63

# §84.2's table, held as the counts a reader can check by hand. Four numbers an
# operationalisation: the rows it caught, the A″ denominator left, the overall
# agreement over that denominator, and the unresolved-class agreement inside it.
_READINGS = {
    "file-reference": {
        "caught": 17,
        "denominator": 46,
        "agreed": 42,
        "unresolved_agreed": 3,
        "unresolved": 4,
    },
    "file-or-symbol": {
        "caught": 15,
        "denominator": 48,
        "agreed": 44,
        "unresolved_agreed": 5,
        "unresolved": 6,
    },
}

# §84.4's divergence, the two pairs by name. The symbol-only narrations are what
# split the two readings; the true pointers are the rows a verdict-blind filter
# reached and §81.1's verdict-aware inspection could not.
_SYMBOL_ONLY = (
    ("belfry-review-the-peals-and-the-board", "claude-code", "claude-haiku-4-5"),
    ("parishhall-review-the-hire-and-the-diary", "claude-code", "claude-haiku-4-5"),
)
_TRUE_POINTERS = (
    ("apiary-review-the-book-and-the-crop", "codex", "gpt-5.6-terra"),
    ("paperround-locate-the-carried-over-count", "claude-code", "claude-sonnet-5"),
)

Cell = tuple[str, str, str]


@pytest.fixture(scope="module", autouse=True)
def no_grader_can_be_built() -> Iterator[None]:
    """The offline claim, made structural for the whole module.

    §84.5 says no grader client was constructed and no paid call made. Nothing
    below should reach the one factory there is, so the factory is replaced by a
    detonator: a construction anywhere in this file fails the suite instead of
    quietly asking for a key.
    """
    original = point_grader.deepseek_point_grader

    def refuse() -> point_grader.PointGrader:
        raise AssertionError(
            "§84's readings are a derivation over spent rulings — this suite "
            "builds no grader client and makes no paid call"
        )

    point_grader.deepseek_point_grader = refuse
    try:
        yield
    finally:
        point_grader.deepseek_point_grader = original


@pytest.fixture(scope="module")
def archive() -> calibration.CalibrationRulings:
    """The committed v2 rulings archive, whole — a missing archive is a loud
    failure of the readings, never a skip."""
    loaded = calibration.read_rulings(_ARCHIVE)
    assert loaded is not None, f"the rulings archive is missing at {_ARCHIVE}"
    return loaded


@pytest.fixture(scope="module")
def registered_stratum_a(
    archive: calibration.CalibrationRulings,
) -> dict[Cell, calibration.AnswerRulings]:
    """The stratum-A rows of the registered split: the cells the archive holds
    rulings for, which is what fixes the denominator of both readings."""
    return {
        (one.task_id, one.agent, one.model): one
        for one in archive.answers
        if one.stratum == "A"
    }


@pytest.fixture(scope="module")
def logs() -> list[Path]:
    """Every run log under the corpus's log directory, collected wholesale.

    Never selected by filename: the sweep protocol's rule, after the round-1
    analysis silently dropped two paid cells by filtering on a name.
    """
    return reconcile_v1.collect_logs([_LOGS])


@pytest.fixture(scope="module")
def rows(logs: list[Path]) -> dict[Cell, firstparty_v1.Run]:
    collected: dict[Cell, firstparty_v1.Run] = {}
    for log in logs:
        for run in load_runs(log):
            cell = (run.task_id, run.agent, run.model)
            assert cell not in collected, f"{cell}: two rows of one cell"
            collected[cell] = run
    return collected


@pytest.fixture(scope="module")
def derived(
    registered_stratum_a: dict[Cell, calibration.AnswerRulings],
    rows: dict[Cell, firstparty_v1.Run],
) -> list[calibration.ArchivedAnswer]:
    """The stratum-A answers of the registered split, machine-scored by replay.

    Only the registered cells are replayed — which is both the scoping §84.1
    describes and the reason a later sweep neither moves a count nor slows this
    suite down by the rows it adds.
    """
    tasks = firstparty_v1.load_task_set(_TASKS)
    scoped = [rows[cell] for cell in sorted(registered_stratum_a)]
    answers = calibration.split(tasks, scoped)
    assert all(one.stratum == "A" for one in answers)
    return answers


def _grader_resolved(rulings: calibration.AnswerRulings) -> bool:
    """The gate's own verdict shape over archived rulings: every point covered
    with a mechanically verified span (§76.5, §76.6). The `verified` flag is
    audited against the live span rule by round 9's own suite, which is where
    that audit belongs — this file re-derives readings, not the instrument."""
    return all(one.covered and one.verified for one in rulings.rulings)


def _reading(
    operationalisation: calibration.Operationalisation,
    answers: list[calibration.ArchivedAnswer],
    registered: dict[Cell, calibration.AnswerRulings],
) -> dict[str, int]:
    """One operationalisation's four counts, re-derived by hand rather than read
    off the module's own `Reading`, so that the section is pinned to the
    arithmetic and not to one implementation of it."""
    kept = [
        one
        for one in answers
        if not operationalisation.catches(one.deliverable, one.task)
    ]
    unresolved = [one for one in kept if not one.machine_resolved]
    return {
        "caught": len(answers) - len(kept),
        "denominator": len(kept),
        "agreed": sum(
            1
            for one in kept
            if _grader_resolved(registered[one.cell]) == one.machine_resolved
        ),
        "unresolved": len(unresolved),
        "unresolved_agreed": sum(
            1 for one in unresolved if not _grader_resolved(registered[one.cell])
        ),
    }


def _caught(
    operationalisation: calibration.Operationalisation,
    answers: list[calibration.ArchivedAnswer],
) -> set[Cell]:
    return {
        one.cell
        for one in answers
        if operationalisation.catches(one.deliverable, one.task)
    }


def _section_84() -> str:
    """§84 with its hard wraps folded, so phrase assertions read across the
    note's 75-column line breaks.

    The slice is deliberate (§80.5's lesson, named in the runbook): from §84's
    own heading to the **next top-level heading**, never to `## Open questions`
    or any other landmark further down, which would swallow every section that
    later lands between the two.
    """
    text = _NOTE.read_text(encoding="utf-8")
    start = text.index("## Round 10 A″ readings — read ")
    end = text.index("\n## ", start + 1)
    return " ".join(text[start:end].split())


# --- the arithmetic: both readings re-derived from the archive -----------------


def test_the_row_set_is_the_registered_split_and_a_later_sweep_moves_no_reading(
    archive: calibration.CalibrationRulings,
    registered_stratum_a: dict[Cell, calibration.AnswerRulings],
    rows: dict[Cell, firstparty_v1.Run],
    logs: list[Path],
) -> None:
    """§84.1's row set: 306 registered rows, 63 of them stratum A, every one of
    them still in the logs — and any log row the archive does not name is out of
    the read rather than an error in it.

    That last clause is the whole reason this suite survives the round's own
    sweep: the nine `round-10` cells are rows the archive never registered, so
    they are outside the set both readings are taken over and §84's counts do
    not move when they land.
    """
    assert len(archive.answers) == _REGISTERED_ROWS
    assert len(registered_stratum_a) == _STRATUM_A
    assert logs, "the run logs are collected wholesale and there are some"

    missing = sorted(set(registered_stratum_a) - set(rows))
    assert not missing, f"registered rows the logs no longer hold: {missing}"

    section = _section_84()
    assert f"**{_REGISTERED_ROWS} rows the archive holds rulings for**" in section
    assert f"**{_STRATUM_A} are stratum A**" in section
    assert "never selected by filename" in section
    assert "is *out of this read* rather than an error in it" in section


def test_both_readings_re_derive_to_the_counts_the_section_quotes(
    derived: list[calibration.ArchivedAnswer],
    registered_stratum_a: dict[Cell, calibration.AnswerRulings],
) -> None:
    """§84.2's table, every figure of it: computed here from the archive and the
    logs, then found in the section — not read out of the section and believed.
    """
    section = _section_84()
    assert len(derived) == _STRATUM_A

    for operationalisation in calibration.OPERATIONALISATIONS:
        name = operationalisation.name
        actual = _reading(operationalisation, derived, registered_stratum_a)
        assert actual == _READINGS[name], name

        # The section's own row, whitespace folded: caught, denominator, overall
        # agreement, unresolved-class agreement, in that order and no other.
        assert (
            f"{name} {actual['caught']} {actual['denominator']} "
            f"{actual['agreed']} of {actual['denominator']} "
            f"{actual['unresolved_agreed']} of {actual['unresolved']}"
        ) in section, name


def test_the_section_names_every_row_the_filters_caught(
    derived: list[calibration.ArchivedAnswer],
) -> None:
    """§84.2 names the caught rows rather than counting at them, so a reader can
    go and look at each one. The two columns are checked against each other too:
    the symbol-aware catch is a strict subset, and the difference is exactly the
    two rows §84.4 reads."""
    section = _section_84()
    by_file = _caught(calibration.FILE_REFERENCE, derived)
    by_symbol = _caught(calibration.FILE_OR_SYMBOL, derived)

    assert len(by_file) == _READINGS["file-reference"]["caught"]
    assert len(by_symbol) == _READINGS["file-or-symbol"]["caught"]
    assert by_symbol < by_file
    assert by_file - by_symbol == set(_SYMBOL_ONLY)
    assert set(_TRUE_POINTERS) <= by_symbol

    for task_id, agent, model in sorted(by_file):
        assert f"{task_id} {agent} {model}" in section, (task_id, agent, model)


def test_the_instrument_tuple_is_the_live_grader_version_and_not_retyped() -> None:
    """§84.1 quotes the instrument out of `point_grader.GRADER_VERSION` and names
    the archive file by it. The live read is the right one while v2 is the
    instrument these readings were taken under; see the module docstring for when
    it freezes."""
    section = _section_84()
    assert point_grader.GRADER_VERSION in section
    assert f"{point_grader.GRADER_VERSION}.json" in section
    assert _ARCHIVE.name == f"{point_grader.GRADER_VERSION}.json"
    assert "`point_grader.GRADER_VERSION`" in section


# --- the prose: what §84 must say, and what it must not -------------------------


def test_the_knowable_outcome_disclosure_is_stated_beside_the_numbers() -> None:
    """§82.2's disclosure, in as many words, and inside the subsection that
    carries the counts rather than a page away from them — the ticket's "beside
    the numbers themselves"."""
    section = _section_84()
    counts = section[section.index("84.2") : section.index("84.3")]
    assert (
        "the A″ read is a derivation over spent rulings, and its outcome is "
        "knowable at registration time" in counts
    )
    assert "not a blind pre-registration and does not claim to be one" in counts
    # And what its honesty rests on: the filters' independence from every verdict.
    assert "never a verdict, a ruling, a category or a stratum" in counts
    assert "**both** readings being reported whole" in counts


def test_the_section_says_the_readings_gate_nothing_and_why() -> None:
    """§82.5's ruling in its own words, and the two reasons it gave: an overall
    clause exactly at its bar under either definition, and a filtered unresolved
    class §77.3's own sentence disqualifies."""
    section = _section_84()
    assert "The readings gate nothing" in section
    assert (
        "a gate whose verdict flips on tokenisation minutiae certifies nothing"
        in section
    )
    assert (
        "both operationalisations are reported as readings, both disclosed, and "
        "neither is tuned into gating" in section
    )
    assert (
        "overall clause sitting exactly at its bar under either definition"
        in section
    )
    assert (
        "on a class this size a percentage hides how few answers separate met "
        "from failed" in section
    )
    assert "The round's one gate is §83.4's, and it is the proofs." in section


def test_no_bar_no_verdict_and_no_percentage_is_presented_as_a_result() -> None:
    """A reading is not a verdict, so the section prints none of a verdict's
    furniture.

    No bar expression (`>=`, `≥`, a registered count to clear), no percentage,
    and no verdict word in the shape a record prints one (`MET`, `NOT MET`,
    `FAILED`). The lowercase pair "met"/"failed" is not searched for: in this
    section it occurs only inside §77.3's own quoted sentence about why a
    percentage on a small class misleads, which is a reason these readings gate
    nothing rather than a result they produced.
    """
    section = _section_84()
    for verdict in ("NOT MET", "MET", "FAILED", "PASSED"):
        assert verdict not in section, verdict
    for bar in (">=", "≥", "the bar is", "against the bar", "met the bar"):
        assert bar not in section, bar
    assert not re.search(r"\d\s*%", section), "no percentage is presented"
    assert not re.search(r"\bper cent\b", section)
    # §76.4's bar and §81's counts belong to their own sections; nothing here is
    # read against either.
    assert "90/80" not in section
    assert "57 of 63" not in section
    assert "the gate is" not in section


def test_the_divergence_is_named_and_read_rather_than_scored() -> None:
    """§84.4: the two rows the operationalisations disagree about, and the two
    agreeing-row true pointers the verdict-blind filter reached."""
    section = _section_84()

    for task_id, _agent, model in _SYMBOL_ONLY:
        assert task_id in section
        assert model in section
    assert "Book.rung_by" in section and "Diary.cancel" in section
    assert "by symbol alone" in section
    assert "naming no location *and no finding*" in section

    for task_id, _agent, _model in _TRUE_POINTERS:
        assert task_id in section
    assert "verdict-blind and the inspection was not" in section
    assert "**four rows**" in section
    assert "they are read here and neither is scored" in section
    assert "Read, and not scored" in section


def test_the_preview_difference_is_recorded_as_a_finding() -> None:
    """§82.5's preview counts were anchors, not registrations. §84.6 records what
    the comparison found rather than reconciling the section to the preview —
    here, that there was no difference, said in a line rather than by silence."""
    section = _section_84()
    assert "**anchors and not registrations**" in section
    assert "no difference to record" in section
    assert "There is none" in section
    assert "**the command's figures are the preview's, figure for figure**" in section


def test_the_section_says_no_new_paid_call_was_made() -> None:
    section = _section_84()
    assert "**No new paid call was made.**" in section
    assert "zero new paid calls" in section
    assert "no key was read and no network was reached" in section
    assert "the archive was read and never written" in section


def test_the_read_path_cannot_construct_a_grader() -> None:
    """§84.5's structural claim, checked against the code rather than trusted:
    the filtered read takes no grader factory, so there is nothing for it to call
    — a factory it happened to call zero times would be a different promise."""
    for function in (
        calibration.pointer_filtered_read,
        calibration.read_registered_split,
    ):
        parameters = signature(function).parameters
        assert not any(
            "grader" in name or "factory" in name for name in parameters
        ), function.__name__


def test_nothing_from_this_read_reached_the_unified_dataset() -> None:
    """A record keeps meaning one thing: a combination's result on an instance.
    Calibration rulings are instrument data and stay under
    `data/point-gate-calibration/` (§76.11)."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        row = json.loads(line)
        flat = json.dumps(row)
        assert "point-gate-calibration" not in flat
        assert "pointer-filtered" not in flat
    section = _section_84()
    assert "**nothing from this read entered `data/unified.jsonl`**" in section
