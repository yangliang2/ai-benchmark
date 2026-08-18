"""Round 6's pre-registration, pinned: what section 52 of the design note
commits to before the first paid Codex run.

Round 6 authors no tasks. It re-runs thirty cells of the existing corpus under
a second harness, so the whole round is a cross-agent reading and its
registration is a *list* rather than a design: which thirty, on which one
combination, under what ceiling, for how much. §46 did the same job for round
5; the shape is deliberately the same one round later.

What makes this file worth having is where it reads the list from. **The
register is the design note**, not a constant in code — the note is what a
reader of the round consults and what a reviewer holds the sweep to — so every
test below parses section 52's own fenced blocks and its own prose, and then
re-derives each claim from the task set and the checked-in run logs. A
register that drifts from the corpus it registers is the exact defect this
file exists to catch, and prose is what nothing else checks.

Two disciplines are inherited rather than re-argued. Runs are found by
scanning every log under the run-log directory and keying on
task x agent x model; **no test here selects a run log by filename**, which is
the sweep protocol's rule after the first pass of the round-1 analysis
silently dropped two paid cells that way. And eligibility is read *as of the
registration date* — a row that lands after 2026-08-18 cannot retroactively
have been available to a sample drawn on it, and pinning it that way keeps
this file a statement about round 6 rather than a tripwire for round 7.

Nothing here runs a live cell, and nothing here grades one: the round has not
been swept.
"""

import datetime as dt
import re
from collections import Counter
from pathlib import Path

import pytest

from ai_benchmark import agents, firstparty_v1, reconcile_v1

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 6 cells and cost — registered 2026-08-18"
_REGISTERED_ON = dt.date(2026, 8, 18)

_SWEEP = "round-6"
_AGENT = "codex"
_MODEL = "gpt-5.6-terra"

# The comparison side, already in the logs: the ladder round 6 does not re-run.
_LADDER = (
    ("claude-code", "claude-sonnet-5"),
    ("claude-code", "claude-haiku-4-5"),
)

# The round the twelve planted-defect cells come from, named by its sweep id
# because that is what identifies a round.
_ROUND_4 = "round-4"

# The registered flat default every one of the thirty runs under, whether by a
# registration (four categories) or by fallback (two).
_LIMIT_S = 600

# What the section claims about the pool each per-category sample was drawn
# from, and how many were taken. The pool sizes are the other half of "the
# first N by id": a sample of six from a pool of six is not a sample.
_SAMPLE = {
    "bug-fix": (6, 6),
    "fault-location": (6, 6),
    "code-review": (4, 8),
    "codebase-comprehension": (2, 4),
    "feature-dev": (6, 11),
    "refactor": (6, 11),
}


