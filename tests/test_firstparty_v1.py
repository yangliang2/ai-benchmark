"""Dataset-seam tests for first-party v1: the checked-in task set plus a raw
run log carrying workdir diffs in, execution-verified records out.

Diffs are built by firstparty_v1_tasks.workdir_diff, the way the live runner
(#11) builds them, so the grader is exercised against genuine patches (added,
modified and deleted files) rather than hand-written hunks that could drift
from git's output.
"""

import json
import shutil
import subprocess
import tempfile
import textwrap
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import firstparty_v1_tasks
import pytest
import yaml
from conftest import FakeClaude
from firstparty_v1_tasks import (
    SOLUTIONS,
    TASKS,
    run_for,
    solution_diff,
    task_by_id,
    workdir_diff,
)
from pydantic import ValidationError

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import load_runs as load_v0_runs
from ai_benchmark.firstparty import local_today
from ai_benchmark.firstparty_v1 import (
    BASELINE_TASK_IDS,
    BENCHMARK,
    KNOB_LEVELS,
    KnobActivation,
    Task,
    evaluate,
    lint_task_set,
    load_runs,
    load_task_set,
    run_live,
)

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
    for name in ("test_ledger_structure.py", "test_ledger_behaviour.py"):
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
        construction:
          knobs:
            - id: K1
              level: acceptance
          prediction:
            rung: haiku-solvable
            rationale: one named function with its return type stated
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


# --- the diff-building helpers these suites are written on ---------------------


