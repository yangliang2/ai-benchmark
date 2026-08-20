"""The ninth `code-review` task, and the first written in TypeScript (#110).

`masonsyard-review-the-lettering-and-the-account` hands the agent a repository
with a change already applied — the words somebody gave a monumental mason set
out for the chisel, and what a quarter of that work comes to — plus
`review.diff`, the unified diff of that change, and asks which of it is wrong.
Three findings are planted, each the code disagreeing with a house rule the
README wrote down as the change was asked for, and each a shape none of the
eight Python review tasks carries:

- `inscription.ts asCut` — `String.prototype.replace` with a string pattern
  writes out the first `&` and leaves every other one standing, where the rule
  is that every one an inscription was given is cut in full: a replacement made
  once where every occurrence was meant;
- `orders.ts Book.strikeOff` — `delete` takes the order out of its place
  without closing the place up, so the book still counts what is no longer in
  it: a removal that leaves behind the place it was made in;
- `account.ts Account.comesTo` — every line is brought to whole shillings on
  its way past, so the odd pence are dropped a line at a time and never reach
  the foot: a rounding made at every step where the rule rounds once at the end.

Two of the three are what TypeScript makes easy to get wrong and Python does
not, which is the reason a TypeScript review task exists at all: `replace` with
a string pattern is the first occurrence only, and `delete` on an array leaves
the array the same length with a hole in it.

Two non-findings are keyed as rejected, each standing next door to a real
finding so that the reviewer who found one is the reviewer most likely to cry
wolf about the other: `inscription.ts dateOn`, which takes the first date the
words give and no other — the rule says the head of a stone carries the first of
two dates — and `account.ts Rate.forLetters`, which rounds a part hundred of
lettering away, which the rule asks for at that one place.

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
- **What being TypeScript costs and does not**: the repository is flat and
  stdlib-only, every specifier a shipped `.ts` file names is a `node:` builtin
  or a relative `.ts` file, `grading/` is the project's own Python and nothing
  else, and the README names the way the visible suite is really run.
- **The declarations**: a control, no behaviour tests, `scale` matching the
  reference solution's one-file diff, and the task linting clean.

What is *not* asserted here is what the task-set lint owns for every task
carrying a key — the terrain rules (#65), the hash-gate digests (#67), the
canonical grading bytes and the discrimination negatives (#70), the existence
proofs (#71), and the stdlib-only load of every `.ts` file the task ships
(ADR-0003). Those live in the lint on purpose; re-asserting them per task is the
round-4 copy-per-suite habit this corpus moved away from.
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
    _typescript_specifiers,
    evaluate,
    findings_key,
    grade,
    is_control,
    lint_task_set,
    proof_test_name,
)
from ai_benchmark.language_runners import PYTHON, TYPESCRIPT

TASK = "masonsyard-review-the-lettering-and-the-account"
ANSWER_PATH = "FINDINGS.json"
REVIEW_DIFF = "review.diff"

# The three planted findings at their primary location, and the two rejected
# non-findings, as the key names them. Written out rather than read off the key,
# so that a key edited to say something else fails here and not silently.
PLANTED = (
    ("inscription.ts", "asCut"),
    ("orders.ts", "Book.strikeOff"),
    ("account.ts", "Account.comesTo"),
)
REJECTED = (
    ("inscription.ts", "dateOn"),
    ("account.ts", "Rate.forLetters"),
)
# The two findings legitimately described at a second level: `orders.ts`
# declares `Order` beside `Book`, and `account.ts` declares `Rate` and `Piece`
# beside `Account`, so naming either class is a location and not a filename in
# disguise (terrain rule 3). The first finding is a module-level function in a
# file that declares no class at all.
CLASS_LEVEL = {
    ("orders.ts", "Book.strikeOff"): ("orders.ts", "Book"),
    ("account.ts", "Account.comesTo"): ("account.ts", "Account"),
}
# A real place a reviewer might mention that the key neither plants nor rejects:
# every line of the account is worked out afresh each time the foot is asked for.
UNREGISTERED = ("account.ts", "Account.lines")

# What the change under review touches, read off the diff the repository ships.
CHANGED_FILES = {
    "README.md",
    "account.test.ts",
    "account.ts",
    "inscription.test.ts",
    "inscription.ts",
    "orders.test.ts",
    "orders.ts",
}

# The harness-side half of a keyed task's grading directory: the canonical
# findings test and the generated hash gate, both Python whatever the task's
# language, and no held-out test of the task's own.
HARNESS_TESTS = ("test_findings.py", "test_the_repository_is_as_it_was.py")


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
    terrain rules are: `asCut` must not be found inside `asCutAndDressed`, and
    a review key's symbols are matched case-exactly.
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
    extra = finding(*UNREGISTERED, "every line is worked out again at the foot")

    assert resolves(answers(every_planted(extra)))
    assert not resolves(answers(reporting(extra)))


@pytest.mark.parametrize("missing", PLANTED)
def test_one_planted_finding_missing_does_not_resolve(missing: tuple[str, str]) -> None:
    kept = [finding(*where) for where in PLANTED if where != missing]

    assert not resolves(answers(reporting(*kept)))


@pytest.mark.parametrize("wolf", REJECTED)
def test_one_rejected_finding_reported_does_not_resolve(wolf: tuple[str, str]) -> None:
    """Crying wolf about the date the head of a stone carries, which the house
    rules ask to be the first of two, or about the part hundred of lettering
    that is not charged for, which the rules ask for too, fails the review
    however complete the rest of it is."""
    assert not resolves(answers(every_planted(finding(*wolf))))


@pytest.mark.parametrize("planted", sorted(CLASS_LEVEL))
def test_a_finding_inside_a_class_resolves_at_either_level(
    planted: tuple[str, str],
) -> None:
    """The mitigation for the round's expensive assumption, on real terrain: an
    agent that says "the order book is no shorter for striking an order off" has
    located the defect, and the key says so."""
    at_the_class = reporting(
        *(
            finding(*(CLASS_LEVEL[planted] if where == planted else where))
            for where in PLANTED
        )
    )

    assert resolves(answers(at_the_class))


def test_a_bare_method_name_answers_a_qualified_one() -> None:
    """The comparison's forgiveness, inherited from the accepted-answer key:
    `strikeOff` answers `Book.strikeOff`."""
    bare = reporting(
        finding("inscription.ts", "asCut"),
        finding("orders.ts", "strikeOff"),
        finding("account.ts", "comesTo"),
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
    # wrong to point at the date the head of a stone carries because the change
    # is what put it there.
    assert {file for file, _ in REJECTED} <= touched
    # And the one module the change never reaches is the terrain the narrowing
    # rule reads: a word of the prompt found there has selected nothing.
    assert "stones.ts" not in touched


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
        (workdir / "account.ts").write_bytes((corrected / "account.ts").read_bytes())

    assert resolves(answers(every_planted()))
    assert not resolves(reviewed_and_repaired)


def test_reading_the_repository_leaves_it_as_it_was_found() -> None:
    def reviewed_with_notes(workdir: Path) -> None:
        answers(every_planted())(workdir)
        (workdir / "notes.md").write_text("the odd pence go a line at a time\n")

    assert resolves(reviewed_with_notes)


# --- what being TypeScript costs, and what it does not --------------------------


def test_the_repository_is_flat_and_installs_nothing() -> None:
    """ADR-0003 and ticket 03's rule, on the one task that owes both: nothing to
    install, and nothing nested — the hash gate that holds a keyed task to
    answering rather than repairing hashes top-level files only."""
    assert [entry for entry in task().repo_dir.iterdir() if entry.is_dir()] == []
    assert not list(task().repo_dir.rglob("package.json"))
    assert not list(task().repo_dir.rglob("node_modules"))


@pytest.mark.parametrize("tree", (REPO_DIR, CORRECTED_DIR, PROOFS_DIR))
def test_every_shipped_typescript_file_names_only_what_grading_can_give_it(
    tree: str,
) -> None:
    """A `node:` builtin or a file of the task, relatively and with the
    extension Node resolves — and nothing else, in any of the three trees this
    task ships TypeScript in. The lint holds the held-out half to this; the
    proofs and the corrected tree are run by the lint itself, in a workdir where
    no install has happened either."""
    for path in sorted((task().directory / tree).glob(TYPESCRIPT.source_glob)):
        for specifier in sorted(set(_typescript_specifiers(path.read_text()))):
            assert specifier.startswith("node:") or (
                specifier.startswith("./") and specifier.endswith(".ts")
            ), (path.name, specifier)


def test_grading_is_this_project_s_own_python_and_nothing_of_the_task_s() -> None:
    """A review task's verdict is read by the harness and never by the
    repository's language: the findings comparison reads a JSON file out of the
    workdir and the hash gate reads file digests, so both halves stay Python
    while the task itself is TypeScript."""
    t = task()

    assert t.harness_test_paths == HARNESS_TESTS
    assert t.language_test_paths == ()
    assert t.grading_halves == ((PYTHON, HARNESS_TESTS),)
    assert not list(t.grading_dir.glob(TYPESCRIPT.source_glob))


def test_the_readme_names_the_way_the_visible_suite_is_actually_run() -> None:
    """`node --test` with no arguments really does discover `*.test.ts` on the
    Node that grades this, so the README is honest — and this suite runs the
    visible tests exactly that way, which is what makes the claim checkable
    rather than a sentence in a file."""
    readme = repo_source("README.md")

    assert "Run the tests with `node --test`." in readme
    assert "no `package.json`, no\n`node_modules`" in readme
    assert visible_tests_pass(task())


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
    assert "monumental mason's yard" in t.prompt
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
