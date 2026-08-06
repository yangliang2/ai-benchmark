"""reconcile-v1: what the task set predicted, read against what the sweeps did.

The knob experiment is only falsifiable if the predictions registered before a
sweep can be scored against it afterwards by something other than memory. This
module is that something: it reads the raw run logs and the task set, and
reports per-task hits and misses, how outcomes group by knob and level against
the zero-knob baseline, whether each family climbs its ladder, what each
crux/control pair cost, and which knobs moved nothing.

**Where the verdicts come from.** A raw run-log row carries the workdir diff
but no verdict, so an observed rung is not derivable from the log alone —
something has to grade. This module grades the way `eval-v1 --replay` does, by
sharing its code path: each logged diff is applied to a fresh copy of the
task's pristine repository, the held-out grading tests are laid over the top,
and the suite is run. That keeps the report on the read side of the provenance
boundary as CONTEXT.md draws it ("live runs write it, evaluation and replay
only ever read it"): no agent, no LLM, no network, no run log written, and no
record merged. It also keeps the design note's exit criterion true —
every number here is recomputable from checked-in artifacts by one command,
which reading an evaluated dataset instead would not be, since the dataset is
a build product and is not checked in.
"""

import textwrap
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Literal

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    BASELINE_TASK_IDS,
    BENCHMARK,
    GRADE_TIMEOUT_S,
    KNOB_LEVELS,
    Construction,
    Run,
    Rung,
    Task,
    construction_problems,
    evaluate,
    load_runs,
)

# The operational difficulty ladder, weakest model first: a task's observed
# rung is named after the weakest model that resolved it, and one no model
# resolved is unsolved. The models are pinned rather than recognised by name,
# because admitting a model is a decision about where it sits on the ladder —
# a run logged under a model nobody has made that decision for fails loudly
# here rather than quietly leaving a denominator.
LADDER: tuple[tuple[str, Rung], ...] = (
    ("claude-haiku-4-5", "haiku-solvable"),
    ("claude-sonnet-5", "sonnet-only"),
)
LADDER_MODELS: tuple[str, ...] = tuple(model for model, _ in LADDER)

# What a task's runs are allowed to say about it. Two of these are not rungs:
# a task no log mentions is `unswept`, and one whose runs cannot decide between
# two rungs — sonnet resolved it but haiku never ran, so it is either
# haiku-solvable or sonnet-only — is `incomplete`. Neither is ever scored, and
# neither is silently read as `unsolved`.
Observed = Literal["haiku-solvable", "sonnet-only", "unsolved", "incomplete", "unswept"]

RUNGS: tuple[Observed, ...] = (*(rung for _, rung in LADDER), "unsolved")
_HEIGHT: dict[Observed, int] = {rung: height for height, rung in enumerate(RUNGS)}
_REPORTED: tuple[Observed, ...] = (*RUNGS, "incomplete", "unswept")

# The kill discipline of docs/design/task-difficulty-and-ex-ante-profiles.md
# section 9: a knob that separates nothing across this many sweeps is demoted.
SILENT_ROUNDS_TO_DEMOTE = 2

# The header's legend for what a round is. Printed every time rather than only
# when the two keyings meet: the round count is the number the kill discipline
# is read off, and it is not readable without knowing what keyed it.
_ROUND_KEYING_NOTE = (
    "a round is one sweep: a run keys on the sweep id it carries, or on the "
    "as-of date it ran on when it carries none. So two sweeps run in one day "
    "count as two rounds and one sweep spilling across midnight counts as one "
    "— except among rows logged before the id existed, where the date is all "
    "there is and both miscounts remain."
)

_BASELINE_LABEL = "(baseline)"


@dataclass(frozen=True)
class Round:
    """One sweep, as the report counts them.

    A run says which sweep it belongs to by carrying a sweep id. A run logged
    before that field existed says only what day it ran on, so it falls back
    to its as-of date — which is the weaker key the sweep id was added to
    replace: it splits a sweep that spilled across midnight and merges two
    sweeps run on one day. Both keyings can appear in one report, so a round
    records which of them produced it and says so in its label.

    `as_of` is the earliest as-of date among the runs keyed to this round. For
    a legacy round that date *is* the key; for a sweep round it only places
    the round in time, so that the kill discipline's rows read chronologically
    even though a sweep id says nothing about when it ran.
    """

    sweep: str | None
    as_of: date

    @property
    def label(self) -> str:
        if self.sweep is None:
            return f"as-of {self.as_of.isoformat()}"
        return f"sweep {self.sweep}"

    @property
    def sort_key(self) -> tuple[date, str]:
        return (self.as_of, self.sweep or "")


