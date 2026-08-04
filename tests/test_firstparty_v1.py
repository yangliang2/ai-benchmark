"""Dataset-seam tests for first-party v1: the checked-in task set plus a raw
run log carrying workdir diffs in, execution-verified records out.

Diffs are built the way the live runner (#11) will build them — copy the
pristine repo, git init + commit, edit, `git add -A && git diff --cached` —
so the grader is exercised against genuine patches (added, modified and
deleted files), not hand-written hunks that could drift from git's output.
"""

import json
import shutil
import subprocess
import tempfile
import textwrap
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
import yaml
from conftest import FakeClaude

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import load_runs as load_v0_runs
from ai_benchmark.firstparty import local_today
from ai_benchmark.firstparty_v1 import (
    BENCHMARK,
    Run,
    Task,
    evaluate,
    lint_task_set,
    load_runs,
    load_task_set,
    run_live,
)

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v1"

FEATURE_SEED = "wordcount-top-words"
REFACTOR_SEED = "ledger-split-formatting"


def clone_seed(root: Path, seed: str, task_id: str) -> Path:
    """Copy a seed task into root under a new id, ready to be broken."""
    destination = root / task_id
    shutil.copytree(TASKS / seed, destination)
    return destination


def retitle(task_dir: Path, **fields: object) -> None:
    """Rewrite fields of a cloned task's task.yaml in place."""
    spec = yaml.safe_load((task_dir / "task.yaml").read_text())
    spec.update(fields)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))


