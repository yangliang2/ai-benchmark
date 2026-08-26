"""The point gate: `investigation`'s verdict shape, pinned against a fake grader.

The fifth verdict shape in `ai_benchmark.firstparty_v1`, and the only one whose
deliverable is prose. A task of that action ships no held-out grading test at
all: it ships a **points key**, and grading collects the prompt-named answer
file out of the workdir diff — that file alone — and asks a grader one narrow
question per planted point and per disqualifier. `resolved` is every point
covered by a ruling whose span the gate could find in the collected answer, and
no disqualifier present; binary, with no fraction of the points computed
anywhere (design note §67.3 pointed at points, §67.4, §76.6).

Nothing here reaches a live grader. The instrument is injected everywhere —
`FakeGrader` below rules on a marker rather than on meaning — because what is
under test is the gate: which file it collects, how many calls it makes, what
it archives, what it recomputes on replay, and what it refuses. That the live
instrument asks the right question is `tests/test_point_grader.py`'s.

The task trees are synthetic and built in `tmp_path` in the style of
`tests/test_firstparty_v1_mutation_gate.py`, and every diff in them is built
with real git (`firstparty_v1_tasks.tree_diff`), because a hand-written hunk
would drift from what `git apply --include` accepts.
"""

import json
import shutil
import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from firstparty_v1_tasks import run_for, workdir_diff

from ai_benchmark import firstparty_v1, point_grader, reconcile_v1
from ai_benchmark.cli import main
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Task,
    evaluate,
    load_task_set,
    rulings_file,
)
from ai_benchmark.point_grader import Point, Ruling
from conftest import FakeClaude

TASK_ID = "coalyard-where-the-weight-goes-missing"
ANSWER_PATH = "ANSWER.md"
AGENT = "claude-code"
MODEL = "claude-sonnet-5"

# The repository the investigation is about: two files, one of which rounds a
# reading before the other sums it. Small enough to read, real enough that an
# answer about it could be right or wrong.
WEIGHTS = '''\
"""Weigh a load in and out."""


def net(gross, tare):
    return round(gross - tare)
'''

LEDGER = '''\
"""Total a day's weighed loads."""

from weights import net


def total(loads):
    return sum(net(gross, tare) for gross, tare in loads)
'''

# The planted points and the one disqualifier, as the key writes them. The ids
# are what the fake grader rules on and what the archive is keyed by.
POINTS = [
    {
        "id": "the-rounding-site",
        "text": "The answer says weights.net() rounds each load before it is summed.",
    },
    {
        "id": "the-accumulated-error",
        "text": "The answer says the per-load rounding is what the day's total loses.",
    },
]
DISQUALIFIERS = [
    {
        "id": "blames-the-scale",
        "text": "The answer claims the weighbridge hardware is miscalibrated.",
    },
]


# --- building a task, an answer and a run's diff -------------------------------


def points_key_json(
    *,
    answer_path: str = ANSWER_PATH,
    points: list[dict[str, str]] | None = None,
    disqualifiers: list[dict[str, str]] | None = None,
) -> str:
    return json.dumps(
        {
            "answer_path": answer_path,
            "points": POINTS if points is None else points,
            "disqualifiers": DISQUALIFIERS if disqualifiers is None else disqualifiers,
        },
        indent=2,
    )


def write_task(
    root: Path,
    *,
    task_id: str = TASK_ID,
    category: str = "investigation",
    key: str | None = None,
    grading: Mapping[str, str] | None = None,
) -> Path:
    """A synthetic task directory, correct unless an argument breaks it."""
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "repo" / "weights.py").write_text(WEIGHTS)
    (task_dir / "repo" / "ledger.py").write_text(LEDGER)
    (task_dir / "task.yaml").write_text(textwrap.dedent(f"""\
        id: {task_id}
        category: {category}
        scale: cross-file
        surface: application
        language: python
        control: true
        prompt: |
          A day's total is lighter than the loads that made it. Work out why,
          and write what you found to {ANSWER_PATH}.
        """))
    if key is not None:
        (task_dir / "grading").mkdir(exist_ok=True)
        (task_dir / "grading" / "points-key.json").write_text(key)
    for name, source in (grading or {}).items():
        (task_dir / "grading").mkdir(exist_ok=True)
        (task_dir / "grading" / name).write_text(source)
    return task_dir


