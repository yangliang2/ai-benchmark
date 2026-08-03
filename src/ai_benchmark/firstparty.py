"""First-party eval loop: run the task set through combinations and land
ordinary unified-dataset records with exact cost dimensions (ticket #7).

The raw run log is the provenance boundary. A live run (claude-code headless)
writes one JSONL row per task x combination with the exact measurements the
provider API reported, then evaluation reads that log — and only ever such
logs — so replaying a checked-in log exercises the identical pipeline with no
live agents. Records carry source_type "first-party" and confidence "high"
(schema-enforced, ADR-0001); the record's source is the run log itself.
"""

import json
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ai_benchmark.dataset import IngestError
from ai_benchmark.schema import (
    LanguageStr,
    NonEmptyStr,
    Record,
    RecordValidationError,
    Scale,
    TaskCategory,
    validate_record,
)

BENCHMARK = "first-party-v0"

DEFAULT_MODELS = ["claude-sonnet-5", "claude-haiku-4-5"]


class Task(BaseModel):
    """One first-party benchmark instance: a self-contained prompt whose final
    output is graded by the check regex (re.search) as resolved or not."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    category: TaskCategory
    scale: Scale
    language: LanguageStr | None = None
    prompt: NonEmptyStr
    check: NonEmptyStr

    @model_validator(mode="after")
    def classified_and_checkable(self) -> Self:
        if self.category == "unclassified":
            raise ValueError(
                "first-party tasks are classified up front — they exist to fill "
                "known capability-matrix cells"
            )
        try:
            re.compile(self.check)
        except re.error as error:
            raise ValueError(f"check is not a valid regex: {error}") from error
        return self


class Run(BaseModel):
    """One raw run-log row: exact measurements for one task x combination."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: NonEmptyStr
    agent: NonEmptyStr
    agent_version: str | None = None
    model: NonEmptyStr
    output: str
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
    latency_s: float = Field(ge=0)
    turns: int = Field(ge=1)
    as_of: date


def load_tasks(path: Path) -> list[Task]:
    try:
        tasks = [Task.model_validate(entry) for entry in yaml.safe_load(path.read_text())]
    except (ValidationError, TypeError) as error:
        raise IngestError(f"{path}: {error}") from error
    duplicates = [
        task_id for task_id, count in Counter(t.id for t in tasks).items() if count > 1
    ]
    if duplicates:
        raise IngestError(f"{path}: duplicate task id(s): {sorted(duplicates)}")
    return tasks


def load_runs(path: Path) -> list[Run]:
    try:
        return [
            Run.model_validate(json.loads(line))
            for line in path.read_text().splitlines()
            if line.strip()
        ]
    except (json.JSONDecodeError, ValidationError) as error:
        raise IngestError(f"{path}: {error}") from error


def evaluate(tasks: list[Task], runs: list[Run], source: str) -> list[Record]:
    """Grade each run's output against its task's check and emit first-party
    records. Runs for unknown tasks and duplicate runs fail loudly — either
    would otherwise vanish or overwrite silently at merge time."""
    by_id = {task.id: task for task in tasks}
    unknown = sorted({run.task_id for run in runs} - by_id.keys())
    if unknown:
        raise IngestError(f"run log references unknown task(s): {unknown}")
    duplicates = [
        key
        for key, count in Counter((r.task_id, r.agent, r.model) for r in runs).items()
        if count > 1
    ]
    if duplicates:
        raise IngestError(
            f"duplicate runs would silently overwrite each other: {sorted(duplicates)}"
        )

    records = []
    for run in runs:
        task = by_id[run.task_id]
        try:
            records.append(
                validate_record(
                    {
                        "category": task.category,
                        "scale": task.scale,
                        "language": task.language,
                        "agent": run.agent,
                        "agent_version": run.agent_version,
                        "model": run.model,
                        "benchmark": BENCHMARK,
                        "instance_id": task.id,
                        "quality_metric": "resolved",
                        "quality_value": (
                            1.0 if re.search(task.check, run.output) else 0.0
                        ),
                        "tokens_in": run.tokens_in,
                        "tokens_out": run.tokens_out,
                        "cost_usd": run.cost_usd,
                        "latency_s": run.latency_s,
                        "turns": run.turns,
                        "source": source,
                        "source_type": "first-party",
                        "confidence": "high",
                        "as_of": run.as_of,
                    }
                )
            )
        except RecordValidationError as error:
            raise IngestError(
                f"{run.task_id} ({run.agent} x {run.model}): {error}"
            ) from error
    return records


# --- live runner: claude-code headless ---------------------------------------


def run_from_claude_json(
    task_id: str,
    model: str,
    payload: dict[str, Any],
    *,
    agent_version: str | None,
    as_of: date,
) -> Run:
    """Turn one `claude -p --output-format json` payload into a raw run row.

    tokens_in counts every input token the provider processed: fresh input
    plus cache creation plus cache reads — the cost-bearing total.
    """
    if payload.get("is_error"):
        raise IngestError(
            f"{task_id} ({model}): claude reported an error: {payload.get('result')!r}"
        )
    try:
        usage = payload["usage"]
        return Run(
            task_id=task_id,
            agent="claude-code",
            agent_version=agent_version,
            model=model,
            output=payload["result"],
            tokens_in=usage["input_tokens"]
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0),
            tokens_out=usage["output_tokens"],
            cost_usd=payload["total_cost_usd"],
            latency_s=payload["duration_ms"] / 1000,
            turns=payload["num_turns"],
            as_of=as_of,
        )
    except (KeyError, TypeError, ValidationError) as error:
        raise IngestError(
            f"{task_id} ({model}): unexpected claude output: {error!r}"
        ) from error


def run_live(tasks: list[Task], models: list[str], log_path: Path) -> list[Run]:
    """Run every task through claude-code headless for each model, writing the
    raw run log before returning — the log, not this process, is the source of
    record, so every live run is replayable afterwards."""
    version = _claude_version()
    today = date.today()
    runs = []
    for model in models:
        for task in tasks:
            process = subprocess.run(
                ["claude", "-p", task.prompt, "--model", model,
                 "--output-format", "json"],
                capture_output=True,
                text=True,
            )
            if process.returncode != 0:
                raise IngestError(
                    f"{task.id} ({model}): claude exited {process.returncode}: "
                    f"{process.stderr.strip()}"
                )
            try:
                payload = json.loads(process.stdout)
            except json.JSONDecodeError as error:
                raise IngestError(
                    f"{task.id} ({model}): claude output is not JSON: {error}"
                ) from error
            runs.append(
                run_from_claude_json(
                    task.id, model, payload, agent_version=version, as_of=today
                )
            )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(run.model_dump(mode="json"), sort_keys=True) for run in runs]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return runs


def _claude_version() -> str | None:
    process = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    if process.returncode != 0:
        return None
    return process.stdout.strip() or None
