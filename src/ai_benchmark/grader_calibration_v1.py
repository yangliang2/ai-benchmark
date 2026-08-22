"""calibrate-grader-v1: the point grader measured against the archive, offline
split and all.

The round-9 calibration experiment (§76.2–§76.4). The instrument
(`ai_benchmark.point_grader`) is about to become the thing a whole action's
verdict is computed from, and this is the experiment that says whether it may:
the grader reads an archived free-text answer **blind to the verdict**, rules
one point at a time, and the held-out machine verdict — recomputed here by
replaying the same run's diff against the same task's held-out grading tests —
scores it.

**Not `calibrate-v1`.** That reader is the difficulty/cost table over the same
corpus and answers a different question entirely. This one grades no cell,
publishes no rate, and merges no record.

**Two strata, and only one of them gates.** The archive is not one corpus.

- **Stratum A** — the rows whose task ships a key the grader can be run
  against in exactly its production mode: an **accepted-answer key**
  (`fault-location` and locate-style `codebase-comprehension`), which asks one
  point — did the answer name an accepted location — and a **findings key**
  (`code-review`), which asks **one point per planted finding**. For the
  single-point categories, per-answer agreement is per-point agreement.
- **Stratum B** — every other row, graded against the one synthetic point
  available to it, "the asked-for work was done". Its deliverable was a diff
  and the prose merely narrates it, so a disagreement there measures the
  agent's narrative truthfulness as much as the grader's skill — an agent that
  sincerely believed it succeeded writes a resolved-sounding message on an
  unresolved run. §76.3 rules that confound out of the gate rather than
  averaging it in: stratum B runs anyway, both numbers are printed, and the
  verdict is read off stratum A alone.

Which stratum a row is in is derived from the task it names and the key shape
that task ships — never from a hand-kept list of ids, for `is_keyed`'s reason:
a list leaves the next keyed task inheriting none of this.

**The archive is read blind in a second sense: no agent filter and no language
filter.** `reconcile-v1` and `calibrate-v1` reach the corpus through
`observed_outcomes`, which selects one agent and one language before anything
is graded — right for a table whose denominators would otherwise pool two
toolchains, and wrong here, where the population *is* the archive. On the
corpus this was registered against, 15 of the 63 stratum-A answers are
TypeScript rows and 17 are `codex` rows, so inheriting either default would
have silently shrunk the very stratum the gate is read off. So this module
loads every log row and every task and filters neither.

**The split is computed offline, before the grader is built.** A row's machine
verdict comes from `firstparty_v1.grade()` over its logged diff — no network,
no grader, nothing the grader will later see. That is what makes
`--split-only` honest: it prints the strata, the resolved/unresolved split
inside stratum A, the calls the run will make and the bar in counts, having
peeked at nothing.

**What it writes.** One rulings archive per instrument version, under
`data/point-gate-calibration/<grader-version>.json`, holding the grader's own
words and what the gate made of each span. **Never merged into the unified
dataset**: a calibration ruling is instrument data, not a combination's result
on an instance, and a record is the latter by definition (ADR-0001). The
archive is rewritten after every answer and read back on the next run, so a
run interrupted after two hundred paid calls resumes rather than repeating
them — the project's own discipline that a second grading is a second
measurement of something already measured.

**Running it for real needs `DEEPSEEK_API_KEY` exported in the invoking
shell.** The grader is a live client; the committed classification cache that
masks a missing key for `classify` masks nothing here.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from ai_benchmark import point_grader
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Answer,
    Run,
    Task,
    answer_key,
    carries_a_key,
    findings_key,
    grade,
    is_findings_keyed,
    load_runs,
)
from ai_benchmark.point_grader import Point, PointGrader
from ai_benchmark.reconcile_v1 import padded_table
from ai_benchmark.schema import NonEmptyStr

# Where the rulings land: under the data directory, one file per instrument
# version, and nowhere near `data/unified.jsonl`.
DEFAULT_RULINGS_DIR = Path("data/point-gate-calibration")

Stratum = Literal["A", "B"]

# §76.4's bar, as percentages of the stratum they are read over. Held as whole
# numbers and turned into counts by integer arithmetic (`registered_count`),
# because the bar is registered as counts a reader can check by hand and a
# float rounding the wrong way at 56.7 would move the bar by one answer.
OVERALL_BAR_PERCENT = 90
UNRESOLVED_BAR_PERCENT = 80

# The one point available to a stratum-B answer, and the whole reason that
# stratum is confounded: it asks the prose whether the work was done, which an
# agent can sincerely get wrong about its own run.
SYNTHETIC_POINT_ID = "the-asked-for-work-was-done"

# The point an accepted-answer key asks. One point, whatever the key's accepted
# set holds — the key is read under "any of these locations", so an answer
# naming one of them covers it (`AnswerKey`).
ACCEPTED_LOCATION_POINT_ID = "the-answer-names-an-accepted-location"

CONFOUND = (
    "stratum B is confounded and gates nothing: its deliverable was a diff "
    "and the prose merely narrates it, so a disagreement there measures the "
    "agent's narrative truthfulness as much as the grader's skill."
)


# --- what the grader is asked, per key shape -----------------------------------


def _location(answer: Answer) -> str:
    """One (file, symbol) pair as a point's text spells it."""
    return f"{answer.file}:{answer.symbol}"


