"""The eighth `code-review` task (#79): a winter's work on a village watermill.

`watermill-review-the-grist-and-the-toll` hands the agent a repository with a
change already applied — the grist book the mill sets down what has been
brought in to be ground in, and the toll it takes for grinding it — plus
`review.diff`, the unified diff of that change, and asks which of it is wrong.
Three findings are planted, each the code disagreeing with a house rule the
README wrote down as the change was asked for, and each a shape none of the
first seven review tasks carries:

- `grist.py Book.to_the_stones` — a lot goes to the stones when it has dried
  *and* it has been weighed at the door, and the change joins the two the other
  way, so either on its own sends a lot up: a pair of conditions joined the
  wrong way round;
- `grist.py Hopper.tip_in` — the hopper is filled and asked afterwards whether
  it should have been, so the lot the rule turns away is in it all the same: a
  guard read after the state it was meant to protect had already changed;
- `toll.py worth_the_water` — the pecks of a lot are held up against a figure
  written in bushels, so two quantities are compared without either side being
  brought to the one measure.

Two non-findings are keyed as rejected: `sacks_to_carry`, which rounds a lot
*up* into sacks where the `bushels` beside it rounds down, because the house
rules ask for exactly that pair of roundings — and `Book.under`, the method next
door to the first finding, which answers for a name with that grower's own corn
*or* what they carried for a neighbour, which is what the rules ask of it.

This suite asserts what only this task can assert, through a git-built workdir
diff and the same execution-verified pipeline a live run takes:

- **The verdict on this task's own terrain**: the reference solution resolves
  and the empty diff does not; every planted finding reported resolves; an
  unregistered extra rides along unpunished; one planted finding missing does
  not resolve; one rejected finding reported does not resolve; and each of the
  two findings keyed at two levels resolves at either.
- **Each planted finding's existence proof**, run both ways: fails on `repo/`
  as handed over, passes on `corrected/`.
- **The repository names none of it**: no visible test names a planted symbol,
  the visible suite is green as shipped and green on the corrected tree, and
  the change under review touches exactly the files the findings live in plus
  the module the measures were added to, the README and the tests it added.
- **What the gate buys**: the same complete, correct review that resolves on
  its own grades unresolved once the repair rides along with it; a scratch note
  left behind does not.
- **The declarations**: a control, no behaviour tests, `scale` matching the
  reference solution's one-file diff, and the task linting clean.

What is *not* asserted here is what the task-set lint owns for every task
carrying a key — the terrain rules (#65), the hash-gate digests (#67), the
canonical grading bytes and the discrimination negatives (#70), the existence
proofs (#71). Those live in the lint on purpose; re-asserting them per task is
the round-4 copy-per-suite habit this corpus moved away from.
"""

import ast
import json
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

TASK = "watermill-review-the-grist-and-the-toll"
ANSWER_PATH = "FINDINGS.json"
REVIEW_DIFF = "review.diff"

# The three planted findings at their primary location, and the two rejected
# non-findings, as the key names them. Written out rather than read off the
# key, so that a key edited to say something else fails here and not silently.
PLANTED = (
    ("grist.py", "Book.to_the_stones"),
    ("grist.py", "Hopper.tip_in"),
    ("toll.py", "worth_the_water"),
)
REJECTED = (
    ("grist.py", "Book.under"),
    ("mill.py", "sacks_to_carry"),
)
# The two findings legitimately described at a second level: `grist.py` defines
# `Lot`, `Book` and `Hopper`, so naming either of the two classes a finding sits
# in is a location and not a filename in disguise (terrain rule 3). The third
# finding is a module-level function in a file that defines no class at all.
CLASS_LEVEL = {
    ("grist.py", "Book.to_the_stones"): ("grist.py", "Book"),
    ("grist.py", "Hopper.tip_in"): ("grist.py", "Hopper"),
}
# A real place a reviewer might mention that the key neither plants nor
# rejects: the whole book walked for a total the toll could keep as it goes.
UNREGISTERED = ("toll.py", "taken_off")

# What the change under review touches, read off the diff the repository ships.
CHANGED_FILES = {
    "README.md",
    "grist.py",
    "mill.py",
    "test_grist.py",
    "test_mill.py",
    "test_toll.py",
    "toll.py",
}


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


def symbols_named_in(source: str) -> set[str]:
    """Every attribute, name and string a test module mentions — the net a
    visible test could name a planted symbol with."""
    named: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            named.add(node.id)
        elif isinstance(node, ast.Attribute):
            named.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            named.add(node.value)
    return named


# --- the key, as this task writes it -------------------------------------------


def test_the_key_plants_three_findings_and_rejects_two() -> None:
    key = findings_key(task())

    primaries = tuple((f.primary.file, f.primary.symbol) for f in key.accepted)
    assert primaries == PLANTED
    assert tuple((a.file, a.symbol) for a in key.rejected) == REJECTED
    assert key.answer_path == ANSWER_PATH


