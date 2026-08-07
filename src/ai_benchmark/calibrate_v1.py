"""calibrate-v1: the swept corpus read as a calibration table.

The actuarial loop the project is built around has two halves: a profile a
ticket can be given in thirty seconds without running anything, and a table
that says what tasks of that profile have cost and how far up the difficulty
ladder they landed. Reconciliation answers what the knob experiment learned;
this answers the question a selection query would actually ask — *what does
this shape of work cost, and who could do it* — and it is the first artifact
of the project the selection tool can consume.

**What a row is.** One capability-matrix category crossed with one
knob-activation profile: the set of knobs a task declares and the levels it
sets them to, sorted by knob number so that two tasks activating the same
knobs are one cell however their task.yaml happened to order them. The tasks
carrying no construction block at all are the zero-knob profile, and that row
is the denominator every other row in its category is divided by.

**What a cell says.** Per model on the ladder, a cost multiplier: the mean
cost of this cell's tasks that ran the model, over the mean cost of the same
category's zero-knob controls that ran it. Every logged run counts, resolved
or not — a run that failed still spent its dollars, and the cells a selection
tool most needs priced are the ones models fail in. Beside them, the cell's
rung floor: the weakest rung any graded task in it landed on. And on every
one of those, its own n, because a multiplier over two tasks and a multiplier
over eleven are not the same claim and a table that printed them alike would
say so.

**What v1 refuses.** It fills no cell it did not measure. No interpolation
between a knob's levels, no backoff to a coarser key when a cell is thin, no
pooling of one category's controls into another's denominator (ADR-0001's
grouping rule, which is why the report is a table per category rather than
one table with a category column). An unmeasured cell prints empty and is
listed at the end with what was missing. Backoff is a real requirement of the
actuarial design — it is how a sparse table still answers — but it has to
arrive declaring the reduced confidence it was answered at, and a v1 that
quietly filled cells would publish numbers no sweep produced.

**What the whole table is scoped to.** One benchmark and one agent. The
ladder check this module inherits refuses a run log carrying a model the
operational ladder does not name, and refuses two harnesses in one reading,
for the reason ADR-0001 groups at all: numbers produced differently never pool
into one rate, and a multiplier meant over two harnesses would price one
harness's spending into the other's profile.

**Where the numbers come from.** The same provenance boundary reconcile-v1
reads under, by sharing its code path: the raw run logs and the task set are
read and never written, the costs come off the log rows, and the rungs come
from replaying each logged diff against its task's held-out grading tests —
no agent, no LLM, no network, no record merged. Every number here is
recomputable from checked-in artifacts by this one command.
"""

import textwrap
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from ai_benchmark.firstparty_v1 import (
    BENCHMARK,
    GRADE_TIMEOUT_S,
    Task,
    load_runs,
)
from ai_benchmark.reconcile_v1 import (
    LADDER,
    LADDER_MODELS,
    RUNGS,
    Observed,
    Outcome,
    baseline,
    knob_order,
    level_order,
    observed_outcomes,
)

# The profile of a task that declares no knob at all. Spelled rather than left
# blank: an empty profile cell would read as a row whose key went missing,
# where this row is the one every other row in its category is read against.
ZERO_KNOB = "(zero-knob)"

# What an unmeasured cell prints. A dash and not whitespace, so that a cell the
# corpus never reached is visibly a cell rather than a column that failed to
# render — the refusal is a result, and it is meant to be seen.
EMPTY = "-"

_FLOOR_COLUMN = "rung floor"


@dataclass(frozen=True)
class Cell:
    """One row: a category crossed with a knob-activation profile.

    Members are every task of the set with this key, swept or not. A profile
    the corpus holds but no sweep reached keeps its row and prints nothing in
    it, because the honest thing to say about it is that it exists and has no
    number — not that it is absent.
    """

    category: str
    profile: tuple[tuple[str, str], ...]
    members: tuple[Outcome, ...]

    @property
    def label(self) -> str:
        return ",".join(f"{knob}={level}" for knob, level in self.profile) or ZERO_KNOB

    @property
    def name(self) -> str:
        """How the cell is named away from its own table."""
        return f"{self.category} {self.label}"

    @property
    def sort_key(self) -> tuple[str, int, tuple[tuple[int, tuple[int, str]], ...]]:
        """Zero-knob first, then the single-knob profiles in knob and ladder
        order, then the composites. A reader comparing a level against the
        baseline reads down one column, and a composite sorts below the knobs
        it is composed of rather than between them."""
        return (
            self.category,
            len(self.profile),
            tuple(
                (knob_order(knob), level_order(knob, level))
                for knob, level in self.profile
            ),
        )


