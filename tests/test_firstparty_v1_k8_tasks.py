"""The K8-misleading refactor tasks of ticket #19.

The knob they set is safety-net quality, at the level where the net is worse
than absent: each starting repository ships a test suite that is green on the
pristine code and stays green when the restructuring quietly changes
behaviour, because the behaviour it changes is the one thing that suite never
looks at. An agent that runs the tests, sees green and stops has been told the
refactor is done, and it is not.

That claim is what the probes here prove, and it takes both halves to prove
it. Each task's careless variant is the reference solution bent one way a
reader who trusted the net would plausibly bend it, and each is asserted to
pass the repository's own tests *and* to satisfy every structural assertion,
and then to grade 0.0 anyway: green net, restructuring done as asked,
behaviour gone. A probe that failed the visible tests would say nothing about
K8, because a net that catches the mistake is exactly what these tasks claim
not to have.

Every task is also probed in the opposite direction, with an answer that
restructures differently but correctly and must grade 1.0 — otherwise the
structural assertions would be describing the reference solution rather than
the change the prompt asks for.

The tasks are deliberately unlike one another, because a net that only
misleads about one shape of behaviour has not been shown to be a knob.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, doing nothing grades unresolved, scale honest to
the reference diff — plus the pre-registration the experiment rests on: these
are predicted to be harder than the refactor tasks that saturated at 100%, so
each rung is pinned here and a sweep that disagrees is a visible miss.
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from firstparty_v1_tasks import run_for, solution_diff, solved_tree, task_by_id

from ai_benchmark.firstparty_v1 import (
    GRADE_TIMEOUT_S,
    Rung,
    Task,
    _run_grading,
    evaluate,
    lint_task_set,
)

# --- the careless refactors: the restructuring done as asked, bent once ---------


def order_alert_rules_by_severity(workdir: Path) -> None:
    """The table built exactly as asked, then tidied so the loudest severity
    comes first — which drops the rule that mutes health checks below the one
    that pages on a 500."""
    alerts = workdir / "alerts.py"
    source = alerts.read_text()
    muted = '    (_is_healthcheck, "ignore"),\n'
    notice = '    (_is_client_error, "notice"),\n'
    assert muted in source
    alerts.write_text(source.replace(muted, "").replace(notice, notice + muted))


def settle_leaderboard_ties_by_name(workdir: Path) -> None:
    """The ordering rule in one place, and made a total order while it is
    being written down — so a tie is settled alphabetically rather than left
    to the order the players were entered in."""
    leaderboard = workdir / "leaderboard.py"
    source = leaderboard.read_text()
    total_only = "    return -player.total()\n"
    assert total_only in source
    leaderboard.write_text(
        source.replace(total_only, "    return (-player.total(), player.name)\n")
    )


def copy_shelving_shallowly(workdir: Path) -> None:
    """The copy given one home, spelled the way relabel already spells it —
    which is right for relabel and hands the caller's own lists to place and
    remove."""
    shelving = workdir / "shelving.py"
    source = shelving.read_text()
    per_shelf = "    return {name: list(items) for name, items in shelves.items()}\n"
    assert per_shelf in source
    shelving.write_text(source.replace(per_shelf, "    return dict(shelves)\n"))


def expire_sessions_a_second_late(workdir: Path) -> None:
    """The predicate written as the negation of the comparison it replaces,
    off by the boundary: a session whose whole allowance has gone by is still
    treated as usable."""
    expiry = workdir / "expiry.py"
    source = expiry.read_text()
    inclusive = "    return now - session.started_at >= TTL_SECONDS\n"
    assert inclusive in source
    expiry.write_text(
        source.replace(inclusive, "    return now - session.started_at > TTL_SECONDS\n")
    )


# --- the honest variants: the same restructuring, answered another way ---------


def walk_the_alert_table_with_next(workdir: Path) -> None:
    """The table built exactly as asked and walked with next() over a
    generator rather than a for loop: same rules, same order, same
    first-match rule."""
    alerts = workdir / "alerts.py"
    source = alerts.read_text()
    loop = (
        "    for matches, level in RULES:\n"
        "        if matches(event):\n"
        "            return level\n"
        '    return "ignore"\n'
    )
    assert loop in source
    alerts.write_text(
        source.replace(
            loop,
            "    return next(\n"
            "        (level for matches, level in RULES if matches(event)),\n"
            '        "ignore",\n'
            "    )\n",
        )
    )


def rank_the_leaderboard_on_a_tuple(workdir: Path) -> None:
    """The ordering rule in one place, spelled as a one-element tuple key,
    with top and rank_of asking standings for the order instead of sorting
    again — a different shape that orders players identically, ties and
    all."""
    leaderboard = workdir / "leaderboard.py"
    source = leaderboard.read_text()
    replacements = {
        "    return -player.total()\n": "    return (-player.total(),)\n",
        "    return sorted(players, key=rank_key)[:count]\n": (
            "    return standings(players)[:count]\n"
        ),
        "    ordered = sorted(players, key=rank_key)\n": (
            "    ordered = standings(players)\n"
        ),
    }
    for before, after in replacements.items():
        assert before in source
        source = source.replace(before, after)
    leaderboard.write_text(source)


def import_the_shelving_module(workdir: Path) -> None:
    """The same seam reached the other way: `import shelving` and a
    module-qualified call, rather than the reference's
    `from shelving import copied`."""
    stockroom = workdir / "stockroom.py"
    source = stockroom.read_text()
    from_import = "from shelving import copied\n"
    assert from_import in source
    stockroom.write_text(
        source.replace(from_import, "import shelving\n").replace(
            " = copied(shelves)", " = shelving.copied(shelves)"
        )
    )


def import_the_expiry_module(workdir: Path) -> None:
    """The same seam reached the other way: `import expiry` and a
    module-qualified call, with the limit re-exported by assignment rather
    than by the reference's `from expiry import TTL_SECONDS, is_expired`."""
    sessions = workdir / "sessions.py"
    source = sessions.read_text()
    from_import = "from expiry import TTL_SECONDS, is_expired\n"
    assert from_import in source
    sessions.write_text(
        source.replace(
            from_import, "import expiry\n\nTTL_SECONDS = expiry.TTL_SECONDS\n"
        ).replace("is_expired(session, now)", "expiry.is_expired(session, now)")
    )


