"""The census of every first-party-v1 sweep, as literals the consumer suites
derive from rather than hand-copy.

**The discipline.** Landing a new sweep is one visible edit here, and it is
made in exactly one place: append the sweep id to `ALL_SWEEPS`, bump
`LOG_COUNT`, `ROW_COUNT`, `UNSWEPT_ROWS`/`AS_OF_KEYS` if the new logs carry
unswept rows, `RECONCILED_ROWS` and `RECONCILED_TASKS`, and add the sweep's
own row to `CENSUS`. Every consumer suite reads through the functions below —
`sweeps_after`, `rows_of`, `claude_code_rows_of`, `reconciled_rows_of`,
`tasks_added_by`, `reconciled_tasks_added_by`, the three `reconcile_*_line`
readers — and never repeats one of these numbers itself. `tests/
test_sweep_census.py` is the one place these literals meet
`data/first-party-v1-runs/` and the checked-in task set: if a sweep lands
here without a matching edit there, or the other way around, that suite is
where it fails loudly rather than a consumer silently drifting from the
directory.

This module is the terrain frozen at a point in time (`2407f02`), not a
computation over it — every figure below was re-derived against the working
tree rather than trusted from an earlier read, but nothing here re-derives
itself at import time. That is `tests/test_sweep_census.py`'s job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Sweep:
    id: str
    # Task ids this sweep is the first to mention, counting the unswept as-of
    # rows as prior — which is why round-6 adds 0 and not 12.
    tasks_added: int
    rows: int                    # rows this sweep landed
    claude_code_rows: int        # of those, rows whose agent is claude-code
    reconciled_rows: int         # rows surviving reconcile-v1's default
                                  # agent + language selection
    reconciled_tasks_added: int  # task ids first mentioned by a reconciled row


# Ordered by round number. There is no round-9 sweep — round 9 was a grader
# round and landed no rows.
ALL_SWEEPS: tuple[str, ...] = (
    "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
    "round-8", "round-10", "round-11", "round-12", "round-13",
)

LOG_COUNT = 53   # files in data/first-party-v1-runs/
ROW_COUNT = 342  # rows across them

# Rows carrying no sweep id, and the provenance keys they reconcile under.
UNSWEPT_ROWS = 98
AS_OF_KEYS: tuple[str, ...] = ("as-of 2026-08-04", "as-of 2026-08-05")

RECONCILED_ROWS = 255
RECONCILED_TASKS = 128

CENSUS: dict[str, Sweep] = {
    "round-2": Sweep("round-2", tasks_added=18, rows=36, claude_code_rows=36,
                      reconciled_rows=36, reconciled_tasks_added=18),
    "round-3": Sweep("round-3", tasks_added=22, rows=43, claude_code_rows=43,
                      reconciled_rows=43, reconciled_tasks_added=22),
    "round-4": Sweep("round-4", tasks_added=12, rows=24, claude_code_rows=24,
                      reconciled_rows=24, reconciled_tasks_added=12),
    "round-5": Sweep("round-5", tasks_added=12, rows=24, claude_code_rows=24,
                      reconciled_rows=24, reconciled_tasks_added=12),
    # Codex-only: no claude-code row, so nothing reconciles under the default
    # agent + language selection.
    "round-6": Sweep("round-6", tasks_added=0, rows=30, claude_code_rows=0,
                      reconciled_rows=0, reconciled_tasks_added=0),
    # claude-code's rows here are TypeScript, so the Python-default language
    # selection reconciles none of them either.
    "round-7": Sweep("round-7", tasks_added=14, rows=42, claude_code_rows=28,
                      reconciled_rows=0, reconciled_tasks_added=0),
    "round-8": Sweep("round-8", tasks_added=3, rows=9, claude_code_rows=6,
                      reconciled_rows=6, reconciled_tasks_added=3),
    "round-10": Sweep("round-10", tasks_added=3, rows=9, claude_code_rows=6,
                       reconciled_rows=6, reconciled_tasks_added=3),
    "round-11": Sweep("round-11", tasks_added=3, rows=9, claude_code_rows=6,
                       reconciled_rows=6, reconciled_tasks_added=3),
    "round-12": Sweep("round-12", tasks_added=3, rows=9, claude_code_rows=6,
                       reconciled_rows=6, reconciled_tasks_added=3),
    "round-13": Sweep("round-13", tasks_added=3, rows=9, claude_code_rows=6,
                       reconciled_rows=6, reconciled_tasks_added=3),
}

# The sweeps reconcile-v1's default agent + language selection actually
# surfaces a row for — round-6 and round-7 reconcile to zero, so neither
# appears in the printed round list.
_PRINTED_SWEEPS: tuple[str, ...] = tuple(
    sweep for sweep in ALL_SWEEPS if CENSUS[sweep].reconciled_rows > 0
)

_ROUND_ID = re.compile(r"round-(\d+)")


def _round_number(sweep_id: str) -> int:
    """The integer a `round-N` label orders on. Raises on anything that does
    not parse that way — a well-formed label whether or not it landed rows,
    per the owner's ruling that `sweeps_after` must accept `round-9`."""
    match = _ROUND_ID.fullmatch(sweep_id)
    if match is None:
        raise ValueError(
            f"{sweep_id!r} is not a well-formed round-N sweep id"
        )
    return int(match.group(1))


def sweeps_after(sweep_id: str) -> tuple[str, ...]:
    """Every registered sweep whose round number is greater than this one's.

    Accepts any well-formed `round-N` label, whether or not it landed rows —
    `round-9` parses and orders even though it is not in `ALL_SWEEPS`, because
    eight live scope-out sites read "every sweep after round 9".
    """
    threshold = _round_number(sweep_id)
    return tuple(sweep for sweep in ALL_SWEEPS if _round_number(sweep) > threshold)


def rows_of(*sweep_ids: str) -> int:
    return sum(CENSUS[sweep_id].rows for sweep_id in sweep_ids)


def claude_code_rows_of(*sweep_ids: str) -> int:
    return sum(CENSUS[sweep_id].claude_code_rows for sweep_id in sweep_ids)


def reconciled_rows_of(*sweep_ids: str) -> int:
    return sum(CENSUS[sweep_id].reconciled_rows for sweep_id in sweep_ids)


def tasks_added_by(*sweep_ids: str) -> int:
    return sum(CENSUS[sweep_id].tasks_added for sweep_id in sweep_ids)


def reconciled_tasks_added_by(*sweep_ids: str) -> int:
    return sum(CENSUS[sweep_id].reconciled_tasks_added for sweep_id in sweep_ids)


def reconcile_rounds_line() -> str:
    labels = (*AS_OF_KEYS, *(f"sweep {sweep_id}" for sweep_id in _PRINTED_SWEEPS))
    return f"  rounds     {len(labels)} round(s): {', '.join(labels)}"


def reconcile_keys_line() -> str:
    return (
        f"             {len(_PRINTED_SWEEPS)} keyed on a sweep id, "
        f"{len(AS_OF_KEYS)} on an as-of date"
    )


def reconcile_runs_line() -> str:
    return f"  runs       {RECONCILED_ROWS} over {RECONCILED_TASKS} task(s)"
