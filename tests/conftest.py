import os
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# A stand-in claude CLI for live-runner tests: no live agent is ever run.
# It answers --version, appends its argv to a log for assertions, acts on its
# cwd the way a tools-enabled agent would (the `act` hole is Python source
# with `model`, `workdir` and `denials` in scope), and prints the payload
# shape of the captured anchor fixtures/firstparty/claude-result.json —
# numbers adjusted, structure identical — so the fake cannot drift from the
# real CLI without the anchor drifting first.
_FAKE_CLAUDE = '''\
#!/usr/bin/env python3
import json
import sys
import time  # noqa: F401  (acts may sleep to simulate a slow run)
from pathlib import Path

if "--version" in sys.argv:
    print("2.1.220 (Claude Code)")
    raise SystemExit(0)

with open({argv_log!r}, "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")

model = sys.argv[sys.argv.index("--model") + 1]
workdir = Path.cwd()
denials = []
{act}
print(json.dumps({{
    "is_error": False,
    "duration_api_ms": 41800,
    "num_turns": 6,
    "stop_reason": "end_turn",
    "session_id": "da4cee36-70ac-41e5-a54c-e71da768317b",
    "total_cost_usd": 0.19,
    "usage": {{"input_tokens": 12, "cache_creation_input_tokens": 30000,
               "cache_read_input_tokens": 11000, "output_tokens": 900,
               "server_tool_use": {{"web_search_requests": 0,
                                    "web_fetch_requests": 0}},
               "service_tier": "standard", "inference_geo": "not_available",
               "speed": "standard"}},
    "permission_denials": denials,
    "terminal_reason": "completed",
    "subtype": "success",
    "api_error_status": None,
    "result": "done",
    "duration_ms": 42500,
    "type": "result",
    "uuid": "6cf23113-6af6-4347-a470-81c13eed620e",
}}))
'''

FakeClaude = Callable[[str], Path]


@pytest.fixture
def fake_claude(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> FakeClaude:
    """Put a fake claude executable first on PATH; returns its argv log."""

    def install(act: str = "") -> Path:
        bin_dir = tmp_path_factory.mktemp("fake-claude-bin")
        argv_log = bin_dir / "argv.jsonl"
        script = bin_dir / "claude"
        script.write_text(
            _FAKE_CLAUDE.format(argv_log=str(argv_log), act=textwrap.dedent(act))
        )
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        return argv_log

    return install


# A stand-in codex CLI for live-runner tests: no live agent is ever run.
# It answers --version, appends its argv to a log for assertions, acts on
# its cwd the way a tools-enabled agent would (the `act` hole is Python
# source with `model`, `workdir`, `events`, `exit_code` and `raw_stdout` in
# scope), and by default emits the event types, item kinds and usage keys of
# the captured anchor tests/fixtures/codex/exec-events.jsonl — numbers
# adjusted, structure identical — so the fake cannot drift from the real CLI
# without the anchor drifting first. `act` can rewrite `events` (a plain
# list of event dicts, mutable in place), set `exit_code`, or set
# `raw_stdout` to replace the JSONL stream outright — that is how a test
# asks for one of the broken-run shapes the codex adapter has to detect: an
# unanswerable approval request, a failed turn, a top-level error event, a
# non-zero exit, a stream missing its closing turn-completed event, output
# that is not JSONL at all, or (via time.sleep) a run slow enough to exceed
# a limit.
_FAKE_CODEX = '''\
#!/usr/bin/env python3
import json
import sys
import time  # noqa: F401  (acts may sleep to simulate a slow run)
from pathlib import Path

if "--version" in sys.argv:
    print("codex-cli 9.9.9 (fake)")
    raise SystemExit(0)

with open({argv_log!r}, "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")


def _flag(*names):
    for name in names:
        if name in sys.argv:
            return sys.argv[sys.argv.index(name) + 1]
    return None


model = _flag("-m", "--model")
workdir = Path.cwd()
exit_code = 0
raw_stdout = None
events = [
    {{"type": "thread.started", "thread_id": "fake-thread-0000"}},
    {{"type": "turn.started"}},
    {{"type": "item.completed", "item": {{"id": "item_0", "type": "reasoning",
        "text": "**Planning the requested change**"}}}},
    {{"type": "item.completed", "item": {{"id": "item_1", "type": "agent_message",
        "text": "Working on it."}}}},
    {{"type": "item.started", "item": {{"id": "item_2", "type": "file_change",
        "changes": [{{"path": str(workdir / "notes.txt"), "kind": "add"}}],
        "status": "in_progress"}}}},
    {{"type": "item.completed", "item": {{"id": "item_2", "type": "file_change",
        "changes": [{{"path": str(workdir / "notes.txt"), "kind": "add"}}],
        "status": "completed"}}}},
    {{"type": "item.started", "item": {{"id": "item_3", "type": "command_execution",
        "command": "/bin/zsh -lc 'cat notes.txt'", "aggregated_output": "",
        "exit_code": None, "status": "in_progress"}}}},
    {{"type": "item.completed", "item": {{"id": "item_3", "type": "command_execution",
        "command": "/bin/zsh -lc 'cat notes.txt'", "aggregated_output": "hello anchor\\n",
        "exit_code": 0, "status": "completed"}}}},
    {{"type": "item.completed", "item": {{"id": "item_4", "type": "agent_message",
        "text": "Done."}}}},
    {{"type": "turn.completed", "usage": {{"input_tokens": 500, "cached_input_tokens": 200,
        "cache_write_input_tokens": 0, "output_tokens": 90, "reasoning_output_tokens": 12}}}},
]
{act}

if raw_stdout is not None:
    sys.stdout.write(raw_stdout)
else:
    for event in events:
        print(json.dumps(event))
raise SystemExit(exit_code)
'''

FakeCodex = Callable[[str], Path]


@pytest.fixture
def fake_codex(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> FakeCodex:
    """Put a fake codex executable first on PATH; returns its argv log."""

    def install(act: str = "") -> Path:
        bin_dir = tmp_path_factory.mktemp("fake-codex-bin")
        argv_log = bin_dir / "argv.jsonl"
        script = bin_dir / "codex"
        script.write_text(
            _FAKE_CODEX.format(argv_log=str(argv_log), act=textwrap.dedent(act))
        )
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
        return argv_log

    return install


@pytest.fixture
def swebench_fixture() -> Path:
    return FIXTURES / "swebench"


@pytest.fixture
def dataset_fixture() -> Path:
    return FIXTURES / "unified.jsonl"


@pytest.fixture
def classified_fixture() -> Path:
    return FIXTURES / "classified.jsonl"


@pytest.fixture
def aggregates_fixture() -> Path:
    return FIXTURES / "aggregates.jsonl"


@pytest.fixture
def aider_fixture() -> Path:
    return FIXTURES / "aider"


@pytest.fixture
def pareto_fixture() -> Path:
    return FIXTURES / "pareto.jsonl"


@pytest.fixture
def firstparty_fixture() -> Path:
    return FIXTURES / "firstparty" / "runs.jsonl"


@pytest.fixture
def firstparty_v1_fixture() -> Path:
    return FIXTURES / "firstparty-v1" / "runs.jsonl"
