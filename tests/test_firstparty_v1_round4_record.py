"""Round 4's record, pinned: what sections 38-42 of the design note publish.

The round swept twelve tasks over six planted defects, each defect authored
twice — a `bug-fix` member whose deliverable is the correction and a
`fault-location` member whose deliverable is one (file, symbol) pair — so the
round's headline reading is what locating cost against fixing, within one
model, on one repository at a time.

Every figure here is pinned rather than derived, which is the point: a
derived expectation follows the corpus wherever it goes, and these numbers
are quoted in the design note and read by whoever is deciding what a round
cost. The pins come in two halves. The first is arithmetic over the three
checked-in run logs and the verdicts re-grading their diffs produces. The
second reads the design note itself — its quoted calibration rows against
what `calibrate-v1` actually prints, and its locate-versus-fix table against
what the logs actually say — because a record whose numbers drift from the
artifacts that earned them is the defect this file exists to catch, and the
record is prose that nothing else checks.

The round's runs are selected by their **sweep id** and never by log
filename: the sweep protocol bans selecting run logs by name, having watched
the first pass of the round-1 analysis silently drop two paid cells that way.
The three filenames appear here only where a command has to be given a log to
replay, which is section 42's verification.
"""

import json
import re
import statistics
from pathlib import Path

import pytest

from ai_benchmark import firstparty_v1, reconcile_v1
from ai_benchmark.cli import main

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_SWEEP = "round-4"
_AGENT_VERSION = "2.1.233 (Claude Code)"
_AS_OF = "2026-08-16"
_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"

# The three logs the sweep's three invocations wrote: the dry cell, haiku's
# other eleven, sonnet's twelve. Named only so that section 42's replay can be
# given one log at a time; nothing here selects runs by them.
_LOG_NAMES = (
    "2026-08-16-r4-a.jsonl",
    "2026-08-16-r4-b.jsonl",
    "2026-08-16-r4-c.jsonl",
)

# The six defects, each as (defect, fault-location member, bug-fix member).
# The two members share a starting repository byte for byte and are
# deliberately neither a task family nor a pair — both constructs require one
# varied knob and an agreed category, and these vary no knob and differ in
# category — so no report draws this pairing and the record has to.
_DEFECTS: tuple[tuple[str, str, str], ...] = (
    (
        "allotments",
        "allotments-locate-the-swallowed-reading",
        "allotments-go-back-for-what-nobody-could-read",
    ),
    ("ferry", "ferry-locate-the-idle-boat", "ferry-cast-off-when-it-should"),
    (
        "lostproperty",
        "lostproperty-locate-the-wrong-write-up",
        "lostproperty-write-up-what-happened",
    ),
    (
        "noticeboard",
        "noticeboard-locate-the-lost-notice",
        "noticeboard-show-every-notice",
    ),
    (
        "paperround",
        "paperround-locate-the-carried-over-count",
        "paperround-count-each-walk-on-its-own",
    ),
    (
        "postoffice",
        "postoffice-locate-the-wrong-band",
        "postoffice-charge-what-the-scale-said",
    ),
)

# Section 38's verdict table, cell by cell. Three of the twenty-four did not
# resolve, and which three is the whole of what sections 40 and 41 have to
# handle rather than drop.
_UNRESOLVED = {
    ("allotments-go-back-for-what-nobody-could-read", _HAIKU),
    ("lostproperty-write-up-what-happened", _HAIKU),
    ("paperround-locate-the-carried-over-count", _SONNET),
}

# Section 38's spend, per model and in total, to the fourth decimal the run
# log carries. The record states $3.27 against an expectation of $5-8 stated
# before the first paid run and against round 3's $12.1969.
_SPEND = {_HAIKU: 0.9066, _SONNET: 2.3681}
_TOTAL = 3.2748

