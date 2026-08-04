"""Instance context: what a benchmark instance actually asked for.

A committed side-input to classification (#8), keyed like the classification
cache ("benchmark/instance_id"). The patch file list makes `scale` mechanical
— no LLM call — and the problem statement gives the classifier real evidence
instead of an id string. SWE-bench publishes both via its HuggingFace dataset;
fetching is a thin network shim over pure, offline-testable parsing.
"""

import json
import re
import urllib.parse
import urllib.request
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, TypedDict, cast

from ai_benchmark.schema import Scale

SWEBENCH_BENCHMARK = "swe-bench-verified"
SWEBENCH_DATASET = "princeton-nlp/SWE-bench_Verified"
DATASETS_SERVER = "https://datasets-server.huggingface.co/rows"
_ROWS_PER_PAGE = 100

# One header per changed file in `git diff` output; the b/ side is the
# post-image path, which is the file the task actually touched.
_DIFF_HEADER = re.compile(r"^diff --git a/.* b/(.*)$", re.MULTILINE)


class InstanceContext(TypedDict):
    problem_statement: str | None
    patch_files: list[str] | None


Instances = dict[str, InstanceContext]


def load_instances(path: Path) -> Instances:
    return cast(Instances, json.loads(path.read_text()))


def write_instances(instances: Instances, path: Path) -> None:
    path.write_text(json.dumps(instances, indent=2, sort_keys=True) + "\n")


def patch_files_from_diff(patch: str) -> list[str]:
    return list(dict.fromkeys(_DIFF_HEADER.findall(patch)))


def scale_from_patch_files(patch_files: list[str] | None) -> Scale:
    if not patch_files:
        return "unknown"
    return "single-file" if len(patch_files) == 1 else "cross-file"


def swebench_context_from_rows(rows: Iterable[Mapping[str, Any]]) -> Instances:
    return {
        f"{SWEBENCH_BENCHMARK}/{row['instance_id']}": InstanceContext(
            problem_statement=row["problem_statement"],
            patch_files=patch_files_from_diff(row["patch"]),
        )
        for row in rows
    }


def fetch_swebench_rows(dataset: str = SWEBENCH_DATASET) -> Iterator[dict[str, Any]]:
    """Page through the HuggingFace datasets-server rows API (network)."""
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "dataset": dataset,
                "config": "default",
                "split": "test",
                "offset": offset,
                "length": _ROWS_PER_PAGE,
            }
        )
        with urllib.request.urlopen(f"{DATASETS_SERVER}?{query}") as response:
            page = json.loads(response.read())
        for row in page["rows"]:
            if row["truncated_cells"]:
                # A truncated patch would parse to too few files and become a
                # wrong "mechanical" scale — refuse rather than mislabel.
                raise RuntimeError(
                    f"datasets-server truncated {row['truncated_cells']} for "
                    f"instance {row['row'].get('instance_id', '?')}; refusing to "
                    "derive context from incomplete rows"
                )
            yield cast(dict[str, Any], row["row"])
        offset += len(page["rows"])
        if offset >= page["num_rows_total"] or not page["rows"]:
            return
