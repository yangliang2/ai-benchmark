"""The tenth `code-review` task, and the second written in TypeScript (#111).

`limekiln-review-the-drawing-and-the-carting` hands the agent a repository with
a change already applied — where the lime went once it was drawn, and who had
the kiln while it was being drawn — plus `review.diff`, the unified diff of that
change, and asks which of it is wrong. Three findings are planted, each the code
disagreeing with a house rule the README wrote down as the change was asked for,
and each a shape neither the eight Python review tasks nor
`masonsyard-review-the-lettering-and-the-account` carries:

- `dockets.ts Docket.asFigure` — `parseInt` takes the figures the written
  quantity begins with and passes over whatever the burner wrote after them,
  where the rule sets aside a docket that says anything but a plain figure: a
  prefix taken for the whole of what was written;
- `carting.ts Sheet.carts` — the carts are put into an object and read back off
  its keys, and a key that reads as a whole number comes back in counting order
  however it was put in: an order kept in a place that does not keep one;
- `spells.ts spellsIn` — a spell is closed where the next burner takes the kiln
  over and nowhere else, so the burner who has it at the end of the day is never
  written up: a run closed only by the one after it, and the last one never is.

Two of the three are what TypeScript makes easy to get wrong and Python does
not, which is the reason a second TypeScript review task is worth its place:
`parseInt` reads as far as it can and keeps what it got where `int` refuses the
whole string, and an object's keys come back in ascending numeric order wherever
they read as array indices where a dict has kept insertion order since 3.7.

Two non-findings are keyed as rejected, each standing next door to a real
finding so that the reviewer who found one is the reviewer most likely to cry
wolf about the other: `dockets.ts DayBook.drawn`, which lets a docket set aside
add nothing to the day, and `carting.ts Sheet.carried`, which gives none for a
cart that never loaded — both of which the house rules ask for.

This suite asserts what only this task can assert, through a git-built workdir
diff and the same execution-verified pipeline a live run takes:

- **The verdict on this task's own terrain**: the reference solution resolves
  and the empty diff does not; every planted finding reported resolves; an
  unregistered extra rides along unpunished; one planted finding missing does
  not resolve; one rejected finding reported does not resolve; and each of the
  two findings keyed at two levels resolves at either.
- **Each planted finding's existence proof**, run both ways through the
  TypeScript runner: fails on `repo/` as handed over, passes on `corrected/`.
- **The repository names none of it**: no visible test names a planted symbol,
  each rejected non-finding *is* exercised by one, the visible suite is green as
  shipped and green on the corrected tree, and the change under review touches
  exactly the files the findings live in plus the modules and tests it added.
- **What the gate buys**: the same complete, correct review that resolves on its
  own grades unresolved once the repair rides along with it; a scratch note left
  behind does not.
- **The declarations**: a control, no behaviour tests, `scale` matching the
  reference solution's one-file diff, and the task linting clean.

What is *not* asserted here is what something else already owns. The task-set
lint owns, for every task carrying a key, the terrain rules (#65), the hash-gate
digests (#67), the canonical grading bytes and the discrimination negatives
(#70), the existence proofs (#71), and the stdlib-only load of every `.ts` file
a task ships (ADR-0003) — re-asserting those per task is the round-4
copy-per-suite habit this corpus moved away from. And what being TypeScript
costs a *review* task — that its `grading/` stays this project's own Python
while its proofs are `.test.ts`, that `node --test` with no arguments really
does discover the visible suite — `tests/test_firstparty_v1_ts_review_1.py`
establishes once for the shape both tasks share; what is kept here of it is the
flatness the hash gate rests on, which is a property of this repository and of
no other.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    run_for,
    solution_diff,
    task_by_id,
    visible_tests_pass,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import (
    CORRECTED_DIR,
    FINDINGS_KEY_FILE,
    GRADE_TIMEOUT_S,
    GRADING_DIR,
    PROOFS_DIR,
    REPO_DIR,
    Task,
    _proof_test_passes,
    evaluate,
    findings_key,
    grade,
    is_control,
    lint_task_set,
    proof_test_name,
)
from ai_benchmark.language_runners import TYPESCRIPT

TASK = "limekiln-review-the-drawing-and-the-carting"
ANSWER_PATH = "FINDINGS.json"
REVIEW_DIFF = "review.diff"

# The three planted findings at their primary location, and the two rejected
# non-findings, as the key names them. Written out rather than read off the key,
# so that a key edited to say something else fails here and not silently.
PLANTED = (
    ("dockets.ts", "Docket.asFigure"),
    ("carting.ts", "Sheet.carts"),
    ("spells.ts", "spellsIn"),
)
REJECTED = (
    ("dockets.ts", "DayBook.drawn"),
    ("carting.ts", "Sheet.carried"),
)
# The two findings legitimately described at a second level: `dockets.ts`
# declares `DayBook` beside `Docket`, and `carting.ts` declares `Load` beside
# `Sheet`, so naming either class is a location and not a filename in disguise
# (terrain rule 3). The third finding is a module-level function in a file that
# declares no class at all — a spell is an interface, which is erased before
# anything runs and is no location a defect can live in.
CLASS_LEVEL = {
    ("dockets.ts", "Docket.asFigure"): ("dockets.ts", "Docket"),
    ("carting.ts", "Sheet.carts"): ("carting.ts", "Sheet"),
}
# A real place a reviewer might mention that the key neither plants nor rejects:
# a whole new sheet is built for every load set down on it.
UNREGISTERED = ("carting.ts", "Sheet.loaded")

# What the change under review touches, read off the diff the repository ships.
CHANGED_FILES = {
    "README.md",
    "carting.test.ts",
    "carting.ts",
    "dockets.test.ts",
    "dockets.ts",
    "spells.test.ts",
    "spells.ts",
}

# The module the change never reaches, and so the terrain the narrowing rule
# reads: a word of the prompt found there has selected nothing the review is
# hiding in.
UNTOUCHED = "kilns.ts"


def task() -> Task:
    return task_by_id(TASK)


def finding(file: str, symbol: str, note: str | None = None) -> dict[str, str]:
    entry = {"file": file, "symbol": symbol}
    if note is not None:
        entry["note"] = note
    return entry


def reporting(*findings: dict[str, str]) -> str:
    return json.dumps(list(findings), indent=2) + "\n"


def every_planted(*extra: dict[str, str]) -> str:
    return reporting(*(finding(*where) for where in PLANTED), *extra)


def answers(payload: str, *, at: str = ANSWER_PATH) -> Callable[[Path], None]:
    """The edit a run that wrote this answer file would log."""

    def write(workdir: Path) -> None:
        (workdir / at).write_text(payload)

    return write


def resolves(edit: Callable[[Path], None]) -> bool:
    """What the pipeline a real run replays through makes of this run."""
    return grade(task(), workdir_diff(task(), edit))


def repo_source(name: str) -> str:
    return (task().repo_dir / name).read_text(encoding="utf-8")


def visible_tests() -> dict[str, str]:
    """The repository's own test files, by name — the net the agent inherits."""
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(task().repo_dir.glob(TYPESCRIPT.visible_test_glob))
    }


