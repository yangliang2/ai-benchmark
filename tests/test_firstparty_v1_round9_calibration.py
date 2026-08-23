"""Round 9's calibration verdict, pinned: §79 against the committed archive.

The experiment ran once — 358 paid grader calls on 2026-08-23 — and the gate
failed: overall agreement 15 of 63 against the registered ≥ 57 of 63, with the
unresolved clause met at 7 of 8. This file is the record's pin suite in the
round-record style (`tests/test_firstparty_v1_round8_record.py`): every figure
§79 quotes is re-derived here from the artifacts that earned it — the rulings
archive under `data/point-gate-calibration/` joined against the same replay
split `calibrate-grader-v1` computes — because a record whose numbers drift
from its artifacts is the defect these suites exist to catch.

Two halves, as always. The arithmetic half re-derives both stratum-A counts
and the stratum-B figure from the archive, audits every covered ruling's
evidence span mechanically (the whole reason spans are mandatory, and cheap to
check over the archive), checks the one-ruling-per-point shape (115 + 243),
the version pinning the archive and naming its file, and that nothing from calibration reached
`data/unified.jsonl`. The prose half reads §79 itself: its quoted counts equal
the derived ones, the transfer gap is stated, and stratum B's confound is
named rather than left to a footnote nobody wrote.

Everything here is offline: the archive is read, the machine verdicts are
replayed from the checked-in run logs, and no grader client is ever built —
replay's own property (§76.6), leaned on by its pin suite.
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
# §80.5: v1's version tuple, a literal of this suite rather than a read of the
# live `point_grader.GRADER_VERSION`. One rulings file is one instrument's, and
# §79 is v1's record — the archive path must not follow a moving version.
_V1_GRADER_VERSION = "deepseek-v4-pro:DeepSeek-V4-Pro-0813:5ec690f5eb62"

_ARCHIVE = (
    _REPO / "data" / "point-gate-calibration" / f"{_V1_GRADER_VERSION}.json"
)

# §79's quoted figures, as counts a reader can check by hand — the registered
# bar beside them so the verdict is arithmetic, not judgment.
_OVERALL_AGREED = 15
_OVERALL_OF = 63
_OVERALL_BAR = 57
_UNRESOLVED_AGREED = 7
_UNRESOLVED_OF = 8
_UNRESOLVED_BAR = 7
_STRATUM_B_AGREED = 149
_STRATUM_B_OF = 243
_POINTS_A = 115
_POINTS_B = 243


@pytest.fixture(scope="module")
def archive() -> calibration.CalibrationRulings:
    """The committed rulings archive, whole — a missing archive is a loud
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
    runs = [run for log in logs for run in load_runs(log)]
    return calibration.split(tasks, runs)


def _by_cell(
    archive: calibration.CalibrationRulings,
) -> dict[tuple[str, str, str], calibration.AnswerRulings]:
    return {
        (one.task_id, one.agent, one.model): one for one in archive.answers
    }


def _span_holds_under_v1(span: str, deliverable: str) -> bool:
    """v1's span rule, whitespace-only — pinned locally per §80.5.

    §79's figures were computed under it, and v2's `span_in_deliverable` gained
    a markdown-stripped fallback (§80.3) that would newly accept §79.2(b)'s
    fifteen refused quotes. This suite audits frozen data, so it keeps v1's
    comparison — calling the unchanged `point_grader.normalise_whitespace`
    rather than re-implementing it.
    """
    return point_grader.normalise_whitespace(
        span
    ) in point_grader.normalise_whitespace(deliverable)


def _grader_resolved(rulings: calibration.AnswerRulings) -> bool:
    """The gate's own verdict shape over archived rulings: every point covered
    with a mechanically verified span."""
    return all(one.covered and one.verified for one in rulings.rulings)


# --- the arithmetic: §79's counts re-derived from the archive -----------------


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
    by it — one rulings file per instrument version (§77.8's sentence), so a
    version change cannot silently continue an old file."""
    assert archive.grader_version == _V1_GRADER_VERSION
    assert _ARCHIVE.name == f"{_V1_GRADER_VERSION}.json"


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

    # The verdict is arithmetic against the registered bar, and it is FAILED:
    # the unresolved clause met, the overall clause not.
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
    """The span audit, over the whole archive: a covered ruling's archived
    `verified` flag equals what `point_grader`'s own normalisation says about
    its span against the deliverable it was quoted from. §79.2's second
    mechanism (the paraphrased quote) lives in exactly the covered rulings
    whose spans this check refuses — so the flag, not blanket truth, is what
    an honest audit pins."""
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
            mechanical = _span_holds_under_v1(ruling.span, deliverable)
            assert ruling.verified == mechanical, (
                f"{answer.task_id} [{ruling.point_id}]: archived "
                f"verified={ruling.verified} but the mechanical check says "
                f"{mechanical}"
            )
            if not mechanical:
                refused += 1
    assert covered > 0
    assert refused > 0, (
        "§79.2 names the paraphrased-quote mechanism; the archive should hold "
        "at least one covered ruling the span check refused"
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


# --- the prose: §79 against the archive ---------------------------------------


def _section_79() -> str:
    """§79 with its hard wraps folded, so phrase assertions read across the
    note's 75-column line breaks."""
    text = _NOTE.read_text(encoding="utf-8")
    start = text.index("**79. The calibration verdict")
    # §80.5: §79 ends where round 9's second amendment begins. Slicing to
    # `## Open questions` would swallow §80 whole, and these pins would stop
    # being assertions about §79's own text.
    end = text.index("## Round 9 second amendment", start)
    return " ".join(text[start:end].split())


def test_the_record_quotes_the_derived_counts_and_the_verdict() -> None:
    record = _section_79()
    assert f"{_OVERALL_AGREED} of {_OVERALL_OF}" in record
    assert f">= {_OVERALL_BAR} of {_OVERALL_OF}" in record
    assert f"{_UNRESOLVED_AGREED} of {_UNRESOLVED_OF}" in record
    assert f"{_STRATUM_B_AGREED} of {_STRATUM_B_OF}" in record
    assert "NOT MET" in record
    assert "the gate is failed" in record
    assert "358" in record, "the spend is quoted in calls"
    # §80.5: §79 quotes v1's tuple and is not edited, so this reads the same
    # literal the archive is named by.
    assert _V1_GRADER_VERSION in record


def test_the_record_states_the_transfer_gap_and_the_confound(
) -> None:
    record = _section_79()
    # The transfer gap, in as many words (§76.2 via §79.4).
    assert "judges argued prose against a known truth" in record
    assert "no truth behind it" in record
    # Stratum B's confound, named (§79.3).
    assert "narrative truthfulness" in record
    assert "gating nothing" in record


def test_the_record_closes_the_round_on_the_failed_branch() -> None:
    record = _section_79()
    assert "heap 3 stays empty" in record
    assert "close unstarted" in record
    assert "#131" in record and "#134" in record
    assert "#127" in record and "either branch" in record