# Section 40's table, read locate-relative-to-fix within one model: per
# defect, (cost, turns) per model. A starred pair in the note is one of whose
# two cells did not resolve; the star is derived here from `_UNRESOLVED`
# rather than pinned twice.
_LOCATE_VS_FIX: dict[str, dict[str, tuple[str, str]]] = {
    "allotments": {_HAIKU: ("0.59x", "0.69x"), _SONNET: ("0.57x", "0.54x")},
    "ferry": {_HAIKU: ("0.92x", "0.78x"), _SONNET: ("0.87x", "0.89x")},
    "lostproperty": {_HAIKU: ("3.01x", "10.00x"), _SONNET: ("0.71x", "0.67x")},
    "noticeboard": {_HAIKU: ("0.93x", "0.89x"), _SONNET: ("0.90x", "0.89x")},
    "paperround": {_HAIKU: ("0.87x", "0.75x"), _SONNET: ("1.53x", "1.22x")},
    "postoffice": {_HAIKU: ("0.70x", "0.67x"), _SONNET: ("0.72x", "0.64x")},
}

# The reading section 40 takes, over the pairs whose *both* members resolved:
# n, then (median, low, high) on cost and on turns.
_BOTH_RESOLVED = {
    _HAIKU: (4, ("0.89x", "0.70x", "0.93x"), ("0.76x", "0.67x", "0.89x")),
    _SONNET: (5, ("0.72x", "0.57x", "0.90x"), ("0.67x", "0.54x", "0.89x")),
}


def round_4_runs() -> dict[tuple[str, str], firstparty_v1.Run]:
    """Every run the sweep logged, keyed task x model.

    Read out of every log in the run-log directory and selected on the sweep
    id, which is what identifies a round: the sweep took three invocations,
    and a filename says nothing about which sweep a row belongs to.
    """
    runs = {
        (run.task_id, run.model): run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
        if run.sweep == _SWEEP
    }
    assert len(runs) == 24, "the round is 24 cells"
    return runs


@pytest.fixture(scope="module")
def verdicts() -> dict[tuple[str, str], bool]:
    """Each logged diff re-graded by its task's held-out tests.

    The computation `eval-v1 --replay` does, and the only way to a verdict: a
    run-log row carries the diff and no verdict at all. Module-scoped because
    grading twenty-four diffs is twenty-four pytest sessions and three tests
    below read the same answer.
    """
    tasks = {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}
    return {
        key: firstparty_v1.grade(tasks[key[0]], run.diff)
        for key, run in round_4_runs().items()
    }


def note_section(heading: str) -> str:
    """One numbered section of the design note, by its heading line."""
    body = _NOTE.read_text(encoding="utf-8").split(f"### {heading}\n")[1]
    return body.split("\n### ")[0].split("\n## ")[0]


def prose(text: str) -> str:
    """A passage with its wrapping collapsed. What a sentence of the record
    says is the pin; where the line happens to break is not, and a pin on the
    break would fail the next time a word is added upstream of it."""
    return " ".join(text.split())


def fenced_block(text: str) -> str:
    """The first fenced code block of a passage of the note."""
    return text.split("```\n")[1]


# The two fields of a calibration block a later round moves, and the only two.
#
# A block holds numbers of two kinds. The **measured** ones — the baseline
# means, every `(n=…)`, the multipliers, the rung floor — are this round's runs,
# and no task authored afterwards touches them. The **counted** ones — how many
# tasks the row holds, and the scope and substrate mix its denominator is drawn
# from — grow the moment a later round authors another control in the category:
# unswept, changing no measurement, and moving two digits in a block this record
# quotes as printed. So the quoted block is compared with the counted ones
# written out, and what they are today is asserted against the corpus itself
# (`controls_per_category`) rather than pinned to the day this was written.
_COUNTED_MIX = re.compile(
    r"^(   baseline mix +)\d+( single-file; )\d+( hand-authored)", re.MULTILINE
)
_COUNTED_ROW = re.compile(r"^(   \(zero-knob\)  )\d+ +", re.MULTILINE)


def counts_written_out(text: str) -> str:
    """This calibration output with its counted fields replaced by a mark."""
    return _COUNTED_ROW.sub(r"\1N ", _COUNTED_MIX.sub(r"\1N\2N\3", text))


def controls_per_category() -> dict[str, int]:
    """How many declared controls each category holds in the corpus today —
    which is exactly what a `(zero-knob)` row counts, a control being the one
    thing with no construction block to give it a profile."""
    counted: dict[str, int] = {}
    for task in firstparty_v1.load_task_set(_TASKS):
        if firstparty_v1.is_control(task):
            counted[task.category] = counted.get(task.category, 0) + 1
    return counted


