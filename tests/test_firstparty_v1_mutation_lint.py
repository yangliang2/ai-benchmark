"""The lint over a `test-authoring` task: what a planted mutant set has to be,
and the proof that it is killable (design note §67.5–§67.7).

`test_firstparty_v1_mutation_gate.py` owns the verdict — what a suite an agent
came back with is worth. This suite owns everything that happens *before* an
agent ever sees the task: the authoring invariants `lint_task_set` holds a
mutation task to, so that a task nobody could resolve, or one whose mutants and
whose agent could collide, is refused at the lint rather than discovered by a
paid sweep.

Four rules read the set and its terrain — at least three mutants, mutants
disjoint from the declared test path and confined to files the starting
repository holds, no tests already sitting at that path, a prompt that names it
— and one registered **existence proof** runs it: the author's own reference
suite, which must pass on the pristine repository and die on each planted mutant
*individually*. Per mutant is the whole point: an equivalent mutant — a change
no behaviour distinguishes — is what makes the gate's universal quantifier
unsatisfiable, and a set-level check would let one hide behind its killable
neighbours.

Every task tree here is synthetic and built in `tmp_path`, each clean except for
the one thing under test, so that every assertion is about one rule. The module
under test and its three mutants are imported from the gate's suite rather than
copied: the two suites are two questions about one action, and a second copy of
`banding.py` would drift.
"""

import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from firstparty_v1_tasks import tree_diff
from test_firstparty_v1_mutation_gate import BANDING, MUTANTS, rewrite

from ai_benchmark.firstparty_v1 import (
    EXISTENCE_PROOFS,
    MUTANTS_DIR,
    TERRAIN_EXEMPT_ACTIONS,
    Task,
    _terrain_problems,
    lint_task_set,
    load_task_set,
)

TASK_ID = "banding-write-the-suite"
TEST_PATH = "tests"
PROMPT = f"Write a suite for band() in banding.py under {TEST_PATH}/.\n"

# The author's reference suite: this action's existence proof, and the thing
# that has to kill every mutant below one at a time. Three tests over the three
# specified behaviours — the two band boundaries and the negative guard.
REFERENCE_SUITE = {
    "test_reference.py": '''\
"""The author's reference suite: the first perfect agent on this task."""

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
''',
}

# Three more killable behaviour changes, so that a six-mutant set can be built
# and shown to lint clean: the minimum binds at three and there is no maximum.
MORE_MUTANTS: dict[str, Callable[[Path], None]] = {
    "04-widen-the-middle-band.diff": rewrite(
        "if reading < 100:", "if reading <= 100:"
    ),
    "05-raise-the-floor-band.diff": rewrite('return "low"', 'return "middle"'),
    "06-let-one-negative-through.diff": rewrite("if reading < 0:", "if reading < -1:"),
}

# The mutant this whole existence proof exists to refuse: the wording of the
# error changes and nothing else does, so no test written against the
# specification — "a negative reading is refused" — can tell it from the
# original. Plausible enough for an author to plant in good faith, which is why
# it is the lint that has to catch it rather than the author's judgement.
UNKILLABLE = "07-reword-the-refusal.diff"
UNKILLABLE_MUTANT: dict[str, Callable[[Path], None]] = {
    UNKILLABLE: rewrite(
        '"a reading is never negative"', '"readings are never negative"'
    ),
}


def writing(files: Mapping[str, str]) -> Callable[[Path], None]:
    """An edit that lays these files into a tree — how a mutant that touches
    something other than the module under test is built."""

    def edit(tree: Path) -> None:
        for name, source in files.items():
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)

    return edit


def write_task(
    root: Path,
    *,
    prompt: str = PROMPT,
    test_path: str = TEST_PATH,
    mutants: Mapping[str, Callable[[Path], None]] | None = None,
    proofs: Mapping[str, str] | None = None,
    repo: Mapping[str, str] | None = None,
) -> Path:
    """A synthetic `test-authoring` task, well-formed unless an argument breaks
    it in exactly one way."""
    task_dir = root / TASK_ID
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "repo" / "banding.py").write_text(BANDING)
    for name, source in (repo or {}).items():
        path = task_dir / "repo" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source))
    (task_dir / "task.yaml").write_text(
        textwrap.dedent(f"""\
            id: {TASK_ID}
            category: test-authoring
            scale: single-file
            surface: application
            language: python
            control: true
            test_path: {test_path}
            prompt: |
            """)
        + textwrap.indent(prompt, "  ")
    )
    (task_dir / MUTANTS_DIR).mkdir()
    for name, edit in (MUTANTS if mutants is None else mutants).items():
        (task_dir / MUTANTS_DIR / name).write_text(tree_diff(task_dir / "repo", edit))
    (task_dir / "proofs").mkdir()
    for name, source in (REFERENCE_SUITE if proofs is None else proofs).items():
        (task_dir / "proofs" / name).write_text(source)
    return task_dir


