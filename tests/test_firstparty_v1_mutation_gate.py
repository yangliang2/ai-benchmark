"""The mutation gate: `test-authoring`'s verdict shape, pinned red-test-first.

The fourth verdict shape in `ai_benchmark.firstparty_v1`, and the only one
whose deliverable is the tests. A task of that action ships no held-out grading
tests at all: it ships planted mutants, and grading collects the prompt-named
test subtree out of the workdir diff — that subtree alone — and asks two
questions of it. Does it pass on the unmodified starting repository, and does
at least one test in it fail on every planted mutant? `resolved` is both,
binary; the fraction of mutants a suite killed is not a score and nothing here
computes one (design note §67.3, §67.4).

Everything below is asserted at the seams a sweep actually runs through —
`load_task_set` for what a task must be, `evaluate` over a crafted run log for
what a suite is worth — and never against the gate's own internals, so that a
future rearrangement of the gate is free to move while what it decides is not.
The task trees are synthetic and built in `tmp_path`, and both kinds of patch
in them are built with real git (`firstparty_v1_tasks.tree_diff`): a planted
mutant and a workdir diff are the same artefact against the same tree, and a
hand-written hunk would drift from what `git apply` accepts.
"""

import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from firstparty_v1_tasks import run_for, tree_diff, workdir_diff

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import Task, evaluate, load_task_set

TASK_ID = "banding-write-the-suite"
TEST_PATH = "tests"

# The module under test: a complete behavioural specification's worth of code
# in eleven lines, with three boundaries a suite can be right or wrong about.
BANDING = '''\
"""Grade a meter reading into a band."""


def band(reading):
    if reading < 0:
        raise ValueError("a reading is never negative")
    if reading < 10:
        return "low"
    if reading < 100:
        return "middle"
    return "high"
'''


# --- building a task, its mutants and a run's diff -----------------------------


def rewrite(old: str, new: str) -> Callable[[Path], None]:
    """One deliberate behaviour change to the module under test, as an edit —
    which is what a planted mutant is before git turns it into a patch."""

    def edit(tree: Path) -> None:
        source = (tree / "banding.py").read_text()
        assert old in source, f"the mutant's target {old!r} is not in banding.py"
        (tree / "banding.py").write_text(source.replace(old, new, 1))

    return edit


# Three mutants, each a different specified behaviour: a boundary moved by one,
# a guard dropped, a case folded into its neighbour. Named the way a task's
# `mutants/` directory names them, because the gate runs them in filename order.
MUTANTS: dict[str, Callable[[Path], None]] = {
    "01-widen-the-low-band.diff": rewrite("if reading < 10:", "if reading <= 10:"),
    "02-drop-the-negative-guard.diff": rewrite(
        '    if reading < 0:\n        raise ValueError("a reading is never negative")\n',
        "",
    ),
    "03-flatten-the-top-band.diff": rewrite('    return "high"\n', '    return "middle"\n'),
}

# The author's reference suite, at the address every existence proof keeps.
# Nothing in this ticket runs it; the task is refused at load without it.
REFERENCE_SUITE = '''\
from banding import band


def test_the_reference_suite_is_here():
    assert band(0) == "low"
'''


def write_task(
    root: Path,
    *,
    task_id: str = TASK_ID,
    category: str = "test-authoring",
    test_path: str | None = TEST_PATH,
    mutants: Mapping[str, Callable[[Path], None]] | None = None,
    proofs: bool = True,
    grading: Mapping[str, str] | None = None,
) -> Path:
    """A synthetic task directory, correct unless an argument breaks it."""
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "repo" / "banding.py").write_text(BANDING)
    spec = textwrap.dedent(f"""\
        id: {task_id}
        category: {category}
        scale: single-file
        surface: application
        language: python
        control: true
        prompt: |
          Write a test suite for band() in banding.py under {TEST_PATH}/.
        """)
    if test_path is not None:
        spec += f"test_path: {test_path}\n"
    (task_dir / "task.yaml").write_text(spec)
    for name, edit in (MUTANTS if mutants is None else mutants).items():
        (task_dir / "mutants").mkdir(exist_ok=True)
        (task_dir / "mutants" / name).write_text(tree_diff(task_dir / "repo", edit))
    if proofs:
        (task_dir / "proofs").mkdir()
        (task_dir / "proofs" / "test_reference.py").write_text(REFERENCE_SUITE)
    for name, source in (grading or {}).items():
        (task_dir / "grading").mkdir(exist_ok=True)
        (task_dir / "grading" / name).write_text(source)
    return task_dir


