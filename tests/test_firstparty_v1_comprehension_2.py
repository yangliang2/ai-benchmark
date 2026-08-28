"""The round's remaining two locate-style `codebase-comprehension` tasks (#81).

The same question as #80 — "where is this behaviour handled?" — asked of two
more hand-authored repositories with **no defect in either of them**, and
asked about two kinds of behaviour the first two did not ask about. Ticket
18's pair asks where a decision is taken and where printed wording is put
together; these ask where an arithmetic lands and where an arrival is matched
to the record it belongs to:

- `coalround-where-the-monthly-figure-is-worked-out` asks where a **figure is
  arrived at**. `grades.price_of` says what a single sack of a kind fetches in
  a month and `Round.at` says what went in at a door; neither multiplies
  anything by anything, and `Statement.made_up` is where the sacks, the
  prices, the carriage, the allowance for empties and the least the yard will
  ask meet. The two narrow modules are the keyed rejects: both hold a piece of
  the arithmetic, and neither is where the figure is arrived at.
- `pigeonloft-where-a-timed-in-bird-is-matched` asks where a bird that came
  down is **matched** to the line it belongs against. `rings.same_bird` says
  only whether two writings of a ring number are the one bird and
  `Entries.for_race` says only what was put in for a race; neither holds one
  against the other, and `Book.belongs_to` is where a ring, a loft and the
  hours a race stands open settle which line a bird goes against. Those two
  are this task's rejects for the same reason.

Four repositories and four kinds of behaviour, deliberately: one repository
asked twice would make the second question's terrain the first question's
answer, and four questions of one kind would measure one reading four times.

This suite asserts what only these two tasks can assert, through a git-built
workdir diff and the same execution-verified pipeline a live run takes: the
reference solution resolves and the empty diff does not; **every** accepted
description level resolves; each rejected answer does not; a correct answer
that also edited the repository does not (the hash gate), while a scratch note
left beside it still does; and the repository holds neither an answer file nor
a copy of the key. It also reads the corpus's coverage table once, because
this ticket is where the category's cell fills up: four tasks, all
`application` and all `python`.

What is *not* asserted here is what the task-set lint owns for every task
carrying a key — the terrain rules (#65), the hash-gate digests (#67), the
canonical grading bytes and the discrimination negatives (#70), the existence
proof (#71). Those moved out of per-task suites on purpose.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    TASKS,
    run_for,
    solution_diff,
    task_by_id,
    visible_tests_pass,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    Task,
    answer_key,
    coverage_table,
    evaluate,
    grade,
    is_control,
    is_keyed,
    lint_task_set,
    load_task_set,
)

ANSWER_PATH = "ANSWER.json"

# Both keys, written out rather than read off disk, so that a key edited to say
# something else fails here and not silently. The accepted half is every
# description level legitimately correct for the behaviour asked about — the
# method, and the class enclosing it — and the rejected half is the plausible
# wrong place, which for this action is where a related but different behaviour
# lives rather than where a symptom points.
COALROUND = "coalround-where-the-monthly-figure-is-worked-out"
PIGEONLOFT = "pigeonloft-where-a-timed-in-bird-is-matched"

ACCEPTED = {
    COALROUND: (("statement.py", "Statement.made_up"), ("statement.py", "Statement")),
    PIGEONLOFT: (("clocking.py", "Book.belongs_to"), ("clocking.py", "Book")),
}
REJECTED = {
    COALROUND: (("grades.py", "price_of"), ("deliveries.py", "Round.at")),
    PIGEONLOFT: (("rings.py", "same_bird"), ("entries.py", "Entries.for_race")),
}
# A file of each repository an agent might tidy while reading it, and a tidy
# that leaves the repository's own tests green — so that what the hash gate
# refuses is visibly "you changed the code", not "you broke something".
TIDIED = {COALROUND: "grades.py", PIGEONLOFT: "rings.py"}

TASK_IDS = sorted(ACCEPTED)

# What the two tasks of #80 landed, read here only to say that these two are
# not those two: four repositories, four questions.
ALREADY_LANDED = (
    "boatyard-where-a-lift-out-is-refused",
    "bandstand-where-the-poster-is-worded",
)


def accepted_levels() -> list[tuple[str, tuple[str, str]]]:
    return [(task_id, where) for task_id in TASK_IDS for where in ACCEPTED[task_id]]


def rejected_answers() -> list[tuple[str, tuple[str, str]]]:
    return [(task_id, where) for task_id in TASK_IDS for where in REJECTED[task_id]]


def naming(file: str, symbol: str) -> str:
    return json.dumps({"file": file, "symbol": symbol}, indent=2) + "\n"


def answers(payload: str, *, at: str = ANSWER_PATH) -> Callable[[Path], None]:
    """The edit a run that wrote this answer file would log."""

    def write(workdir: Path) -> None:
        (workdir / at).write_text(payload, encoding="utf-8")

    return write


def resolves(task: Task, edit: Callable[[Path], None]) -> bool:
    """What the pipeline a real run replays through makes of this run."""
    return grade(task, workdir_diff(task, edit))


def modules(task: Task) -> list[str]:
    """The repository's own modules, as against the tests that measure them."""
    return sorted(
        path.name
        for path in task.repo_dir.glob("*.py")
        if not path.name.startswith("test_")
    )


