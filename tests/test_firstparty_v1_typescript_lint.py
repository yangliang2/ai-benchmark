"""The loader and the lint, on a TypeScript task: what is refused at load, and
what is refused about the files a task ships.

The authoring half of admitting TypeScript. Everything here is read rather than
run — no live agent, no LLM, no network — over synthetic task trees built by
`tests/typescript_tasks.py` under `tmp_path`, the way the Python rule tests are
read over a cloned seed. Node is required on the machine running this suite, as
pytest is; probed at v22.22.2 on 2026-08-19, where every claim below about what
Node accepts and refuses was measured.

Each rule is asserted in **both** directions: the tree that trips it, and the
tree that does not. A rule only proved one way is a rule that could be firing on
everything.

The first test that reads a lint problem runs the whole lint, because the
wiring is the claim; every one after it reads `_typescript_problems`, which is
the very function `lint_task_set` calls, so that proving nine more rules does
not pay for nine more runs of the grading pipeline.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from firstparty_v1_tasks import TASKS
from typescript_tasks import DEFAULT_GRADING, DEFAULT_REPO, typescript_task

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    Task,
    _typescript_problems,
    hash_gate_source,
    lint_task_set,
    load_task_set,
    repo_digests,
)
from ai_benchmark.language_runners import PYTHON, TYPESCRIPT

# The harness-side half of a grading directory: canonical Python, run by pytest,
# which a TypeScript task's grading directory holds *beside* its own held-out
# tests — or, for a task whose whole deliverable is an answer file, instead of
# them.
ANSWER_CHECK = {
    "test_answer_shape.py": """\
import json
from pathlib import Path


def test_the_agent_wrote_the_answer_file():
    assert json.loads(Path("ANSWER.json").read_text(encoding="utf-8"))
"""
}

# A checked-in Python task, cloned where a rule has to be read against one.
PYTHON_SEED = "wordcount-top-words"

# A key, so that a task counts as keyed and the hash-gate rules apply to it.
ANSWER_KEY = json.dumps(
    {
        "answer_path": "ANSWER.json",
        "accepted": [{"file": "calc.ts", "symbol": "half"}],
        "rejected": [{"file": "other.ts", "symbol": "twice"}],
    }
)


def one_file(source: str) -> dict[str, str]:
    """A starting repository of this source and nothing else, so that whatever
    a test is reading is the only thing its tree can trip."""
    return {"calc.ts": source}


# --- at load: the grading directory is read per runner glob ---------------------


def test_a_grading_directory_of_typescript_tests_alone_is_a_suite(
    tmp_path: Path,
) -> None:
    """The rule the corpus's `test_*.py` spelling used to be: a task's own
    held-out tests are found by its language runner's glob, so a grading
    directory holding nothing but `.test.ts` files is not refused for holding
    no `test_*.py`."""
    task = typescript_task(tmp_path)

    assert task.language_test_paths == ("calc.test.ts",)
    assert task.harness_test_paths == ()
    assert task.grading_test_paths == ("calc.test.ts",)


def test_a_grading_directory_of_the_canonical_python_checks_alone_is_a_suite(
    tmp_path: Path,
) -> None:
    """The other half, and the other direction: the answer-key test, the
    findings-key test and the hash gate are canonical Python whatever the task
    declares, so a TypeScript task whose deliverable is an answer file has a
    suite with no `.test.ts` in it at all."""
    task = typescript_task(tmp_path, grading=ANSWER_CHECK)

    assert task.language_test_paths == ()
    assert task.harness_test_paths == ("test_answer_shape.py",)
    assert task.grading_test_paths == ("test_answer_shape.py",)


def test_a_grading_directory_with_neither_half_is_refused_at_load(
    tmp_path: Path,
) -> None:
    """And the refusal names both globs, because either would have been a
    suite: the task's own tests under its runner's spelling, the harness-side
    checks under pytest's."""
    with pytest.raises(IngestError) as refusal:
        typescript_task(tmp_path, grading={"notes.md": "nothing runs this\n"})

    assert TYPESCRIPT.grading_test_glob in str(refusal.value)
    assert PYTHON.grading_test_glob in str(refusal.value)


