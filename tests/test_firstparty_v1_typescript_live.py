"""The stdlib-only rule's consequence for the agent, plus the two live-seam
facts a TypeScript row owes (ticket 05 / #102).

Three things, over a synthetic TypeScript task (`tests/typescript_tasks.py`):

1. `node_modules/` never reaches the pristine commit or the captured diff, so
   a held-out test that imports a package the agent installed fails at grade
   time — the rule working, not a bug.
2. A TypeScript task's live run limit is its category's registered limit, or
   the flat default where its category has none — the same key a Python
   task's limit is read off, and no new limit is registered this round.
3. The same diff bytes grade to the same verdict whichever harness logged
   them, and a TypeScript row round-trips through `eval-v1 --replay` with
   `language: typescript` and `surface: application`.

The seams are the existing ones: `run_live` driven through the fake `claude`
and fake `codex` on `PATH` (`tests/conftest.py`'s `FakeClaude` and
`FakeCodex`; `tests/test_firstparty_v1_codex_adapter.py` is the worked
example), and `evaluate` for the byte-identical-verdict pair. No live agent,
LLM or network reached anywhere in this file.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import typescript_tasks
from conftest import FakeClaude, FakeCodex
from typescript_tasks import solve, typescript_task

from ai_benchmark import firstparty_v1
from ai_benchmark.agents import CODEX
from ai_benchmark.cli import main
from ai_benchmark.firstparty import RUN_TIMEOUT_S
from ai_benchmark.firstparty_v1 import evaluate, live_run_limit_s, run_live

SWEEP = "round-7-typescript-live"
CLAUDE_MODEL = "claude-sonnet-5"
CODEX_MODEL = "gpt-5.6-terra"

# What either fake agent writes when it solves the default task — the same
# solution `typescript_tasks.solve` writes, but as an act a fake CLI runs in
# its own subprocess, so the two harnesses can be made to produce byte-
# identical diffs.
SOLVE_ACT = (
    f'(workdir / "calc.ts").write_text({typescript_tasks.SOLVED_CALC!r}, '
    'encoding="utf-8")\n'
)


# --- node_modules: neither the pristine commit nor the captured diff ----------


def test_workdir_ignore_excludes_node_modules() -> None:
    assert "node_modules/" in firstparty_v1._WORKDIR_IGNORE


def test_an_installed_package_reaches_neither_the_pristine_commit_nor_the_captured_diff(
    tmp_path: Path,
) -> None:
    """`_WORKDIR_IGNORE` is written before the initial commit and restored
    before capture — proven directly against both git operations, not only
    against a live run's end result. A package already sitting in the
    workdir before the pristine commit (as a retried run might leave one)
    must not be committed, and one installed mid-run must not be captured."""
    task = typescript_task(tmp_path / "tasks")
    workdir = tmp_path / "workdir"
    shutil.copytree(task.repo_dir, workdir)
    package = workdir / "node_modules" / "left-pad"
    package.mkdir(parents=True)
    (package / "index.js").write_text("export function pad() {}\n", encoding="utf-8")

    initial = firstparty_v1._commit_pristine(task, workdir)
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", initial],
        cwd=workdir, capture_output=True, text=True, check=True,
    ).stdout
    assert "node_modules" not in tracked

    solve(workdir)  # a genuine edit, still made after the install
    diff = firstparty_v1._capture_workdir_diff(task, workdir, initial)

    assert "node_modules" not in diff
    assert "calc.ts" in diff  # the real edit still reaches the diff


LEFT_PAD_GRADING = {
    "calc.test.ts": """\
import test from "node:test";
import assert from "node:assert";
import { pad } from "left-pad";

