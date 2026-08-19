"""The TypeScript runner: `node --test`, a per-testcase verdict, and the
forgery classes it closes.

The second entry in the language-runner registry, held to the bar the Python
runner is held to. Every forgery class the Python suite closes in
`tests/test_firstparty_v1.py` is closed again here in Node's terms, in the same
sentences: an agent's edit at a grading test's path buys nothing, agent code
cannot short-circuit the run, agent-written configuration changes nothing that
runs, a run that never finishes is unresolved at the timeout, and the control —
a genuine solution resolves, the empty diff does not.

**Node is required on the machine running this suite, as pytest is.** Probed
here at v22.22.2 on 2026-08-19, which is where every claim below about what
`node --test` emits was measured. There is no live agent, no LLM and no network
in any test: every verdict is read from a synthetic task tree built by
`tests/typescript_tasks.py` and a workdir diff built by git.
"""


import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
import typescript_tasks
from firstparty_v1_tasks import run_for, workdir_diff
from typescript_tasks import DEFAULT_GRADING, DEFAULT_REPO, solve, typescript_task

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import GRADE_TIMEOUT_S, Task, evaluate, grade
from ai_benchmark.language_runners import (
    NODE_TYPE_STRIPPING_FLOOR,
    PYTHON,
    RUNNERS,
    TYPESCRIPT,
    _every_named_testcase_passed,
    _report_shows_every_test_passed,
    runner_for,
)

# A harness-side check: canonical Python, run by pytest, reading a file back out
# of the workdir the way the answer-key and findings-key tests do. It is what a
# TypeScript task's grading directory holds *beside* its own held-out tests.
ANSWER_CHECK = {
    "test_answer_shape.py": """\
import json
from pathlib import Path


def test_the_agent_wrote_the_answer_file():
    answer = json.loads(Path("ANSWER.json").read_text(encoding="utf-8"))
    assert answer["file"] == "calc.ts"
"""
}


def write_answer(workdir: Path) -> None:
    """What satisfies the harness-side half, and nothing else."""
    (workdir / "ANSWER.json").write_text('{"file": "calc.ts"}\n', encoding="utf-8")


def solve_and_answer(workdir: Path) -> None:
    solve(workdir)
    write_answer(workdir)


def resolved(
    task: Task,
    edit: Callable[[Path], None] | None = None,
    *,
    timeout_s: int = GRADE_TIMEOUT_S,
) -> float:
    """This task's quality value for the run an agent making this edit would
    log — the whole pipeline, the way every grading test in the Python suite
    reads a verdict."""
    diff = "" if edit is None else workdir_diff(task, edit)
    [record] = evaluate(
        [task], [run_for(task, diff)], source="run-log", timeout_s=timeout_s
    )
    return record.quality_value


# --- the registry and the declaration that reaches it --------------------------


def test_typescript_is_registered_and_selected_by_the_declaration_alone(
    tmp_path: Path,
) -> None:
    """The key is the task's own `language` and nothing an operator can pass:
    registering the runner is what makes a TypeScript task gradable, and the
    task's declaration is the only thing that reaches it."""
    assert RUNNERS["typescript"] is TYPESCRIPT
    assert TYPESCRIPT.language == "typescript"
    assert runner_for("typescript") is TYPESCRIPT

    task = typescript_task(tmp_path)

    assert task.language == "typescript"
    assert task.runner is TYPESCRIPT


def test_the_runner_answers_the_same_closed_list_the_python_one_does() -> None:
    """A second entry owes exactly what the first does — no more members, and
    none missing."""
    assert TYPESCRIPT.grading_test_glob == "*.test.ts"
    assert TYPESCRIPT.visible_test_glob == "*.test.ts"
    assert TYPESCRIPT.source_glob == "*.ts"

    def owned(runner: object) -> set[str]:
        return {name for name in dir(runner) if not name.startswith("_")}

    assert owned(TYPESCRIPT) == owned(PYTHON)


# --- grade() runs every half present -------------------------------------------


def test_a_task_with_only_harness_side_checks_is_graded_by_pytest(
    tmp_path: Path,
) -> None:
    """Shape one of three. The harness-side half is canonical Python whatever
    the task's language is, so a TypeScript task holding only those is graded
    by pytest and by nothing else."""
    task = typescript_task(tmp_path, grading=ANSWER_CHECK)

    assert [runner for runner, _ in task.grading_halves] == [PYTHON]
    assert task.grading_halves[0][1] == ("test_answer_shape.py",)
    assert resolved(task, write_answer) == 1.0
    assert resolved(task) == 0.0


