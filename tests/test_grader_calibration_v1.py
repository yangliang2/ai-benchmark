"""The calibrate-grader-v1 command surface: the grader measured against an
archive, with a fake grader standing in for the paid one.

Everything here drives `main([...])` and reads stdout, the repo's convention
for a command: the printed counts are what ticket 06's pre-registration will
quote and what a reader checks the gate by hand from, so asserting on the page
catches a figure that is right in `gate()` and wrong in the rendering.

**No live grader is ever reached.** The instrument is injected by monkeypatching
`point_grader.deepseek_point_grader`, exactly as the point-gate suite does, and
the fakes below rule on a marker rather than on meaning — what is under test is
the experiment around the grader: which rows land in which stratum, how many
calls each stratum costs, which verdict is compared with which, and which of the
two strata the bar is read off.

The fixture archive is deliberately tiny and its every verdict is decided by the
diff its row logged, so a stratum's agreement moves only when a test moves an
answer's prose or a row's diff.
"""

import json
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import workdir_diff

from ai_benchmark import firstparty_v1, grader_calibration_v1, point_grader
from ai_benchmark.cli import main
from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    ANSWER_MODULE,
    ANSWER_TEST_FILE,
    FINDINGS_KEY_FILE,
    FINDINGS_MODULE,
    FINDINGS_TEST_FILE,
    Run,
    Task,
    answer_module_source,
    answer_test_source,
    findings_module_source,
    findings_test_source,
    load_task_set,
)
from ai_benchmark.point_grader import Point, Ruling

AGENT = "claude-code"
MODEL = "claude-sonnet-5"
_AS_OF = date(2026, 8, 20)

# The repository every fixture task is about, in each language: one module with
# one defect in it. Trivial on purpose — these tests are about strata and
# counts, and a task with any depth of its own would only slow the replay down.
PRICING_PY = '''\
"""Total a basket."""


def total(lines):
    return sum(round(price) for price, _ in lines)
'''

PRICING_TS = """\
export function total(lines: [number, number][]): number {
  return lines.reduce((sum, [price]) => sum + Math.round(price), 0);
}
"""

# The stratum-B task's change and what solves it: one function, one answer.
PLAIN_PRISTINE = "def answer():\n    return None\n"
PLAIN_SOLVED = "def answer():\n    return 42\n"
PLAIN_GRADING = (
    "from thing import answer\n\n\ndef test_answer():\n    assert answer() == 42\n"
)


# --- fixture task trees --------------------------------------------------------


def _write_spec(task_dir: Path, fields: dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))


def write_keyed_task(
    root: Path,
    task_id: str,
    *,
    category: str = "fault-location",
    language: str = "python",
) -> None:
    """A task shipping an **accepted-answer key**: stratum A, one point.

    The grading half is Python whatever the repository's language is, because
    the deliverable is a JSON answer file and the comparison that reads it is
    `_answer.py` — which is why the checked-in TypeScript fault-location tasks
    ship a Python `test_answer.py` too, and why a TypeScript fixture here needs
    no second runner.
    """
    task_dir = root / task_id
    module = "pricing.py" if language == "python" else "pricing.ts"
    (task_dir / "repo").mkdir(parents=True, exist_ok=True)
    (task_dir / "repo" / module).write_text(
        PRICING_PY if language == "python" else PRICING_TS
    )
    _write_spec(task_dir, {
        "id": task_id,
        "category": category,
        "scale": "single-file",
        "surface": "application",
        "language": language,
        "control": True,
        "prompt": f"A basket totals low. Name where, in ANSWER.json ({task_id}).",
    })
    (task_dir / "grading").mkdir(exist_ok=True)
    (task_dir / "grading" / ANSWER_MODULE).write_bytes(answer_module_source())
    (task_dir / "grading" / ANSWER_TEST_FILE).write_bytes(answer_test_source())
    (task_dir / "grading" / ANSWER_KEY_FILE).write_text(json.dumps(
        {
            "answer_path": "ANSWER.json",
            "accepted": [{"file": module, "symbol": "total"}],
            "rejected": [{"file": module, "symbol": "lines"}],
        },
        indent=2,
    ))


