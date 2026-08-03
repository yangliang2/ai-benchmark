"""Ingest the Aider polyglot leaderboard into unified-dataset records.

Raw layout mirrors the leaderboard's published data:
  polyglot_leaderboard.yml — one entry per run, with pass_rate_2 (%),
    total_cost (USD for the whole run), test_cases, seconds_per_case,
    edit_format, date, versions
  metadata.json — source URL

The leaderboard publishes aggregates only: records carry source_type
"aggregate" and confidence "low" (ADR-0001). cost_usd is normalized to
USD per benchmark instance (total_cost / test_cases) so cost is
comparable across sources; latency_s is the published seconds per case.
The edit format is part of the agent identity ("aider (diff)") — the
leaderboard lists the same model under several edit formats, and they
are genuinely different harness configurations.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from ai_benchmark.dataset import IngestError
from ai_benchmark.schema import Record, RecordValidationError, validate_record


def ingest_aider(raw_dir: Path) -> list[Record]:
    metadata = json.loads((raw_dir / "metadata.json").read_text())
    entries = yaml.safe_load((raw_dir / "polyglot_leaderboard.yml").read_text())

    records = [_ingest_entry(entry, metadata["source"]) for entry in entries]

    collisions = [
        key for key, count in Counter(r.identity_key for r in records).items() if count > 1
    ]
    if collisions:
        raise IngestError(
            "leaderboard entries would silently overwrite each other "
            f"(same agent, model, and metric): {sorted(collisions)}"
        )
    return records


def _ingest_entry(entry: dict[str, Any], source: str) -> Record:
    name = entry.get("dirname") or entry.get("model") or "<entry>"
    try:
        edit_format = entry.get("edit_format")
        version = entry.get("versions")
        return validate_record(
            {
                "category": "unclassified",
                "scale": "unknown",
                "language": None,
                "agent": f"aider ({edit_format})" if edit_format else "aider",
                "agent_version": str(version) if isinstance(version, (str, int, float)) else None,
                "model": entry["model"],
                "benchmark": "aider-polyglot",
                "instance_id": None,
                "quality_metric": "pass-rate-2",
                "quality_value": entry["pass_rate_2"] / 100,
                "cost_usd": entry["total_cost"] / entry["test_cases"],
                "latency_s": entry["seconds_per_case"],
                "source": source,
                "source_type": "aggregate",
                "confidence": "low",
                "as_of": entry["date"],
            }
        )
    except (KeyError, TypeError, ZeroDivisionError, RecordValidationError) as error:
        raise IngestError(f"{name}: {error!r}") from error