def workdir_diff(task: Task, edit: Callable[[Path], None]) -> str:
    """The diff a run would log: pristine repo, edited, captured against the
    initial commit exactly as the live runner will capture it."""
    git = ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval"]
    with tempfile.TemporaryDirectory(prefix="ai-bench-test-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        subprocess.run([*git, "init", "-q", "."], cwd=workdir, check=True)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        subprocess.run([*git, "commit", "-qm", "pristine"], cwd=workdir, check=True)
        edit(workdir)
        subprocess.run([*git, "add", "-A"], cwd=workdir, check=True)
        return subprocess.run(
            [*git, "diff", "--cached"], cwd=workdir, capture_output=True, text=True,
            check=True,
        ).stdout


def run_for(task: Task, diff: str, *, model: str = "claude-sonnet-5") -> Run:
    """A raw run-log row for one task, carrying the workdir diff it produced."""
    return Run(
        task_id=task.id,
        agent="claude-code",
        agent_version="2.1.220",
        model=model,
        output="done",
        diff=diff,
        tokens_in=41000,
        tokens_out=1500,
        cost_usd=0.21,
        latency_s=64.5,
        turns=7,
        as_of=date(2026, 8, 4),
    )


def task_by_id(task_id: str) -> Task:
    [task] = [t for t in load_task_set(TASKS) if t.id == task_id]
    return task


def append(path: Path, source: str) -> None:
    path.write_text(path.read_text() + textwrap.dedent(source))


# --- what a solving and a failing agent do to each seed task -------------------


def solve_wordcount(workdir: Path) -> None:
    append(workdir / "wordcount.py", '''
        def top_words(text, n):
            """The n most frequent words, most frequent first, ties alphabetical."""
            counts = word_counts(text)
            ordered = sorted(counts, key=lambda word: (-counts[word], word))
            return ordered[:n]
        ''')


def half_solve_wordcount(workdir: Path) -> None:
    """Frequency right, tie-break forgotten — the common near-miss."""
    append(workdir / "wordcount.py", '''
        def top_words(text, n):
            counts = word_counts(text)
            return sorted(counts, key=lambda word: -counts[word])[:n]
        ''')


def solve_wordcount_across_files(workdir: Path) -> None:
    """A cross-file solution: one file modified, one added, one deleted."""
    (workdir / "ordering.py").write_text(textwrap.dedent('''
        """Ordering helpers for word counts."""


        def by_frequency(counts):
            """Words most frequent first, ties broken alphabetically."""
            return sorted(counts, key=lambda word: (-counts[word], word))
        '''))
    append(workdir / "wordcount.py", '''
        from ordering import by_frequency


        def top_words(text, n):
            """The n most frequent words, most frequent first."""
            return by_frequency(word_counts(text))[:n]
        ''')
    (workdir / "README.md").unlink()


def solve_ledger(workdir: Path) -> None:
    (workdir / "formatting.py").write_text(textwrap.dedent('''
        """Money formatting for the ledger."""


        def format_amount(cents):
            """Render an integer number of cents as a signed currency string."""
            sign = "-" if cents < 0 else ""
            whole, remainder = divmod(abs(cents), 100)
            return f"{sign}${whole}.{remainder:02d}"


        def format_line(description, cents):
            """Render one ledger line as "<description>: <amount>"."""
            return f"{description}: {format_amount(cents)}"
        '''))
    (workdir / "ledger.py").write_text(textwrap.dedent('''
        """A tiny expense ledger."""

        from formatting import format_line


        class Ledger:
            """An ordered list of (description, cents) entries."""

            def __init__(self):
                self.entries = []

            def add(self, description, cents):
                """Append one entry."""
                self.entries.append((description, cents))

            def total(self):
                """The sum of every entry's amount, in cents."""
                return sum(cents for _, cents in self.entries)

            def render(self):
                """Render every entry, then a total line."""
                lines = [format_line(d, c) for d, c in self.entries]
                lines.append(format_line("total", self.total()))
                return "\\n".join(lines)
        '''))


def fake_solve_ledger(workdir: Path) -> None:
    """formatting.py exists and imports cleanly, but nothing actually moved."""
    (workdir / "formatting.py").write_text(
        "from ledger import format_amount, format_line  # noqa: F401\n"
    )


def overwrite_the_grading_tests(workdir: Path) -> None:
    """An agent that writes its own tests at the grading files' paths."""
    for name in ("test_formatting_module.py", "test_ledger_behaviour.py"):
        (workdir / name).write_text("def test_everything_is_fine():\n    assert True\n")


def forge_exit_status_via_conftest(workdir: Path) -> None:
    """No work done; a conftest hook rewrites pytest's exit status to 0."""
    (workdir / "conftest.py").write_text(
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    session.exitstatus = 0\n"
    )


def inject_the_missing_symbol_via_conftest(workdir: Path) -> None:
    """No work done; a conftest defines the wanted function at collection."""
    (workdir / "conftest.py").write_text(
        "import wordcount\n"
        "wordcount.top_words = lambda text, n: sorted(\n"
        "    wordcount.word_counts(text),\n"
        "    key=lambda word: (-wordcount.word_counts(text)[word], word))[:n]\n"
    )


def forge_exit_status_via_pyproject(workdir: Path) -> None:
    """No work done; a config file's addopts loads a plugin that forges the
    exit status. pytest.ini, tox.ini and setup.cfg are the same vector."""
    (workdir / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-p forge"\n'
    )
    (workdir / "forge.py").write_text(
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    session.exitstatus = 0\n"
    )


def synthetic_task(root: Path) -> Task:
    """A task whose grading oracle is a stdlib import.

    The two shipped seeds happen not to be exploitable this way; the 18 tasks
    #12/#13 will author are the reason the class has to be closed, so the
    attack is proven against the shape those will have.
    """
    task_dir = root / "exact-ratio"
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "grading").mkdir()
    (task_dir / "task.yaml").write_text(textwrap.dedent("""\
        id: exact-ratio
        category: feature-dev
        scale: single-file
        language: python
        prompt: |
          Add ratio(a, b) to calc.py, returning a / b as an exact fraction.
        """))
    (task_dir / "repo" / "calc.py").write_text("def half(x):\n    return x / 2\n")
    (task_dir / "grading" / "test_ratio.py").write_text(textwrap.dedent("""\
        from fractions import Fraction

        from calc import ratio


        def test_ratio_is_exact():
            assert ratio(1, 3) == Fraction(1, 3)
        """))
    [task] = load_task_set(root)
    return task


def solve_exact_ratio(workdir: Path) -> None:
    append(workdir / "calc.py", """
        from fractions import Fraction


        def ratio(a, b):
            return Fraction(a, b)
        """)


def shadow_the_oracle(workdir: Path) -> None:
    """Implements ratio wrongly, then replaces the standard-library module the
    grading test measures it against."""
    append(workdir / "calc.py", """
        def ratio(a, b):
            return "not a fraction at all"
        """)
    (workdir / "fractions.py").write_text(textwrap.dedent("""\
        class Fraction:
            def __init__(self, *args):
                pass

            def __eq__(self, other):
                return True
        """))


def forge_success_by_exiting(workdir: Path) -> None:
    """No work done; the repo module kills the process with a zero status the
    moment the grading test imports it."""
    (workdir / "calc.py").write_text(
        "import os\n\nos._exit(0)\n\n\ndef half(x):\n    return x / 2\n"
    )