# --- the stdlib-only rule: a typescript task installs nothing -------------------


def test_lint_refuses_a_package_json_in_the_starting_repository(
    tmp_path: Path,
) -> None:
    """ADR-0003 through the whole lint, because the wiring is the claim: a
    manifest declares dependencies grading will never install and decides the
    module system the runner pins itself.

    Declared a control so that the one problem this returns is the one under
    test: every task declares how it was built or that it is a control, and a
    fixture that declares neither has two problems rather than one."""
    task = typescript_task(
        tmp_path,
        control=True,
        repo=DEFAULT_REPO | {"package.json": '{"dependencies": {"left-pad": "*"}}\n'},
    )

    [problem] = lint_task_set([task])

    assert task.id in problem and "package.json" in problem
    assert "ADR-0003" in problem


def test_a_node_modules_at_any_depth_of_the_repository_is_a_problem(
    tmp_path: Path,
) -> None:
    """Anywhere, not just at the top: a vendored dependency tree is the
    stdlib-only rule broken however deep it is checked in, and the problem
    names the path so an author knows which one to delete.

    One problem and not one per file: the manifests *inside* a vendored tree
    are not separately fixable, and reporting them would bury the line that
    says to delete it."""
    task = typescript_task(
        tmp_path,
        repo=DEFAULT_REPO
        | {
            "tools/node_modules/left-pad/index.js": "module.exports = 1;\n",
            "tools/node_modules/left-pad/package.json": '{"name": "left-pad"}\n',
        },
    )

    [problem] = _typescript_problems(task)

    assert task.id in problem and "tools/node_modules" in problem


def test_a_repository_of_the_task_s_own_files_alone_is_clean(tmp_path: Path) -> None:
    """The other direction, and the one every TypeScript task authored this
    round has to be in: `node:` builtins and the task's own files, and no
    lint problem of any kind."""
    assert _typescript_problems(typescript_task(tmp_path)) == []


def test_a_python_task_shipping_a_package_json_is_not_this_rule_s_business(
    tmp_path: Path,
) -> None:
    """These are Node's rules, dispatched on the registered runner: a Python
    task's `repo/` may hold whatever its own language's rules allow, and
    nothing here reads it."""
    shutil.copytree(TASKS / PYTHON_SEED, tmp_path / PYTHON_SEED)
    (tmp_path / PYTHON_SEED / "repo" / "package.json").write_text('{"name": "x"}\n')
    [task] = load_task_set(tmp_path)

    assert task.runner is PYTHON
    assert _typescript_problems(task) == []


# --- every .ts file the task ships has to load ---------------------------------


def test_an_enum_is_a_lint_problem_though_node_check_passes_it(
    tmp_path: Path,
) -> None:
    """Why the check is a real import and not `node --check`.

    Probed at v22.22.2: `node --check` exits 0 on this file, and the refusal —
    "TypeScript enum is not supported in strip-only mode" — appears only when
    the file is really loaded. A syntax check would have let this task be
    authored, and every run of it would then have scored 0.0 and read as a very
    bad model rather than as a file Node cannot load.
    """
    task = typescript_task(tmp_path, repo=one_file("export enum Size { S, M }\n"))

    [problem] = _typescript_problems(task)

    assert task.id in problem and "repo/calc.ts" in problem
    assert "enum is not supported" in problem
    assert (
        subprocess.run(
            ["node", "--check", str(task.repo_dir / "calc.ts")], check=False
        ).returncode
        == 0
    )


@pytest.mark.parametrize("tree", ["proofs", "corrected"])
def test_the_load_check_reads_the_trees_beside_the_repository_too(
    tmp_path: Path, tree: str
) -> None:
    """`proofs/` and `corrected/` are run and read by this lint itself, so a
    file in either that cannot be imported is a task that cannot do its job as
    surely as one in `repo/`."""
    task = typescript_task(tmp_path)
    (task.directory / tree).mkdir()
    (task.directory / tree / "aside.ts").write_text("export enum E { A }\n")

    [problem] = _typescript_problems(task)

    assert task.id in problem and f"{tree}/aside.ts" in problem