def profile(outcome: Outcome) -> tuple[tuple[str, str], ...]:
    """The knob activations this task declares, sorted by knob number.

    A profile is a set of activations, so the sort is what makes the key: two
    tasks setting K1 and K12 to the same levels belong in one cell whichever
    order their construction blocks listed them in, and a key that kept the
    authoring order would split one cell into two and halve both n's.
    """
    construction = outcome.task.construction
    levels: Mapping[str, str] = {} if construction is None else construction.levels
    return tuple(sorted(levels.items(), key=lambda item: knob_order(item[0])))


def cells(outcomes: Iterable[Outcome]) -> list[Cell]:
    """Every cell the task set holds, in the order the table prints them."""
    grouped: dict[tuple[str, tuple[tuple[str, str], ...]], list[Outcome]] = {}
    for outcome in outcomes:
        grouped.setdefault((outcome.task.category, profile(outcome)), []).append(outcome)
    return sorted(
        (
            Cell(
                category=category,
                profile=key,
                members=tuple(sorted(members, key=lambda member: member.task.id)),
            )
            for (category, key), members in grouped.items()
        ),
        key=lambda cell: cell.sort_key,
    )


# --- the readings ---------------------------------------------------------------


@dataclass(frozen=True)
class Denominator:
    """What one category's zero-knob controls cost on one model.

    The mean, not the median, for the reason reconciliation reads its baseline
    effort comparator as a mean: at the handful of tasks per cell this
    experiment runs at, a median discards the tail the effort signal has so
    far lived in, and two views of one corpus quoting differently-centred
    baselines would disagree about what a task cost relative to its controls.
    """

    mean: float | None
    n: int
    # Why there is no mean, when there is none.
    reason: str | None

    @property
    def text(self) -> str:
        return EMPTY if self.mean is None else f"{_money(self.mean)} (n={self.n})"


def denominator(controls: Sequence[Outcome], category: str, model: str) -> Denominator:
    """The cost this category's multipliers are divided by, on this model.

    Same category only. Pooling another category's controls in would be the
    one shortcut that fills an unpriced cell, and it would answer a question
    nobody asked: ADR-0001 groups so that rows produced differently never pool
    into one rate, and a refactor control is not a feature-dev control.
    """
    ran = [
        control for control in controls
        if control.task.category == category and model in control.effort
    ]
    if not ran:
        return Denominator(None, 0, (
            f"{category} has no zero-knob baseline control with a {model} run"
        ))
    mean = sum(control.effort[model].cost_usd for control in ran) / len(ran)
    if not mean:
        # No multiple of zero is anything, so a ratio read against it is
        # unreadable rather than infinite — the reading reconciliation gives
        # an effort claim whose comparator measured zero.
        return Denominator(None, len(ran), (
            f"the {category} zero-knob baseline measured {_money(mean)} on {model} "
            f"over {len(ran)} control(s), and no multiple of zero is anything"
        ))
    return Denominator(mean, len(ran), None)


def denominators(outcomes: Sequence[Outcome]) -> dict[tuple[str, str], Denominator]:
    """One denominator per category per model, over the zero-knob controls."""
    controls = baseline(outcomes)
    return {
        (category, model): denominator(controls, category, model)
        for category in sorted({outcome.task.category for outcome in outcomes})
        for model in LADDER_MODELS
    }


@dataclass(frozen=True)
class Multiplier:
    """What this cell's tasks cost on one model, against their baseline."""

    value: float | None
    # The tasks the numerator was meant over, which is what the cell's n
    # counts: a cell of four tasks two of which ran the model is priced off
    # two, and printing the cell's population there would overstate it.
    n: int
    reason: str | None

    @property
    def text(self) -> str:
        return EMPTY if self.value is None else f"{self.value:.2f}x (n={self.n})"


def multiplier(cell: Cell, model: str, against: Denominator) -> Multiplier:
    """This cell's mean cost over its category's baseline mean, on one model.

    Every logged run of a member counts, resolved or not: a multiplier is a
    claim about what the work cost, not about whether it worked, and pricing a
    cell off its resolved runs alone would quote the cheapest reading of the
    cells that most need pricing.
    """
    ran = [member for member in cell.members if model in member.effort]
    if not ran:
        return Multiplier(None, 0, f"no task in the cell has a {model} run")
    mean = sum(member.effort[model].cost_usd for member in ran) / len(ran)
    if against.mean is None:
        assert against.reason is not None
        return Multiplier(None, len(ran), (
            f"{against.reason}, so this cell's mean of {len(ran)} task(s) "
            f"({_money(mean)}) has nothing to divide by"
        ))
    return Multiplier(mean / against.mean, len(ran), None)