def problems(root: Path) -> list[str]:
    """What the lint says about the one task built under this root."""
    return lint_task_set(load_task_set(root))


def only_problem(root: Path) -> str:
    """The lint's single complaint — asserted as single, because every tree here
    is clean but for the one thing under test, and a second problem would mean
    this test is not measuring what it says."""
    [problem] = problems(root)
    return problem


def loaded(root: Path) -> Task:
    """The one task built under this root, loaded."""
    [task] = load_task_set(root)
    return task


# --- the well-formed task ------------------------------------------------------


def test_a_well_formed_mutation_task_lints_clean(tmp_path: Path) -> None:
    """The baseline every negative below is one edit away from: three planted
    mutants, all killed by the author's reference suite, none of them reaching
    into a test path the repository leaves empty and the prompt names."""
    write_task(tmp_path)

    assert problems(tmp_path) == []


def test_a_well_formed_mutation_task_declares_no_terrain_waiver(
    tmp_path: Path,
) -> None:
    """The exemption is the action's, so no task of it carries an apology of its
    own: three identical action-shaped reasons in three `task.yaml` files would
    counterfeit a mechanism built to be per task and reason-per-task."""
    write_task(tmp_path)

    task = loaded(tmp_path)

    assert task.terrain_waiver == ()


# --- the mutant set: disjointness ----------------------------------------------


def test_a_mutant_touching_the_test_path_is_refused(tmp_path: Path) -> None:
    """What makes "no agent edit and no mutation can ever collide" true by
    construction: grading lays the agent's collected test subtree over the
    mutated copy, so a mutation inside that subtree is either overwritten by the
    suite meant to catch it or handed to the agent."""
    write_task(
        tmp_path,
        mutants=MUTANTS
        | {
            "04-mutate-a-test.diff": writing(
                {f"{TEST_PATH}/test_planted.py": "def test_nothing():\n    pass\n"}
            )
        },
    )

    problem = only_problem(tmp_path)

    assert "04-mutate-a-test.diff" in problem
    assert f"{TEST_PATH}/test_planted.py" in problem
    assert "test path" in problem


def test_a_mutant_touching_a_file_the_repository_does_not_hold_is_refused(
    tmp_path: Path,
) -> None:
    """A patch against a file that is not in `repo/` cannot apply, so the second
    gate would quantify over one fewer behaviour change than the task claims."""
    write_task(
        tmp_path,
        mutants=MUTANTS
        | {"04-mutate-a-stranger.diff": writing({"elsewhere.py": "VALUE = 1\n"})},
    )

    problem = only_problem(tmp_path)

    assert "04-mutate-a-stranger.diff" in problem
    assert "elsewhere.py" in problem


# --- the mutant set: how many --------------------------------------------------


def test_two_mutants_are_refused(tmp_path: Path) -> None:
    """Below three the universal quantifier barely binds and one lucky assertion
    clears the gate (§67.7)."""
    write_task(tmp_path, mutants=dict(list(MUTANTS.items())[:2]))

    problem = only_problem(tmp_path)

    assert "2 planted mutant(s)" in problem
    assert "minimum is 3" in problem


def test_three_mutants_lint_clean(tmp_path: Path) -> None:
    """The minimum binds exactly at three, and the well-formed task is three."""
    assert len(MUTANTS) == 3
    write_task(tmp_path)

    assert problems(tmp_path) == []


def test_six_mutants_lint_clean(tmp_path: Path) -> None:
    """There is no maximum. Four to six is the spec's authoring guidance and
    deliberately not a lint rule, so a six-mutant set is as clean as a three."""
    write_task(tmp_path, mutants=MUTANTS | MORE_MUTANTS)

    assert problems(tmp_path) == []


# --- the existence proof -------------------------------------------------------


def test_an_unkillable_mutant_is_refused_and_named(tmp_path: Path) -> None:
    """The equivalent mutant, and the reason the proof is checked per mutant
    rather than over the set: the other three die honestly, and a set-level
    check would let this one ride along. The message names the mutant, because
    "a proof failed" leaves the author to work out which."""
    write_task(tmp_path, mutants=MUTANTS | UNKILLABLE_MUTANT)

    problem = only_problem(tmp_path)

    assert UNKILLABLE in problem
    assert "survives" in problem


