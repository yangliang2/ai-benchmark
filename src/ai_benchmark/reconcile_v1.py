"""reconcile-v1: what the task set predicted, read against what the sweeps did.

The knob experiment is only falsifiable if the predictions registered before a
sweep can be scored against it afterwards by something other than memory. This
module is that something: it reads the raw run logs and the task set, and
reports per-task hits and misses, how outcomes group by knob and level against
the zero-knob baseline, whether each family climbs its ladder, what each
crux/control pair cost, which knobs moved nothing in a round that asked them,
and — for the tasks that registered one — whether each effort claim came true
on each model.

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

from ai_benchmark.agents import DEFAULT_AGENT
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
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
    is_control,
    load_runs,
)
from ai_benchmark.language_runners import PYTHON

# The language a reading selects when `--language` is not given, so that
# today's Python-only logs read exactly as they always have: the registry's
# own name for the first language it admitted, rather than a string this
# module repeats.
DEFAULT_LANGUAGE = PYTHON.language

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
# section 9, as amended there for round 3 and mirrored here: a knob silent
# across this many rounds it was actually asked in is demoted. What counts as
# being asked is a registered contrast — a family or pair varying the knob, or
# an effort claim registered on a task activating it — and what counts as
# speaking is upward separation or a claim that hit. The number itself did not
# change; what a silent round is did.
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

_BASELINE_LABEL = "(control)"


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


def select_agent(runs: list[Run], agent: str, *, explicit: bool) -> list[Run]:
    """Keep only this agent's rows, before the ladder checks run.

    This is what lets a mixed log directory stop aborting: the default log
    directory can hold both harnesses' rows because a reading only ever looks
    at one of them, selected here, before `_check_ladder` ever sees the rest.
    One directory rather than one per agent, so `eval-v1 --replay` and the
    record suites keep pointing at one root, and the default — `claude-code`,
    unasked — reproduces today's output byte for byte over today's logs,
    which carry nothing else.

    `explicit` is whether `--agent` was actually given, and it is the only
    thing that can turn an empty selection into a refusal: an operator who
    named an agent no row carries made a mistake worth stopping on, but the
    unflagged default reporting over nothing is exactly what it did before
    this filter existed whenever its logs held no claude-code row, and gains
    no new abort path here.
    """
    selected = [run for run in runs if run.agent == agent]
    if explicit and not selected:
        carried = sorted({run.agent for run in runs}) or ["(no runs)"]
        raise IngestError(
            f"no run log names agent {agent!r} — --agent named it explicitly, "
            f"and the log(s) given carry {carried}"
        )
    return selected


def select_language(
    tasks: list[Task], runs: list[Run], language: str, *, explicit: bool
) -> list[Run]:
    """Keep only the rows of tasks declaring this language, before the ladder
    checks run.

    This is what lets a mixed task set stop pooling: a category's control
    mean is read off `effort`, and `effort` is built from `runs` after this
    filter, so a TypeScript control's cost never lands in a Python category's
    denominator (or the reverse) whichever language a reading selects.

    Unlike `select_agent`, this reads off the *task* a row names rather than
    the row itself — a run carries no language of its own — so a row naming a
    task outside `tasks` altogether is kept rather than dropped here: dropping
    it would silently hide the row from `evaluate`'s own refusal of a run
    naming a task that is not in the set, which is the loud failure that row
    deserves, not a quiet exclusion by a language it cannot be assigned.

    `explicit` is whether `--language` was actually given, and it is the only
    thing that can turn an empty selection into a refusal, for the reason
    `select_agent` gives for the same parameter: the unflagged default reading
    over nothing gains no new abort path.
    """
    languages_by_id = {task.id: task.language for task in tasks}
    selected = [
        run for run in runs
        if languages_by_id.get(run.task_id, language) == language
    ]
    if explicit and not any(
        languages_by_id.get(run.task_id) == language for run in runs
    ):
        carried = sorted({
            found for run in runs
            if (found := languages_by_id.get(run.task_id)) is not None
        }) or ["(no runs)"]
        raise IngestError(
            f"no run log names a task in language {language!r} — --language "
            f"named it explicitly, and the log(s) given carry {carried}"
        )
    return selected


def observed_outcomes(
    tasks: list[Task],
    runs: list[Run],
    *,
    source: str,
    timeout_s: int = GRADE_TIMEOUT_S,
    agent: str = DEFAULT_AGENT,
    agent_explicit: bool = False,
    language: str = DEFAULT_LANGUAGE,
    language_explicit: bool = False,
) -> dict[str, Outcome]:
    """Grade every logged diff and reduce each task's runs to one rung.

    Selects `agent`'s rows before anything else runs (`select_agent`), then
    `language`'s (`select_language`), so the checks below never see a second
    harness's rows or a second language's rows to refuse. Grading then goes
    through `evaluate`, which is also what makes the two failures that would
    otherwise corrupt the report loud: a run naming a task that is not in the
    set, and two runs of one task x agent x model cell, whose verdicts would
    have to be silently picked between.
    """
    runs = select_agent(runs, agent, explicit=agent_explicit)
    runs = select_language(tasks, runs, language, explicit=language_explicit)
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
    """Every task is a frozen baseline control, declares itself a control, or
    declares how it was built. The lint already refuses anything else before a
    paid run; checked again here because the alternative is reconciliation
    quietly deciding for itself which of the three an undeclared task is."""
    if problems := [problem for task in tasks for problem in construction_problems(task)]:
        raise IngestError(
            "the task set does not declare itself well enough to reconcile:\n"
            + "\n".join(f"  {problem}" for problem in problems)
        )


def _check_ladder(runs: list[Run]) -> None:
    """The report reads one agent's ladder, over the models the ladder names.

    Its multi-agent branch is unreachable through the CLI by construction:
    every reading goes through `observed_outcomes`, and `select_agent` has
    already reduced `runs` to one agent's rows before this runs. It stays as
    the last line of defence for a direct caller of this function — a future
    reader that grades a set of runs without selecting an agent first — and
    its wording is unchanged, because what it refuses is unchanged.
    """
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


def control_group(outcomes: Iterable[Outcome]) -> list[Outcome]:
    """Every outcome of a task that claims nothing about difficulty: the
    frozen zero-knob baseline, and every task declaring itself a control.

    The population every denominator here is drawn from, and never read whole:
    a control prices its own category and no other, so both readings that take
    it — the baseline effort comparator and the calibration view's cost
    baseline — filter this by the category they are pricing.
    """
    return [outcome for outcome in outcomes if is_control(outcome.task)]


def by_knob_level(outcomes: Iterable[Outcome]) -> dict[tuple[str, str], list[Outcome]]:
    """The outcomes under each (knob, level), a task appearing under every knob
    it activates."""
    groups: dict[tuple[str, str], list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        for knob, level in outcome.construction.levels.items():
            groups.setdefault((knob, level), []).append(outcome)
    return groups


def families_by_id(outcomes: Iterable[Outcome]) -> dict[str, list[Outcome]]:
    """The outcomes under each family id, unfamilied tasks left out.

    Every member is kept, for the reason `pairs_by_id` keeps every member of a
    pair: section 3 renders a family the lint would refuse and the contrast
    reading declines to score it, and both have to see it to say so.
    """
    families: dict[str, list[Outcome]] = {}
    for outcome in constructed(outcomes):
        assert outcome.construction is not None
        if outcome.construction.family is not None:
            families.setdefault(outcome.construction.family, []).append(outcome)
    return families


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


def _levels(outcome: Outcome) -> Mapping[str, str]:
    """The knob levels this task declares. Asserted rather than defaulted: a
    task with no construction block is a zero-knob baseline control, and a
    control belongs to no family, no pair and no contrast, so every caller
    here has already selected the constructed tasks."""
    assert outcome.construction is not None
    return outcome.construction.levels


def _level(outcome: Outcome, knob: str) -> str:
    """The level this task sets the knob to, or `-` where it never declares it.

    The dash is what the family and pair tables render a member built for
    other knobs as, and the task-set lint's own message for refusing that
    shape names it. The counting side does not read it as a level at all:
    `read_contrast` reports such a contrast not assessable rather than
    ordering the dash anywhere on the ladder.
    """
    return _levels(outcome).get(knob, "-")


# --- registered contrasts ------------------------------------------------------


@dataclass(frozen=True)
class Contrast:
    """A comparison the task set declares, as against one the report draws.

    A family or a pair varying exactly one knob: the two shapes an author
    builds when they mean two tasks to be read against each other. The kill
    discipline counts a knob's rounds off these and off registered effort
    claims, and off nothing else (design note section 9, as amended in round
    3) — a level read against the frozen zero-knob baseline is a comparison
    the report constructs out of tasks nobody built to be read against it,
    which is why the baseline rows print as informational.
    """

    kind: Literal["family", "pair"]
    name: str
    knob: str
    members: tuple[Outcome, ...]

    @property
    def label(self) -> str:
        return f"{self.kind} {self.name}"

    @property
    def round(self) -> Round | None:
        """The round this contrast was read in: the latest its members were
        swept in, the same rule an Outcome dates itself by. A contrast whose
        members were swept apart is read where it was completed."""
        rounds = [member.round for member in self.members if member.round is not None]
        return max(rounds, key=lambda round: round.sort_key) if rounds else None


def registered_contrasts(outcomes: Iterable[Outcome]) -> list[Contrast]:
    """Every registered contrast in the task set, families before pairs and
    each group in name order, so the report reads the same way twice."""
    families = families_by_id(outcomes)
    pairs = pairs_by_id(outcomes)
    grouped: list[tuple[Literal["family", "pair"], str, list[Outcome]]] = [
        *(("family", name, families[name]) for name in sorted(families)),
        *(("pair", name, pairs[name]) for name in sorted(pairs)),
    ]
    contrasts: list[Contrast] = []
    for kind, name, members in grouped:
        if len(members) < 2 or (knob := contrast_knob(members)) is None:
            continue
        contrasts.append(Contrast(
            kind=kind, name=name, knob=knob,
            members=tuple(sorted(members, key=lambda member: member.task.id)),
        ))
    return contrasts


def contrast_knob(members: Sequence[Outcome]) -> str | None:
    """The one knob these members vary, or None where that is not one knob.

    A knob some members declare and others do not counts as varied here, even
    though the task-set lint refuses that shape: registering the contrast is
    what lets `read_contrast` say what is wrong with it, where returning None
    would drop it off the page and print the knob as stalled — never asked —
    when a pair naming it was built and got its shape wrong. Where two knobs
    move at once the contrast attributes its outcome to neither, and where
    none moves there is nothing
    to attribute — both return None, and the round goes uncounted rather than
    being scored against a knob that sat still. Distinct from `_varied_knob`,
    which always answers, because a section that has to render a malformed
    family still has to print something.
    """
    declared = [_levels(member) for member in members]
    varied = [
        knob for knob in sorted({knob for levels in declared for knob in levels})
        if len({levels.get(knob) for levels in declared}) > 1
    ]
    return varied[0] if len(varied) == 1 else None


@dataclass(frozen=True)
class Reading:
    """What one registered contrast said, read in the harder direction only."""

    separated: bool
    assessable: bool
    text: str


def read_contrast(contrast: Contrast) -> Reading:
    """Whether this contrast's knob reached *upward*.

    Order the levels on the knob's ladder; the contrast separates when some
    harder level's highest observed rung stands strictly above some easier
    level's highest. Set difference on its own is not separation — under the
    direction-blind criterion this replaced, a level that resolved uniformly
    differed from a spread comparison and read as the knob working, which is
    how K11, commissioned to push tasks up, was credited for coming out easier
    (design note section 19). Where the ladder is not enumerated no level is
    the harder one, and the contrast is not assessable rather than scored on
    the alphabetical order `level_order` falls back to.

    A contrast whose members do not all declare the knob is not assessable
    either, and the row names the member that does not declare it. The
    task-set lint refuses that shape (`_varied_knob_problem` in
    `firstparty_v1`), so it arrives here only from an artifact replayed from
    before the lint or a set assembled by hand — and neither of the readings
    it used to get was true of it. "The ladder is not enumerated" is false
    wherever the ladder is written down, and ordering the undeclared side
    below the lowest rung separates two states that mean the same thing on
    every ladder whose bottom rung already means the knob is off, as K9's
    `none` and K8's `covered` do.

    The minimum-sample guard rides here as it does on the informational rows,
    adapted to the direction this reading runs: there it asks whether two rung
    sets could have matched, here whether the harder side had the draws to top
    the easier side's spread. It only ever withdraws a verdict — an observed
    upward separation stands whatever the sampling, and so does silence read
    off sides that were balanced enough to speak.
    """
    ladder = KNOB_LEVELS.get(contrast.knob, ())
    undeclared = sorted(
        member.task.id for member in contrast.members
        if contrast.knob not in _levels(member)
    )
    if undeclared:
        return Reading(False, False, (
            f"{contrast.label}: {', '.join(undeclared)} "
            f"{'does not' if len(undeclared) == 1 else 'do not'} declare "
            f"{contrast.knob} — a shape the task-set lint refuses, so its sides "
            "are not all rungs of one ladder and no direction can be read"
        ))
    by_level: dict[str, list[Outcome]] = {}
    for member in contrast.members:
        if member.determined:
            by_level.setdefault(_level(member, contrast.knob), []).append(member)
    if len(by_level) < 2:
        return Reading(False, False, (
            f"{contrast.label}: fewer than two of its levels have a rung"
        ))
    if any(level not in ladder for level in by_level):
        return Reading(False, False, (
            f"{contrast.label}: {contrast.knob}'s ladder is not enumerated, so "
            "neither level is the harder one and no direction can be read"
        ))
    ordered = sorted(by_level, key=lambda level: level_order(contrast.knob, level))
    comparisons = list(combinations(ordered, 2))
    for easier, harder in comparisons:
        if _top(by_level[harder]) > _top(by_level[easier]):
            return Reading(True, True, (
                f"{contrast.label}: {harder} "
                f"{_rung_set_text(by_level[harder])} above {easier} "
                f"{_rung_set_text(by_level[easier])}"
            ))
    described = ", ".join(
        f"{level} {_rung_set_text(by_level[level])}" for level in ordered
    )
    unbalanced = [
        (easier, harder) for easier, harder in comparisons
        if _outsampled(by_level[harder], by_level[easier])
    ]
    if len(unbalanced) == len(comparisons):
        return Reading(False, False, (
            f"{contrast.label}: {described} — "
            + "; ".join(
                _unbalanced_text((easier, by_level[easier]),
                                 (harder, by_level[harder]))
                for easier, harder in unbalanced
            )
        ))
    return Reading(False, True, (
        f"{contrast.label}: {described} — no level reaches above an easier one"
    ))


def _top(members: Sequence[Outcome]) -> int:
    """The highest rung these outcomes reached. Only ever called on a level
    grouped out of determined members, which is what makes the max defined."""
    return max(_HEIGHT[member.rung] for member in members)


def claim_knobs(outcome: Outcome, contrasts: Sequence[Contrast]) -> frozenset[str]:
    """The knobs this task's registered effort claim is scored to.

    A claim is attributed the way the contrast it is read in attributes it: a
    pair claim to the pair's varied knob, because that is the one knob that
    moved between the two measurements, and a baseline claim to the knob its
    task activates where that is exactly one knob, because that is then what
    the task varies from the baseline. A pair claim on a pair that varies no
    single knob is scored nowhere, for the same reason its rung delta is not
    attributed either, and a baseline claim on a task activating several knobs
    is scored nowhere for that same reason: a composite varies all of them at
    once and one reading over three knobs names none of them. Composites and
    anchors declare their activations for the calibration table's profile key
    and form no contrast on purpose; advancing a round for K1, K9 and K7
    together off one cost claim is the artifact verdict this rule removes.
    """
    construction = outcome.construction
    if construction is None or construction.prediction.effort is None:
        return frozenset()
    if construction.prediction.effort.comparator == "baseline":
        activated = construction.levels
        return frozenset(activated) if len(activated) == 1 else frozenset()
    return frozenset(
        contrast.knob for contrast in contrasts
        if contrast.kind == "pair" and contrast.name == construction.pair
    )


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
    controls = control_group(outcomes)
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
            f"no {category} zero-knob control has a {model} run"
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


def padded_table(rows: Sequence[Sequence[str]], *, indent: str) -> list[str]:
    """Header row first, columns padded to the widest cell.

    Public because the calibration view lays its tables out the same way, and
    two copies of this would let one report's columns drift out of line with
    the other's over the same corpus.
    """
    widths = [max(len(cell) for cell in column) for column in zip(*rows)]
    return [
        indent + "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in rows
    ]


def money(value: float) -> str:
    """One cost, in the one form every reading here quotes a cost in.

    Four decimal places because a run of this benchmark costs cents: rounded
    to two, most of the baseline means would print as the same number and a
    multiplier could not be checked against them from the page.
    """
    return f"${value:.4f}"


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
    # Graded once and read twice: section 5 counts these claims into its
    # verdicts and section 6 shows the working, and grading them apart would
    # let the two sections disagree about what a claim came out as.
    assessments = effort_assessments(ordered)
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
        *_flags(ordered, assessments),
        "",
        # Last, and numbered after the five sections that were here before it,
        # rather than beside section 1 where it belongs by subject. The report
        # is read by diffing one round's against the last one's, so renumbering
        # the existing sections would move every line of a report to add one
        # block. Section 5 now reads these claims as well as the rungs, so this
        # block is the working of a verdict printed above it — which is the one
        # place the numbering costs something, and cheaper than the churn.
        *_effort_claims(assessments),
    ])


def corpus_header(
    reading: str,
    outcomes: Sequence[Outcome],
    *,
    tasks_root: Path,
    logs: Sequence[Path],
) -> list[str]:
    """What a reading of this corpus is, what it read, and how much there was.

    Public because the calibration view opens on the same four lines over the
    same two inputs: one implementation, because two would let one report
    count a task set or name a log differently from the other while both
    claimed to have read the same artifacts.
    """
    swept = [outcome for outcome in outcomes if outcome.swept]
    runs = sum(len(outcome.resolved) for outcome in outcomes)
    lines = [
        f"{reading}: {BENCHMARK}",
        (
            f"  task set   {tasks_root} — {len(outcomes)} task(s): "
            f"{len(control_group(outcomes))} control(s), "
            f"{len(constructed(outcomes))} constructed"
        ),
    ]
    lines += [
        f"  {'run logs' if index == 0 else '':<10} {log}"
        for index, log in enumerate(logs)
    ] or ["  run logs   (none)"]
    return [*lines, f"  runs       {runs} over {len(swept)} task(s)"]


# The ladder every reading here is scoped to, and the provenance boundary
# every one of them was taken under. Said once, for the two reports that owe
# it to a reader: a disclaimer copied into a second report is a disclaimer
# that can go on describing a discipline only the first one still keeps.
PROVENANCE: tuple[str, ...] = (
    "  ladder     "
    + "; ".join(f"{model} -> {rung}" for model, rung in LADDER)
    + "; neither -> unsolved",
    "  verdicts   replayed: every logged diff re-graded by its task's held-out",
    "             tests, the computation eval-v1 --replay does. No agent, no LLM,",
    "             no network; the run logs are read and never added to, and no",
    "             record is merged into the dataset.",
)


def _header(
    outcomes: Sequence[Outcome], *, tasks_root: Path, logs: Sequence[Path]
) -> list[str]:
    rounds = sorted(
        {
            outcome.round
            for outcome in outcomes
            if outcome.swept and outcome.round is not None
        },
        key=lambda round: round.sort_key,
    )
    return [
        *corpus_header("reconciliation", outcomes, tasks_root=tasks_root, logs=logs),
        # Rounds are counted off the tasks, not off the log files: a task's
        # round is the latest of the rounds its runs belong to, so one log can
        # carry more than one round and one round more than one log.
        f"  rounds     {len(rounds)} round(s)"
        + (f": {', '.join(round.label for round in rounds)}" if rounds else ""),
        f"             {_keying(rounds)}",
        *wrap(_ROUND_KEYING_NOTE, indent="             "),
        *PROVENANCE,
    ]


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
    lines += ["", *padded_table(rows, indent="   ")]

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
                *wrap(prediction.rationale, indent="     "),
            ]
    return lines


def wrap(text: str, *, indent: str = "", width: int = 74) -> list[str]:
    """One paragraph of prose, wrapped and indented. Public for the same
    reason `padded_table` is: the calibration view wraps its own prose, and a
    second copy of this would be a second answer to how a report is shaped."""
    return textwrap.wrap(
        " ".join(text.split()), width=width,
        initial_indent=indent, subsequent_indent=indent,
    )


def _knob_grouping(outcomes: Sequence[Outcome]) -> list[str]:
    groups = by_knob_level(outcomes)
    lines = ["2. knob grouping, against the zero-knob controls of the same category"]
    if not groups:
        return [*lines, "   (no constructed task in the task set)"]

    controls = control_group(outcomes)
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
        lines += ["", f"   {knob}", *padded_table(rows, indent="     ")]
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
    families = families_by_id(outcomes)
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
            *padded_table(rows, indent="     "),
            f"     monotonic along the ladder: {_monotonic(ordered)}",
        ]
    return lines


def _varied_knob(members: Sequence[Outcome]) -> str:
    """The knob a family varies: the one its members do not all set alike.

    A knob one member declares and another does not is varied too, read the
    way `contrast_knob` reads it, so this section and the counting one name
    the same knob for the same pair — the counting one then refuses to read a
    direction off it, but which knob the pair is about does not change. The
    lint holds a family to exactly one such knob; a family that somehow has
    none (identical levels throughout) falls back to its lowest-numbered knob
    so the block still renders rather than the whole report failing.
    """
    activated = sorted(
        {knob for member in members for knob in _levels(member)}, key=knob_order
    )
    varied = [
        knob for knob in activated
        if len({_level(member, knob) for member in members}) > 1
    ]
    return (varied or activated)[0]


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
        lines += ["", *padded_table(ranked, indent="   ")]
    if len(unranked) > 1:
        lines += [
            "",
            *wrap(
                "pairs varying a knob whose ladder the design note has not "
                "enumerated: its levels carry no difficulty order, so neither "
                "member is named the crux and no rung delta is claimed.",
                indent="   ",
            ),
            "",
            *padded_table(unranked, indent="   "),
        ]
    return lines


@dataclass(frozen=True)
class Verdict:
    """What one round said about one knob, and whether it counted as silence."""

    round: Round
    silent: bool
    summary: str
    detail: tuple[str, ...]


def _flags(
    outcomes: Sequence[Outcome], assessments: Sequence[Assessment]
) -> list[str]:
    lines = [
        "5. no-separation flags",
        *wrap(
            "criterion: a round counts for a knob only where it put the knob to a "
            "registered contrast — a task family or pair swept in that round whose "
            "varied knob this is, or an effort claim registered on a task "
            "activating it and scored to it. Those are the comparisons the task "
            "set declares. A knob's levels read against each other within a round, "
            "or against the frozen zero-knob baseline where the round swept only "
            "one of them, are comparisons this report draws instead; they are "
            "printed below as informational and advance nothing.",
            indent="   ",
        ),
        *wrap(
            "direction: a contrast separates only upward. Its levels are ordered "
            "on the knob's ladder, and it separates when some harder level's "
            "highest observed rung stands strictly above some easier level's "
            "highest. A set difference on its own is not separation: a level that "
            "resolves uniformly differs from a spread comparison, and reading that "
            "as the knob working credits an anti-saturation knob for coming out "
            "easier. Where the knob's ladder is not enumerated, no level is the "
            "harder one and the contrast is not assessable. So is a contrast whose "
            "members do not all declare the knob: the task-set lint refuses that "
            "shape, and where a replayed artifact carries one anyway the "
            "undeclared side has no rung to be ordered against, so the row names "
            "the member that does not declare it and reads no direction.",
            indent="   ",
        ),
        *wrap(
            "sample: the minimum-sample guard applies to a contrast too, turned in "
            "this reading's direction. A side of n graded tasks lands on at most n "
            "distinct rungs, so a harder side holding fewer graded tasks than the "
            "easier side has rungs is read against the maximum of more draws than "
            "it took itself; its silence would be the sample as much as the knob, "
            "and where every comparison a contrast could draw is unbalanced that "
            "way the contrast is not assessable. The guard only ever withdraws a "
            "verdict — an observed separation stands whatever the sampling, and so "
            "does silence read off balanced sides.",
            indent="   ",
        ),
        *wrap(
            "effort: a counted round is non-silent when a registered contrast "
            "separated upward or when any effort claim scored to the knob hit on "
            "any model — a pair claim scoring to the pair's varied knob, a "
            "baseline claim to the one knob its task activates where that is "
            "exactly one, and to no knob where the task activates several, since "
            "one reading over several knobs names none of them. Effort is the axis "
            "this experiment's signal has actually shown up on, and a knob judged "
            "only on rungs is judged on an outcome its author never bet on.",
            indent="   ",
        ),
        *wrap(
            "not assessable: silence needs a reading that could have spoken. A "
            "round whose contrasts are all unreadable and whose claim readings are "
            "all not assessable says nothing about the knob rather than saying the "
            "knob moved nothing, so it prints not assessable and advances nothing. "
            "Every tally below counts assessable readings, naming the unreadable "
            "ones separately, so a row never renders an unreadable claim as an "
            "assessed miss.",
            indent="   ",
        ),
        *wrap(
            "informational rows: the widest reading of where a level landed, and "
            "the only reading a knob with no contrast has. They carry the older "
            "direction-blind set comparison and its minimum-sample guard — a side "
            "of n graded tasks lands on at most n distinct rungs, so a side "
            "holding fewer graded tasks than the other side has rungs could not "
            "have matched it however the runs came out, and is reported not "
            "assessable naming the counts. That guard and the counting one above "
            "answer different questions off the same data, so they can disagree "
            "on it: this one asks whether two rung sets could have matched, the "
            "counting one whether an upward separation was observed. One task at "
            "the easier level against three at the harder one prints as separated "
            "up there and not assessable here, and both readings are right about "
            "the question they were asked. No row under this label moves a "
            "counter.",
            indent="   ",
        ),
        *wrap(
            f"kill discipline: a knob silent for {SILENT_ROUNDS_TO_DEMOTE} round(s) "
            "is demoted (docs/design/task-difficulty-and-ex-ante-profiles.md "
            "section 9). A knob with no counted round is stalled rather than "
            "silent: it has not been shown to move nothing, it has never been "
            "asked, and demoting it would be reading a verdict off evidence "
            "nobody collected. A round is one sweep, named below by the sweep id "
            "its runs carried — or, for runs logged before that field existed, by "
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
    contrasts = registered_contrasts(outcomes)
    scored = {
        outcome.task.id: claim_knobs(outcome, contrasts) for outcome in outcomes
    }
    for knob in sorted({knob for knob, _ in groups}, key=knob_order):
        verdicts = [
            verdict for round in rounds
            if (verdict := _counted(knob, round, outcomes, contrasts, assessments, scored))
            is not None
        ]
        silent = [verdict.round for verdict in verdicts if verdict.silent]
        block: list[str] = []
        for verdict in verdicts:
            block.append(f"   {knob}  {verdict.round.label}  {verdict.summary}")
            block += [f"          {line}" for line in verdict.detail]
        if not block:
            block = [(
                f"   {knob}  (no registered contrast: no family or pair varies it, "
                "and no task activating it registers an effort claim)"
            )]
        tail = [f"       silent round(s): {len(silent)}"]
        if not verdicts:
            tail = [(
                f"       silent round(s): 0 — stalled: no round put {knob} to a "
                "registered contrast, so the counter cannot advance"
            )]
        elif len(silent) >= SILENT_ROUNDS_TO_DEMOTE:
            # Naming them is the point: a demotion travels out of this report
            # into the design note and the tickets that follow it, and one
            # that does not say which rounds it counted cannot be checked
            # against the sweeps it was read off.
            counted = ", ".join(round.dated_label for round in silent)
            tail = [(
                f"       silent round(s): {len(silent)} — demote {knob}: silent in "
                f"{counted} — {len(silent)} round(s) against the "
                f"{SILENT_ROUNDS_TO_DEMOTE} the kill discipline allows"
            )]
        informational = [
            f"          {round.label}  {_separation(knob, outcomes, round)}"
            for round in rounds
            if _activated_in(knob, outcomes, round)
        ]
        if informational:
            tail += ["       informational, advancing no counter:", *informational]
        lines += ["", *block, *tail]
    return lines


def _counted(
    knob: str,
    round: Round,
    outcomes: Sequence[Outcome],
    contrasts: Sequence[Contrast],
    assessments: Sequence[Assessment],
    scored: Mapping[str, frozenset[str]],
) -> Verdict | None:
    """What this round said about this knob, or None if it did not ask.

    A round asks when it holds a registered contrast of the knob: a family or
    pair varying it, or a task activating it that registered an effort claim.
    A round that holds neither gets no row at all — a printed verdict there
    would read as a round the knob was tried in, and the kill discipline would
    then have to explain it away.
    """
    readings = [
        read_contrast(contrast) for contrast in contrasts
        if contrast.knob == knob and contrast.round == round
    ]
    claims = [
        assessment for assessment in assessments
        if knob in scored.get(assessment.task, frozenset())
        and _swept_in(assessment.task, outcomes, round)
    ]
    if not readings and not claims:
        return None

    hits = [assessment for assessment in claims if assessment.verdict == "hit"]
    readable = [
        assessment for assessment in claims if assessment.verdict != "not assessable"
    ]
    assessable = [reading for reading in readings if reading.assessable]
    separated = [reading for reading in readings if reading.separated]
    contrast_tally = _contrast_tally(separated, assessable, readings)
    claim_tally = _claim_tally(hits, readable, claims)
    tally = f"{contrast_tally}; {claim_tally}"
    if separated:
        # The reading that spoke is named in the summary, so the detail lines
        # below carry the ones it does not: printing it in both places made the
        # row argue the same comparison with itself.
        detail = tuple(
            reading.text for reading in readings if reading is not separated[0]
        )
        return Verdict(round, False, f"separated — {separated[0].text} ({tally})", detail)
    detail = tuple(reading.text for reading in readings)
    if hits:
        # The claim half leads, the way the separated row leads with the
        # contrast that spoke: what made the round non-silent is the first
        # thing on it, and the tally beside it says the other half stayed
        # quiet without a second sentence saying so.
        return Verdict(
            round, False, f"non-silent — {claim_tally} ({contrast_tally})", detail
        )
    if not assessable and not readable:
        # Nothing here could have spoken: every contrast unreadable and every
        # claim reading unassessable. The round said nothing rather than saying
        # the knob moved nothing, and an unreadable comparison has never been
        # allowed to count as silence.
        return Verdict(round, False, f"not assessable — {tally}", detail)
    # Both halves of the silence are spelled out, because a knob is demoted off
    # this row and "no separation" alone does not say which axis stayed quiet.
    return Verdict(round, True, f"no separation — {tally}", detail)


def _claim_tally(
    hits: Sequence[Assessment],
    readable: Sequence[Assessment],
    claims: Sequence[Assessment],
) -> str:
    """The effort half of a knob's round, in the one form the section uses.

    Always "M of N hit", never a bare count: a row that printed how many
    readings there were and not how many landed made the reader open section 6
    to find out what its own verdict was read off. The denominator is the
    readings that could be assessed, and the ones that could not are named
    beside it rather than folded in, because a claim read against an unswept
    comparator is not a bet that came out false.
    """
    if not claims:
        return "no effort claim registered"
    if not readable:
        return f"none of {len(claims)} registered effort reading(s) assessable"
    unreadable = len(claims) - len(readable)
    tally = f"{len(hits)} of {len(readable)} registered effort reading(s) hit"
    return f"{tally} ({unreadable} not assessable)" if unreadable else tally


def _contrast_tally(
    separated: Sequence[Reading],
    assessable: Sequence[Reading],
    readings: Sequence[Reading],
) -> str:
    """The contrast half of a knob's round, in the form the effort half uses.

    "M of N separated", never a bare count of how many contrasts existed: one
    parenthetical printing "3 registered contrast(s)" beside "1 of 2
    registered effort reading(s) hit" left its two halves counting different
    things, and the reader to work out which. As there, the denominator is the
    readings that could be assessed and the ones that could not are named
    beside it rather than folded in, because a contrast nothing could be read
    off is not a contrast that came out flat.
    """
    if not readings:
        return "no registered contrast"
    if not assessable:
        return f"none of {len(readings)} registered contrast(s) readable"
    unreadable = len(readings) - len(assessable)
    tally = f"{len(separated)} of {len(assessable)} registered contrast(s) separated"
    return f"{tally} ({unreadable} not assessable)" if unreadable else tally


def _swept_in(task_id: str, outcomes: Sequence[Outcome], round: Round) -> bool:
    return any(
        outcome.task.id == task_id and outcome.round == round for outcome in outcomes
    )


def _activated_in(knob: str, outcomes: Sequence[Outcome], round: Round) -> bool:
    """Whether any task activating this knob was swept in this round, which is
    what earns the round an informational row.

    A round that swept none of them has nothing to say about the knob at all,
    so it gets no row on either side of the block: a printed "not assessable"
    would read as a round the knob was tried in.
    """
    return any(
        outcome.round == round
        and outcome.construction is not None
        and knob in outcome.construction.levels
        for outcome in outcomes
    )


def _separation(knob: str, outcomes: Sequence[Outcome], round: Round) -> str:
    """Whether this knob's levels landed on different sets of rungs in this
    round — the informational reading, which advances no counter.

    The direction-blind set comparison the kill discipline used to be read
    off, kept because it is the widest view of where a level landed and the
    only view a knob with no registered contrast has. What it may no longer do
    is count: two of the three flags it fired in round 2 said more about the
    samples than about the knob (design note sections 19 and 22).

    The levels are read within the round; the zero-knob controls are read
    across every round. A cell is only ever swept once, so the baseline cannot
    be re-swept alongside a later round's tasks — scoping the controls to the
    round too would leave every single-level knob permanently unreadable
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
            control for control in control_group(outcomes)
            if control.task.category in categories and control.determined
        ]
        if not controls:
            return (
                f"not assessable — one level swept ({described}) and no zero-knob "
                f"control of the same category ({', '.join(sorted(categories))}) "
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

    The question is symmetric here, which is the whole of the difference from
    `_outsampled`: a set comparison is withdrawn whichever side was the small
    one, where the contrast reading only ever asks it of the harder side.
    """
    return _outsampled(one, other) or _outsampled(other, one)


def _graded(outcomes: Sequence[Outcome]) -> list[Outcome]:
    """The outcomes a set comparison is built from: the ones with a rung."""
    return [outcome for outcome in outcomes if outcome.determined]


def _outsampled(harder: Sequence[Outcome], easier: Sequence[Outcome]) -> bool:
    """Whether this comparison's harder side was too small to be read against
    the easier one — the minimum-sample guard, turned in the direction the
    contrast reading runs.

    A side of n graded tasks lands on at most n distinct rungs, so a harder
    side holding fewer graded tasks than the easier side has rungs is being
    read against the maximum of more draws than it took itself. That does not
    make its silence impossible — one task landing unsolved would still stand
    above anything — but it makes the silence an unbalanced sample as much as
    a quiet knob, which is not evidence a demotion may be argued from.
    """
    return len(_graded(harder)) < len(rung_set(easier))


def _sample_text(short: Side, against: Side, consequence: str) -> str:
    """The guard's arithmetic, said once for both readings that carry it: how
    many tasks the short side graded against how many rungs the other side
    spread over. Only the consequence differs between them, because only the
    question does."""
    return (
        f"{short[0]} has {len(_graded(short[1]))} graded task(s) against "
        f"{against[0]}'s {len(rung_set(against[1]))} distinct rung(s), "
        f"{consequence}"
    )


def _unbalanced_text(easier: Side, harder: Side) -> str:
    return _sample_text(
        harder, easier, "so its silence would be the sample as much as the knob"
    )


def _forced_text(one: Side, other: Side) -> str:
    small, large = sorted(
        (one, other), key=lambda side: (len(_graded(side[1])), side[0])
    )
    return _sample_text(
        small, large, "so the two sets could not have matched however the runs came out"
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
        return money(value)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _effort_claims(assessments: Sequence[Assessment]) -> list[str]:
    lines = ["6. effort-claim reconciliation"]
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
        *wrap(
            "criterion: a claim is a hit when this task's own measurement is at "
            "least its registered factor times its comparator's, for that "
            "model. Read per model because that is how a run log measures: one "
            "turns and one cost per task x model, and round 1's contrasts moved "
            "by different multiples on the two. Every logged run counts, "
            "resolved or not — a claim is about what the work cost, not about "
            "whether it worked.",
            indent="   ",
        ),
        *wrap(
            "comparators: a pair claim is read against the one other member of "
            "this task's pair, and a baseline claim against the mean over the "
            "zero-knob baseline controls of this task's category that ran the "
            "model. The mean and not the median: at the few tasks per cell this "
            "experiment runs at, a median discards the tail the effort signal "
            "has so far lived in, and the round-1 contrasts this section makes "
            "falsifiable were themselves read off means.",
            indent="   ",
        ),
        *wrap(
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
    lines += padded_table(rows, indent="   ")

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
                *wrap(
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
                *wrap(assessment.reason, indent="     "),
            ]
    return lines


# --- the command ---------------------------------------------------------------


def reconcile(
    tasks: list[Task],
    tasks_root: Path,
    logs: Sequence[Path],
    *,
    timeout_s: int = GRADE_TIMEOUT_S,
    agent: str = DEFAULT_AGENT,
    agent_explicit: bool = False,
    language: str = DEFAULT_LANGUAGE,
    language_explicit: bool = False,
) -> str:
    runs = [run for log in logs for run in load_runs(log)]
    outcomes = observed_outcomes(
        tasks,
        runs,
        source=", ".join(str(log) for log in logs) or "(no run log)",
        timeout_s=timeout_s,
        agent=agent,
        agent_explicit=agent_explicit,
        language=language,
        language_explicit=language_explicit,
    )
    return render(outcomes, tasks_root=tasks_root, logs=logs)