def names(source: str, symbol: str) -> bool:
    """Whether this TypeScript source names this symbol as a whole word.

    Word-bounded rather than a substring test, for the reason the lint's own
    terrain rules are: `carts` must not be found inside `carting`, and a review
    key's symbols are matched case-exactly.
    """
    return re.search(rf"\b{re.escape(symbol)}\b", source) is not None


def put_right(workdir: Path) -> None:
    """Lay the corrected tree over a workdir: the repository with all three
    planted findings put right and nothing else changed."""
    for path in (task().directory / CORRECTED_DIR).iterdir():
        if path.is_file():
            (workdir / path.name).write_bytes(path.read_bytes())


# --- the key, as this task writes it -------------------------------------------


def test_the_key_plants_three_findings_and_rejects_two() -> None:
    key = findings_key(task())

    primaries = tuple((f.primary.file, f.primary.symbol) for f in key.accepted)
    assert primaries == PLANTED
    assert tuple((a.file, a.symbol) for a in key.rejected) == REJECTED
    assert key.answer_path == ANSWER_PATH


def test_the_two_findings_inside_a_class_are_keyed_at_two_levels() -> None:
    """Where the class level was legitimately available it is written down;
    where there was no class to name it is not. The task's own comments say why
    for each."""
    key = findings_key(task())

    levels = {
        (f.primary.file, f.primary.symbol): [(a.file, a.symbol) for a in f.any]
        for f in key.accepted
    }
    assert levels == {
        planted: [planted, CLASS_LEVEL[planted]] if planted in CLASS_LEVEL else [planted]
        for planted in PLANTED
    }


# --- the verdict on this task's own terrain ------------------------------------


def test_reference_solution_resolves_and_doing_nothing_does_not() -> None:
    runs = [
        run_for(task(), solution_diff(task()), model="reference"),
        run_for(task(), "", model="empty"),
    ]

    records = evaluate([task()], runs, source="run-log")

    assert {r.model: r.quality_value for r in records} == {"reference": 1.0, "empty": 0.0}


def test_reporting_every_planted_finding_resolves() -> None:
    assert resolves(answers(every_planted()))