def solve_wordcount_and_leave_a_broken_conftest(workdir: Path) -> None:
    """A real solution plus a plausible honest artefact: a leftover conftest
    importing a helper the agent decided not to ship."""
    solve_wordcount(workdir)
    (workdir / "conftest.py").write_text("from helpers import fixture_text  # noqa\n")


# --- task format and loader ---------------------------------------------------


def test_task_set_loads_one_classified_task_per_seed_category() -> None:
    tasks = load_task_set(TASKS)

    assert {task.category for task in tasks} == {"feature-dev", "refactor"}
    assert len({task.id for task in tasks}) == len(tasks)
    for task in tasks:
        assert task.category != "unclassified"
        assert task.language == "python"
        assert list(task.repo_dir.iterdir())
        assert list(task.grading_dir.rglob("test_*.py"))


def test_refactor_task_names_its_behaviour_tests() -> None:
    [refactor] = [t for t in load_task_set(TASKS) if t.category == "refactor"]

    assert refactor.grading.behaviour_tests
    for name in refactor.grading.behaviour_tests:
        assert (refactor.grading_dir / name).exists()
    # Something is left over to assert the restructuring actually happened.
    assert set(refactor.grading_test_paths) > set(refactor.behaviour_test_paths)


def test_a_task_id_must_match_its_directory_name(tmp_path: Path) -> None:
    """Which is also what makes duplicate ids unexpressible: the two clones
    below cannot both answer to the seed's id, because the filesystem already
    refuses to give two directories the same name."""
    clone_seed(tmp_path, FEATURE_SEED, "one")
    clone_seed(tmp_path, FEATURE_SEED, "two")  # both keep the seed's id

    with pytest.raises(IngestError, match="directory name"):
        load_task_set(tmp_path)


def test_malformed_task_yaml_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    retitle(task_dir, category="not-a-category")

    with pytest.raises(IngestError, match="category"):
        load_task_set(tmp_path)


def test_unclassified_task_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    retitle(task_dir, category="unclassified")

    with pytest.raises(IngestError, match="unclassified"):
        load_task_set(tmp_path)


def test_task_without_grading_tests_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    for path in task_dir.glob("grading/test_*.py"):
        path.unlink()

    with pytest.raises(IngestError, match="grading"):
        load_task_set(tmp_path)


def test_task_without_a_starting_repo_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    shutil.rmtree(task_dir / "repo")

    with pytest.raises(IngestError, match="repo"):
        load_task_set(tmp_path)


def test_a_repo_module_named_after_the_stdlib_fails_loudly(tmp_path: Path) -> None:
    """Grading keeps the standard library ahead of the workdir on sys.path, so
    such a module is invisible at grade time. Caught here because the lint
    cannot catch it: when the stdlib module does not happen to satisfy the
    grading tests, the task fails pristine like any good task and is also
    impossible to solve — it would just grade every agent unresolved."""
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    (task_dir / "repo" / "calendar.py").write_text("MONTHS = 12\n")

    with pytest.raises(IngestError, match="calendar.py"):
        load_task_set(tmp_path)


def test_a_repo_package_named_after_the_stdlib_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    (task_dir / "repo" / "json").mkdir()
    (task_dir / "repo" / "json" / "__init__.py").write_text("")

    with pytest.raises(IngestError, match="json"):
        load_task_set(tmp_path)


def test_a_task_shipping_its_own_gitignore_fails_loudly(tmp_path: Path) -> None:
    """The live runner owns the workdir's .gitignore and would silently
    replace a task-shipped one — the agent would then work in a repository
    that differs from the pristine one grading applies the diff to."""
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    (task_dir / "repo" / ".gitignore").write_text("*.tmp\n")

    with pytest.raises(IngestError, match="gitignore"):
        load_task_set(tmp_path)


def test_refactor_task_without_behaviour_tests_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, REFACTOR_SEED, REFACTOR_SEED)
    retitle(task_dir, grading={"behaviour_tests": []})

    with pytest.raises(IngestError, match="behaviour"):
        load_task_set(tmp_path)


def test_behaviour_test_naming_a_missing_file_fails_loudly(tmp_path: Path) -> None:
    task_dir = clone_seed(tmp_path, REFACTOR_SEED, REFACTOR_SEED)
    retitle(task_dir, grading={"behaviour_tests": ["test_nowhere.py"]})

    with pytest.raises(IngestError, match="test_nowhere.py"):
        load_task_set(tmp_path)