def test_bytecode_left_in_a_solution_tree_never_reaches_the_diff(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Anything that imports a solution leaves a __pycache__ beside it, and
    the helpers copy whole trees: without this, one probe run turns every
    later reference-solution grading into a diff carrying stale bytecode,
    which is how it was found."""
    task = task_by_id(REFACTOR_SEED)
    solutions = tmp_path / "solutions"
    shutil.copytree(SOLUTIONS / task.id, solutions / task.id)
    cache = solutions / task.id / "__pycache__"
    cache.mkdir()
    (cache / "ledger.cpython-313.pyc").write_bytes(b"\x00stale bytecode\x00")
    (solutions / task.id / "ledger.pyc").write_bytes(b"\x00stale bytecode\x00")
    monkeypatch.setattr(firstparty_v1_tasks, "SOLUTIONS", solutions)

    diff = solution_diff(task)

    assert "__pycache__" not in diff
    assert ".pyc" not in diff
    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    assert record.quality_value == 1.0


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


def test_refactor_tasks_name_their_behaviour_tests() -> None:
    refactors = [t for t in load_task_set(TASKS) if t.category == "refactor"]

    assert refactors
    for refactor in refactors:
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


# --- construction metadata: knobs, families, predictions, provenance -----------


def a_construction_block(**overrides: object) -> dict[str, object]:
    """A well-formed construction block, ready to be broken one field at a
    time: one knob activation and the pre-registered difficulty prediction."""
    return {
        "knobs": [{"id": "K1", "level": "acceptance"}],
        "prediction": {
            "rung": "haiku-solvable",
            "rationale": "every decision is stated as an acceptance criterion",
        },
    } | overrides


def clone_constructed(
    root: Path, task_id: str, construction: object, *, seed: str = FEATURE_SEED
) -> Path:
    """A seed task cloned under a knob-experiment id, carrying construction
    metadata — the shape every task authored after the baseline must have."""
    task_dir = clone_seed(root, seed, task_id)
    retitle(task_dir, id=task_id, construction=construction)
    return task_dir


A_SUBSTRATE = {
    "origin": "https://github.com/example/tiny-lib",
    "commit": "0f8c2b9a1d4e6f70a3b5c8d9e2f1a4b6c7d8e9f0",
    "license": "MIT",
    "modifications": [
        {"knob": "K8", "description": "deleted the module's own test suite"}
    ],
}


def a_vendored_block(**overrides: object) -> dict[str, object]:
    """A construction block for a vendored starting repository.

    It activates K8 as well as K1 because A_SUBSTRATE's one modification sets
    K8: a planted edit has to answer to a knob the task itself declares.
    """
    return a_construction_block(
        knobs=[
            {"id": "K1", "level": "acceptance"},
            {"id": "K8", "level": "bare"},
        ],
        substrate=A_SUBSTRATE,
    ) | overrides


def test_a_task_records_the_knobs_it_sets_and_its_difficulty_prediction(
    tmp_path: Path,
) -> None:
    clone_constructed(
        tmp_path, "knobbed-task", a_vendored_block(family="a-family", pair="a-pair")
    )

    [task] = load_task_set(tmp_path)

    assert task.construction is not None
    assert [(k.id, k.level) for k in task.construction.knobs] == [
        ("K1", "acceptance"),
        ("K8", "bare"),
    ]
    assert task.construction.family == "a-family"
    assert task.construction.pair == "a-pair"
    assert task.construction.prediction.rung == "haiku-solvable"
    assert task.construction.prediction.rationale.startswith("every decision")
    assert task.construction.substrate is not None
    assert task.construction.substrate.license == "MIT"
    assert [m.knob for m in task.construction.substrate.modifications] == ["K8"]


def test_the_baseline_tasks_declare_no_construction() -> None:
    """Absence of the block is what makes the 22 pre-experiment tasks
    zero-knob baseline controls; reconciliation reads them that way, so
    nothing may quietly give one of them a knob."""
    baseline = [t for t in load_task_set(TASKS) if t.id in BASELINE_TASK_IDS]

    assert len(baseline) == len(BASELINE_TASK_IDS)
    assert all(task.construction is None for task in baseline)


def test_an_unknown_knob_id_fails_loudly(tmp_path: Path) -> None:
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        knobs=[{"id": "K99", "level": "acceptance"}],
    ))

    with pytest.raises(IngestError, match="unknown difficulty knob 'K99'"):
        load_task_set(tmp_path)


def test_a_knob_level_off_its_ladder_fails_loudly(tmp_path: Path) -> None:
    """K1's levels are an enumerated ladder, so a free-text level would make
    the family sweep and the per-level reconciliation grouping meaningless."""
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        knobs=[{"id": "K1", "level": "quite-vague"}],
    ))

    with pytest.raises(IngestError, match="quite-vague"):
        load_task_set(tmp_path)


def test_the_k9_ladder_is_the_two_levels_the_design_note_names() -> None:
    """K9 got an enumerated ladder with the planted-crux tasks, so a level off
    it is refused rather than recorded — reconciliation groups outcomes by
    level, and a free-text level is a group of one."""
    assert KNOB_LEVELS["K9"] == ("none", "single")

    with pytest.raises(ValidationError, match="not one of"):
        KnobActivation(id="K9", level="planted")


def test_a_knob_whose_ladder_is_not_enumerated_takes_a_free_text_level(
    tmp_path: Path,
) -> None:
    """The design note enumerates K1's, K8's and K9's levels and no others; a
    knob it has not pinned down yet records its level as written."""
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        knobs=[{"id": "K7", "level": "dense"}],
    ))

    [task] = load_task_set(tmp_path)

    assert task.construction is not None
    assert task.construction.knobs[0].level == "dense"


def test_a_construction_block_setting_no_knob_fails_loudly(tmp_path: Path) -> None:
    """Setting no knob is what having no block already means."""
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(knobs=[]))

    with pytest.raises(IngestError, match="at least one knob"):
        load_task_set(tmp_path)


def test_the_same_knob_set_twice_fails_loudly(tmp_path: Path) -> None:
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(knobs=[
        {"id": "K1", "level": "acceptance"},
        {"id": "K1", "level": "intent"},
    ]))

    with pytest.raises(IngestError, match=r"\['K1'\] set more than once"):
        load_task_set(tmp_path)


def test_a_construction_block_without_a_prediction_fails_loudly(
    tmp_path: Path,
) -> None:
    """A knob activation with no prediction is unfalsifiable: the theory would
    be fitted to the sweep after the fact."""
    block = a_construction_block()
    del block["prediction"]
    clone_constructed(tmp_path, "knobbed-task", block)

    with pytest.raises(IngestError, match="prediction"):
        load_task_set(tmp_path)


def test_a_prediction_rung_off_the_ladder_fails_loudly(tmp_path: Path) -> None:
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        prediction={"rung": "opus-only", "rationale": "a hunch"},
    ))

    with pytest.raises(IngestError, match="rung"):
        load_task_set(tmp_path)


def test_a_prediction_without_a_rationale_fails_loudly(tmp_path: Path) -> None:
    """The rationale is what a missed prediction teaches: which knob level was
    misjudged, and why the author expected otherwise."""
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        prediction={"rung": "unsolved", "rationale": ""},
    ))

    with pytest.raises(IngestError, match="rationale"):
        load_task_set(tmp_path)


def test_an_unknown_construction_field_fails_loudly(tmp_path: Path) -> None:
    """The task model forbids extras, so a misspelt field is a loud failure
    rather than metadata that silently never reaches reconciliation."""
    clone_constructed(tmp_path, "knobbed-task", a_construction_block(
        familly="a-typo",
    ))

    with pytest.raises(IngestError, match="familly"):
        load_task_set(tmp_path)


def test_substrate_provenance_missing_its_license_fails_loudly(
    tmp_path: Path,
) -> None:
    """Provenance is what keeps a vendored snapshot redistributable and
    auditable, so a partial record is no record."""
    substrate = dict(A_SUBSTRATE)
    del substrate["license"]
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(substrate=substrate))

    with pytest.raises(IngestError, match="license"):
        load_task_set(tmp_path)


def test_a_substrate_pinned_to_a_moving_ref_fails_loudly(tmp_path: Path) -> None:
    """A branch name moves under the task; only a full commit id is a pin."""
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        substrate=A_SUBSTRATE | {"commit": "main"},
    ))

    with pytest.raises(IngestError, match="commit"):
        load_task_set(tmp_path)


def test_a_substrate_commit_pinned_in_uppercase_hex_fails_loudly(
    tmp_path: Path,
) -> None:
    """Same commit, other spelling: the pin is written one canonical way so
    that two records of one snapshot cannot read as two snapshots."""
    commit = str(A_SUBSTRATE["commit"]).upper()
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        substrate=A_SUBSTRATE | {"commit": commit},
    ))

    with pytest.raises(IngestError, match="lowercase"):
        load_task_set(tmp_path)


def test_a_substrate_origin_that_is_not_a_url_fails_loudly(tmp_path: Path) -> None:
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        substrate=A_SUBSTRATE | {"origin": "somebody's laptop"},
    ))

    with pytest.raises(IngestError, match="origin"):
        load_task_set(tmp_path)


def test_a_substrate_origin_naming_no_host_fails_loudly(tmp_path: Path) -> None:
    """A scheme on its own is a URL nobody can follow back to the snapshot."""
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        substrate=A_SUBSTRATE | {"origin": "https://"},
    ))

    with pytest.raises(IngestError, match="host"):
        load_task_set(tmp_path)


def test_a_substrate_modification_naming_no_known_knob_fails_loudly(
    tmp_path: Path,
) -> None:
    """Every surgical edit to a vendored repository has to be traceable to a
    knob, or the substrate carries difficulty nothing accounts for."""
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        substrate=A_SUBSTRATE | {
            "modifications": [{"knob": "tidying", "description": "general cleanup"}]
        },
    ))

    with pytest.raises(IngestError, match="unknown difficulty knob 'tidying'"):
        load_task_set(tmp_path)


def test_a_substrate_modification_setting_an_unactivated_knob_fails_loudly(
    tmp_path: Path,
) -> None:
    """Naming a known knob is not enough. The edit deletes the repository's
    test suite, so the task has to activate K8 — a task that plants the edit
    without declaring the knob has planted difficulty its profile denies, and
    reconciliation would credit the outcome to the knobs it does declare."""
    clone_constructed(tmp_path, "knobbed-task", a_vendored_block(
        knobs=[{"id": "K1", "level": "acceptance"}],
    ))

    with pytest.raises(IngestError, match=r"\['K8'\] this task does not activate"):
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
    assert "test_ledger_structure.py" in tampered  # the tamper really is in the diff

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


# --- task-set lint: construction metadata, families and pairs ------------------


def clone_k1_family(root: Path, family: str, levels: Sequence[str]) -> None:
    """One cloned task per named K1 level, all declaring the same family.

    Each variant gets its own prompt, the way a real K1 family does: the
    clones are identical everywhere else, so a shared prompt would be a
    declared spec gradient with nothing behind it.
    """
    for index, level in enumerate(levels, start=1):
        task_dir = clone_constructed(root, f"{family}-{index}", a_construction_block(
            family=family, knobs=[{"id": "K1", "level": level}],
        ))
        retitle(task_dir, prompt=(
            f"Add top_words(text, n) to wordcount.py, specified at the {level} "
            f"level (variant {index})."
        ))


def test_lint_requires_construction_metadata_outside_the_baseline(
    tmp_path: Path,
) -> None:
    """A knob-experiment task that declares nothing would silently join the
    baseline controls, and its sweep result would explain nothing."""
    task_dir = clone_seed(tmp_path, FEATURE_SEED, "undeclared-task")
    retitle(task_dir, id="undeclared-task")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "undeclared-task" in problem and "construction" in problem


def test_lint_rejects_a_baseline_task_that_declares_construction(
    tmp_path: Path,
) -> None:
    """The other direction of the same rule: absence of the block is the whole
    of what makes a baseline task a control, so one that declares knobs is
    neither control nor knob-experiment task."""
    clone_constructed(tmp_path, FEATURE_SEED, a_construction_block())

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert FEATURE_SEED in problem and "baseline" in problem


def test_lint_accepts_a_complete_one_knob_family(tmp_path: Path) -> None:
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])

    assert lint_task_set(load_task_set(tmp_path)) == []


def test_lint_accepts_a_family_sweeping_part_of_a_ladder(tmp_path: Path) -> None:
    """A family need not use every enumerated level: the planned K8 family
    runs covered → bare → misleading and skips partial. Such a family says
    less than a full sweep would, which is the author's call, not the lint's."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "intent"])

    assert lint_task_set(load_task_set(tmp_path)) == []


def test_lint_rejects_a_family_of_one(tmp_path: Path) -> None:
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance"])

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "spec-ladder-1" in problem


def test_lint_rejects_a_family_that_varies_two_knobs(tmp_path: Path) -> None:
    """Two knobs moving at once attributes the difference to neither."""
    for index, (spec, net) in enumerate(
        [("acceptance", "covered"), ("intent", "misleading")], start=1
    ):
        clone_constructed(tmp_path, f"muddled-{index}", a_construction_block(
            family="muddled",
            knobs=[{"id": "K1", "level": spec}, {"id": "K8", "level": net}],
        ))

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "muddled" in problem and "K1" in problem and "K8" in problem


def test_lint_rejects_a_family_whose_members_set_different_knobs(
    tmp_path: Path,
) -> None:
    clone_constructed(tmp_path, "mixed-1", a_construction_block(
        family="mixed", knobs=[{"id": "K1", "level": "acceptance"}],
    ))
    clone_constructed(tmp_path, "mixed-2", a_construction_block(
        family="mixed", knobs=[{"id": "K8", "level": "misleading"}],
    ))

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "mixed" in problem and "mixed-1" in problem and "mixed-2" in problem


def test_lint_rejects_a_family_with_two_members_at_the_same_level(
    tmp_path: Path,
) -> None:
    """Two variants at one level are one variant; the family looks fuller than
    the evidence it can produce."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "acceptance", "intent"])

    problems = lint_task_set(load_task_set(tmp_path))

    assert any("spec-ladder" in p and "same level" in p for p in problems)


def test_lint_rejects_a_family_whose_members_start_from_different_repos(
    tmp_path: Path,
) -> None:
    """Varying one knob is only half of what isolating it means: the variants
    are self-contained copies of one underlying change, and copies drift
    silently, so the lint reads the trees rather than trusting the author."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])
    append(tmp_path / "spec-ladder-2" / "repo" / "wordcount.py", """


        def unrelated_helper(text):
            return text.strip()
        """)

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "wordcount.py" in problem


def test_lint_rejects_a_family_whose_members_grade_differently(
    tmp_path: Path,
) -> None:
    """Same for the held-out suite: a variant graded against different tests
    is measuring a different change, however identical its knob list."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])
    append(tmp_path / "spec-ladder-3" / "grading" / "test_top_words.py", """


        def test_ties_break_alphabetically():
            assert top_words("b a a b c", 2) == ["a", "b"]
        """)

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "test_top_words.py" in problem


def test_lint_rejects_a_family_whose_members_classify_themselves_differently(
    tmp_path: Path,
) -> None:
    """Records inherit the task's annotations, so variants that disagree land
    in capability-matrix cells that are never compared — and with identical
    repositories and grading suites, one of the two is simply wrong."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])
    retitle(tmp_path / "spec-ladder-2", category="bug-fix")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "category" in problem
    assert "spec-ladder-1" in problem and "spec-ladder-2" in problem


def test_lint_rejects_a_family_whose_members_declare_different_scales(
    tmp_path: Path,
) -> None:
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])
    retitle(tmp_path / "spec-ladder-3", scale="cross-file")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "scale" in problem
    assert "spec-ladder-1" in problem and "spec-ladder-3" in problem


