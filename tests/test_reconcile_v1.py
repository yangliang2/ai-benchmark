"""The reconcile-v1 command surface: predictions read against swept outcomes.

Everything here drives `main([...])` and reads stdout, which is the repo's
convention for a command: the rendered report is what a reader acts on, so
asserting on it catches a grouping that is right in `observed_outcomes` and
wrong on the page. Fixture task sets are built in tmp_path from one trivial
underlying change, so a variant's rung is decided by the diff its run logged
and by nothing else.
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

from ai_benchmark import firstparty_v1, reconcile_v1
from ai_benchmark.cli import main

# The underlying change every fixture task asks for: one function, one answer.
# Trivial on purpose — these tests are about grouping logged verdicts, and a
# task with any depth of its own would only slow the grader down.
_PRISTINE = "def answer():\n    return None\n"
_SOLVED = "def answer():\n    return 42\n"
_GRADING = "from thing import answer\n\n\ndef test_answer():\n    assert answer() == 42\n"
_BEHAVIOUR = "import thing\n\n\ndef test_module_imports():\n    assert thing.answer\n"

_HAIKU = "claude-haiku-4-5"
_SONNET = "claude-sonnet-5"


def write_task(
    root: Path,
    task_id: str,
    *,
    category: str = "feature-dev",
    construction: dict[str, Any] | None = None,
) -> None:
    """One fixture task directory, with or without a construction block."""
    directory = root / task_id
    (directory / "repo").mkdir(parents=True)
    (directory / "grading").mkdir()
    (directory / "repo" / "thing.py").write_text(_PRISTINE)
    (directory / "grading" / "test_answer.py").write_text(_GRADING)
    spec: dict[str, Any] = {
        "id": task_id,
        "category": category,
        "scale": "single-file",
        "language": "python",
        "prompt": f"make answer() return 42 ({task_id})",
    }
    if category == "refactor":
        (directory / "grading" / "test_behaviour.py").write_text(_BEHAVIOUR)
        spec["grading"] = {"behaviour_tests": ["test_behaviour.py"]}
    if construction is not None:
        spec["construction"] = construction
    (directory / "task.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))


def constructed(
    knob: str,
    level: str,
    rung: str,
    *,
    family: str | None = None,
    pair: str | None = None,
    rationale: str = "the level this task sets should land it here",
    effort: dict[str, Any] | None = None,
    also: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One fixture construction block, activating `knob` and whatever `also`
    names beside it.

    `also` is what makes the composite shapes reachable: a task activating
    several knobs at once is the case the counting rules exist to refuse — no
    single knob is the varied one, and a baseline claim over three of them
    names none — and a helper that could only write one activation left those
    branches untestable.
    """
    prediction: dict[str, Any] = {"rung": rung, "rationale": rationale}
    if effort is not None:
        prediction["effort"] = effort
    block: dict[str, Any] = {
        "knobs": [
            {"id": knob, "level": level},
            *({"id": other, "level": at} for other, at in (also or {}).items()),
        ],
        "prediction": prediction,
    }
    if family is not None:
        block["family"] = family
    if pair is not None:
        block["pair"] = pair
    return block


def claim(comparator: str, metric: str, at_least_factor: float) -> dict[str, Any]:
    return {
        "comparator": comparator,
        "metric": metric,
        "at_least_factor": at_least_factor,
    }


def solved_diff(task: firstparty_v1.Task) -> str:
    def solve(workdir: Path) -> None:
        (workdir / "thing.py").write_text(_SOLVED)

    return workdir_diff(task, solve)


def write_log(
    path: Path,
    tasks: list[firstparty_v1.Task],
    resolved_by: dict[str, list[str]],
    *,
    as_of: date = date(2026, 8, 4),
    sweep: str | None = None,
    models: tuple[str, ...] = (_HAIKU, _SONNET),
    agent: str = "claude-code",
    effort: dict[str, dict[str, tuple[int, float]]] | None = None,
) -> None:
    """A raw run log sweeping `tasks` with `models`.

    `resolved_by` names, per task id, the models whose run solved it; every
    other model logs the empty diff, which grades unresolved because the
    grading tests fail on the pristine repository. `sweep` left out writes a
    legacy log: rows from before the sweep id existed, which reconciliation
    has to keep reading by their as-of date.

    `effort` names what a run cost, per task id and model, as (turns, cost);
    every cell it does not name gets the same default, so a test that says
    nothing about effort logs a flat sweep and a test about effort claims sets
    only the cells its claim is read from.
    """
    rows = []
    for task in tasks:
        diff = solved_diff(task)
        for model in models:
            turns, cost = (effort or {}).get(task.id, {}).get(model, (7, 0.21))
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
                    cost_usd=cost,
                    latency_s=64.5,
                    turns=turns,
                    as_of=as_of,
                    sweep=sweep,
                )
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(row.model_dump_json() + "\n" for row in rows))


def reconcile(
    tasks: Path, log: Path, capsys: pytest.CaptureFixture[str]
) -> str:
    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])
    return capsys.readouterr().out


_REPO = Path(__file__).parent.parent


def checked_in_argv() -> list[str]:
    """The checked-in task set and run logs, named explicitly. The command's
    own defaults are relative to the working directory, and a test that leans
    on them passes or fails by where pytest was started from."""
    return [
        "reconcile-v1",
        "--tasks", str(_REPO / "tasks" / "first-party-v1"),
        "--replay", str(_REPO / "data" / "first-party-v1-runs"),
    ]


def family_block(out: str) -> str:
    """Section 3 alone. A verdict like "monotonic along the ladder: no" has to
    be read inside the block it belongs to: "no" and "yes" and "unknown" all
    turn up somewhere in a full report whatever the family did, so an
    unscoped assertion would hold however wrong the answer was."""
    return out.split("3. family ladders")[1].split("4. crux/control pairs")[0]


def pairs_block(out: str) -> str:
    return out.split("4. crux/control pairs")[1].split("5. no-separation flags")[0]


def effort_block(out: str) -> str:
    """Section 6 alone. "hit", "miss" and "not assessable" are all words the
    rung reconciliation in section 1 uses too, so an unscoped assertion about
    an effort verdict would pass on the wrong section's row."""
    return out.split("6. effort-claim reconciliation")[1]


# --- the demo: the checked-in sweeps against the checked-in task set ----------


def checked_in_tasks_and_models() -> tuple[list[firstparty_v1.Task], dict[str, set[str]]]:
    """The checked-in task set, and per task id the models some log ran it on.

    Read from the same artifacts the command reads, so that what this file
    expects of the report moves when the artifacts move. Sweeps are the thing
    that keeps arriving here — round 1 covered the baseline, round 2 the
    Track-A tasks, round 3 the pysm substrate — and every count the report
    prints is a count of them. Pinned as literals they would be a running
    total edited once per round, and a number edited to match the output it is
    checking has stopped testing anything.

    The models and not just the ids, because a task swept on one model is a
    different report state from one swept on both: only the second can be
    scored to a rung, and round 3 produced the first of the first kind."""
    tasks = firstparty_v1.load_task_set(_REPO / "tasks" / "first-party-v1")
    logs = reconcile_v1.collect_logs([_REPO / "data" / "first-party-v1-runs"])
    models: dict[str, set[str]] = {}
    for log in logs:
        for run in firstparty_v1.load_runs(log):
            models.setdefault(run.task_id, set()).add(run.model)
    return tasks, models