test("left-pad is available once installed", () => {
  assert.strictEqual(pad("1", 3, "0"), "001");
});
"""
}

INSTALL_LEFT_PAD_ACT = """\
package = workdir / "node_modules" / "left-pad"
package.mkdir(parents=True)
(package / "package.json").write_text(
    '{"name": "left-pad", "version": "1.0.0", "type": "module", "main": "index.js"}\\n'
)
(package / "index.js").write_text(
    'export function pad(str, len, ch) {\\n'
    '  ch = ch || "0";\\n'
    '  str = String(str);\\n'
    '  while (str.length < len) str = ch + str;\\n'
    '  return str;\\n'
    '}\\n'
)
"""


def test_a_held_out_test_importing_an_agent_installed_package_fails_at_grade_time(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """The rule's stated consequence: an agent that installs a package mid-run
    logs a diff that never carries it, so a held-out test that imports it
    fails at grade time — even though the run itself, and the install inside
    it, both genuinely succeeded."""
    fake_claude(INSTALL_LEFT_PAD_ACT)
    task = typescript_task(tmp_path / "tasks", grading=LEFT_PAD_GRADING)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([task], [CLAUDE_MODEL], log, sweep=SWEEP)

    assert "node_modules" not in run.diff
    [record] = evaluate([task], [run], source=str(log))
    assert record.quality_value == 0.0


# --- the registered limit: category only, no new tier this round --------------


def test_no_new_limit_is_registered_this_round() -> None:
    assert firstparty_v1.LIVE_RUN_LIMITS_S == {
        "bug-fix": 600,
        "fault-location": 600,
        "code-review": 600,
        "codebase-comprehension": 600,
    }


def test_a_typescript_tasks_live_run_limit_resolves_through_its_category_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Keyed on `task.category` and nothing else — not on `task.language` —
    so a TypeScript task takes the same tier a Python task of the same
    category would, and falls back to the flat default exactly as one
    would."""
    monkeypatch.setitem(firstparty_v1.LIVE_RUN_LIMITS_S, "bug-fix", 42)
    tiered = typescript_task(
        tmp_path / "tiered", task_id="ts-bugfix", category="bug-fix",
    )
    untiered = typescript_task(
        tmp_path / "untiered", task_id="ts-feature", category="feature-dev",
    )

    assert live_run_limit_s(tiered) == 42
    assert live_run_limit_s(untiered) == RUN_TIMEOUT_S


def spy_on_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record every `claude` child the adapter spawns, and still spawn it."""
    calls: list[dict[str, Any]] = []
    real = subprocess.run

    def spy(*args: Any, **kwargs: Any) -> Any:
        command = list(args[0]) if args else list(kwargs.get("args", []))
        if command[:2] == ["claude", "-p"]:
            calls.append({"command": command, "kwargs": dict(kwargs)})
        return real(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    return calls


def test_the_registered_limit_reaches_the_live_invocation_for_a_typescript_task(
    fake_claude: FakeClaude, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wiring, not just arithmetic: the value `live_run_limit_s` computes is
    what actually bounds the child claude-code process for a TypeScript
    task, exactly as it would for a Python one."""
    fake_claude("")
    calls = spy_on_subprocess(monkeypatch)
    task = typescript_task(tmp_path / "tasks", category="bug-fix")

    run_live([task], [CLAUDE_MODEL], tmp_path / "runs.jsonl", sweep=SWEEP)

    [call] = calls
    assert call["kwargs"]["timeout"] == live_run_limit_s(task) == 600  # registered


# --- one diff, either harness, the same verdict --------------------------------


def test_the_same_typescript_diff_grades_the_same_verdict_from_either_harness(
    fake_codex: FakeCodex, fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """The graded artifact is the diff, and grading never learns which harness
    produced it — round 6's expensive assumption, held in the second
    language."""
    fake_codex(SOLVE_ACT)
    fake_claude(SOLVE_ACT)
    task = typescript_task(tmp_path / "tasks")

    codex_log = tmp_path / "codex.jsonl"
    [codex_run] = run_live(
        [task], [CODEX_MODEL], codex_log, sweep=SWEEP, agent=CODEX,
    )
    claude_log = tmp_path / "claude.jsonl"
    [claude_run] = run_live(
        [task], [CLAUDE_MODEL], claude_log, sweep=SWEEP, agent="claude-code",
    )

    assert codex_run.diff == claude_run.diff  # the same bytes
    graded = {
        record.agent: record.quality_value
        for log, run in ((codex_log, codex_run), (claude_log, claude_run))
        for record in evaluate([task], [run], source=str(log))
    }
    assert graded == {CODEX: 1.0, "claude-code": 1.0}


# --- the round trip -------------------------------------------------------------


def test_a_typescript_row_round_trips_through_replay_with_its_language_and_surface(
    fake_claude: FakeClaude, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Replayed by `eval-v1 --replay`, a TypeScript row grades through the
    TypeScript runner — no different from any other row reaching that CLI —
    and its record still carries the language and surface the task declared."""
    fake_claude(SOLVE_ACT)
    tasks_dir = tmp_path / "tasks"
    typescript_task(tasks_dir)
    log = tmp_path / "runs.jsonl"

    main([
        "eval-v1", "--tasks", str(tasks_dir), "--live",
        "--agent", "claude-code", "--model", CLAUDE_MODEL,
        "--log", str(log), "--sweep", SWEEP,
        "--data", str(tmp_path / "unified.jsonl"),
    ])
    capsys.readouterr()

    replayed = tmp_path / "replayed.jsonl"
    main([
        "eval-v1", "--tasks", str(tasks_dir), "--replay", str(log),
        "--data", str(replayed),
    ])

    assert "evaluated 1 runs over 1 tasks (1 resolved)" in capsys.readouterr().out
    [record] = [json.loads(line) for line in replayed.read_text().splitlines()]
    assert record["language"] == "typescript"
    assert record["surface"] == "application"