def test_the_two_findings_inside_a_class_are_keyed_at_two_levels() -> None:
    """Where the class level was legitimately available it is written down;
    where there was no class to name it is not. The task's own comments say
    why for each."""
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
    extra = finding(*UNREGISTERED, "the whole book is walked for a running total")

    assert resolves(answers(every_planted(extra)))
    assert not resolves(answers(reporting(extra)))


@pytest.mark.parametrize("missing", PLANTED)
def test_one_planted_finding_missing_does_not_resolve(missing: tuple[str, str]) -> None:
    kept = [finding(*where) for where in PLANTED if where != missing]

    assert not resolves(answers(reporting(*kept)))


@pytest.mark.parametrize("wolf", REJECTED)
def test_one_rejected_finding_reported_does_not_resolve(wolf: tuple[str, str]) -> None:
    """Crying wolf about the sack a part-filled lot still takes to carry it,
    which the house rules ask for, or about the name answered with its own corn
    as well as what it carried for a neighbour, which the rules ask for too,
    fails the review however complete the rest of it is."""
    assert not resolves(answers(every_planted(finding(*wolf))))


@pytest.mark.parametrize("planted", sorted(CLASS_LEVEL))
def test_a_finding_inside_a_class_resolves_at_either_level(
    planted: tuple[str, str],
) -> None:
    """The mitigation for the round's expensive assumption, on real terrain: an
    agent that says "the hopper takes the lot in before it asks whether it
    fits" has located the defect, and the key says so."""
    at_the_class = reporting(
        *(
            finding(*(CLASS_LEVEL[planted] if where == planted else where))
            for where in PLANTED
        )
    )

    assert resolves(answers(at_the_class))


def test_a_bare_method_name_answers_a_qualified_one() -> None:
    """The comparison's forgiveness, inherited from the accepted-answer key:
    `tip_in` answers `Hopper.tip_in`."""
    bare = reporting(
        finding("grist.py", "to_the_stones"),
        finding("grist.py", "tip_in"),
        finding("toll.py", "worth_the_water"),
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
    key = findings_key(task())
    [this] = [f for f in key.accepted if (f.primary.file, f.primary.symbol) == planted]
    proof = task().directory / PROOFS_DIR / proof_test_name(this)

    assert proof.is_file(), proof
    assert not _proof_test_passes(task().repo_dir, proof, timeout_s=GRADE_TIMEOUT_S)
    assert _proof_test_passes(
        task().directory / CORRECTED_DIR, proof, timeout_s=GRADE_TIMEOUT_S
    )


def test_the_corrected_tree_differs_from_the_repository_only_where_findings_live() -> None:
    """The corrected tree is the repository with the three put right and
    nothing else — so a proof that passes there proves the finding and not
    some other change."""
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
    """The repository's own tests are the net the agent sees; a test that
    named a planted symbol would hand the review over."""
    planted_names = {symbol.rpartition(".")[-1] for _, symbol in PLANTED}

    for path in sorted(task().repo_dir.glob("test_*.py")):
        assert not symbols_named_in(path.read_text()) & planted_names, path.name


def test_the_visible_suite_is_green_as_shipped_and_once_corrected() -> None:
    """What the change added tests for is the part of it that works, and the
    correction breaks none of it — so neither tree reproduces a symptom."""
    corrected = task().directory / CORRECTED_DIR

    def put_right(workdir: Path) -> None:
        for path in corrected.iterdir():
            if path.is_file():
                (workdir / path.name).write_bytes(path.read_bytes())

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
    # wrong to point at the sacks a part-filled lot is carried off in because
    # the change is what put them there.
    assert {file for file, _ in REJECTED} <= touched


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
        (workdir / "toll.py").write_bytes((corrected / "toll.py").read_bytes())

    assert resolves(answers(every_planted()))
    assert not resolves(reviewed_and_repaired)


def test_reading_the_repository_leaves_it_as_it_was_found() -> None:
    def reviewed_with_notes(workdir: Path) -> None:
        answers(every_planted())(workdir)
        (workdir / "notes.md").write_text("the pecks are held up against bushels\n")

    assert resolves(reviewed_with_notes)


# --- the declarations -----------------------------------------------------------


def test_the_task_is_declared_as_designed() -> None:
    t = task()

    assert t.category == "code-review"
    assert is_control(t) and t.construction is None
    assert t.surface == "application"
    assert t.language == "python"
    assert t.grading.behaviour_tests == ()
    assert ANSWER_PATH in t.prompt and REVIEW_DIFF in t.prompt


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


def test_the_task_directory_has_the_shape_the_first_one_landed() -> None:
    """The layout ticket 10 landed and this task copies: the repository with
    the change applied and its diff, the corrected tree and the proofs beside
    it and outside `grading/`, one proof per planted finding."""
    d = task().directory

    assert (d / REPO_DIR / REVIEW_DIFF).is_file()
    assert (d / CORRECTED_DIR).is_dir() and (d / PROOFS_DIR).is_dir()
    assert not (d / "grading" / CORRECTED_DIR).exists()
    assert not (d / "grading" / PROOFS_DIR).exists()
    assert sorted(p.name for p in (d / PROOFS_DIR).iterdir()) == sorted(
        proof_test_name(f) for f in findings_key(task()).accepted
    )