def test_reconcile_v1_reports_the_checked_in_sweeps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command's reason to exist, run on real artifacts: every constructed
    task the checked-in logs have a run for is reported as swept, every one
    they do not is still on the page saying so, and the swept ones are told
    apart by how much of the ladder reached them — a task the whole ladder ran
    is scored against an observed rung, and a task only part of it ran reads
    `incomplete`, because a rung names the weakest model that resolved a task
    and no run log can name one until every rung has been tried.

    The numbers are derived from those artifacts rather than pinned, so a
    later round adds rows here instead of breaking the test. What is asserted
    is that the report accounts for exactly what the logs and the task set
    contain — a task dropped from a section, or counted in the header and
    missing from section 1, is what this is watching for."""
    tasks, swept_models = checked_in_tasks_and_models()
    constructed = [task for task in tasks if task.construction is not None]
    controls = [task for task in tasks if task.construction is None]
    swept = [task for task in constructed if task.id in swept_models]
    unswept = [task for task in constructed if task.id not in swept_models]
    # A rung names the weakest model that resolved a task, so only a task the
    # logs ran on every rung of the ladder can be scored to one. A task swept
    # on some of them is `incomplete`: the report withholds a rung rather than
    # reading the model that never ran as one that failed.
    fully_swept = [
        task
        for task in swept
        if swept_models[task.id] >= set(reconcile_v1.LADDER_MODELS)
    ]
    incomplete = [task for task in swept if task not in fully_swept]
    assert swept, "the demo has nothing to show until a round has been swept"

    main(checked_in_argv())
    out = capsys.readouterr().out

    # The header's census and section 1's agree, and both agree with the disk.
    assert (
        f"{len(tasks)} task(s): {len(controls)} control(s), "
        f"{len(constructed)} constructed"
    ) in out
    assert (
        f"{len(constructed)} constructed task(s): {len(swept)} swept, "
        f"{len(unswept)} unswept"
    ) in out
    for log in reconcile_v1.collect_logs([_REPO / "data" / "first-party-v1-runs"]):
        assert f"data/first-party-v1-runs/{log.name}" in out

    predictions = out.split("1. prediction reconciliation")[1]
    predictions = predictions.split("2. knob grouping")[0]
    # Every constructed task keeps a row whether or not a sweep has reached
    # it, and a swept one is scored: predicted rung, observed rung, verdict.
    for task in constructed:
        assert task.id in predictions, f"{task.id} vanished from the report"
    for task in fully_swept:
        assert re.search(
            rf"^ +{task.id} +\S+ +\S+ +(hit|miss)$", predictions, re.MULTILINE
        ), f"{task.id} ran on every ladder model and should carry a scored verdict"
    for task in incomplete:
        assert re.search(
            rf"^ +{task.id} +\S+ +incomplete +incomplete$", predictions, re.MULTILINE
        ), f"{task.id} ran on some ladder models and should say it is incomplete"
    for task in unswept:
        assert re.search(
            rf"^ +{task.id} +\S+ +unswept +unswept$", predictions, re.MULTILINE
        ), f"{task.id} has no runs logged and should say so"

    # Only a task the whole ladder ran can be scored, so the hit-rate cannot
    # outrun those: an incomplete task is swept and still carries no verdict.
    rate = re.search(r"hit-rate: (\d+)/(\d+) scored", predictions)
    assert rate
    hits, scored = int(rate[1]), int(rate[2])
    assert hits <= scored <= len(fully_swept)

    # The baseline is on the page as every knob's comparison row, and round 1
    # swept all of it: no baseline row has a task it did not sweep.
    grouping = out.split("2. knob grouping")[1].split("3. family ladders")[0]
    rows = [line for line in grouping.splitlines() if "(baseline)" in line]
    assert rows
    for row in rows:
        _, category, tasks_in_row, swept_in_row, *_ = row.split()
        assert tasks_in_row == swept_in_row, (
            f"{category} baseline not fully swept: {row}"
        )

    # Effort claims, derived the same way. Round 1 registered none — effort
    # was only ever recovered from its logs after the fact, which is the whole
    # reason the claim exists — so today this reads as the empty state. A
    # round-2 task that registers one moves this branch rather than breaking
    # it, which is what keeps the expectation coming from the artifacts.
    claimed = [
        task for task in constructed
        if task.construction is not None
        and task.construction.prediction.effort is not None
    ]
    effort = effort_block(out)
    if not claimed:
        assert effort.strip() == "(no effort claim registered in the task set)"
    else:
        assert f"{len(claimed)} registered claim(s)" in effort
        for task in claimed:
            assert task.id in effort, f"{task.id} registered a claim and lost it"


def test_reconcile_v1_keys_the_checked_in_rounds_the_way_their_logs_allow(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Which key the report used on the real artifacts, derived from them.

    Every round-1 row was written before the sweep id existed, so today every
    round here is an as-of date and the header says so. A round-2 log carrying
    ids moves this test rather than breaking it: what is asserted is that each
    round the report names is a key its logs actually contain, and that the
    header's account of which keying it used matches the logs."""
    logs = reconcile_v1.collect_logs([_REPO / "data" / "first-party-v1-runs"])
    runs = [run for log in logs for run in firstparty_v1.load_runs(log)]
    sweeps = {run.sweep for run in runs if run.sweep is not None}
    dates = {run.as_of for run in runs if run.sweep is None}

    main(checked_in_argv())
    header = capsys.readouterr().out.split("1. prediction reconciliation")[0]

    named = re.search(r"^  rounds +\d+ round\(s\): (.*)$", header, re.MULTILINE)
    assert named, "the report names the rounds it counted"
    labels = named[1].split(", ")
    for label in labels:
        if label.startswith("sweep "):
            assert label.removeprefix("sweep ") in sweeps
        else:
            assert date.fromisoformat(label.removeprefix("as-of ")) in dates
    assert ("no run carries a sweep id" in header) == (not sweeps)


def test_reconcile_v1_defaults_to_the_checked_in_task_set_and_run_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The demo is meant to be one argument-free command, so where the defaults
    point is behaviour. Checked at the seam rather than by grading the whole
    sweep a third time, which is what the two tests around it already pay
    for."""
    monkeypatch.chdir(_REPO)
    seen: dict[str, Any] = {}

    def spy(tasks: list[Any], tasks_root: Path, logs: list[Path], **_: Any) -> str:
        seen.update(tasks_root=tasks_root, logs=logs)
        return ""

    monkeypatch.setattr(reconcile_v1, "reconcile", spy)
    main(["reconcile-v1"])

    assert seen["tasks_root"] == Path("tasks/first-party-v1")
    assert seen["logs"]
    assert all(log.parent == Path("data/first-party-v1-runs") for log in seen["logs"])


def test_reconcile_v1_report_is_byte_identical_on_a_second_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The report is read by diffing it against the last one, so any set or
    dict iteration order leaking into it would show up as churn that means
    nothing. Twice in this process, then once more in a subprocess under a
    pinned PYTHONHASHSEED: within one process a hash-ordered structure iterates
    the same way every time, which is exactly how that bug would hide.
    """
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


