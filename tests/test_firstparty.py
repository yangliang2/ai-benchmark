"""Dataset-seam tests: task set + raw run log in -> first-party records out.

Replay mode is the test surface (acceptance: no live agent runs needed);
the live path shares everything but the subprocess call, whose JSON payload
parsing is covered here against a captured real claude CLI result.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from ai_benchmark.dataset import IngestError, read_records
from ai_benchmark.firstparty import (
    BENCHMARK,
    evaluate,
    load_runs,
    load_tasks,
    run_from_claude_json,
)

TASKS = Path(__file__).parent.parent / "tasks" / "first-party-v0.yaml"


def test_task_set_is_classified_and_big_enough() -> None:
    tasks = load_tasks(TASKS)

    assert len(tasks) >= 5
    assert len({task.id for task in tasks}) == len(tasks)
    assert all(task.category != "unclassified" for task in tasks)
    # More than one taxonomy category is actually exercised.
    assert len({task.category for task in tasks}) >= 3


def test_replay_produces_first_party_records(firstparty_runs: Path) -> None:
    tasks = load_tasks(TASKS)
    runs = load_runs(firstparty_runs)

    records = evaluate(tasks, runs, source=str(firstparty_runs))

    assert len(records) == len(runs) == 2 * len(tasks)
    assert {r.source_type for r in records} == {"first-party"}
    assert {r.confidence for r in records} == {"high"}
    assert {r.benchmark for r in records} == {BENCHMARK}
    assert {r.model for r in records} == {"claude-sonnet-5", "claude-haiku-4-5"}
    # Exact cost dimensions are captured on every record, no gaps.
    for r in records:
        assert r.tokens_in and r.tokens_out
        assert r.cost_usd and r.cost_usd > 0
        assert r.latency_s and r.latency_s > 0
        assert r.turns == 1
        assert r.as_of == date(2026, 8, 2)


def test_replay_grades_outputs_against_task_checks(firstparty_runs: Path) -> None:
    tasks = load_tasks(TASKS)

    records = evaluate(tasks, load_runs(firstparty_runs), source="run-log")

    by_key = {(r.instance_id, r.model): r.quality_value for r in records}
    # haiku answered evens-comprehension with the original loop — not resolved.
    assert by_key[("evens-comprehension", "claude-haiku-4-5")] == 0.0
    assert by_key[("evens-comprehension", "claude-sonnet-5")] == 1.0
    assert sum(by_key.values()) == len(records) - 1


def test_task_metadata_lands_on_the_record(firstparty_runs: Path) -> None:
    tasks = load_tasks(TASKS)

    records = evaluate(tasks, load_runs(firstparty_runs), source="run-log")

    [record] = [
        r for r in records
        if r.instance_id == "pytest-ci-workflow" and r.model == "claude-sonnet-5"
    ]
    assert record.category == "infra-config"
    assert record.scale == "single-file"
    assert record.language == "yaml"
    assert record.agent == "claude-code"
    assert record.quality_metric == "resolved"


def test_run_for_unknown_task_fails_loudly(firstparty_runs: Path) -> None:
    tasks = load_tasks(TASKS)
    runs = load_runs(firstparty_runs)
    orphan = runs[0].model_copy(update={"task_id": "no-such-task"})

    with pytest.raises(IngestError, match="no-such-task"):
        evaluate(tasks, [*runs, orphan], source="run-log")


def test_duplicate_runs_fail_loudly(firstparty_runs: Path) -> None:
    tasks = load_tasks(TASKS)
    runs = load_runs(firstparty_runs)

    with pytest.raises(IngestError, match="duplicate"):
        evaluate(tasks, [*runs, runs[0]], source="run-log")


def test_run_from_claude_json_captures_exact_cost_dimensions() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "firstparty" / "claude-result.json")
        .read_text()
    )

    run = run_from_claude_json(
        "trace-return-value", "claude-haiku-4-5", payload,
        agent_version="2.1.220", as_of=date(2026, 8, 3),
    )

    assert run.output == "OK"
    # Exact tokens in = fresh input + cache creation + cache reads.
    assert run.tokens_in == 10 + 10909 + 17703
    assert run.tokens_out == 193
    assert run.cost_usd == 0.0245633
    assert run.latency_s == pytest.approx(6.314)
    assert run.turns == 1
    assert run.agent == "claude-code"


def test_run_from_claude_json_rejects_errored_runs() -> None:
    payload = {"is_error": True, "result": "overloaded"}

    with pytest.raises(IngestError, match="trace-return-value"):
        run_from_claude_json(
            "trace-return-value", "claude-haiku-4-5", payload,
            agent_version=None, as_of=date(2026, 8, 3),
        )
