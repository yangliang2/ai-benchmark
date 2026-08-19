"""The language runner seam: one registry, one entry, and a grader that
reaches pytest only through it.

Round 7 admits a second language, and the per-language half of grading had to
become a named thing before it could. These tests hold the seam to what
`ai_benchmark.language_runners` says it is — six responsibilities answered by
the task's own declared `language` and by nothing an operator can pass — and
say the one thing this ticket's re-expression must not have done: move a
verdict. The Python runner's own behaviour is already covered by the grading
and forgery tests in `test_firstparty_v1.py`; nothing here re-states them.
"""

import inspect
from pathlib import Path

import pytest
from firstparty_v1_tasks import TASKS, solution_diff, task_by_id

from ai_benchmark.dataset import IngestError
from ai_benchmark import firstparty_v1
from ai_benchmark.firstparty_v1 import GRADE_TIMEOUT_S, grade, load_task_set
from ai_benchmark.language_runners import (
    PYTHON,
    RUNNERS,
    TYPESCRIPT,
    LanguageRunner,
    SourceUnreadable,
    runner_for,
)

FEATURE_SEED = "wordcount-top-words"


def test_the_registry_holds_exactly_the_languages_with_a_runner() -> None:
    """Two entries. A third language is a third entry here, and this test is
    what makes adding one a deliberate act rather than a side effect of some
    other change."""
    assert set(RUNNERS) == {"python", "typescript"}
    assert RUNNERS["python"] is PYTHON
    assert PYTHON.language == "python"
    assert RUNNERS["typescript"] is TYPESCRIPT
    assert TYPESCRIPT.language == "typescript"
    assert all(isinstance(runner, LanguageRunner) for runner in RUNNERS.values())


def test_a_task_selects_its_runner_by_its_own_declaration() -> None:
    """The key is the task's `language` and nothing an operator can pass: a
    task carries its own grading mechanism, so no flag can grade it with the
    wrong one."""
    task = task_by_id(FEATURE_SEED)

    assert task.language == "python"
    assert task.runner is PYTHON
    assert task.runner is runner_for(task.language)

    parameters = inspect.signature(grade).parameters
    assert set(parameters) == {"task", "diff", "timeout_s"}


def test_every_checked_in_task_has_a_registered_runner() -> None:
    """And the one its own declaration names — the registry is reached through
    the task and never around it. Every task declares one: `language` is
    required of a first-party v1 task, so there is no fallback to read here."""
    for task in load_task_set(TASKS):
        assert task.runner is RUNNERS[task.language]


def test_an_unregistered_language_has_no_runner_to_grade_it() -> None:
    """No unregistered language is silently graded as Python, and the refusal
    names the registered ones. `typescript` was this test's example until round
    7 registered it — which is the point: a language is graded when it has a
    runner and refused when it has none. That the refusal reaches an author
    *at load* is `test_firstparty_v1.py`'s to say."""
    with pytest.raises(IngestError, match="(?s)rust.*python.*typescript"):
        runner_for("rust")


def test_the_seam_answers_the_six_responsibilities() -> None:
    """The list in the module docstring, as members. A seventh responsibility
    creeping in is the failure this guards against: what a runner owns is a
    closed list, and everything else stays the grader's or harness-side."""
    assert PYTHON.grading_test_glob == "test_*.py"
    assert PYTHON.visible_test_glob == "test_*.py"
    assert PYTHON.source_glob == "*.py"

    owned = {name for name, _ in inspect.getmembers(PYTHON) if not name.startswith("_")}
    assert owned == {
        "language",
        "grading_test_glob",
        "visible_test_glob",
        "source_glob",
        "require_toolchain",
        "run_tests",
        "starting_repository_problem",
        "loads",
        "defined_symbols",
        "defined_classes",
    }


def test_the_grader_names_no_toolchain_of_its_own() -> None:
    """The rule the seam exists for: nothing outside the runner may reach
    grading through a path that assumes pytest. `firstparty_v1` still *talks*
    about pytest in prose, and the harness-side half really does run under it,
    but it must not invoke it."""
    source = Path(firstparty_v1.__file__).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    assert '"pytest"' not in code
    assert "-m\", \"pytest" not in code
    assert "junitxml" not in code


def test_the_grading_test_glob_is_the_runners_and_finds_what_it_used_to() -> None:
    task = task_by_id(FEATURE_SEED)

    assert task.grading_test_paths == tuple(
        sorted(
            str(path.relative_to(task.grading_dir))
            for path in task.grading_dir.rglob(PYTHON.grading_test_glob)
        )
    )
    assert task.grading_test_paths


def test_the_naming_invariant_is_the_runners_and_says_why() -> None:
    """Responsibility 5, and it stays the *Python* runner's: what a top-level
    name may not collide with is a fact about how that language resolves an
    import."""
    task = task_by_id(FEATURE_SEED)

    assert PYTHON.starting_repository_problem(task.repo_dir) is None


def test_the_naming_invariant_fires_on_a_shadowed_standard_library_name(
    tmp_path: Path,
) -> None:
    (tmp_path / "calendar.py").write_text("MONTHS = 12\n", encoding="utf-8")

    problem = PYTHON.starting_repository_problem(tmp_path)

    assert problem is not None
    assert "calendar.py" in problem
    assert "sys.path" in problem


def test_source_that_does_not_load_is_reported_in_the_seams_own_terms(
    tmp_path: Path,
) -> None:
    """Responsibility 6's third primitive. A caller in the grader asks the
    runner whether a file loads, and catches `SourceUnreadable` rather than a
    Python-only `SyntaxError`, because a second language's toolchain raises
    something else entirely."""
    assert PYTHON.loads("def total(): return 1\n")
    assert not PYTHON.loads("def total(:\n")

    with pytest.raises(SourceUnreadable):
        PYTHON.defined_symbols("def total(:\n")
    with pytest.raises(SourceUnreadable):
        PYTHON.defined_classes("class Basket(:\n")


def test_grading_still_reads_the_verdict_it_read_before() -> None:
    """The hard rule of the re-expression: no verdict moves. The reference
    solution resolves and the empty diff does not, through the seam."""
    task = task_by_id(FEATURE_SEED)

    assert grade(task, solution_diff(task), timeout_s=GRADE_TIMEOUT_S)
    assert not grade(task, "", timeout_s=GRADE_TIMEOUT_S)