def test_a_held_out_test_naming_what_the_pristine_repo_has_not_got_yet_is_clean(
    tmp_path: Path,
) -> None:
    """The deliberate tolerance, and the reason the check reports Node's error
    rather than its exit status.

    A held-out test is written against the *solved* repository: the default
    task's test imports `ratio`, which is exactly what the agent is asked to
    write, so against the pristine repository it names something that is not
    there. Both shapes of that — a name the module does not export yet, and a
    module that does not exist yet — are passed over, because they are the
    task rather than a defect in the file.
    """
    task = typescript_task(
        tmp_path,
        grading=DEFAULT_GRADING
        | {
            "later.test.ts": """\
import test from "node:test";

import { unwritten } from "./nowhere.ts";

test("later", () => unwritten());
"""
        },
    )

    assert _typescript_problems(task) == []


def test_an_unguarded_entry_point_is_a_lint_problem_and_a_guarded_one_is_not(
    tmp_path: Path,
) -> None:
    """The consequence for authors the message has to make actionable: a module
    is imported by the tests that grade it, so it must be side-effect-free at
    import. Node 22 has no `import.meta.main`, so the idiom the guard is spelled
    with is `process.argv[1]` against `fileURLToPath(import.meta.url)` — and the
    probe imports the file from outside the tree it copied, so a guarded entry
    point sees the probe's path and stays quiet."""
    unguarded = """\
export function main(): void {
  throw new Error("no arguments given");
}

main();
"""
    guarded = """\
import { fileURLToPath } from "node:url";

export function main(): void {
  throw new Error("no arguments given");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
"""
    trips = typescript_task(tmp_path / "trips", repo=one_file(unguarded))
    passes = typescript_task(tmp_path / "passes", repo=one_file(guarded))

    [problem] = _typescript_problems(trips)

    assert trips.id in problem and "repo/calc.ts" in problem
    assert "no arguments given" in problem
    assert "import.meta.url" in problem
    assert _typescript_problems(passes) == []


def test_a_module_that_ends_the_process_at_import_is_a_lint_problem(
    tmp_path: Path,
) -> None:
    """The same rule from its other side, and the one an exit status alone
    cannot see: a module calling `process.exit` while it is being loaded ends
    the probe with status 0, which is what a clean load looks like. The verdict
    is read from what the probe *said*, so silence is a problem rather than a
    pass."""
    task = typescript_task(
        tmp_path, repo=one_file("export const ready = true;\nprocess.exit(0);\n")
    )

    [problem] = _typescript_problems(task)

    assert task.id in problem and "repo/calc.ts" in problem
    assert "ended the process" in problem


# --- what a held-out test may import -------------------------------------------


def test_a_held_out_test_importing_a_package_is_a_lint_problem(
    tmp_path: Path,
) -> None:
    """There is no package. A test naming one grades every run unresolved on a
    module error, however well the agent solved the task."""
    task = typescript_task(
        tmp_path,
        grading={
            "calc.test.ts": """\
import test from "node:test";
import expect from "expect";

import { ratio } from "./calc.ts";

test("ratio divides", () => expect(ratio(1, 2)).toBe(0.5));
"""
        },
    )

    [problem] = _typescript_problems(task)

    assert task.id in problem and "calc.test.ts" in problem
    assert "'expect'" in problem