def note_section() -> str:
    """Section 52, from its heading to the next top-level one."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{_HEADING}\n")
    assert len(body) == 2, f"the note carries exactly one {_HEADING!r}"
    return body[1].split("\n## ")[0]


def prose() -> str:
    """The section with its wrapping collapsed. What a sentence says is the
    pin; where the line happens to break is not, and a pin on the break would
    fail the next time a word is added upstream of it."""
    return " ".join(note_section().split())


# A task id as the register writes it: lowercase words joined by hyphens, and
# nothing else. The section's last fenced block is the sweep's command line
# rather than a list of cells, so the blocks are told apart by their contents
# — and a block that is neither wholly ids nor wholly not is a malformed
# register rather than something to read half of.
_TASK_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def registered_ids() -> list[str]:
    """The thirty task ids, read out of the section's own fenced blocks.

    The register is the list in the note. Each listed line is one id, possibly
    followed by the action it is listed under, so the id is the first token.
    """
    ids: list[str] = []
    for block in note_section().split("```")[1::2]:
        first = [line.split()[0] for line in block.splitlines() if line.strip()]
        listed = [token for token in first if _TASK_ID.fullmatch(token)]
        if not listed:
            continue
        assert listed == first, f"a fenced block mixes ids with other lines: {first}"
        ids.extend(listed)
    return ids


@pytest.fixture(scope="module")
def tasks() -> dict[str, firstparty_v1.Task]:
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def rows() -> dict[tuple[str, str, str], firstparty_v1.Run]:
    """Every checked-in v1 run, keyed task x agent x model.

    Every log under the directory, read for its contents: a filename says
    nothing about which sweep a row belongs to, and selecting on one is what
    the sweep protocol forbids.
    """
    return {
        (run.task_id, run.agent, run.model): run
        for log in reconcile_v1.collect_logs([_LOGS])
        for run in firstparty_v1.load_runs(log)
    }


def eligible(
    tasks: dict[str, firstparty_v1.Task],
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
    category: str,
) -> list[str]:
    """The pool the section says each sample was drawn from, re-derived: this
    category's controls that already carry both ladder rows, by id.

    Read as of the registration date. A ladder row logged after the register
    was written was not available to be sampled, so counting it would make the
    pool this test checks a different pool from the one the author drew from.
    """
    return sorted(
        task_id
        for task_id, task in tasks.items()
        if task.category == category
        and firstparty_v1.is_control(task)
        and all(
            (task_id, agent, model) in rows
            and rows[(task_id, agent, model)].as_of <= _REGISTERED_ON
            for agent, model in _LADDER
        )
    )


def test_the_register_is_thirty_ids_the_task_set_actually_loads(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The first thing a register has to be: thirty real tasks, named once.

    A duplicated id would make the round twenty-nine cells while reading as
    thirty, and an id naming nothing would be a cell `--task` refuses before
    anything runs — which is the good failure, but it is one paid invocation
    later than this.
    """
    ids = registered_ids()

    assert len(ids) == 30, "the round is thirty cells"
    assert len(set(ids)) == 30, "no id is registered twice"
    unknown = sorted(set(ids) - set(tasks))
    assert not unknown, f"the register names tasks the set does not load: {unknown}"

    assert "thirty task" in prose() or "thirty cells" in prose()