def _alternatives(answers: Sequence[Answer]) -> str:
    return ", ".join(_location(answer) for answer in answers)


def points_for(task: Task) -> tuple[Point, ...]:
    """Every point this task's archived answers are graded against, derived from
    the key shape the task ships and never from its category.

    Three shapes, two of them stratum A's:

    - a **findings key** asks one point per planted finding, each written under
      the key's own quantifier — a finding is matched at *any* of its
      alternative locations (`PlantedFinding`), so the point names them all and
      is covered by prose reporting the defect at any one;
    - an **accepted-answer key** asks the single point that key exists to
      settle, naming every location the author accepts;
    - everything else asks the synthetic point, which is stratum B.

    The ids are stable across runs and readable in the archive, because the
    archive is keyed by them: a ruling whose id nothing can be matched back to
    answers for a point nobody asked about.
    """
    if is_findings_keyed(task):
        key = findings_key(task)
        return tuple(
            {
                "id": f"reports-{_location(finding.primary)}",
                "text": (
                    "The answer reports a defect at one of these locations: "
                    f"{_alternatives(finding.any)}."
                ),
            }
            for finding in key.accepted
        )
    if carries_a_key(task):
        key_locations = _alternatives(answer_key(task).accepted)
        return (
            {
                "id": ACCEPTED_LOCATION_POINT_ID,
                "text": (
                    "The answer names the location it was asked for as one of "
                    f"these: {key_locations}."
                ),
            },
        )
    return (
        {
            "id": SYNTHETIC_POINT_ID,
            "text": "The answer states that the work it was asked to do was done.",
        },
    )


# --- the split, computed offline by replay -------------------------------------


@dataclass(frozen=True)
class ArchivedAnswer:
    """One row of the experiment: an archived free-text answer, the stratum it
    falls in, the points it will be graded against, and the held-out verdict
    that scores the grading.

    `deliverable` is the run's `output` — the agent's final message, which is
    what the archive holds. The run's *diff* is what `machine_resolved` was
    replayed from, and the grader never sees it: that separation is the whole
    experiment.
    """

    run: Run
    task: Task
    stratum: Stratum
    points: tuple[Point, ...]
    machine_resolved: bool

    @property
    def deliverable(self) -> str:
        return self.run.output

    @property
    def cell(self) -> tuple[str, str, str]:
        """The triple that identifies this answer in the rulings archive."""
        return (self.run.task_id, self.run.agent, self.run.model)


