"""Classify benchmark instances into taxonomy categories, cache-first.

The cache is committed to the repo (keyed by "benchmark/instance_id"), so a
warm run is deterministic and free — the LLM is only consulted on misses.
An "unclassified" verdict is cached too: never force-fit, never re-ask.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from ai_benchmark.instances import InstanceContext, Instances, scale_from_patch_files
from ai_benchmark.schema import Record, Scale, TaskCategory, validate_record


class Label(TypedDict):
    category: TaskCategory
    scale: Scale
    language: str | None


Cache = dict[str, Label]

Classifier = Callable[[str, str, InstanceContext | None], Label]


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
    records: list[Record],
    cache: Cache,
    llm: Classifier,
    instances: Instances | None = None,
) -> tuple[list[Record], Cache, int]:
    """Returns (classified records, updated cache, number of LLM calls made).

    Instance context, when available, is passed to the LLM on misses; its patch
    file list makes `scale` mechanical and always beats an LLM guess. Cached
    entries are preserved — only "unknown" scale is re-derived (#8).
    """
    updated_cache = dict(cache)
    llm_calls = 0

    classified = []
    for record in records:
        if not needs_classification(record) or record.instance_id is None:
            classified.append(record)
            continue
        key = cache_key(record)
        context = instances.get(key) if instances else None
        if key not in updated_cache:
            updated_cache[key] = llm(record.benchmark, record.instance_id, context)
            llm_calls += 1
        label = updated_cache[key]
        if label["scale"] == "unknown" and context is not None:
            mechanical = scale_from_patch_files(context["patch_files"])
            if mechanical != "unknown":
                label = updated_cache[key] = Label(
                    category=label["category"],
                    scale=mechanical,
                    language=label["language"],
                )
        classified.append(_apply(record, label))
    return classified, updated_cache, llm_calls