def test_lint_rejects_a_family_whose_members_share_a_prompt(
    tmp_path: Path,
) -> None:
    """With everything else held identical, the prompt is where a K1 family's
    knob actually moves: two variants declaring different levels of it while
    shipping the same prompt have declared a gradient the agent never sees."""
    clone_k1_family(tmp_path, "spec-ladder", ["acceptance", "description", "intent"])
    for index in (1, 2):
        retitle(tmp_path / f"spec-ladder-{index}", prompt="Add top_words(text, n).")

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "spec-ladder" in problem and "same prompt" in problem
    assert "spec-ladder-1" in problem and "spec-ladder-2" in problem


def clone_pair(root: Path, pair: str, task_ids: Sequence[str]) -> None:
    """One cloned task per named id, all declaring the same pair."""
    for task_id in task_ids:
        clone_constructed(root, task_id, a_construction_block(pair=pair))


def test_lint_accepts_two_tasks_paired_on_one_repository(tmp_path: Path) -> None:
    clone_pair(tmp_path, "crux-and-control", ["crux-task", "control-task"])

    assert lint_task_set(load_task_set(tmp_path)) == []


def test_lint_rejects_a_pair_with_a_third_member(tmp_path: Path) -> None:
    """A pair id says which two tasks are read against each other, and a third
    member leaves it saying nothing about any of them."""
    clone_pair(
        tmp_path, "crux-and-control", ["crux-task", "control-task", "spare-task"]
    )

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "crux-and-control" in problem and "spare-task" in problem


