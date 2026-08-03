"""The ai-bench command: ingest sources into the unified dataset and query it."""

import argparse
import os
from pathlib import Path

from ai_benchmark.classify import (
    Label,
    cache_key,
    classify_records,
    load_cache,
    needs_classification,
    write_cache,
)
from ai_benchmark.aider import ingest_aider
from ai_benchmark.dataset import merge_records, read_records, write_records
from ai_benchmark.queries import (
    aggregate_rows,
    category_rates,
    render_aggregate_table,
    render_category_table,
    render_table,
    resolution_rates,
)
from ai_benchmark.schema import Record
from ai_benchmark.swebench import ingest_swebench

DEFAULT_DATA = Path("data/unified.jsonl")
DEFAULT_CACHE = Path("data/classification-cache.json")


def _merge_into(new: list[Record], data: Path) -> None:
    existing = read_records(data) if data.exists() else []
    data.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_records(existing, new)
    write_records(merged, data)
    print(f"merged {len(new)} records into {data} ({len(merged)} total)")


def _ingest_swebench_command(args: argparse.Namespace) -> None:
    _merge_into(ingest_swebench(args.raw_dir), args.data)


def _ingest_aider_command(args: argparse.Namespace) -> None:
    _merge_into(ingest_aider(args.raw_dir), args.data)


def _table_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    if args.by_category:
        print(render_category_table(category_rates(records)))
    else:
        print(render_table(resolution_rates(records)))
    if aggregates := aggregate_rows(records):
        print()
        print(f"aggregate records ({len(aggregates)}), as published — not pooled above:")
        print(render_aggregate_table(aggregates))


def _never_llm(benchmark: str, instance_id: str) -> Label:
    raise AssertionError("warm cache must not reach the LLM")


def _classify_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    cache = load_cache(args.cache) if args.cache.exists() else {}

    misses = {cache_key(r) for r in records if needs_classification(r)} - cache.keys()
    if misses and "ANTHROPIC_API_KEY" not in os.environ:
        raise SystemExit(
            f"{len(misses)} instance(s) need LLM classification but "
            "ANTHROPIC_API_KEY is not set; set it (or pre-fill the cache) and re-run"
        )

    if misses:
        from ai_benchmark.llm import anthropic_classifier

        llm = anthropic_classifier()
    else:
        llm = _never_llm

    classified, cache_after, llm_calls = classify_records(records, cache, llm)
    write_records(classified, args.data)
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    write_cache(cache_after, args.cache)
    unclassified = sum(needs_classification(r) for r in classified)
    print(
        f"classified {len(classified)} records with {llm_calls} LLM call(s); "
        f"{unclassified} instance record(s) remain unclassified"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ai-bench")
    subcommands = parser.add_subparsers(required=True)

    ingest = subcommands.add_parser(
        "ingest-swebench",
        help="merge a directory of SWE-bench per-instance submissions into the dataset",
    )
    ingest.add_argument("raw_dir", type=Path)
    ingest.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ingest.set_defaults(command=_ingest_swebench_command)

    ingest_aider_parser = subcommands.add_parser(
        "ingest-aider",
        help="merge Aider polyglot leaderboard data into the dataset",
    )
    ingest_aider_parser.add_argument("raw_dir", type=Path)
    ingest_aider_parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ingest_aider_parser.set_defaults(command=_ingest_aider_command)

    table = subcommands.add_parser(
        "table", help="print per-instance resolution rates per benchmark x combination"
    )
    table.add_argument("--data", type=Path, default=DEFAULT_DATA)
    table.add_argument(
        "--by-category", action="store_true", help="group rates by task category"
    )
    table.set_defaults(command=_table_command)

    classify = subcommands.add_parser(
        "classify", help="classify unclassified instances via the committed cache + LLM"
    )
    classify.add_argument("--data", type=Path, default=DEFAULT_DATA)
    classify.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    classify.set_defaults(command=_classify_command)

    args = parser.parse_args(argv)
    args.command(args)