def test_a_task_with_only_held_out_typescript_tests_is_graded_by_node(
    tmp_path: Path,
) -> None:
    """Shape two of three."""
    task = typescript_task(tmp_path)

    assert [runner for runner, _ in task.grading_halves] == [TYPESCRIPT]
    assert task.grading_halves[0][1] == ("calc.test.ts",)
    assert resolved(task, solve) == 1.0
    assert resolved(task) == 0.0


def test_a_task_with_both_halves_resolves_only_when_both_pass(
    tmp_path: Path,
) -> None:
    """Shape three of three, and the spec's rule outright: a task's verdict is
    every half present passes. Either half satisfied alone leaves it
    unresolved, because the other half is a grading test too."""
    task = typescript_task(tmp_path, grading=DEFAULT_GRADING | ANSWER_CHECK)

    assert [runner for runner, _ in task.grading_halves] == [PYTHON, TYPESCRIPT]
    assert task.grading_test_paths == ("calc.test.ts", "test_answer_shape.py")

    assert resolved(task, solve_and_answer) == 1.0
    assert resolved(task, solve) == 0.0
    assert resolved(task, write_answer) == 0.0


def test_a_python_task_still_has_exactly_one_half(tmp_path: Path) -> None:
    """The reading must not double-run a Python task: its two halves are the
    same files under the same runner, so it keeps one."""
    task = typescript_task(
        tmp_path,
        language="python",
        repo={"calc.py": "def half(x):\n    return x / 2\n"},
        grading={"test_calc.py": "from calc import half\n\n\n"
                 "def test_half():\n    assert half(4) == 2\n"},
    )

    assert [runner for runner, _ in task.grading_halves] == [PYTHON]
    assert task.harness_test_paths == task.language_test_paths


# --- the invocation ------------------------------------------------------------


def test_the_report_and_the_preload_are_written_outside_the_workdir(
    tmp_path: Path,
) -> None:
    """A logged diff can only write inside the workdir, so everything the
    verdict rests on is written beside it: the JUnit report the verdict is read
    from, and the preload that makes an exit throw."""
    root = tmp_path / "root"
    workdir = root / "workdir"
    workdir.mkdir(parents=True)
    (workdir / "calc.ts").write_text(typescript_tasks.SOLVED_CALC, encoding="utf-8")
    (workdir / "calc.test.ts").write_text(
        DEFAULT_GRADING["calc.test.ts"], encoding="utf-8"
    )

    assert TYPESCRIPT.run_tests(root, workdir, ["calc.test.ts"], timeout_s=60)

    outside = {path.name for path in root.iterdir() if path.is_file()}
    assert "node-report.xml" in outside
    assert "grading-preload.mjs" in outside
    inside = {path.name for path in workdir.iterdir()}
    assert not inside & outside


def test_a_test_file_the_agent_wrote_is_never_collected(tmp_path: Path) -> None:
    """The held-out files are named explicitly, so `node --test` runs no
    discovery: a plausible-looking test file the agent left in the workdir is
    not part of the verdict in either direction."""
    task = typescript_task(tmp_path)

    def solve_and_leave_a_failing_test(workdir: Path) -> None:
        solve(workdir)
        (workdir / "extra.test.ts").write_text(
            'import test from "node:test";\n'
            'import assert from "node:assert";\n\n'
            'test("the agent\'s own test", () => {\n'
            "  assert.fail(\"collected, and it should not have been\");\n"
            "});\n",
            encoding="utf-8",
        )

    assert resolved(task, solve_and_leave_a_failing_test) == 1.0