@dataclass(frozen=True)
class Floor:
    """The weakest rung any graded task in a cell landed on.

    The weakest and not the strongest, and not an average of them: a profile
    one task of which the weakest model solved has been solved that cheaply at
    least once, which is the claim a selection query can act on. An averaged
    cell would quote a difficulty no task in it was ever measured at.
    """

    rung: Observed | None
    # The tasks with a rung, which is fewer than the cell holds wherever a
    # member is unswept or its runs cannot decide between two rungs.
    n: int
    reason: str | None

    @property
    def text(self) -> str:
        return EMPTY if self.rung is None else f"{self.rung} (n={self.n})"


def rung_floor(cell: Cell) -> Floor:
    graded = [member for member in cell.members if member.determined]
    if not graded:
        states = Counter(member.rung for member in cell.members)
        return Floor(None, 0, (
            "no task in the cell has a rung: "
            + ", ".join(f"{states[state]} {state}" for state in sorted(states))
        ))
    weakest = min(graded, key=lambda member: RUNGS.index(member.rung))
    return Floor(weakest.rung, len(graded), None)


@dataclass(frozen=True)
class Row:
    """One rendered row, and everything it could not print."""

    cell: Cell
    multipliers: tuple[Multiplier, ...]
    floor: Floor

    @property
    def columns(self) -> tuple[str, ...]:
        return (
            self.cell.label,
            str(len(self.cell.members)),
            *(multiplier.text for multiplier in self.multipliers),
            self.floor.text,
        )

    @property
    def missing(self) -> list[tuple[str, str]]:
        """What each empty cell of this row was missing, column by column."""
        readings: list[tuple[str, str | None]] = [
            *zip(LADDER_MODELS, [reading.reason for reading in self.multipliers]),
            (_FLOOR_COLUMN, self.floor.reason),
        ]
        return [(column, reason) for column, reason in readings if reason is not None]


def read(
    table: Sequence[Cell], against: Mapping[tuple[str, str], Denominator]
) -> list[Row]:
    """Every cell read into the numbers its row prints."""
    return [
        Row(
            cell=cell,
            multipliers=tuple(
                multiplier(cell, model, against[(cell.category, model)])
                for model in LADDER_MODELS
            ),
            floor=rung_floor(cell),
        )
        for cell in table
    ]


# --- rendering -------------------------------------------------------------------


def _money(value: float) -> str:
    return f"${value:.4f}"


def _table(rendered: Sequence[Sequence[str]], *, indent: str) -> list[str]:
    """Header row first, columns padded to the widest cell."""
    widths = [max(len(cell) for cell in column) for column in zip(*rendered)]
    return [
        indent + "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in rendered
    ]


def _wrap(text: str, *, indent: str = "", width: int = 78) -> list[str]:
    return textwrap.wrap(
        " ".join(text.split()), width=width,
        initial_indent=indent, subsequent_indent=indent,
    )


# Where a header line's value starts: two spaces, an eleven-column label, and
# then the value, so a wrapped paragraph lines up under the one above it.
_VALUE = " " * 13


def _labelled(label: str, text: str) -> list[str]:
    """One header paragraph: its label, then the text wrapped under itself."""
    wrapped = _wrap(text, width=78 - len(_VALUE))
    return [
        f"  {label:<11}{wrapped[0]}",
        *(f"{_VALUE}{line}" for line in wrapped[1:]),
    ]


# The refusals, said once for the two places that owe them to a reader: the
# report itself and the command's help page. They are the v1 contract with
# whatever reads the table — a consumer that assumed a filled cell where the
# corpus has none would be reading a number no sweep produced.
REFUSALS = (
    "v1 prints no number it did not measure: no interpolation between a "
    "knob's levels, no backoff to a coarser key where a cell is thin, and no "
    "pooling of one category's controls into another category's denominator "
    "— which is why this is a table per category and not one table with a "
    "category column (ADR-0001's grouping rule). A cell nothing measured "
    f"prints {EMPTY!r} and is listed at the end with what was missing."
)

