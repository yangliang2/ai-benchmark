"""The pin suite for `tests/sweep_census.py`: the one place its literals meet
`data/first-party-v1-runs/` and the checked-in task set.

Every figure in the census module is re-derived here from the live raw run
logs and the live task set, through the same readers the consumers of the
census depend on (`ai_benchmark.reconcile_v1.collect_logs`, `select_agent`,
`select_language`, `DEFAULT_LANGUAGE`, and `ai_benchmark.firstparty_v1.
load_runs` / `load_task_set`). A stray row that lands under a sweep id the
census has not registered fails loudly here, naming this file and the id, so
the census cannot drift silently from the directory it counts.

No paid call, no network, no sweep is landed here, and no design-note line or
existing test file is touched.
"""

from collections import Counter
from pathlib import Path

import pytest

from ai_benchmark.agents import DEFAULT_AGENT
from ai_benchmark.cli import main
from ai_benchmark.firstparty_v1 import Run, Task, load_runs, load_task_set
from ai_benchmark.reconcile_v1 import (
    DEFAULT_LANGUAGE,
    collect_logs,
    select_agent,
    select_language,
)
from sweep_census import (
    ALL_SWEEPS,
    AS_OF_KEYS,
    CENSUS,
    LOG_COUNT,
    RECONCILED_ROWS,
    RECONCILED_TASKS,
    ROW_COUNT,
    UNSWEPT_ROWS,
    claude_code_rows_of,
    reconcile_keys_line,
    reconcile_rounds_line,
    reconcile_runs_line,
    reconciled_rows_of,
    reconciled_tasks_added_by,
    rows_of,
    sweeps_after,
    tasks_added_by,
)

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"


@pytest.fixture(scope="module")
def logs() -> list[Path]:
    return collect_logs([_LOGS])


@pytest.fixture(scope="module")
def runs(logs: list[Path]) -> list[Run]:
    return [run for log in logs for run in load_runs(log)]


@pytest.fixture(scope="module")
def tasks() -> list[Task]:
    return load_task_set(_TASKS)


def test_every_live_sweep_id_is_registered(runs: list[Run]) -> None:
    carried = {run.sweep for run in runs if run.sweep is not None}
    unregistered = carried - set(ALL_SWEEPS)
    assert not unregistered, (
        f"tests/sweep_census.py does not register sweep id(s) {sorted(unregistered)} "
        "that data/first-party-v1-runs/ carries — a new sweep is one visible "
        "edit to that module (append to ALL_SWEEPS, bump the totals, add the "
        "CENSUS row)"
    )
    assert carried == set(ALL_SWEEPS), (
        "tests/sweep_census.py registers sweep id(s) no live row carries: "
        f"{sorted(set(ALL_SWEEPS) - carried)}"
    )


def test_all_sweeps_is_ordered_by_round_number_with_no_duplicates() -> None:
    numbers = [int(sweep_id.split("-")[1]) for sweep_id in ALL_SWEEPS]
    assert numbers == sorted(numbers), "ALL_SWEEPS is ordered by round number"
    assert len(set(ALL_SWEEPS)) == len(ALL_SWEEPS), "ALL_SWEEPS holds no duplicates"
    assert set(ALL_SWEEPS) == set(CENSUS), "every registered sweep has a CENSUS row"


def test_log_and_row_counts_match_the_live_directory(
    logs: list[Path], runs: list[Run]
) -> None:
    assert LOG_COUNT == len(logs)
    assert ROW_COUNT == len(runs)


def test_unswept_rows_and_as_of_keys_match_the_live_rows(runs: list[Run]) -> None:
    unswept = [run for run in runs if run.sweep is None]
    assert UNSWEPT_ROWS == len(unswept)
    assert set(AS_OF_KEYS) == {f"as-of {run.as_of.isoformat()}" for run in unswept}
    assert len(AS_OF_KEYS) == len(set(AS_OF_KEYS)), "AS_OF_KEYS holds no duplicates"


def test_reconciled_totals_match_the_default_selection(
    tasks: list[Task], runs: list[Run]
) -> None:
    selected = select_agent(runs, DEFAULT_AGENT, explicit=False)
    selected = select_language(tasks, selected, DEFAULT_LANGUAGE, explicit=False)
    assert RECONCILED_ROWS == len(selected)
    assert RECONCILED_TASKS == len({run.task_id for run in selected})


