"""Pins the captured `codex exec --json` anchor and the `fake_codex` test
double written against it (tickets 04 / #90 of round 6). No adapter code
lives here — ticket 05 (#91) is the first consumer of both. The point of
this file is that a real CLI upgrade which reshapes the event stream fails
here, in a free test, rather than silently in a paid sweep.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from conftest import FakeCodex

ANCHOR = Path(__file__).parent / "fixtures" / "codex" / "exec-events.jsonl"
ANCHOR_METADATA = Path(__file__).parent / "fixtures" / "codex" / "metadata.json"

# The event types and usage keys the codex adapter (ticket 05) parses.
REQUIRED_EVENT_TYPES = {
    "thread.started",
    "turn.started",
    "item.completed",
    "turn.completed",
}
REQUIRED_ITEM_KINDS = {
    "agent_message",
    "command_execution",
    "file_change",
    "reasoning",
}
REQUIRED_USAGE_KEYS = {
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
}


def _load_anchor() -> list[dict[str, Any]]:
    lines = ANCHOR.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def _run_fake_codex(argv_log: Path, *extra_argv: str) -> subprocess.CompletedProcess[str]:
    script = argv_log.parent / "codex"
    return subprocess.run(
        [str(script), "exec", "--json", "-m", "gpt-5.6-terra", *extra_argv, "prompt"],
        capture_output=True,
        text=True,
        cwd=argv_log.parent,
        timeout=10,
    )


def _event_types(events: list[dict[str, Any]]) -> set[str]:
    return {event["type"] for event in events}


def _item_kinds(events: list[dict[str, Any]]) -> set[str]:
    return {
        event["item"]["type"]
        for event in events
        if event["type"] in ("item.completed", "item.started")
    }


def _usage_keys(events: list[dict[str, Any]]) -> set[str]:
    [usage] = [event["usage"] for event in events if event["type"] == "turn.completed"]
    return set(usage)


# --- the anchor itself ---------------------------------------------------


def test_anchor_parses_as_jsonl() -> None:
    events = _load_anchor()
    assert events  # non-empty: every line was valid JSON
    assert all(isinstance(event, dict) and "type" in event for event in events)


def test_anchor_carries_the_required_event_types() -> None:
    assert REQUIRED_EVENT_TYPES <= _event_types(_load_anchor())


def test_anchor_carries_the_required_item_kinds() -> None:
    assert REQUIRED_ITEM_KINDS <= _item_kinds(_load_anchor())


def test_anchor_turn_completed_usage_carries_the_required_keys() -> None:
    assert REQUIRED_USAGE_KEYS <= _usage_keys(_load_anchor())


def test_anchor_metadata_records_cli_version_and_capture_date() -> None:
    metadata = json.loads(ANCHOR_METADATA.read_text(encoding="utf-8"))
    assert metadata["cli_version"]
    assert metadata["captured_at"]


# --- the fake codex: identity, PATH, argv, cwd ----------------------------


def test_fake_codex_is_first_on_path_and_answers_version(fake_codex: FakeCodex) -> None:
    fake_codex("")
    resolved = shutil.which("codex")
    assert resolved is not None
    result = subprocess.run(
        [resolved, "--version"], capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "codex-cli" in result.stdout


def test_fake_codex_logs_its_argv(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex("")
    _run_fake_codex(argv_log, "--ignore-user-config")

    [argv] = [json.loads(line) for line in argv_log.read_text().splitlines()]
    assert argv[0] == "exec"
    assert "--ignore-user-config" in argv
    assert "--version" not in "".join(argv)  # the version probe is not logged


def test_fake_codex_acts_on_its_cwd(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex('(workdir / "made-by-act.txt").write_text("hi")\n')
    _run_fake_codex(argv_log)

    assert (argv_log.parent / "made-by-act.txt").read_text() == "hi"


# --- the fake's default stream, pinned against the anchor -----------------


def test_fake_codex_default_stream_matches_the_anchors_event_types(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex("")
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert result.returncode == 0
    assert _event_types(events) == _event_types(_load_anchor())


def test_fake_codex_default_stream_matches_the_anchors_item_kinds(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex("")
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert _item_kinds(events) == _item_kinds(_load_anchor())


def test_fake_codex_default_stream_matches_the_anchors_usage_keys(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex("")
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert _usage_keys(events) == _usage_keys(_load_anchor())


# --- the seven broken-run shapes, each on demand ---------------------------


def test_fake_codex_can_emit_an_unanswerable_approval_request(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex(
        'events.insert(-1, {"type": "item.completed", "item": {'
        '"id": "item_x", "type": "approval_request", "status": "pending", '
        '"message": "approval required; no approver available"}})\n'
    )
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert any(
        event["type"] == "item.completed"
        and event["item"]["type"] == "approval_request"
        for event in events
    )


def test_fake_codex_can_emit_a_failed_turn(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex(
        'events[-1] = {"type": "turn.failed", "error": {"message": "boom"}}\n'
    )
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert events[-1]["type"] == "turn.failed"
    assert not any(event["type"] == "turn.completed" for event in events)


def test_fake_codex_can_emit_an_error_event(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex(
        'events.append({"type": "error", "message": "stream error"})\n'
    )
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert any(event["type"] == "error" for event in events)


def test_fake_codex_can_exit_non_zero(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex("exit_code = 1\n")
    result = _run_fake_codex(argv_log)

    assert result.returncode == 1


def test_fake_codex_can_end_the_stream_without_a_turn_completed_event(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex("del events[-1]\n")
    result = _run_fake_codex(argv_log)
    events = [json.loads(line) for line in result.stdout.splitlines()]

    assert events  # the stream is not empty
    assert not any(event["type"] == "turn.completed" for event in events)


def test_fake_codex_can_emit_output_that_is_not_jsonl(fake_codex: FakeCodex) -> None:
    argv_log = fake_codex('raw_stdout = "not json at all\\n"\n')
    result = _run_fake_codex(argv_log)

    assert result.stdout == "not json at all\n"
    for line in result.stdout.splitlines():
        try:
            json.loads(line)
        except json.JSONDecodeError:
            return
    raise AssertionError("expected at least one non-JSON line")


def test_fake_codex_can_run_slow_enough_to_exceed_a_limit(
    fake_codex: FakeCodex,
) -> None:
    argv_log = fake_codex("time.sleep(2)\n")
    script = argv_log.parent / "codex"

    try:
        subprocess.run(
            [str(script), "exec", "--json", "-m", "gpt-5.6-terra", "prompt"],
            capture_output=True, text=True, cwd=argv_log.parent, timeout=0.5,
        )
        raise AssertionError("expected the run to still be going at the timeout")
    except subprocess.TimeoutExpired:
        pass