def test_an_unregistered_extra_finding_is_neither_rewarded_nor_punished() -> None:
    """A real problem the author did not plant must not fail the run; the
    verdict measures recall of the planted truth and nothing it cannot
    enumerate."""
    extra = finding(*UNREGISTERED, "a whole new sheet for every load set down")

    assert resolves(answers(every_planted(extra)))
    assert not resolves(answers(reporting(extra)))


@pytest.mark.parametrize("missing", PLANTED)
def test_one_planted_finding_missing_does_not_resolve(missing: tuple[str, str]) -> None:
    kept = [finding(*where) for where in PLANTED if where != missing]

    assert not resolves(answers(reporting(*kept)))


@pytest.mark.parametrize("wolf", REJECTED)
def test_one_rejected_finding_reported_does_not_resolve(wolf: tuple[str, str]) -> None:
    """Crying wolf about the day's figure that lets a docket set aside add
    nothing, or about the cart that never loaded carrying none, fails the review
    however complete the rest of it is: the house rules ask for both."""
    assert not resolves(answers(every_planted(finding(*wolf))))


@pytest.mark.parametrize("planted", sorted(CLASS_LEVEL))
def test_a_finding_inside_a_class_resolves_at_either_level(
    planted: tuple[str, str],
) -> None:
    """The mitigation for the round's expensive assumption, on real terrain: an
    agent that says "the day sheet is no record of the order the carts came in"
    has located the defect, and the key says so."""
    at_the_class = reporting(
        *(
            finding(*(CLASS_LEVEL[planted] if where == planted else where))
            for where in PLANTED
        )
    )

    assert resolves(answers(at_the_class))


def test_a_bare_method_name_answers_a_qualified_one() -> None:
    """The comparison's forgiveness, inherited from the accepted-answer key:
    `asFigure` answers `Docket.asFigure`."""
    bare = reporting(
        finding("dockets.ts", "asFigure"),
        finding("carting.ts", "carts"),
        finding("spells.ts", "spellsIn"),
    )

    assert resolves(answers(bare))


def test_the_note_is_never_read() -> None:
    plain = every_planted()
    with_notes = reporting(
        *(finding(*where, "a note the verdict must not read") for where in PLANTED)
    )

    assert resolves(answers(plain)) == resolves(answers(with_notes)) is True


# --- each planted finding's existence proof ------------------------------------


@pytest.mark.parametrize("planted", PLANTED)
def test_each_proof_test_fails_as_shipped_and_passes_once_corrected(
    planted: tuple[str, str],
) -> None:
    """Run through the *TypeScript* runner, because the proof of a TypeScript
    task is a `.test.ts` file: `proof_test_name` spells it with the runner's own
    held-out glob, so a `.py` proof beside this task would be a file its runner
    could not run at all."""
    key = findings_key(task())
    [this] = [f for f in key.accepted if (f.primary.file, f.primary.symbol) == planted]
    proof = task().directory / PROOFS_DIR / proof_test_name(this, task().runner)

    assert task().runner is TYPESCRIPT
    assert proof.name.endswith(".test.ts") and proof.is_file(), proof
    assert not _proof_test_passes(
        task().repo_dir,
        proof,
        runner=task().runner,
        timeout_s=GRADE_TIMEOUT_S,
    )
    assert _proof_test_passes(
        task().directory / CORRECTED_DIR,
        proof,
        runner=task().runner,
        timeout_s=GRADE_TIMEOUT_S,
    )


def test_the_corrected_tree_differs_from_the_repository_only_where_findings_live() -> None:
    """The corrected tree is the repository with the three put right and nothing
    else — so a proof that passes there proves the finding and not some other
    change."""
    repo, corrected = task().repo_dir, task().directory / CORRECTED_DIR

    differing = {
        path.name
        for path in repo.iterdir()
        if path.is_file()
        and (corrected / path.name).is_file()
        and (corrected / path.name).read_bytes() != path.read_bytes()
    }
    assert differing == {file for file, _ in PLANTED}
    # Nothing is only on one side except the diff file, which describes the
    # change and has no place in the corrected tree.
    assert {p.name for p in repo.iterdir()} - {p.name for p in corrected.iterdir()} == {
        REVIEW_DIFF
    }


# --- the repository names none of it -------------------------------------------


def test_no_visible_test_names_a_planted_symbol() -> None:
    """The repository's own tests are the net the agent sees; a test that named
    a planted symbol would hand the review over — and, the findings being real
    defects, would also be red as the repository ships."""
    planted_names = {symbol.rpartition(".")[-1] for _, symbol in PLANTED}

    for name, source in visible_tests().items():
        for symbol in sorted(planted_names):
            assert not names(source, symbol), (name, symbol)