# --- the key, as these two tasks write it ---------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_key_says_what_this_suite_says_it_says(task_id: str) -> None:
    key = answer_key(task_by_id(task_id))

    assert tuple((a.file, a.symbol) for a in key.accepted) == ACCEPTED[task_id]
    assert tuple((a.file, a.symbol) for a in key.rejected) == REJECTED[task_id]
    assert key.answer_path == ANSWER_PATH


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_rejected_half_names_a_file_the_accepted_half_does_not(
    task_id: str,
) -> None:
    """The near-miss no lint can invent. Asserted here as the authoring
    judgement it is — the lint refuses a rejected set confined to the accepted
    files, this says which files these two authors actually chose."""
    accepted_files = {file for file, _ in ACCEPTED[task_id]}
    rejected_files = {file for file, _ in REJECTED[task_id]}

    assert rejected_files.isdisjoint(accepted_files)
    assert len(rejected_files) == 2


# --- the verdict on each task's own terrain --------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_resolves_and_doing_nothing_does_not(task_id: str) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    assert {r.model: r.quality_value for r in records} == {
        "reference": 1.0, "empty": 0.0,
    }


@pytest.mark.parametrize(("task_id", "where"), accepted_levels())
def test_every_accepted_description_level_resolves(
    task_id: str, where: tuple[str, str]
) -> None:
    """The mitigation for this grading's one expensive assumption, paid for on
    real terrain: an agent that answers "the class that does it" has located
    the behaviour as surely as one that answers with the method, and the key
    says so."""
    task = task_by_id(task_id)

    assert resolves(task, answers(naming(*where)))


@pytest.mark.parametrize(("task_id", "where"), rejected_answers())
def test_each_rejected_answer_does_not_resolve(
    task_id: str, where: tuple[str, str]
) -> None:
    """Naming the module that supplies a piece of the answer — what one sack
    fetches, whether two numbers are the one bird — is where a reader who
    stopped early stops, and it is wrong."""
    task = task_by_id(task_id)

    assert not resolves(task, answers(naming(*where)))