@dataclass(frozen=True)
class Outcome:
    """What one task's runs said about it, and when they said it."""

    task: Task
    # Only the ladder models that actually ran this task, so that a missing
    # model reads as missing rather than as a failure.
    resolved: Mapping[str, bool]
    rung: Observed
    # The round this task was swept in: the latest of the rounds its runs
    # belong to, so a cell finished in a second sweep counts to the sweep that
    # finished it.
    round: Round | None

    @property
    def determined(self) -> bool:
        return self.rung in _HEIGHT

    @property
    def swept(self) -> bool:
        return self.rung != "unswept"

    @property
    def construction(self) -> Construction | None:
        return self.task.construction


# --- reading the inputs --------------------------------------------------------


def collect_logs(paths: Sequence[Path]) -> list[Path]:
    """Every run log named by these paths, each of which is a log or a
    directory of them. Sorted, because the report names the logs it read and
    the same inputs have to produce the same bytes."""
    logs: set[Path] = set()
    for path in paths:
        if path.is_dir():
            logs.update(path.glob("*.jsonl"))
        elif path.exists():
            logs.add(path)
        else:
            raise IngestError(f"{path}: no such run log or directory of run logs")
    return sorted(logs)


def observed_outcomes(
    tasks: list[Task], runs: list[Run], *, source: str, timeout_s: int = GRADE_TIMEOUT_S
) -> dict[str, Outcome]:
    """Grade every logged diff and reduce each task's runs to one rung.

    Grading goes through `evaluate`, which is also what makes the two failures
    that would otherwise corrupt the report loud: a run naming a task that is
    not in the set, and two runs of one task x agent x model cell, whose
    verdicts would have to be silently picked between.
    """
    _check_declarations(tasks)
    _check_ladder(runs)
    records = evaluate(tasks, runs, source=source, timeout_s=timeout_s)

    resolved: dict[str, dict[str, bool]] = {task.id: {} for task in tasks}
    for record in records:
        assert record.instance_id is not None  # evaluate writes the task id
        resolved[record.instance_id][record.model] = bool(record.quality_value)

    # Rounds are read off the runs rather than the records: a record carries
    # the as-of date but not the sweep id, and the sweep id is the round key
    # wherever a run has one. `evaluate` has already refused a run naming a
    # task the set does not have, so every id here is one of these tasks.
    by_key = rounds_by_key(runs)
    rounds: dict[str, list[Round]] = {task.id: [] for task in tasks}
    for run in runs:
        rounds[run.task_id].append(by_key[round_key(run)])
    return {
        task.id: Outcome(
            task=task,
            resolved=resolved[task.id],
            rung=observed_rung(resolved[task.id]),
            round=(
                max(rounds[task.id], key=lambda round: round.sort_key)
                if rounds[task.id]
                else None
            ),
        )
        for task in tasks
    }


def round_key(run: Run) -> str | date:
    """What groups this run with the other runs of its sweep.

    The sweep id when the row carries one, and the as-of date when it does
    not. The two can never collide: a str key and a date key are different
    keys even when a sweep was named after the day it ran.
    """
    return run.as_of if run.sweep is None else run.sweep


def rounds_by_key(runs: Iterable[Run]) -> dict[str | date, Round]:
    """One Round per key, dated by the earliest run keyed to it.

    Dating the round here rather than on each run is what keeps a sweep whole:
    every row of one sweep resolves to the same Round however many days the
    sweep took, which is the whole point of keying on the id.
    """
    dates: dict[str | date, list[date]] = {}
    for run in runs:
        dates.setdefault(round_key(run), []).append(run.as_of)
    return {
        key: Round(sweep=key if isinstance(key, str) else None, as_of=min(days))
        for key, days in dates.items()
    }


