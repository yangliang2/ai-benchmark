"""Agent adapters: the seam a second harness plugs into.

An **agent adapter** is the runner code that drives one agent headless and
turns its output into a run (CONTEXT.md). Its whole job is five things, and
this module is where that list is enforced rather than merely written down:

- invocation — driving the CLI headless in the workdir the runner prepared;
- event/payload parsing — into the row's `output`, `tokens_in`, `tokens_out`,
  `latency_s`, `turns`, `cost_usd`;
- version capture — what lands in `agent_version`;
- cost-source disclosure — the adapter names how its `cost_usd` was obtained
  (`cost_source`) and, for a table-derived figure, the `price_table` version;
- the permission-denial equivalent — the harness-ended run that raises and
  logs nothing;
- honouring the live run-time limit it is *given*.

That last one is a negative: the adapter never chooses a limit. The v1 live
runner reads the task's class limit from `firstparty_v1.LIVE_RUN_LIMITS_S` and
hands it over, because a limit an adapter (or a caller) could pick is a limit
adjusted for the one cell about to hit it, once its neighbours have already
run at another.

Everything around the run stays outside the adapter and belongs to the v1
runner: the fresh workdir seeded from the task's starting repository, the
pristine commit, the workdir-diff capture, the sweep id, the log append. An
adapter is handed a prepared workdir and gives back one row's measurements.

Adding an agent adds a column to every cell of the matrix and is an instrument
in its own right, so an unregistered name is refused rather than guessed at:
admitting an agent to a reading is a decision, the same stance the sweep id
and the model ladder already take. `claude-code` is the first instance;
`codex` is the second, and lands as its own registration here.
"""

from datetime import date
from pathlib import Path
from typing import Literal, Protocol

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import (
    CLAUDE_CODE,
    Run,
    claude_headless_json,
    claude_version,
    run_from_claude_json,
)


class AgentAdapter(Protocol):
    """What one harness has to provide to be swept."""

    @property
    def name(self) -> str:
        """The agent's registered name — what a row's `agent` field carries."""

    @property
    def cost_source(self) -> Literal["vendor-reported", "table-derived"]:
        """How this adapter's `cost_usd` was obtained (CONTEXT.md's "cost
        source") — stamped on every row it builds."""

    @property
    def price_table(self) -> str | None:
        """The price_table version `cost_usd` was computed from, for a
        table-derived adapter; None for one that reports its own figure."""

    def version(self) -> str:
        """The harness version this sweep is running, for `agent_version`."""

    def run(
        self,
        task_id: str,
        prompt: str,
        model: str,
        workdir: Path,
        *,
        agent_version: str | None,
        as_of: date,
        limit_s: int,
    ) -> Run:
        """One headless run in the prepared workdir, as a raw run-log row.

        Raises `IngestError` for anything that is not a measurement of the
        model: the CLI missing, a run that exceeded `limit_s`, a non-zero
        exit, unparseable output, and the harness-ended run (claude-code's
        permission denials) — a blocked run is a broken run, not a verdict.
        """


class ClaudeCodeAdapter:
    """claude-code headless, the first adapter.

    Thin by construction: the three functions it composes are the ones v0's
    live runner has always called, and they stay where they are so that
    runner keeps working. What this class adds is only the seam — a name to
    select it by, and the fixed shape the v1 runner drives it through.
    """

    name = CLAUDE_CODE
    # claude-code prints its own dollar figure (`total_cost_usd`); no price
    # table is ever consulted for it.
    cost_source: Literal["vendor-reported", "table-derived"] = "vendor-reported"
    price_table: str | None = None

    def version(self) -> str:
        return claude_version()

    def run(
        self,
        task_id: str,
        prompt: str,
        model: str,
        workdir: Path,
        *,
        agent_version: str | None,
        as_of: date,
        limit_s: int,
    ) -> Run:
        payload = claude_headless_json(
            task_id, prompt, model, workdir, tools=True, timeout_s=limit_s,
        )
        return run_from_claude_json(
            task_id, model, payload,
            agent_version=agent_version, as_of=as_of, agent=self.name,
        )


DEFAULT_AGENT = CLAUDE_CODE

# The registry: what a sweep may name. Keyed by each adapter's own name, so a
# registration cannot disagree with the value its rows carry.
ADAPTERS: dict[str, AgentAdapter] = {
    adapter.name: adapter for adapter in (ClaudeCodeAdapter(),)
}


def adapter_for(agent: str) -> AgentAdapter:
    """The registered adapter of that name, or a loud refusal.

    Refused before anything runs rather than falling back to the default: an
    agent is a column of the matrix, and a sweep that quietly ran a different
    one than it was told to is a reading nobody chose.
    """
    if agent not in ADAPTERS:
        registered = ", ".join(sorted(ADAPTERS))
        raise IngestError(
            f"unknown agent {agent!r} — no adapter is registered for it; "
            f"registered agents: {registered}"
        )
    return ADAPTERS[agent]