def test_a_reference_suite_that_fails_on_the_pristine_repository_is_refused(
    tmp_path: Path,
) -> None:
    """Gate 1 of this task's own verdict, turned on its author: a reference
    suite that accuses correct code is either wrong about the specification or
    reading a repository the prompt does not describe, and nothing about the
    mutants can be judged until it passes."""
    write_task(
        tmp_path,
        proofs={
            "test_reference.py": (
                "from banding import band\n\n\n"
                "def test_five_is_in_the_middle_band():\n"
                '    assert band(5) == "middle"\n'
            )
        },
    )

    problem = only_problem(tmp_path)

    assert "fails on the pristine" in problem


def test_a_proofs_directory_with_no_test_in_it_is_refused(tmp_path: Path) -> None:
    """The loader refuses an empty `proofs/`; a `proofs/` holding only prose is
    the same absence one file later, and the lint is where it is caught."""
    write_task(tmp_path, proofs={"README.md": "The suite is coming.\n"})

    problem = only_problem(tmp_path)

    assert "no file this task's runner would collect as a test" in problem


def test_the_actions_proof_form_is_registered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key with no registered proof form is refused rather than exempt.
    Asserted through the lint's own output rather than by reading the registry:
    what the registry buys is a refusal, and a test that read the dict would
    pass however unwired that dict was."""
    write_task(tmp_path)
    monkeypatch.delitem(EXISTENCE_PROOFS, "test-authoring")

    reported = " ".join(problems(tmp_path))

    assert "carry a key and register no existence proof" in reported
    assert "test-authoring" in reported


# --- the terrain the suite is written into -------------------------------------


def test_a_repository_shipping_a_test_at_the_test_path_is_refused(
    tmp_path: Path,
) -> None:
    """An existing suite where the agent is told to write is a crib: it hands
    over which behaviours are worth asserting, which is the whole of what this
    action measures."""
    write_task(
        tmp_path,
        repo={
            f"{TEST_PATH}/test_band.py": """\
                from banding import band


                def test_the_low_band_stops_below_ten():
                    assert band(9) == "low"
                """
        },
    )

    problem = only_problem(tmp_path)

    assert f"{TEST_PATH}/test_band.py" in problem
    assert "crib" in problem


def test_a_prompt_that_never_names_the_test_path_is_refused(tmp_path: Path) -> None:
    """A task whose agent cannot locate its own deliverable grades every run
    unresolved for a reason no verdict would explain."""
    write_task(tmp_path, prompt="Write a suite for band() in banding.py.\n")

    problem = only_problem(tmp_path)

    assert "never names the test path" in problem


def test_a_prompt_naming_the_test_path_only_inside_a_longer_word_is_refused(
    tmp_path: Path,
) -> None:
    """Named as a whole token or not at all, by the same check the terrain rules
    read paths with: "integration-tests/" is not the "tests/" the agent was told
    to write in, and a plain substring test would say it was."""
    write_task(
        tmp_path,
        prompt="Write a suite for band() in banding.py under integration-tests/.\n",
    )

    problem = only_problem(tmp_path)

    assert "never names the test path" in problem


def test_a_prompt_naming_the_test_path_as_a_token_lints_clean(
    tmp_path: Path,
) -> None:
    """The other side of the same rule, so that the two refusals above are about
    the token and not about the sentence around it."""
    write_task(
        tmp_path, prompt=f"The suite belongs in {TEST_PATH}/, one file per behaviour.\n"
    )

    assert problems(tmp_path) == []


# --- the action-level terrain exemption ----------------------------------------


def test_the_terrain_exemption_is_recorded_with_its_reason() -> None:
    """§67.6 asks for the exemption to be *recorded*, not inherited from the
    accident that this action carries no greppable key: a stated rule survives
    someone later giving the action a key of some other shape, and a side effect
    does not."""
    reason = TERRAIN_EXEMPT_ACTIONS["test-authoring"]

    assert "workdir" in reason
    assert "mutant" in reason


def test_a_clean_mutation_task_raises_no_terrain_problem(tmp_path: Path) -> None:
    """And so needs no waiver: the exemption is the action's, and what a task of
    it declares about terrain is nothing at all."""
    write_task(tmp_path)

    task = loaded(tmp_path)

    assert _terrain_problems(task) == []
