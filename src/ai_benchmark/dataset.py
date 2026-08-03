"""Read and write the unified dataset: one JSONL file of validated records.

Writes are deterministic (sorted, canonical JSON) so re-ingesting the same
input yields a byte-identical file.
"""

import json
from pathlib import Path

from ai_benchmark.schema import Record, validate_record


def _sort_key(record: Record) -> tuple[str, str, str, str]:
    return (record.benchmark, record.instance_id or "", record.agent, record.model)


def write_records(records: list[Record], path: Path) -> None:
    lines = [
        json.dumps(record.model_dump(mode="json"), sort_keys=True)
        for record in sorted(records, key=_sort_key)
    ]
    path.write_text("\n".join(lines) + "\n")


def read_records(path: Path) -> list[Record]:
    return [
        validate_record(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]