def ratio(numerator: float, denominator: float) -> str:
    """A multiple as the record writes one: two decimals and an x."""
    return f"{numerator / denominator:.2f}x"


def test_the_round_is_one_sweep_of_twenty_four_cells_under_one_agent_version(
) -> None:
    """Section 38's sweep facts, off the rows themselves.

    One sweep id over three invocations and one agent version across all of
    them is the protocol's contract, and it is the only thing that makes the
    round's within-round comparisons free of a version boundary. A cell swept
    twice is schema-forbidden rather than checked here; what is checked is
    that each of the twelve tasks ran on each of the two ladder models.
    """
    runs = round_4_runs()

    assert {run.sweep for run in runs.values()} == {_SWEEP}
    assert {run.agent_version for run in runs.values()} == {_AGENT_VERSION}
    assert {run.agent for run in runs.values()} == {"claude-code"}
    assert {run.as_of.isoformat() for run in runs.values()} == {_AS_OF}

    tasks = {task_id for task_id, _ in runs}
    assert tasks == {member for _, locate, fix in _DEFECTS for member in (locate, fix)}
    assert len(tasks) == 12
    for task_id in tasks:
        assert {(task_id, _HAIKU), (task_id, _SONNET)} <= set(runs), task_id


def test_the_round_cost_what_the_record_states() -> None:
    """Section 38's spend line, and the design note's own statement of it.

    The expectation was stated before the first paid run and the comparison
    is against round 3, so all three numbers travel together: what was
    expected, what it came to, and what the last round cost.
    """
    runs = round_4_runs()

    for model, spend in _SPEND.items():
        actual = sum(
            run.cost_usd for (_, run_model), run in runs.items() if run_model == model
        )
        assert round(actual, 4) == spend, model
    assert round(sum(run.cost_usd for run in runs.values()), 4) == _TOTAL

    measured = prose(note_section("38. What the round measured"))
    assert (
        "Expected **$5–8**, 24 cells priced at the nearest terrain's p90"
    ) in measured
    assert (
        "Actual **$3.27** — $0.9066 on haiku and $2.3681 on sonnet, "
        "$3.2748 in total — against round 3's **$12.1969**"
    ) in measured


def test_the_limits_in_force_were_registered_before_the_sweep_and_never_reached(
) -> None:
    """Section 38's limits paragraph, against the table the runner reads.

    Both of the round's categories are registered, both at the flat default's
    own value, which is what makes the locate/fix contrast free of a ceiling
    difference and what makes the round free of a cross-round caveat. The
    second half is the round's own evidence that no verdict is a timeout in
    disguise: the longest run is a fraction of the limit it ran under.
    """
    assert firstparty_v1.LIVE_RUN_LIMITS_S["bug-fix"] == 600
    assert firstparty_v1.LIVE_RUN_LIMITS_S["fault-location"] == 600

    latencies = [run.latency_s for run in round_4_runs().values()]
    assert round(max(latencies), 1) == 101.4
    assert round(statistics.mean(latencies), 1) == 51.4

    measured = prose(note_section("38. What the round measured"))
    assert "`bug-fix` and `fault-location` in `LIVE_RUN_LIMITS_S`, both at" in measured
    assert "**600 seconds**" in measured
    assert "**No cross-round caveat arises**" in measured
    assert "the round's longest run was **101.4 s**" in measured