def test_node_options_in_the_environment_changes_nothing_that_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Node reads its own options out of the environment, so a `NODE_OPTIONS`
    on the operator's machine would join the invocation the runner pinned and
    make the verdict a fact about the machine. Both directions: it must not
    sink a correct solution, and it must not raise an empty one."""
    hostile = tmp_path / "hostile.mjs"
    hostile.write_text('throw new Error("NODE_OPTIONS reached grading");\n')
    monkeypatch.setenv("NODE_OPTIONS", f"--import {hostile.as_uri()}")
    monkeypatch.setenv("NODE_PATH", str(tmp_path))
    task = typescript_task(tmp_path / "tasks")

    assert resolved(task, solve) == 1.0
    assert resolved(task) == 0.0


# --- the verdict, read per testcase --------------------------------------------


def test_the_verdict_reads_top_level_tests_the_python_reader_cannot_see(
    tmp_path: Path,
) -> None:
    """`node --test`'s JUnit reporter emits a top-level test as a bare
    `<testcase>` child of `<testsuites>` and only a `describe` block as a
    `<testsuite>` with count attributes. Summing those attributes — which is
    what the Python runner's reader does, and it stays the Python runner's —
    reads a file of top-level tests as zero tests, so this runner reads every
    `testcase` wherever it sits."""
    report = tmp_path / "node-report.xml"
    report.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<testsuites>\n"
        '\t<testcase name="ratio divides" time="0.0003" classname="test"/>\n'
        '\t<testcase name="ratio divides again" time="0.0001" classname="test"/>\n'
        "</testsuites>\n",
        encoding="utf-8",
    )

    assert _every_named_testcase_passed(report, ["calc.test.ts"])
    assert not _report_shows_every_test_passed(report)


def test_a_report_with_no_testcase_in_it_is_not_a_pass(tmp_path: Path) -> None:
    """At least one `testcase` must exist: a run that verified nothing is
    unresolved, not vacuously resolved."""
    empty = tmp_path / "empty.xml"
    empty.write_text("<testsuites>\n</testsuites>\n", encoding="utf-8")

    assert not _every_named_testcase_passed(empty, ["calc.test.ts"])
    assert not _every_named_testcase_passed(tmp_path / "never-written.xml", [])


def test_a_failure_inside_a_describe_block_is_read_as_a_failure(
    tmp_path: Path,
) -> None:
    """The nested shape: a `describe` block is a `<testsuite>` and its tests
    are `<testcase>` children of it, so the reading has to reach them."""
    grouped = {
        "calc.test.ts": """\
import { describe, it } from "node:test";
import assert from "node:assert";

import { ratio } from "./calc.ts";

describe("ratio", () => {
  it("divides", () => {
    assert.strictEqual(ratio(1, 2), 0.5);
  });

  it("divides exactly", () => {
    assert.strictEqual(ratio(1, 3), 1 / 3);
  });
});
"""
    }
    task = typescript_task(tmp_path / "good", grading=grouped)
    wrong = typescript_task(tmp_path / "wrong", grading=grouped)

    def solve_wrongly(workdir: Path) -> None:
        (workdir / "calc.ts").write_text(
            "export function half(x: number): number {\n  return x / 2;\n}\n\n"
            "export function ratio(a: number, b: number): number {\n"
            "  return Math.round(a / b);\n}\n",
            encoding="utf-8",
        )

    assert resolved(task, solve) == 1.0
    assert resolved(wrong, solve_wrongly) == 0.0


def test_a_skipped_test_is_not_a_passed_test(tmp_path: Path) -> None:
    """Node writes a skip as a `<skipped>` child rather than an attribute, and
    a skipped grading test asserted nothing — the same rule the Python runner
    reads out of its report's counts."""
    task = typescript_task(
        tmp_path,
        grading={
            "calc.test.ts": """\
import test from "node:test";
import assert from "node:assert";

import { ratio } from "./calc.ts";

test("ratio divides", () => {
  assert.strictEqual(ratio(1, 2), 0.5);
});

test("ratio divides again", { skip: true }, () => {
  assert.strictEqual(ratio(9, 3), 3);
});
"""
        },
    )

    assert resolved(task, solve) == 0.0


def test_a_held_out_test_file_that_registers_no_tests_is_unresolved(
    tmp_path: Path,
) -> None:
    """Node reports a file that registered no tests — or exited before they
    ran — as a single *passing* `testcase` named after the file. A placeholder
    is not evidence that anything was verified, so one named after a held-out
    file this run was asked to grade refuses the verdict, even alongside a real
    test that genuinely passed."""
    task = typescript_task(
        tmp_path,
        grading=DEFAULT_GRADING | {"registers-nothing.test.ts": "export const x = 1;\n"},
    )

    assert task.grading_halves[0][1] == ("calc.test.ts", "registers-nothing.test.ts")
    assert resolved(task, solve) == 0.0


