"""The `codex` adapter: round 6's one instrument, and the second **agent
adapter** the v1 live runner can be pointed at (ticket 05 / #91).

Everything here runs through the seams the spec already fixes and no new one:
`ai-bench eval-v1 --live --agent codex …` through the CLI's `main` with the
fake `codex` of ticket 04 first on `PATH`, and `eval-v1 --replay` over the log
that run wrote. No live agent, no LLM and no network is reached — the fake's
default stream is the captured anchor's shape with the numbers adjusted, so a
real CLI upgrade that reshapes the stream fails in `test_codex_anchor.py`
rather than here or, worse, in a paid sweep.
"""

import inspect
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeClaude, FakeCodex
from firstparty_v1_tasks import task_by_id

from ai_benchmark import firstparty_v1
from ai_benchmark.agents import (
    CODEX,
    CODEX_REASONING_LEVELS,
    CodexAdapter,
    adapter_for,
    codex_reasoning_level,
)
from ai_benchmark.cli import main
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import local_today
from ai_benchmark.firstparty_v1 import live_run_limit_s, load_runs, run_live

CHECKED_IN = Path(__file__).parent.parent / "tasks" / "first-party-v1"
ANCHOR = Path(__file__).parent / "fixtures" / "codex" / "exec-events.jsonl"

SEED = "wordcount-top-words"
SWEEP = "round-6-codex"
MODEL = "gpt-5.6-terra"

# The fake's default stream, straight from the anchor's shape: five completed
# items (one of them a reasoning item) and one turn-completed event carrying
# usage. What the adapter must make of it.
FAKE_OUTPUT = "Done."
FAKE_TOKENS_IN = 500  # the input *total*; the 200 cached tokens are inside it
FAKE_TOKENS_OUT = 90  # the output total; the 12 reasoning tokens are inside it
FAKE_TURNS = 4  # five completed items, minus the reasoning item

# What the fake agent appends to wordcount.py when it solves the seed task —
# the same solution the claude-code live-runner tests use, so the two
# harnesses can be made to write byte-identical diffs.
SOLUTION = (
    "\n\ndef top_words(text, n):\n"
    "    counts = word_counts(text)\n"
    "    return sorted(counts, key=lambda w: (-counts[w], w))[:n]\n"
)

SOLVE_ACT = f"""\
with open(workdir / "wordcount.py", "a") as source:
    source.write({SOLUTION!r})
"""


def seed_tasks(tmp_path: Path) -> Path:
    """A one-task task set: the whole corpus would grade for minutes."""
    tasks = tmp_path / "tasks"
    shutil.copytree(CHECKED_IN / SEED, tasks / SEED)
    return tasks


def live(tmp_path: Path, *extra: str, model: str = MODEL, agent: str = CODEX) -> Path:
    """One `eval-v1 --live` invocation through the CLI; returns its log path."""
    log = tmp_path / "runs.jsonl"
    main([
        "eval-v1", "--tasks", str(seed_tasks(tmp_path)), "--live",
        "--agent", agent, "--model", model,
        "--log", str(log), "--sweep", SWEEP,
        "--data", str(tmp_path / "unified.jsonl"), *extra,
    ])
    return log


def logged_argv(argv_log: Path) -> list[str]:
    [argv] = [json.loads(line) for line in argv_log.read_text().splitlines()]
    return list(argv)


def spy_on_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record every `codex exec` child the adapter spawns, and still spawn it.

    The two things this pins — the child's stdin and the timeout in force —
    are arguments to the child, not text in its argv, so the argv log the fake
    keeps cannot show them.
    """
    calls: list[dict[str, Any]] = []
    real = subprocess.run

    def spy(*args: Any, **kwargs: Any) -> Any:
        command = list(args[0]) if args else list(kwargs.get("args", []))
        if command[:2] == ["codex", "exec"]:
            cwd = Path(kwargs["cwd"])
            calls.append({
                "command": command,
                "kwargs": dict(kwargs),
                # Snapshotted now, not read back later: the runner's workdir is
                # a temp directory it deletes as soon as the run is captured.
                "cwd_contents": sorted(entry.name for entry in cwd.iterdir()),
            })
        return real(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    return calls


# --- the live run, end to end -------------------------------------------------


def test_a_live_codex_run_appends_a_row_with_the_streams_measurements(
    fake_codex: FakeCodex, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """`--agent codex` drives `codex exec --json` in the prepared workdir and
    lands one replayable row, parsed as the spec says: the last agent
    message's text, the input and output totals with their cached and
    reasoning subsets counted once, the completed non-reasoning items as
    turns, and the adapter's own wall clock as latency."""
    fake_codex(SOLVE_ACT)

    log = live(tmp_path)

    assert "ran 1 live runs; raw log written to" in capsys.readouterr().out
    [run] = load_runs(log)
    assert run.agent == CODEX
    assert run.model == MODEL
    assert run.task_id == SEED
    assert run.output == FAKE_OUTPUT
    assert run.tokens_in == FAKE_TOKENS_IN
    assert run.tokens_out == FAKE_TOKENS_OUT
    assert run.turns == FAKE_TURNS
    # The stream carries no duration, so latency is what the adapter watched.
    assert run.latency_s > 0
    assert run.sweep == SWEEP
    assert "def top_words" in run.diff