def observed_rung(resolved: Mapping[str, bool]) -> Observed:
    """The rung these per-model verdicts put a task on.

    The weakest model that resolved it names the rung, so a stronger model's
    verdict cannot lower it. A weaker model that never ran leaves the rung
    undecided rather than assumed: sonnet resolving a task haiku never saw is
    consistent with both haiku-solvable and sonnet-only.
    """
    if not resolved:
        return "unswept"
    for model, rung in LADDER:
        if model not in resolved:
            return "incomplete"
        if resolved[model]:
            return rung
    return "unsolved"


def _check_declarations(tasks: list[Task]) -> None:
    """Every task is either a frozen baseline control or declares how it was
    built. The lint already refuses anything else before a paid run; checked
    again here because the alternative is reconciliation quietly deciding for
    itself which of the two an undeclared task is."""
    if problems := [problem for task in tasks for problem in construction_problems(task)]:
        raise IngestError(
            "the task set does not declare itself well enough to reconcile:\n"
            + "\n".join(f"  {problem}" for problem in problems)
        )


def _check_ladder(runs: list[Run]) -> None:
    """The report reads one agent's ladder, over the models the ladder names."""
    if strangers := sorted({run.model for run in runs} - set(LADDER_MODELS)):
        raise IngestError(
            f"run log(s) carry model(s) {strangers}, which the operational "
            f"difficulty ladder does not name — it runs {list(LADDER_MODELS)}, and "
            "a run with no rung would leave a denominator without being counted"
        )
    if len(agents := sorted({run.agent for run in runs})) > 1:
        raise IngestError(
            f"run log(s) carry more than one agent ({agents}) — the ladder is a "
            "ladder of models, so pooling two harnesses onto it would attribute "
            "one harness's failures to the other's rung"
        )


# --- grouping ------------------------------------------------------------------


def knob_order(knob_id: str) -> int:
    return int(knob_id[1:])


def level_order(knob_id: str, level: str) -> tuple[int, str]:
    """Where a level sits on its knob's ladder.

    The enumerated ladders run easy to hard — K1 acceptance to intent, K8
    covered to misleading, K9 none to single — which is what lets a family be
    checked for climbing its ladder and a pair's crux be told from its control
    without either being written down twice. Knobs whose ladder the design note
    has not enumerated sort their levels alphabetically instead, which puts
    them in some order without pretending the order means difficulty.
    """
    levels = KNOB_LEVELS.get(knob_id, ())
    return (levels.index(level) if level in levels else len(levels), level)


def constructed(outcomes: Iterable[Outcome]) -> list[Outcome]:
    return [outcome for outcome in outcomes if outcome.construction is not None]


def baseline(outcomes: Iterable[Outcome]) -> list[Outcome]:
    return [outcome for outcome in outcomes if outcome.task.id in BASELINE_TASK_IDS]