def test_reconcile_v1_recomputes_the_checked_in_counters_under_the_amended_rule(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The rule change applied to history rather than grandfathered onto it.

    Counters are derived and never stored, so amending the rule re-reads every
    round of checked-in artifacts by itself. What that recomputation comes to
    is registered in the design note's section 9 amendment, and this is the
    test that the code and that table say the same thing — every expectation
    below is a row of it.

    Three of the six move, and each was argued in the record before the code
    could produce it: K1's round-2 flag stops counting because K12's families
    hold K1 constant and a knob nobody varied was not tested; K11 reads silent
    on four registered claims whose eight readings all missed, which is what
    section 19 predicted a direction-aware criterion would print; K7 and K8
    read stalled because no family, pair or registered claim ever put them to
    a contrast — K8's demotion stands in the note as the human verdict it
    always was, not as a counter this report reproduces.

    Round 3 moved K7 off that list by registering effort claims on tasks
    activating it, so K8 is now the only stalled knob here. That is the
    counter behaving as designed rather than an expectation loosened to fit:
    stalled says a knob has never been asked, and K7 has now been asked.
    """
    main(checked_in_argv())
    out = capsys.readouterr().out

    k1 = knob_block(out, "K1")
    # Round 1's four K1 families are the only rounds K1 was ever varied in.
    assert "as-of 2026-08-05  separated — family billing-split-by-weight" in k1
    assert "sweep round-2" not in counted_block(k1)
    assert "sweep round-2  separated" in informational_block(k1)
    assert "silent round(s): 0" in k1

    k8 = knob_block(out, "K8")
    assert "stalled: no round put K8 to a registered contrast" in k8
    assert "silent round(s): 0" in k8

    # K7 was stalled beside K8 until round 3 registered effort claims on
    # pysm tasks activating it, which is what a stalled knob being asked
    # looks like: the counter starts, and it starts on effort rather than
    # rungs, because K7's ladder is not enumerated and so its pairs order
    # no level above another.
    k7 = knob_block(out, "K7")
    assert "stalled" not in k7
    assert "sweep round-3  non-silent" in counted_block(k7)
    assert "registered effort reading(s) hit" in counted_block(k7)
    assert "K7's ladder is not enumerated" in counted_block(k7)
    assert "silent round(s): 0" in k7

    k9 = knob_block(out, "K9")
    assert "as-of 2026-08-05  no separation" in counted_block(k9)
    assert "sweep round-2  separated — pair digest" in counted_block(k9)
    assert "silent round(s): 1" in k9

    k11 = knob_block(out, "K11")
    assert "sweep round-2  no separation" in counted_block(k11)
    assert "0 of 8 registered effort reading(s) hit" in k11
    assert "silent round(s): 1" in k11
    assert "stalled" not in k11

    # K12 is the first knob the counter itself demotes. Round 2 left it one
    # silent round short; round 3 asked it again with the nightbus family and
    # got the same silence — no contrast separating upward, no effort reading
    # hitting — which is the second of the two rounds the discipline allows.
    k12 = knob_block(out, "K12")
    assert "sweep round-2  no separation" in counted_block(k12)
    assert "sweep round-3  no separation" in counted_block(k12)
    assert "silent round(s): 2" in k12
    assert (
        "demote K12: silent in sweep round-2 (2026-08-06), "
        "sweep round-3 (2026-08-08)"
    ) in k12

    # And it is the only one: a demotion travels out of this report into the
    # design note, so a second one appearing unnoticed is what this catches.
    # K8's demotion lives in the note as a human verdict and is not a counter
    # reading, which is why it is absent here despite being demoted there.
    assert re.findall(r"demote K\d+", out) == ["demote K12"]


# --- section 1: predictions ----------------------------------------------------


def test_reconcile_v1_scores_a_hit_and_echoes_the_rationale_of_a_miss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "hit-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="p",
        rationale="one planted decision the spec never makes derivable",
    ))
    write_task(tasks, "miss-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="p",
        rationale="every decision is stated, so the weakest model should get it",
    ))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    # hit-task: sonnet only -> sonnet-only, as predicted.
    # miss-task: neither model -> unsolved, against a haiku-solvable prediction.
    write_log(log, loaded, {"hit-task": [_SONNET]})

    out = reconcile(tasks, log, capsys)

    assert "hit-rate: 1/2" in out
    assert "hit" in out and "miss" in out
    # The rationale is echoed on the miss — that is what a wrong prediction
    # teaches — and not on the hit, where it would only be noise.
    assert "every decision is stated" in out
    assert "one planted decision" not in out


def test_reconcile_v1_reports_an_unswept_prediction_instead_of_dropping_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A task missing from the logs is not a miss and not a hit: it is unswept,
    and it stays out of the hit-rate denominator while staying on the page."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "swept-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="p"))
    write_task(tasks, "never-run-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="p"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [t for t in loaded if t.id == "swept-task"],
              {"swept-task": [_SONNET]})

    out = reconcile(tasks, log, capsys)

    assert "never-run-task" in out
    assert "unswept" in out
    assert "hit-rate: 1/1" in out
    assert "1 swept, 1 unswept" in out


def test_reconcile_v1_leaves_a_rung_incomplete_when_a_model_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sonnet resolved but haiku never ran: the task is either haiku-solvable
    or sonnet-only and the log cannot say which, so the rung is withheld rather
    than guessed, and the prediction is not scored against a guess."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "half-swept-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="p"))
    write_task(tasks, "other-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="p"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"half-swept-task": [_SONNET]}, models=(_SONNET,))

    out = reconcile(tasks, log, capsys)

    assert "incomplete" in out
    assert _HAIKU in out  # the missing model is named
    assert "hit-rate: 0/0" in out


def test_reconcile_v1_names_a_task_resolved_by_haiku_haiku_solvable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "easy-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="p"))
    write_task(tasks, "hard-task", construction=constructed(
        "K9", "single", "unsolved", pair="p"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"easy-task": [_HAIKU, _SONNET]})

    out = reconcile(tasks, log, capsys)

    predictions = out.split("1. prediction reconciliation")[1].split("2. knob")[0]
    [easy] = [line for line in predictions.splitlines() if "easy-task" in line]
    [hard] = [line for line in predictions.splitlines() if "hard-task" in line]
    assert easy.split() == ["easy-task", "haiku-solvable", "haiku-solvable", "hit"]
    assert hard.split() == ["hard-task", "unsolved", "unsolved", "hit"]
    assert "hit-rate: 2/2" in out


# --- section 2: knob grouping against the baseline -----------------------------


def test_reconcile_v1_groups_a_knob_by_level_against_the_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "wordcount-top-words")  # frozen baseline id, no block
    write_task(tasks, "spans-subtract-gaps")
    write_task(tasks, "open-l1", construction=constructed(
        "K1", "acceptance", "haiku-solvable", family="open"))
    write_task(tasks, "open-l2", construction=constructed(
        "K1", "description", "sonnet-only", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "wordcount-top-words": [_HAIKU, _SONNET],
        "spans-subtract-gaps": [_HAIKU, _SONNET],
        "open-l1": [_HAIKU, _SONNET],
        "open-l2": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    assert "K1" in out
    assert "acceptance" in out and "description" in out
    # The baseline of the same category is on the page as the comparison row.
    assert "baseline" in out and "feature-dev" in out
    # Per-model resolved counts per level: acceptance 1/1 haiku, description 0/1.
    assert "1/1" in out and "0/1" in out


def test_reconcile_v1_compares_a_knob_only_against_its_own_category(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refactor knob is read against refactor baselines. Pooling the
    feature-dev controls in would compare across capability-matrix cells,
    which is what the taxonomy exists to stop."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "wordcount-top-words")  # feature-dev baseline
    write_task(tasks, "metrics-dispatch-table", category="refactor")
    write_task(tasks, "net-task", category="refactor", construction=constructed(
        "K8", "misleading", "sonnet-only"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "wordcount-top-words": [_HAIKU, _SONNET],
        "metrics-dispatch-table": [_HAIKU, _SONNET],
        "net-task": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    k8_block = out.split("K8")[1].split("\n\n")[0]
    assert "refactor" in k8_block
    assert "feature-dev" not in k8_block


# --- section 3: family ladders -------------------------------------------------


def test_reconcile_v1_calls_a_family_monotonic_along_its_ladder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """K8's ladder runs covered -> partial -> bare -> misleading, which is not
    alphabetical order, so a family listed in ladder order can only have been
    ordered by the ladder."""
    tasks = tmp_path / "tasks"
    for level, rung in (("covered", "haiku-solvable"), ("bare", "sonnet-only"),
                        ("misleading", "unsolved")):
        write_task(tasks, f"net-{level}", construction=constructed(
            "K8", level, rung, family="net"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "net-covered": [_HAIKU, _SONNET],
        "net-bare": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    ladder = family_block(out)
    assert "monotonic along the ladder: yes" in ladder
    assert ladder.index("net-covered") < ladder.index("net-bare")
    assert ladder.index("net-bare") < ladder.index("net-misleading")


def test_reconcile_v1_reports_a_family_that_goes_backwards_down_the_ladder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The opener spec variant turned out easier than the tighter one — the
    finding a family exists to surface, so it is named, not smoothed over."""
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "open-acceptance": [_SONNET],
        "open-description": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    assert "monotonic along the ladder: no" in family_block(out)


def test_reconcile_v1_cannot_judge_monotonicity_of_an_unswept_family(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    write_task(tasks, "wordcount-top-words")
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [t for t in loaded if t.id == "wordcount-top-words"],
              {"wordcount-top-words": [_HAIKU]})

    out = reconcile(tasks, log, capsys)

    assert "monotonic along the ladder: unknown" in family_block(out)


# --- section 4: crux/control pairs ---------------------------------------------


def test_reconcile_v1_reports_the_rung_delta_of_a_pair(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="thing"))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "crux-task": [_SONNET],
        "control-task": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    pairs = out.split("crux/control pairs")[1]
    assert "thing" in pairs
    assert "crux-task" in pairs and "control-task" in pairs
    assert "+1 rung" in pairs


def test_reconcile_v1_reports_a_pair_the_crux_did_not_move(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="thing"))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "crux-task": [_HAIKU, _SONNET],
        "control-task": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    assert "no rung delta" in out.split("crux/control pairs")[1]


def test_reconcile_v1_names_the_pair_whose_control_came_out_harder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The pair isolated nothing — the zero-crux control was the harder task.
    Reported in words, because a bare negative sign is easy to read past."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="thing"))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "crux-task": [_HAIKU, _SONNET],
        "control-task": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    assert "-1 rung (control harder)" in out.split("crux/control pairs")[1]


def test_reconcile_v1_names_no_crux_in_a_pair_on_an_unenumerated_ladder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """K7's levels are recorded as the author wrote them rather than enumerated
    into a ladder, so "dense" sorting before "sparse" is the alphabet and not a
    difficulty order. Reading a crux off it would let the report accuse a
    working pair of failing to isolate what it was built to isolate — so this
    pair gets its two levels and two rungs, and no claim about which of them
    should have been higher."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "terrain-dense", construction=constructed(
        "K7", "dense", "sonnet-only", pair="terrain"))
    write_task(tasks, "terrain-sparse", construction=constructed(
        "K7", "sparse", "haiku-solvable", pair="terrain"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"terrain-sparse": [_HAIKU, _SONNET]})

    out = reconcile(tasks, log, capsys)

    pairs = pairs_block(out)
    assert "harder" not in pairs
    assert not re.search(r"[+-]\d+ rung", pairs)  # no delta, in either direction
    # Both members stay on the page, with their level and their rung.
    [dense] = [line for line in pairs.splitlines() if "terrain-dense" in line]
    [sparse] = [line for line in pairs.splitlines() if "terrain-sparse" in line]
    assert dense.split() == ["terrain", "terrain-dense", "K7=dense", "unsolved"]
    assert sparse.split() == [
        "terrain", "terrain-sparse", "K7=sparse", "haiku-solvable"
    ]


# --- section 5: no-separation flags and the kill discipline --------------------
#
# The counting rule is the one registered in section 9 of the design note and
# amended there for round 3: a round advances a knob's counter only where it
# put the knob to a registered contrast — a family or pair varying it, or an
# effort claim registered on it — separation is read only in the harder
# direction, and a registered claim that hit counts as the knob speaking.
# Everything a knob's level is read against the frozen baseline for is still
# printed, labelled informational, and advances nothing.


def flags_block(out: str) -> str:
    """Section 5 alone — or, handed one knob's block of it, that block. Split
    on the last header rather than the first so the three helpers here compose:
    a per-knob assertion reads the same counted/informational split a
    whole-report one does."""
    return out.split("5. no-separation flags")[-1].split("6. effort-claim")[0]


def knob_blocks(out: str) -> list[str]:
    """Section 5's per-knob blocks, without the criterion prose above them.

    The prose says what "separated" and "no separation" mean, in those words,
    so an assertion that did not drop it would pass on the definition of the
    verdict it was looking for rather than on the verdict."""
    return [
        block for block in flags_block(out).split("\n\n")
        if re.match(r"^ +K\d+ ", block)
    ]


def knob_block(out: str, knob: str) -> str:
    """One knob's block of section 5, counted rows and informational alike."""
    [block] = [
        block for block in knob_blocks(out)
        if block.lstrip().startswith(f"{knob}  ")
    ]
    return block