def point_task(root: Path) -> Task:
    """The well-formed task, loaded — what every gate test starts from."""
    write_task(root, key=points_key_json())
    [task] = load_task_set(root)
    return task


def wrote(files: Mapping[str, str]) -> Callable[[Path], None]:
    """What an agent did in its workdir, as the edit a run's diff records."""

    def edit(workdir: Path) -> None:
        for name, source in files.items():
            path = workdir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(source))

    return edit


def answer(*ids: str, extra: str = "") -> str:
    """An answer file that covers exactly these questions.

    One line per id, each naming the id itself, because that is what the fake
    grader rules on: the point of these tests is the gate around the grader,
    not the grader's reading.
    """
    lines = [f"- {id}: this is what I found, in as many words.\n" for id in ids]
    return "# What the day loses\n\n" + "".join(lines) + extra


# --- the instrument, faked -----------------------------------------------------


VERSION = "fake-grader:0000000000ff"


class FakeGrader:
    """A stand-in point grader that counts what it was asked.

    By default it rules a question covered when some line of the deliverable
    names the question's id, and quotes that line as its span — a marker rule,
    so that an answer's coverage is exactly what a test wrote into it. A
    ruling passed to the constructor overrides that for one id, which is how a
    test makes the instrument say something the deliverable does not support.
    """

    def __init__(
        self,
        rulings: Mapping[str, tuple[bool, str | None]] | None = None,
        *,
        version: str = VERSION,
    ) -> None:
        self.calls: list[str] = []
        self.rulings = dict(rulings or {})
        self.version = version

    def __call__(self, deliverable: str, point: Point) -> Ruling:
        self.calls.append(point["id"])
        if point["id"] in self.rulings:
            covered, span = self.rulings[point["id"]]
        else:
            span = next(
                (line for line in deliverable.splitlines() if point["id"] in line),
                None,
            )
            covered = span is not None
        return Ruling(
            point_id=point["id"],
            covered=covered,
            span=span,
            grader_version=self.version,
        )


class FakeFactory:
    """The grader factory, counting how often a grader was built at all."""

    def __init__(self, grader: FakeGrader | None = None) -> None:
        self.grader = grader or FakeGrader()
        self.built = 0

    def __call__(self) -> point_grader.PointGrader:
        self.built += 1
        return self.grader


def never_built() -> point_grader.PointGrader:
    """A factory a replay must never call."""
    raise AssertionError("a replay constructed a grader")


# --- running one row through the seam a sweep runs through ---------------------


def evaluated(
    task: Task,
    diff: str,
    *,
    rulings: Path,
    factory: Callable[[], point_grader.PointGrader] | None = None,
    model: str = MODEL,
) -> float:
    """What a sweep would record for a run that produced this diff.

    Read at `evaluate`, the seam a sweep and a replay both run through, rather
    than at the gate's own internals.
    """
    [record] = evaluate(
        [task],
        [run_for(task, diff, model=model)],
        source="run-log",
        rulings=rulings,
        grader_factory=factory,
    )
    return record.quality_value


def archive_of(rulings: Path, task: Task, *, model: str = MODEL) -> dict[str, Any]:
    """One run row's archived rulings, as JSON — read as the file holds them,
    so that what a later reader will find is what is asserted here."""
    path = rulings_file(rulings, task.id, AGENT, model)
    data: dict[str, Any] = json.loads(path.read_text())
    return data


# --- the round trip: a live grade archives, a replay recomputes -----------------