def test_lint_rejects_a_pair_starting_from_different_repositories(
    tmp_path: Path,
) -> None:
    """The shared terrain is what makes the second task a control: a pair
    pitched on two repositories measures where the work was asked as well as
    what was asked, which is the one thing pairing them was for."""
    clone_pair(tmp_path, "crux-and-control", ["crux-task", "control-task"])
    append(tmp_path / "control-task" / "repo" / "wordcount.py", """


        def unrelated_helper(text):
            return text.strip()
        """)

    [problem] = lint_task_set(load_task_set(tmp_path))

    assert "crux-and-control" in problem and "repo/" in problem


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


def test_live_runs_grant_all_tools_but_not_setting_sources(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """v1 runs are genuinely multi-turn: tools stay on (no --tools ""), and —
    because headless runs auto-deny whatever was not granted up front, while
    --setting-sources "" discards any user-level grants — the runner must
    grant tool use itself or the agent is billed in full while every action
    is denied. The grant is bypassPermissions: a real sweep died when a model
    Read outside its workdir under the narrower acceptEdits+Bash grant, and
    behaviour-driven denials recur on retry."""
    argv_log = fake_claude("")
    wordcount = task_by_id(FEATURE_SEED)

    run_live([wordcount], ["claude-sonnet-5"], tmp_path / "runs.jsonl")

    [argv] = [json.loads(line) for line in argv_log.read_text().splitlines()]
    assert "--tools" not in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--permission-mode") + 1] == "bypassPermissions"
    assert "--allowedTools" not in argv
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