# The three defects the review task plants, each at one location. Three because
# that is what the registered corpus's review tasks carry, and the ticket's
# call arithmetic (26 x 3) is read off it.
REVIEW_FINDINGS = ("gross_for", "net_for", "owed")


def write_review_task(root: Path, task_id: str) -> None:
    """A task shipping a **findings key**: stratum A, one point per planted
    finding."""
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True, exist_ok=True)
    (task_dir / "repo" / "payroll.py").write_text(
        '"""Pay a week."""\n\n\n'
        + "\n\n".join(
            f"def {name}(hours):\n    return round(hours * 12)"
            for name in REVIEW_FINDINGS
        )
        + "\n"
    )
    _write_spec(task_dir, {
        "id": task_id,
        "category": "code-review",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "prompt": f"Review the change and list what is wrong ({task_id}).",
    })
    (task_dir / "grading").mkdir(exist_ok=True)
    (task_dir / "grading" / ANSWER_MODULE).write_bytes(answer_module_source())
    (task_dir / "grading" / FINDINGS_MODULE).write_bytes(findings_module_source())
    (task_dir / "grading" / FINDINGS_TEST_FILE).write_bytes(findings_test_source())
    (task_dir / "grading" / FINDINGS_KEY_FILE).write_text(json.dumps(
        {
            "answer_path": "FINDINGS.json",
            "accepted": [
                {"any": [{"file": "payroll.py", "symbol": name}]}
                for name in REVIEW_FINDINGS
            ],
            "rejected": [{"file": "payroll.py", "symbol": "PAYROLL_RATE"}],
        },
        indent=2,
    ))


def write_plain_task(root: Path, task_id: str) -> None:
    """A task shipping no key at all: stratum B, the synthetic point."""
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True, exist_ok=True)
    (task_dir / "repo" / "thing.py").write_text(PLAIN_PRISTINE)
    _write_spec(task_dir, {
        "id": task_id,
        "category": "feature-dev",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "prompt": f"make answer() return 42 ({task_id})",
    })
    (task_dir / "grading").mkdir(exist_ok=True)
    (task_dir / "grading" / "test_answer.py").write_text(PLAIN_GRADING)


# --- the diffs a fixture run logs ----------------------------------------------


def _wrote(name: str, payload: str) -> Callable[[Path], None]:
    def edit(workdir: Path) -> None:
        (workdir / name).write_text(payload)

    return edit


def keyed_diff(task: Task, *, right: bool) -> str:
    """The answer file a keyed row logged: the accepted location, or a rejected
    one, which is what decides the machine verdict."""
    module = "pricing.py" if task.language == "python" else "pricing.ts"
    symbol = "total" if right else "lines"
    return workdir_diff(
        task, _wrote("ANSWER.json", json.dumps({"file": module, "symbol": symbol}))
    )


def review_diff(task: Task, *, reported: tuple[str, ...]) -> str:
    """The findings file a review row logged: every planted finding it named.
    Reporting fewer than all three is unresolved — the verdict's quantifier is
    universal."""
    return workdir_diff(task, _wrote("FINDINGS.json", json.dumps(
        [{"file": "payroll.py", "symbol": name} for name in reported]
    )))


def plain_diff(task: Task, *, solved: bool) -> str:
    if not solved:
        return ""
    return workdir_diff(task, _wrote("thing.py", PLAIN_SOLVED))


# --- the fixture archive -------------------------------------------------------