def test_which_cells_resolved_per_category_and_model(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 38's resolution table: 21 of 24, and which three did not.

    Pinned per cell rather than as two counts, because the counts are the
    same under three different stories about which cells failed and sections
    40 and 41 both turn on which ones they were.
    """
    assert {key for key, resolved in verdicts.items() if not resolved} == _UNRESOLVED

    categories = {
        task.id: task.category for task in firstparty_v1.load_task_set(_TASKS)
    }
    counts = {
        (category, model): sum(
            1
            for (task_id, run_model), resolved in verdicts.items()
            if categories[task_id] == category and run_model == model and resolved
        )
        for category in ("bug-fix", "fault-location")
        for model in (_HAIKU, _SONNET)
    }
    assert counts == {
        ("bug-fix", _HAIKU): 4,
        ("bug-fix", _SONNET): 6,
        ("fault-location", _HAIKU): 6,
        ("fault-location", _SONNET): 5,
    }
    assert sum(counts.values()) == 21


def test_the_rungs_the_round_landed_on() -> None:
    """Section 38's rung line, through the code the reports read rungs with.

    Two `sonnet-only`, both `bug-fix`, and nothing `unsolved` — so the
    corpus's unsolved census is unmoved by this round. Taken from
    `observed_outcomes` over the round's own tasks and runs rather than from
    the verdicts above, so that the record's rungs are the reports' rungs and
    not this file's arithmetic about them.

    The round's own tasks are the ones it swept, and are selected as such: a
    later round authoring another task in either of these two categories adds
    an `unswept` outcome that says nothing about what round 4 landed on, and
    reading it in here would turn this section over for a task the round never
    saw.
    """
    runs = list(round_4_runs().values())
    swept = {run.task_id for run in runs}
    tasks = [
        task
        for task in firstparty_v1.load_task_set(_TASKS)
        if task.category in ("bug-fix", "fault-location") and task.id in swept
    ]
    outcomes = reconcile_v1.observed_outcomes(
        tasks, runs, source="round-4 record"
    )

    sonnet_only = {
        task_id for task_id, outcome in outcomes.items()
        if outcome.rung == "sonnet-only"
    }
    assert sonnet_only == {task_id for task_id, model in _UNRESOLVED if model == _HAIKU}
    assert {outcome.rung for outcome in outcomes.values()} == {
        "haiku-solvable", "sonnet-only"
    }
    assert sum(1 for o in outcomes.values() if o.rung == "haiku-solvable") == 10


def test_locating_against_fixing_reads_per_defect_as_the_record_states(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 40's table, both halves: the numbers, and the note's own copy.

    The ratio is locate over fix within one model, off the logs' `cost_usd`
    and `turns`, because neither read-only report groups by a pair whose
    members differ in category. The note's table is parsed and compared cell
    for cell, so the record cannot drift from the artifacts silently; the
    stars it carries are checked against the verdicts rather than pinned,
    since what a star means is that one of the pair's cells did not resolve.
    """
    runs = round_4_runs()
    printed = {
        line.split()[0]: line.split()[1:]
        for line in fenced_block(
            note_section("40. Locating against fixing, per model over six matched "
                         "defects")
        ).splitlines()[1:]
        if line.strip()
    }

    for defect, locate, fix in _DEFECTS:
        row = printed[defect]
        for column, model in enumerate((_HAIKU, _SONNET)):
            cost = ratio(runs[locate, model].cost_usd, runs[fix, model].cost_usd)
            turns = ratio(runs[locate, model].turns, runs[fix, model].turns)
            assert (cost, turns) == _LOCATE_VS_FIX[defect][model], f"{defect} {model}"

            starred = not (verdicts[locate, model] and verdicts[fix, model])
            star = "*" if starred else ""
            assert row[column * 2: column * 2 + 2] == [cost + star, turns + star], (
                f"{defect} {model}: the note's row"
            )


def test_the_pairs_whose_both_members_resolved_read_below_parity(
    verdicts: dict[tuple[str, str], bool],
) -> None:
    """Section 40's reading, and the handling of the cells it leaves out.

    An unresolved run still spent its dollars, but what it spent them on is a
    failed attempt rather than the action being priced, so the reading is
    taken over the pairs whose both members resolved — nine of the twelve.
    The three it leaves out are quoted in the table above and read one at a
    time in section 41, and this pins the reason they cannot be dropped
    quietly: every above-parity figure in the round is one of them.
    """
    runs = round_4_runs()

    for model, (n, cost_reading, turns_reading) in _BOTH_RESOLVED.items():
        costs: list[float] = []
        turns: list[float] = []
        for _, locate, fix in _DEFECTS:
            if not (verdicts[locate, model] and verdicts[fix, model]):
                continue
            costs.append(runs[locate, model].cost_usd / runs[fix, model].cost_usd)
            turns.append(runs[locate, model].turns / runs[fix, model].turns)
        assert len(costs) == n, model
        for measured, reading in ((costs, cost_reading), (turns, turns_reading)):
            assert (
                f"{statistics.median(measured):.2f}x",
                f"{min(measured):.2f}x",
                f"{max(measured):.2f}x",
            ) == reading, model
            assert max(measured) < 1.0, f"{model}: every pair below parity"

    above_parity = {
        (defect, model)
        for defect, per_model in _LOCATE_VS_FIX.items()
        for model, (cost, turns) in per_model.items()
        if float(cost.rstrip("x")) > 1.0 or float(turns.rstrip("x")) > 1.0
    }
    assert above_parity == {("lostproperty", _HAIKU), ("paperround", _SONNET)}


def test_calibrate_v1_prints_the_two_new_rows_the_record_quotes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 39's quoted rows, against what the command actually prints.

    Both rows are their own category's denominator, so both multipliers read
    1.00x by construction and what the round publishes is the baseline mean
    each carries with the n it was taken over. The note quotes the two blocks
    as printed, which is a claim about bytes: it is checked as one.
    """
    main([
        "calibrate-v1",
        "--tasks", str(_TASKS),
        "--replay", str(_LOGS),
    ])
    out = capsys.readouterr().out

    quoted = fenced_block(note_section("39. The two new categories' rows, as printed"))
    # Block by block rather than as one string: the note quotes bug-fix and
    # fault-location back to back because in round 4 nothing sorted between
    # them, and round 5's code-review and codebase-comprehension now do. Each
    # quoted block is still checked as bytes; only their adjacency is not a
    # claim the note makes.
    printed = counts_written_out(out)
    for block in quoted.split("\ncategory ")[0:1] + [
        "category " + rest for rest in quoted.split("\ncategory ")[1:]
    ]:
        assert counts_written_out(block).strip("\n") in printed, (
            "a quoted block of the note is not what the table prints:\n" + block
        )
    # The counted fields, derived rather than quoted: a control authored in
    # either category by a later round is counted here, unswept, and the record
    # above still holds because nothing it measured moved.
    controls = controls_per_category()
    for category in ("bug-fix", "fault-location"):
        assert f"   (zero-knob)  {controls[category]} " in out
        assert (
            f"   baseline mix         {controls[category]} single-file; "
            f"{controls[category]} hand-authored"
        ) in out
    # Named again here, so that a note edited to match a changed table still
    # has to face the numbers the round actually published.
    assert (
        "   baseline mean cost   claude-haiku-4-5 $0.0805 (n=6), "
        "claude-sonnet-5 $0.2128 (n=6)"
    ) in quoted
    assert (
        "   baseline mean cost   claude-haiku-4-5 $0.0706 (n=6), "
        "claude-sonnet-5 $0.1819 (n=6)"
    ) in quoted
    assert quoted.count(
        "   (zero-knob)  6      1.00x (n=6)       1.00x (n=6)      "
        "haiku-solvable (n=6)"
    ) == 2


def test_replaying_each_log_reproduces_the_merged_records_exactly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 42's verification, run rather than remembered.

    Each of the three logs is replayed into a scratch dataset of its own, and
    all three into one merged dataset. The three per-log datasets together
    have to be the merged one record for record: no row missing, none
    duplicated, no field differing. Every record also has to carry its log
    row's own measurements, because replay re-grades the diff and never
    re-runs the agent.
    """
    per_log: list[dict[str, object]] = []
    merged_path = tmp_path / "merged.jsonl"
    for name in _LOG_NAMES:
        log = _LOGS / name
        alone = tmp_path / name
        for data in (alone, merged_path):
            main(["eval-v1", "--tasks", str(_TASKS), "--replay", str(log),
                  "--data", str(data)])
        capsys.readouterr()
        per_log.extend(
            json.loads(line) for line in alone.read_text().splitlines() if line.strip()
        )

    merged = [
        json.loads(line)
        for line in merged_path.read_text().splitlines()
        if line.strip()
    ]
    assert len(merged) == 24

    def cell(record: dict[str, object]) -> tuple[str, str]:
        return str(record["instance_id"]), str(record["model"])

    assert sorted(per_log, key=cell) == sorted(merged, key=cell)

    runs = round_4_runs()
    for record in merged:
        run = runs[record["instance_id"], record["model"]]
        assert record["cost_usd"] == run.cost_usd
        assert record["turns"] == run.turns
        assert record["tokens_in"] == run.tokens_in
        assert record["tokens_out"] == run.tokens_out
        assert record["latency_s"] == run.latency_s
        assert record["agent_version"] == run.agent_version
        assert record["as_of"] == run.as_of.isoformat()
        assert record["benchmark"] == "first-party-v1"