@pytest.mark.parametrize("rejected", REJECTED)
def test_every_rejected_non_finding_is_exercised_by_a_visible_test(
    rejected: tuple[str, str],
) -> None:
    """The other half of why the rejected half discriminates: the repository
    itself says what these two come to, so an agent reporting one has been told
    in the tests it was handed that the change got that part right."""
    _, symbol = rejected
    bare = symbol.rpartition(".")[-1]

    assert any(names(source, bare) for source in visible_tests().values())


def test_the_visible_suite_is_green_as_shipped_and_once_corrected() -> None:
    """What the change added tests for is the part of it that works, and the
    correction breaks none of it — so neither tree reproduces a symptom."""
    assert visible_tests_pass(task())
    assert visible_tests_pass(task(), put_right)


def test_the_change_under_review_touches_exactly_the_files_it_says() -> None:
    diff = repo_source(REVIEW_DIFF)

    touched = {
        line.split(" b/")[-1]
        for line in diff.splitlines()
        if line.startswith("diff --git ")
    }
    assert touched == CHANGED_FILES
    assert {file for file, _ in PLANTED} <= touched
    # The rejected half is judged against the same change: a reviewer is only
    # wrong to point at the day's figure because the change is what put it there.
    assert {file for file, _ in REJECTED} <= touched
    # And the one module the change never reaches is the terrain the narrowing
    # rule reads: a word of the prompt found there has selected nothing.
    assert UNTOUCHED not in touched


def test_the_key_ships_held_out_and_the_repository_carries_no_answer() -> None:
    assert (task().grading_dir / FINDINGS_KEY_FILE).is_file()
    assert not (task().repo_dir / FINDINGS_KEY_FILE).exists()
    assert not (task().repo_dir / ANSWER_PATH).exists()
    assert (task().repo_dir / REVIEW_DIFF).is_file()


# --- what the gate buys ---------------------------------------------------------


def test_a_correct_review_that_also_repaired_the_change_is_unresolved() -> None:
    corrected = task().directory / CORRECTED_DIR

    def reviewed_and_repaired(workdir: Path) -> None:
        answers(every_planted())(workdir)
        (workdir / "spells.ts").write_bytes((corrected / "spells.ts").read_bytes())

    assert resolves(answers(every_planted()))
    assert not resolves(reviewed_and_repaired)


def test_reading_the_repository_leaves_it_as_it_was_found() -> None:
    def reviewed_with_notes(workdir: Path) -> None:
        answers(every_planted())(workdir)
        (workdir / "notes.md").write_text("the last spell never reaches the sheet\n")

    assert resolves(reviewed_with_notes)


# --- what being TypeScript costs this task, and what it does not ----------------


def test_the_repository_is_flat_and_installs_nothing() -> None:
    """ADR-0003 and ticket 03's rule, on the one thing a second TypeScript
    review task still owes for itself: nothing to install, and nothing nested —
    the hash gate that holds a keyed task to answering rather than repairing
    hashes top-level files only, so a nested file would be outside it."""
    assert [entry for entry in task().repo_dir.iterdir() if entry.is_dir()] == []
    assert not list(task().repo_dir.rglob("package.json"))
    assert not list(task().repo_dir.rglob("node_modules"))


# --- the declarations -----------------------------------------------------------


def test_the_task_is_declared_as_designed() -> None:
    t = task()

    assert t.category == "code-review"
    assert is_control(t) and t.construction is None
    assert t.surface == "application"
    assert t.language == "typescript"
    assert t.grading.behaviour_tests == ()
    assert ANSWER_PATH in t.prompt and REVIEW_DIFF in t.prompt
    # The scenario is stated in the prompt and is not a new task field.
    assert "bank of lime kilns" in t.prompt
    assert not hasattr(t, "scenario")


def test_declared_scale_matches_the_reference_solution() -> None:
    """Single-file: the reference solution is the pristine tree plus the
    findings file, so the diff a solved run logs touches exactly one file."""
    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task()).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {ANSWER_PATH}
    assert task().scale == "single-file"


def test_the_task_lints_clean() -> None:
    assert lint_task_set([task()]) == []


def test_the_task_directory_has_the_shape_every_review_task_lands_in() -> None:
    """The layout the first review task landed and this one copies, spelled in
    the task's own language: the repository with the change applied and its
    diff, the corrected tree and the proofs beside it and outside `grading/`,
    one `.test.ts` proof per planted finding."""
    d = task().directory

    assert (d / REPO_DIR / REVIEW_DIFF).is_file()
    assert (d / CORRECTED_DIR).is_dir() and (d / PROOFS_DIR).is_dir()
    assert not (d / GRADING_DIR / CORRECTED_DIR).exists()
    assert not (d / GRADING_DIR / PROOFS_DIR).exists()
    assert sorted(p.name for p in (d / PROOFS_DIR).iterdir()) == sorted(
        proof_test_name(f, task().runner) for f in findings_key(task()).accepted
    )