# What each fixture row's prose says, keyed by task id. A line naming a point's
# id is what the marker grader rules covered, so these strings are how a test
# says what the grader will make of an answer — and they are the *output*, the
# agent's final message, which is the deliverable this experiment grades.
FL_RESOLVED = "fl-python"
FL_UNRESOLVED = "fl-typescript"
CODEX_ROW = "fl-codex"
REVIEW = "cr-payroll"
PLAIN_RESOLVED = "fd-resolved"
PLAIN_UNRESOLVED = "fd-unresolved"


def covering(*point_ids: str) -> str:
    """An answer whose prose covers exactly these points under the marker rule."""
    return "I read the repository and here is what I found.\n" + "".join(
        f"- {point_id}: this is what I found, in as many words.\n"
        for point_id in point_ids
    )


ACCEPTED = grader_calibration_v1.ACCEPTED_LOCATION_POINT_ID
SYNTHETIC = grader_calibration_v1.SYNTHETIC_POINT_ID


def review_point_id(symbol: str) -> str:
    return f"reports-payroll.py:{symbol}"


def write_archive(root: Path, log: Path, outputs: Mapping[str, str] | None = None) -> None:
    """The whole fixture corpus and one run log over it.

    Six answers. Stratum A is four — two Python fault-location rows, one
    TypeScript fault-location row logged by `codex`, and one review row whose
    key plants three findings — so stratum A costs 1 + 1 + 1 + 3 = 6 calls and
    holds two machine-resolved rows and two unresolved ones. Stratum B is two
    feature-dev rows, one of each verdict, costing one call each.

    Every row's prose agrees with its machine verdict unless `outputs`
    overrides it, so the base archive is a clean instrument and each test moves
    exactly one thing away from it.
    """
    write_keyed_task(root, FL_RESOLVED)
    write_keyed_task(root, FL_UNRESOLVED, language="typescript")
    write_keyed_task(root, CODEX_ROW, category="codebase-comprehension")
    write_review_task(root, REVIEW)
    write_plain_task(root, PLAIN_RESOLVED)
    write_plain_task(root, PLAIN_UNRESOLVED)
    by_id = {task.id: task for task in load_task_set(root)}

    said = {
        FL_RESOLVED: covering(ACCEPTED),
        FL_UNRESOLVED: covering(),
        CODEX_ROW: covering(ACCEPTED),
        REVIEW: covering(*[review_point_id(name) for name in REVIEW_FINDINGS[:2]]),
        PLAIN_RESOLVED: covering(SYNTHETIC),
        PLAIN_UNRESOLVED: covering(),
    } | dict(outputs or {})

    diffs = {
        FL_RESOLVED: keyed_diff(by_id[FL_RESOLVED], right=True),
        FL_UNRESOLVED: keyed_diff(by_id[FL_UNRESOLVED], right=False),
        CODEX_ROW: keyed_diff(by_id[CODEX_ROW], right=True),
        REVIEW: review_diff(by_id[REVIEW], reported=REVIEW_FINDINGS[:2]),
        PLAIN_RESOLVED: plain_diff(by_id[PLAIN_RESOLVED], solved=True),
        PLAIN_UNRESOLVED: plain_diff(by_id[PLAIN_UNRESOLVED], solved=False),
    }

    rows = [
        Run(
            task_id=task_id,
            agent="codex" if task_id == CODEX_ROW else AGENT,
            model=MODEL,
            output=said[task_id],
            diff=diff,
            tokens_in=41000,
            tokens_out=1500,
            cost_usd=0.0 if task_id == CODEX_ROW else 0.2,
            latency_s=64.5,
            turns=7,
            as_of=_AS_OF,
            sweep="fixture-sweep",
            cost_source="table-derived" if task_id == CODEX_ROW else None,
            price_table="fixture-price-table" if task_id == CODEX_ROW else None,
        )
        for task_id, diff in diffs.items()
    ]
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(row.model_dump_json() + "\n" for row in rows))


# --- the instrument, faked -----------------------------------------------------