def test_feature_dev_task_naming_behaviour_tests_fails_loudly(tmp_path: Path) -> None:
    """Only refactor tasks split their suite; anywhere else the split would
    quietly exempt those files from the must-fail-pristine invariant."""
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    retitle(task_dir, grading={"behaviour_tests": ["test_top_words.py"]})

    with pytest.raises(IngestError, match="behaviour"):
        load_task_set(tmp_path)


# --- execution-verified grading ------------------------------------------------


def test_solved_and_unsolved_runs_of_both_seed_tasks_are_graded_by_execution() -> None:
    tasks = load_task_set(TASKS)
    wordcount, ledger = task_by_id(FEATURE_SEED), task_by_id(REFACTOR_SEED)
    runs = [
        run_for(wordcount, workdir_diff(wordcount, solve_wordcount)),
        run_for(wordcount, workdir_diff(wordcount, half_solve_wordcount),
                model="claude-haiku-4-5"),
        run_for(ledger, workdir_diff(ledger, solve_ledger)),
        run_for(ledger, workdir_diff(ledger, fake_solve_ledger),
                model="claude-haiku-4-5"),
    ]

    records = evaluate(tasks, runs, source="run-log")

    graded = {(r.instance_id, r.model): r.quality_value for r in records}
    assert graded[(FEATURE_SEED, "claude-sonnet-5")] == 1.0
    assert graded[(FEATURE_SEED, "claude-haiku-4-5")] == 0.0
    assert graded[(REFACTOR_SEED, "claude-sonnet-5")] == 1.0
    # formatting.py imports cleanly, but ledger.py still defines the helpers.
    assert graded[(REFACTOR_SEED, "claude-haiku-4-5")] == 0.0


def test_an_empty_diff_leaves_the_task_unresolved() -> None:
    wordcount = task_by_id(FEATURE_SEED)

    [record] = evaluate([wordcount], [run_for(wordcount, "")], source="run-log")

    assert record.quality_value == 0.0


def test_agent_edits_to_grading_test_files_have_no_effect() -> None:
    """The canonical grading files overwrite same-path files in the workdir,
    so rewriting them buys an agent nothing."""
    ledger = task_by_id(REFACTOR_SEED)
    tampered = workdir_diff(ledger, overwrite_the_grading_tests)
    assert "test_formatting_module.py" in tampered  # the tamper really is in the diff

    [record] = evaluate([ledger], [run_for(ledger, tampered)], source="run-log")

    assert record.quality_value == 0.0