class K8Task(NamedTuple):
    """One K8-misleading task, and what is pinned about it here.

    `touched` is the set of files the reference solution edits, `bend` is the
    careless refactor the repository's own tests do not catch, `differently`
    is an alternative correct answer to the same prompt, and `rung` is the
    pre-registered prediction.
    """

    task_id: str
    touched: frozenset[str]
    rung: Rung
    bend: Callable[[Path], None]
    differently: Callable[[Path], None]


K8_TASKS = (
    K8Task(
        task_id="alerts-rule-table",
        touched=frozenset({"alerts.py"}),
        rung="sonnet-only",
        bend=order_alert_rules_by_severity,
        differently=walk_the_alert_table_with_next,
    ),
    K8Task(
        task_id="leaderboard-extract-rank-key",
        touched=frozenset({"leaderboard.py"}),
        rung="unsolved",
        bend=settle_leaderboard_ties_by_name,
        differently=rank_the_leaderboard_on_a_tuple,
    ),
    K8Task(
        task_id="stockroom-extract-shelf-copy",
        touched=frozenset({"stockroom.py", "shelving.py"}),
        rung="sonnet-only",
        bend=copy_shelving_shallowly,
        differently=import_the_shelving_module,
    ),
    K8Task(
        task_id="sessions-extract-expiry",
        touched=frozenset({"sessions.py", "expiry.py"}),
        rung="sonnet-only",
        bend=expire_sessions_a_second_late,
        differently=import_the_expiry_module,
    ),
)

BY_TASK = [pytest.param(entry, id=entry.task_id) for entry in K8_TASKS]


def visible_tests_pass(task: Task, edit: Callable[[Path], None] | None = None) -> bool:
    """Whether the repository's own tests — the net the agent sees — pass.

    Run the way an agent would run them: plain pytest in the workdir, with
    none of the isolation grading applies, because the question here is what
    the agent is told rather than what the verdict reads.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-k8-") as name:
        workdir = Path(name)
        shutil.copytree(task.repo_dir, workdir, dirs_exist_ok=True)
        if edit is not None:
            edit(workdir)
        return (
            subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=False,
                timeout=GRADE_TIMEOUT_S,
            ).returncode
            == 0
        )


def structural_half_passes(task: Task, diff: str) -> bool:
    """Whether the structural assertions alone accept this diff, through the
    grader's own private runner — the split is not reachable through grade()."""
    structural = sorted(set(task.grading_test_paths) - set(task.behaviour_test_paths))
    return _run_grading(task, diff, structural, timeout_s=GRADE_TIMEOUT_S)


