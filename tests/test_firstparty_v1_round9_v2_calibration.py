"""Round 9's v2 calibration verdict, pinned: §81 against the committed archive.

Grader v2 — §80's prompt revision on the same alias and checkpoint — ran its
one paid experiment on 2026-08-23 and the gate failed again: overall agreement
46 of 63 against the registered ≥ 57 of 63, the unresolved clause met at 7 of
8, and §81 closes the question of this vendor's grader. This file is the
record's pin suite in §79's suite's shape
(`tests/test_firstparty_v1_round9_calibration.py`): every figure §81 quotes is
re-derived from the artifacts that earned it — the v2 rulings archive under
`data/point-gate-calibration/` joined against the same replay split
`calibrate-grader-v1` computes.

Two halves, §79's again. The arithmetic half re-derives both stratum-A counts
and the stratum-B figure, audits every covered ruling's evidence span
mechanically under the v2 rule (§80.3: whitespace normalisation plus the
markdown-stripped fallback), checks the one-ruling-per-point shape (115 +
243), the version stamping the archive and naming its file, and that nothing
reached `data/unified.jsonl`. The prose half reads §81 itself: its quoted
counts equal the derived ones, the pointer confound and the transfer gap are
stated, and the failed branch's closing sentence is present.

§80.5's freezing rule, carried forward: this suite reaches the live
`point_grader.GRADER_VERSION` and the live `span_in_deliverable` because v2
is the instrument §81's record was computed under; the next time the
instrument moves, both freeze here to v2's literals, exactly as §79's suite
froze to v1's.

Everything here is offline: the archive is read, the machine verdicts are
replayed from the checked-in run logs, and no grader client is ever built.
"""

import json
from pathlib import Path

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

# §81's quoted figures, as counts a reader can check by hand — the registered
# bar beside them so the verdict is arithmetic, not judgment.
_OVERALL_AGREED = 46
_OVERALL_OF = 63
_OVERALL_BAR = 57
_UNRESOLVED_AGREED = 7
_UNRESOLVED_OF = 8
_UNRESOLVED_BAR = 7
_STRATUM_B_AGREED = 157
_STRATUM_B_OF = 243
_POINTS_A = 115
_POINTS_B = 243
# §81.2: mechanism (b)'s residue — covered rulings the v2 span rule refused,
# archive-wide. v1's archive held fifteen; this one holds two.
_SPAN_REFUSED = 2


@pytest.fixture(scope="module")
def archive() -> calibration.CalibrationRulings:
    """The committed v2 rulings archive, whole — a missing archive is a loud
    failure of the record, never a skip."""
    loaded = calibration.read_rulings(_ARCHIVE)
    assert loaded is not None, f"the rulings archive is missing at {_ARCHIVE}"
    return loaded


@pytest.fixture(scope="module")
def answers() -> list[calibration.ArchivedAnswer]:
    """The same split the experiment graded: every archived answer, stratified
    and machine-scored by replay, no network."""
    tasks = firstparty_v1.load_task_set(_TASKS)
    logs = reconcile_v1.collect_logs([_LOGS])
    # This suite pins §81's run, whose inputs were the rows that existed at
    # that run — every sweep before round 10's, which landed the first
    # `investigation` rows the day after, round 11's `requirement-decomposition`
    # rows following on 2026-08-26 and round 12's `codebase-comprehension`
    # rows on 2026-08-28. Scoped by sweep id, never by a log
    # filename; the constants below stay §81's own, unretyped.
    runs = [
        run for log in logs for run in load_runs(log)
        if run.sweep not in {"round-10", "round-11", "round-12"}
    ]
    return calibration.split(tasks, runs)


def _by_cell(
    archive: calibration.CalibrationRulings,
) -> dict[tuple[str, str, str], calibration.AnswerRulings]:
    return {
        (one.task_id, one.agent, one.model): one for one in archive.answers
    }


def _grader_resolved(rulings: calibration.AnswerRulings) -> bool:
    """The gate's own verdict shape over archived rulings: every point covered
    with a mechanically verified span."""
    return all(one.covered and one.verified for one in rulings.rulings)


# --- the arithmetic: §81's counts re-derived from the archive -----------------


def test_the_archive_holds_one_ruling_per_point_and_nothing_more(
    archive: calibration.CalibrationRulings,
    answers: list[calibration.ArchivedAnswer],
) -> None:
    by_cell = _by_cell(archive)
    assert len(archive.answers) == len(answers) == 306

    points_a = 0
    points_b = 0
    for answer in answers:
        rulings = by_cell[answer.cell]
        assert len(rulings.rulings) == len(answer.points), (
            f"{answer.cell}: {len(rulings.rulings)} ruling(s) for "
            f"{len(answer.points)} point(s)"
        )
        ruled = [one.point_id for one in rulings.rulings]
        assert ruled == [point["id"] for point in answer.points]
        if answer.stratum == "A":
            points_a += len(rulings.rulings)
        else:
            points_b += len(rulings.rulings)
    assert points_a == _POINTS_A
    assert points_b == _POINTS_B


def test_the_archive_is_pinned_to_the_grader_version_and_named_by_it(
    archive: calibration.CalibrationRulings,
) -> None:
    """The version is stamped once at the archive level and the file is named
    by it — one rulings file per instrument version (§77.8's sentence). The
    live `GRADER_VERSION` is the right read today because v2 is the current
    instrument; see the module docstring for when this freezes."""
    assert archive.grader_version == point_grader.GRADER_VERSION
    assert _ARCHIVE.name == f"{point_grader.GRADER_VERSION}.json"