def counted_block(out: str) -> str:
    """The rows the kill discipline reads, without the informational ones.

    Split on the label rather than by indentation: "separated" and "no
    separation" appear on both sides of it, so an unscoped assertion would
    pass on a row that advances no counter — which is the whole distinction
    these tests exist to hold."""
    return "\n".join(
        block.split("informational, advancing no counter:")[0]
        for block in knob_blocks(out)
    )


def informational_block(out: str) -> str:
    return "\n".join(
        block.split("informational, advancing no counter:")[1]
        for block in knob_blocks(out)
        if "informational, advancing no counter:" in block
    )


def test_reconcile_v1_flags_a_knob_whose_levels_did_not_separate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description", "intent"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded})

    out = reconcile(tasks, log, capsys)

    flags = out.split("no-separation flags")[1]
    assert "K1" in flags and "no separation" in counted_block(out)
    assert "silent round(s): 1" in flags


def test_reconcile_v1_does_not_flag_a_knob_whose_levels_separated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "open-acceptance": [_HAIKU, _SONNET],
        "open-description": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    flags = out.split("no-separation flags")[1]
    assert "separated" in counted_block(out)
    assert "silent round(s): 0" in flags


def write_single_level_knob_against_an_earlier_baseline(tmp_path: Path) -> Path:
    """A standalone knob task swept a round after the baseline it is read
    against, which is the only shape a knob with no contrast can ever have: a
    cell is swept once, so the zero-knob controls cannot be re-run beside a
    knob added later. This is K8's shape and K7's and K11's — the three knobs
    the round-3 amendment reclassifies."""
    tasks = tmp_path / "tasks"
    # A frozen zero-knob baseline id, so it counts as a control.
    write_task(tasks, "ledger-split-formatting", category="refactor")
    write_task(tasks, "net-misleading", category="refactor",
               construction=constructed("K8", "misleading", "unsolved"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "round-1.jsonl",
              [task for task in loaded if task.id == "ledger-split-formatting"],
              {"ledger-split-formatting": [_HAIKU, _SONNET]}, as_of=date(2026, 8, 4))
    write_log(logs / "round-2.jsonl",
              [task for task in loaded if task.id == "net-misleading"], {},
              as_of=date(2026, 9, 1))
    return logs


def test_reconcile_v1_prints_a_frozen_baseline_comparison_as_informational(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The widest reading of where a level landed is still on the page.

    K8's one level lands a rung above the frozen baseline it is read against,
    which the report has always printed and should go on printing: it is the
    only reading a knob with no contrast has. What it may no longer do is
    count. The zero-knob controls were swept once, in an earlier round,
    against tasks nobody built to be read against this level, so the row is
    labelled and the counter does not move for it."""
    logs = write_single_level_knob_against_an_earlier_baseline(tmp_path)

    main(["reconcile-v1", "--tasks", str(tmp_path / "tasks"), "--replay", str(logs)])

    out = capsys.readouterr().out
    informational = informational_block(out)
    assert "2026-09-01  separated —" in informational
    assert "misleading {unsolved} vs baseline {haiku-solvable}" in informational
    # Round 1 swept no K8 task at all, so it is not a round K8 was read in.
    assert "2026-08-04" not in flags_block(out)
    # Nothing on the counting side, and the tail says why rather than reading
    # as a knob that was asked and stayed quiet.
    assert "separated" not in counted_block(out)
    assert "silent round(s): 0" in flags_block(out)
    assert "stalled: no round put K8 to a registered contrast" in flags_block(out)


def test_reconcile_v1_will_not_demote_a_knob_off_frozen_baseline_silence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The counting rule, on the shape that would otherwise demote a knob
    nobody ever tested.

    Two rounds, two standalone K8 tasks, each landing exactly where the frozen
    baseline landed. Under the direction-blind rule that read the baseline as
    a comparison, that is two silent rounds and a demotion. Under the amended
    rule neither round put K8 to a registered contrast — no family, no pair,
    no registered claim — so neither round counts, and a knob that was never
    asked is stalled rather than silent. Demoting it would be reading a
    verdict off evidence nobody collected."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "ledger-split-formatting", category="refactor")
    for index in (1, 2):
        write_task(tasks, f"net-misleading-{index}", category="refactor",
                   construction=constructed("K8", "misleading", "haiku-solvable"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "round-0.jsonl",
              [task for task in loaded if task.id == "ledger-split-formatting"],
              {"ledger-split-formatting": [_HAIKU, _SONNET]}, as_of=date(2026, 8, 4))
    for index, as_of in ((1, date(2026, 9, 1)), (2, date(2026, 10, 1))):
        swept = [task for task in loaded if task.id == f"net-misleading-{index}"]
        write_log(logs / f"round-{index}.jsonl", swept,
                  {task.id: [_HAIKU, _SONNET] for task in swept}, as_of=as_of)

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    flags = flags_block(out)
    assert "3 round(s)" in out
    # Both rounds are read, and both readings are informational.
    assert "2026-09-01  no separation" in informational_block(out)
    assert "2026-10-01  no separation" in informational_block(out)
    assert "silent round(s): 0" in flags
    assert "demote K8" not in flags


def test_reconcile_v1_counts_a_registered_contrast_and_names_the_one_that_spoke(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """What the counter does read: a family varying one knob, whose harder
    level landed above its easier one. The row names the contrast, because a
    demotion argued from this section has to say which comparison it was
    read off."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "open-acceptance", construction=constructed(
        "K1", "acceptance", "haiku-solvable", family="open"))
    write_task(tasks, "open-intent", construction=constructed(
        "K1", "intent", "sonnet-only", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "open-acceptance": [_HAIKU, _SONNET],
        "open-intent": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert (
        "separated — family open: intent {sonnet-only} above "
        "acceptance {haiku-solvable}"
    ) in counted
    assert "silent round(s): 0" in flags_block(out)


def test_reconcile_v1_will_not_read_separation_in_the_easier_direction(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """K11's round-2 flag, moved inside a registered contrast where it can be
    read at all.

    The harder level came out uniformly easier than the level below it. The
    two sets differ, and the direction-blind criterion this replaced called
    that separation — which is how a knob commissioned to push tasks up was
    credited for pushing one down. A knob separates only upward, so this is
    silence, and it is the round's whole verdict."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "open-acceptance", construction=constructed(
        "K1", "acceptance", "unsolved", family="open"))
    write_task(tasks, "open-intent", construction=constructed(
        "K1", "intent", "unsolved", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"open-intent": [_HAIKU, _SONNET]})

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    # The sets differ — {unsolved} against {haiku-solvable} — and the harder
    # level is the one holding the lower rung.
    assert "acceptance {unsolved}" in counted and "intent {haiku-solvable}" in counted
    assert "no separation" in counted and "separated —" not in counted
    assert "silent round(s): 1" in flags_block(out)


def test_reconcile_v1_reads_an_effort_claim_hit_as_the_knob_speaking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The round-3 amendment's third clause, on the shape it was written for.

    The pair's rungs never moved, so on rungs alone this round is silent. The
    crux registered a cost claim against its partner before the run and the
    claim hit, which is the knob saying something on the axis it was
    registered against — effort is where this experiment's signal has actually
    shown up, and a knob judged only on rungs is judged on an outcome its
    author never bet on."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "haiku-solvable", pair="thing",
        effort=claim("pair", "cost", 1.25)))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (7, 0.60), _SONNET: (7, 0.21)},
        "control-task": {_HAIKU: (7, 0.20), _SONNET: (7, 0.21)},
    })

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert "no rung delta" in pairs_block(out)
    assert (
        "non-silent — 1 of 2 registered effort reading(s) hit "
        "(0 of 1 registered contrast(s) separated)"
    ) in counted
    assert "silent round(s): 0" in flags_block(out)


def test_reconcile_v1_counts_the_round_of_a_registered_claim_that_missed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """K11's shape: no contrast, but four registered baseline claims.

    Registration is what makes the round count. The author named a
    comparator, a metric and a factor before the run and the measurement came
    in under it, so the knob was asked and answered nothing — which is
    silence, and is the difference between K11 and K7, whose tasks register
    nothing and can sit where they are forever."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "checkout-discount-codes")
    write_task(tasks, "net-far", construction=constructed(
        "K11", "far", "haiku-solvable", effort=claim("baseline", "cost", 1.2)))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "round-1.jsonl",
              [task for task in loaded if task.id == "checkout-discount-codes"],
              {"checkout-discount-codes": [_HAIKU, _SONNET]}, as_of=date(2026, 8, 4),
              effort={"checkout-discount-codes": {_HAIKU: (7, 0.20), _SONNET: (7, 0.20)}})
    write_log(logs / "round-2.jsonl",
              [task for task in loaded if task.id == "net-far"],
              {"net-far": [_HAIKU, _SONNET]}, as_of=date(2026, 9, 1),
              effort={"net-far": {_HAIKU: (7, 0.21), _SONNET: (7, 0.21)}})

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    counted = counted_block(out)
    assert "2026-09-01  no separation" in counted
    assert "0 of 2 registered effort reading(s) hit" in counted
    assert "silent round(s): 1" in flags_block(out)
    assert "stalled" not in knob_block(out, "K11")


def test_reconcile_v1_will_not_read_a_contrast_on_an_unenumerated_ladder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Direction needs a ladder to be a direction along. Where the design note
    has not enumerated the knob's levels, neither member of the contrast is
    the harder one — the same reason section 4 names no crux in such a pair —
    so the contrast is not assessable and the round stays uncounted rather
    than being scored on an alphabetical order nobody registered."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "net-dense", construction=constructed(
        "K7", "dense", "sonnet-only", pair="terrain"))
    write_task(tasks, "net-calm", construction=constructed(
        "K7", "calm", "haiku-solvable", pair="terrain"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"net-calm": [_HAIKU, _SONNET], "net-dense": [_SONNET]})

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert "not assessable — none of 1 registered contrast(s) readable" in counted
    assert "pair terrain: K7's ladder is not enumerated" in counted
    assert "silent round(s): 0" in flags_block(out)


