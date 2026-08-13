"""The calibrate-v1 command surface: the corpus read as a calibration table.

Everything here drives `main([...])` and reads stdout, the repo's convention
for a command: the rendered table is what a selection query would consume, so
asserting on it catches a cell that is right in `cells` and wrong on the page.
Fixture task sets are built in tmp_path from one trivial underlying change, so
a cell's rung floor is decided by the diffs its runs logged and by nothing
else, and its multipliers by the costs the log carries.
"""

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import workdir_diff

from ai_benchmark import calibrate_v1, firstparty_v1, reconcile_v1
from ai_benchmark.cli import main

# The underlying change every fixture task asks for: one function, one answer.
# Trivial on purpose — these tests are about grouping logged costs and
# verdicts, and a task with any depth of its own would only slow the grader
# down.
_PRISTINE = "def answer():\n    return None\n"
_SOLVED = "def answer():\n    return 42\n"
_GRADING = "from thing import answer\n\n\ndef test_answer():\n    assert answer() == 42\n"

_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"

# Two frozen zero-knob ids, so a fixture control counts as one. Which category
# a fixture writes them into is the fixture's business — the frozen set says
# these tasks carry no construction block, not what they are about.
_CONTROL = "wordcount-top-words"
_OTHER_CONTROL = "spans-subtract-gaps"

# The prediction every constructed fixture task registers. A constant and not
# a parameter: calibrate reads no prediction at all — it reads costs off the
# log and rungs off the replay — so a fixture varying this would suggest the
# table moved with it. The block is written because the loader requires one.
_PREDICTION = {
    "rung": "haiku-solvable",
    "rationale": "the levels this task sets should land it here",
}

# When the fixture sweeps ran. Constant for the same reason: calibrate keys
# nothing on a round, so no fixture has a reason to move the date.
_AS_OF = date(2026, 8, 4)


