"""Classify benchmark instances into taxonomy categories, cache-first.

The cache is committed to the repo (keyed by "benchmark/instance_id"), so a
warm run is deterministic and free — the LLM is only consulted on misses.
An "unclassified" verdict is cached too: never force-fit, never re-ask.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from ai_benchmark.schema import Record, Scale, TaskCategory, validate_record


class Label(TypedDict):
    category: TaskCategory
    scale: Scale
    language: str | None


Cache = dict[str, Label]

Classifier = Callable[[str, str], Label]


def load_cache(path: Path) -> Cache:
    return cast(Cache, json.loads(path.read_text()))


def write_cache(cache: Cache, path: Path) -> None:
    path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def cache_key(record: Record) -> str:
    return f"{record.benchmark}/{record.instance_id}"


def needs_classification(record: Record) -> bool:
    return record.category == "unclassified" and record.instance_id is not None


def _apply(record: Record, label: Label) -> Record:
    """Labels fill gaps but never overwrite source-derived facts. The result
    goes back through the validation seam — the committed cache is hand-editable
    and must not become an unvalidated input to the unified dataset."""
    return validate_record(
        record.model_dump(mode="json")
        | {
            "category": label["category"],
            "scale": record.scale if record.scale != "unknown" else label["scale"],
            "language": record.language or label["language"],
        }
    )


def classify_records(
    records: list[Record], cache: Cache, llm: Classifier
) -> tuple[list[Record], Cache, int]:
    """Returns (classified records, updated cache, number of LLM calls made)."""
    updated_cache = dict(cache)
    llm_calls = 0

    classified = []
    for record in records:
        if not needs_classification(record) or record.instance_id is None:
            classified.append(record)
            continue
        key = cache_key(record)
        if key not in updated_cache:
            updated_cache[key] = llm(record.benchmark, record.instance_id)
            llm_calls += 1
        label = updated_cache[key]
        if label["category"] == "unclassified":
            classified.append(record)
        else:
            classified.append(_apply(record, label))
    return classified, updated_cache, llm_calls
