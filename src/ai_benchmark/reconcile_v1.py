"""reconcile-v1: what the task set predicted, read against what the sweeps did.

The knob experiment is only falsifiable if the predictions registered before a
sweep can be scored against it afterwards by something other than memory. This
module is that something: it reads the raw run logs and the task set, and
reports per-task hits and misses, how outcomes group by knob and level against
the zero-knob baseline, whether each family climbs its ladder, what each
crux/control pair cost, which knobs moved nothing, and — for the tasks that
registered one — whether each effort claim came true on each model.

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
from itertools import combinations, pairwise
from pathlib import Path
from typing import Literal

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    BASELINE_TASK_IDS,
    BENCHMARK,
    GRADE_TIMEOUT_S,
    KNOB_LEVELS,
    Construction,
    EffortClaim,
    EffortMetric,
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
    def dated_label(self) -> str:
        """The label with the date the round ran on, for the places that name
        a round away from the table listing it — a demotion, above all. A
        sweep id says nothing about when it ran, and a demotion that cannot be
        placed in time cannot be checked against the sweeps that produced it."""
        if self.sweep is None:
            return self.label
        return f"{self.label} ({self.as_of.isoformat()})"

    @property
    def sort_key(self) -> tuple[date, str]:
        return (self.as_of, self.sweep or "")


@dataclass(frozen=True)
class Effort:
    """What one run cost, on the two axes an effort claim can be read on.

    Taken off the run-log row rather than off the graded record, and taken
    whatever the verdict was: a run that failed still spent its turns and its
    dollars, and an effort claim is a claim about what the work took, not
    about whether it worked.
    """

    turns: int
    cost_usd: float

    def value(self, metric: EffortMetric) -> float:
        return float(self.turns) if metric == "turns" else self.cost_usd


@dataclass(frozen=True)
class Outcome:
    """What one task's runs said about it, and when they said it."""

    task: Task
    # Only the ladder models that actually ran this task, so that a missing
    # model reads as missing rather than as a failure.
    resolved: Mapping[str, bool]
    # Keyed the same way and for the same reason: a model with no row here
    # never ran this task, which is the difference between a claim that came
    # out false and one nothing measured.
    effort: Mapping[str, Effort]
    rung: Observed
    # The round this task was swept in: the latest of the rounds its runs
    # belong to, so a cell finished in a second sweep counts to the sweep that
    # finished it. "Latest" is by the round's own date, which is when it
    # started, so a task swept in two overlapping sweeps attributes to the one
    # that started later rather than the one that finished it. Unreachable
    # under the sequential-sweep protocol (a sweep is read before the next is
    # launched); documented rather than fixed, because fixing it would mean
    # dating a round by its last run and that reads worse everywhere else.
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
    # What each run cost, read straight off the log rather than out of the
    # records: `evaluate` has already refused the two rows that would make
    # this ambiguous (an unknown task, two runs of one cell), so one row per
    # task x model is all there is to read.
    effort: dict[str, dict[str, Effort]] = {task.id: {} for task in tasks}
    for run in runs:
        rounds[run.task_id].append(by_key[round_key(run)])
        effort[run.task_id][run.model] = Effort(
            turns=run.turns, cost_usd=run.cost_usd
        )
    return {
        task.id: Outcome(
            task=task,
            resolved=resolved[task.id],
            effort=effort[task.id],
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


def pairs_by_id(outcomes: Iterable[Outcome]) -> dict[str, list[Outcome]]:
    """The outcomes under each pair id, unpaired tasks left out.

    Every member is kept, including the ones belonging to a pair of a size no
    pair should have: what the report and the effort grading each do with such
    a pair differs, and both need to see it to say so.
    """
    pairs: dict[str, list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        if outcome.construction.pair is not None:
            pairs.setdefault(outcome.construction.pair, []).append(outcome)
    return pairs


def rung_set(outcomes: Iterable[Outcome]) -> frozenset[Observed]:
    """The rungs these outcomes landed on, undetermined ones left out."""
    return frozenset(outcome.rung for outcome in outcomes if outcome.determined)


# --- grading the effort claims -------------------------------------------------

# What an effort claim can come out as. "not assessable" is the third state
# for the same reason the rung reconciliation has `unswept` and `incomplete`:
# a comparator no sweep reached says nothing about the claim, and reading it
# as a miss would invent a result out of an absent measurement.
Assessed = Literal["hit", "miss", "not assessable"]


@dataclass(frozen=True)
class Assessment:
    """One registered effort claim, read for one model.

    Per model rather than per task because that is the shape of the
    measurement: a run log holds one turns and one cost per task x model, and
    round 1's contrasts moved by different multiples on the two models (K9's
    turns 1.80x on haiku against 1.36x on sonnet). Collapsing them would
    average away the thing the claim is about.
    """

    task: str
    model: str
    claim: EffortClaim
    verdict: Assessed
    # Absent exactly when the run that would have measured it is absent, which
    # is what `not assessable` means and where its reason comes from.
    observed: float | None
    comparator: float | None
    # What the claim was read against, named so a miss can be checked: the
    # partner's task id, or the baseline the mean was taken over.
    against: str
    # Why it could not be read, when it could not.
    reason: str | None

    @property
    def ratio(self) -> float | None:
        if self.observed is None or not self.comparator:
            return None
        return self.observed / self.comparator


def effort_assessments(outcomes: Sequence[Outcome]) -> list[Assessment]:
    """Every registered effort claim, graded for every model on the ladder.

    Tasks in id order and models in ladder order, so the section this feeds
    is byte-identical run to run however the outcomes were collected.
    """
    controls = baseline(outcomes)
    partners = _pair_partners(outcomes)
    assessments: list[Assessment] = []
    for outcome in sorted(outcomes, key=lambda outcome: outcome.task.id):
        if outcome.construction is None:
            continue
        claim = outcome.construction.prediction.effort
        if claim is None:
            continue
        assessments.extend(
            _assess(outcome, claim, model, controls=controls, partners=partners)
            for model in LADDER_MODELS
        )
    return assessments


def _pair_partners(outcomes: Sequence[Outcome]) -> dict[str, Outcome]:
    """The other member of each task's pair, where the pair has exactly two.

    A pair of any other size has no defined partner, so nothing is recorded
    for its members and a claim against one is reported not assessable. The
    lint refuses such a pair before a sweep; this is what the report does if
    one reaches it anyway, rather than picking a member to compare against.
    """
    partners: dict[str, Outcome] = {}
    for members in pairs_by_id(outcomes).values():
        if len(members) == 2:
            one, other = members
            partners[one.task.id] = other
            partners[other.task.id] = one
    return partners


def _assess(
    outcome: Outcome,
    claim: EffortClaim,
    model: str,
    *,
    controls: Sequence[Outcome],
    partners: Mapping[str, Outcome],
) -> Assessment:
    """This task's own measurement against its comparator's, for one model.

    Nothing here is inferred from an absence. A missing run on either side, a
    pair without a partner and a category with no controls all end the same
    way: not assessable, with the reason named, and scored nowhere.
    """
    comparator, against, reason = _comparator(
        outcome, claim, model, controls=controls, partners=partners
    )
    measured = outcome.effort.get(model)
    observed = measured.value(claim.metric) if measured is not None else None
    verdict: Assessed = "not assessable"
    if observed is None:
        reason = f"{outcome.task.id} has no {model} run"
    elif reason is None and comparator is not None:
        # A comparator of zero is not a comparator: no multiple of it is
        # anything, so the claim is unreadable rather than trivially met.
        if not comparator:
            reason = f"{against} measured 0 {claim.metric} on {model}"
        else:
            verdict = (
                "hit" if observed >= claim.at_least_factor * comparator else "miss"
            )
    return Assessment(
        task=outcome.task.id,
        model=model,
        claim=claim,
        verdict=verdict,
        observed=observed,
        comparator=comparator,
        against=against,
        reason=reason if verdict == "not assessable" else None,
    )


def _comparator(
    outcome: Outcome,
    claim: EffortClaim,
    model: str,
    *,
    controls: Sequence[Outcome],
    partners: Mapping[str, Outcome],
) -> tuple[float | None, str, str | None]:
    """What this claim is read against: the value, its name, and — where there
    is no value — why there is none."""
    if claim.comparator == "pair":
        partner = partners.get(outcome.task.id)
        if partner is None:
            pair = outcome.construction.pair if outcome.construction else None
            return None, "its pair partner", (
                f"pair {pair!r} does not hold exactly two tasks, so "
                f"{outcome.task.id} has no partner to be read against"
            )
        measured = partner.effort.get(model)
        if measured is None:
            return None, partner.task.id, f"{partner.task.id} has no {model} run"
        return measured.value(claim.metric), partner.task.id, None

    category = outcome.task.category
    ran = [
        control for control in controls
        if control.task.category == category and model in control.effort
    ]
    against = f"the {category} baseline"
    if not ran:
        return None, against, (
            f"no {category} zero-knob baseline control has a {model} run"
        )
    # The mean, not the median. A factor claim is a claim about the size of a
    # cost, and at the handful of tasks per cell this experiment runs at a
    # median throws away the tail the effort signal has so far lived in — K7's
    # 36-turn haiku cell against a 9.8-turn baseline mean. Round 1's contrasts
    # were read off means for the same reason (design note section 11), so
    # reading a registered claim off medians would score it against numbers
    # nothing else in this project quotes.
    values = [control.effort[model].value(claim.metric) for control in ran]
    return sum(values) / len(values), f"{against} (mean of {len(ran)})", None


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
        "",
        # Last, and numbered after the five sections that were here before it,
        # rather than beside section 1 where it belongs by subject. The report
        # is read by diffing one round's against the last one's, so renumbering
        # the existing sections would move every line of a report to add one
        # block; and the kill discipline in section 5 still counts rung
        # silence alone, so printing effort above it would read as feeding it.
        *_effort_claims(ordered),
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
    pairs = pairs_by_id(outcomes)
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
            "minimum sample: a side of n graded tasks lands on at most n distinct "
            "rungs, so a side holding fewer graded tasks than the other side has "
            "rungs cannot reproduce that set however its runs come out. That "
            "difference is arithmetic rather than a knob effect, and is reported "
            "not assessable, naming the counts. The guard counts graded tasks per "
            "side — per level within the round, and the baseline's own tasks where "
            "a lone level is read against it — and it can only ever withdraw a "
            "claim of separation: two sides landing on the same set always pass "
            "it, so no knob is guarded into a silent round.",
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
        silent = [
            round for round, verdict in verdicts
            if verdict.startswith("no separation")
        ]
        block = [
            f"   {knob}  {round.label}  {verdict}"
            for round, verdict in verdicts
        ] or [f"   {knob}  (no round has swept it)"]
        tail = f"       silent round(s): {len(silent)}"
        if len(silent) >= SILENT_ROUNDS_TO_DEMOTE:
            # Naming them is the point: a demotion travels out of this report
            # into the design note and the tickets that follow it, and one
            # that does not say which rounds it counted cannot be checked
            # against the sweeps it was read off.
            counted = ", ".join(round.dated_label for round in silent)
            tail += (
                f" — demote {knob}: silent in {counted} — {len(silent)} round(s) "
                f"against the {SILENT_ROUNDS_TO_DEMOTE} the kill discipline allows"
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
        return _compare([(level, groups[level]) for level in levels], described)
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
        return _compare(
            [(levels[0], groups[levels[0]]), (_BASELINE_LABEL, controls)],
            f"{described} vs baseline {_rung_set_text(controls)}",
        )
    return "not assessable — no level of it has a rung in this round"


Side = tuple[str, Sequence[Outcome]]


def _compare(sides: Sequence[Side], described: str) -> str:
    """The verdict these sides support, guarded against sample size.

    Two sides separate when they landed on different sets of rungs — but a
    difference is only evidence when both sides had the tasks to land on one
    set. `_forced_apart` is what says they did not, and this is where its
    verdict becomes "not assessable" rather than "separated": an under-sampled
    difference is arithmetic, and reading it as a knob effect is what put a
    "separated" flag on K7 in round 1 (design note section 15, anomaly 3).

    Every side is compared with every other, and one believable difference is
    enough: a knob that separated two of its levels separated, whatever a
    third under-sampled level does or does not add.
    """
    differing = [
        (one, other) for one, other in combinations(sides, 2)
        if rung_set(one[1]) != rung_set(other[1])
    ]
    if not differing:
        return f"no separation — {described}"
    forced = [pair for pair in differing if _forced_apart(pair[0][1], pair[1][1])]
    if len(forced) < len(differing):
        return f"separated — {described}"
    return (
        f"not assessable — {described}; "
        + "; ".join(_forced_text(one, other) for one, other in forced)
    )


def _forced_apart(one: Sequence[Outcome], other: Sequence[Outcome]) -> bool:
    """Whether these two sides could not have matched however their runs came out.

    The minimum-sample guard, and the reason it is stated as a comparison
    rather than as a constant: a side of n graded tasks lands on at most n
    distinct rungs, so a side holding fewer tasks than the other side has
    rungs cannot reproduce that set whatever any of its runs does. The
    difference between them is then arithmetic and not a knob effect.

    It cannot silence a genuinely-sampled comparison, and cannot silence a
    knob into demotion, because sides landing on the *same* set always pass
    it: a set drawn from n tasks holds at most n rungs, so each side already
    has at least as many tasks as the shared set has rungs. The guard only
    ever withdraws a claim of separation.
    """
    return (
        len(_graded(one)) < len(rung_set(other))
        or len(_graded(other)) < len(rung_set(one))
    )


def _graded(outcomes: Sequence[Outcome]) -> list[Outcome]:
    """The outcomes a set comparison is built from: the ones with a rung."""
    return [outcome for outcome in outcomes if outcome.determined]


def _forced_text(one: Side, other: Side) -> str:
    small, large = sorted(
        (one, other), key=lambda side: (len(_graded(side[1])), side[0])
    )
    return (
        f"{small[0]} has {len(_graded(small[1]))} graded task(s) against "
        f"{large[0]}'s {len(rung_set(large[1]))} distinct rung(s), so the two "
        "sets could not have matched however the runs came out"
    )


def _factor_text(factor: float) -> str:
    """The registered factor, printed so it reads back as itself.

    `repr` and not a fixed precision: a factor is a bet, and a format that
    rounds it prints a claim nobody registered. `:g` rounded 1.5000001 to six
    significant digits and put "1.5" on the page beside the 1.50x ratio the
    same claim had been missed by, so the section read as an argument with
    itself over a number it had rounded. A float's repr is the shortest string
    that reads back as that exact float, so no two accepted factors print
    alike and none prints as a number it is not.
    """
    return repr(factor)


def _claim_text(claim: EffortClaim) -> str:
    """The registered claim, in the words it was registered in."""
    factor = _factor_text(claim.at_least_factor)
    return f"{claim.metric} >= {factor}x {claim.comparator}"


def _measured(value: float | None, metric: EffortMetric) -> str:
    """One measurement in the unit its metric is quoted in, or a dash where
    the run that would have produced it is missing."""
    if value is None:
        return "-"
    if metric == "cost":
        return f"${value:.4f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _effort_claims(outcomes: Sequence[Outcome]) -> list[str]:
    lines = ["6. effort-claim reconciliation"]
    assessments = effort_assessments(outcomes)
    if not assessments:
        # The round-1 task set's state, and the honest one: no task registered
        # an effort claim, so there is nothing here to be right or wrong about.
        # Said rather than omitted, because a section that disappears when it
        # has nothing to report is indistinguishable from one that broke.
        return [*lines, "   (no effort claim registered in the task set)"]

    graded = [a for a in assessments if a.verdict != "not assessable"]
    hits = [a for a in graded if a.verdict == "hit"]
    rate = f"{len(hits) / len(graded):.1%}" if graded else "n/a"
    lines += [
        (
            f"   {len(assessments)} reading(s) of "
            f"{len({a.task for a in assessments})} registered claim(s), "
            "one per model on the ladder"
        ),
        (
            f"   hit-rate: {len(hits)}/{len(graded)} assessed ({rate}); "
            f"{len(assessments) - len(graded)} not assessable"
        ),
        *_wrap(
            "criterion: a claim is a hit when this task's own measurement is at "
            "least its registered factor times its comparator's, for that "
            "model. Read per model because that is how a run log measures: one "
            "turns and one cost per task x model, and round 1's contrasts moved "
            "by different multiples on the two. Every logged run counts, "
            "resolved or not — a claim is about what the work cost, not about "
            "whether it worked.",
            indent="   ",
        ),
        *_wrap(
            "comparators: a pair claim is read against the one other member of "
            "this task's pair, and a baseline claim against the mean over the "
            "zero-knob baseline controls of this task's category that ran the "
            "model. The mean and not the median: at the few tasks per cell this "
            "experiment runs at, a median discards the tail the effort signal "
            "has so far lived in, and the round-1 contrasts this section makes "
            "falsifiable were themselves read off means.",
            indent="   ",
        ),
        *_wrap(
            "not assessable: a missing run on either side, a pair without a "
            "partner, a category with no swept control, or a comparator that "
            "measured zero — no multiple of zero is anything, so a claim read "
            "against it is unreadable rather than met. None of them is "
            "guessed at and none is scored — an unswept comparator is the "
            "absence of a measurement, not a claim that came out false.",
            indent="   ",
        ),
        "",
    ]

    # `against` names the other side on every row, hit and miss alike, the way
    # sections 2 and 4 name both sides of every comparison they print. Without
    # it only the misses said what "1.50x" was a multiple of, and a hit row's
    # two numbers sat beside each other unattributed.
    rows: list[Sequence[str]] = [
        ("task", "model", "claim", "against", "comparator", "observed", "ratio",
         "verdict")
    ]
    for assessment in assessments:
        metric = assessment.claim.metric
        rows.append((
            assessment.task,
            assessment.model,
            _claim_text(assessment.claim),
            assessment.against,
            _measured(assessment.comparator, metric),
            _measured(assessment.observed, metric),
            f"{assessment.ratio:.2f}x" if assessment.ratio is not None else "-",
            assessment.verdict,
        ))
    lines += _table(rows, indent="   ")

    misses = [a for a in assessments if a.verdict == "miss"]
    if misses:
        # Echoed the way a missed rung echoes its rationale: the claim is what
        # was bet, and a miss is only readable beside what it was bet against.
        lines += ["", "   misses, with the claim that was registered for them:"]
        for assessment in misses:
            metric = assessment.claim.metric
            factor = _factor_text(assessment.claim.at_least_factor)
            # A verdict is only ever reached with both sides measured and a
            # non-zero comparator, so a miss always has a ratio to print.
            assert assessment.ratio is not None
            lines += [
                f"   {assessment.task} ({assessment.model}):",
                *_wrap(
                    f"claimed {metric} at least {factor}x {assessment.against}, "
                    f"which measured {_measured(assessment.comparator, metric)}; "
                    f"it spent {_measured(assessment.observed, metric)} "
                    f"({assessment.ratio:.2f}x)",
                    indent="     ",
                ),
            ]

    if unread := [a for a in assessments if a.verdict == "not assessable"]:
        lines += ["", "   not assessable, with what was missing:"]
        for assessment in unread:
            assert assessment.reason is not None
            lines += [
                f"   {assessment.task} ({assessment.model}):",
                *_wrap(assessment.reason, indent="     "),
            ]
    return lines


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