def split(
    tasks: Sequence[Task], runs: Sequence[Run], *, timeout_s: int = GRADE_TIMEOUT_S
) -> list[ArchivedAnswer]:
    """Every archived answer, stratified and scored by replay — no grader, no
    network, no key peeked at that the grader will later be shown.

    Two failures are refused here rather than worked around, both of them
    `evaluate`'s refusals for `evaluate`'s reasons: a row naming a task that is
    not in the set is a broken log rather than a row to drop, and two rows of
    one task x agent x model cell are two measurements of something the archive
    holds one slot for.
    """
    by_id = {task.id: task for task in tasks}
    seen: dict[tuple[str, str, str], Run] = {}
    answers: list[ArchivedAnswer] = []
    for run in runs:
        task = by_id.get(run.task_id)
        if task is None:
            raise IngestError(
                f"{run.task_id}: a run log names a task the task set does not "
                "hold — the calibration reads the whole archive, so a row it "
                "cannot stratify is a broken log rather than a row to drop"
            )
        cell = (run.task_id, run.agent, run.model)
        if cell in seen:
            raise IngestError(
                f"{run.task_id}: two runs of {run.agent} x {run.model} — one "
                "cell is one archived answer, and a second would have to be "
                "silently picked between when its rulings were archived"
            )
        seen[cell] = run
        answers.append(
            ArchivedAnswer(
                run=run,
                task=task,
                stratum="A" if carries_a_key(task) else "B",
                points=points_for(task),
                machine_resolved=grade(task, run.diff, timeout_s=timeout_s),
            )
        )
    return answers


# --- the rulings archive -------------------------------------------------------


class CalibrationRuling(BaseModel):
    """One archived ruling: what the grader said about one point of one answer,
    and what this reader made of the span it quoted.

    `PointRuling`'s shape minus its `kind`, because a calibration point is never
    a disqualifier: the synthetic point and both key shapes ask "is this
    covered?" and nothing here asks the opposite. `verified` is archived beside
    the grader's own words rather than folded into them for `PointRuling`'s
    reason — a covered ruling quoting a span the answer does not contain is a
    fact about the instrument worth reading back off the archive — and nothing
    downstream trusts it: every agreement figure re-verifies the span.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    point_id: NonEmptyStr
    covered: bool
    span: str | None
    verified: bool


class AnswerRulings(BaseModel):
    """Every ruling taken on one archived answer.

    The deliverable's hash is what makes a resumed run honest: rulings taken
    against some other answer are refused rather than recounted over this one.
    No verdict is stored — neither the grader's nor the machine's — because both
    are recomputations, the machine's from a replay that is free and the
    grader's from these rulings, and a stored verdict is a number a later
    reading could disagree with while still printing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: NonEmptyStr
    agent: NonEmptyStr
    model: NonEmptyStr
    stratum: Stratum
    deliverable_sha256: NonEmptyStr
    rulings: tuple[CalibrationRuling, ...]


