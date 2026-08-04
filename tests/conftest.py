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