def write_pair_declaring_different_knobs(tmp_path: Path) -> Path:
    """A pair whose control never declares the knob its crux varies: both
    members write K1 at the same level and only the crux turns K9.

    The two tests below are the two halves of one rule — the lint refuses this
    shape, and reconciliation says so accurately where a replayed artifact
    carries one anyway — so they read it off one fixture."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="terrain", also={"K1": "acceptance"}))
    write_task(tasks, "control-task", construction=constructed(
        "K1", "acceptance", "haiku-solvable", pair="terrain"))
    return tasks


def test_reconcile_v1_will_not_read_a_contrast_whose_control_never_declares_the_knob(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shape the task-set lint refuses, read here as what it is.

    Both members write K1 at the same level and only the crux turns K9, so K9
    has one side and nothing on the ladder opposite it. The crux landed a rung
    above the control, and that is still not an upward separation: the control
    is not at the bottom of K9's ladder, it is off it, and K9's bottom rung
    (`none`, the zero-crux control) already means no crux was planted — so
    reading the two as separated would call two states that mean the same
    thing apart on whichever way the noise fell.

    What the row owes the shape is an accurate refusal. Naming the member that
    does not declare the knob is that; "K9's ladder is not enumerated" is not,
    since K9's ladder is enumerated in the design note this rule lives in.
    """
    tasks = write_pair_declaring_different_knobs(tmp_path)
    log = tmp_path / "runs.jsonl"
    write_log(log, firstparty_v1.load_task_set(tasks), {
        "crux-task": [_SONNET], "control-task": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert "not assessable — none of 1 registered contrast(s) readable" in counted
    assert (
        "pair terrain: control-task does not declare K9 — a shape the task-set "
        "lint refuses"
    ) in counted
    assert "separated —" not in counted
    assert "silent round(s): 0" in flags_block(out)


def test_the_lint_refuses_the_shape_that_row_is_written_for(tmp_path: Path) -> None:
    """The other half: the pair the test above reads is one no lint-clean task
    set can hold, so that row is for artifacts replayed from before the lint
    and for sets assembled by hand, and never for a set a sweep was paid on."""
    tasks = write_pair_declaring_different_knobs(tmp_path)

    problems = firstparty_v1.lint_task_set(firstparty_v1.load_task_set(tasks))

    assert [
        problem for problem in problems if "do not set the same knob(s)" in problem
    ]


def test_reconcile_v1_does_not_count_a_contrast_that_varies_two_knobs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pair moving two knobs at once attributes its rungs to neither, so it
    is nobody's registered contrast and neither knob is counted off it. The
    rung delta is not attributed either, and for the same reason."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="terrain", also={"K1": "intent"}))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="terrain", also={"K1": "acceptance"}))
    log = tmp_path / "runs.jsonl"
    write_log(log, firstparty_v1.load_task_set(tasks), {
        "crux-task": [_SONNET], "control-task": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    for knob in ("K1", "K9"):
        block = knob_block(out, knob)
        assert f"stalled: no round put {knob} to a registered contrast" in block
        assert "silent round(s): 0" in block


def test_reconcile_v1_scores_a_baseline_claim_on_a_composite_to_no_knob(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One cost claim over three knobs names none of them.

    A composite varies all three from the baseline at once, so a single
    baseline claim cannot say which one moved the money — and reading it as a
    round for each would advance three counters off one measurement. The task
    is still swept, still graded, and still shows up on the informational
    rows; what it does not do is count."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "checkout-discount-codes")
    write_task(tasks, "composite-task", construction=constructed(
        "K1", "intent", "unsolved", also={"K9": "single", "K7": "dense"},
        effort=claim("baseline", "cost", 1.25)))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "round-1.jsonl",
              [task for task in loaded if task.id == "checkout-discount-codes"],
              {"checkout-discount-codes": [_HAIKU, _SONNET]}, as_of=date(2026, 8, 4),
              effort={"checkout-discount-codes": {_HAIKU: (7, 0.20), _SONNET: (7, 0.20)}})
    write_log(logs / "round-2.jsonl",
              [task for task in loaded if task.id == "composite-task"], {},
              as_of=date(2026, 9, 1),
              effort={"composite-task": {_HAIKU: (9, 0.90), _SONNET: (9, 0.90)}})

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    # The claim is graded and hits — section 6 says so on every row it wrote —
    # and still moves nothing. The hit is the point: a claim that came out
    # false would leave the three counters alone on its own merits.
    graded = [
        line for line in out.split("6. effort-claim")[1].splitlines()
        if "composite-task" in line
    ]
    assert graded and all(line.split()[-1] == "hit" for line in graded)
    for knob in ("K1", "K7", "K9"):
        block = knob_block(out, knob)
        assert f"stalled: no round put {knob} to a registered contrast" in block
        assert "silent round(s): 0" in block


def test_reconcile_v1_reports_a_round_of_unreadable_claims_as_not_assessable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Silence needs a reading that could have spoken.

    The claim is registered against a category baseline the sweep never ran,
    so neither of its readings can be assessed at all. A round that got a
    readable answer out of nothing said nothing about the knob, and rendering
    its unreadable readings as "0 of 2 hit" would put an assessed miss on the
    page where no measurement exists to have missed."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "net-far", construction=constructed(
        "K11", "far", "haiku-solvable", effort=claim("baseline", "cost", 1.2)))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {"net-far": [_HAIKU, _SONNET]},
              effort={"net-far": {_HAIKU: (7, 0.21), _SONNET: (7, 0.21)}})

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert "not assessable — no registered contrast" in counted
    assert "none of 2 registered effort reading(s) assessable" in counted
    assert "hit" not in counted
    assert "silent round(s): 0" in flags_block(out)


def test_reconcile_v1_will_not_read_silence_off_an_unbalanced_contrast(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The minimum-sample guard, turned in the counting side's direction.

    Three tasks at the easier level spread across two rungs; the harder level
    got one. The one cell is read against the maximum of three draws, so its
    failure to stand above them is an unbalanced sample as much as a quiet
    knob — not the evidence a demotion is argued from."""
    tasks = tmp_path / "tasks"
    for index in (1, 2, 3):
        write_task(tasks, f"open-acceptance-{index}", construction=constructed(
            "K1", "acceptance", "haiku-solvable", family="open"))
    write_task(tasks, "open-intent", construction=constructed(
        "K1", "intent", "unsolved", family="open"))
    log = tmp_path / "runs.jsonl"
    write_log(log, firstparty_v1.load_task_set(tasks), {
        "open-acceptance-1": [_HAIKU, _SONNET],
        "open-acceptance-2": [_HAIKU, _SONNET],
        "open-acceptance-3": [_SONNET],
        "open-intent": [_HAIKU, _SONNET],
    })

    out = reconcile(tasks, log, capsys)

    counted = counted_block(out)
    assert "not assessable — none of 1 registered contrast(s) readable" in counted
    assert (
        "intent has 1 graded task(s) against acceptance's 2 distinct rung(s), "
        "so its silence would be the sample as much as the knob"
    ) in counted
    assert "silent round(s): 0" in flags_block(out)


# Three frozen zero-knob ids, so they count as controls, and one per rung of
# the ladder: a baseline landing on all three rungs is what a small level
# cannot reproduce, and it is what the checked-in refactor baseline does.
_SPANNING_BASELINE = {
    "ledger-split-formatting": [_HAIKU, _SONNET],
    "exporters-pull-up-base-class": [_SONNET],
    "gradebook-split-compute-from-format": [],
}


def write_baseline_spanning_the_ladder(tasks: Path) -> None:
    for task_id in _SPANNING_BASELINE:
        write_task(tasks, task_id, category="refactor")


def write_baseline_log(log: Path, loaded: list[firstparty_v1.Task]) -> None:
    """The round that swept those controls, a round before the knob's own."""
    write_log(
        log,
        [task for task in loaded if task.id in _SPANNING_BASELINE],
        {task_id: models for task_id, models in _SPANNING_BASELINE.items() if models},
        as_of=date(2026, 8, 4),
    )


def test_reconcile_v1_will_not_read_separation_off_a_level_too_small_to_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The minimum-sample guard, on the shape that produced K7's round-1 flag.

    One swept cell lands on one rung, so a level of one can never reproduce a
    three-rung baseline whatever its run does: the sets differ by arithmetic
    and not because the knob moved anything. The guard rides along on the
    informational row, which is the only place a frozen-baseline comparison is
    printed now — and where it was never allowed to be read as silence either,
    since a knob whose only comparison was unreadable has not been shown to
    move nothing.
    """
    tasks = tmp_path / "tasks"
    write_baseline_spanning_the_ladder(tasks)
    write_task(tasks, "net-dense", category="refactor",
               construction=constructed("K7", "dense", "sonnet-only"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_baseline_log(logs / "round-1.jsonl", loaded)
    write_log(logs / "round-2.jsonl",
              [task for task in loaded if task.id == "net-dense"],
              {"net-dense": [_HAIKU, _SONNET]}, as_of=date(2026, 9, 1))

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    [verdict] = [
        line for line in informational_block(out).splitlines() if line.strip()
    ]
    assert "not assessable" in verdict
    assert "dense {haiku-solvable} vs baseline " in verdict
    assert "dense has 1 graded task(s) against (baseline)'s 3 distinct rung(s)" in verdict
    assert "silent round(s): 0" in flags_block(out)


def test_reconcile_v1_still_reads_a_level_sampled_as_deeply_as_the_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The guard has to leave a real comparison alone. Three cells could have
    landed on the baseline's three rungs and did not, so their agreeing on one
    rung is a result rather than an arithmetic consequence — this is the shape
    of K1's four-per-level contrast, which the guard must not touch."""
    tasks = tmp_path / "tasks"
    write_baseline_spanning_the_ladder(tasks)
    for index in (1, 2, 3):
        write_task(tasks, f"net-dense-{index}", category="refactor",
                   construction=constructed("K7", "dense", "sonnet-only"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_baseline_log(logs / "round-1.jsonl", loaded)
    write_log(
        logs / "round-2.jsonl",
        [task for task in loaded if task.id.startswith("net-")],
        {task.id: [_HAIKU, _SONNET] for task in loaded if task.id.startswith("net-")},
        as_of=date(2026, 9, 1),
    )

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    [verdict] = [
        line for line in informational_block(out).splitlines() if line.strip()
    ]
    assert "separated —" in verdict and "not assessable" not in verdict


def test_reconcile_v1_guards_two_levels_of_one_knob_against_each_other(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The guard is on the comparison, not on the baseline: two levels read
    against each other inside one round are guarded the same way, and one
    believable difference among several is enough to call the knob separated.

    Here acceptance and description each land on one rung and differ, which
    one cell each is enough to show; intent spans two rungs, which neither of
    them could have reproduced. The knob separated, on the pair that could.

    These four tasks declare no family and no pair, so this is the
    informational reading throughout — which is the point of keeping the
    guard on it: the widest view of a knob is still the view a reader gets
    when no contrast has been authored yet, and it should not be wrong.
    """
    tasks = tmp_path / "tasks"
    write_task(tasks, "open-acceptance",
               construction=constructed("K1", "acceptance", "haiku-solvable"))
    write_task(tasks, "open-description",
               construction=constructed("K1", "description", "sonnet-only"))
    for index in (1, 2):
        write_task(tasks, f"open-intent-{index}",
                   construction=constructed("K1", "intent", "unsolved"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {
        "open-acceptance": [_HAIKU, _SONNET],
        "open-description": [_SONNET],
        "open-intent-1": [_HAIKU, _SONNET],
        "open-intent-2": [_SONNET],
    })

    out = reconcile(tasks, log, capsys)

    [verdict] = [
        line for line in informational_block(out).splitlines() if line.strip()
    ]
    assert "separated —" in verdict
    assert "silent round(s): 0" in flags_block(out)


def test_reconcile_v1_demotes_a_knob_silent_for_two_rounds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The pre-registered kill discipline, counted rather than remembered: two
    as-of dates are two sweeps, and a knob silent in both has run out of rope.

    The second round sweeps a second family rather than re-running the first —
    a cell is only ever swept once, which is why re-reading the same tasks is
    not what "two sweeps" can mean here.
    """
    tasks = tmp_path / "tasks"
    for family in ("open", "wide"):
        for level in ("acceptance", "description"):
            write_task(tasks, f"{family}-{level}", construction=constructed(
                "K1", level, "haiku-solvable", family=family))
    loaded = firstparty_v1.load_task_set(tasks)
    rounds = {
        date(2026, 8, 4): [t for t in loaded if t.id.startswith("open-")],
        date(2026, 9, 1): [t for t in loaded if t.id.startswith("wide-")],
    }
    logs = tmp_path / "logs"
    for index, (as_of, swept) in enumerate(sorted(rounds.items()), start=1):
        write_log(logs / f"round-{index}.jsonl", swept,
                  {task.id: [_HAIKU, _SONNET] for task in swept}, as_of=as_of)

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert "2 round(s)" in out
    assert "silent round(s): 2" in out
    # The demotion names the rounds it counted: it travels out of this report
    # into the design note, and a demotion that does not say which sweeps went
    # silent cannot be checked against them.
    assert (
        "demote K1: silent in as-of 2026-08-04, as-of 2026-09-01 — 2 round(s) "
        "against the 2 the kill discipline allows"
    ) in out


def test_reconcile_v1_dates_the_sweeps_a_demotion_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sweep id says nothing about when it ran, so the demote line carries
    the date alongside it. Round-1's own demotion was argued from which sweeps
    ran and when, off a report that printed neither."""
    tasks = tmp_path / "tasks"
    for family in ("open", "wide"):
        for level in ("acceptance", "description"):
            write_task(tasks, f"{family}-{level}", construction=constructed(
                "K1", level, "haiku-solvable", family=family))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    sweeps = [("round-one", date(2026, 8, 4), "open-"),
              ("round-two", date(2026, 9, 1), "wide-")]
    for sweep, as_of, stem in sweeps:
        swept = [task for task in loaded if task.id.startswith(stem)]
        write_log(logs / f"{sweep}.jsonl", swept,
                  {task.id: [_HAIKU, _SONNET] for task in swept},
                  as_of=as_of, sweep=sweep)

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert (
        "demote K1: silent in sweep round-one (2026-08-04), "
        "sweep round-two (2026-09-01) — 2 round(s)"
    ) in out


# --- rounds: keyed on the sweep id, falling back to the as-of date -------------


def test_reconcile_v1_counts_two_sweeps_of_one_calendar_day_as_two_rounds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Why the sweep id exists at all. Round 1's two sweeps both carried
    2026-08-05, so the kill discipline read them as one round and no knob
    could run out of rope on the evidence it actually had. Keyed on the sweep
    the same rows are two rounds, and a knob silent in both is demoted."""
    tasks = tmp_path / "tasks"
    for family in ("open", "wide"):
        for level in ("acceptance", "description"):
            write_task(tasks, f"{family}-{level}", construction=constructed(
                "K1", level, "haiku-solvable", family=family))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    for sweep, stem in (("round-2-a", "open"), ("round-2-b", "wide")):
        swept = [task for task in loaded if task.id.startswith(f"{stem}-")]
        write_log(logs / f"{sweep}.jsonl", swept,
                  {task.id: [_HAIKU, _SONNET] for task in swept},
                  as_of=date(2026, 8, 5), sweep=sweep)

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert "2 round(s): sweep round-2-a, sweep round-2-b" in out
    assert "2 keyed on a sweep id" in out
    flags = out.split("5. no-separation flags")[1]
    assert "K1  sweep round-2-a  no separation" in flags
    assert "K1  sweep round-2-b  no separation" in flags
    assert "silent round(s): 2" in flags
    assert "demote K1" in flags


def test_reconcile_v1_keeps_one_sweep_that_spilled_across_midnight_as_one_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The mirror of the bug the sweep id fixes: a long sweep whose rows land
    on two dates is still one sweep, and counting it twice would spend a
    knob's kill-discipline rope on a clock."""
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    for index, task in enumerate(loaded):
        write_log(logs / f"part-{index}.jsonl", [task],
                  {task.id: [_HAIKU, _SONNET]},
                  as_of=date(2026, 8, 5 + index), sweep="round-2")

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert "1 round(s): sweep round-2" in out
    assert "silent round(s): 1" in out


def test_reconcile_v1_keys_a_round_on_its_as_of_date_when_no_run_names_a_sweep(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every checked-in log predates the field, so the fallback is the common
    case and not a corner. The round is the as-of date, labelled as such: a
    reader counting rounds has to see that the weaker key was the one
    available."""
    tasks = tmp_path / "tasks"
    for level in ("acceptance", "description"):
        write_task(tasks, f"open-{level}", construction=constructed(
            "K1", level, "haiku-solvable", family="open"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded},
              as_of=date(2026, 8, 5))

    out = reconcile(tasks, log, capsys)

    assert "1 round(s): as-of 2026-08-05" in out
    assert "1 keyed on an as-of date; no run carries a sweep id" in out
    assert "K1  as-of 2026-08-05  no separation" in out.split(
        "5. no-separation flags")[1]


def test_reconcile_v1_names_both_keyings_when_the_logs_are_mixed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A legacy log and a sweep-tagged one in one report, which is what every
    report looks like from round 2 on. Each run keys on its own sweep id where
    it has one and on its as-of date where it does not, and the header says
    how many rounds came from each — a round count that silently mixed the two
    mechanisms would be the same unreadable number the sweep id replaced."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "ledger-split-formatting", category="refactor")
    write_task(tasks, "net-misleading", category="refactor",
               construction=constructed("K8", "misleading", "unsolved"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "legacy.jsonl",
              [task for task in loaded if task.id == "ledger-split-formatting"],
              {"ledger-split-formatting": [_HAIKU, _SONNET]},
              as_of=date(2026, 8, 4))
    write_log(logs / "round-2.jsonl",
              [task for task in loaded if task.id == "net-misleading"], {},
              as_of=date(2026, 9, 1), sweep="round-2")

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert "2 round(s): as-of 2026-08-04, sweep round-2" in out
    assert "1 keyed on a sweep id, 1 on an as-of date" in out
    # K8 is standalone, so its round reads on the informational side — which is
    # still keyed and labelled the same way, and is what this is checking.
    [verdict] = [
        line for line in informational_block(out).splitlines() if line.strip()
    ]
    assert "sweep round-2  separated —" in verdict
    assert "misleading {unsolved} vs baseline {haiku-solvable}" in verdict


def test_reconcile_v1_says_so_when_there_is_no_run_to_key_a_round_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A task set whose sweep has not run yet: no round, and the keying line
    says why rather than printing a bare zero that reads like a broken key."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "open-acceptance", construction=constructed(
        "K1", "acceptance", "haiku-solvable", family="open"))
    log = tmp_path / "runs.jsonl"
    write_log(log, [], {})

    out = reconcile(tasks, log, capsys)

    assert "0 round(s)" in out
    assert "(no swept run to key a round on)" in out


def test_reconcile_v1_reads_every_log_in_a_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first sweep is split across two files; a directory keeps the demo a
    single command as more sweeps land."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "one-task", construction=constructed(
        "K9", "single", "sonnet-only", pair="p"))
    write_task(tasks, "two-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="p"))
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    for task in loaded:
        write_log(logs / f"{task.id}.jsonl", [task],
                  {task.id: [_HAIKU, _SONNET]})

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    assert "2 swept, 0 unswept" in out


# --- section 6: effort claims --------------------------------------------------


def write_effort_pair(tasks: Path) -> None:
    """A planted crux claiming to cost 1.5x the turns of the control built
    beside it.

    Only the crux registers the claim: the control is what it is read against,
    and a control claiming to cost more than the crux would be a different
    experiment.
    """
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "haiku-solvable", pair="thing",
        effort=claim("pair", "turns", 1.5),
    ))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))


def test_reconcile_v1_scores_an_effort_claim_that_came_true(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The crux cost exactly the 1.5x it was registered at, on both models.

    Exactly, rather than comfortably: the claim is a minimum, so the boundary
    is the case a reader would have to guess about otherwise."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (15, 0.30), _SONNET: (15, 0.30)},
        "control-task": {_HAIKU: (10, 0.20), _SONNET: (10, 0.20)},
    })

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "hit-rate: 2/2 assessed (100.0%); 0 not assessable" in effort
    rows = [line.split() for line in effort.splitlines() if "crux-task" in line]
    # The hit rows name what they were read against, the same way a miss does:
    # "1.50x" is a multiple of something, and the row says of what.
    assert rows == [
        ["crux-task", _HAIKU, "turns", ">=", "1.5x", "pair", "control-task",
         "10", "15", "1.50x", "hit"],
        ["crux-task", _SONNET, "turns", ">=", "1.5x", "pair", "control-task",
         "10", "15", "1.50x", "hit"],
    ]
    # The control registered no claim, so it is scored nowhere — it appears
    # only as the thing the crux's rows were read against, never as a row of
    # its own.
    assert not [line for line in effort.splitlines()
                if line.split()[:1] == ["control-task"]]


def test_reconcile_v1_echoes_the_claim_an_effort_miss_was_registered_under(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missed effort claim teaches the same way a missed rung does, so the
    bet is echoed beside what it was read against — and the comparator is
    named, because 1.2x of what is the whole question."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (12, 0.30), _SONNET: (12, 0.30)},
        "control-task": {_HAIKU: (10, 0.20), _SONNET: (10, 0.20)},
    })

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "hit-rate: 0/2 assessed (0.0%)" in effort
    assert "misses, with the claim that was registered for them:" in effort
    assert f"crux-task ({_HAIKU}):" in effort
    assert (
        "claimed turns at least 1.5x control-task, which measured 10; it "
        "spent 12 (1.20x)"
    ) in " ".join(effort.split())


def test_reconcile_v1_prints_the_factor_the_claim_was_registered_at(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A factor a rounding format would round away, printed whole.

    1.5000001 shown as "1.5" beside a ratio of "1.50x" reads as a claim that
    was met and scored a miss, so the section would be arguing with itself
    about a number it had rounded itself. The claim is a bet, and a report
    that rounds the bet reports one nobody registered.
    """
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "haiku-solvable", pair="thing",
        effort=claim("pair", "turns", 1.5000001),
    ))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (15, 0.30), _SONNET: (15, 0.30)},
        "control-task": {_HAIKU: (10, 0.20), _SONNET: (10, 0.20)},
    })

    effort = " ".join(effort_block(reconcile(tasks, log, capsys)).split())

    assert "turns >= 1.5000001x pair" in effort
    assert "turns >= 1.5x pair" not in effort
    # And in the miss echo, where the same factor is spelt out in words.
    assert "claimed turns at least 1.5000001x control-task" in effort


def test_reconcile_v1_reads_a_baseline_effort_claim_against_its_own_category(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The other comparator: the mean over the zero-knob baseline controls of
    the task's own category. The feature-dev control is deliberately expensive
    — pooled in it would swamp the mean, and it is the taxonomy's job that it
    is not."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "ledger-split-formatting", category="refactor")
    write_task(tasks, "exporters-pull-up-base-class", category="refactor")
    write_task(tasks, "wordcount-top-words")  # feature-dev, and far pricier
    write_task(tasks, "net-task", category="refactor", construction=constructed(
        "K8", "misleading", "haiku-solvable",
        effort=claim("baseline", "cost", 2.0),
    ))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "ledger-split-formatting": {_HAIKU: (7, 0.10), _SONNET: (7, 0.10)},
        "exporters-pull-up-base-class": {_HAIKU: (7, 0.20), _SONNET: (7, 0.20)},
        "wordcount-top-words": {_HAIKU: (7, 5.00), _SONNET: (7, 5.00)},
        "net-task": {_HAIKU: (7, 0.25), _SONNET: (7, 0.25)},
    })

    effort = effort_block(reconcile(tasks, log, capsys))

    [row] = [line for line in effort.splitlines()
             if line.split()[:2] == ["net-task", _HAIKU]]
    assert " ".join(row.split()) == (
        f"net-task {_HAIKU} cost >= 2.0x baseline "
        "the refactor baseline (mean of 2) $0.1500 $0.2500 1.67x miss"
    )
    # The mean's denominator travels with the miss: two controls, not three.
    assert "the refactor baseline (mean of 2)" in " ".join(effort.split())