class CalibrationRulings(BaseModel):
    """One instrument version's calibration archive.

    Instrument data, and deliberately not a `Record`: it says what a grader
    said about an archived answer, not how a combination did on an instance, so
    it lives under its own path and is never merged into `data/unified.jsonl`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    grader_version: NonEmptyStr
    answers: tuple[AnswerRulings, ...]


def rulings_file(rulings_dir: Path, grader_version: str) -> Path:
    """Where one instrument version's calibration rulings live.

    Keyed by version and nothing else: re-versioning the grader is a new
    experiment against the same archive, and it gets its own file rather than
    overwriting the evidence the previous version's gate was read off.
    """
    return rulings_dir / f"{grader_version}.json"


def _sha256(deliverable: str) -> str:
    return hashlib.sha256(deliverable.encode("utf-8")).hexdigest()


def read_rulings(path: Path) -> CalibrationRulings | None:
    """The archive at this path, or None where there is none.

    An archive that is there but unreadable, not JSON or not this shape is a
    broken artefact rather than a missing one and fails loudly: quietly
    re-grading over it would spend the whole experiment's dollars again and
    overwrite the very file whose breakage wants looking at.
    """
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise IngestError(
            f"the archived calibration rulings at {path} are unreadable ({error})"
        ) from error
    except json.JSONDecodeError as error:
        raise IngestError(
            f"the archived calibration rulings at {path} are not JSON ({error})"
        ) from error
    try:
        return CalibrationRulings.model_validate(raw)
    except ValidationError as error:
        raise IngestError(
            f"the archived calibration rulings at {path}: {error}"
        ) from error


def write_rulings(path: Path, archive: CalibrationRulings) -> None:
    """Archive what the grader has said so far.

    Called after every answer rather than once at the end, so that an
    interrupted run resumes from what it paid for instead of paying again.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(archive.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise IngestError(
            f"cannot write the calibration rulings at {path}: {error}"
        ) from error


def _reusable(
    archived: AnswerRulings | None, answer: ArchivedAnswer
) -> AnswerRulings | None:
    """These rulings, if they were taken against this very answer and answer
    exactly the points it asks; None otherwise.

    `_archived_rulings`' test, narrowed to what this archive keys on. Anything
    short of both is not a stale detail to work around — it is rulings about a
    different measurement — so the answer is graded afresh.
    """
    if archived is None:
        return None
    if archived.deliverable_sha256 != _sha256(answer.deliverable):
        return None
    asked = {point["id"] for point in answer.points}
    if asked != {ruling.point_id for ruling in archived.rulings}:
        return None
    return archived


# --- grading the archive -------------------------------------------------------


@dataclass(frozen=True)
class Judged:
    """One answer, its two verdicts, and whether they agree."""

    answer: ArchivedAnswer
    rulings: AnswerRulings

    @property
    def grader_resolved(self) -> bool:
        """Every point covered by a ruling whose span this answer really
        contains — the point gate's own quantifier and its own span check
        (§76.5, §76.6), recomputed here rather than read off `verified`.
        """
        by_id = {ruling.point_id: ruling for ruling in self.rulings.rulings}
        return all(
            _the_span_holds(by_id[point["id"]], self.answer.deliverable)
            for point in self.answer.points
        )

    @property
    def agrees(self) -> bool:
        return self.grader_resolved == self.answer.machine_resolved


def _the_span_holds(ruling: CalibrationRuling, deliverable: str) -> bool:
    """§76.6: no quotable span, no coverage. The demotion is mechanical, here
    rather than in the instrument, so that nothing grades its own quotations."""
    return (
        ruling.covered
        and ruling.span is not None
        and point_grader.span_in_deliverable(ruling.span, deliverable)
    )


def judge(
    answers: Sequence[ArchivedAnswer],
    grader_factory: Callable[[], PointGrader],
    *,
    rulings_dir: Path = DEFAULT_RULINGS_DIR,
) -> tuple[list[Judged], int, int]:
    """Grade every archived answer, one call per point, archiving as it goes.

    Returns the judged answers, the calls made and the rulings reused from the
    archive. The factory is called on the first answer that needs a fresh
    ruling and never otherwise, so a fully archived re-run stays free and
    keyless.

    An answer whose prose is empty or whitespace-only is unresolved with no
    call and nothing archived, the point gate's own rule: there is no prose to
    quote a span out of, so no point could be covered by one.
    """
    path = rulings_file(rulings_dir, point_grader.GRADER_VERSION)
    existing = read_rulings(path)
    if existing is not None and existing.grader_version != point_grader.GRADER_VERSION:
        raise IngestError(
            f"{path} archives rulings taken under "
            f"{existing.grader_version!r} while this build's instrument is "
            f"{point_grader.GRADER_VERSION!r} — one file is one instrument's "
            "measurement of the archive, and a re-versioned grader gets its own"
        )
    archived = {
        (one.task_id, one.agent, one.model): one
        for one in (existing.answers if existing else ())
    }

    grader: PointGrader | None = None
    judged: list[Judged] = []
    taken: list[AnswerRulings] = []
    calls = 0
    reused = 0
    for answer in answers:
        rulings = _reusable(archived.get(answer.cell), answer)
        if rulings is not None:
            reused += 1
        else:
            if grader is None:
                grader = grader_factory()
            rulings = _grade_one(answer, grader)
            calls += len(rulings.rulings)
            taken.append(rulings)
            write_rulings(
                path, CalibrationRulings(
                    grader_version=point_grader.GRADER_VERSION,
                    answers=tuple(list(archived.values()) + taken),
                ),
            )
        judged.append(Judged(answer=answer, rulings=rulings))
    return judged, calls, reused


def _grade_one(answer: ArchivedAnswer, grader: PointGrader) -> AnswerRulings:
    """One call per point of one answer, in key order, with what the gate made
    of each span.

    A grader answering about a question other than the one it was asked is
    refused rather than archived under the id it was meant to answer, and a row
    graded under an instrument version other than this build's is refused for
    the reason the archive is keyed by version: the file would then hold two
    instruments' measurements under one name.
    """
    deliverable = answer.deliverable
    rulings: list[CalibrationRuling] = []
    for point in answer.points:
        if not deliverable.strip():
            rulings.append(
                CalibrationRuling(
                    point_id=point["id"], covered=False, span=None, verified=False
                )
            )
            continue
        ruling = grader(deliverable, point)
        if ruling.point_id != point["id"]:
            raise IngestError(
                f"{answer.run.task_id}: the grader was asked about "
                f"{point['id']!r} and ruled on {ruling.point_id!r} — a ruling "
                "archived under the wrong question answers for a point nobody "
                "asked about"
            )
        if ruling.grader_version != point_grader.GRADER_VERSION:
            raise IngestError(
                f"{answer.run.task_id}: the grader ruled under "
                f"{ruling.grader_version!r} while this build's instrument is "
                f"{point_grader.GRADER_VERSION!r} — the calibration archive is "
                "keyed by version, so a ruling from another one belongs in "
                "another file"
            )
        rulings.append(
            CalibrationRuling(
                point_id=point["id"],
                covered=ruling.covered,
                span=ruling.span,
                verified=(
                    ruling.covered
                    and ruling.span is not None
                    and point_grader.span_in_deliverable(ruling.span, deliverable)
                ),
            )
        )
    return AnswerRulings(
        task_id=answer.run.task_id,
        agent=answer.run.agent,
        model=answer.run.model,
        stratum=answer.stratum,
        deliverable_sha256=_sha256(deliverable),
        rulings=tuple(rulings),
    )


# --- the bar ------------------------------------------------------------------


def registered_count(percent: int, n: int) -> int:
    """The smallest count that clears `percent` of `n`, in integers.

    §76.4 registers the bar as counts a reader can check by hand — "≥57 of 63"
    — so the percentage is turned into a count once, here, and every later
    comparison is between two integers.
    """
    return -(-percent * n // 100)


@dataclass(frozen=True)
class Clause:
    """One clause of the gate: what agreed, out of what, against what was
    registered."""

    label: str
    agreed: int
    n: int
    bar: int
    readable: bool = True

    @property
    def met(self) -> bool:
        return self.readable and self.agreed >= self.bar


@dataclass(frozen=True)
class Gate:
    """§76.4's bar, read off stratum A alone."""

    overall: Clause
    unresolved: Clause

    @property
    def met(self) -> bool:
        return self.overall.met and self.unresolved.met

    @property
    def clauses(self) -> tuple[Clause, Clause]:
        return (self.overall, self.unresolved)


def gate(judged: Sequence[Judged]) -> Gate:
    """The gate, over stratum A's judged answers and nothing else.

    Two clauses, and the second is the load-bearing one: a grader that always
    says "covered" collects the resolved class free, so the unresolved class —
    where discrimination actually lives — gets its own floor.

    An empty unresolved class makes that clause unreadable rather than
    vacuously true. A stratum with nothing to discriminate on cannot say the
    instrument discriminates, and a gate that read MET off it would be
    certifying exactly the grader §76.4 refuses outright.
    """
    stratum_a = [one for one in judged if one.answer.stratum == "A"]
    unresolved = [one for one in stratum_a if not one.answer.machine_resolved]
    return Gate(
        overall=Clause(
            label="overall agreement",
            agreed=sum(1 for one in stratum_a if one.agrees),
            n=len(stratum_a),
            bar=registered_count(OVERALL_BAR_PERCENT, len(stratum_a)),
        ),
        unresolved=Clause(
            label="unresolved-class agreement",
            agreed=sum(1 for one in unresolved if one.agrees),
            n=len(unresolved),
            bar=registered_count(UNRESOLVED_BAR_PERCENT, len(unresolved)),
            readable=bool(unresolved),
        ),
    )


# --- the page -----------------------------------------------------------------


def _header(
    answers: Sequence[ArchivedAnswer], tasks_root: Path, logs: Sequence[Path]
) -> list[str]:
    return [
        "grader calibration: the point grader read against the v1 archive",
        *padded_table(
            [
                ["  task set:", str(tasks_root)],
                ["  run log(s):", f"{len(logs)} log(s)"],
                ["  instrument:", point_grader.GRADER_VERSION],
                ["  deliverable:", "each row's output — the agent's final message"],
                [
                    "  read blind:",
                    f"every agent and every language; {len(answers)} answer(s)",
                ],
            ],
            indent="",
        ),
    ]


def _strata_table(answers: Sequence[ArchivedAnswer]) -> list[str]:
    rows = [["stratum", "answers", "points", "what the grader is asked"]]
    for stratum, asked in (
        ("A", "the task's planted key, run in production mode"),
        ("B", 'the synthetic point "the asked-for work was done"'),
    ):
        selected = [one for one in answers if one.stratum == stratum]
        rows.append([
            stratum,
            str(len(selected)),
            str(sum(len(one.points) for one in selected)),
            asked,
        ])
    return padded_table(rows, indent="  ")


def _stratum_a_table(answers: Sequence[ArchivedAnswer]) -> list[str]:
    """Stratum A broken out by the action each answer came from, with the
    replay-computed split the second clause of the bar is read over."""
    stratum_a = [one for one in answers if one.stratum == "A"]
    counted: Counter[str] = Counter(one.task.category for one in stratum_a)
    rows = [["category", "answers", "points", "resolved", "unresolved"]]
    for category in sorted(counted):
        selected = [one for one in stratum_a if one.task.category == category]
        rows.append([
            category,
            str(len(selected)),
            str(sum(len(one.points) for one in selected)),
            str(sum(1 for one in selected if one.machine_resolved)),
            str(sum(1 for one in selected if not one.machine_resolved)),
        ])
    rows.append([
        "(all)",
        str(len(stratum_a)),
        str(sum(len(one.points) for one in stratum_a)),
        str(sum(1 for one in stratum_a if one.machine_resolved)),
        str(sum(1 for one in stratum_a if not one.machine_resolved)),
    ])
    return padded_table(rows, indent="  ")


def _calls_line(answers: Sequence[ArchivedAnswer]) -> str:
    per_stratum = {
        stratum: sum(len(one.points) for one in answers if one.stratum == stratum)
        for stratum in ("A", "B")
    }
    return (
        f"grader calls: {per_stratum['A']} on stratum A + {per_stratum['B']} on "
        f"stratum B = {sum(per_stratum.values())} in all"
    )


def _bar_lines(answers: Sequence[ArchivedAnswer]) -> list[str]:
    """The bar in counts, registered before the first call — which is why it is
    computed from the replay-derived split alone and printed by `--split-only`
    as well as by a full run."""
    stratum_a = [one for one in answers if one.stratum == "A"]
    unresolved = [one for one in stratum_a if not one.machine_resolved]
    clauses = (
        Clause(
            label="overall agreement",
            agreed=0,
            n=len(stratum_a),
            bar=registered_count(OVERALL_BAR_PERCENT, len(stratum_a)),
        ),
        Clause(
            label="unresolved-class agreement",
            agreed=0,
            n=len(unresolved),
            bar=registered_count(UNRESOLVED_BAR_PERCENT, len(unresolved)),
            readable=bool(unresolved),
        ),
    )
    rows = [
        [
            clause.label,
            f">= {clause.bar} of {clause.n}",
            "" if clause.readable else "(unreadable: the class is empty)",
        ]
        for clause in clauses
    ]
    return [
        "the bar (§76.4), registered as counts over stratum A alone",
        *padded_table(rows, indent="  "),
    ]


def render_split(
    answers: Sequence[ArchivedAnswer], *, tasks_root: Path, logs: Sequence[Path]
) -> str:
    """What `--split-only` prints: everything derivable without a grader call.

    Everything on this page comes from the run logs, the task set and a replay
    of each logged diff, so printing it costs nothing and reveals nothing to
    the instrument — which is what lets §76.4's bar be registered from it
    before the first call is made.
    """
    return "\n".join([
        *_header(answers, tasks_root, logs),
        "",
        "strata (derived from each row's task and the key shape it ships)",
        *_strata_table(answers),
        "",
        "stratum A, by action, with the replay-computed split the bar reads",
        *_stratum_a_table(answers),
        "",
        _calls_line(answers),
        "",
        *_bar_lines(answers),
    ])


def _agreement_lines(judged: Sequence[Judged]) -> list[str]:
    rows = []
    for stratum in ("A", "B"):
        selected = [one for one in judged if one.answer.stratum == stratum]
        agreed = sum(1 for one in selected if one.agrees)
        rows.append([f"stratum {stratum}, overall", f"{agreed} of {len(selected)}"])
        if stratum == "A":
            unresolved = [
                one for one in selected if not one.answer.machine_resolved
            ]
            agreed = sum(1 for one in unresolved if one.agrees)
            rows.append([
                "stratum A, unresolved class",
                f"{agreed} of {len(unresolved)}",
            ])
    return padded_table(rows, indent="  ")


def _gate_lines(verdict: Gate) -> list[str]:
    rows = [
        [
            clause.label,
            f"{clause.agreed} of {clause.n}",
            f">= {clause.bar} of {clause.n}",
            ""
            if clause.met
            else ("not met" if clause.readable else "unreadable: the class is empty"),
        ]
        for clause in verdict.clauses
    ]
    return [
        f"gate (stratum A alone): {'MET' if verdict.met else 'FAILED'}",
        *padded_table(rows, indent="  "),
    ]


def render(
    judged: Sequence[Judged],
    *,
    tasks_root: Path,
    logs: Sequence[Path],
    calls: int,
    reused: int,
) -> str:
    """The whole page: the split, what the grader made of the archive, and the
    gate read off stratum A alone."""
    answers = [one.answer for one in judged]
    reuse = (
        [f"{reused} answer(s) reused rulings already archived under this version"]
        if reused
        else []
    )
    return "\n".join([
        render_split(answers, tasks_root=tasks_root, logs=logs),
        "",
        f"grader calls made: {calls}",
        *reuse,
        "",
        "agreement between the grader's verdict and the replayed machine verdict",
        *_agreement_lines(judged),
        f"  {CONFOUND}",
        "",
        *_gate_lines(gate(judged)),
    ])


def calibrate_grader(
    tasks: Sequence[Task],
    tasks_root: Path,
    logs: Sequence[Path],
    *,
    split_only: bool = False,
    grader_factory: Callable[[], PointGrader],
    rulings_dir: Path = DEFAULT_RULINGS_DIR,
    timeout_s: int = GRADE_TIMEOUT_S,
) -> str:
    """Run the calibration experiment over the archive and render its page.

    No agent filter and no language filter: every row of every log is read,
    for the reason in the module docstring. The split runs first and always;
    `split_only` stops there, having built no grader and made no call.
    """
    runs = [run for log in logs for run in load_runs(log)]
    answers = split(tasks, runs, timeout_s=timeout_s)
    if split_only:
        return render_split(answers, tasks_root=tasks_root, logs=logs)
    judged, calls, reused = judge(answers, grader_factory, rulings_dir=rulings_dir)
    return render(
        judged, tasks_root=tasks_root, logs=logs, calls=calls, reused=reused
    )