def test_a_live_grade_archives_its_rulings_and_a_replay_returns_the_same_verdict(
    tmp_path: Path,
) -> None:
    """The whole round trip. One live grading, one call per question, an
    archive written under the run's own key — and the same row replayed to the
    identical verdict with a factory that raises if it is ever called."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))
    factory = FakeFactory()

    assert evaluated(task, diff, rulings=rulings, factory=factory) == 1.0
    assert factory.built == 1
    assert factory.grader.calls == [
        "the-rounding-site", "the-accumulated-error", "blames-the-scale",
    ]
    archived = archive_of(rulings, task)
    assert archived["grader_version"] == VERSION
    assert {ruling["point_id"] for ruling in archived["rulings"]} == {
        "the-rounding-site", "the-accumulated-error", "blames-the-scale",
    }

    assert evaluated(task, diff, rulings=rulings, factory=never_built) == 1.0


def test_a_replay_with_no_archived_rulings_raises_naming_the_row(
    tmp_path: Path,
) -> None:
    """`--replay` passes no factory, so a point-keyed row with nothing archived
    is refused loudly rather than silently re-graded at a second row's cost."""
    task = point_task(tmp_path / "tasks")
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))

    with pytest.raises(IngestError) as refusal:
        evaluated(task, diff, rulings=tmp_path / "rulings")

    assert TASK_ID in str(refusal.value)
    assert f"{TASK_ID}__{AGENT}__{MODEL}.json" in str(refusal.value)


def test_rulings_archived_for_another_deliverable_are_not_reused(
    tmp_path: Path,
) -> None:
    """The archive is keyed to the answer it was taken against by hash: a
    second run of the same cell writing different prose is graded afresh where
    a grader is there, and refused where one is not."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    covered = [p["id"] for p in POINTS]
    first = workdir_diff(task, wrote({ANSWER_PATH: answer(*covered)}))
    assert evaluated(task, first, rulings=rulings, factory=FakeFactory()) == 1.0

    second = workdir_diff(task, wrote({ANSWER_PATH: answer(covered[0])}))
    with pytest.raises(IngestError) as refusal:
        evaluated(task, second, rulings=rulings)
    assert "different deliverable" in str(refusal.value)

    factory = FakeFactory()
    assert evaluated(task, second, rulings=rulings, factory=factory) == 0.0
    assert factory.built == 1


# --- what the verdict is -------------------------------------------------------


def test_every_point_covered_and_no_disqualifier_resolves(tmp_path: Path) -> None:
    task = point_task(tmp_path / "tasks")
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))

    assert evaluated(task, diff, rulings=tmp_path / "r", factory=FakeFactory()) == 1.0


def test_one_uncovered_point_does_not_resolve(tmp_path: Path) -> None:
    """Every planted point, not most of them: an answer covering one of two is
    unresolved, and nothing between the two verdicts is computed."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer("the-rounding-site")}))

    assert evaluated(task, diff, rulings=rulings, factory=FakeFactory()) == 0.0
    # Half the points covered is not half a verdict, and no fraction over the
    # points is stored either (§67.3): the archive holds rulings and nothing
    # that could be read as a score.
    archived = archive_of(rulings, task)
    assert set(archived) == {"grader_version", "deliverable_sha256", "rulings"}
    assert all(
        set(ruling) == {"point_id", "kind", "covered", "span", "verified"}
        for ruling in archived["rulings"]
    )


def test_a_present_disqualifier_does_not_resolve(tmp_path: Path) -> None:
    """Even with every planted point covered: a disqualifying claim is the one
    thing an otherwise complete answer cannot survive."""
    task = point_task(tmp_path / "tasks")
    diff = workdir_diff(task, wrote({
        ANSWER_PATH: answer(*[p["id"] for p in POINTS], "blames-the-scale"),
    }))

    assert evaluated(task, diff, rulings=tmp_path / "r", factory=FakeFactory()) == 0.0