def test_agent_version_is_codex_version_as_printed(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex("")

    [run] = load_runs(live(tmp_path))

    assert run.agent_version == "codex-cli 9.9.9 (fake)"


def test_the_sweep_id_is_stamped_on_every_codex_row(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """The sweep id is the runner's, not the adapter's — a second harness does
    not get its own round key."""
    fake_codex("")
    log = tmp_path / "runs.jsonl"

    runs = run_live(
        [task_by_id(SEED)], [MODEL], log, sweep="round-6-track-a", agent=CODEX,
    )

    assert [run.sweep for run in runs] == ["round-6-track-a"]
    assert [run.sweep for run in load_runs(log)] == ["round-6-track-a"]


# --- the invocation -----------------------------------------------------------


def test_the_argv_carries_the_registered_combination_and_the_grant(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """Non-interactive exec, JSONL events, the registered model *and* its
    registered reasoning level passed explicitly, the operator's own
    configuration ignored, an ephemeral session that leaves nothing on the
    machine, and the same blanket grant claude-code runs under — the two
    harnesses must be measured under one permission stance or the harness
    contrast measures the stance instead."""
    argv_log = fake_codex("")

    live(tmp_path)

    argv = logged_argv(argv_log)
    assert argv[0] == "exec"
    assert "--json" in argv
    assert argv[argv.index("-m") + 1] == MODEL
    assert argv[argv.index("-c") + 1] == "model_reasoning_effort=medium"
    assert "--ignore-user-config" in argv
    assert "--ephemeral" in argv
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert argv[-1] == task_by_id(SEED).prompt
    # Nothing narrower than the blanket grant, and no sandbox re-imposed under
    # it: a per-tool allowlist is what aborted a real claude-code sweep.
    assert "-s" not in argv
    assert "--sandbox" not in argv
    assert "--approve-for-me" not in argv


def test_the_childs_stdin_is_closed(
    fake_codex: FakeCodex, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`codex exec` reads its instructions from stdin when it is given none as
    an argument, so a child that inherited a terminal is a run that hangs
    inside the sweep's own timeout instead of finishing."""
    fake_codex("")
    calls = spy_on_subprocess(monkeypatch)

    live(tmp_path)

    [call] = calls
    assert call["kwargs"]["stdin"] == subprocess.DEVNULL


def test_the_run_is_made_in_the_prepared_workdir(
    fake_codex: FakeCodex, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The workdir is the runner's, seeded from the starting repository; the
    adapter is handed it and runs the child there, which is why what the fake
    writes to its cwd reaches the run's diff."""
    fake_codex('(workdir / "made-in-the-workdir.txt").write_text("hi")\n')
    calls = spy_on_subprocess(monkeypatch)

    [run] = load_runs(live(tmp_path))

    [call] = calls
    # The child was started in a directory already holding the pristine
    # starting repository — the runner's, prepared before the adapter is called.
    assert "wordcount.py" in call["cwd_contents"]
    assert "made-in-the-workdir.txt" not in call["cwd_contents"]
    # And what it wrote there reached the graded artifact.
    assert "made-in-the-workdir.txt" in run.diff


# --- the limit ----------------------------------------------------------------


def test_the_limit_in_force_is_the_task_classs_registered_one(
    fake_codex: FakeCodex, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter is handed the limit and never chooses one: a cell may not
    be given a longer or shorter run because of which harness ran it."""
    fake_codex("")
    calls = spy_on_subprocess(monkeypatch)

    live(tmp_path)

    [call] = calls
    assert call["kwargs"]["timeout"] == live_run_limit_s(task_by_id(SEED))


def test_no_caller_can_pass_a_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raising the limit for the one cell about to hit it spends that cell,
    only ever swept once, under conditions nobody chose in advance — so there
    is no seam to raise it through: not on the runner, not on the CLI."""
    assert set(inspect.signature(run_live).parameters) == {
        "tasks", "models", "log_path", "sweep", "agent",
    }
    with pytest.raises(SystemExit):
        main(["eval-v1", "--help"])
    help_text = capsys.readouterr().out
    assert "--timeout" not in help_text
    assert "--limit" not in help_text


def test_the_live_run_time_limit_expiring_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """Called through the adapter rather than the runner, because the seed
    task's registered limit is ten minutes and no test may wait for it."""
    fake_codex("time.sleep(30)\n")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    with pytest.raises(IngestError, match="timed out after 1s"):
        CodexAdapter().run(
            SEED, "prompt", MODEL, workdir,
            agent_version="codex-cli 9.9.9 (fake)",
            as_of=local_today(), limit_s=1,
        )


# --- the registered combination -----------------------------------------------


def test_exactly_one_codex_combination_is_registered() -> None:
    """Admitting a combination to a reading is a decision, never an accident
    of what a CLI's configuration defaulted to."""
    assert CODEX_REASONING_LEVELS == {"gpt-5.6-terra": "medium"}
    assert adapter_for(CODEX).name == CODEX


def test_an_unregistered_codex_model_is_refused_before_anything_runs(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    argv_log = fake_codex("")
    log = tmp_path / "runs.jsonl"

    with pytest.raises(SystemExit, match="gpt-5.6-mars"):
        main([
            "eval-v1", "--tasks", str(seed_tasks(tmp_path)), "--live",
            "--agent", CODEX, "--model", "gpt-5.6-mars",
            "--log", str(log), "--sweep", SWEEP,
            "--data", str(tmp_path / "unified.jsonl"),
        ])

    assert not argv_log.exists()  # the CLI was never invoked
    assert not log.exists()


def test_a_claude_model_under_agent_codex_is_refused_before_anything_runs(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """The realistic mistake: `--agent codex` with the ladder's own models,
    which are what `--model` defaults to."""
    argv_log = fake_codex("")
    log = tmp_path / "runs.jsonl"

    with pytest.raises(SystemExit, match="claude-sonnet-5"):
        main([
            "eval-v1", "--tasks", str(seed_tasks(tmp_path)), "--live",
            "--agent", CODEX, "--model", "claude-sonnet-5",
            "--log", str(log), "--sweep", SWEEP,
            "--data", str(tmp_path / "unified.jsonl"),
        ])

    assert not argv_log.exists()
    assert not log.exists()


def test_run_live_refuses_an_unregistered_model_before_it_opens_the_log(
    tmp_path: Path,
) -> None:
    """Refused before the log exists, so a sweep cannot be half-written by the
    time the refusal lands."""
    log = tmp_path / "runs.jsonl"

    with pytest.raises(IngestError, match="registered combinations"):
        run_live([task_by_id(SEED)], ["gpt-5.6-mars"], log, sweep=SWEEP, agent=CODEX)

    assert not log.exists()


def test_an_unregistered_reasoning_level_cannot_be_asked_for(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The spec does not say how the level is passed on the command line and
    this ticket invents no flag for it: the registered level rides with the
    registered model, so the only way to reach a level is to name a model, and
    an unregistered model is refused. `--model` stays the only model-facing
    flag `eval-v1` has."""
    assert codex_reasoning_level(MODEL) == "medium"
    with pytest.raises(IngestError, match="registered combinations"):
        codex_reasoning_level("gpt-5.6-terra-high")

    # No seam takes one: not the adapter's run(), not the CLI.
    assert set(inspect.signature(CodexAdapter.run).parameters) == {
        "self", "task_id", "prompt", "model", "workdir",
        "agent_version", "as_of", "limit_s",
    }
    with pytest.raises(SystemExit):
        main(["eval-v1", "--help"])
    assert "reasoning" not in capsys.readouterr().out


# --- the cost -----------------------------------------------------------------

# The checked-in price table (data/price-table.json, version
# openai-pricing-2026-08-18.1), written out here as the four prices it
# carries: Standard, short context, per 1M tokens, read 2026-08-18 from
# https://platform.openai.com/docs/pricing. Written out rather than loaded so
# that the arithmetic below is a hand computation against the checked-in
# numbers — a price change has to be made here too, deliberately.
PRICE_TABLE_VERSION = "openai-pricing-2026-08-18.1"
PLAIN_INPUT_PER_TOKEN = 2.00 / 1_000_000
CACHED_INPUT_PER_TOKEN = 0.20 / 1_000_000
CACHE_WRITE_INPUT_PER_TOKEN = 2.50 / 1_000_000
OUTPUT_PER_TOKEN = 12.00 / 1_000_000


def anchor_usage() -> dict[str, int]:
    """The captured anchor's own turn-completed usage."""
    events = [json.loads(line) for line in ANCHOR.read_text().splitlines()]
    [usage] = [
        event["usage"] for event in events if event["type"] == "turn.completed"
    ]
    return dict(usage)


def usage_act(usage: dict[str, int]) -> str:
    """An act that makes the fake's turn-completed event carry this usage."""
    return f'events[-1]["usage"] = {usage!r}\n'


def test_cost_usd_is_the_hand_computation_from_the_anchors_usage(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """Codex prints no dollar figure of its own, so `cost_usd` is the price
    table applied to the usage breakdown at write time, by the derivation
    #96 fixed: plain input is the input total less the cached and cache-write
    subsets, each of the three priced at its own rate, and the output total
    priced once with its reasoning tokens inside it and never twice."""
    usage = anchor_usage()
    fake_codex(usage_act(usage))

    [run] = load_runs(live(tmp_path))

    plain = (
        usage["input_tokens"]
        - usage["cached_input_tokens"]
        - usage["cache_write_input_tokens"]
    )
    expected = (
        plain * PLAIN_INPUT_PER_TOKEN
        + usage["cached_input_tokens"] * CACHED_INPUT_PER_TOKEN
        + usage["cache_write_input_tokens"] * CACHE_WRITE_INPUT_PER_TOKEN
        + usage["output_tokens"] * OUTPUT_PER_TOKEN
    )
    assert run.cost_usd == pytest.approx(expected)
    # And the row says how that number was made, so a cross-agent cost reading
    # can say the two figures were made differently.
    assert run.cost_source == "table-derived"
    assert run.price_table == PRICE_TABLE_VERSION


def test_the_hand_computations_prices_are_the_checked_in_ones() -> None:
    """The arithmetic above is only a check on the adapter if its numbers are
    the table's: a price edit that reached the data and not this file would
    otherwise leave the test passing against a table nobody swept under."""
    table = CodexAdapter().table
    prices = table.models[MODEL]

    assert table.version == PRICE_TABLE_VERSION
    assert prices.input_uncached_per_token == pytest.approx(PLAIN_INPUT_PER_TOKEN)
    assert prices.input_cached_per_token == pytest.approx(CACHED_INPUT_PER_TOKEN)
    assert prices.input_cache_write_per_token == pytest.approx(
        CACHE_WRITE_INPUT_PER_TOKEN
    )
    assert prices.output_per_token == pytest.approx(OUTPUT_PER_TOKEN)


def test_a_price_table_that_will_not_load_stops_the_sweep_before_it_is_paid_for(
    tmp_path: Path,
) -> None:
    """The table is consulted at the same moment the combination is — before
    the first workdir — because the only thing left to do with a measured run
    that cannot be priced is throw it away."""
    adapter = CodexAdapter(price_table_path=tmp_path / "not-a-table.json")

    with pytest.raises(IngestError, match="cannot read price table"):
        adapter.check_models([MODEL])


def test_cache_write_tokens_are_priced_at_their_own_rate(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """The anchor's own run cache-wrote nothing, so the fourth price would go
    unexercised by that arithmetic alone."""
    usage = {
        "input_tokens": 1000, "cached_input_tokens": 400,
        "cache_write_input_tokens": 100, "output_tokens": 200,
        "reasoning_output_tokens": 50,
    }
    fake_codex(usage_act(usage))

    [run] = load_runs(live(tmp_path))

    expected = (
        500 * PLAIN_INPUT_PER_TOKEN
        + 400 * CACHED_INPUT_PER_TOKEN
        + 100 * CACHE_WRITE_INPUT_PER_TOKEN
        + 200 * OUTPUT_PER_TOKEN
    )
    assert run.cost_usd == pytest.approx(expected)
    assert run.tokens_in == 1000  # the total, cached and cache-write inside it
    assert run.tokens_out == 200  # the total, reasoning inside it


def test_replay_never_recomputes_a_logged_cost(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """`cost_usd` is whatever the row says: a later price table reprices
    nothing already logged, so the number survives a round trip untouched."""
    fake_codex(usage_act(anchor_usage()))
    log = live(tmp_path)
    before = json.loads(log.read_text().splitlines()[0])

    [run] = load_runs(log)

    assert run.cost_usd == before["cost_usd"]
    assert run.price_table == before["price_table"] == PRICE_TABLE_VERSION


# --- what the parsing means ---------------------------------------------------


def test_cached_input_tokens_are_counted_once_inside_the_input_total(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """They are a priced-differently subset of the total, not an addend — so
    `tokens_in` means on a codex row what it means on a claude-code one: every
    cost-bearing input token, once."""
    fake_codex(usage_act({
        "input_tokens": 800, "cached_input_tokens": 800,
        "cache_write_input_tokens": 0, "output_tokens": 10,
        "reasoning_output_tokens": 0,
    }))

    [run] = load_runs(live(tmp_path))

    assert run.tokens_in == 800
    assert run.cost_usd == pytest.approx(
        800 * CACHED_INPUT_PER_TOKEN + 10 * OUTPUT_PER_TOKEN
    )


def test_reasoning_tokens_are_counted_once_inside_the_output_total(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex(usage_act({
        "input_tokens": 100, "cached_input_tokens": 0,
        "cache_write_input_tokens": 0, "output_tokens": 300,
        "reasoning_output_tokens": 300,
    }))

    [run] = load_runs(live(tmp_path))

    assert run.tokens_out == 300
    assert run.cost_usd == pytest.approx(
        100 * PLAIN_INPUT_PER_TOKEN + 300 * OUTPUT_PER_TOKEN
    )


def test_usage_sums_across_more_than_one_turn_completed_event(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """A run that took more than one turn is measured, and priced, on all of
    it."""
    fake_codex(
        'events.append({"type": "turn.started"})\n'
        'events.append({"type": "item.completed", "item": {"id": "item_5",'
        ' "type": "agent_message", "text": "Second turn done."}})\n'
        'events.append({"type": "turn.completed", "usage": {'
        '"input_tokens": 1000, "cached_input_tokens": 0,'
        ' "cache_write_input_tokens": 0, "output_tokens": 10,'
        ' "reasoning_output_tokens": 0}})\n'
    )

    [run] = load_runs(live(tmp_path))

    assert run.tokens_in == FAKE_TOKENS_IN + 1000
    assert run.tokens_out == FAKE_TOKENS_OUT + 10
    assert run.output == "Second turn done."  # the *last* agent message
    assert run.turns == FAKE_TURNS + 1


def test_turns_count_the_completed_items_that_are_not_reasoning(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """A reasoning item is the model thinking, not an action it took."""
    fake_codex(
        'events.insert(-1, {"type": "item.completed", "item": {"id": "item_9",'
        ' "type": "reasoning", "text": "**More thinking**"}})\n'
    )

    [run] = load_runs(live(tmp_path))

    assert run.turns == FAKE_TURNS


def test_only_completed_items_count_as_turns(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """The stream announces an item twice — started, then completed — and the
    fake's default stream carries two such pairs."""
    started = [
        line for line in ANCHOR.read_text().splitlines()
        if json.loads(line)["type"] == "item.started"
    ]
    assert started  # the anchor really does carry the started half
    fake_codex("")

    [run] = load_runs(live(tmp_path))

    assert run.turns == FAKE_TURNS


# --- the seven broken-run signals ---------------------------------------------
#
# Each says the harness, not the model, ended the run — exactly what
# claude-code's permission_denials rule says. Each raises loudly and leaves
# the log without a row: a blocked run is a broken run, not a verdict.


def assert_broken(tmp_path: Path, match: str) -> None:
    """The run raises, and the log is left without a row — which for a signal
    the runner meets before it opens the log at all means no log."""
    log = tmp_path / "runs.jsonl"
    with pytest.raises(IngestError, match=match):
        run_live([task_by_id(SEED)], [MODEL], log, sweep=SWEEP, agent=CODEX)
    assert (load_runs(log) if log.exists() else []) == []


def test_an_unanswerable_approval_request_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """There is no approver behind a headless sweep, so the run is waiting on
    a person who is not there."""
    fake_codex(
        'events.insert(-1, {"type": "item.completed", "item": {'
        '"id": "item_x", "type": "approval_request", "status": "pending", '
        '"message": "approval required; no approver available"}})\n'
    )

    assert_broken(tmp_path, "approval")


def test_a_failed_turn_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex('events[-1] = {"type": "turn.failed", "error": {"message": "boom"}}\n')

    assert_broken(tmp_path, "failed turn")


def test_an_error_event_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex('events.append({"type": "error", "message": "stream error"})\n')

    assert_broken(tmp_path, "stream error")


def test_a_non_zero_exit_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex("exit_code = 3\n")

    assert_broken(tmp_path, "exited 3")


def test_a_stream_that_never_completes_its_turn_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """The run did not finish, so whatever it did measure is not a verdict."""
    fake_codex("del events[-1]\n")

    assert_broken(tmp_path, "no turn-completed event")


def test_output_that_is_not_jsonl_is_a_broken_run(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    fake_codex('raw_stdout = "not json at all\\n"\n')

    assert_broken(tmp_path, "not JSONL")


def test_an_absent_cli_is_a_broken_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No fake is installed and PATH holds nothing: a sweep that cannot find
    its harness stops rather than logging a run of nothing."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    assert_broken(tmp_path, "cannot run the codex CLI")


# --- replay -------------------------------------------------------------------


def test_replay_grades_a_codex_rows_diff_through_the_identical_pipeline(
    fake_codex: FakeCodex, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Nothing about grading is the adapter's: the row carries a workdir diff
    like any other, and `--replay` applies it, overlays the held-out tests and
    runs them — no agent, no LLM, no network."""
    fake_codex(SOLVE_ACT)
    log = live(tmp_path)
    capsys.readouterr()

    main([
        "eval-v1", "--tasks", str(tmp_path / "tasks"), "--replay", str(log),
        "--data", str(tmp_path / "replayed.jsonl"),
    ])

    assert "evaluated 1 runs over 1 tasks (1 resolved)" in capsys.readouterr().out


def test_the_same_bytes_from_either_harness_grade_the_same_verdict(
    fake_codex: FakeCodex, fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """The graded artifact is the diff, and grading never learns which harness
    produced it — which is what makes a harness contrast a contrast."""
    fake_codex(SOLVE_ACT)
    fake_claude(SOLVE_ACT)
    tasks = [task_by_id(SEED)]

    codex_log = tmp_path / "codex.jsonl"
    [codex_run] = run_live(tasks, [MODEL], codex_log, sweep=SWEEP, agent=CODEX)
    claude_log = tmp_path / "claude.jsonl"
    [claude_run] = run_live(
        tasks, ["claude-sonnet-5"], claude_log, sweep=SWEEP, agent="claude-code",
    )

    assert codex_run.diff == claude_run.diff  # the same bytes
    graded = {
        record.agent: record.quality_value
        for log, run in ((codex_log, codex_run), (claude_log, claude_run))
        for record in firstparty_v1.evaluate(tasks, [run], source=str(log))
    }
    assert graded == {CODEX: 1.0, "claude-code": 1.0}


def test_a_codex_row_reaching_the_record_keeps_its_agent_and_model(
    fake_codex: FakeCodex, tmp_path: Path,
) -> None:
    """A second harness adds a column to every cell: the record has to say
    which one ran."""
    fake_codex(SOLVE_ACT)
    tasks = [task_by_id(SEED)]
    log = tmp_path / "runs.jsonl"
    runs = run_live(tasks, [MODEL], log, sweep=SWEEP, agent=CODEX)

    [record] = firstparty_v1.evaluate(tasks, runs, source=str(log))

    assert (record.agent, record.model) == (CODEX, MODEL)
    assert record.agent_version == "codex-cli 9.9.9 (fake)"
    assert record.quality_value == 1.0
