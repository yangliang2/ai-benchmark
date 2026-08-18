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
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty import (
    CLAUDE_CODE,
    Run,
    claude_headless_json,
    claude_version,
    run_from_claude_json,
)
from ai_benchmark.pricing import (
    DEFAULT_PRICE_TABLE_PATH,
    PriceTable,
    cost_usd,
    load_price_table,
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

    def check_models(self, models: list[str]) -> None:
        """Refuse, before anything runs, any model this harness is not
        registered to drive.

        Part of invocation, not a sixth responsibility: which combination may
        be invoked at all is decided here rather than discovered from what a
        CLI's configuration defaulted to. The v1 live runner calls it right
        after it resolves the adapter and before it prepares the first
        workdir, so a sweep named with a model the harness does not run stops
        having prepared nothing and paid nothing.
        """

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

    def check_models(self, models: list[str]) -> None:
        """claude-code registers no model set of its own: which models it may
        be read on is policed from the other end, by
        `reconcile_v1.LADDER_MODELS`, and has been since before this seam
        existed. Nothing to refuse here."""

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


# --- codex: the second harness -----------------------------------------------

# The name a codex row's `agent` field carries, and the name that selects this
# adapter. Written once here; `firstparty_v1._cost_source_problem` knows the
# same string from the other end, where it refuses a codex row that does not
# disclose a table-derived cost.
CODEX = "codex"

# The registered Codex combinations: model → reasoning level. One entry, and
# the level rides with the model rather than being passed on the command line,
# because a reasoning level is as much a property of what was measured as the
# model name is. Admitting a combination to a reading is a decision — the same
# stance the model ladder and the sweep id already take — so a `--model` naming
# anything not in this table is refused before anything runs, rather than
# quietly running at whatever effort the CLI's own configuration defaults to.
# There is deliberately no flag for the level: adding one would make the level
# an accident of an invocation, and `--model` stays the only model-facing flag
# `eval-v1` has.
CODEX_REASONING_LEVELS: dict[str, str] = {"gpt-5.6-terra": "medium"}

# What `codex exec` calls the reasoning level, as a config override: the CLI
# publishes no flag for it (`codex exec --help`, codex-cli 0.147.0), so it
# rides on `-c`, which is not a user-configuration read but an explicit
# setting of it.
_REASONING_LEVEL_KEY = "model_reasoning_effort"

# Item kinds that are not turns. A reasoning item is the model thinking, not
# an action it took, and counting it would make `turns` mean something
# different on a codex row than on a claude-code one.
_NOT_A_TURN = frozenset({"reasoning"})


def codex_reasoning_level(model: str) -> str:
    """The registered reasoning level for this Codex model, or a refusal."""
    level = CODEX_REASONING_LEVELS.get(model)
    if level is None:
        registered = (
            ", ".join(
                f"{name} @ {value}"
                for name, value in sorted(CODEX_REASONING_LEVELS.items())
            )
            or "(none)"
        )
        raise IngestError(
            f"codex runs no model {model!r} — no Codex combination is "
            f"registered for it; registered combinations: {registered}"
        )
    return level


def codex_argv(prompt: str, model: str) -> list[str]:
    """The exact command one Codex run is made with.

    Every flag is there for a stated reason, and each is the spelling the
    installed CLI publishes (`codex exec --help`, codex-cli 0.147.0):

    - `exec` — non-interactive; there is no terminal to drive one from;
    - `--json` — events as JSONL on stdout, which is what is parsed;
    - `-m` and `-c model_reasoning_effort=…` — the registered combination,
      both passed explicitly so the run is the one that was registered;
    - `--ignore-user-config` — the operator's `config.toml` is not read, the
      analogue of claude-code's `--setting-sources ""`; authentication is
      unaffected, so the run still runs;
    - `--ephemeral` — no session files left on the operator's machine, so a
      sweep leaves nothing behind and no earlier session can leak into one;
    - `--dangerously-bypass-approvals-and-sandbox` — the same blanket grant
      claude-code runs under (`--permission-mode bypassPermissions`). The two
      harnesses have to be measured under one permission stance or the
      harness contrast measures the stance instead; the not-a-sandbox stance
      is already documented (CONTEXT.md, **execution-verified**) and ticketed
      as #15, and a second harness widens its scope rather than its nature.

    The prompt goes last, positionally, exactly as the captured anchor's
    invocation had it.
    """
    return [
        "codex", "exec",
        "--json",
        "-m", model,
        "-c", f"{_REASONING_LEVEL_KEY}={codex_reasoning_level(model)}",
        "--ignore-user-config",
        "--ephemeral",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    ]


def codex_exec_events(
    task_id: str,
    prompt: str,
    model: str,
    workdir: Path,
    *,
    timeout_s: int,
) -> tuple[list[dict[str, Any]], float]:
    """One headless `codex exec --json` run in workdir: its parsed event
    stream, and the adapter's own wall clock over the child process.

    The clock is measured here because the stream carries no duration of its
    own — a Codex row's `latency_s` is what the adapter watched, not what the
    harness reported.

    The child's stdin is closed (`DEVNULL`): `codex exec` reads instructions
    from stdin when it is given none as an argument, so an inherited terminal
    is a run that hangs forever inside the sweep's timeout instead of
    finishing.

    An absent CLI, a run that outlived `timeout_s`, a non-zero exit and output
    that is not JSONL each raise rather than logging a corrupt row.
    """
    command = codex_argv(prompt, model)
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=timeout_s,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except OSError as error:
        raise IngestError(
            f"cannot run the codex CLI (is it installed and on PATH?): {error}"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise IngestError(
            f"{task_id} ({model}): codex timed out after {timeout_s}s"
        ) from error
    latency_s = time.monotonic() - started
    if process.returncode != 0:
        raise IngestError(
            f"{task_id} ({model}): codex exited {process.returncode}: "
            f"{process.stderr.strip()}"
        )
    events = []
    for number, line in enumerate(process.stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise IngestError(
                f"{task_id} ({model}): codex output is not JSONL "
                f"(line {number}): {error}"
            ) from error
        if not isinstance(event, dict):
            raise IngestError(
                f"{task_id} ({model}): codex output is not JSONL (line "
                f"{number}): expected an event object, got {type(event).__name__}"
            )
        events.append(event)
    return events, latency_s


def _harness_ended_the_run(task_id: str, model: str, event: dict[str, Any]) -> None:
    """Raise if this event says the harness, not the model, ended the run.

    The exact counterpart of claude-code's `permission_denials` rule: a
    blocked run is a broken run, not a verdict, so it raises loudly and no row
    is logged. Three shapes say it — an approval request nothing can answer
    (there is no approver behind a headless sweep, so the run is waiting on a
    person who is not there), a failed turn, and an error event or item.
    """
    kind = event.get("type")
    item = event.get("item")
    item_kind = item.get("type") if isinstance(item, dict) else None
    if item_kind == "approval_request":
        raise IngestError(
            f"{task_id} ({model}): codex asked for an approval nothing can "
            "answer in a headless run — a blocked run is a broken run, not a "
            "verdict"
        )
    if kind == "turn.failed":
        error = event.get("error")
        message = error.get("message") if isinstance(error, dict) else error
        raise IngestError(
            f"{task_id} ({model}): codex reported a failed turn: {message!r} "
            "— the harness ended this run, so it is not a verdict"
        )
    if kind == "error" or item_kind == "error":
        source = item if item_kind == "error" else event
        message = source.get("message") if isinstance(source, dict) else None
        raise IngestError(
            f"{task_id} ({model}): codex reported an error: {message!r} — the "
            "harness ended this run, so it is not a verdict"
        )


def run_from_codex_events(
    task_id: str,
    model: str,
    events: list[dict[str, Any]],
    *,
    agent_version: str | None,
    as_of: date,
    latency_s: float,
    table: PriceTable,
    agent: str = CODEX,
) -> Run:
    """Turn one `codex exec --json` event stream into a raw run row.

    From the anchor's shape (`tests/fixtures/codex/exec-events.jsonl`,
    codex-cli 0.147.0): a thread-started event, a turn-started event, one
    item-completed event per item, and a turn-completed event carrying usage.

    - `output` is the last agent message's text — metadata on a v1 row, where
      the diff is the graded artifact;
    - `tokens_in` is the input *total*, so cached and cache-write tokens are
      counted **once**: they are priced-differently subsets of that total, not
      addends, and the field has to mean on a codex row what it means on a
      claude-code one — every cost-bearing input token, once;
    - `tokens_out` is the output total, reasoning tokens likewise counted once
      inside it;
    - `turns` counts the completed items that are not reasoning items;
    - usage summed across every turn-completed event, so a run that took more
      than one turn is priced on all of it.

    `cost_usd` is the price table applied to that usage at write time — Codex
    reports no dollar figure of its own — with the split the table prices
    derived here and never put on the row: plain input is the input total less
    the cached and cache-write subsets, each of the three priced at its own
    rate, and the output total priced once with its reasoning tokens inside it.
    """
    usage: dict[str, int] = {}
    completed = []
    finished = False
    for event in events:
        _harness_ended_the_run(task_id, model, event)
        if event.get("type") == "turn.completed":
            finished = True
            for key, value in (event.get("usage") or {}).items():
                if not isinstance(value, int):
                    raise IngestError(
                        f"{task_id} ({model}): unexpected codex usage — "
                        f"{key}={value!r} is not a token count"
                    )
                usage[key] = usage.get(key, 0) + value
        elif event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict):
                completed.append(item)
    if not finished:
        raise IngestError(
            f"{task_id} ({model}): the codex event stream ended with no "
            "turn-completed event — the run did not finish, so its measurements "
            "are not a verdict"
        )
    messages = [
        item.get("text", "") for item in completed if item.get("type") == "agent_message"
    ]
    try:
        input_tokens = usage["input_tokens"]
        cached = usage.get("cached_input_tokens", 0)
        cache_write = usage.get("cache_write_input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        return Run(
            task_id=task_id,
            agent=agent,
            agent_version=agent_version,
            model=model,
            output=messages[-1] if messages else "",
            tokens_in=input_tokens,
            tokens_out=output_tokens,
            cost_usd=cost_usd(
                table,
                model,
                input_plain_tokens=input_tokens - cached - cache_write,
                input_cached_tokens=cached,
                input_cache_write_tokens=cache_write,
                output_tokens=output_tokens,
            ),
            latency_s=latency_s,
            turns=sum(1 for item in completed if item.get("type") not in _NOT_A_TURN),
            as_of=as_of,
        )
    except (KeyError, TypeError, ValidationError) as error:
        raise IngestError(
            f"{task_id} ({model}): unexpected codex output: {error!r}"
        ) from error


def codex_version() -> str:
    try:
        process = subprocess.run(
            ["codex", "--version"], capture_output=True, text=True, timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise IngestError(
            f"cannot run the codex CLI (is it installed and on PATH?): {error}"
        ) from error
    if process.returncode != 0:
        raise IngestError(f"codex --version failed: {process.stderr.strip()}")
    return process.stdout.strip()


class CodexAdapter:
    """codex exec headless, the second adapter — round 6's one instrument.

    It authors no task and moves nothing on the claude-code path: what it adds
    is a column to every cell of the matrix. Its cost is the one thing shaped
    differently from claude-code's — Codex prints no dollar figure, so
    `cost_usd` is this project's checked-in price table applied to the usage
    breakdown at write time, and the row says so (`cost_source: table-derived`
    plus the table's version). Nothing recomputes it afterwards: replay reads
    what the row says.
    """

    name = CODEX
    cost_source: Literal["vendor-reported", "table-derived"] = "table-derived"

    def __init__(self, price_table_path: Path = DEFAULT_PRICE_TABLE_PATH) -> None:
        # Loaded on first use rather than at import: a table that fails to
        # load must stop the sweep that would have been priced by it, not
        # every command that happens to import this module.
        self._price_table_path = price_table_path
        self._table: PriceTable | None = None

    @property
    def table(self) -> PriceTable:
        if self._table is None:
            self._table = load_price_table(self._price_table_path)
        return self._table

    @property
    def price_table(self) -> str | None:
        return self.table.version

    def version(self) -> str:
        return codex_version()

    def check_models(self, models: list[str]) -> None:
        for model in models:
            codex_reasoning_level(model)
        # And the table those models will be priced by, loaded here so that a
        # table that fails to load — or that prices none of these models —
        # stops the sweep before it is paid for rather than after, when the
        # only thing left to do with a measured run is throw it away.
        for model in models:
            cost_usd(
                self.table, model,
                input_plain_tokens=0, input_cached_tokens=0,
                input_cache_write_tokens=0, output_tokens=0,
            )

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
        # Re-checked here as well as in check_models: this is the last point
        # before a paid invocation, and an adapter called directly must refuse
        # an unregistered combination just as the runner does.
        codex_reasoning_level(model)
        events, latency_s = codex_exec_events(
            task_id, prompt, model, workdir, timeout_s=limit_s,
        )
        return run_from_codex_events(
            task_id, model, events,
            agent_version=agent_version, as_of=as_of,
            latency_s=latency_s, table=self.table, agent=self.name,
        )


DEFAULT_AGENT = CLAUDE_CODE

# The registry: what a sweep may name. Keyed by each adapter's own name, so a
# registration cannot disagree with the value its rows carry.
_REGISTERED: tuple[AgentAdapter, ...] = (ClaudeCodeAdapter(), CodexAdapter())

ADAPTERS: dict[str, AgentAdapter] = {
    adapter.name: adapter for adapter in _REGISTERED
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
