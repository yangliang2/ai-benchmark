"""Read and write the unified dataset: one JSONL file of validated records.

Writes are deterministic (ordered by record identity, canonical JSON) so
re-ingesting the same input yields a byte-identical file. Ingesters merge
rather than truncate: records replace existing ones with the same identity,
everything else is preserved.
"""

import json
from pathlib import Path

from ai_benchmark.schema import Record, validate_record


class IngestError(ValueError):
    """Raw source data cannot become valid unified-dataset records."""


def write_records(records: list[Record], path: Path) -> None:
    lines = [
        json.dumps(record.model_dump(mode="json"), sort_keys=True)
        for record in sorted(records, key=lambda r: r.identity_key)
    ]
    path.write_text("\n".join(lines) + "\n")


def read_records(path: Path) -> list[Record]:
    return [
        validate_record(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def merge_records(existing: list[Record], new: list[Record]) -> list[Record]:
    by_identity = {record.identity_key: record for record in existing}
    by_identity.update((record.identity_key, record) for record in new)
    return sorted(by_identity.values(), key=lambda r: r.identity_key)