def write_task(
    root: Path,
    task_id: str,
    *,
    category: str = "feature-dev",
    scale: str = "single-file",
    substrate: bool = False,
    control: bool = False,
    knobs: dict[str, str] | None = None,
) -> None:
    """One fixture task directory: a zero-knob control when `knobs` is None, a
    constructed task activating exactly those knobs otherwise.

    `scale` and `substrate` are what the mix disclosure is read off, and they
    are the two annotations the row key does not carry — so a fixture sets
    them to build a cell whose composition differs from its denominator's.

    `control` is the other way to be a control: written under an id of the
    fixture's own choosing rather than borrowed from the frozen set, which is
    what a task authored to fill a category does.
    """
    directory = root / task_id
    (directory / "repo").mkdir(parents=True)
    (directory / "grading").mkdir()
    (directory / "repo" / "thing.py").write_text(_PRISTINE)
    (directory / "grading" / "test_answer.py").write_text(_GRADING)
    spec: dict[str, Any] = {
        "id": task_id,
        "category": category,
        "scale": scale,
        "language": "python",
        "prompt": f"make answer() return 42 ({task_id})",
    }
    if control:
        spec["control"] = True
    if knobs is not None:
        spec["construction"] = {
            "knobs": [{"id": knob, "level": level} for knob, level in knobs.items()],
            "prediction": _PREDICTION,
        }
        if substrate:
            spec["construction"]["substrate"] = {
                "origin": "https://example.invalid/cold/repo",
                "commit": "0" * 40,
                "license": "MIT",
            }
    (directory / "task.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))


def solved_diff(task: firstparty_v1.Task) -> str:
    def solve(workdir: Path) -> None:
        (workdir / "thing.py").write_text(_SOLVED)

    return workdir_diff(task, solve)


def write_log(
    path: Path,
    tasks: list[firstparty_v1.Task],
    resolved_by: dict[str, list[str]],
    *,
    cost: dict[str, dict[str, float]] | None = None,
    models: tuple[str, ...] = (_HAIKU, _SONNET),
    agent: str = "claude-code",
) -> None:
    """A raw run log sweeping `tasks` with `models`.

    `resolved_by` names, per task id, the models whose run solved it; every
    other model logs the empty diff, which grades unresolved because the
    grading tests fail on the pristine repository. `cost` names what a run
    cost, per task id and model; every cell it does not name costs the same
    default, so a test that says nothing about cost logs a flat sweep and one
    about multipliers sets only the cells its ratio is read from.
    """
    rows = []
    for task in tasks:
        diff = solved_diff(task)
        for model in models:
            rows.append(
                firstparty_v1.Run(
                    task_id=task.id,
                    agent=agent,
                    agent_version="2.1.220",
                    model=model,
                    output="done",
                    diff=diff if model in resolved_by.get(task.id, []) else "",
                    tokens_in=41000,
                    tokens_out=1500,
                    cost_usd=(cost or {}).get(task.id, {}).get(model, 0.20),
                    latency_s=64.5,
                    turns=7,
                    as_of=_AS_OF,
                    sweep="fixture-sweep",
                )
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(row.model_dump_json() + "\n" for row in rows))


def calibrate(tasks: Path, log: Path, capsys: pytest.CaptureFixture[str]) -> str:
    main(["calibrate-v1", "--tasks", str(tasks), "--replay", str(log)])
    return capsys.readouterr().out


_REPO = Path(__file__).parent.parent

# The table's columns, in the order it prints them. Named here so that reading
# a cell out of a row is done by column and not by counting tokens: an empty
# cell is one token and a filled one is two, so a positional read would shift
# under exactly the rows these tests are about.
_COLUMNS = ("profile", "tasks", *reconcile_v1.LADDER_MODELS, "rung floor")


def checked_in_argv() -> list[str]:
    """The checked-in task set and run logs, named explicitly. The command's
    own defaults are relative to the working directory, and a test that leans
    on them passes or fails by where pytest was started from."""
    return [
        "calibrate-v1",
        "--tasks", str(_REPO / "tasks" / "first-party-v1"),
        "--replay", str(_REPO / "data" / "first-party-v1-runs"),
    ]


def category_block(out: str, category: str) -> str:
    """One category's table alone. A multiplier read off the wrong table is
    the pooling this command refuses, so every assertion about a row is scoped
    to the table the row belongs to."""
    block = out.split(f"category {category}\n")[1]
    return re.split(
        r"^(?:category |empty cells)", block, maxsplit=1, flags=re.MULTILINE
    )[0]


def table_block(out: str, category: str) -> list[str]:
    """The rows of one category's table, header first.

    The denominator sits above it and the mix disclosures below it, both
    carrying profile labels of their own, so a row picked out of the whole
    block by its label could be picked out of the prose around it instead.
    """
    paragraphs = category_block(out, category).split("\n\n")
    [block] = [
        paragraph for paragraph in paragraphs
        if paragraph.strip().startswith("profile")
    ]
    return [line for line in block.splitlines() if line.strip()]


def cells(out: str, category: str, profile: str) -> dict[str, str]:
    """One row of one category's table, read by column.

    Column boundaries come from the header, so a cell keeps its own spaces —
    "1.62x (n=3)" is one cell and reads like one.
    """
    header, *rows = table_block(out, category)
    starts = [header.index(column) for column in _COLUMNS]
    [row] = [line for line in rows if line.split()[:1] == [profile]]
    padded = row.ljust(len(header))
    return {
        column: padded[start:end].strip()
        for column, start, end in zip(_COLUMNS, starts, [*starts[1:], None])
    }


def profiles(out: str, category: str) -> list[str]:
    """The profile column of one category's table, in the order printed."""
    return [line.split()[0] for line in table_block(out, category)[1:]]


def mixes(out: str, category: str) -> dict[str, str]:
    """The disclosed mix of every row whose own differs from its baseline's,
    keyed by profile. Empty where the table disclosed nothing."""
    paragraphs = category_block(out, category).split("\n\n")
    disclosed = [
        paragraph for paragraph in paragraphs
        if "rows whose mix differs" in paragraph
    ]
    if not disclosed:
        return {}
    lines = [line for line in disclosed[0].splitlines()[1:] if line.strip()]
    split = (line.strip().split(" ", 1) for line in lines)
    return {label.rstrip(":"): mix.strip() for label, mix in split}


def baseline_line(out: str, category: str, label: str) -> str:
    """One of the two lines naming what a table's denominator was: its mean
    cost per model, or what the controls behind that mean are made of."""
    [line] = [
        line for line in category_block(out, category).splitlines()
        if line.strip().startswith(label)
    ]
    return line.strip().removeprefix(label).strip()


def empty_cells(out: str) -> str:
    """The empty-cell list, with its whitespace collapsed. The reasons there
    are wrapped prose, so a sentence asserted against the raw text would pass
    or fail on where the wrap happened to fall — while a cell heading, whose
    parts are single-spaced, reads the same either way."""
    return " ".join(out.split("empty cells")[1].split())


# --- the demo: the checked-in corpus as a calibration table --------------------


def checked_in_profiles() -> dict[tuple[str, str], list[firstparty_v1.Task]]:
    """The cells the checked-in task set holds, keyed category x profile.

    Derived from the artifacts the command reads rather than pinned, so that a
    round adding tasks adds rows here instead of breaking the test. The key is
    built independently of `calibrate_v1` — sorting the activations by knob
    number is what the row key claims to be, and a helper that called the
    module's own key builder would agree with it however wrong both were.
    """
    profiles: dict[tuple[str, str], list[firstparty_v1.Task]] = {}
    for task in firstparty_v1.load_task_set(_REPO / "tasks" / "first-party-v1"):
        levels = {} if task.construction is None else task.construction.levels
        profile = ",".join(
            f"{knob}={levels[knob]}"
            for knob in sorted(levels, key=lambda knob: int(knob[1:]))
        )
        profiles.setdefault((task.category, profile or "(zero-knob)"), []).append(task)
    return profiles


def checked_in_costs() -> dict[str, dict[str, float]]:
    """What every checked-in run cost, per task and model."""
    costs: dict[str, dict[str, float]] = {}
    for log in reconcile_v1.collect_logs([_REPO / "data" / "first-party-v1-runs"]):
        for run in firstparty_v1.load_runs(log):
            costs.setdefault(run.task_id, {})[run.model] = run.cost_usd
    return costs


def test_calibrate_v1_tabulates_the_checked_in_corpus(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command's reason to exist, run on real artifacts.

    Every profile the task set holds gets a row in its own category's table,
    carrying the tasks it holds and a multiplier per model with the n that
    multiplier was meant over. The expectations are computed from the same
    artifacts the command reads — the arithmetic done twice, here and in the
    module — so a later round adds rows rather than breaking this test, and a
    cell whose numbers stop matching the corpus is what it watches for.
    """
    profiles = checked_in_profiles()
    costs = checked_in_costs()
    controls = {
        category: tasks
        for (category, profile), tasks in profiles.items()
        if profile == "(zero-knob)"
    }

    main(checked_in_argv())
    out = capsys.readouterr().out

    assert f"{len(profiles)} cell(s)" in out
    for (category, profile), tasks in profiles.items():
        row = cells(out, category, profile)
        assert row["tasks"] == str(len(tasks)), f"{category} {profile}: task count"
        for model in reconcile_v1.LADDER_MODELS:
            ran = [task for task in tasks if model in costs.get(task.id, {})]
            denominator = [
                control for control in controls.get(category, [])
                if model in costs.get(control.id, {})
            ]
            if not ran or not denominator:
                assert row[model] == "-", f"{category} {profile}: {model} not measured"
                continue
            mean = sum(costs[task.id][model] for task in ran) / len(ran)
            base = sum(costs[c.id][model] for c in denominator) / len(denominator)
            assert row[model] == f"{mean / base:.2f}x (n={len(ran)})", (
                f"{category} {profile}: {model} multiplier"
            )

    # The denominator each table divides by is its own category's, named on
    # the table so the arithmetic can be checked without the raw logs — and so
    # that pooling two categories' controls would be visible here.
    for category, members in controls.items():
        line = category_block(out, category).splitlines()[0]
        assert "baseline mean cost" in line
        for model in reconcile_v1.LADDER_MODELS:
            ran = [task for task in members if model in costs.get(task.id, {})]
            mean = sum(costs[task.id][model] for task in ran) / len(ran)
            assert f"{model} ${mean:.4f} (n={len(ran)})" in line


def test_calibrate_v1_floors_the_checked_in_cells_at_their_weakest_rung(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The floor column, against rungs derived from the same replay.

    Reconciliation grades every checked-in diff into an observed rung, and a
    cell's floor is the weakest of them. Reading the expectation off that
    computation rather than off a pinned list is what keeps the two views of
    one corpus honest with each other: a floor that stopped matching the rungs
    reconcile prints would be this command inventing difficulty.
    """
    tasks = firstparty_v1.load_task_set(_REPO / "tasks" / "first-party-v1")
    logs = reconcile_v1.collect_logs([_REPO / "data" / "first-party-v1-runs"])
    runs = [run for log in logs for run in firstparty_v1.load_runs(log)]
    outcomes = reconcile_v1.observed_outcomes(tasks, runs, source="test")

    main(checked_in_argv())
    out = capsys.readouterr().out

    for (category, profile), members in checked_in_profiles().items():
        graded = [
            outcomes[task.id] for task in members if outcomes[task.id].determined
        ]
        row = cells(out, category, profile)
        if not graded:
            assert row["rung floor"] == "-", f"{category} {profile}: no graded task"
            continue
        weakest = min(
            graded, key=lambda outcome: reconcile_v1.RUNGS.index(outcome.rung)
        )
        assert row["rung floor"] == f"{weakest.rung} (n={len(graded)})", (
            f"{category} {profile}: rung floor"
        )


def test_calibrate_v1_discloses_what_the_checked_in_corpus_is_made_of(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The scope and substrate skew of the real corpus, on the page.

    The row key is category x profile and the actuarial-loop design's own
    primary key is category x scope, so every multiplier here divides tasks of
    one scope mix by controls of another — and no control in the corpus is
    vendored at all, so a vendored cell's multiplier prices the substrate too.
    Neither is fixed by re-keying, which is a decision above this command; both
    are disclosed, and this is the test that they are.

    The feature-dev baseline's own mix is pinned rather than derived because
    the zero-knob baseline is frozen in code: those eleven controls are the
    denominator of every feature-dev multiplier this project will ever print,
    and a round that changed their mix would have changed the frozen set.
    """
    main(checked_in_argv())
    out = capsys.readouterr().out

    assert baseline_line(out, "feature-dev", "baseline mix") == (
        "6 single-file + 5 cross-file; 11 hand-authored"
    )
    # Every constructed feature-dev cell is single-file, so every one of them
    # is read against a denominator nearly half of which is not.
    disclosed = mixes(out, "feature-dev")
    assert set(disclosed) == {
        profile for (category, profile) in checked_in_profiles()
        if category == "feature-dev" and profile != "(zero-knob)"
    }
    # Round 1's four `-l1` variants and, since #43, the two headroom anchors —
    # which declare `K1=acceptance` because a task outside the frozen baseline
    # has to declare something and that is the level their specs are written
    # at. The mix is what stays even across the join, and it is the reading
    # this row cannot give: those six are alike in scope and substrate and
    # nothing else, since four are 26-to-36-line changes bet at the
    # floor and two are wide contracts bet unsolved. The pooling is registered
    # in the design note's section 23.10 and in both anchors' own comments,
    # because the row key has no way to say it.
    assert disclosed["K1=acceptance"] == "6 single-file; 6 hand-authored"
    # The cells built entirely on vendored substrate, priced against
    # hand-authored controls because no control in the corpus is vendored:
    # round 1's two dense K7 tasks, joined by round 3's two (#41), and the calm
    # controls those were paired with. What the row key cannot show is that
    # those calm tasks are the corpus's first vendored *comparator* — they are
    # a K7 cell of their own here, not a denominator, because a zero-knob
    # control declares no construction and these declare K7. The pair they
    # close is read by `reconcile-v1`, which compares the two members directly;
    # this table goes on dividing both cells by the hand-authored eleven.
    assert disclosed["K7=dense"] == "4 single-file; 4 vendored"
    assert disclosed["K7=calm"] == "2 single-file; 2 vendored"


# What the table published over the checked-in corpus after round 3, per
# category and profile: the two multiplier columns and the denominator each
# was divided by. Pinned rather than derived, which is the opposite of what
# the demo tests above do and is the point of this one — a derived expectation
# follows the corpus wherever it goes, and these numbers are quoted in the
# design note's section 31 and read by whoever is deciding what a round cost.
# A round that adds feature-dev or refactor tasks moves them and updates this
# table in the same commit; anything else that moves them is the defect this
# watches for.
# Each row: tasks, the two multiplier columns, rung floor. A declared
# feature-dev or refactor control would move every one of these — the tasks
# column by joining the row it lands in, a multiplier by entering the mean it
# divides by or is divided by, and a rung floor by adding a graded task to a
# cell's population — so all four are pinned together rather than just the
# two multipliers.
_PUBLISHED = {
    "feature-dev": {
        "(zero-knob)": ("11", "1.00x (n=11)", "1.00x (n=11)", "haiku-solvable (n=11)"),
        "K1=acceptance": ("6", "2.06x (n=6)", "1.79x (n=6)", "haiku-solvable (n=6)"),
        "K1=description": ("4", "0.85x (n=4)", "0.96x (n=4)", "haiku-solvable (n=4)"),
        "K1=intent": ("4", "0.94x (n=4)", "1.02x (n=4)", "haiku-solvable (n=4)"),
        "K4=narrow": ("1", "2.37x (n=1)", "1.54x (n=1)", "haiku-solvable (n=1)"),
        "K4=wide": ("1", "3.10x (n=1)", "2.28x (n=1)", "haiku-solvable (n=1)"),
        "K7=calm": ("2", "2.18x (n=2)", "1.95x (n=2)", "haiku-solvable (n=2)"),
        "K7=dense": ("4", "3.80x (n=4)", "2.42x (n=4)", "haiku-solvable (n=4)"),
        "K9=none": ("9", "0.74x (n=9)", "0.91x (n=9)", "haiku-solvable (n=9)"),
        "K9=single": ("9", "1.10x (n=9)", "1.29x (n=9)", "haiku-solvable (n=9)"),
        "K10=narrow": ("1", "3.14x (n=1)", "1.45x (n=1)", "haiku-solvable (n=1)"),
        "K10=wide": ("1", "6.40x (n=1)", "7.93x (n=1)", "haiku-solvable (n=1)"),
        "K11=far": ("4", "0.88x (n=4)", "0.75x (n=4)", "haiku-solvable (n=4)"),
        "K1=acceptance,K12=criterion": (
            "3", "1.19x (n=3)", "0.67x (n=3)", "haiku-solvable (n=3)"
        ),
        "K1=acceptance,K12=repo-primitive": (
            "3", "0.81x (n=3)", "0.68x (n=3)", "haiku-solvable (n=3)"
        ),
        "K1=acceptance,K12=unmentioned": (
            "3", "0.94x (n=3)", "0.70x (n=3)", "haiku-solvable (n=3)"
        ),
        "K1=acceptance,K12=prose": (
            "3", "0.99x (n=3)", "0.71x (n=3)", "haiku-solvable (n=3)"
        ),
        "K1=intent,K7=dense,K9=single": (
            "2", "6.84x (n=2)", "3.73x (n=1)", "sonnet-only (n=1)"
        ),
    },
    "refactor": {
        "(zero-knob)": ("11", "1.00x (n=11)", "1.00x (n=11)", "haiku-solvable (n=11)"),
        "K8=misleading": ("7", "1.11x (n=7)", "1.19x (n=7)", "haiku-solvable (n=7)"),
    },
}

_PUBLISHED_DENOMINATORS = {
    "feature-dev": f"{_HAIKU} $0.0711 (n=11), {_SONNET} $0.1846 (n=11)",
    "refactor": f"{_HAIKU} $0.0572 (n=11), {_SONNET} $0.1643 (n=11)",
}

# The baseline's own mix, and every row whose mix differs from it — the other
# two axes a declared control would move, on top of the row's own numbers.
_PUBLISHED_MIX = {
    "feature-dev": "6 single-file + 5 cross-file; 11 hand-authored",
    "refactor": "5 single-file + 6 cross-file; 11 hand-authored",
}

_PUBLISHED_ROW_MIX = {
    "feature-dev": {
        "K1=acceptance": "6 single-file; 6 hand-authored",
        "K1=description": "4 single-file; 4 hand-authored",
        "K1=intent": "4 single-file; 4 hand-authored",
        "K4=narrow": "1 single-file; 1 vendored",
        "K4=wide": "1 single-file; 1 vendored",
        "K7=calm": "2 single-file; 2 vendored",
        "K7=dense": "4 single-file; 4 vendored",
        "K9=none": "9 single-file; 9 hand-authored",
        "K9=single": "9 single-file; 9 hand-authored",
        "K10=narrow": "1 cross-file; 1 vendored",
        "K10=wide": "1 cross-file; 1 vendored",
        "K11=far": "4 single-file; 4 hand-authored",
        "K1=acceptance,K12=criterion": "3 single-file; 3 hand-authored",
        "K1=acceptance,K12=repo-primitive": "3 single-file; 3 hand-authored",
        "K1=acceptance,K12=unmentioned": "3 single-file; 3 hand-authored",
        "K1=acceptance,K12=prose": "3 single-file; 3 hand-authored",
        "K1=intent,K7=dense,K9=single": "2 single-file; 2 vendored",
    },
    "refactor": {
        "K8=misleading": "4 single-file + 3 cross-file; 4 hand-authored + 3 vendored",
    },
}


def test_calibrate_v1_publishes_the_multipliers_round_3_published(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The published table, pinned.

    A multiplier is divided by its own category's controls, so anything that
    changes which tasks are read as controls changes every number in that
    category's column — quietly, because the arithmetic stays consistent with
    itself. The two categories the corpus holds are the two whose numbers are
    already published and being read, so this is where a change in the notion
    of a control would have to show up first. Pinned in full: tasks, both
    multipliers and the rung floor per row, the baseline's own mix, and every
    row's disclosed mix — a declared control moves all of them, not just the
    two multiplier columns.
    """
    main(checked_in_argv())
    out = capsys.readouterr().out

    for category, published in _PUBLISHED.items():
        assert baseline_line(out, category, "baseline mean cost") == (
            _PUBLISHED_DENOMINATORS[category]
        )
        assert baseline_line(out, category, "baseline mix") == (
            _PUBLISHED_MIX[category]
        )
        assert profiles(out, category) == list(published), f"{category}: rows"
        assert mixes(out, category) == _PUBLISHED_ROW_MIX[category], (
            f"{category}: row mixes"
        )
        for profile, (tasks, haiku, sonnet, rung_floor) in published.items():
            row = cells(out, category, profile)
            assert (
                row["tasks"], row[_HAIKU], row[_SONNET], row["rung floor"]
            ) == (tasks, haiku, sonnet, rung_floor), (
                f"{category} {profile}: row"
            )


def test_calibrate_v1_defaults_to_the_checked_in_task_set_and_run_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The demo is meant to be one argument-free command, so where the
    defaults point is behaviour. Checked at the seam rather than by grading
    the whole corpus a third time, which is what the tests around it pay
    for."""
    monkeypatch.chdir(_REPO)
    seen: dict[str, Any] = {}

    def spy(tasks: list[Any], tasks_root: Path, logs: list[Path], **_: Any) -> str:
        seen.update(tasks_root=tasks_root, logs=logs)
        return ""

    monkeypatch.setattr(calibrate_v1, "calibrate", spy)
    main(["calibrate-v1"])

    assert seen["tasks_root"] == Path("tasks/first-party-v1")
    assert seen["logs"]
    assert all(log.parent == Path("data/first-party-v1-runs") for log in seen["logs"])


def test_calibrate_v1_table_is_byte_identical_on_a_second_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A table a query reads has to be the same table twice, so any set or
    dict iteration order leaking into it is a defect. Twice in this process,
    then once more in a subprocess under a pinned PYTHONHASHSEED: within one
    process a hash-ordered structure iterates the same way every time, which
    is exactly how that bug would hide."""
    argv = checked_in_argv()

    main(argv)
    first = capsys.readouterr().out
    main(argv)
    assert capsys.readouterr().out == first

    reseeded = subprocess.run(
        [sys.executable, "-c",
         "import sys; from ai_benchmark.cli import main; main(sys.argv[1:])",
         *argv],
        capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONHASHSEED": "1"},
    )

    assert reseeded.stdout == first


# --- the row key: category x sorted knob-activation profile --------------------


def test_calibrate_v1_keys_a_row_by_its_sorted_knob_activation_profile(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two tasks activating the same knobs at the same levels are one cell,
    however their task.yaml happened to order the activations. A profile is a
    set of activations, so a key that kept the authoring order would split one
    cell into two and halve both n's."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "declared-forwards", knobs={"K1": "intent", "K12": "prose"})
    write_task(tasks, "declared-backwards", knobs={"K12": "prose", "K1": "intent"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"declared-forwards": [_HAIKU, _SONNET]})

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K1=intent,K12=prose")["tasks"] == "2"
    assert "K12=prose,K1=intent" not in out


def test_calibrate_v1_orders_the_zero_knob_row_first_then_knob_then_ladder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The order a reader reads a column down: the denominator at the top,
    then the single-knob profiles by knob number and by where their level
    sits on that knob's ladder, then the composites below the knobs they are
    composed of. Ladder order and not alphabetical — `none` before `single`
    on K9, `acceptance` before `intent` on K1 — so that reading down a column
    is reading up a ladder."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "intent", knobs={"K1": "intent"})
    write_task(tasks, "acceptance", knobs={"K1": "acceptance"})
    write_task(tasks, "planted", knobs={"K9": "single"})
    write_task(tasks, "stated", knobs={"K9": "none"})
    write_task(tasks, "composite", knobs={"K1": "intent", "K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    assert profiles(out, "feature-dev") == [
        "(zero-knob)",
        "K1=acceptance",
        "K1=intent",
        "K9=none",
        "K9=single",
        "K1=intent,K9=single",
    ]


def test_calibrate_v1_keeps_one_profile_per_category(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One profile in two categories is two cells, never one row over both:
    the categories are the capability matrix's own rows, and a multiplier
    pooled across them would divide one category's cost by another's
    baseline."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL, category="feature-dev")
    write_task(tasks, _OTHER_CONTROL, category="bug-fix")
    write_task(tasks, "feature-crux", knobs={"K9": "single"})
    write_task(tasks, "bug-crux", category="bug-fix", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, cost={
        _CONTROL: {_HAIKU: 0.10},
        _OTHER_CONTROL: {_HAIKU: 0.50},
        "feature-crux": {_HAIKU: 0.20},
        "bug-crux": {_HAIKU: 0.20},
    })

    out = calibrate(tasks, log, capsys)

    # Same numerator, different denominators: 0.20/0.10 against 0.20/0.50.
    assert cells(out, "feature-dev", "K9=single")[_HAIKU] == "2.00x (n=1)"
    assert cells(out, "bug-fix", "K9=single")[_HAIKU] == "0.40x (n=1)"


def test_calibrate_v1_prints_the_zero_knob_baseline_as_its_own_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The denominator is a row like any other, at 1.00x by construction, so
    the n every multiplier in the table was divided by is on the page."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, _OTHER_CONTROL)
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, cost={
        _CONTROL: {_HAIKU: 0.10, _SONNET: 0.30},
        _OTHER_CONTROL: {_HAIKU: 0.30, _SONNET: 0.50},
        "crux": {_HAIKU: 0.40, _SONNET: 0.80},
    })

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "(zero-knob)") == {
        "profile": "(zero-knob)",
        "tasks": "2",
        _HAIKU: "1.00x (n=2)",
        _SONNET: "1.00x (n=2)",
        "rung floor": "unsolved (n=2)",
    }
    # 0.40 / mean(0.10, 0.30) and 0.80 / mean(0.30, 0.50).
    crux = cells(out, "feature-dev", "K9=single")
    assert (crux[_HAIKU], crux[_SONNET]) == ("2.00x (n=1)", "2.00x (n=1)")


# --- the readings: cost multiplier and rung floor ------------------------------


def test_calibrate_v1_reads_the_cost_of_runs_that_failed_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that failed still spent its dollars, and a multiplier is a claim
    about what the work cost, not about whether it worked. Dropping the
    unresolved runs would price a cell off its lucky tasks alone — and the
    cells the selection tool most needs priced are the ones models fail in."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "hard-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {_CONTROL: [_HAIKU]}, cost={
        _CONTROL: {_HAIKU: 0.10},
        "hard-crux": {_HAIKU: 0.35},
    })

    out = calibrate(tasks, log, capsys)

    row = cells(out, "feature-dev", "K9=single")
    assert row[_HAIKU] == "3.50x (n=1)"
    assert row["rung floor"] == "unsolved (n=1)"


def test_calibrate_v1_floors_a_cell_at_its_weakest_rung(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The floor is the weakest rung in the cell, not the strongest and not an
    average: a profile one task of which haiku solved has been solved that
    cheaply at least once, and an averaged cell would claim a difficulty no
    task in it was ever measured at."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "easy-crux", knobs={"K9": "single"})
    write_task(tasks, "hard-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"easy-crux": [_HAIKU, _SONNET]})

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K9=single")["rung floor"] == "haiku-solvable (n=2)"


def test_calibrate_v1_counts_only_graded_tasks_into_a_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A task whose runs cannot decide between two rungs — sonnet resolved it
    and haiku never ran — is not on a rung, so it is left out of the floor's n
    rather than read as the weakest one. Its sonnet run still counts into the
    sonnet multiplier: a cost is measured whether or not the rung is."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "graded-crux", knobs={"K9": "single"})
    write_task(tasks, "half-swept-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "both.jsonl",
              [task for task in loaded if task.id != "half-swept-crux"], {})
    write_log(logs / "sonnet.jsonl",
              [task for task in loaded if task.id == "half-swept-crux"],
              {"half-swept-crux": [_SONNET]}, models=(_SONNET,))

    out = calibrate(tasks, logs, capsys)

    row = cells(out, "feature-dev", "K9=single")
    assert row["rung floor"] == "unsolved (n=1)"
    assert (row[_HAIKU], row[_SONNET]) == ("1.00x (n=1)", "1.00x (n=2)")


# --- the mix: what the row key does not carry ----------------------------------


def test_calibrate_v1_legends_the_three_counts_a_row_prints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A row carries three counts of different things — its population, the
    tasks a multiplier was meant over, and the tasks that landed on a rung —
    and an unexplained one reads as whichever of the others the reader met
    first. The header names all three, and the mix says what population it is
    counted from."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)
    # Down to the first category's table, and the wrapping collapsed: the
    # legend is a wrapped paragraph, so a sentence asserted against the raw
    # text would pass or fail on where the wrap happened to fall.
    header = " ".join(out.split("\ncategory ")[0].split())

    assert "tasks: the row's whole population" in header
    assert "a multiplier's n counts the tasks that ran that model" in header
    assert "a floor's n the tasks that landed on a rung" in header
    assert "mix: what a population of tasks is made of" in header
    assert "category x scope" in header
    # And why a vendored cell can never be read against its own substrate:
    # provenance lives in a construction block and a control carries none.
    assert "no control can be vendored" in header


def test_calibrate_v1_discloses_a_cell_whose_scope_is_not_its_denominators(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A row of single-file tasks divided by a part-cross-file baseline says
    so. Scope is the actuarial-loop design's primary key and this table keys
    on the knob profile instead, so the multiplier is a comparison across the
    scope difference as much as across the knob — and a reader who could not
    see the difference would read the whole of it as the knob's price."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL, scale="single-file")
    write_task(tasks, _OTHER_CONTROL, scale="cross-file")
    write_task(tasks, "narrow-crux", knobs={"K9": "single"}, scale="single-file")
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    assert baseline_line(out, "feature-dev", "baseline mix") == (
        "1 single-file + 1 cross-file; 2 hand-authored"
    )
    assert mixes(out, "feature-dev") == {
        "K9=single": "1 single-file; 1 hand-authored"
    }


def test_calibrate_v1_discloses_a_vendored_cell_priced_off_hand_authored_controls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A cell built on a vendored substrate names its provenance, because no
    control in this corpus has one. There is no same-substrate denominator to
    read such a cell against, so its multiplier prices the difference between
    somebody else's repository and ours along with the knob — which is a
    reading, not a defect, but only if the page says which it is."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "found-terrain", knobs={"K7": "dense"}, substrate=True)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, cost={
        _CONTROL: {_HAIKU: 0.10},
        "found-terrain": {_HAIKU: 0.50},
    })

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K7=dense")[_HAIKU] == "5.00x (n=1)"
    assert baseline_line(out, "feature-dev", "baseline mix") == (
        "1 single-file; 1 hand-authored"
    )
    assert mixes(out, "feature-dev") == {"K7=dense": "1 single-file; 1 vendored"}


def test_calibrate_v1_discloses_no_mix_where_a_row_matches_its_denominator(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The disclosure is about a difference, so a table where there is none
    prints no list of differences. A row read against controls of its own
    scope and its own substrate is the reading the multiplier claims to be."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "matched-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    assert baseline_line(out, "feature-dev", "baseline mix") == (
        "1 single-file; 1 hand-authored"
    )
    assert mixes(out, "feature-dev") == {}


def test_calibrate_v1_says_so_where_a_category_has_no_controls_to_be_made_of(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A category with no zero-knob control has no denominator and so nothing
    for a mix to be taken over. "The controls are of this mix" and "there are
    no controls" are different statements, and a blank would be neither.

    Nor is any row listed as differing from that absent baseline: with no
    control there is no denominator, so every multiplier in the table is
    empty, and a mix disclosed there would footnote a reading the table does
    not make."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _OTHER_CONTROL, category="bug-fix")
    write_task(tasks, "unpriced-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    assert baseline_line(out, "feature-dev", "baseline mix") == (
        "(no zero-knob control in this category)"
    )
    assert cells(out, "feature-dev", "K9=single")[_HAIKU] == "-"
    assert mixes(out, "feature-dev") == {}


# --- what v1 refuses: interpolation, backoff, pooling --------------------------


def test_calibrate_v1_leaves_an_unswept_cell_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A profile the corpus holds but no sweep reached keeps its row and
    prints nothing in it. The row is the honest artifact: the profile exists,
    and the table has no number for it."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "unswept-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task for task in loaded if task.id == _CONTROL], {})

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K9=single") == {
        "profile": "K9=single",
        "tasks": "1",
        _HAIKU: "-",
        _SONNET: "-",
        "rung floor": "-",
    }
    missing = empty_cells(out)
    assert f"feature-dev K9=single ({_HAIKU}):" in missing
    assert f"no task in the cell has a {_HAIKU} run" in missing
    assert "feature-dev K9=single (rung floor):" in missing
    assert "no task in the cell has a rung" in missing


def test_calibrate_v1_will_not_back_off_to_another_level_of_the_same_knob(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal that keeps the table honest: an unmeasured level prints
    empty, never filled in from the level next to it on the same knob's
    ladder. Backoff is what the actuarial-loop design defers to a later
    version, and a v1 that quietly did it would publish a number no sweep
    produced."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "stated", knobs={"K9": "none"})
    write_task(tasks, "planted", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task for task in loaded if task.id != "planted"], {}, cost={
        _CONTROL: {_HAIKU: 0.10, _SONNET: 0.10},
        "stated": {_HAIKU: 0.25, _SONNET: 0.25},
    })

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K9=none")[_HAIKU] == "2.50x (n=1)"
    planted = cells(out, "feature-dev", "K9=single")
    assert (planted[_HAIKU], planted[_SONNET], planted["rung floor"]) == ("-", "-", "-")


def test_calibrate_v1_will_not_interpolate_a_level_its_neighbours_bracket(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shape that would tempt an interpolator: a rung of K8's ladder
    unswept with the rungs either side of it measured. `partial` sits between
    `covered` at 2.00x and `bare` at 4.00x, so a table that filled it in from
    its neighbours would print 3.00x — a number no sweep produced, and one a
    consumer could not tell from a measured one. It prints empty instead."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "covered", knobs={"K8": "covered"})
    write_task(tasks, "partial", knobs={"K8": "partial"})
    write_task(tasks, "bare", knobs={"K8": "bare"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task for task in loaded if task.id != "partial"], {}, cost={
        _CONTROL: {_HAIKU: 0.10, _SONNET: 0.10},
        "covered": {_HAIKU: 0.20, _SONNET: 0.20},
        "bare": {_HAIKU: 0.40, _SONNET: 0.40},
    })

    out = calibrate(tasks, log, capsys)

    assert cells(out, "feature-dev", "K8=covered")[_HAIKU] == "2.00x (n=1)"
    assert cells(out, "feature-dev", "K8=bare")[_HAIKU] == "4.00x (n=1)"
    bracketed = cells(out, "feature-dev", "K8=partial")
    assert (bracketed[_HAIKU], bracketed[_SONNET]) == ("-", "-")
    assert bracketed["rung floor"] == "-"
    assert "3.00x" not in out
    assert f"feature-dev K8=partial ({_HAIKU}):" in empty_cells(out)


def test_calibrate_v1_will_not_pool_a_denominator_across_categories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A category with no swept control prices nothing, however well swept the
    other category is. Pooling is the one shortcut that would fill the cell,
    and the v1 contract this table is built to is that a cell is read against
    its own category's controls — a bug-fix baseline is not a feature-dev
    baseline."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _OTHER_CONTROL, category="bug-fix")
    write_task(tasks, "feature-crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    unpriced = cells(out, "feature-dev", "K9=single")
    assert (unpriced[_HAIKU], unpriced[_SONNET]) == ("-", "-")
    assert unpriced["rung floor"] == "unsolved (n=1)"
    assert (
        f"feature-dev has no zero-knob control with a {_HAIKU} run"
    ) in empty_cells(out)
    assert cells(out, "bug-fix", "(zero-knob)")[_HAIKU] == "1.00x (n=1)"


def test_calibrate_v1_prices_a_category_off_the_controls_it_declares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A declared control is a control of its own category and of no other.

    It is what a category the frozen baseline never reached is priced off:
    without it such a category has no denominator at all and every cell in it
    prints empty. And the pooling refusal is the same rule read the other way
    — each category divides by its own controls whatever the corpus grows
    beside it, which is why both K9=single rows read 3.00x, where a
    denominator pooling the two categories' controls would have printed 1.50x
    for feature-dev and 4.50x for fault-location.
    """
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "feature-crux", knobs={"K9": "single"})
    write_task(tasks, "located-control", category="fault-location", control=True)
    write_task(tasks, "located-crux", category="fault-location", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, cost={
        _CONTROL: {_HAIKU: 0.10},
        "feature-crux": {_HAIKU: 0.30},
        "located-control": {_HAIKU: 0.30},
        "located-crux": {_HAIKU: 0.90},
    })

    out = calibrate(tasks, log, capsys)

    assert baseline_line(out, "fault-location", "baseline mean cost").startswith(
        f"{_HAIKU} $0.3000 (n=1)"
    )
    assert cells(out, "fault-location", "(zero-knob)")[_HAIKU] == "1.00x (n=1)"
    assert cells(out, "fault-location", "K9=single")[_HAIKU] == "3.00x (n=1)"
    assert baseline_line(out, "feature-dev", "baseline mean cost").startswith(
        f"{_HAIKU} $0.1000 (n=1)"
    )
    assert cells(out, "feature-dev", "K9=single")[_HAIKU] == "3.00x (n=1)"


def test_calibrate_v1_will_not_divide_by_a_baseline_that_measured_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No multiple of zero is anything, so a cell read against a zero
    denominator is unreadable rather than infinitely expensive — the reading
    reconciliation gives an effort claim against a zero comparator.

    The baseline line still carries the n it measured that zero over: an empty
    *cell* is owed its reason in the list at the end, and the baseline line is
    not in that list, so a bare dash there would drop the only statement of
    how many controls produced the zero."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, cost={
        _CONTROL: {_HAIKU: 0.0, _SONNET: 0.20},
        "crux": {_HAIKU: 0.30, _SONNET: 0.40},
    })

    out = calibrate(tasks, log, capsys)

    row = cells(out, "feature-dev", "K9=single")
    assert (row[_HAIKU], row[_SONNET]) == ("-", "2.00x (n=1)")
    assert "measured $0.0000" in empty_cells(out)
    assert baseline_line(out, "feature-dev", "baseline mean cost") == (
        f"{_HAIKU} - (n=1), {_SONNET} $0.2000 (n=1)"
    )


def test_calibrate_v1_says_so_when_every_cell_is_filled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The empty-cell list is printed even when it is empty, because a section
    that disappears when it has nothing to report is indistinguishable from
    one that broke."""
    tasks = tmp_path / "tasks"
    write_task(tasks, _CONTROL)
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    out = calibrate(tasks, log, capsys)

    assert "(every cell the corpus holds is filled)" in empty_cells(out)


def test_calibrate_v1_documents_its_refusals_and_disclosures_in_its_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The refusals are v1's contract with whatever reads the table, and so is
    what the table discloses because its key does not carry it. Both are on the
    command's own help page and not only in the design note — a consumer
    reading the table from a script meets the help before it meets the
    header."""
    with pytest.raises(SystemExit):
        main(["calibrate-v1", "--help"])

    help_text = " ".join(capsys.readouterr().out.split())
    for refusal in ("interpolat", "backoff", "pool"):
        assert refusal in help_text
    for disclosure in ("substrate", "category x scope"):
        assert disclosure in help_text


# --- provenance: the discipline reconcile-v1 reads under -----------------------


def test_calibrate_v1_merges_nothing_into_the_dataset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The table is read-only over its inputs: it grades to get rungs, the way
    eval-v1 --replay does, but it is not an ingest and writes no record."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"crux": [_HAIKU, _SONNET]})
    before = sorted(path.name for path in tmp_path.rglob("*.jsonl"))

    calibrate(tasks, log, capsys)

    assert sorted(path.name for path in tmp_path.rglob("*.jsonl")) == before
    assert log.read_text().count("\n") == 2  # the two runs, nothing appended


def test_calibrate_v1_rejects_a_model_that_is_not_on_the_ladder(
    tmp_path: Path,
) -> None:
    """A rung floor is named after a model tier and a multiplier is read per
    model, so a run logged under a model the ladder does not name belongs to
    no column — and silently dropping it would shrink an n the table is read
    off."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {}, models=("claude-opus-5",))

    with pytest.raises(SystemExit, match="claude-opus-5"):
        main(["calibrate-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_calibrate_v1_rejects_runs_from_more_than_one_agent(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux", knobs={"K9": "single"})
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "a.jsonl", loaded, {}, agent="claude-code")
    write_log(logs / "b.jsonl", loaded, {}, agent="aider")

    with pytest.raises(SystemExit, match="aider"):
        main(["calibrate-v1", "--tasks", str(tasks), "--replay", str(logs)])


def test_calibrate_v1_rejects_a_task_that_declares_no_construction(
    tmp_path: Path,
) -> None:
    """Impossible past the lint, checked anyway: a task outside the frozen
    baseline with no construction block would land in the zero-knob row and
    become part of the denominator every multiplier is divided by."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "undeclared-task")
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {})

    with pytest.raises(SystemExit, match="undeclared-task"):
        main(["calibrate-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_calibrate_v1_rejects_a_replay_path_that_is_not_there(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux", knobs={"K9": "single"})

    with pytest.raises(SystemExit, match="missing.jsonl"):
        main(["calibrate-v1", "--tasks", str(tasks),
              "--replay", str(tmp_path / "missing.jsonl")])
