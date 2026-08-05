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
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "knobs": [{"id": knob, "level": level}],
        "prediction": {"rung": rung, "rationale": rationale},
    }
    if family is not None:
        block["family"] = family
    if pair is not None:
        block["pair"] = pair
    return block


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
    models: tuple[str, ...] = (_HAIKU, _SONNET),
    agent: str = "claude-code",
) -> None:
    """A raw run log sweeping `tasks` with `models`.

    `resolved_by` names, per task id, the models whose run solved it; every
    other model logs the empty diff, which grades unresolved because the
    grading tests fail on the pristine repository.
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
                    cost_usd=0.21,
                    latency_s=64.5,
                    turns=7,
                    as_of=as_of,
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


# --- the demo: the checked-in sweeps against the checked-in task set ----------


def test_reconcile_v1_reports_the_checked_in_sweeps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command's reason to exist, run on real artifacts: round 1 swept the
    22 zero-knob baseline tasks and round 2 swept every Track-A constructed
    one, so those predictions are scored against an observed rung.

    What this pins is what a later round can only add to. A cell is swept once
    and a log is only ever appended to, so a task that carries a verdict here
    carries it for good — where the counts of tasks, rounds and scored
    predictions all move as soon as the next sweep lands, and pinning them
    would make this test a running total to be edited rather than a claim
    about the report."""
    main(checked_in_argv())

    out = capsys.readouterr().out
    assert "22 zero-knob baseline" in out
    for log in ("2026-08-04.jsonl", "2026-08-04-resume.jsonl",
                "2026-08-05-dry.jsonl", "2026-08-05-haiku.jsonl",
                "2026-08-05-haiku-resume.jsonl", "2026-08-05-sonnet.jsonl"):
        assert f"data/first-party-v1-runs/{log}" in out
    assert re.search(r"hit-rate: \d+/\d+ scored", out)

    # Every constructed task is on the page rather than vanishing, swept or
    # not — an unswept one keeps its row (asserted on a fixture next to this,
    # where a sweep cannot come along and settle it).
    for constructed_id in ("settleup-settle-debts", "alerts-rule-table",
                           "billing-split-by-weight-l3",
                           "pysm-remember-substate-history"):
        assert constructed_id in out
    # The Track-A tasks are scored: predicted and observed rung, then a
    # verdict, rather than the `unswept` their rows read before round 2.
    for swept_id in ("settleup-settle-debts", "alerts-rule-table",
                     "billing-split-by-weight-l3"):
        assert re.search(
            rf"^ +{swept_id} +\S+ +\S+ +(hit|miss)$", out, re.MULTILINE
        ), f"{swept_id} is swept and should carry a scored verdict"

    # The baseline is on the page as every knob's comparison row, and round 1
    # swept all of it: no baseline row has a task it did not sweep.
    grouping = out.split("2. knob grouping")[1].split("3. family ladders")[0]
    rows = [line for line in grouping.splitlines() if "(baseline)" in line]
    assert rows
    for row in rows:
        _, category, tasks_in_row, swept, *_ = row.split()
        assert tasks_in_row == swept, f"{category} baseline not fully swept: {row}"


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
    assert "K1" in flags and "no separation" in flags
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
    assert "separated" in flags
    assert "silent round(s): 0" in flags


def test_reconcile_v1_reads_a_single_level_knob_against_an_earlier_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The knob's one level was swept a round after the baseline was, which is
    the only shape a single-level knob can ever have: a cell is swept once, so
    the zero-knob controls cannot be re-run beside a knob added later. The
    levels are read within the round and the controls across all of them, or
    K8 — the one knob whose ladder has a single level in the set — would read
    "not assessable" in every round from the second on.
    """
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

    main(["reconcile-v1", "--tasks", str(tasks), "--replay", str(logs)])

    out = capsys.readouterr().out
    flags = out.split("5. no-separation flags")[1]
    [verdict] = [line for line in flags.splitlines() if line.startswith("   K8")]
    assert "2026-09-01  separated —" in verdict
    assert "misleading {unsolved} vs baseline {haiku-solvable}" in verdict
    # Round 1 swept no K8 task at all, so it is not a round K8 was silent in.
    assert "2026-08-04" not in flags
    assert "silent round(s): 0" in flags


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
    assert "demote" in out


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