def test_a_bare_builtin_and_a_relative_import_without_the_extension_are_problems(
    tmp_path: Path,
) -> None:
    """Both near-misses, because both fail at grade time for reasons an author
    reads as "it worked in my editor": a builtin has to carry its explicit
    `node:` prefix, and a relative import has to carry the `.ts` extension Node
    actually resolves."""
    task = typescript_task(
        tmp_path,
        grading={
            "calc.test.ts": """\
import test from "node:test";
import assert from "assert";

import { ratio } from "./calc";

test("ratio divides", () => assert.strictEqual(ratio(1, 2), 0.5));
"""
        },
    )

    problems = _typescript_problems(task)

    assert len(problems) == 2
    assert any("'assert'" in problem for problem in problems)
    assert any("'./calc'" in problem for problem in problems)


def test_node_builtins_and_relative_ts_paths_are_what_a_held_out_test_may_name(
    tmp_path: Path,
) -> None:
    """The other direction: the default task's test imports `node:test`,
    `node:assert` and `./calc.ts`, which is the whole of what a held-out test
    is allowed, and nothing fires. `Array.from("...")` is there because the
    rule reads specifiers out of text, and a method call is not an import."""
    task = typescript_task(
        tmp_path,
        grading={
            "calc.test.ts": """\
import test from "node:test";
import assert from "node:assert";

import { ratio } from "./calc.ts";

test("ratio divides", () => {
  assert.deepStrictEqual(Array.from("ab"), ["a", "b"]);
  assert.strictEqual(ratio(1, 2), 0.5);
});
"""
        },
    )

    assert _typescript_problems(task) == []


# --- a keyed typescript task's repository is flat -------------------------------


def keyed(root: Path, repo: dict[str, str]) -> Task:
    """A keyed TypeScript task: one carrying an accepted-answer key, and so one
    the hash gate holds to answering rather than repairing."""
    return typescript_task(
        root,
        task_id="locate-the-ratio-ts",
        category="fault-location",
        repo=repo,
        grading=ANSWER_CHECK | {"accepted-answer.json": ANSWER_KEY},
    )


def test_a_directory_under_a_keyed_task_s_repository_is_a_lint_problem(
    tmp_path: Path,
) -> None:
    """The hash gate hashes top-level files only, so a nested file is ungated:
    an agent could repair it and still grade resolved, at answer-file cost,
    with nothing in the run log to show it happened."""
    task = keyed(
        tmp_path,
        DEFAULT_REPO | {"lib/units.ts": "export const HALF = 0.5;\n"},
    )

    [problem] = _typescript_problems(task)

    assert task.id in problem and "repo/lib/" in problem
    assert "flat" in problem


def test_a_flat_keyed_repository_is_clean_and_an_unkeyed_nested_one_is_too(
    tmp_path: Path,
) -> None:
    """Both other directions. The rule is the keyed corpus's, because it is the
    hash gate's: a task that ships no key ships no gate, and nothing about a
    nested file there is ungated."""
    flat = keyed(tmp_path / "flat", DEFAULT_REPO)
    nested = typescript_task(
        tmp_path / "nested",
        repo=DEFAULT_REPO | {"lib/units.ts": "export const HALF = 0.5;\n"},
    )

    assert _typescript_problems(flat) == []
    assert _typescript_problems(nested) == []


def test_the_hash_gate_itself_still_hashes_top_level_files_only(
    tmp_path: Path,
) -> None:
    """The rule above is a refusal and not a widening, and this is what says so:
    the gate is untouched this round, so a nested file is still not hashed. That
    is exactly why a keyed task may not have one — widening the gate would
    change what a replay of every keyed task computes."""
    task = keyed(
        tmp_path,
        DEFAULT_REPO | {"lib/units.ts": "export const HALF = 0.5;\n"},
    )

    assert set(repo_digests(task.repo_dir)) == {"calc.ts"}
    assert b"lib/units.ts" not in hash_gate_source(task.repo_dir)


# --- the checked-in corpus ------------------------------------------------------


def test_no_checked_in_task_trips_any_of_these_rules() -> None:
    """The corpus is all Python today, so every rule here is dispatched away
    from it — which is the claim worth making cheaply, since `ai-bench lint-v1`
    makes the expensive one."""
    assert [
        problem
        for task in load_task_set(TASKS)
        for problem in _typescript_problems(task)
    ] == []