def test_reconcile_v1_scores_an_effort_claim_separately_per_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One claim, two readings. Round 1's effort contrasts moved by different
    multiples on the two models — K9's turns 1.80x on haiku against 1.36x on
    sonnet — so a claim collapsed to one verdict would average away exactly
    the thing it is about."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (20, 0.30), _SONNET: (11, 0.30)},
        "control-task": {_HAIKU: (10, 0.20), _SONNET: (10, 0.20)},
    })

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "hit-rate: 1/2 assessed (50.0%)" in effort
    scored = {
        line.split()[1]: line.split()
        for line in effort.splitlines()
        if line.split()[:1] == ["crux-task"] and line.split()[-1] in ("hit", "miss")
    }
    assert scored[_HAIKU][-2:] == ["2.00x", "hit"]
    assert scored[_SONNET][-2:] == ["1.10x", "miss"]


def test_reconcile_v1_will_not_assess_a_claim_whose_comparator_was_not_swept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The crux ran and the control did not, so there is no multiple to take.
    Reading the absent control as cheap would manufacture the claim's own
    conclusion out of a sweep that never happened."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task for task in loaded if task.id == "crux-task"],
              {"crux-task": [_HAIKU, _SONNET]},
              effort={"crux-task": {_HAIKU: (20, 0.30), _SONNET: (20, 0.30)}})

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "hit-rate: 0/0 assessed (n/a); 2 not assessable" in effort
    assert "not assessable, with what was missing:" in effort
    assert f"control-task has no {_HAIKU} run" in effort
    assert f"control-task has no {_SONNET} run" in effort