# --- what the gate buys ----------------------------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_a_correct_answer_that_also_edited_the_repository_does_not_resolve(
    task_id: str,
) -> None:
    """These tasks are read against the ones that ask for an edit, so an agent
    that did edit work and then answered correctly must not grade resolved at
    answer-file cost. The prompt says so and the hash gate makes it binding."""
    task = task_by_id(task_id)
    correct = naming(*ACCEPTED[task_id][0])

    def answered_and_tidied(workdir: Path) -> None:
        answers(correct)(workdir)
        tidied = workdir / TIDIED[task_id]
        tidied.write_text(
            tidied.read_text(encoding="utf-8") + "\n# tidied while reading\n",
            encoding="utf-8",
        )

    assert resolves(task, answers(correct))
    assert not resolves(task, answered_and_tidied)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_a_note_left_beside_the_answer_still_resolves(task_id: str) -> None:
    """What the gate does not forbid is what a reader leaves behind: the task
    asks for the repository unchanged, not for a workdir nobody wrote in."""
    task = task_by_id(task_id)

    def answered_with_notes(workdir: Path) -> None:
        answers(naming(*ACCEPTED[task_id][0]))(workdir)
        (workdir / "notes.md").write_text("read every module\n", encoding="utf-8")

    assert resolves(task, answered_with_notes)


# --- the repository gives none of it away -----------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_repository_holds_no_answer_file_and_no_copy_of_the_key(
    task_id: str,
) -> None:
    task = task_by_id(task_id)

    assert (task.grading_dir / ANSWER_KEY_FILE).is_file()
    assert not (task.repo_dir / ANSWER_KEY_FILE).exists()
    assert not (task.repo_dir / ANSWER_PATH).exists()
    assert not any(path.name == ANSWER_KEY_FILE for path in task.repo_dir.rglob("*"))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_where_is_a_question_rather_than_a_formality(task_id: str) -> None:
    """At least two load-bearing modules, and the accepted answer in only one
    of them: a repository of one module answers "where" by having nowhere
    else."""
    task = task_by_id(task_id)
    accepted_files = {file for file, _ in ACCEPTED[task_id]}

    assert len(modules(task)) >= 2
    assert len(accepted_files) == 1
    assert accepted_files < set(modules(task))


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_nothing_in_the_repository_is_broken(task_id: str) -> None:
    """No planted defect: the ground truth here is where a behaviour is
    *correctly* implemented, and the repository's own tests say it is."""
    assert visible_tests_pass(task_by_id(task_id))


def test_the_four_comprehension_tasks_are_four_repositories() -> None:
    """Not one repository asked four times, and not these two asked what the
    first two were asked: the terrain of each question is another question's
    answer as soon as two of them share a repository."""
    tasks = [task_by_id(task_id) for task_id in (*TASK_IDS, *ALREADY_LANDED)]

    seen: set[str] = set()
    for task in tasks:
        assert seen.isdisjoint(modules(task))
        seen |= set(modules(task))
    assert len({task.prompt for task in tasks}) == len(tasks)


# --- the declarations --------------------------------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_is_declared_as_designed(task_id: str) -> None:
    task = task_by_id(task_id)

    assert task.category == "codebase-comprehension"
    assert is_keyed(task)
    assert is_control(task) and task.construction is None
    assert task.surface == "application"
    assert task.language == "python"
    assert task.grading.behaviour_tests == ()
    assert ANSWER_PATH in task.prompt


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_asks_where_and_says_the_repository_is_to_be_left_alone(
    task_id: str,
) -> None:
    prompt = task_by_id(task_id).prompt

    assert "Where in this repository is that" in prompt
    assert "leave it precisely as you found it" in prompt
    assert "graded unresolved" in prompt


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    """Single-file: the reference solution is the pristine tree plus the answer
    file, so the diff a solved run logs touches exactly one path."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {ANSWER_PATH}
    assert task.scale == "single-file"


def test_the_category_cell_counts_two_shapes_in_one_row() -> None:
    """What the ticket asked to be checked before it closed, caught up as the
    row moved: the coverage table `ai-bench lint-v1` prints still holds one
    `codebase-comprehension` row, and since round 12's first explain-style
    task it counts five tasks of two shapes — this round's four locate-style
    tasks on an accepted-answer key, and the point-keyed explain shape beside
    them (§106.2)."""
    comprehension = [
        row for row in coverage_table(load_task_set(TASKS))
        if row[0] == "codebase-comprehension"
    ]

    assert comprehension == [("codebase-comprehension", "application", "python", 5)]


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_lints_clean(task_id: str) -> None:
    assert lint_task_set([task_by_id(task_id)]) == []
