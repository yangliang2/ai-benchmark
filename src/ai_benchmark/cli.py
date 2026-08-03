"""The ai-bench command: ingest sources into the unified dataset and query it."""

import argparse
from pathlib import Path

from ai_benchmark.dataset import read_records, write_records
from ai_benchmark.queries import render_table, resolution_rates
from ai_benchmark.swebench import ingest_swebench

DEFAULT_DATA = Path("data/unified.jsonl")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ai-bench")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser(
        "ingest-swebench",
        help="ingest a directory of SWE-bench per-instance submissions",
    )
    ingest.add_argument("raw_dir", type=Path)
    ingest.add_argument("--data", type=Path, default=DEFAULT_DATA)

    table = subcommands.add_parser(
        "table", help="print resolution rates per agent x model combination"
    )
    table.add_argument("--data", type=Path, default=DEFAULT_DATA)

    args = parser.parse_args(argv)
    if args.command == "ingest-swebench":
        records = ingest_swebench(args.raw_dir)
        args.data.parent.mkdir(parents=True, exist_ok=True)
        write_records(records, args.data)
        print(f"wrote {len(records)} records to {args.data}")
    else:
        print(render_table(resolution_rates(read_records(args.data))))