def tasks() -> list[Task]:
    return [task_by_id(entry.task_id) for entry in K8_TASKS]


# --- four refactor tasks, each declaring the one knob it sets -------------------


def test_every_task_is_a_refactor_setting_the_net_knob_alone() -> None:
    for task in tasks():
        assert task.category == "refactor"
        assert task.language == "python"
        assert task.behaviour_test_paths
        assert task.construction is not None
        assert task.construction.levels == {"K8": "misleading"}
        # Standalone tasks: a K8 family would have to vary its lever inside
        # repo/, which the family lint holds byte-identical across variants.
        assert task.construction.family is None
    assert {task.scale for task in tasks()} == {"single-file", "cross-file"}


def test_the_tasks_lint_clean() -> None:
    assert lint_task_set(tasks()) == []


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_resolves_and_doing_nothing_does_not(
    entry: K8Task,
) -> None:
    task = task_by_id(entry.task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_declared_scale_matches_the_reference_solution(entry: K8Task) -> None:
    task = task_by_id(entry.task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == set(entry.touched)
    assert task.scale == ("single-file" if len(entry.touched) == 1 else "cross-file")


# --- the misleading net ---------------------------------------------------------


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_repository_starts_out_green(entry: K8Task) -> None:
    """Misleading, not broken: the net an agent inherits passes, which is what
    makes trusting it the reasonable thing to do."""
    assert visible_tests_pass(task_by_id(entry.task_id))


@pytest.mark.parametrize("entry", BY_TASK)
def test_the_reference_solution_keeps_the_repository_green(entry: K8Task) -> None:
    assert visible_tests_pass(
        task_by_id(entry.task_id), solved_tree(task_by_id(entry.task_id))
    )


@pytest.mark.parametrize("entry", BY_TASK)
def test_a_careless_refactor_stays_green_and_still_grades_unresolved(
    entry: K8Task,
) -> None:
    """The K8-misleading probe, and the reason both halves are asserted here.

    The bent solution restructures exactly as the prompt asks — every
    structural assertion passes — and the repository's own tests go on
    passing, so nothing the agent can see says anything is wrong. Only the
    held-out behaviour tests do, and they are what makes the verdict 0.0.
    """
    task = task_by_id(entry.task_id)
    diff = solution_diff(task, mutate=entry.bend)

    assert visible_tests_pass(task, solved_tree(task, entry.bend))
    assert structural_half_passes(task, diff)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 0.0


@pytest.mark.parametrize("entry", BY_TASK)
def test_an_alternative_correct_restructuring_still_resolves(entry: K8Task) -> None:
    """The probe pointing the other way, and what keeps the structural
    assertions from being a description of the reference solution rather than
    of the change asked for: an answer that restructures differently but
    correctly must still grade 1.0.

    For the two cross-file tasks the variant deliberately picks the import
    form the reference does not — module-qualified where the reference uses
    `from X import Y` — because a seam assertion that replaces the function
    at runtime is most easily written around one form and then silently
    grades the other zero.
    """
    task = task_by_id(entry.task_id)
    diff = solution_diff(task, mutate=entry.differently)

    [record] = evaluate([task], [run_for(task, diff)], source="run-log")

    assert record.quality_value == 1.0


# --- pre-registered predictions -------------------------------------------------


def test_the_registered_rungs_are_the_k8_claim() -> None:
    """Pinned so the claim cannot be reinterpreted once the sweep is in. The
    refactor tasks these are answering to were solved by every rung; nothing
    here is registered haiku-solvable, because a task whose net misleads and
    whose easiest rung still solves it has not moved the knob."""
    registered = {
        task.id: task.construction.prediction.rung
        for task in tasks()
        if task.construction is not None
    }

    assert registered == {entry.task_id: entry.rung for entry in K8_TASKS}
    assert "haiku-solvable" not in registered.values()


def test_every_prediction_says_why_the_net_is_what_makes_it_hard() -> None:
    """A rationale is what a missed prediction teaches, and for K8 what it has
    to teach is which visible test was expected to stay green."""
    for task in tasks():
        assert task.construction is not None
        rationale = task.construction.prediction.rationale
        assert len(rationale.split()) >= 15
        assert any(word in rationale for word in ("test", "visible", "repo"))