def test_a_covered_ruling_whose_span_is_absent_is_demoted_by_the_gate(
    tmp_path: Path,
) -> None:
    """Span verification is the gate's, not the grader's (§76.6). A ruling that
    says covered and quotes something the answer does not contain is not a
    covered ruling, and the demotion is in the archive rather than lost."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer("the-rounding-site")}))
    grader = FakeGrader({
        "the-accumulated-error": (True, "a span this answer never wrote"),
    })

    assert evaluated(task, diff, rulings=rulings, factory=FakeFactory(grader)) == 0.0

    [demoted] = [
        ruling
        for ruling in archive_of(rulings, task)["rulings"]
        if ruling["point_id"] == "the-accumulated-error"
    ]
    assert demoted["covered"] is True and demoted["verified"] is False


def test_a_covered_ruling_with_no_span_at_all_is_demoted(tmp_path: Path) -> None:
    task = point_task(tmp_path / "tasks")
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))
    grader = FakeGrader({"the-rounding-site": (True, None)})

    assert evaluated(task, diff, rulings=tmp_path / "r", factory=FakeFactory(grader)) == 0.0


def test_a_span_is_verified_through_the_instrument_s_own_normalisation(
    tmp_path: Path,
) -> None:
    """A quote that differs from the answer only in whitespace is the answer's
    own text, and the gate reads it the way `point_grader` does — one
    normalisation, defined once, rather than a second one written here."""
    task = point_task(tmp_path / "tasks")
    covered = [p["id"] for p in POINTS]
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*covered)}))
    rewrapped = f"-   {covered[0]}:   this is what I found,\n   in as many words."
    grader = FakeGrader({covered[0]: (True, rewrapped)})

    assert evaluated(task, diff, rulings=tmp_path / "r", factory=FakeFactory(grader)) == 1.0


# --- what is collected, and what costs nothing ---------------------------------


def test_an_empty_diff_is_unresolved_with_no_grader_call_and_nothing_written(
    tmp_path: Path,
) -> None:
    """The property the lint depends on: `grade(task, "")` on a point-keyed
    task is offline and free."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    factory = FakeFactory()

    assert evaluated(task, "", rulings=rulings, factory=factory) == 0.0
    assert factory.built == 0 and factory.grader.calls == []
    assert not rulings.exists()


def test_an_empty_answer_file_is_unresolved_with_no_grader_call(
    tmp_path: Path,
) -> None:
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    factory = FakeFactory()

    assert evaluated(
        task, workdir_diff(task, wrote({ANSWER_PATH: "   \n\n"})),
        rulings=rulings, factory=factory,
    ) == 0.0
    assert factory.grader.calls == []
    assert not rulings.exists()