def mutation_task(root: Path) -> Task:
    """The well-formed task, loaded — what every gate test starts from."""
    write_task(root)
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


def verdict(task: Task, files: Mapping[str, str]) -> float:
    """What a sweep would record for an agent that wrote exactly these files."""
    return graded(task, workdir_diff(task, wrote(files)))


def graded(task: Task, diff: str) -> float:
    """The same thing for a diff built some other way — the empty one, or one
    an agent's edit cannot express. Read at the seam a sweep runs through:
    `evaluate` over a run log, never the gate's own internals."""
    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    return record.quality_value


# --- the suites an agent might come back with ----------------------------------


HONEST_SUITE = {
    "tests/test_band.py": """
        import pytest

        from banding import band


        def test_the_low_band_stops_below_ten():
            assert band(0) == "low"
            assert band(9) == "low"
            assert band(10) == "middle"


        def test_the_middle_band_stops_below_a_hundred():
            assert band(99) == "middle"
            assert band(100) == "high"


        def test_a_negative_reading_is_refused():
            with pytest.raises(ValueError):
                band(-1)
        """,
}

ASSERTS_NOTHING = {
    "tests/test_band.py": """
        def test_the_module_is_fine():
            assert True
        """,
}

# The honest suite plus one assertion that is false on correct code — and false
# on every mutant too, so this suite would kill all three at gate 2.
FALSE_ACCUSATION = HONEST_SUITE | {
    "tests/test_middle.py": """
        from banding import band


        def test_the_middle_band_starts_at_five():
            assert band(5) == "middle"
        """,
}

# N-1 of N: nothing here calls band() with a negative reading, so the mutant
# that drops the guard walks through.
PARTIAL_KILL = {
    "tests/test_band.py": """
        from banding import band


        def test_the_low_band_stops_below_ten():
            assert band(0) == "low"
            assert band(9) == "low"
            assert band(10) == "middle"


        def test_the_middle_band_stops_below_a_hundred():
            assert band(99) == "middle"
            assert band(100) == "high"
        """,
}

# A suite that leans on a helper the agent added to the module under test.
LEANS_ON_A_SOURCE_EDIT = HONEST_SUITE | {
    "banding.py": BANDING + '''

def shout(reading):
    return band(reading).upper()
''',
    "tests/test_shout.py": """
        from banding import shout


        def test_the_band_can_be_shouted():
            assert shout(5) == "LOW"
        """,
}

# Everything an agent might touch that is not the deliverable: the module under
# test rewritten into something no honest suite would pass, and a note beside it.
EDITS_OUTSIDE_THE_TEST_PATH = {
    "banding.py": '''\
"""Grade a meter reading into a band."""


def band(reading):
    return "high"
''',
    "NOTES.md": "I rewrote band() while I was in here.\n",
}


# --- the two gates -------------------------------------------------------------


def test_an_honest_thorough_suite_resolves(tmp_path: Path) -> None:
    """Gate 1 green and every planted mutant killed — the whole of `resolved`
    for this action, and the only thing that earns it."""
    task = mutation_task(tmp_path)

    assert verdict(task, HONEST_SUITE) == 1.0


def test_a_suite_nested_one_directory_deeper_is_collected_too(tmp_path: Path) -> None:
    """Collection takes the subtree, not its top level: the negative-reading
    test lives one directory down, and without it the guard mutant survives —
    so resolving here is only possible if the nested file was collected."""
    task = mutation_task(tmp_path)

    assert verdict(task, PARTIAL_KILL | {
        "tests/deep/test_guard.py": """
            import pytest

            from banding import band


            def test_a_negative_reading_is_refused():
                with pytest.raises(ValueError):
                    band(-1)
            """,
    }) == 1.0


def test_a_suite_that_asserts_nothing_kills_nothing_and_is_unresolved(
    tmp_path: Path,
) -> None:
    """The degenerate suite gate 2 exists for: it passes on the starting
    repository and on all three mutants alike, so it verified nothing."""
    task = mutation_task(tmp_path)

    assert verdict(task, ASSERTS_NOTHING) == 0.0


