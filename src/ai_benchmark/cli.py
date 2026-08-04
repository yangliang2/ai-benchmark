"""The ai-bench command: ingest sources into the unified dataset and query it."""

import argparse
import os
from datetime import date
from pathlib import Path

from ai_benchmark.classify import (
    Label,
    cache_key,
    classify_records,
    load_cache,
    needs_classification,
    write_cache,
)
from collections.abc import Callable
from functools import partial

from ai_benchmark.aider import ingest_aider
from ai_benchmark.dataset import IngestError, merge_records, read_records, write_records
from ai_benchmark.instances import (
    InstanceContext,
    fetch_swebench_rows,
    load_instances,
    swebench_context_from_rows,
    write_instances,
)
from ai_benchmark.firstparty import (
    DEFAULT_MODELS,
    evaluate,
    load_runs,
    load_tasks,
    run_live,
)
from ai_benchmark.queries import (
    category_rates,
    published_aggregates,
    render_aggregate_table,
    render_category_table,
    render_table,
    resolution_rates,
)
from ai_benchmark.report import pareto_points, render_report
from ai_benchmark.schema import Record
from ai_benchmark.swebench import ingest_swebench

DEFAULT_DATA = Path("data/unified.jsonl")
DEFAULT_CACHE = Path("data/classification-cache.json")
DEFAULT_INSTANCES = Path("data/instance-context.json")


def _merge_into(new: list[Record], data: Path) -> None:
    existing = read_records(data) if data.exists() else []
    data.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_records(existing, new)
    write_records(merged, data)
    print(f"merged {len(new)} records into {data} ({len(merged)} total)")


def _ingest_command(
    args: argparse.Namespace, ingester: Callable[[Path], list[Record]]
) -> None:
    _merge_into(ingester(args.raw_dir), args.data)


INGESTERS: dict[str, tuple[Callable[[Path], list[Record]], str]] = {
    "ingest-swebench": (
        ingest_swebench,
        "merge a directory of SWE-bench per-instance submissions into the dataset",
    ),
    "ingest-aider": (
        ingest_aider,
        "merge Aider polyglot leaderboard data into the dataset",
    ),
}


def _table_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    if args.by_category:
        print(render_category_table(category_rates(records)))
    else:
        print(render_table(resolution_rates(records)))
    if aggregates := published_aggregates(records):
        print()
        print(f"aggregate records ({len(aggregates)}), as published — not pooled above:")
        print(render_aggregate_table(aggregates))


def _eval_command(args: argparse.Namespace) -> None:
    tasks = load_tasks(args.tasks)
    if args.live:
        log = args.log or Path("data/first-party-runs") / f"{date.today().isoformat()}.jsonl"
        runs = run_live(tasks, args.model or DEFAULT_MODELS, log)
        source = str(log)
        print(f"ran {len(runs)} live runs; raw log written to {log}")
    else:
        if args.model or args.log:
            raise SystemExit("--model and --log apply only to --live runs")
        runs = load_runs(args.replay)
        source = str(args.replay)
    records = evaluate(tasks, runs, source=source)
    resolved = int(sum(r.quality_value for r in records))
    print(f"evaluated {len(records)} runs over {len(tasks)} tasks ({resolved} resolved)")
    _merge_into(records, args.data)


def _report_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_report(pareto_points(records)), encoding="utf-8")
    print(f"wrote Pareto report over {len(records)} records to {args.out}")


def _never_llm(
    benchmark: str, instance_id: str, context: InstanceContext | None
) -> Label:
    raise AssertionError("warm cache must not reach the LLM")


def _fetch_swebench_context_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    wanted = {
        r.instance_id
        for r in records
        if r.benchmark == "swe-bench-verified" and r.instance_id is not None
    }
    fetched = swebench_context_from_rows(
        row for row in fetch_swebench_rows() if row["instance_id"] in wanted
    )
    existing = load_instances(args.out) if args.out.exists() else {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_instances(existing | fetched, args.out)
    print(
        f"fetched context for {len(fetched)} of {len(wanted)} swe-bench-verified "
        f"instance(s) into {args.out}"
    )


def _classify_command(args: argparse.Namespace) -> None:
    records = read_records(args.data)
    cache = load_cache(args.cache) if args.cache.exists() else {}
    instances = load_instances(args.instances) if args.instances.exists() else {}

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

    classified, cache_after, llm_calls = classify_records(records, cache, llm, instances)
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

    for name, (ingester, help_text) in INGESTERS.items():
        ingest = subcommands.add_parser(name, help=help_text)
        ingest.add_argument("raw_dir", type=Path)
        ingest.add_argument("--data", type=Path, default=DEFAULT_DATA)
        ingest.set_defaults(command=partial(_ingest_command, ingester=ingester))

    table = subcommands.add_parser(
        "table", help="print instance-level resolution rates per benchmark x combination"
    )
    table.add_argument("--data", type=Path, default=DEFAULT_DATA)
    table.add_argument(
        "--by-category", action="store_true", help="group rates by task category"
    )
    table.set_defaults(command=_table_command)

    evaluate_parser = subcommands.add_parser(
        "eval",
        help="run the first-party eval (live via claude-code, or replay a raw "
        "run log) and merge the records",
    )
    evaluate_parser.add_argument(
        "--tasks", type=Path, default=Path("tasks/first-party-v0.yaml")
    )
    evaluate_parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    mode = evaluate_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--replay", type=Path, help="replay a raw run log instead of running live"
    )
    mode.add_argument(
        "--live", action="store_true", help="run live via the claude CLI"
    )
    evaluate_parser.add_argument(
        "--model",
        action="append",
        help=f"live model (repeatable; default: {', '.join(DEFAULT_MODELS)})",
    )
    evaluate_parser.add_argument(
        "--log", type=Path, help="where a live run writes its raw log"
    )
    evaluate_parser.set_defaults(command=_eval_command)

    report = subcommands.add_parser(
        "report",
        help="write a static HTML report: per-category Pareto frontier of quality vs cost",
    )
    report.add_argument("--data", type=Path, default=DEFAULT_DATA)
    report.add_argument("--out", type=Path, default=Path("report.html"))
    report.set_defaults(command=_report_command)

    classify = subcommands.add_parser(
        "classify", help="classify unclassified instances via the committed cache + LLM"
    )
    classify.add_argument("--data", type=Path, default=DEFAULT_DATA)
    classify.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    classify.add_argument(
        "--instances",
        type=Path,
        default=DEFAULT_INSTANCES,
        help="instance-context store (problem statements + patch file lists)",
    )
    classify.set_defaults(command=_classify_command)

    fetch = subcommands.add_parser(
        "fetch-swebench-context",
        help="fetch problem statements + patch file lists for swe-bench-verified "
        "instances in the dataset from the HuggingFace datasets-server",
    )
    fetch.add_argument("--data", type=Path, default=DEFAULT_DATA)
    fetch.add_argument("--out", type=Path, default=DEFAULT_INSTANCES)
    fetch.set_defaults(command=_fetch_swebench_context_command)

    args = parser.parse_args(argv)
    try:
        args.command(args)
    except IngestError as error:
        raise SystemExit(f"error: {error}") from error