def test_a_conftest_cannot_forge_the_exit_status() -> None:
    """The verdict comes from the held-out tests, never from agent-authored
    pytest configuration — a conftest hook must not be able to force a pass."""
    wordcount = task_by_id(FEATURE_SEED)
    diff = workdir_diff(wordcount, forge_exit_status_via_conftest)

    [record] = evaluate([wordcount], [run_for(wordcount, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_a_conftest_cannot_define_the_work_away() -> None:
    wordcount = task_by_id(FEATURE_SEED)
    diff = workdir_diff(wordcount, inject_the_missing_symbol_via_conftest)

    [record] = evaluate([wordcount], [run_for(wordcount, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_a_config_file_cannot_smuggle_in_addopts() -> None:
    """pyproject.toml here; pytest.ini, tox.ini and setup.cfg are the same
    vector, all shut off by pinning the config file grading runs under."""
    wordcount = task_by_id(FEATURE_SEED)
    diff = workdir_diff(wordcount, forge_exit_status_via_pyproject)

    [record] = evaluate([wordcount], [run_for(wordcount, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_a_stray_broken_conftest_does_not_sink_a_correct_solution() -> None:
    """The false-negative direction of the same rule: agent-authored pytest
    configuration is ignored, so a leftover conftest cannot cost a real fix."""
    wordcount = task_by_id(FEATURE_SEED)
    diff = workdir_diff(wordcount, solve_wordcount_and_leave_a_broken_conftest)

    [record] = evaluate([wordcount], [run_for(wordcount, diff)], source="run-log")

    assert record.quality_value == 1.0


def test_a_shadowed_stdlib_module_cannot_become_the_oracle(tmp_path: Path) -> None:
    """The workdir must not precede the standard library on sys.path: a task
    whose grading test measures against a stdlib type is otherwise graded by a
    module the agent wrote."""
    task = synthetic_task(tmp_path)
    assert lint_task_set([task]) == []  # a well-formed task, not a broken one
    diff = workdir_diff(task, shadow_the_oracle)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_a_task_repo_module_is_still_importable(tmp_path: Path) -> None:
    """The control for the rule above: keeping the workdir behind the standard
    library must not stop the grading tests importing what they are grading."""
    task = synthetic_task(tmp_path)
    diff = workdir_diff(task, solve_exact_ratio)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


def test_agent_code_cannot_short_circuit_the_test_run(tmp_path: Path) -> None:
    """Exit status alone is not evidence of a pass: agent code runs during
    collection, and one os._exit(0) there looks exactly like a clean run."""
    task = synthetic_task(tmp_path)
    diff = workdir_diff(task, forge_success_by_exiting)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


def test_a_diff_that_adds_modifies_and_deletes_files_applies_in_full() -> None:
    """Every hunk kind reaches the graded copy — a hunk git could not apply
    fails loudly rather than scoring 0.0, so a resolved verdict here means the
    whole patch landed."""
    wordcount = task_by_id(FEATURE_SEED)
    diff = workdir_diff(wordcount, solve_wordcount_across_files)
    assert "new file mode" in diff and "deleted file mode" in diff

    [record] = evaluate([wordcount], [run_for(wordcount, diff)], source="run-log")

    assert record.quality_value == 1.0


def test_a_diff_that_does_not_apply_fails_loudly() -> None:
    wordcount = task_by_id(FEATURE_SEED)
    corrupt = workdir_diff(wordcount, solve_wordcount).replace("wordcount.py", "gone.py")

    with pytest.raises(IngestError, match="diff"):
        evaluate([wordcount], [run_for(wordcount, corrupt)], source="run-log")


def test_grading_patches_only_its_own_temp_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """git apply walks up to the enclosing repository, so a temp dir that
    happens to sit inside one must not let a logged diff escape into it."""
    enclosing = tmp_path / "enclosing-repo"
    (enclosing / "tmp").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "."], cwd=enclosing, check=True)
    (enclosing / "wordcount.py").write_text("sentinel\n")
    monkeypatch.setattr(tempfile, "tempdir", str(enclosing / "tmp"))
    wordcount = task_by_id(FEATURE_SEED)

    [record] = evaluate(
        [wordcount],
        [run_for(wordcount, workdir_diff(wordcount, solve_wordcount))],
        source="run-log",
    )

    assert record.quality_value == 1.0
    assert (enclosing / "wordcount.py").read_text() == "sentinel\n"


def test_grading_that_never_finishes_is_unresolved_not_a_hang() -> None:
    wordcount = task_by_id(FEATURE_SEED)

    def loop_forever(workdir: Path) -> None:
        append(workdir / "wordcount.py", """
            while True:
                pass
            """)

    [record] = evaluate(
        [wordcount], [run_for(wordcount, workdir_diff(wordcount, loop_forever))],
        source="run-log", timeout_s=5,
    )

    assert record.quality_value == 0.0


# --- records at the unified-dataset seam ---------------------------------------


def test_records_carry_v1_benchmark_and_first_party_provenance() -> None:
    ledger = task_by_id(REFACTOR_SEED)

    [record] = evaluate(
        [ledger],
        [run_for(ledger, workdir_diff(ledger, solve_ledger))],
        source="data/first-party-v1-runs/2026-08-04.jsonl",
    )

    assert record.benchmark == BENCHMARK == "first-party-v1"
    assert record.source_type == "first-party"
    assert record.confidence == "high"
    assert record.instance_id == REFACTOR_SEED
    assert record.quality_metric == "resolved"
    assert record.category == "refactor"
    assert record.scale == "cross-file"
    assert record.language == "python"
    assert record.agent == "claude-code" and record.agent_version == "2.1.220"
    assert (record.tokens_in, record.tokens_out) == (41000, 1500)
    assert (record.cost_usd, record.latency_s, record.turns) == (0.21, 64.5, 7)
    assert record.as_of == date(2026, 8, 4)


def test_run_for_an_unknown_task_fails_loudly() -> None:
    wordcount = task_by_id(FEATURE_SEED)
    orphan = run_for(wordcount, "").model_copy(update={"task_id": "no-such-task"})

    with pytest.raises(IngestError, match="no-such-task"):
        evaluate([wordcount], [orphan], source="run-log")


def test_the_checked_in_run_log_carries_a_diff_per_run(
    firstparty_v1_fixture: Path,
) -> None:
    runs = load_runs(firstparty_v1_fixture)

    assert len(runs) == 4
    assert all(run.diff.startswith("diff --git") for run in runs)


def test_a_malformed_run_log_fails_loudly(tmp_path: Path) -> None:
    log = tmp_path / "runs.jsonl"
    log.write_text('{"task_id": "wordcount-top-words", "agent": "claude-code"}\n')

    with pytest.raises(IngestError, match="diff"):
        load_runs(log)


def test_duplicate_runs_fail_loudly() -> None:
    wordcount = task_by_id(FEATURE_SEED)
    run = run_for(wordcount, "")

    with pytest.raises(IngestError, match="duplicate"):
        evaluate([wordcount], [run, run], source="run-log")


# --- task-set lint: the authoring invariants, checked by running them ----------


def test_the_seed_tasks_pass_the_lint() -> None:
    assert lint_task_set(load_task_set(TASKS)) == []


def test_lint_rejects_a_feature_dev_task_that_is_already_solved(
    tmp_path: Path,
) -> None:
    task_dir = clone_seed(tmp_path, FEATURE_SEED, FEATURE_SEED)
    solve_wordcount(task_dir / "repo")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert FEATURE_SEED in problem and "pristine" in problem


def test_lint_rejects_a_refactor_task_whose_behaviour_is_already_broken(
    tmp_path: Path,
) -> None:
    task_dir = clone_seed(tmp_path, REFACTOR_SEED, REFACTOR_SEED)
    ledger = task_dir / "repo" / "ledger.py"
    ledger.write_text(ledger.read_text().replace('sign = "-" if cents < 0 else ""',
                                                 'sign = ""'))

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert REFACTOR_SEED in problem and "behaviour" in problem


def test_lint_rejects_a_refactor_task_that_is_already_restructured(
    tmp_path: Path,
) -> None:
    """The structural assertions must fail pristine too, or the task is done."""
    task_dir = clone_seed(tmp_path, REFACTOR_SEED, REFACTOR_SEED)
    solve_ledger(task_dir / "repo")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert REFACTOR_SEED in problem and "pristine" in problem


# --- live runner: tools-enabled claude-code, workdir diff into the run log -----


# What the fake agent appends to wordcount.py when it solves the seed task.
SOLUTION = (
    "\n\ndef top_words(text, n):\n"
    "    counts = word_counts(text)\n"
    "    return sorted(counts, key=lambda w: (-counts[w], w))[:n]\n"
)

# Every act also leaves the droppings a real agent leaves after running the
# repo's tests in its workdir: bytecode caches (binary!) and pytest state.
PYTEST_DROPPINGS = """\
(workdir / "__pycache__").mkdir(exist_ok=True)
(workdir / "__pycache__" / "wordcount.cpython-313.pyc").write_bytes(bytes(range(256)))
(workdir / ".pytest_cache").mkdir(exist_ok=True)
(workdir / ".pytest_cache" / "lastfailed").write_text("busted")
"""

SOLVE_AS_SONNET_ACT = f"""\
if model == "claude-sonnet-5":
    with open(workdir / "wordcount.py", "a") as source:
        source.write({SOLUTION!r})
{PYTEST_DROPPINGS}"""

# A cross-file solution whose new file is what a hostile ignore rule would
# silently drop: the tests for capture completeness hinge on ordering.py
# being an *added* file, not an edit to a tracked one.
NEW_FILE_SOLUTION = (
    "\n\nfrom ordering import by_frequency\n\n\n"
    "def top_words(text, n):\n"
    "    return by_frequency(word_counts(text))[:n]\n"
)
ORDERING_MODULE = (
    '"""Ordering helpers for word counts."""\n\n\n'
    "def by_frequency(counts):\n"
    "    return sorted(counts, key=lambda word: (-counts[word], word))\n"
)

SOLVE_WITH_NEW_FILE_ACT = f"""\
with open(workdir / "wordcount.py", "a") as source:
    source.write({NEW_FILE_SOLUTION!r})
(workdir / "ordering.py").write_text({ORDERING_MODULE!r})
"""


def test_live_runs_append_replayable_rows_with_exact_measurements(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """The whole live loop against a faked CLI: sonnet solves, haiku changes
    nothing, both run pytest and litter the workdir — and every row lands in
    the log with the CLI's own measurements and a diff that replays."""
    fake_claude(SOLVE_AS_SONNET_ACT)
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    runs = run_live([wordcount], ["claude-sonnet-5", "claude-haiku-4-5"], log)

    assert load_runs(log) == runs
    sonnet, haiku = runs
    assert (sonnet.model, haiku.model) == ("claude-sonnet-5", "claude-haiku-4-5")
    for run in runs:
        assert run.task_id == FEATURE_SEED
        assert run.agent == "claude-code"
        assert run.agent_version == "2.1.220 (Claude Code)"
        assert run.output == "done"
        # Exact CLI-reported measurements, tokens_in summed over cache tiers.
        assert run.tokens_in == 12 + 30000 + 11000
        assert run.tokens_out == 900
        assert run.cost_usd == 0.19
        assert run.latency_s == 42.5
        assert run.turns == 6
        assert run.as_of == local_today()
        # The test droppings never reach the graded artifact.
        assert "__pycache__" not in run.diff
        assert ".pytest_cache" not in run.diff
        assert ".gitignore" not in run.diff
    assert haiku.diff == ""  # ran pytest, changed nothing

    records = evaluate([wordcount], runs, source=str(log))

    graded = {record.model: record.quality_value for record in records}
    # A run that changed nothing is unresolved, not an error.
    assert graded == {"claude-sonnet-5": 1.0, "claude-haiku-4-5": 0.0}


def test_live_runs_grant_edits_and_bash_but_not_setting_sources(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """v1 runs are genuinely multi-turn: tools stay on (no --tools ""), and —
    because headless runs auto-deny whatever was not granted up front, while
    --setting-sources "" discards any user-level grants — the runner must
    itself grant file edits and shell commands, or the agent is billed in
    full and every edit is denied. Probed against the real CLI: acceptEdits
    alone still denies Bash, so both flags are load-bearing."""
    argv_log = fake_claude("")
    wordcount = task_by_id(FEATURE_SEED)

    run_live([wordcount], ["claude-sonnet-5"], tmp_path / "runs.jsonl")

    [argv] = [json.loads(line) for line in argv_log.read_text().splitlines()]
    assert "--tools" not in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert argv[argv.index("--allowedTools") + 1] == "Bash"
    assert argv[argv.index("-p") + 1] == wordcount.prompt


def test_a_run_the_environment_blocked_fails_loudly_not_as_a_verdict(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """A payload reporting permission denials means the harness, not the
    model, decided the outcome — logging it would grade the environment.
    The row is not written: a blocked run is a broken run, not a 0.0."""
    fake_claude(
        SOLVE_AS_SONNET_ACT
        + 'denials.append({"tool_name": "Bash",'
        ' "tool_use_id": "toolu_01Xy",'
        ' "tool_input": {"command": "pytest -q"}})\n'
    )
    log = tmp_path / "runs.jsonl"

    with pytest.raises(IngestError, match="Bash"):
        run_live([task_by_id(FEATURE_SEED)], ["claude-sonnet-5"], log)

    assert load_runs(log) == []


def test_capture_is_immune_to_hostile_operator_git_config(
    fake_claude: FakeClaude, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The graded artifact must not vary with the operator's machine:
    diff.noprefix strips the a/ b/ prefixes replay's git apply expects
    (silent at capture, explodes at grading), and core.excludesFile silently
    drops agent-written files from the diff. Both neutralised."""
    excludes = tmp_path / "hostile-excludes"
    excludes.write_text("*.py\n")
    hostile = tmp_path / "hostile-gitconfig"
    hostile.write_text(
        f"[diff]\n\tnoprefix = true\n[core]\n\texcludesFile = {excludes}\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(hostile))
    fake_claude(SOLVE_WITH_NEW_FILE_ACT)
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert "diff --git a/" in run.diff  # noprefix did not shape the artifact
    assert "ordering.py" in run.diff  # excludesFile did not drop the new file
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_an_agent_file_that_is_not_utf8_fails_loudly(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """Latin-1 text has no NUL bytes, so git diffs it as text and the capture
    cannot decode it. v1 run logs are UTF-8 JSON; rather than logging a row
    that cannot round-trip, the run fails loudly and attributably."""
    fake_claude(r'(workdir / "notes.txt").write_bytes(b"caf\xe9\n")' + "\n")

    with pytest.raises(IngestError, match="UTF-8"):
        run_live(
            [task_by_id(FEATURE_SEED)], ["claude-sonnet-5"],
            tmp_path / "runs.jsonl",
        )


def test_a_file_the_agent_deleted_is_captured_and_applies_at_replay(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    fake_claude(SOLVE_AS_SONNET_ACT + '(workdir / "README.md").unlink()\n')
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert "deleted file mode" in run.diff
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_edits_the_agent_committed_mid_run_are_still_captured(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """The capture diffs against the recorded initial commit, not HEAD: an
    agent that commits part-way and keeps editing loses nothing."""
    fake_claude(
        SOLVE_AS_SONNET_ACT
        + "import subprocess\n"
        + 'agent_git = ["git", "-c", "user.email=agent@x", "-c",'
        ' "user.name=agent"]\n'
        + 'subprocess.run([*agent_git, "add", "-A"], check=True)\n'
        + 'subprocess.run([*agent_git, "commit", "-qm", "wip"], check=True)\n'
        + '(workdir / "notes.md").write_text("still experimenting")\n'
    )
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert "top_words" in run.diff  # the committed edit
    assert "notes.md" in run.diff  # the edit after the commit
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_an_agent_modified_ignore_file_is_neutralised(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """Appending *.py to the runner's .gitignore would silently drop an added
    solution file from the capture; the restore before staging prevents it."""
    fake_claude(
        'with open(workdir / ".gitignore", "a") as ignore:\n'
        '    ignore.write("*.py\\n")\n'
        + SOLVE_WITH_NEW_FILE_ACT
    )
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert ".gitignore" not in run.diff
    assert "ordering.py" in run.diff
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_a_sweep_that_dies_mid_way_keeps_the_rows_already_paid_for(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    fake_claude(
        SOLVE_AS_SONNET_ACT
        + 'if model == "claude-haiku-4-5":\n'
        + '    print("overloaded", file=sys.stderr)\n'
        + "    raise SystemExit(3)\n"
    )
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    with pytest.raises(IngestError, match="claude exited 3"):
        run_live([wordcount], ["claude-sonnet-5", "claude-haiku-4-5"], log)

    [row] = load_runs(log)
    assert row.model == "claude-sonnet-5"
    assert "top_words" in row.diff


def test_run_live_refuses_to_overwrite_an_existing_log(tmp_path: Path) -> None:
    log = tmp_path / "runs.jsonl"
    log.write_text("")

    with pytest.raises(IngestError, match="already exists"):
        run_live([task_by_id(FEATURE_SEED)], ["claude-sonnet-5"], log)


def test_a_live_run_that_exceeds_the_timeout_fails_loudly(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    fake_claude("time.sleep(30)\n")

    with pytest.raises(IngestError, match="timed out after 1s"):
        run_live(
            [task_by_id(FEATURE_SEED)], ["claude-sonnet-5"],
            tmp_path / "runs.jsonl", timeout_s=1,
        )


def test_an_agent_authored_binary_file_survives_capture_and_replay(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """Caches are excluded by name, not by being binary: a binary file the
    agent deliberately wrote is captured with --binary, so the logged diff
    still applies at replay instead of aborting evaluation as unapplyable."""
    fake_claude(
        SOLVE_AS_SONNET_ACT
        + r'(workdir / "golden.bin").write_bytes(b"\x00\xff" * 16)' + "\n"
    )
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert "GIT binary patch" in run.diff
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_the_runner_owns_the_ignore_file_even_if_the_agent_deletes_it(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """Deleting the runner's .gitignore must neither let cache files into the
    diff nor log a .gitignore deletion that cannot apply to the pristine repo."""
    fake_claude(
        '(workdir / ".gitignore").unlink()\n' + SOLVE_AS_SONNET_ACT
    )
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log)

    assert ".gitignore" not in run.diff
    assert "__pycache__" not in run.diff
    [record] = evaluate([wordcount], [run], source=str(log))
    assert record.quality_value == 1.0


def test_v0_and_v1_run_logs_never_mix_silently(
    firstparty_fixture: Path, firstparty_v1_fixture: Path,
) -> None:
    """A v1 row carries a diff a v0 row must not have, and vice versa — so
    loading a log with the wrong pipeline fails loudly instead of grading
    the wrong artifact."""
    with pytest.raises(IngestError, match="diff"):
        load_v0_runs(firstparty_v1_fixture)
    with pytest.raises(IngestError, match="diff"):
        load_runs(firstparty_fixture)