# --- the toolchain floor -------------------------------------------------------


def fake_node(directory: Path, version: str | None, *, ran: Path) -> None:
    """A `node` on PATH that prints `version` and touches `ran` if it is ever
    asked to run tests — which is how "refuses *before any test runs*" is
    something this suite can see. `version` None means no `node` at all."""
    directory.mkdir(parents=True, exist_ok=True)
    if version is None:
        return
    executable = directory / "node"
    executable.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "--version" ]; then echo "{version}"; exit 0; fi\n'
        f'touch "{ran}"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IEXEC)


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, "not on PATH"),
        ("v20.19.0", "below"),
        ("v22.17.0", "below"),
        ("not a version", "not a version this grader can read"),
    ],
)
def test_a_node_below_the_floor_or_absent_refuses_loudly_before_any_test_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str | None, expected: str
) -> None:
    """A verdict must never be a toolchain artefact: without a Node that strips
    TypeScript types unflagged, every task would score 0.0 and read as a very
    bad model rather than an environment that cannot grade. The floor is 22.18,
    the first Node that does."""
    assert NODE_TYPE_STRIPPING_FLOOR == (22, 18)
    task = typescript_task(tmp_path / "tasks")
    ran = tmp_path / "node-ran-a-test"
    fake_node(tmp_path / "bin", version, ran=ran)
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    with pytest.raises(IngestError, match=expected):
        grade(task, "", timeout_s=GRADE_TIMEOUT_S)

    assert not ran.exists()


def test_the_real_node_on_this_machine_clears_the_floor() -> None:
    """The suite's own precondition, said out loud: Node is required here the
    way pytest is."""
    assert shutil.which("node") is not None

    TYPESCRIPT.require_toolchain()


# --- the forgery classes, each in the Python suite's own sentences --------------


def test_agent_edits_to_grading_test_files_have_no_effect(tmp_path: Path) -> None:
    """The canonical grading files overwrite same-path files in the workdir,
    so rewriting them buys an agent nothing."""
    task = typescript_task(tmp_path)

    def overwrite_the_grading_tests(workdir: Path) -> None:
        (workdir / "calc.test.ts").write_text(
            'import test from "node:test";\n\n'
            'test("nothing at all", () => {});\n',
            encoding="utf-8",
        )

    tampered = workdir_diff(task, overwrite_the_grading_tests)
    assert "calc.test.ts" in tampered  # the tamper really is in the diff

    [record] = evaluate([task], [run_for(task, tampered)], source="run-log")

    assert record.quality_value == 0.0


def test_agent_code_cannot_short_circuit_the_test_run_at_import(
    tmp_path: Path,
) -> None:
    """Exit status alone is not evidence of a pass: agent code runs when the
    grading test imports it, and one `process.exit(0)` there ends `node --test`
    with status 0 and a report holding one passing placeholder."""
    task = typescript_task(tmp_path)

    def forge_success_by_exiting_at_import(workdir: Path) -> None:
        (workdir / "calc.ts").write_text(
            "process.exit(0);\n\n" + typescript_tasks.SOLVED_CALC, encoding="utf-8"
        )

    assert resolved(task, forge_success_by_exiting_at_import) == 0.0


def test_agent_code_cannot_short_circuit_the_test_run_mid_run(
    tmp_path: Path,
) -> None:
    """The same class one step later: the exit is inside a function the
    grading test calls, so the run has really started before it is killed."""
    task = typescript_task(tmp_path)

    def forge_success_by_exiting_mid_run(workdir: Path) -> None:
        (workdir / "calc.ts").write_text(
            "export function half(x: number): number {\n  return x / 2;\n}\n\n"
            "export function ratio(a: number, b: number): number {\n"
            "  process.exit(0);\n"
            "  return a / b;\n}\n",
            encoding="utf-8",
        )

    assert resolved(task, forge_success_by_exiting_mid_run) == 0.0