class MarkerGrader:
    """A stand-in point grader that rules a point covered when some line of the
    answer names the point's id, and quotes that line as its span.

    The same rule the point-gate suite's fake uses, for the same reason: an
    answer's coverage is then exactly what a test wrote into it, and nothing
    here depends on a grader's reading.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, deliverable: str, point: Point) -> Ruling:
        self.calls.append(point["id"])
        span = next(
            (line for line in deliverable.splitlines() if point["id"] in line), None
        )
        return Ruling(
            point_id=point["id"],
            covered=span is not None,
            span=span,
            grader_version=point_grader.GRADER_VERSION,
        )


class AlwaysCovered:
    """The grader §76.4 exists to refuse: it rules every point covered, and
    quotes a span it really can find, so the gate's own span check cannot demote
    it. It collects the resolved class free and has to fail anyway."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, deliverable: str, point: Point) -> Ruling:
        self.calls.append(point["id"])
        return Ruling(
            point_id=point["id"],
            covered=True,
            span=deliverable.splitlines()[0],
            grader_version=point_grader.GRADER_VERSION,
        )


def install(
    monkeypatch: pytest.MonkeyPatch, grader: Callable[[str, Point], Ruling]
) -> None:
    monkeypatch.setattr(point_grader, "deepseek_point_grader", lambda: grader)


def refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """No grader may be built at all — what `--split-only` is held to."""

    def never_built() -> Callable[[str, Point], Ruling]:
        raise AssertionError("a grader was built when none should have been")

    monkeypatch.setattr(point_grader, "deepseek_point_grader", never_built)