def test_a_suite_that_accuses_correct_code_is_unresolved_at_gate_one(
    tmp_path: Path,
) -> None:
    """A single failing test on correct code sinks the suite even though it
    would kill every mutant — gate 1 admits no exception, because a false
    accusation is what the findings key's rejected half refuses elsewhere."""
    task = mutation_task(tmp_path)

    assert verdict(task, FALSE_ACCUSATION) == 0.0


def test_a_suite_that_leans_on_the_agents_own_source_edits_is_unresolved(
    tmp_path: Path,
) -> None:
    """The hole the collection rule closes: the helper this suite imports was
    written into the module under test, which is outside the test path and so
    never reaches the world the gates run in. Gate 1 goes red honestly."""
    task = mutation_task(tmp_path)

    assert verdict(task, LEANS_ON_A_SOURCE_EDIT) == 0.0


def test_a_suite_that_kills_all_but_one_mutant_is_unresolved(tmp_path: Path) -> None:
    """The quantifier is universal: two of three killed is not a score, and
    N-1 of N is exactly as unresolved as none."""
    task = mutation_task(tmp_path)

    assert verdict(task, PARTIAL_KILL) == 0.0


def test_edits_outside_the_test_path_change_no_verdict(tmp_path: Path) -> None:
    """Archived, not scored, in both directions: the same suites with the module
    under test rewritten under them grade exactly as they do without it. An
    agent that edits source commits no foul and buys nothing."""
    task = mutation_task(tmp_path)

    assert verdict(task, HONEST_SUITE) == 1.0
    assert verdict(task, HONEST_SUITE | EDITS_OUTSIDE_THE_TEST_PATH) == 1.0
    assert verdict(task, ASSERTS_NOTHING) == 0.0
    assert verdict(task, ASSERTS_NOTHING | EDITS_OUTSIDE_THE_TEST_PATH) == 0.0


def test_a_diff_with_nothing_under_the_test_path_is_unresolved(
    tmp_path: Path,
) -> None:
    """Nothing collected means nothing ran, and nothing ran means nothing was
    verified — never a vacuous pass over an empty universe of tests."""
    task = mutation_task(tmp_path)

    assert graded(task, "") == 0.0
    assert verdict(task, EDITS_OUTSIDE_THE_TEST_PATH) == 0.0
    # A real test file, written somewhere the prompt did not name: collected by
    # nothing, so it neither counts as a suite nor rescues one.
    assert verdict(task, HONEST_SUITE | EDITS_OUTSIDE_THE_TEST_PATH | {
        "test_band.py": """
            def test_the_module_is_fine():
                assert True
            """,
    }) == 1.0
    assert verdict(task, EDITS_OUTSIDE_THE_TEST_PATH | {
        "test_band.py": """
            def test_the_module_is_fine():
                assert True
            """,
    }) == 0.0


# --- the forgery guards, in the agent's own test files -------------------------


def test_an_agent_test_that_exits_early_cannot_forge_a_pass(tmp_path: Path) -> None:
    """The early-exit class, written where this action's agent writes: the
    verdict reads a report from outside the workdir rather than the exit status,
    and a session that killed itself before finishing wrote none."""
    task = mutation_task(tmp_path)

    assert verdict(task, {
        "tests/test_band.py": """
            import os

            os._exit(0)
            """,
    }) == 0.0


def test_an_agent_test_that_writes_its_own_report_cannot_forge_a_pass(
    tmp_path: Path,
) -> None:
    """The verdict-file class: the report the verdict is read from is written
    outside the workdir, so a file the agent's own test writes at a workdir path
    called `report.xml` is not it. (The residual — code that computes the real
    path at runtime — is the not-a-sandbox limitation the module records.)"""
    task = mutation_task(tmp_path)

    assert verdict(task, {
        "tests/test_band.py": """
            from banding import band

            FORGED = (
                '<?xml version="1.0" encoding="utf-8"?><testsuites>'
                '<testsuite name="pytest" errors="0" failures="0" skipped="0" '
                'tests="1"><testcase name="test_ok"/></testsuite></testsuites>'
            )

            for name in ("report.xml", "junit.xml", "grading-report.xml"):
                with open(name, "w") as handle:
                    handle.write(FORGED)


            def test_the_bands_are_all_high():
                assert band(0) == "high"
            """,
    }) == 0.0


