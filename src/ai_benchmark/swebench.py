"""Ingest SWE-bench Verified per-instance results into unified-dataset records.

Raw layout: one directory per submission, each holding
  metadata.json — agent, agent_version, model, source (URL), as_of
  results.json  — {"resolved": [instance ids], "unresolved": [instance ids]}
mirroring the per-instance dumps published in swe-bench/experiments.

Category is `unclassified` until the classification pipeline (#4) runs.
Language is `python` — every SWE-bench Verified task repo is Python.
"""

import json
from pathlib import Path

from ai_benchmark.dataset import IngestError
from ai_benchmark.schema import Record, RecordValidationError, validate_record

__all__ = ["IngestError", "ingest_swebench"]


def ingest_swebench(raw_dir: Path) -> list[Record]:
    records: list[Record] = []
    for submission in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        records.extend(_ingest_submission(submission))
    return records


def _ingest_submission(submission: Path) -> list[Record]:
    metadata = json.loads((submission / "metadata.json").read_text())
    results = json.loads((submission / "results.json").read_text())

    resolved = set(results["resolved"])
    unresolved = set(results["unresolved"])
    if overlap := resolved & unresolved:
        raise IngestError(
            f"{submission.name}: instances both resolved and unresolved: "
            f"{', '.join(sorted(overlap))}"
        )

    try:
        return [
            validate_record(
                {
                    "category": "unclassified",
                    "scale": "unknown",
                    "language": "python",
                    "agent": metadata["agent"],
                    "agent_version": metadata["agent_version"],
                    "model": metadata["model"],
                    "benchmark": "swe-bench-verified",
                    "instance_id": instance_id,
                    "quality_metric": "resolved",
                    "quality_value": 1.0 if instance_id in resolved else 0.0,
                    "source": metadata["source"],
                    "source_type": "per-instance",
                    "confidence": "medium",
                    "as_of": metadata["as_of"],
                }
            )
            for instance_id in sorted(resolved | unresolved)
        ]
    except RecordValidationError as error:
        raise IngestError(f"{submission.name}: {error}") from error