_READINGS = (
    "cost multiplier, per model: the mean cost of this cell's tasks that ran "
    "the model, over the mean cost of the same category's zero-knob baseline "
    "controls that ran it. Every logged run counts, resolved or not — a run "
    "that failed still spent its dollars — and n is the tasks the numerator "
    "was meant over. The zero-knob row is the denominator, so it reads 1.00x "
    "by construction and carries the n every multiplier in its table was "
    "divided by."
)

_FLOORS = (
    "rung floor: the weakest rung any graded task in the cell landed on, and "
    "the number of tasks that had one. A task no log mentions, and one whose "
    "runs cannot decide between two rungs, are not rungs and are left out of "
    "that n rather than read as the weakest."
)


def render(
    outcomes: Mapping[str, Outcome], *, tasks_root: Path, logs: Sequence[Path]
) -> str:
    ordered = [outcomes[task_id] for task_id in sorted(outcomes)]
    table = cells(ordered)
    against = denominators(ordered)
    read_rows = read(table, against)
    by_category: dict[str, list[Row]] = {}
    for row in read_rows:
        by_category.setdefault(row.cell.category, []).append(row)
    return "\n".join(chain(
        _header(ordered, table, tasks_root=tasks_root, logs=logs),
        *(
            ["", *_category(category, by_category[category], against)]
            for category in by_category
        ),
        ["", *_missing(read_rows)],
    ))


def _header(
    outcomes: Sequence[Outcome],
    table: Sequence[Cell],
    *,
    tasks_root: Path,
    logs: Sequence[Path],
) -> list[str]:
    controls = baseline(outcomes)
    swept = [outcome for outcome in outcomes if outcome.swept]
    runs = sum(len(outcome.resolved) for outcome in outcomes)
    categories = {cell.category for cell in table}
    ladder = "; ".join(f"{model} -> {rung}" for model, rung in LADDER)
    lines = [
        f"calibration: {BENCHMARK}",
        (
            f"  task set   {tasks_root} — {len(outcomes)} task(s): "
            f"{len(controls)} zero-knob baseline, "
            f"{len(outcomes) - len(controls)} constructed"
        ),
    ]
    lines += [
        f"  {'run logs' if index == 0 else '':<10} {log}"
        for index, log in enumerate(logs)
    ] or ["  run logs   (none)"]
    lines += [
        f"  runs       {runs} over {len(swept)} task(s)",
        (
            f"  cells      {len(table)} cell(s) over {len(categories)} category(ies), "
            "keyed category x sorted knob-activation profile"
        ),
        f"  ladder     {ladder}; neither -> unsolved",
        "  verdicts   replayed: every logged diff re-graded by its task's held-out",
        "             tests, the computation eval-v1 --replay does. No agent, no LLM,",
        "             no network; the run logs are read and never added to, and no",
        "             record is merged into the dataset.",
        *_labelled("reads", _READINGS),
        *_labelled("", _FLOORS),
        *_labelled("refuses", REFUSALS),
    ]
    return lines


def _category(
    category: str,
    category_rows: Sequence[Row],
    against: Mapping[tuple[str, str], Denominator],
) -> list[str]:
    """One category's table, under the denominator its multipliers were
    divided by.

    A table per category rather than one table with a category column, because
    the denominator is per category: printing it once above the rows it
    divides is what makes the arithmetic checkable from the page, and what
    makes a pooled denominator impossible to write without it being visible.
    """
    header = ("profile", "tasks", *LADDER_MODELS, _FLOOR_COLUMN)
    means = ", ".join(
        f"{model} {against[(category, model)].text}" for model in LADDER_MODELS
    )
    return [
        f"category {category}",
        f"   baseline mean cost   {means}",
        "",
        *_table([header, *(row.columns for row in category_rows)], indent="   "),
    ]


def _missing(read_rows: Sequence[Row]) -> list[str]:
    """Every empty cell, with what was missing.

    Printed even when there is nothing to print, because a section that
    disappears when it has nothing to report is indistinguishable from one
    that broke — and because an empty cell is a result of this command rather
    than a gap in it, so it is owed a reason the way a filled cell is owed
    its n.
    """
    lines = ["empty cells, with what was missing:"]
    entries = [
        (row.cell.name, column, reason)
        for row in read_rows
        for column, reason in row.missing
    ]
    if not entries:
        return [*lines, "   (every cell the corpus holds is filled)"]
    for name, column, reason in entries:
        lines += [f"   {name} ({column}):", *_wrap(reason, indent="     ")]
    return lines


def calibrate(
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