def test_a_conftest_inside_the_subtree_is_collected_but_never_loaded(
    tmp_path: Path,
) -> None:
    """Collection copies the whole subtree, and the runner passes
    `--noconftest`: a `conftest.py` the agent wrote lands as a file and is never
    loaded as a plugin, so a fixture defined only there errors at gate 1. The
    same suite with the fixture in the test file itself resolves — which is what
    makes this a fact about conftest loading rather than about the suite, and
    what a prompt requiring self-contained test files rests on."""
    task = mutation_task(tmp_path)
    suite = """
        import pytest

        from banding import band


        def test_the_bands(boundaries):
            assert [band(r) for r in boundaries] == [
                "low", "low", "middle", "middle", "high"
            ]


        def test_a_negative_reading_is_refused():
            with pytest.raises(ValueError):
                band(-1)
        """
    fixture = """
        import pytest


        @pytest.fixture
        def boundaries():
            return [0, 9, 10, 99, 100]
        """

    assert verdict(task, {"tests/test_band.py": suite, "tests/conftest.py": fixture}) == 0.0
    assert verdict(task, {"tests/test_band.py": fixture + suite}) == 1.0


# --- a task the gate cannot grade ----------------------------------------------


def test_a_mutant_patch_that_does_not_apply_fails_loudly(tmp_path: Path) -> None:
    """A broken task, not a verdict — the way a diff git cannot apply is a
    broken run log. Grading a mutant that quietly did not land would quantify
    over one fewer behaviour change than the task claims."""
    task = mutation_task(tmp_path)
    (task.mutants_dir / "04-against-a-file-that-is-not-there.diff").write_text(
        "diff --git a/banding.py b/banding.py\n"
        "--- a/banding.py\n"
        "+++ b/banding.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-nothing in the starting repository says this\n"
        "+and so this patch cannot land\n"
    )

    with pytest.raises(IngestError) as excinfo:
        verdict(task, HONEST_SUITE)

    assert TASK_ID in str(excinfo.value)
    assert "04-against-a-file-that-is-not-there.diff" in str(excinfo.value)


# --- what the loader refuses ---------------------------------------------------


def test_a_test_path_that_escapes_the_workdir_is_refused(tmp_path: Path) -> None:
    """A run's diff only carries what was written inside the workdir, so a
    suite could never land at such a path and the gate would collect nothing."""
    write_task(tmp_path, test_path="../elsewhere")

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "climbs out of the workdir" in str(
        excinfo.value
    )


def test_a_mutant_set_shipped_by_another_action_is_refused(tmp_path: Path) -> None:
    """Which verdict shape grades a task is read off the mutants being there,
    so a mutant set under any other action would swap that task's whole verdict
    for one its grading directory was never authored for."""
    write_task(
        tmp_path,
        category="feature-dev",
        test_path=None,
        grading={"test_band.py": REFERENCE_SUITE},
    )

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "mutants/" in str(excinfo.value)


def test_a_test_authoring_task_with_no_mutants_is_refused(tmp_path: Path) -> None:
    """Gate 2 would quantify over nothing, and every suite that compiles would
    resolve."""
    write_task(tmp_path, mutants={})

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "ships no mutants/" in str(excinfo.value)


def test_a_test_authoring_task_with_no_proofs_is_refused(tmp_path: Path) -> None:
    """Nothing would say the planted mutants are killable at all, and a mutant
    no test can kill makes a task unresolvable for every agent while looking
    like a hard one."""
    write_task(tmp_path, proofs=False)

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "ships no proofs/" in str(excinfo.value)


def test_a_test_authoring_task_shipping_a_grading_directory_is_refused(
    tmp_path: Path,
) -> None:
    """Its verdict is the mutation gate, which overlays nothing: a held-out
    test kept there would never run and would read as a second ground truth."""
    write_task(tmp_path, grading={"test_held_out.py": REFERENCE_SUITE})

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "ships grading/" in str(excinfo.value)


def test_another_action_may_not_declare_a_test_path(tmp_path: Path) -> None:
    """The field says *this* subtree is the deliverable and the rest is
    archived, which is a claim only the mutation gate's grading makes good."""
    write_task(tmp_path, category="feature-dev", mutants={},
               grading={"test_band.py": REFERENCE_SUITE})

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert TASK_ID in str(excinfo.value) and "test_path" in str(excinfo.value)