def by_knob_level(outcomes: Iterable[Outcome]) -> dict[tuple[str, str], list[Outcome]]:
    """The outcomes under each (knob, level), a task appearing under every knob
    it activates."""
    groups: dict[tuple[str, str], list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        for knob, level in outcome.construction.levels.items():
            groups.setdefault((knob, level), []).append(outcome)
    return groups


def rung_set(outcomes: Iterable[Outcome]) -> frozenset[Observed]:
    """The rungs these outcomes landed on, undetermined ones left out."""
    return frozenset(outcome.rung for outcome in outcomes if outcome.determined)


# --- rendering -----------------------------------------------------------------


def _table(rows: Sequence[Sequence[str]], *, indent: str) -> list[str]:
    """Header row first, columns padded to the widest cell."""
    widths = [max(len(cell) for cell in column) for column in zip(*rows)]
    return [
        indent + "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in rows
    ]


def _rung_counts(outcomes: Sequence[Outcome]) -> str:
    counts = Counter(outcome.rung for outcome in outcomes)
    parts = [f"{rung} x{counts[rung]}" for rung in _REPORTED if counts[rung]]
    return ", ".join(parts) if parts else "-"


def _rung_set_text(outcomes: Sequence[Outcome]) -> str:
    ranked = sorted(rung_set(outcomes), key=lambda rung: _HEIGHT[rung])
    return "{" + ", ".join(ranked) + "}"


def _model_cell(outcomes: Sequence[Outcome], model: str) -> str:
    ran = [outcome for outcome in outcomes if model in outcome.resolved]
    if not ran:
        return "-"
    return f"{sum(outcome.resolved[model] for outcome in ran)}/{len(ran)}"


def _delta_text(crux: Outcome, control: Outcome) -> str:
    """How much harder the crux turned out than its control.

    A negative delta says the control was the harder of the two, which is the
    pair failing to isolate what it was built to isolate — so it is spelled
    out rather than left to the reader to notice the sign.
    """
    if not (crux.determined and control.determined):
        return "unknown"
    delta = _HEIGHT[crux.rung] - _HEIGHT[control.rung]
    if delta == 0:
        return "no rung delta"
    rungs = "rung" if abs(delta) == 1 else "rungs"
    return f"{delta:+d} {rungs} ({'crux' if delta > 0 else 'control'} harder)"


def render(
    outcomes: Mapping[str, Outcome], *, tasks_root: Path, logs: Sequence[Path]
) -> str:
    ordered = [outcomes[task_id] for task_id in sorted(outcomes)]
    return "\n".join([
        *_header(ordered, tasks_root=tasks_root, logs=logs),
        "",
        *_predictions(ordered),
        "",
        *_knob_grouping(ordered),
        "",
        *_families(ordered),
        "",
        *_pairs(ordered),
        "",
        *_flags(ordered),
    ])


def _header(
    outcomes: Sequence[Outcome], *, tasks_root: Path, logs: Sequence[Path]
) -> list[str]:
    swept = [outcome for outcome in outcomes if outcome.swept]
    runs = sum(len(outcome.resolved) for outcome in outcomes)
    rounds = sorted(
        {outcome.round for outcome in swept if outcome.round is not None},
        key=lambda round: round.sort_key,
    )
    ladder = "; ".join(f"{model} -> {rung}" for model, rung in LADDER)
    lines = [
        f"reconciliation: {BENCHMARK}",
        (
            f"  task set   {tasks_root} — {len(outcomes)} task(s): "
            f"{len(baseline(outcomes))} zero-knob baseline, "
            f"{len(constructed(outcomes))} constructed"
        ),
    ]
    lines += [
        f"  {'run logs' if index == 0 else '':<10} {log}"
        for index, log in enumerate(logs)
    ] or ["  run logs   (none)"]
    lines += [
        f"  runs       {runs} over {len(swept)} task(s)",
        # Rounds are counted off the tasks, not off the log files: a task's
        # round is the latest of the rounds its runs belong to, so one log can
        # carry more than one round and one round more than one log.
        f"  rounds     {len(rounds)} round(s)"
        + (f": {', '.join(round.label for round in rounds)}" if rounds else ""),
        f"             {_keying(rounds)}",
        *_wrap(_ROUND_KEYING_NOTE, indent="             "),
        f"  ladder     {ladder}; neither -> unsolved",
        "  verdicts   replayed: every logged diff re-graded by its task's held-out",
        "             tests, the computation eval-v1 --replay does. No agent, no LLM,",
        "             no network; the run logs are read and never added to, and no",
        "             record is merged into the dataset.",
    ]
    return lines


def _keying(rounds: Sequence[Round]) -> str:
    """How many of these rounds each keying produced."""
    if not rounds:
        return "(no swept run to key a round on)"
    by_sweep = sum(round.sweep is not None for round in rounds)
    by_date = len(rounds) - by_sweep
    if not by_date:
        return f"{by_sweep} keyed on a sweep id"
    if not by_sweep:
        return f"{by_date} keyed on an as-of date; no run carries a sweep id"
    return f"{by_sweep} keyed on a sweep id, {by_date} on an as-of date"


def _predictions(outcomes: Sequence[Outcome]) -> list[str]:
    predicted = constructed(outcomes)
    scored = [outcome for outcome in predicted if outcome.determined]
    hits = [
        outcome for outcome in scored
        if outcome.construction is not None
        and outcome.construction.prediction.rung == outcome.rung
    ]
    rate = f"{len(hits) / len(scored):.1%}" if scored else "n/a"
    lines = [
        "1. prediction reconciliation",
        (
            f"   {len(predicted)} constructed task(s): "
            f"{sum(outcome.swept for outcome in predicted)} swept, "
            f"{sum(not outcome.swept for outcome in predicted)} unswept"
        ),
        f"   hit-rate: {len(hits)}/{len(scored)} scored ({rate})",
    ]
    if not predicted:
        return [*lines, "   (no constructed task in the task set)"]

    rows: list[Sequence[str]] = [("task", "predicted", "observed", "verdict")]
    misses: list[Outcome] = []
    for outcome in predicted:
        assert outcome.construction is not None
        prediction = outcome.construction.prediction
        verdict: str
        if not outcome.determined:
            verdict = outcome.rung
        elif prediction.rung == outcome.rung:
            verdict = "hit"
        else:
            verdict = "miss"
            misses.append(outcome)
        rows.append((outcome.task.id, prediction.rung, outcome.rung, verdict))
    lines += ["", *_table(rows, indent="   ")]

    if misses:
        lines += ["", "   misses, with the rationale that was registered for them:"]
        for outcome in misses:
            assert outcome.construction is not None
            prediction = outcome.construction.prediction
            lines += [
                (
                    f"   {outcome.task.id}: predicted {prediction.rung}, "
                    f"observed {outcome.rung}"
                ),
                *_wrap(prediction.rationale, indent="     "),
            ]
    return lines


def _wrap(text: str, *, indent: str, width: int = 74) -> list[str]:
    return textwrap.wrap(
        " ".join(text.split()), width=width,
        initial_indent=indent, subsequent_indent=indent,
    )


def _knob_grouping(outcomes: Sequence[Outcome]) -> list[str]:
    groups = by_knob_level(outcomes)
    lines = ["2. knob grouping, against the zero-knob baseline of the same category"]
    if not groups:
        return [*lines, "   (no constructed task in the task set)"]

    controls = baseline(outcomes)
    header = ("level", "category", "tasks", "swept", *LADDER_MODELS, "observed rungs")
    for knob in sorted({knob for knob, _ in groups}, key=knob_order):
        levels = sorted(
            (level for other, level in groups if other == knob),
            key=lambda level: level_order(knob, level),
        )
        rows: list[Sequence[str]] = [header]
        categories: set[str] = set()
        for level in levels:
            members = groups[(knob, level)]
            for category in sorted({member.task.category for member in members}):
                categories.add(category)
                rows.append(_group_row(
                    level, category,
                    [m for m in members if m.task.category == category],
                ))
        for compared in sorted(categories):
            rows.append(_group_row(
                _BASELINE_LABEL, compared,
                [control for control in controls if control.task.category == compared],
            ))
        lines += ["", f"   {knob}", *_table(rows, indent="     ")]
    return lines


def _group_row(label: str, category: str, members: Sequence[Outcome]) -> Sequence[str]:
    return (
        label,
        category,
        str(len(members)),
        str(sum(member.swept for member in members)),
        *(_model_cell(members, model) for model in LADDER_MODELS),
        _rung_counts(members),
    )


def _families(outcomes: Sequence[Outcome]) -> list[str]:
    families: dict[str, list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        if outcome.construction.family is not None:
            families.setdefault(outcome.construction.family, []).append(outcome)

    lines = ["3. family ladders"]
    if not families:
        return [*lines, "   (no task family in the task set)"]

    for family in sorted(families):
        members = families[family]
        knob = _varied_knob(members)
        ordered = sorted(members, key=lambda member: level_order(knob, _level(member, knob)))
        rows: list[Sequence[str]] = [("level", "task", "predicted", "observed")]
        for member in ordered:
            assert member.construction is not None
            rows.append((
                _level(member, knob), member.task.id,
                member.construction.prediction.rung, member.rung,
            ))
        ladder = " -> ".join(_level(member, knob) for member in ordered)
        lines += [
            "",
            f"   {family} ({knob}: {ladder})",
            *_table(rows, indent="     "),
            f"     monotonic along the ladder: {_monotonic(ordered)}",
        ]
    return lines


def _level(outcome: Outcome, knob: str) -> str:
    assert outcome.construction is not None
    return outcome.construction.levels.get(knob, "-")


def _varied_knob(members: Sequence[Outcome]) -> str:
    """The knob a family varies: the one its members do not all set alike. The
    lint holds a family to exactly one such knob; a family that somehow has
    none (identical levels throughout) falls back to its lowest-numbered knob
    so the block still renders rather than the whole report failing."""
    activated: dict[str, set[str]] = {}
    for member in members:
        assert member.construction is not None
        for knob, level in member.construction.levels.items():
            activated.setdefault(knob, set()).add(level)
    varied = [knob for knob, levels in activated.items() if len(levels) > 1]
    return min(varied or activated, key=knob_order)


def _monotonic(ordered: Sequence[Outcome]) -> str:
    """Whether rungs climb (never fall) as the family's knob climbs its ladder.

    Variants without a determined rung are skipped rather than guessed at, and
    fewer than two determined rungs means the question is not yet answerable.
    """
    heights = [_HEIGHT[member.rung] for member in ordered if member.determined]
    undetermined = len(ordered) - len(heights)
    if len(heights) < 2:
        return f"unknown — {undetermined} of {len(ordered)} variant(s) without a rung"
    verdict = "yes" if all(a <= b for a, b in pairwise(heights)) else (
        "no — a variant further up the ladder landed on a lower rung"
    )
    if undetermined:
        return f"{verdict} (over the {len(heights)} variant(s) with a rung)"
    return verdict


def _pairs(outcomes: Sequence[Outcome]) -> list[str]:
    pairs: dict[str, list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        if outcome.construction.pair is not None:
            pairs.setdefault(outcome.construction.pair, []).append(outcome)

    lines = ["4. crux/control pairs"]
    if not pairs:
        return [*lines, "   (no paired task in the task set)"]

    ranked: list[Sequence[str]] = [
        ("pair", "crux", "control", "crux rung", "control rung", "delta")
    ]
    unranked: list[Sequence[str]] = [("pair", "task", "level", "observed rung")]
    for pair in sorted(pairs):
        members = pairs[pair]
        if len(members) != 2:
            ranked.append((
                pair, ", ".join(sorted(member.task.id for member in members)), "-",
                "-", "-", f"unknown — pair holds {len(members)} member(s)",
            ))
            continue
        knob = _varied_knob(members)
        if not KNOB_LEVELS.get(knob):
            # An unenumerated ladder orders its levels alphabetically, which
            # says nothing about difficulty. Calling the alphabetically later
            # member the crux would let the delta accuse a working pair of
            # failing to isolate what it was built to isolate, so this pair is
            # reported as two rungs and no claim about which should be higher.
            unranked += [
                (pair, member.task.id, f"{knob}={_level(member, knob)}", member.rung)
                for member in sorted(members, key=lambda member: member.task.id)
            ]
            continue
        control, crux = sorted(
            members, key=lambda member: level_order(knob, _level(member, knob))
        )
        ranked.append((
            pair,
            f"{crux.task.id} ({knob}={_level(crux, knob)})",
            f"{control.task.id} ({knob}={_level(control, knob)})",
            crux.rung, control.rung, _delta_text(crux, control),
        ))

    if len(ranked) > 1:
        lines += ["", *_table(ranked, indent="   ")]
    if len(unranked) > 1:
        lines += [
            "",
            *_wrap(
                "pairs varying a knob whose ladder the design note has not "
                "enumerated: its levels carry no difficulty order, so neither "
                "member is named the crux and no rung delta is claimed.",
                indent="   ",
            ),
            "",
            *_table(unranked, indent="   "),
        ]
    return lines


def _flags(outcomes: Sequence[Outcome]) -> list[str]:
    lines = [
        "5. no-separation flags",
        *_wrap(
            "criterion: within one round, a knob separates when two of its swept "
            "levels produced different sets of observed rungs — or, when only one "
            "level was swept, when that level's set differs from the zero-knob "
            "baseline's over the same task categories. The levels are read within "
            "the round, the baseline controls across all of them, because the "
            "baseline is swept once and a cell is never swept twice. At n=1 per "
            "cell a single task changes a set, so a flag is a reason to look, not "
            "a test.",
            indent="   ",
        ),
        *_wrap(
            f"kill discipline: a knob silent for {SILENT_ROUNDS_TO_DEMOTE} round(s) "
            "is demoted (docs/design/task-difficulty-and-ex-ante-profiles.md "
            "section 9). A round is one sweep, named below by the sweep id its "
            "runs carried — or, for runs logged before that field existed, by "
            "their as-of date, which is the weaker key: it still merges two "
            "sweeps run in one day and still splits one that ran past midnight. "
            "Read the labels below before reading a demotion off them.",
            indent="   ",
        ),
    ]
    groups = by_knob_level(outcomes)
    if not groups:
        return [*lines, "", "   (no constructed task in the task set)"]

    rounds = sorted(
        {outcome.round for outcome in outcomes if outcome.round is not None},
        key=lambda round: round.sort_key,
    )
    for knob in sorted({knob for knob, _ in groups}, key=knob_order):
        verdicts = [
            (round, _separation(knob, outcomes, round))
            for round in rounds
            if _activated_in(knob, outcomes, round)
        ]
        silent = sum(verdict.startswith("no separation") for _, verdict in verdicts)
        block = [
            f"   {knob}  {round.label}  {verdict}"
            for round, verdict in verdicts
        ] or [f"   {knob}  (no round has swept it)"]
        tail = f"       silent round(s): {silent}"
        if silent >= SILENT_ROUNDS_TO_DEMOTE:
            tail += (
                f" — demote {knob}: silent for the "
                f"{SILENT_ROUNDS_TO_DEMOTE} round(s) the kill discipline allows"
            )
        lines += ["", *block, tail]
    return lines


def _activated_in(knob: str, outcomes: Sequence[Outcome], round: Round) -> bool:
    """Whether any task activating this knob was swept in this round.

    A round that swept none of them has nothing to say about the knob, so it
    gets no row: a printed "not assessable" would read as a round the knob was
    tried in and the kill discipline would then have to explain it away.
    """
    return any(
        outcome.round == round
        and outcome.construction is not None
        and knob in outcome.construction.levels
        for outcome in outcomes
    )


def _separation(knob: str, outcomes: Sequence[Outcome], round: Round) -> str:
    """Whether this knob's levels told outcomes apart in this round.

    The levels are read within the round; the zero-knob controls are read
    across every round. A cell is only ever swept once, so the baseline cannot
    be re-swept alongside a later round's tasks — scoping the controls to the
    round too would leave every single-level knob permanently unassessable
    from the round after the baseline's onwards.
    """
    in_round = [outcome for outcome in outcomes if outcome.round == round]
    groups = {
        level: members
        for (other, level), members in by_knob_level(in_round).items()
        if other == knob and rung_set(members)
    }
    levels = sorted(groups, key=lambda level: level_order(knob, level))
    described = ", ".join(f"{level} {_rung_set_text(groups[level])}" for level in levels)

    if len(levels) >= 2:
        separated = len({rung_set(groups[level]) for level in levels}) > 1
        return f"{'separated' if separated else 'no separation'} — {described}"
    if len(levels) == 1:
        categories = {member.task.category for member in groups[levels[0]]}
        controls = [
            control for control in baseline(outcomes)
            if control.task.category in categories and control.determined
        ]
        if not controls:
            return (
                f"not assessable — one level swept ({described}) and no zero-knob "
                f"baseline of the same category ({', '.join(sorted(categories))}) "
                "has a rung in any round"
            )
        separated = rung_set(groups[levels[0]]) != rung_set(controls)
        return (
            f"{'separated' if separated else 'no separation'} — {described} vs "
            f"baseline {_rung_set_text(controls)}"
        )
    return "not assessable — no level of it has a rung in this round"


# --- the command ---------------------------------------------------------------


def reconcile(
    tasks: list[Task],
    tasks_root: Path,
    logs: Sequence[Path],
    *,
    timeout_s: int = GRADE_TIMEOUT_S,
) -> str:
    runs = [run for log in logs for run in load_runs(log)]
    outcomes = observed_outcomes(
        tasks,
        runs,
        source=", ".join(str(log) for log in logs) or "(no run log)",
        timeout_s=timeout_s,
    )
    return render(outcomes, tasks_root=tasks_root, logs=logs)
