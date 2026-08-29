"""Round 13's `performance-optimisation` tasks: what one of them is, and that
it is proved.

Heap 4's one action, taken from behind the fork §117.1 ruled (registered
§118, recorded ADR-0006). A task of it ships two held-out suites: a
behaviour suite, named in the `grading` block's `behaviour_tests` exactly as
a refactor names its own, which must pass on the pristine repository and on
the reference solution; and a complexity suite — every other grading test —
which must fail on the pristine repository and pass on the reference,
counting operations through a seam the task repository already owns.
`resolved` is both suites passing, computed and never spoken, and wall-clock
never enters the verdict path.

This suite is **parametrised over every checked-in `performance-optimisation`
task on disk** — never a list written in this file and never a task count —
so the round's later tasks are covered by being authored, which is the
explain-tasks suite's selection pattern; what it proves per task is the
refactor suite's: the split, the two pristine invariants, the reference
solution grading 1.0 and doing nothing grading 0.0, and the scale annotation
held to the reference solution's own diff.

**The honest-proxy rule is not machine-asserted here** (§117.2, §118.5): that
the counter counts a fact of the algorithm — never a wall-clock and never an
implementation constant an agent could satisfy without changing the
algorithm's shape — is an authoring discipline, policed where authoring is
already policed: the spec review, and the two pristine invariants this file
does assert through the real grading pipeline. What *is* machine-checked
below is §117.1's own prohibition, which is narrower and greppable: no
wall-clock call of any kind in the complexity half. The prompt checks are
likewise a smoke check over a needle list and not the ruling — §117.3's rule
is that the prompt names the hot operation and the observable scale
requirement and never the counter's numbers, and no word list can check the
whole of that; the needles catch the obvious slip.

Nothing here calls an agent, a grader or the network: every verdict below is
the two held-out suites run against a diff built with real git, offline.
"""

import ast
import re
import sys
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    SOLUTIONS,
    TASKS,
    run_for,
    solution_diff,
    structural_half_passes,
    task_by_id,
)

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Task,
    _run_grading,
    evaluate,
    grade,
    lint_task_set,
    load_task_set,
)

# The words a prompt of this action may not contain — §117.3's two held-back
# halves, as needles. A smoke check and not the ruling: what actually keeps
# the instrument's numbers out is the author writing a prompt that names the
# hot operation and the observable requirement and nothing else, and no word
# list can check that. Algorithm names first (a prompt naming the bound
# outright grades whether the agent can implement a named algorithm), then
# the counter's own vocabulary (input sizes, ratios, ceilings), then grading
# mechanics.
UNDISCLOSED = (
    "sort", "index", "cache", "memo", "hash", "binary search", "big-o", "o(n",
    "ceiling", "ratio", "threshold", "linear", "quadratic",
    "complexity", "wall-clock", "grading", "held-out", "counter",
)


def performance_task_ids() -> list[str]:
    """Every checked-in task of the action, in a stable order — selected off
    the corpus rather than listed here, so ticket 05's two tasks join this
    suite by landing on disk."""
    return sorted(
        task.id
        for task in load_task_set(TASKS)
        if task.category == "performance-optimisation"
    )


TASK_IDS = performance_task_ids()


def complexity_half(task: Task) -> list[str]:
    """The complexity suite: everything in `grading/` that is not the named
    behaviour half — the same subtraction `structural_half_passes` runs."""
    return sorted(set(task.grading_test_paths) - set(task.behaviour_test_paths))


# --- the round shipped some ----------------------------------------------------


def test_the_round_checked_in_at_least_one_performance_task() -> None:
    """Everything below is parametrised over the corpus, so an empty corpus
    would pass the whole file by having nothing to run."""
    assert TASK_IDS


# --- what a task of this action declares ---------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_declares_the_action_and_registers_no_prediction(
    task_id: str,
) -> None:
    """The declarations §118.10 registers: Python, `application`, and a
    declared control — `control: true`, no construction block, no knob
    activation, no prediction. The round declares no contrast, so it moves no
    knob's counter."""
    task = task_by_id(task_id)

    assert task.category == "performance-optimisation"
    assert task.language == "python"
    assert task.surface == "application"
    assert task.control is True
    assert task.construction is None


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_grading_split_is_present_and_disjoint_by_name(task_id: str) -> None:
    """The two halves of §118.3's verdict, both present: the behaviour suite
    named in `behaviour_tests`, and a complexity suite that is strictly more
    than it. A task with no complexity half has nothing left to assert the
    optimisation by, and a task with no behaviour half has nothing to say the
    optimisation preserved."""
    task = task_by_id(task_id)

    assert task.behaviour_test_paths
    assert set(task.grading_test_paths) > set(task.behaviour_test_paths)
    assert complexity_half(task)