def test_reconcile_v1_will_not_assess_a_claim_on_a_task_that_was_not_swept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The mirror case: the comparator is there and the claiming task is not."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task for task in loaded if task.id == "control-task"],
              {"control-task": [_HAIKU, _SONNET]})

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "2 not assessable" in effort
    assert f"crux-task has no {_HAIKU} run" in effort


def test_reconcile_v1_will_not_assess_a_claim_on_the_model_the_comparator_missed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Half-swept comparators are the normal shape of a sweep that died
    part-way, and they leave one model readable and the other not. The claim
    is scored on the model both sides ran and withheld on the other."""
    tasks = tmp_path / "tasks"
    write_effort_pair(tasks)
    loaded = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "crux.jsonl",
              [task for task in loaded if task.id == "crux-task"],
              {"crux-task": [_HAIKU, _SONNET]},
              effort={"crux-task": {_HAIKU: (20, 0.30), _SONNET: (20, 0.30)}})
    write_log(logs / "control.jsonl",
              [task for task in loaded if task.id == "control-task"],
              {"control-task": [_HAIKU]}, models=(_HAIKU,),
              effort={"control-task": {_HAIKU: (10, 0.20)}})

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])
    effort = effort_block(capsys.readouterr().out)

    assert "hit-rate: 1/1 assessed (100.0%); 1 not assessable" in effort
    assert f"control-task has no {_SONNET} run" in effort


def test_reconcile_v1_will_not_assess_a_baseline_claim_with_no_such_control(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A claim read against a category the zero-knob baseline does not cover.
    The lint refuses this before a sweep; the report's job is to say what is
    missing rather than to fall back on some other category's controls."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "wordcount-top-words")  # a feature-dev control
    write_task(tasks, "bug-task", category="bug-fix", construction=constructed(
        "K9", "single", "haiku-solvable",
        effort=claim("baseline", "turns", 1.5),
    ))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded})

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "2 not assessable" in effort
    assert f"no bug-fix zero-knob baseline control has a {_HAIKU} run" in effort


def test_reconcile_v1_will_not_assess_a_claim_against_a_comparator_of_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A comparator that measured nothing is not a comparator: no multiple of
    zero is anything, so a claim read against it is unreadable rather than
    met by whatever the task spent. Reachable only on cost — a run log's
    turns are at least one by schema — and it is what keeps the ratio the
    report prints well defined."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "haiku-solvable", pair="thing",
        effort=claim("pair", "cost", 2.0),
    ))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "crux-task": {_HAIKU: (7, 0.30), _SONNET: (7, 0.30)},
        "control-task": {_HAIKU: (7, 0.0), _SONNET: (7, 0.0)},
    })

    effort = effort_block(reconcile(tasks, log, capsys))

    assert "hit-rate: 0/0 assessed (n/a); 2 not assessable" in effort
    assert f"control-task measured 0 cost on {_HAIKU}" in effort
    # And the legend lists it beside the other three causes, so a reader meets
    # it before the row that hit it rather than only in the row's own reason.
    assert "or a comparator that measured zero" in " ".join(effort.split())


def test_reconcile_v1_says_when_no_effort_claim_is_registered_at_all(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Round 1's task set, and every task set before effort was registrable.
    The section says so rather than vanishing: a section that disappears when
    it has nothing to report cannot be told from one that broke."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "crux-task", construction=constructed(
        "K9", "single", "haiku-solvable", pair="thing"))
    write_task(tasks, "control-task", construction=constructed(
        "K9", "none", "haiku-solvable", pair="thing"))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded})

    effort = effort_block(reconcile(tasks, log, capsys))

    assert effort.strip() == "(no effort claim registered in the task set)"


def test_reconcile_v1_renders_effort_claims_byte_identically_twice_over(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same reason as the whole-report determinism test, on the section that
    walks pairs and baselines: both are built out of dictionaries, and an
    iteration order leaking into the page would show up as churn in a report
    that is read by diffing."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "ledger-split-formatting", category="refactor")
    write_task(tasks, "exporters-pull-up-base-class", category="refactor")
    write_effort_pair(tasks)
    write_task(tasks, "net-task", category="refactor", construction=constructed(
        "K8", "misleading", "haiku-solvable",
        effort=claim("baseline", "cost", 2.0),
    ))
    loaded = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, loaded, {task.id: [_HAIKU, _SONNET] for task in loaded}, effort={
        "ledger-split-formatting": {_HAIKU: (7, 0.10), _SONNET: (7, 0.10)},
        "exporters-pull-up-base-class": {_HAIKU: (9, 0.20), _SONNET: (9, 0.20)},
        "crux-task": {_HAIKU: (15, 0.30), _SONNET: (12, 0.30)},
        "control-task": {_HAIKU: (10, 0.20), _SONNET: (10, 0.20)},
        "net-task": {_HAIKU: (7, 0.40), _SONNET: (7, 0.25)},
    })
    argv = ["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)]

    main(argv)
    first = effort_block(capsys.readouterr().out)
    main(argv)
    assert effort_block(capsys.readouterr().out) == first

    reseeded = subprocess.run(
        [sys.executable, "-c",
         "import sys; from ai_benchmark.cli import main; main(sys.argv[1:])", *argv],
        capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONHASHSEED": "1"},
    )

    assert effort_block(reseeded.stdout) == first
    # Both comparators and both metrics are on the page, so what is being
    # pinned as stable is the whole section rather than one branch of it.
    assert "cost >= 2.0x baseline" in first and "turns >= 1.5x pair" in first
    assert "hit" in first and "miss" in first


# --- loud failures -------------------------------------------------------------


def test_reconcile_v1_rejects_an_unknown_task_id_in_a_run_log(
    tmp_path: Path
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {})
    log.write_text(log.read_text().replace("known-task", "ghost-task"))

    with pytest.raises(SystemExit, match="ghost-task"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_reconcile_v1_rejects_duplicate_runs_of_one_cell(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {})
    log.write_text(log.read_text() + log.read_text())

    with pytest.raises(SystemExit, match="duplicate"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_reconcile_v1_rejects_a_model_that_is_not_on_the_ladder(
    tmp_path: Path
) -> None:
    """A rung is named after a model tier, so a run logged under a model the
    ladder does not name has no rung — and silently dropping it would shrink a
    denominator the report is read off."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {}, models=("claude-opus-5",))

    with pytest.raises(SystemExit, match="claude-opus-5"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_reconcile_v1_rejects_runs_from_more_than_one_agent(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    logs = tmp_path / "logs"
    write_log(logs / "a.jsonl", [task], {}, agent="claude-code")
    write_log(logs / "b.jsonl", [task], {}, agent="aider")

    with pytest.raises(SystemExit, match="aider"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])


def test_reconcile_v1_rejects_a_task_that_declares_no_construction(
    tmp_path: Path
) -> None:
    """Impossible past the lint, checked anyway: a task outside the frozen
    baseline with no construction block is neither a control nor a prediction,
    and reconciliation would have to invent which."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "undeclared-task")
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {})

    with pytest.raises(SystemExit, match="undeclared-task"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_reconcile_v1_rejects_a_baseline_task_that_declares_construction(
    tmp_path: Path
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "wordcount-top-words", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {})

    with pytest.raises(SystemExit, match="wordcount-top-words"):
        main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(log)])


def test_reconcile_v1_rejects_a_replay_path_that_is_not_there(
    tmp_path: Path
) -> None:
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))

    with pytest.raises(SystemExit, match="missing.jsonl"):
        main(["reconcile-v1", "--tasks", str(tasks),
              "--replay", str(tmp_path / "missing.jsonl")])


def test_reconcile_v1_merges_nothing_into_the_dataset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The report is read-only over its inputs: it grades to get verdicts, the
    way eval-v1 --replay does, but it is not an ingest and writes no record."""
    tasks = tmp_path / "tasks"
    write_task(tasks, "known-task", construction=constructed(
        "K9", "single", "sonnet-only"))
    [task] = firstparty_v1.load_task_set(tasks)
    log = tmp_path / "runs.jsonl"
    write_log(log, [task], {"known-task": [_HAIKU, _SONNET]})
    before = sorted(path.name for path in tmp_path.rglob("*.jsonl"))

    reconcile(tasks, log, capsys)

    assert sorted(path.name for path in tmp_path.rglob("*.jsonl")) == before
    assert log.read_text().count("\n") == 2  # the two runs, nothing appended