def test_an_answer_written_anywhere_but_the_prompt_named_path_is_not_collected(
    tmp_path: Path,
) -> None:
    """A run that put its findings in scratch files answered nowhere the prompt
    named: nothing is collected, and the row costs no grader call."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    factory = FakeFactory()
    diff = workdir_diff(task, wrote({
        "NOTES.md": answer(*[p["id"] for p in POINTS]),
        "scratch/findings.md": answer(*[p["id"] for p in POINTS]),
    }))

    assert evaluated(task, diff, rulings=rulings, factory=factory) == 0.0
    assert factory.grader.calls == []
    assert not rulings.exists()


def test_everything_outside_the_answer_file_is_scored_by_nothing(
    tmp_path: Path,
) -> None:
    """§67.4 narrowed to one path: an agent that rewrote the repository while
    reading it, and left notes behind, is graded on its answer alone — the same
    deliverable, byte for byte, as one that touched nothing else."""
    task = point_task(tmp_path / "tasks")
    rulings = tmp_path / "rulings"
    covered = [p["id"] for p in POINTS]
    alone = workdir_diff(task, wrote({ANSWER_PATH: answer(*covered)}))
    busy = workdir_diff(task, wrote({
        ANSWER_PATH: answer(*covered),
        "weights.py": '''\
            """Weigh a load in and out."""


            def net(gross, tare):
                return gross - tare
            ''',
        "NOTES.md": "I went and rewrote net() while I was in here.\n",
    }))

    assert evaluated(task, alone, rulings=rulings, factory=FakeFactory()) == 1.0
    hash_of_the_answer_alone = archive_of(rulings, task)["deliverable_sha256"]

    assert evaluated(
        task, busy, rulings=rulings, factory=FakeFactory(), model="claude-haiku-4-5",
    ) == 1.0
    busy_archive = archive_of(rulings, task, model="claude-haiku-4-5")
    assert busy_archive["deliverable_sha256"] == hash_of_the_answer_alone


# --- the loader ----------------------------------------------------------------


def test_a_points_key_shipped_by_any_other_action_is_refused(tmp_path: Path) -> None:
    """Any action outside the registered set, and the refusal names the set
    rather than one member of it: the key is the ground truth of the two prose
    actions and of nothing else, and what the refusal is *for* — the verdict
    swap — is what a `bug-fix` task shipping one would have bought."""
    root = tmp_path / "tasks"
    write_task(root, category="bug-fix", key=points_key_json())

    with pytest.raises(IngestError) as refusal:
        load_task_set(root)

    assert "points-key.json" in str(refusal.value)
    assert "investigation" in str(refusal.value)
    assert "requirement-decomposition" in str(refusal.value)
    assert "swap this task's whole verdict" in str(refusal.value)


def test_a_requirement_decomposition_task_shipping_a_points_key_loads(
    tmp_path: Path,
) -> None:
    """The positive twin of the refusal above. Heap 3's second action is
    registered as point-keyed (§94.1, ADR-0005's Context), so the key it ships
    is its own ground truth and the loader takes it down the same branch an
    `investigation` task goes down — no second gate, no second key shape."""
    root = tmp_path / "tasks"
    write_task(root, category="requirement-decomposition", key=points_key_json())

    [task] = load_task_set(root)

    assert task.category == "requirement-decomposition"
    assert firstparty_v1.is_point_keyed(task)
    assert task.grading_test_paths == ()
    assert firstparty_v1.points_key(task).answer_path == ANSWER_PATH


def test_a_requirement_decomposition_task_shipping_no_points_key_is_refused(
    tmp_path: Path,
) -> None:
    """The "and must" half of the widening: the registered set says which
    actions may ship this key *and* which have to, so the second action is held
    to the mandatory key the first is."""
    root = tmp_path / "tasks"
    write_task(root, category="requirement-decomposition", key=None)

    with pytest.raises(IngestError) as refusal:
        load_task_set(root)

    assert "points-key.json" in str(refusal.value)


def test_an_investigation_task_shipping_no_points_key_is_refused(
    tmp_path: Path,
) -> None:
    """Read at load and not left to the lint: `run-live` loads a task set and
    never lints it, so a task the gate could not grade would otherwise reach a
    paid run."""
    root = tmp_path / "tasks"
    write_task(root, key=None)

    with pytest.raises(IngestError) as refusal:
        load_task_set(root)

    assert "points-key.json" in str(refusal.value)


def test_a_points_key_planting_nothing_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "tasks"
    write_task(root, key=points_key_json(points=[]))

    with pytest.raises(IngestError) as refusal:
        load_task_set(root)

    assert "plants no points" in str(refusal.value)


def test_a_points_key_reusing_one_id_across_its_halves_is_refused(
    tmp_path: Path,
) -> None:
    root = tmp_path / "tasks"
    write_task(root, key=points_key_json(
        disqualifiers=[{"id": POINTS[0]["id"], "text": "the same id twice over"}],
    ))

    with pytest.raises(IngestError) as refusal:
        load_task_set(root)

    assert POINTS[0]["id"] in str(refusal.value)


def test_a_point_keyed_task_shipping_no_held_out_test_loads(tmp_path: Path) -> None:
    """A point-keyed task's `grading/` holds the key and nothing that runs —
    the branch that refuses a task with no held-out suite must not reach it."""
    task = point_task(tmp_path / "tasks")

    assert task.category == "investigation"
    assert task.grading_test_paths == ()
    assert firstparty_v1.is_point_keyed(task)
    assert firstparty_v1.points_key(task).answer_path == ANSWER_PATH


# --- the default archive, and the callers that thread no argument --------------


def test_the_observed_outcomes_call_path_replays_from_the_default_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`reconcile_v1.observed_outcomes` — and `calibrate-v1` through it — runs
    at the end of every sweep and threads no rulings argument at all. With the
    module-level default it replays a point-keyed row from the committed
    archive; with a required argument it would raise on the first one. No
    grader is constructed on that path, which the poisoned instrument pins."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(point_grader, "deepseek_point_grader", never_built)
    task = point_task(tmp_path / "tasks")
    covered = [p["id"] for p in POINTS]
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*covered)}))
    # One live grading, into the default archive exactly where a sweep leaves it.
    assert evaluated(
        task, diff, rulings=firstparty_v1.DEFAULT_RULINGS_DIR, factory=FakeFactory(),
    ) == 1.0
    assert (
        tmp_path / firstparty_v1.DEFAULT_RULINGS_DIR
        / f"{TASK_ID}__{AGENT}__{MODEL}.json"
    ).is_file()

    outcomes = reconcile_v1.observed_outcomes(
        [task], [run_for(task, diff, model=MODEL)], source="run-log",
    )

    assert outcomes[TASK_ID].resolved == {MODEL: True}
    # And the seam is exactly what that reader reaches: `evaluate` called the
    # way it calls it, with neither argument threaded.
    [record] = evaluate(
        [task], [run_for(task, diff, model=MODEL)],
        source="run-log", timeout_s=GRADE_TIMEOUT_S,
    )
    assert record.quality_value == 1.0


# --- the command surface -------------------------------------------------------


def test_eval_v1_replays_a_point_keyed_row_from_the_rulings_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--replay` reads the archive `--rulings` names and constructs no
    client — the poisoned instrument would raise if the command reached for
    one."""
    monkeypatch.setattr(point_grader, "deepseek_point_grader", never_built)
    tasks = tmp_path / "tasks"
    task = point_task(tasks)
    rulings = tmp_path / "rulings"
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))
    run = run_for(task, diff, model=MODEL)
    assert evaluated(task, diff, rulings=rulings, factory=FakeFactory()) == 1.0
    log = tmp_path / "runs.jsonl"
    log.write_text(json.dumps(run.model_dump(mode="json")) + "\n")

    main(["eval-v1", "--tasks", str(tasks), "--replay", str(log),
          "--rulings", str(rulings), "--data", str(tmp_path / "unified.jsonl")])

    assert "evaluated 1 runs over 1 tasks (1 resolved)" in capsys.readouterr().out