# --- the prompt: the observable requirement, never the counter's numbers -------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_names_the_hot_operation_and_the_growth_in_plain_terms(
    task_id: str,
) -> None:
    """The positive half of §117.3, as a smoke check: some backticked name in
    the prompt is a name the starting repository actually defines (the hot
    operation, handed over rather than left to telepathy), and the scale
    requirement is put in behavioural terms — something grows, and the
    operation must stay fast as it does."""
    task = task_by_id(task_id)
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(task.repo_dir.rglob("*.py"))
    )
    named = [
        token.split(".")[-1]
        for token in re.findall(r"`([^`]+)`", task.prompt)
    ]

    assert any(
        re.search(rf"\bdef {name}\b|\bclass {name}\b", source) for name in named
    ), "no backticked prompt token names a definition of the repository"
    assert "grows" in task.prompt


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_holds_back_the_instruments_numbers_and_the_algorithm(
    task_id: str,
) -> None:
    """The negative half of §117.3, as the same kind of smoke check: no digit
    anywhere (the counter's input sizes and ceilings are numbers, and the
    observable requirement needs none), and none of the needle words — the
    algorithm to use, the counter's vocabulary, the grading mechanics."""
    prompt = task_by_id(task_id).prompt.lower()

    assert not re.search(r"\d", prompt), "a prompt of this action names no number"
    assert [word for word in UNDISCLOSED if word in prompt] == []


# --- the repository: stdlib-only, per ADR-0003 ---------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_repository_and_its_grading_are_stdlib_only(task_id: str) -> None:
    """ADR-0003's rule, read off the imports: every module a shipped file
    imports is the stdlib's or the repository's own, and no dependency
    manifest ships at all — which is what keeps grading hermetic with nothing
    installed. The grading halves are held to it too: they overlay the same
    workdir and run under the same toolchain."""
    task = task_by_id(task_id)
    local = {path.stem for path in task.repo_dir.rglob("*.py")}

    for root in (task.repo_dir, task.grading_dir):
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = {
                name.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for name in node.names
            } | {
                node.module.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            foreign = imported - local - set(sys.stdlib_module_names)
            assert not foreign, f"{path.name} imports {sorted(foreign)}"
    assert not [
        path
        for path in task.repo_dir.rglob("*")
        if path.name in {"requirements.txt", "pyproject.toml", "package.json"}
    ]


# --- the two pristine invariants, through the real pipeline --------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_behaviour_half_passes_on_the_pristine_repository(
    task_id: str,
) -> None:
    """The behaviour side of §117.1's two-sided proof: a task must start from
    behaviour that already works, or "preserved" has nothing to be measured
    against. The same invariant the lint runs, asserted here through the
    grader's own slice runner."""
    task = task_by_id(task_id)

    assert _run_grading(
        task, "", task.behaviour_test_paths, timeout_s=GRADE_TIMEOUT_S
    )


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_whole_suite_does_not_pass_on_the_pristine_repository(
    task_id: str,
) -> None:
    """The complexity side of the same proof: a proxy the unoptimised code
    already satisfies is a task with nothing left for an agent to do. With
    the behaviour half green above, what fails here is the complexity suite
    on the planted slow path."""
    assert grade(task_by_id(task_id), "") is False


# --- the reference solution, and doing nothing ---------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_reference_solution_passes_both_halves_and_resolves(
    task_id: str,
) -> None:
    """§117.1's other side: the author's optimised tree passes the behaviour
    half, the complexity half on its own, and grades 1.0 through `evaluate` —
    the very function a run is graded by."""
    task = task_by_id(task_id)
    assert (SOLUTIONS / task.id).is_dir()
    diff = solution_diff(task)

    assert _run_grading(task, diff, task.behaviour_test_paths, timeout_s=GRADE_TIMEOUT_S)
    assert structural_half_passes(task, diff)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    assert record.quality_value == 1.0


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_doing_nothing_leaves_the_task_unresolved(task_id: str) -> None:
    task = task_by_id(task_id)

    [record] = evaluate([task], [run_for(task, "")], source="run-log")

    assert record.quality_value == 0.0


# --- the prohibition that is machine-checkable ---------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_complexity_suite_takes_no_wall_clock_reading(task_id: str) -> None:
    """§117.1's prohibition, which — unlike the honest-proxy rule — is
    greppable and grepped: no `time`, `perf_counter`, `timeit` or sleep of any
    kind anywhere in the complexity half. A reading nobody gates on is still
    a reading a later round would be tempted to gate on."""
    task = task_by_id(task_id)

    for name in complexity_half(task):
        text = (task.grading_dir / name).read_text(encoding="utf-8")
        assert not re.search(r"\btime\b|perf_counter|timeit|\bsleep\b", text), name


# --- the annotations, and the standing lint ------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_scale_annotation_matches_the_reference_solution(task_id: str) -> None:
    """Scale is honest to the canonical solution, checked the mechanical way
    the refactor suite checks it: one touched file means single-file, more
    than one means cross-file."""
    task = task_by_id(task_id)
    touched = [
        line
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    ]

    if task.scale == "single-file":
        assert len(touched) == 1
    else:
        assert len(touched) > 1


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_is_lint_clean(task_id: str) -> None:
    """The round's one hard gate, per task: both pristine invariants run
    inside the standing lint, with no LLM call and no key."""
    assert lint_task_set([task_by_id(task_id)]) == []