def test_agent_written_node_configuration_changes_nothing_that_runs(
    tmp_path: Path,
) -> None:
    """`package.json`, `.npmrc` and `tsconfig.json` are the Node equivalents of
    the pytest configuration the Python runner pins away, and the false-negative
    direction is the one that bites: Node reads the module system off the
    nearest `package.json`, so an agent-written `"type": "commonjs"` makes every
    held-out `.test.ts` a syntax error and would sink a correct solution."""
    task = typescript_task(tmp_path)

    def solve_and_leave_configuration(workdir: Path) -> None:
        solve(workdir)
        (workdir / "package.json").write_text(
            '{"name": "agent", "type": "commonjs"}\n', encoding="utf-8"
        )
        (workdir / ".npmrc").write_text("registry=http://127.0.0.1:1\n")
        (workdir / "tsconfig.json").write_text(
            '{"compilerOptions": {"target": "es5", "strict": false}}\n', encoding="utf-8"
        )

    def leave_configuration_only(workdir: Path) -> None:
        (workdir / "package.json").write_text('{"type": "module"}\n', encoding="utf-8")
        (workdir / "tsconfig.json").write_text("{}\n", encoding="utf-8")

    assert resolved(task, solve_and_leave_configuration) == 1.0
    assert resolved(task, leave_configuration_only) == 0.0


def test_grading_that_never_finishes_is_unresolved_not_a_hang(tmp_path: Path) -> None:
    """`node --test` runs each file in a child process of its own, so a
    synchronous loop in agent code outlives killing the parent alone — the
    timeout kills the session as a group."""
    task = typescript_task(tmp_path)

    def loop_forever(workdir: Path) -> None:
        (workdir / "calc.ts").write_text(
            typescript_tasks.SOLVED_CALC + "\nwhile (true) {}\n", encoding="utf-8"
        )

    assert resolved(task, loop_forever, timeout_s=5) == 0.0


def test_a_genuine_solution_resolves_and_the_empty_diff_does_not(
    tmp_path: Path,
) -> None:
    """The control every forgery test above is read against: the verdict really
    does discriminate, so a 0.0 elsewhere in this suite means the forgery was
    refused rather than that nothing could ever pass."""
    task = typescript_task(tmp_path)

    assert resolved(task, solve) == 1.0
    assert resolved(task) == 0.0


def test_the_starting_repository_naming_invariant_has_no_typescript_analogue(
    tmp_path: Path,
) -> None:
    """Python's rule exists because grading puts the workdir on `sys.path`. Node
    reaches a builtin through a bare specifier and a repository module through a
    relative one, so a file cannot shadow a builtin however it is named — and a
    task whose repository is named after one loads rather than being refused."""
    task = typescript_task(
        tmp_path,
        repo=dict(DEFAULT_REPO) | {"assert.ts": "export const ok = true;\n"},
    )

    assert TYPESCRIPT.starting_repository_problem(task.repo_dir) is None
    assert resolved(task, solve) == 1.0


def test_the_source_primitives_are_answered_by_the_declaration_scan() -> None:
    """Responsibility 6 is the lint's half of the seam and landed with ticket 04
    (#101): the runner reads a file's declarations rather than refusing to. What
    that reading is — a method both qualified and bare, a class at the file's own
    top level, a file the scan cannot get through — is
    `tests/test_firstparty_v1_typescript_instruments.py`'s, beside the lint
    instruments that ask for it."""
    assert TYPESCRIPT.loads("export const x = 1;\n")
    assert TYPESCRIPT.defined_symbols("export const x = 1;\n") == {"x"}
    assert TYPESCRIPT.defined_classes("export class Basket {}\n") == {"Basket"}


def test_the_runner_kills_the_whole_session_it_started(tmp_path: Path) -> None:
    """What makes the timeout a verdict rather than a runaway: nothing the
    grading subprocess spawned is still running once the timeout has fired."""
    root = tmp_path / "root"
    workdir = root / "workdir"
    workdir.mkdir(parents=True)
    (workdir / "slow.test.ts").write_text(
        'import test from "node:test";\n\n'
        'test("spins", () => {\n'
        "  while (true) {}\n"
        "});\n",
        encoding="utf-8",
    )

    assert not TYPESCRIPT.run_tests(root, workdir, ["slow.test.ts"], timeout_s=5)

    survivors = subprocess.run(
        ["pgrep", "-f", str(workdir)], capture_output=True, text=True, check=False
    )
    assert survivors.stdout.strip() == "", survivors.stdout