def test_every_census_field_is_re_derived_per_sweep(
    tasks: list[Task], runs: list[Run]
) -> None:
    by_sweep: dict[str, list[Run]] = {sweep_id: [] for sweep_id in ALL_SWEEPS}
    for run in runs:
        if run.sweep is not None:
            by_sweep[run.sweep].append(run)

    # tasks_added counts each sweep's first mention of a task id, counting the
    # unswept as-of rows as prior — which is why round-6 adds 0 and not 12.
    seen_all = {run.task_id for run in runs if run.sweep is None}
    seen_reconciled = {
        run.task_id
        for run in select_language(
            tasks,
            select_agent([run for run in runs if run.sweep is None],
                         DEFAULT_AGENT, explicit=False),
            DEFAULT_LANGUAGE, explicit=False,
        )
    }

    for sweep_id in ALL_SWEEPS:
        rows = by_sweep[sweep_id]
        registered = CENSUS[sweep_id]
        assert registered.id == sweep_id

        task_ids = {run.task_id for run in rows}
        added = task_ids - seen_all
        seen_all |= task_ids

        cc_rows = select_agent(rows, DEFAULT_AGENT, explicit=False)
        rec_rows = select_language(tasks, cc_rows, DEFAULT_LANGUAGE, explicit=False)
        rec_task_ids = {run.task_id for run in rec_rows}
        rec_added = rec_task_ids - seen_reconciled
        seen_reconciled |= rec_task_ids

        assert registered.rows == len(rows), sweep_id
        assert registered.claude_code_rows == len(cc_rows), sweep_id
        assert registered.reconciled_rows == len(rec_rows), sweep_id
        assert registered.tasks_added == len(added), sweep_id
        assert registered.reconciled_tasks_added == len(rec_added), sweep_id


def test_the_derivations_sum_the_census(runs: list[Run]) -> None:
    by_sweep: Counter[str] = Counter(
        run.sweep for run in runs if run.sweep is not None
    )
    assert rows_of(*ALL_SWEEPS) == sum(by_sweep.values())
    assert claude_code_rows_of(*ALL_SWEEPS) == sum(
        1 for run in runs
        if run.sweep in ALL_SWEEPS and run.agent == DEFAULT_AGENT
    )
    assert reconciled_rows_of(*ALL_SWEEPS) == sum(
        CENSUS[sweep_id].reconciled_rows for sweep_id in ALL_SWEEPS
    )
    assert tasks_added_by(*ALL_SWEEPS) == sum(
        CENSUS[sweep_id].tasks_added for sweep_id in ALL_SWEEPS
    )
    assert reconciled_tasks_added_by(*ALL_SWEEPS) == sum(
        CENSUS[sweep_id].reconciled_tasks_added for sweep_id in ALL_SWEEPS
    )
    # And a single sweep's derivation is just its own CENSUS row.
    for sweep_id in ALL_SWEEPS:
        registered = CENSUS[sweep_id]
        assert rows_of(sweep_id) == registered.rows
        assert claude_code_rows_of(sweep_id) == registered.claude_code_rows
        assert reconciled_rows_of(sweep_id) == registered.reconciled_rows
        assert tasks_added_by(sweep_id) == registered.tasks_added
        assert reconciled_tasks_added_by(sweep_id) == registered.reconciled_tasks_added


def test_sweeps_after_reads_the_registered_order() -> None:
    for index, sweep_id in enumerate(ALL_SWEEPS):
        assert sweeps_after(sweep_id) == ALL_SWEEPS[index + 1:]

    # round-9 landed no rows and is not registered, but it is a well-formed
    # round-N label and the order says what comes after it.
    assert sweeps_after("round-9") == tuple(
        sweep_id for sweep_id in ALL_SWEEPS
        if int(sweep_id.split("-")[1]) > 9
    )
    assert sweeps_after("round-9") == (
        "round-10", "round-11", "round-12", "round-13",
    )

    with pytest.raises(ValueError):
        sweeps_after("not-a-round")


def test_the_reconcile_lines_appear_in_live_cli_output(capsys: pytest.CaptureFixture[str]) -> None:
    main(["reconcile-v1", "--tasks", str(_TASKS), "--replay", str(_LOGS)])
    printed = capsys.readouterr().out
    assert reconcile_rounds_line() in printed
    assert reconcile_keys_line() in printed
    assert reconcile_runs_line() in printed
