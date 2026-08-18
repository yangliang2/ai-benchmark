"""Cost source and price-table version on the v1 raw run row (CONTEXT.md's
"cost source"): `cost_source` and `price_table` are optional, refuse an
internally-contradictory row, and the live runner stamps `vendor-reported`
on every claude-code row it writes.
"""

import json
from pathlib import Path

import pytest
from conftest import FakeClaude
from firstparty_v1_tasks import task_by_id

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import load_runs, run_live

FEATURE_SEED = "wordcount-top-words"
SWEEP = "sweep-under-test"


def log_row(**overrides: object) -> str:
    """One raw run-log line as JSON, with any field overridden.

    Written as JSON rather than by dumping a Run, because half of what these
    tests check is what the model refuses, and a value the model rejects
    cannot be built by constructing a Run first — nor by copying one, since
    `model_copy(update=...)` does not revalidate what it is handed.
    """
    row: dict[str, object] = {
        "task_id": FEATURE_SEED,
        "agent": "claude-code",
        "agent_version": "2.1.220",
        "model": "claude-sonnet-5",
        "output": "done",
        "diff": "",
        "tokens_in": 41000,
        "tokens_out": 1500,
        "cost_usd": 0.21,
        "latency_s": 64.5,
        "turns": 7,
        "as_of": "2026-08-04",
    }
    return json.dumps(row | overrides) + "\n"


def test_live_runs_stamp_vendor_reported_cost_source(
    fake_claude: FakeClaude, tmp_path: Path,
) -> None:
    """Every claude-code row the live runner writes says how its cost_usd was
    obtained, and names no price table — the CLI prints its own figure."""
    fake_claude("")
    wordcount = task_by_id(FEATURE_SEED)
    log = tmp_path / "runs.jsonl"

    [run] = run_live([wordcount], ["claude-sonnet-5"], log, sweep=SWEEP)

    assert run.cost_source == "vendor-reported"
    assert run.price_table is None
    [loaded] = load_runs(log)
    assert loaded.cost_source == "vendor-reported"
    assert loaded.price_table is None


def test_a_run_log_row_from_before_the_cost_source_fields_still_loads(
    firstparty_v1_fixture: Path,
) -> None:
    """Every checked-in log predates the fields and none may need rewriting to
    stay readable: such a row simply carries neither."""
    runs = load_runs(firstparty_v1_fixture)

    assert runs
    assert all(run.cost_source is None for run in runs)
    assert all(run.price_table is None for run in runs)


def test_a_row_from_before_the_fields_replays_exactly_as_before(
    firstparty_v1_fixture: Path, tmp_path: Path,
) -> None:
    """Absent fields stay absent through a load-and-write round trip: their
    introduction is not a migration, so no checked-in row changes shape."""
    before = firstparty_v1_fixture.read_text().splitlines()
    runs = load_runs(firstparty_v1_fixture)

    rewritten = tmp_path / "runs.jsonl"
    rewritten.write_text(
        "".join(run.model_dump_json(exclude_none=True) + "\n" for run in runs)
    )

    assert load_runs(rewritten) == runs
    for line, run in zip(before, runs, strict=True):
        assert json.loads(line) == json.loads(run.model_dump_json(exclude_none=True))


def test_cost_source_and_price_table_round_trip(tmp_path: Path) -> None:
    """A row carrying both fields reaches the model with both intact."""
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(cost_source="table-derived", price_table="2026-08-v1"))

    [loaded] = load_runs(log)

    assert loaded.cost_source == "table-derived"
    assert loaded.price_table == "2026-08-v1"


# --- the three shapes a row may not have --------------------------------------


def test_a_codex_row_not_saying_table_derived_is_refused(tmp_path: Path) -> None:
    """Codex reports no dollar figure of its own, so a codex row claiming a
    vendor-reported cost is claiming something the harness cannot have got."""
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(agent="codex", cost_source="vendor-reported"))

    with pytest.raises(IngestError, match="codex"):
        load_runs(log)


def test_a_codex_row_naming_no_price_table_is_refused(tmp_path: Path) -> None:
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(agent="codex", cost_source="table-derived"))

    with pytest.raises(IngestError, match="codex"):
        load_runs(log)


def test_a_codex_row_disclosing_nothing_at_all_is_refused(tmp_path: Path) -> None:
    """Absent fields are legal in general — but not on a codex row, whose
    cost_usd can only ever have come from a price table."""
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(agent="codex"))

    with pytest.raises(IngestError, match="codex"):
        load_runs(log)


def test_a_vendor_reported_row_naming_a_price_table_is_refused(
    tmp_path: Path,
) -> None:
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(cost_source="vendor-reported", price_table="2026-08-v1"))

    with pytest.raises(IngestError, match="vendor-reported"):
        load_runs(log)


def test_a_table_derived_row_naming_no_price_table_is_refused(
    tmp_path: Path,
) -> None:
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row(cost_source="table-derived"))

    with pytest.raises(IngestError, match="table-derived"):
        load_runs(log)


def test_a_refused_row_names_its_own_line(tmp_path: Path) -> None:
    """The refusal points at the offending row the way every other bad-row
    refusal does: a sweep that was paid for is not re-read by hand."""
    log = tmp_path / "runs.jsonl"
    log.write_text(log_row() + log_row(cost_source="table-derived"))

    with pytest.raises(IngestError, match="line 2"):
        load_runs(log)