def test_the_per_category_counts_are_the_categories_the_tasks_declare(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 52.1's count sentence, against what the thirty actually are.

    The counts are the shape of the round — six actions, unevenly sampled on
    purpose — and they are written in prose the sweep is planned against. A
    sentence claiming four `code-review` while the list holds five is a round
    whose per-action reading is off by one and nothing would say so.
    """
    declared = Counter(tasks[task_id].category for task_id in registered_ids())
    assert declared == {name: taken for name, (taken, _) in _SAMPLE.items()}

    counted = prose()
    for name, (taken, _) in _SAMPLE.items():
        spelled = {2: "two", 4: "four", 6: "six"}[taken]
        assert re.search(rf"\b{taken} `{name}`", counted) or re.search(
            rf"\b(?i:{spelled}) `{name}`", counted
        ), f"section 52 does not state {taken} `{name}`"


def test_round_fours_twelve_are_present_as_six_repositories_under_both_actions(
    tasks: dict[str, firstparty_v1.Task],
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """The twelve are in, and they are the contrast rather than twelve tasks.

    What makes them worth carrying into an agent round is that they are six
    starting repositories, each answered under two actions — the one contrast
    in the corpus that spans two categories over one repository. The pairing
    is discovered the way the lint's existence proof discovers it, by the
    bytes of the starting repository the two share, because a locate/fix pair
    is deliberately neither a task family nor a pair and declares no link to
    read.
    """
    registered = set(registered_ids())
    twelve = {
        run.task_id for run in rows.values() if run.sweep == _ROUND_4
    }
    assert len(twelve) == 12, "round 4 swept twelve tasks"
    assert twelve <= registered, sorted(twelve - registered)

    by_repo: dict[tuple[tuple[str, bytes], ...], set[str]] = {}
    for task_id in twelve:
        task = tasks[task_id]
        key = tuple(sorted(firstparty_v1._tree_bytes(task.repo_dir).items()))
        by_repo.setdefault(key, set()).add(task.category)

    assert len(by_repo) == 6, "the twelve are six planted-defect repositories"
    for categories in by_repo.values():
        assert categories == {"bug-fix", "fault-location"}, sorted(categories)

    assert "six planted-defect repositories" in prose()


def test_every_sampled_task_is_a_control_and_declares_no_knob(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 52.2's first filter, both halves of it.

    A control is a **declared control** or a member of the frozen zero-knob
    baseline — one implementation for the whole project, because a control is
    what every denominator is drawn from. Drawing only from them is what gives
    each Codex row a claude-code denominator in its own category, and the
    absence of a construction block is what stops the round being misread as a
    knob result it never registered a contrast for.
    """
    for task_id in registered_ids():
        task = tasks[task_id]
        assert firstparty_v1.is_control(task), task_id
        assert task.construction is None, task_id
        assert task.control or task_id in firstparty_v1.BASELINE_TASK_IDS, task_id

    baseline = set(registered_ids()) & firstparty_v1.BASELINE_TASK_IDS
    assert {tasks[task_id].category for task_id in baseline} == {
        "feature-dev", "refactor"
    }
    assert len(baseline) == 12, "the twelve frozen-22 ids are the two code samples"


def test_every_registered_cell_already_carries_both_ladder_rows(
    tasks: dict[str, firstparty_v1.Task],
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """Section 52.2's second filter: nothing is re-run on Claude this round.

    The comparison side of every cell is a row that already exists, which is
    what makes the round thirty cells rather than ninety. Selected on the row's
    own task x agent x model, over every log in the directory — never on a log
    filename.
    """
    for task_id in registered_ids():
        for agent, model in _LADDER:
            row = rows.get((task_id, agent, model))
            assert row is not None, f"{task_id} has no {agent} x {model} row"
            assert row.as_of <= _REGISTERED_ON, task_id

    # And nothing of the round's own combination is logged yet: this ticket
    # ran no sweep, so a `codex` row anywhere would mean one was run.
    assert not [
        key for key in rows if key[1] == _AGENT
    ], "no Codex row is checked in; ticket 08 runs no sweep"
    assert not [run for run in rows.values() if run.sweep == _SWEEP]


def test_the_sample_is_the_first_n_by_id_of_each_categorys_control_pool(
    tasks: dict[str, firstparty_v1.Task],
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """Section 52.2's rule, re-derived: the pool, and the prefix taken from it.

    The rule is the point rather than the ids it happens to pick. A sample
    drawn after looking at the runs is a sample somebody chose; ordering the
    eligible set by id and taking the first N is a rule that could be written
    down before the sweep, and this is the check that it was followed.
    """
    registered = set(registered_ids())
    for category, (taken, pool_size) in _SAMPLE.items():
        pool = eligible(tasks, rows, category)
        assert len(pool) == pool_size, f"{category}: pool is {len(pool)}"
        assert sorted(t for t in registered if tasks[t].category == category) == (
            pool[:taken]
        ), category

    counted = prose()
    assert "the eligible set was ordered by task id and the first N taken" in counted
    assert "eleven eligible tasks and six were taken" in counted


def test_every_cell_runs_at_six_hundred_seconds_and_nothing_new_is_registered(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 52.5: one ceiling over the round, reached two ways.

    Eighteen cells run under a registered limit and twelve under the flat
    default, and the numbers are equal — which is what keeps the round free of
    a ceiling difference between its actions *and* free of a cross-round
    caveat, since 600 is what every earlier round ran at. The distinction
    matters anyway, because only a registered category's cell can later be
    described as running "under the registered 600 s".
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension"
    }, "this ticket registers nothing new"
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}

    registered_categories = set()
    defaulted_categories = set()
    for task_id in registered_ids():
        task = tasks[task_id]
        assert firstparty_v1.live_run_limit_s(task) == _LIMIT_S, task_id
        if task.category in firstparty_v1.LIVE_RUN_LIMITS_S:
            registered_categories.add(task.category)
        else:
            defaulted_categories.add(task.category)

    assert defaulted_categories == {"feature-dev", "refactor"}
    assert registered_categories == set(firstparty_v1.LIVE_RUN_LIMITS_S)

    counted = prose()
    assert "`feature-dev` and `refactor` are **not** in that table" in counted
    assert "run under the **flat default**" in counted
    assert "**no cross-round caveat arises**" in counted


def test_the_section_registers_the_combination_the_range_and_the_sweep_id(
) -> None:
    """Sections 52.3, 52.4 and 52.6: the three things a pre-registration is for.

    One combination and no ladder, a dollar range stated before anyone spends,
    and the sweep id every invocation of the round will carry. The reasoning
    level is checked against the registry rather than only quoted, because it
    is as much a property of what was measured as the model name is.
    """
    counted = prose()

    assert agents.CODEX_REASONING_LEVELS[_MODEL] == "medium"
    assert f"`{_AGENT}` × `{_MODEL}` at reasoning `medium`" in counted
    assert "One model, **no ladder**" in counted
    assert "thirty tasks × one combination = **thirty cells**" in counted

    assert "**$5–10**" in counted
    assert "Cost, stated before anyone spends: $5–10, at list price" in counted

    assert f"Sweep id **`{_SWEEP}`**" in counted
    assert "A **dry cell first**, in its own invocation" in counted
    assert "bans `-dry` in a log's name" in counted
    assert "**`--task`**" in counted


def test_the_stated_anchor_for_the_range_is_what_the_logs_say(
    tasks: dict[str, firstparty_v1.Task],
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """Section 52.4's arithmetic: the range is anchored, not guessed.

    The anchor is the same thirty tasks' sonnet rows rather than a round's flat
    per-cell figure, because a per-cell figure averages over whichever tasks
    that round happened to hold and this one is exactly the selection about to
    be swept. Both numbers the section quotes are recomputable from the
    checked-in logs by this test.
    """
    sonnet = [
        rows[(task_id, "claude-code", "claude-sonnet-5")].cost_usd
        for task_id in registered_ids()
    ]
    total = round(sum(sonnet), 4)
    assert total == 6.2572
    assert round(total / 30, 4) == 0.2086

    counted = prose()
    assert "total **$6.2572**" in counted
    assert "$0.2086 a cell" in counted
    assert 5 < total < 10, "the anchor sits inside the registered range"


def test_the_codex_calls_that_preceded_the_registration_are_disclosed() -> None:
    """Section 52.4's disclosure paragraph, against the capture's own record.

    The anchor capture spent real Codex calls before any of this was written
    down, and the fixture's metadata names this section as where they are
    disclosed. What the disclosure has to say is that they are outside the
    round: no task run, no row written, not one of the thirty, not inside the
    range. It also has to say why a Codex dollar figure is list price at all —
    a ChatGPT-login account is not billed per token, so `cost_usd` is
    `table-derived` by construction rather than by choice.
    """
    counted = prose()

    assert "several throwaway calls" in counted
    assert "`tests/fixtures/codex/metadata.json`" in counted
    assert (
        "none of it ran a task, none of it wrote a run-log row, and none of it "
        "is one of the thirty cells or inside the $5–10 range"
    ) in counted.lower()

    assert "authenticated by **ChatGPT login**, not by an API key" in counted
    assert "not billed per token" in counted
    assert "`cost_source: table-derived`" in counted
    assert "**nothing in the pipeline changes**" in counted

    metadata = (_REPO / "tests" / "fixtures" / "codex" / "metadata.json").read_text(
        encoding="utf-8"
    )
    assert "Ticket 08's registration is the place" in metadata
