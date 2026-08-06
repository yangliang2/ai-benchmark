"""The ai-bench command: ingest sources into the unified dataset and query it."""

import argparse
import os
from collections.abc import Callable
from functools import partial
from pathlib import Path

from ai_benchmark import firstparty_v1, reconcile_v1
from ai_benchmark.aider import ingest_aider
from ai_benchmark.classify import (
    Label,
    cache_key,
    classify_records,
    load_cache,
    needs_classification,
    write_cache,
)
from ai_benchmark.dataset import IngestError, merge_records, read_records, write_records
from ai_benchmark.firstparty import (
    DEFAULT_MODELS,
    RUN_TIMEOUT_S,
    evaluate,
    load_runs,
    load_tasks,
    local_today,
    run_live,
)
from ai_benchmark.instances import (
    SWEBENCH_BENCHMARK,
    InstanceContext,
    fetch_swebench_rows,
    load_instances,
    swebench_context_from_rows,
    write_instances,
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
DEFAULT_V1_RUNS = Path("data/first-party-v1-runs")


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
        log = args.log or Path("data/first-party-runs") / f"{local_today().isoformat()}.jsonl"
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


def _eval_v1_command(args: argparse.Namespace) -> None:
    """Run the v1 eval: live (tools-enabled claude-code in a fresh workdir per
    run, workdir diffs captured into the raw run log) or replay of such a log.
    Grading is the same pipeline either way — each logged diff, by execution."""
    if args.timeout is not None and args.timeout <= 0:
        # Checked before anything runs: a non-positive timeout would kill
        # every run after billing had already started.
        raise SystemExit("error: --timeout must be a positive number of seconds")
    if args.live and not args.sweep:
        # Also checked before anything runs, and required rather than
        # defaulted: reconciliation counts its rounds by sweep id, and the two
        # values the runner could have guessed both miscount. The date merges
        # two sweeps run in one day; the log's name splits one sweep across
        # the invocations that ran its models or resumed it.
        raise SystemExit(
            "error: --live runs need a --sweep id naming the sweep this "
            "invocation is part of; reuse it for every invocation of one sweep"
        )
    tasks = firstparty_v1.load_task_set(args.tasks)
    if args.live:
        log = args.log or DEFAULT_V1_RUNS / f"{local_today().isoformat()}.jsonl"
        # The default timeout lives on run_live alone; None means "not given".
        timeout = {} if args.timeout is None else {"timeout_s": args.timeout}
        runs = firstparty_v1.run_live(
            tasks, args.model or DEFAULT_MODELS, log, sweep=args.sweep, **timeout
        )
        source = str(log)
        print(f"ran {len(runs)} live runs; raw log written to {log}")
    else:
        if args.model or args.log or args.timeout is not None or args.sweep:
            raise SystemExit(
                "--model, --log, --timeout and --sweep apply only to --live runs"
            )
        runs = firstparty_v1.load_runs(args.replay)
        source = str(args.replay)
    records = firstparty_v1.evaluate(tasks, runs, source=source)
    resolved = int(sum(r.quality_value for r in records))
    print(f"evaluated {len(records)} runs over {len(tasks)} tasks ({resolved} resolved)")
    _merge_into(records, args.data)


def _lint_v1_command(args: argparse.Namespace) -> None:
    tasks = firstparty_v1.load_task_set(args.tasks)
    if problems := firstparty_v1.lint_task_set(tasks):
        raise SystemExit("\n".join([f"error: {problem}" for problem in problems]))
    print(f"lint clean: {len(tasks)} task(s) in {args.tasks}")


def _reconcile_v1_command(args: argparse.Namespace) -> None:
    """Report what the task set predicted against what the sweeps did.

    Reads the raw run logs and the task set, and writes nothing: no record is
    merged, no log is appended to. Verdicts come from replaying each logged
    diff against its task's held-out tests — the same computation eval-v1
    --replay does, and the only way a rung is derivable from a log at all,
    since a run-log row carries the diff but no verdict. No agent, no LLM and
    no network are involved, so the report stays recomputable from checked-in
    artifacts by this one command.
    """
    tasks = firstparty_v1.load_task_set(args.tasks)
    logs = reconcile_v1.collect_logs(args.replay or [DEFAULT_V1_RUNS])
    print(reconcile_v1.reconcile(tasks, args.tasks, logs))


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
    """Context is wanted for every SWE-bench instance we hold a record or a
    cached label for — the cache matters because the committed cache outlives
    any locally built dataset."""
    records = read_records(args.data) if args.data.exists() else []
    prefix = f"{SWEBENCH_BENCHMARK}/"
    wanted = {
        r.instance_id
        for r in records
        if r.benchmark == SWEBENCH_BENCHMARK and r.instance_id is not None
    }
    if args.cache.exists():
        wanted |= {
            key.removeprefix(prefix)
            for key in load_cache(args.cache)
            if key.startswith(prefix)
        }
    if not wanted:
        print(f"no {SWEBENCH_BENCHMARK} instances in {args.data} or {args.cache}")
        return
    fetched = swebench_context_from_rows(
        row for row in fetch_swebench_rows() if row["instance_id"] in wanted
    )
    existing = load_instances(args.out) if args.out.exists() else {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_instances(existing | fetched, args.out)
    print(
        f"fetched context for {len(fetched)} of {len(wanted)} {SWEBENCH_BENCHMARK} "
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

    v1_tasks_default = Path("tasks/first-party-v1")

    evaluate_v1 = subcommands.add_parser(
        "eval-v1",
        help="run the first-party v1 eval (live via tools-enabled claude-code, "
        "or replay a raw run log), grading each workdir diff by running the "
        "task's held-out tests, and merge the records",
    )
    evaluate_v1.add_argument("--tasks", type=Path, default=v1_tasks_default)
    evaluate_v1.add_argument("--data", type=Path, default=DEFAULT_DATA)
    v1_mode = evaluate_v1.add_mutually_exclusive_group(required=True)
    v1_mode.add_argument(
        "--replay", type=Path, help="replay a raw run log instead of running live"
    )
    v1_mode.add_argument(
        "--live", action="store_true",
        help="run live via the claude CLI, tools enabled",
    )
    evaluate_v1.add_argument(
        "--model",
        action="append",
        help=f"live model (repeatable; default: {', '.join(DEFAULT_MODELS)})",
    )
    evaluate_v1.add_argument(
        "--log", type=Path, help="where a live run writes its raw log"
    )
    evaluate_v1.add_argument(
        "--timeout",
        type=int,
        help=f"per-run live timeout in seconds (default: {RUN_TIMEOUT_S})",
    )
    evaluate_v1.add_argument(
        "--sweep",
        help="the sweep this invocation is part of, stamped on every row it "
        "writes; required for --live, and there is no default because both "
        "guesses miscount. reconcile-v1 counts one round per sweep id, so give "
        "every invocation of one sweep the same id — models run in separate "
        "invocations, a sweep resumed after a crash — and a new sweep a new one",
    )
    evaluate_v1.set_defaults(command=_eval_v1_command)

    lint_v1 = subcommands.add_parser(
        "lint-v1",
        help="check the first-party v1 task set's authoring invariants by "
        "running each task's grading tests on its pristine repository",
    )
    lint_v1.add_argument("--tasks", type=Path, default=v1_tasks_default)
    lint_v1.set_defaults(command=_lint_v1_command)

    reconcile_v1_parser = subcommands.add_parser(
        "reconcile-v1",
        help="report the v1 task set's pre-registered difficulty predictions "
        "against what the sweeps did: hit-rate, per-knob/per-level grouping "
        "against the zero-knob baseline, family ladders, crux/control pairs "
        "and no-separation flags",
        description=(
            "Read the raw run logs and the task set, and report predictions "
            "against outcomes. Writes nothing: no record is merged and no log "
            "is appended to. A run-log row carries the workdir diff but no "
            "verdict, so the observed rungs are obtained by replaying each "
            "logged diff against its task's held-out grading tests — the same "
            "computation `eval-v1 --replay` performs, with no agent, no LLM "
            "and no network, which is what keeps every number here "
            "recomputable from checked-in artifacts by this one command."
        ),
    )
    reconcile_v1_parser.add_argument("--tasks", type=Path, default=v1_tasks_default)
    reconcile_v1_parser.add_argument(
        "--replay",
        type=Path,
        action="append",
        help="a raw run log, or a directory of them (repeatable; default: "
        f"{DEFAULT_V1_RUNS})",
    )
    reconcile_v1_parser.set_defaults(command=_reconcile_v1_command)

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
    fetch.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    fetch.add_argument("--out", type=Path, default=DEFAULT_INSTANCES)
    fetch.set_defaults(command=_fetch_swebench_context_command)

    args = parser.parse_args(argv)
    try:
        args.command(args)
    except IngestError as error:
        raise SystemExit(f"error: {error}") from error