def test_both_stratum_a_figures_re_derive_to_the_quoted_counts(
    archive: calibration.CalibrationRulings,
    answers: list[calibration.ArchivedAnswer],
) -> None:
    by_cell = _by_cell(archive)
    stratum_a = [one for one in answers if one.stratum == "A"]
    assert len(stratum_a) == _OVERALL_OF

    agreed = sum(
        1
        for answer in stratum_a
        if _grader_resolved(by_cell[answer.cell]) == answer.machine_resolved
    )
    assert agreed == _OVERALL_AGREED

    unresolved = [one for one in stratum_a if not one.machine_resolved]
    assert len(unresolved) == _UNRESOLVED_OF
    unresolved_agreed = sum(
        1
        for answer in unresolved
        if not _grader_resolved(by_cell[answer.cell])
    )
    assert unresolved_agreed == _UNRESOLVED_AGREED

    # The verdict is arithmetic against the registered bar, and it is FAILED
    # again: the unresolved clause met, the overall clause eleven short.
    assert unresolved_agreed >= _UNRESOLVED_BAR
    assert agreed < _OVERALL_BAR


def test_the_stratum_b_figure_re_derives_and_gates_nothing(
    archive: calibration.CalibrationRulings,
    answers: list[calibration.ArchivedAnswer],
) -> None:
    by_cell = _by_cell(archive)
    stratum_b = [one for one in answers if one.stratum == "B"]
    assert len(stratum_b) == _STRATUM_B_OF
    agreed = sum(
        1
        for answer in stratum_b
        if _grader_resolved(by_cell[answer.cell]) == answer.machine_resolved
    )
    assert agreed == _STRATUM_B_AGREED


def test_every_covered_rulings_span_is_audited_mechanically(
    archive: calibration.CalibrationRulings,
    answers: list[calibration.ArchivedAnswer],
) -> None:
    """The span audit, over the whole archive, under the v2 rule: a covered
    ruling's archived `verified` flag equals what the live
    `point_grader.span_in_deliverable` — whitespace normalisation plus §80.3's
    markdown-stripped fallback — says about its span against the deliverable
    it was quoted from. §81.2 counts mechanism (b)'s residue at two; the flag,
    not blanket truth, is what an honest audit pins."""
    deliverables = {one.cell: one.deliverable for one in answers}
    covered = 0
    refused = 0
    for answer in archive.answers:
        deliverable = deliverables[(answer.task_id, answer.agent, answer.model)]
        for ruling in answer.rulings:
            if not ruling.covered:
                assert not ruling.verified
                continue
            covered += 1
            assert ruling.span is not None, (
                "a covered ruling without a span is not a covered ruling"
            )
            mechanical = point_grader.span_in_deliverable(
                ruling.span, deliverable
            )
            assert ruling.verified == mechanical, (
                f"{answer.task_id} [{ruling.point_id}]: archived "
                f"verified={ruling.verified} but the mechanical check says "
                f"{mechanical}"
            )
            if not mechanical:
                refused += 1
    assert covered > 0
    assert refused == _SPAN_REFUSED, (
        "§81.2 counts the paraphrased-quote residue at two archive-wide"
    )


def test_nothing_from_calibration_reached_the_unified_dataset() -> None:
    """A record keeps meaning one thing: a combination's result on an
    instance. Calibration rulings are instrument data and stay out."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        row = json.loads(line)
        flat = json.dumps(row)
        assert "point-gate-calibration" not in flat
        assert "round-9" not in json.dumps(row.get("sweep_id", ""))


# --- the prose: §81 against the archive ---------------------------------------


def _section_81() -> str:
    """§81 with its hard wraps folded, so phrase assertions read across the
    note's 75-column line breaks. The slice is deliberate (§80.5's lesson,
    named in the runbook): from §81's own heading to the next top-level
    heading, never to a landmark further down that would silently swallow a
    later section."""
    text = _NOTE.read_text(encoding="utf-8")
    start = text.index("**81. The v2 calibration verdict")
    end = text.index("\n## ", start)
    return " ".join(text[start:end].split())


def test_the_record_quotes_the_derived_counts_and_the_verdict() -> None:
    record = _section_81()
    assert f"{_OVERALL_AGREED} of {_OVERALL_OF}" in record
    assert f">= {_OVERALL_BAR} of {_OVERALL_OF}" in record
    assert f"{_UNRESOLVED_AGREED} of {_UNRESOLVED_OF}" in record
    assert f"{_STRATUM_B_AGREED} of {_STRATUM_B_OF}" in record
    assert "NOT MET" in record
    assert "the gate is failed" in record
    assert "358" in record, "the spend is quoted in calls"
    # v2 is the instrument §81 quotes; the live read is right until the
    # instrument moves (module docstring).
    assert point_grader.GRADER_VERSION in record


def test_the_record_states_the_gap_the_confound_and_the_pointer_finding(
) -> None:
    record = _section_81()
    # The transfer gap, in as many words (§81.4).
    assert "judges argued prose against a known truth" in record
    assert "no truth behind it" in record
    # Stratum B's confound, named (§81.3).
    assert "narrative truthfulness" in record
    assert "gating nothing" in record
    # §81.2's own finding: the pointer confound the mechanisms' removal
    # uncovered, sized but never re-scored.
    assert "pointer" in record
    assert "never to re-score a registered gate" in record
    assert "no prompt can quote what a deliverable does not contain" in record


def test_the_record_closes_the_vendor_question_on_the_failed_branch() -> None:
    record = _section_81()
    assert "closes the question of this vendor's grader" in record
    assert "design discussion, not a third prompt" in record
    assert "Heap 3 stays empty" in record
    assert "#131" in record and "#134" in record
    assert "#127" in record and "either branch" in record