def calibrate(
    tasks: Path,
    log: Path,
    rulings: Path,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> str:
    main([
        "calibrate-grader-v1",
        "--tasks", str(tasks),
        "--runs", str(log),
        "--rulings", str(rulings),
        *extra,
    ])
    return capsys.readouterr().out


@pytest.fixture
def archive(tmp_path: Path) -> tuple[Path, Path, Path]:
    tasks, log = tmp_path / "tasks", tmp_path / "runs" / "fixture.jsonl"
    write_archive(tasks, log)
    return tasks, log, tmp_path / "rulings"


# --- the split, and what it costs ----------------------------------------------


def test_split_only_stratifies_by_key_shape_and_makes_no_grader_call(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--split-only` prints the strata, the replay-computed split, the calls a
    run would make and the bar in counts — and builds no grader to do it."""
    tasks, log, rulings = archive
    refuse(monkeypatch)

    page = calibrate(tasks, log, rulings, capsys, "--split-only")

    assert "A        4        6" in page
    assert "B        2        2" in page
    assert "grader calls: 6 on stratum A + 2 on stratum B = 8 in all" in page
    assert not rulings.exists()


def test_split_only_prints_the_resolved_split_and_the_bar_in_counts(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The resolved/unresolved split inside stratum A is what the second clause
    of the bar is read over, and both clauses print as counts a reader can check
    by hand."""
    tasks, log, rulings = archive
    refuse(monkeypatch)

    page = calibrate(tasks, log, rulings, capsys, "--split-only")

    assert "code-review             1        3       0         1" in page
    assert "codebase-comprehension  1        1       1         0" in page
    assert "fault-location          2        2       1         1" in page
    assert "(all)                   4        6       2         2" in page
    assert "overall agreement           >= 4 of 4" in page
    assert "unresolved-class agreement  >= 2 of 2" in page


def test_the_bar_is_the_registered_counts(
    archive: tuple[Path, Path, Path],
) -> None:
    """§76.4's percentages, turned into the counts the round registered them as.

    Pinned against the anchor the ticket re-derived on the corpus at `cf71344`
    — 63 stratum-A answers, 8 of them unresolved — so that a rounding change
    that moved the bar by one answer would fail here rather than in a paid run.
    """
    assert grader_calibration_v1.registered_count(90, 63) == 57
    assert grader_calibration_v1.registered_count(80, 8) == 7
    # An exact percentage takes no extra answer with it.
    assert grader_calibration_v1.registered_count(90, 10) == 9
    assert grader_calibration_v1.registered_count(80, 5) == 4


def test_a_typescript_row_and_a_codex_row_stay_in_stratum_a(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The filter regression this reader exists not to inherit.

    `reconcile-v1`'s defaults would drop the TypeScript row on `--language` and
    the `codex` row on `--agent`, shrinking stratum A by half in this fixture
    and by a quarter on the registered corpus. Neither filter is here, so both
    rows are graded.
    """
    tasks, log, rulings = archive
    grader = MarkerGrader()
    install(monkeypatch, grader)

    page = calibrate(tasks, log, rulings, capsys)

    assert "A        4        6" in page
    archived = grader_calibration_v1.read_rulings(
        grader_calibration_v1.rulings_file(rulings, point_grader.GRADER_VERSION)
    )
    assert archived is not None
    graded = {(one.task_id, one.agent) for one in archived.answers}
    assert (FL_UNRESOLVED, AGENT) in graded  # the TypeScript task's row
    assert (CODEX_ROW, "codex") in graded


# --- what the grader made of the archive ---------------------------------------


def test_a_fixture_archive_with_known_agreement_prints_the_counts(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every fixture answer's prose agrees with its machine verdict, so both
    strata agree in full and the gate is met on stratum A's counts."""
    tasks, log, rulings = archive
    grader = MarkerGrader()
    install(monkeypatch, grader)

    page = calibrate(tasks, log, rulings, capsys)

    assert len(grader.calls) == 8
    assert "grader calls made: 8" in page
    assert "stratum A, overall           4 of 4" in page
    assert "stratum A, unresolved class  2 of 2" in page
    assert "stratum B, overall           2 of 2" in page
    assert "gate (stratum A alone): MET" in page


def test_the_always_covered_grader_fails_the_unresolved_class_clause(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """§76.4's load-bearing clause. A grader that rules everything covered
    collects the whole resolved class for free — and is refused anyway, because
    the class where discrimination lives has its own floor."""
    tasks, log, rulings = archive
    install(monkeypatch, AlwaysCovered())

    page = calibrate(tasks, log, rulings, capsys)

    assert "stratum A, overall           2 of 4" in page
    assert "stratum A, unresolved class  0 of 2" in page
    assert "gate (stratum A alone): FAILED" in page
    assert "unresolved-class agreement  0 of 2  >= 2 of 2  not met" in page


def test_the_resolved_class_is_where_the_always_covered_grader_looks_right(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half of the same claim, read off the API because the page does
    not print the resolved class: the always-covered grader agrees with every
    resolved row in stratum A, which is exactly why an overall figure alone
    would be gameable by base rate."""
    tasks, log, rulings = archive
    tasks_loaded = load_task_set(tasks)
    runs = firstparty_v1.load_runs(log)
    answers = grader_calibration_v1.split(tasks_loaded, runs)
    judged, _, _ = grader_calibration_v1.judge(
        answers, AlwaysCovered, rulings_dir=rulings
    )

    stratum_a = [one for one in judged if one.answer.stratum == "A"]
    resolved = [one for one in stratum_a if one.answer.machine_resolved]
    assert resolved and all(one.agrees for one in resolved)
    assert not any(one.agrees for one in stratum_a if not one.answer.machine_resolved)


def test_stratum_b_is_printed_with_its_confound_and_gates_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Moving stratum B's agreement moves the printed stratum-B figure and
    nothing else: §76.3's ruling that the confounded stratum reports and does
    not gate."""
    tasks, log = tmp_path / "tasks", tmp_path / "runs" / "fixture.jsonl"
    # The resolved feature-dev row now narrates a failure it did not have: the
    # confound itself, an agent's message disagreeing with its own diff.
    write_archive(tasks, log, outputs={PLAIN_RESOLVED: covering()})
    install(monkeypatch, MarkerGrader())

    page = calibrate(tasks, log, tmp_path / "rulings", capsys)

    assert "stratum B, overall           1 of 2" in page
    assert "stratum A, overall           4 of 4" in page
    assert "gate (stratum A alone): MET" in page
    assert grader_calibration_v1.CONFOUND in page


# --- the rulings archive -------------------------------------------------------


def test_the_rulings_carry_the_grader_version_and_never_reach_the_dataset(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Calibration rulings are instrument data: they land under the rulings
    directory, in a file named for the instrument that produced them, and
    nothing is merged into the unified dataset."""
    tasks, log, rulings = archive
    install(monkeypatch, MarkerGrader())
    dataset = Path("data/unified.jsonl")
    before = dataset.read_bytes() if dataset.exists() else None

    calibrate(tasks, log, rulings, capsys)

    path = rulings / f"{point_grader.GRADER_VERSION}.json"
    archived = json.loads(path.read_text())
    assert archived["grader_version"] == point_grader.GRADER_VERSION
    assert len(archived["answers"]) == 6
    assert sum(len(one["rulings"]) for one in archived["answers"]) == 8
    assert {one["stratum"] for one in archived["answers"]} == {"A", "B"}
    assert (dataset.read_bytes() if dataset.exists() else None) == before


def test_an_archived_ruling_is_reused_rather_than_paid_for_twice(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A second reading of the same archive under the same instrument makes no
    call: a second grading would be a second measurement of something already
    measured, and it is what makes an interrupted paid run resumable."""
    tasks, log, rulings = archive
    install(monkeypatch, MarkerGrader())
    first = calibrate(tasks, log, rulings, capsys)

    refuse(monkeypatch)
    second = calibrate(tasks, log, rulings, capsys)

    assert "grader calls made: 8" in first
    assert "grader calls made: 0" in second
    assert "6 answer(s) reused rulings already archived under this version" in second
    assert "gate (stratum A alone): MET" in second


def test_rulings_taken_against_another_answer_are_not_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The archive is keyed to the very prose it was taken against. Edit the
    answer and its rulings are rulings about a different measurement, so the row
    is graded afresh rather than scored off them."""
    tasks, log = tmp_path / "tasks", tmp_path / "runs" / "fixture.jsonl"
    rulings = tmp_path / "rulings"
    write_archive(tasks, log)
    install(monkeypatch, MarkerGrader())
    calibrate(tasks, log, rulings, capsys)

    write_archive(tasks, log, outputs={PLAIN_RESOLVED: covering(SYNTHETIC, "extra")})
    grader = MarkerGrader()
    install(monkeypatch, grader)
    page = calibrate(tasks, log, rulings, capsys)

    assert grader.calls == [SYNTHETIC]
    assert "grader calls made: 1" in page


def test_a_broken_rulings_archive_fails_loudly(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An archive that is there but unreadable is a broken artefact rather than
    a missing one: re-grading over it would spend the experiment's dollars again
    and overwrite the very file whose breakage wants looking at."""
    tasks, log, rulings = archive
    rulings.mkdir(parents=True)
    (rulings / f"{point_grader.GRADER_VERSION}.json").write_text("{not json")
    install(monkeypatch, MarkerGrader())

    with pytest.raises(SystemExit, match="are not JSON"):
        calibrate(tasks, log, rulings, capsys)


# --- what the reader refuses ---------------------------------------------------


def test_a_row_naming_a_task_the_set_does_not_hold_is_refused(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The calibration reads the whole archive, so a row it cannot stratify is a
    broken log rather than a row to drop quietly."""
    tasks, log, rulings = archive
    rows = log.read_text().splitlines()
    stray = json.loads(rows[0])
    stray["task_id"] = "a-task-nobody-authored"
    log.write_text("\n".join([*rows, json.dumps(stray)]) + "\n")
    refuse(monkeypatch)

    with pytest.raises(SystemExit, match="the task set does not hold"):
        calibrate(tasks, log, rulings, capsys, "--split-only")


def test_an_empty_unresolved_class_makes_the_clause_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stratum with nothing to discriminate on cannot say the instrument
    discriminates. The clause reads unreadable rather than vacuously true, and
    the gate does not certify the very grader §76.4 refuses outright.
    """
    tasks, log = tmp_path / "tasks", tmp_path / "runs" / "fixture.jsonl"
    write_keyed_task(tasks, FL_RESOLVED)
    [task] = load_task_set(tasks)
    row = Run(
        task_id=FL_RESOLVED,
        agent=AGENT,
        model=MODEL,
        output=covering(ACCEPTED),
        diff=keyed_diff(task, right=True),
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.1,
        latency_s=1.0,
        turns=1,
        as_of=_AS_OF,
    )
    log.parent.mkdir(parents=True)
    log.write_text(row.model_dump_json() + "\n")
    install(monkeypatch, MarkerGrader())

    page = calibrate(tasks, log, tmp_path / "rulings", capsys)

    assert "gate (stratum A alone): FAILED" in page
    assert "unreadable: the class is empty" in page


def test_the_deliverable_is_the_agents_final_message_and_not_its_diff(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """What the grader is shown, pinned: the row's `output`. The diff is the
    held-out half — it is what the machine verdict is replayed from — and a
    grader that saw it would be scoring itself."""
    tasks, log, rulings = archive
    seen: list[str] = []

    def watch(deliverable: str, point: Point) -> Ruling:
        seen.append(deliverable)
        return Ruling(
            point_id=point["id"],
            covered=False,
            span=None,
            grader_version=point_grader.GRADER_VERSION,
        )

    install(monkeypatch, watch)
    calibrate(tasks, log, rulings, capsys)

    outputs = {row.output for row in firstparty_v1.load_runs(log)}
    assert set(seen) == outputs
    assert not any("diff --git" in deliverable for deliverable in seen)


def test_the_page_names_the_task_set_the_instrument_and_the_blind_read(
    archive: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The header a reader checks the run's provenance from."""
    tasks, log, rulings = archive
    refuse(monkeypatch)

    page = calibrate(tasks, log, rulings, capsys, "--split-only")

    assert str(tasks) in page
    assert point_grader.GRADER_VERSION in page
    assert "every agent and every language; 6 answer(s)" in page


def test_the_points_a_key_shape_asks_are_derived_from_the_key(
    tmp_path: Path,
) -> None:
    """The strata are derived from each row's task and its key shape, never
    from a hand-kept list: a findings key expands to one point per planted
    finding, an accepted-answer key asks one, and everything else asks the
    synthetic point."""
    review_root, keyed_root, plain_root = (
        tmp_path / "review", tmp_path / "keyed", tmp_path / "plain"
    )
    write_review_task(review_root, REVIEW)
    write_keyed_task(keyed_root, FL_RESOLVED, category="codebase-comprehension")
    write_plain_task(plain_root, PLAIN_RESOLVED)
    [review] = load_task_set(review_root)
    [keyed] = load_task_set(keyed_root)
    [plain] = load_task_set(plain_root)

    assert [point["id"] for point in grader_calibration_v1.points_for(review)] == [
        review_point_id(name) for name in REVIEW_FINDINGS
    ]
    assert [point["id"] for point in grader_calibration_v1.points_for(keyed)] == [
        ACCEPTED
    ]
    assert [point["id"] for point in grader_calibration_v1.points_for(plain)] == [
        SYNTHETIC
    ]
    # The findings key's own quantifier travels into the point's text: a finding
    # is matched at any of its alternatives, so the point names them all.
    assert "payroll.py:gross_for" in grader_calibration_v1.points_for(review)[0]["text"]
