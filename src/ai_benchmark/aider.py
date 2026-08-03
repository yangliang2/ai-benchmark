"""Ingest the Aider polyglot leaderboard into unified-dataset records.

Raw layout mirrors the leaderboard's published data:
  polyglot_leaderboard.yml — one entry per run, with pass_rate_2 (%),
    total_cost (USD for the whole run), seconds_per_case, date, versions
  metadata.json — source URL

The leaderboard publishes aggregates only: records carry source_type
"aggregate" and confidence "low" (ADR-0001). cost_usd is the published
total run cost; latency_s is the published seconds per case.
"""

import json
from pathlib import Path

import yaml

from ai_benchmark.schema import Record, validate_record


def ingest_aider(raw_dir: Path) -> list[Record]:
    metadata = json.loads((raw_dir / "metadata.json").read_text())
    entries = yaml.safe_load((raw_dir / "polyglot_leaderboard.yml").read_text())

    return [
        validate_record(
            {
                "category": "unclassified",
                "scale": "unknown",
                "language": None,
                "agent": "aider",
                "agent_version": str(entry["versions"]) if "versions" in entry else None,
                "model": entry["model"],
                "benchmark": "aider-polyglot",
                "instance_id": None,
                "quality_metric": "pass-rate",
                "quality_value": entry["pass_rate_2"] / 100,
                "cost_usd": entry["total_cost"],
                "latency_s": entry["seconds_per_case"],
                "source": metadata["source"],
                "source_type": "aggregate",
                "confidence": "low",
                "as_of": entry["date"],
            }
        )
        for entry in entries
    ]