def test_eval_v1_live_grades_a_point_keyed_row_and_leaves_the_archive_behind(
    fake_claude: FakeClaude, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Live at the command surface, against a faked claude CLI and a faked
    grader: the run writes an answer, the gate grades it a point at a time, and
    the rulings land under `--rulings` where a replay will find them."""
    written = answer(*[p["id"] for p in POINTS])
    fake_claude(
        f"(workdir / {ANSWER_PATH!r}).write_text({written!r})\n"
    )
    factory = FakeFactory()
    monkeypatch.setattr(point_grader, "deepseek_point_grader", factory)
    tasks = tmp_path / "tasks"
    point_task(tasks)
    rulings = tmp_path / "rulings"

    main(["eval-v1", "--tasks", str(tasks), "--live", "--model", MODEL,
          "--log", str(tmp_path / "runs.jsonl"), "--sweep", "round-9-fake",
          "--rulings", str(rulings), "--data", str(tmp_path / "unified.jsonl")])

    assert "evaluated 1 runs over 1 tasks (1 resolved)" in capsys.readouterr().out
    assert factory.built == 1
    assert (rulings / f"{TASK_ID}__{AGENT}__{MODEL}.json").is_file()


def test_eval_v1_with_no_rulings_flag_reads_the_module_level_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The flag's default is `firstparty_v1.DEFAULT_RULINGS_DIR` rather than a
    second copy of the path owned here, so an invocation naming no archive
    replays out of the one every other caller writes to."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(point_grader, "deepseek_point_grader", never_built)
    tasks = tmp_path / "tasks"
    task = point_task(tasks)
    diff = workdir_diff(task, wrote({ANSWER_PATH: answer(*[p["id"] for p in POINTS])}))
    assert evaluated(
        task, diff, rulings=firstparty_v1.DEFAULT_RULINGS_DIR, factory=FakeFactory(),
    ) == 1.0
    log = tmp_path / "runs.jsonl"
    log.write_text(
        json.dumps(run_for(task, diff, model=MODEL).model_dump(mode="json")) + "\n"
    )

    main(["eval-v1", "--tasks", str(tasks), "--replay", str(log),
          "--data", str(tmp_path / "unified.jsonl")])

    assert "evaluated 1 runs over 1 tasks (1 resolved)" in capsys.readouterr().out


# --- keeping the fixture honest ------------------------------------------------


def test_the_synthetic_task_is_the_shape_the_gate_expects(tmp_path: Path) -> None:
    """The tree these tests are written against, checked once: the key is held
    out in `grading/`, and nothing in the starting repository discloses it."""
    task = point_task(tmp_path / "tasks")

    assert (task.grading_dir / "points-key.json").is_file()
    assert not any(
        "points-key" in path.read_text() for path in task.repo_dir.rglob("*.py")
    )
    assert "points-key" not in task.prompt
    shutil.rmtree(task.directory / "grading")
    assert not firstparty_v1.is_point_keyed(task)
