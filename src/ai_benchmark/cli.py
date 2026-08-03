"""The ai-bench command: ingest sources into the unified dataset and query it."""

import argparse
from pathlib import Path

from ai_benchmark.dataset import merge_records, read_records, write_records
from ai_benchmark.queries import render_table, resolution_rates
from ai_benchmark.swebench import ingest_swebench

DEFAULT_DATA = Path("data/unified.jsonl")


def _ingest_swebench_command(args: argparse.Namespace) -> None:
    new = ingest_swebench(args.raw_dir)
    existing = read_records(args.data) if args.data.exists() else []
    args.data.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_records(existing, new)
    write_records(merged, args.data)
    print(f"merged {len(new)} records into {args.data} ({len(merged)} total)")


def _table_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    print(render_table(resolution_rates(records)))
    if aggregates := sum(r.source_type == "aggregate" for r in records):
        print(f"note: {aggregates} aggregate record(s) in the dataset are not shown")


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

    table = subcommands.add_parser(
        "table", help="print per-instance resolution rates per benchmark x combination"
    )
    table.add_argument("--data", type=Path, default=DEFAULT_DATA)
    table.set_defaults(command=_table_command)

    args = parser.parse_args(argv)
    args.command(args)
