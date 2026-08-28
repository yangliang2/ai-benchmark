"""Round 7's pre-registration, pinned: what section 59 of the design note
commits to before the first paid TypeScript run.

Round 7 authors fourteen tasks in a second language and sweeps them under
three combinations. Its registration is therefore both a *list* — which
fourteen, on which three combinations, under what ceiling, for how much — and
a *coverage target*, because the round's acceptance is a figure read off the
lint rather than a task count somebody remembers. §46 did the list job for
round 5 and §52 for round 6; the shape here is deliberately theirs, one round
on.

What makes this file worth having is where it reads the list from. **The
register is the design note**, not a constant in code — the note is what a
reader of the round consults and what a reviewer holds the sweep to — so every
test below parses section 59's own fenced blocks and its own prose, and then
re-derives each claim from the task set, from the lint's coverage table and
from the checked-in run logs. A register that drifts from the corpus it
registers is the exact defect this file exists to catch, and prose is what
nothing else checks.

Two disciplines are inherited rather than re-argued. Runs are found by
scanning every log under the run-log directory and keying on
task x agent x model; **no test here selects a run log by filename**, which is
the sweep protocol's rule after the first pass of the round-1 analysis
silently dropped two paid cells that way. And the round's cost anchor is
recomputed from round 6's rows rather than quoted, because a registration
whose arithmetic cannot be re-derived is a number somebody wrote down.

Nothing here runs a live cell, and nothing here grades one: the round has not
been swept, and the last test says so by looking for the sweep id.
"""

import re
from collections import Counter
from pathlib import Path

import pytest

from ai_benchmark import agents, firstparty, firstparty_v1, pricing, reconcile_v1

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 7 cells and cost — registered 2026-08-20"

_SWEEP = "round-7"

# The three combinations the round registers: the ladder, plus the column
# round 6 opened. Written agent-first because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the per-cell cost anchor comes from, named by its sweep id because
# that is what identifies a round. It is the only round in the corpus that has
# priced all three of the above over one task selection.
_ANCHOR_ROUND = "round-6"

# The one number in force for every cell, reached two ways: a registration for
# four categories and the flat default for the other two.
_LIMIT_S = 600

# What the section claims the round is, per action.
_COUNTS = {
    "bug-fix": 3,
    "fault-location": 3,
    "feature-dev": 3,
    "refactor": 3,
    "code-review": 2,
}

# The coverage target, worded as the lint's table can actually print it: five
# `typescript` x `application` rows and nothing else in that language.
_TYPESCRIPT_ROWS = {
    (category, "application", "typescript", count)
    for category, count in _COUNTS.items()
}

# The Python side of the same table, which this round does not touch. It reads
# 123 rather than round 7's 113 because later rounds authored into the Python
# column — round 8's three `test-authoring` tasks, round 10's three
# `investigation` ones, round 11's three `requirement-decomposition` ones,
# round 12's first explain-style `codebase-comprehension` one; §59.8's own
# prose, quoted below, is a claim about what round 7 did and stays at 113.
_PYTHON_TOTAL = 123


def note_section() -> str:
    """Section 59, from its heading to the next top-level one."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{_HEADING}\n")
    assert len(body) == 2, f"the note carries exactly one {_HEADING!r}"
    return body[1].split("\n## ")[0]


def prose() -> str:
    """The section with its wrapping collapsed. What a sentence says is the
    pin; where the line happens to break is not, and a pin on the break would
    fail the next time a word is added upstream of it."""
    return " ".join(note_section().split())


# One line of the register: a task id — lowercase words joined by hyphens —
# alone or followed by a parenthesised note on the scenario. Three of the
# section's fenced blocks are not lists of cells (the sweep's command line and
# the coverage table it targets), and the coverage table's own first column is
# a category name shaped exactly like a task id, so the line as a whole is
# what tells a register block from the rest. A block that is neither wholly
# register lines nor wholly not is a malformed register rather than something
# to read half of.
_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\(.+\))?$")


def registered_ids() -> list[str]:
    """The fourteen task ids, read out of the section's own fenced blocks.

    The register is the list in the note.
    """
    ids: list[str] = []
    for block in note_section().split("```")[1::2]:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        listed = [
            match.group(1)
            for line in lines
            if (match := _REGISTER_LINE.fullmatch(line)) is not None
        ]
        if not listed:
            continue
        assert len(listed) == len(lines), (
            f"a fenced block mixes register lines with other lines: {lines}"
        )
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


def anchor_rows(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> dict[tuple[str, str], list[firstparty_v1.Run]]:
    """Round 6's cells, per combination: the anchor §59.4 prices from.

    The round is found by its sweep id on the Codex rows, and the two Claude
    rows of each of those tasks are then looked up by task x agent x model.
    That is the same selection §52 registered and §54 reported, re-derived
    here rather than re-listed, so this file needs no copy of the thirty ids.
    """
    swept = sorted(
        key[0] for key, run in rows.items() if run.sweep == _ANCHOR_ROUND
    )
    assert len(swept) == 30, "round 6 swept thirty cells"
    return {
        (agent, model): [rows[(task_id, agent, model)] for task_id in swept]
        for agent, model in _COMBINATIONS
    }


def test_the_register_is_fourteen_ids_the_task_set_actually_loads(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The first thing a register has to be: fourteen real tasks, named once.

    A duplicated id would make the round thirteen tasks while reading as
    fourteen, and an id naming nothing would be a cell `--task` refuses before
    anything runs — which is the good failure, but it is one paid invocation
    later than this.
    """
    ids = registered_ids()

    assert len(ids) == 14, "the round is fourteen tasks"
    assert len(set(ids)) == 14, "no id is registered twice"
    unknown = sorted(set(ids) - set(tasks))
    assert not unknown, f"the register names tasks the set does not load: {unknown}"

    counted = prose()
    assert "fourteen tasks × three combinations = forty-two cells" in counted
    assert "**This list is the register.**" in counted


def test_the_per_action_counts_are_the_categories_the_tasks_declare(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 59.1's count sentence, against what the fourteen actually are.

    The counts are the shape of the round — five actions, three of them at
    three tasks and one at two — and they are written in prose the sweep is
    planned against and the coverage target is read against. A sentence
    claiming three `code-review` while the list holds two is a round whose
    per-action reading is off by one and nothing else would say so.
    """
    declared = Counter(tasks[task_id].category for task_id in registered_ids())
    assert declared == _COUNTS

    counted = prose()
    for name, count in _COUNTS.items():
        assert re.search(rf"\b{count} `{name}`", counted), (
            f"section 59 does not state {count} `{name}`"
        )


def test_every_registered_task_is_a_typescript_application_control(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 59.2, all three halves of it.

    A **declared control** with no construction block is what gives each cell
    a category baseline to be read against and what stops the round being
    misread as a knob result it never registered a contrast for. The language
    and the surface are the other two claims: the round widens *scenario* in
    one language on one surface, and a task in the register declaring
    otherwise would be a cell no reading of the round covers.
    """
    for task_id in registered_ids():
        task = tasks[task_id]
        assert task.language == "typescript", task_id
        assert task.surface == "application", task_id
        assert firstparty_v1.is_control(task), task_id
        assert task.control is True, task_id
        assert task.construction is None, task_id
        assert task_id not in firstparty_v1.BASELINE_TASK_IDS, task_id

    # The fourteen are every TypeScript task there is: a fifteenth outside the
    # register would be a task the round authored and does not sweep.
    typescript = {
        task_id for task_id, task in tasks.items() if task.language == "typescript"
    }
    assert typescript == set(registered_ids())

    counted = prose()
    assert "each is a **declared control**" in counted
    assert "moves no knob's counter" in counted
    assert "Nothing is re-run in Python, and nothing was ported from it" in counted


def test_every_cell_runs_at_six_hundred_seconds_and_nothing_new_is_registered(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 59.5: one ceiling over the round, reached two ways.

    Eight tasks per combination run under a registered limit and six under the
    flat default, and the numbers are equal — which is what keeps the round
    free of a ceiling difference between its actions *and* free of a
    cross-round caveat, since 600 is what every earlier round ran at. The
    distinction matters anyway, because only a registered category's cell can
    later be described as running "under the registered 600 s".

    The language claim is the one this round adds: `live_run_limit_s` is keyed
    on category alone, so the same table answers for both languages and no
    cell gets a longer run because of its toolchain.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == {
        "bug-fix", "fault-location", "code-review", "codebase-comprehension"
    }, "this ticket registers nothing new"
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S, "the flat default is the same number"

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
    assert registered_categories == {"bug-fix", "fault-location", "code-review"}

    # The same category answers the same number whatever language it is in:
    # the Python task of a registered category and the TypeScript one of the
    # same category resolve to one limit, because the key is the category.
    for category in _COUNTS:
        limits = {
            firstparty_v1.live_run_limit_s(task)
            for task in tasks.values()
            if task.category == category
        }
        assert limits == {_LIMIT_S}, category

    counted = prose()
    assert "`feature-dev` and `refactor` are **not** in that table" in counted
    assert "run under the **flat default**" in counted
    assert "the limit comes out of the same table for every language" in counted
    assert "**no cell gets a longer run because of its toolchain**" in counted
    assert "**no cross-round caveat arises**" in counted


def test_the_section_registers_the_three_combinations_and_the_sweep_id() -> None:
    """Sections 59.3 and 59.6: what is swept, and how it is invoked.

    Three combinations, not one and not two, and this is the first task round
    to carry the Codex column — round 6's cells were a re-run of tasks the
    ladder had already answered. The reasoning level is checked against the
    registry rather than only quoted, because it is as much a property of what
    was measured as the model name is.
    """
    counted = prose()

    assert agents.CODEX_REASONING_LEVELS["gpt-5.6-terra"] == "medium"
    assert (
        "`claude-code` × `claude-haiku-4-5`, `claude-code` × `claude-sonnet-5`, "
        "and `codex` × `gpt-5.6-terra` at reasoning `medium`"
    ) in counted
    assert "**this is the first task round to carry the Codex column**" in counted

    assert f"Sweep id **`{_SWEEP}`**" in counted
    assert "A **dry cell first**, in its own invocation" in counted
    assert "**one paid run rather than forty**" in counted
    assert "bans `-dry` in a log's name" in counted
    assert "**`--task`**" in counted
    assert f"--sweep {_SWEEP}" in counted


def test_the_cost_range_is_derived_from_round_sixs_per_cell_figures(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """Section 59.4's arithmetic, recomputed from the rows it claims to read.

    The anchor is round 6's spend on all three combinations over one task
    selection, which is the only place the corpus prices this round's whole
    grid. Every figure the section quotes for it — the three per-cell dollars,
    their sum, and the fourteen-task total — is re-derived here from the logs,
    because a registration whose arithmetic cannot be reproduced is a number
    somebody wrote down rather than an estimate anybody can check.
    """
    anchor = anchor_rows(rows)
    per_cell = {
        combination: round(sum(run.cost_usd for run in runs) / len(runs), 4)
        for combination, runs in anchor.items()
    }
    assert per_cell == {
        ("claude-code", "claude-haiku-4-5"): 0.0783,
        ("claude-code", "claude-sonnet-5"): 0.2086,
        ("codex", "gpt-5.6-terra"): 0.0717,
    }

    per_task = round(sum(per_cell.values()), 4)
    assert per_task == 0.3586
    assert round(per_task * 14, 2) == 5.02

    counted = prose()
    assert "**$0.0783** a cell on `claude-haiku-4-5`" in counted
    assert "**$0.2086** on `claude-sonnet-5`" in counted
    assert "**$0.0717** on `codex` × `gpt-5.6-terra`" in counted
    assert "**$0.3586 — about $0.36 — a task across the three combinations**" in counted
    assert "come to **about $5** if TypeScript cost what Python did" in counted
    assert "**$6–15**" in counted
    assert "Cost, stated before anyone spends: $6–15, at list price" in counted
    assert "fresh scenario types" in counted
    assert "a toolchain the corpus has not exercised at all" in counted


def test_the_registered_bound_is_caching_aware_at_both_ends(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """Section 59.4's two bounds, against the price table and round 6's tokens.

    Round 6 missed its range 2.3× low by pricing every input token as uncached,
    which put the registration on the round's upper bound. The fix is in the
    estimate, so this round registers the Codex column at both ends — and the
    check that it is a *fix* rather than a sentence about one is that the
    all-uncached total lands inside the registered range instead of at its
    floor. Both ends are recomputed here from the checked-in price table and
    from the token counts round 6's own rows carry.
    """
    anchor = anchor_rows(rows)
    codex = anchor[("codex", "gpt-5.6-terra")]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == (3892528, 49636)

    prices = pricing.load_price_table(
        _REPO / "data" / "price-table.json"
    ).models["gpt-5.6-terra"]
    projected_in = tokens_in / len(codex) * 14
    projected_out = tokens_out / len(codex) * 14
    assert round(projected_in) == 1816513
    assert round(projected_out) == 23163

    output_cost = projected_out * prices.output_per_token
    uncached = projected_in * prices.input_uncached_per_token
    cached = projected_in * prices.input_cached_per_token
    assert round(output_cost, 4) == 0.2780
    assert round(uncached, 4) == 3.6330
    assert round(cached, 4) == 0.3633
    assert (round(cached + output_cost, 2), round(uncached + output_cost, 2)) == (
        0.64, 3.91
    )

    # The Claude columns are projected from the per-cell figures §54 published
    # and §59.4 quotes, not from an unrounded re-sum: the section's arithmetic
    # is what a reader can redo, and a reader has the rounded cents.
    claude_per_cell = [
        round(sum(run.cost_usd for run in anchor[combination]) / 30, 4)
        for combination in _COMBINATIONS[:2]
    ]
    assert [round(figure * 14, 4) for figure in claude_per_cell] == [1.0962, 2.9204]
    claude = round(sum(figure * 14 for figure in claude_per_cell), 4)
    assert claude == 4.0166
    low = round(claude + cached + output_cost, 2)
    high = round(claude + uncached + output_cost, 2)
    assert (low, high) == (4.66, 7.93)
    assert 6 <= high <= 15, (
        "the all-uncached bound must sit inside the registered range rather "
        "than at its floor — pricing the round at its upper bound is round 6's "
        "error"
    )

    counted = prose()
    assert "Round 6 missed its range 2.3× low" in counted
    assert "The fix is in the estimate, not in the stance" in counted
    assert "**3,892,528** input tokens and wrote **49,636**" in counted
    assert "**$0.64 all-cached to $3.91 all-uncached**" in counted
    assert "**$4.66 all-cached to $7.93 all-uncached**" in counted
    assert "The two Claude columns are **vendor-reported**" in counted
    assert "**$4.0166** together" in counted
    assert "**The one way this round misses low is registered here too**" in counted

    # And the stance itself, unchanged: a ChatGPT-login account is not metered,
    # so the Codex figure is an equivalent and never an invoice.
    assert "authenticated by **ChatGPT login**, not by an API key" in counted
    assert "**not billed per token**" in counted
    assert "**list-price equivalent**" in counted
    assert "`cost_source: table-derived`" in counted


def test_the_coverage_target_is_what_the_lint_prints(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """Section 59.8, against `coverage_table` itself.

    Acceptance is a figure off the lint, so the figure has to be one the lint
    can print. The table carries a row per populated (category, surface,
    language) plus a `(category, "-", "-", 0)` row only for a category with no
    task in *any* language, which is why `codebase-comprehension` prints only
    its Python row: TypeScript's absence from a populated category is disclosed
    by absence and by this section, never by a row. Pinning that is what stops
    the lint quietly growing a registered-zero-per-language column and moving
    every earlier record suite's printed table.

    `test-authoring` was round 7's example of the zero row and is round 8's
    example of the other half of the same rule: the round authored Python tasks
    for it, so it prints a Python row and no TypeScript one (§67.2), exactly as
    `codebase-comprehension` does. The zero shape is still pinned, on the
    categories that still have no task in any language.
    """
    table = firstparty_v1.coverage_table(list(tasks.values()))

    typescript = {row for row in table if row[2] == "typescript"}
    assert typescript == _TYPESCRIPT_ROWS

    zeros = {row[0] for row in table if row[1:] == ("-", "-", 0)}
    assert "performance-optimisation" in zeros, (
        "no task in any language, so it prints as 0"
    )
    assert "test-authoring" not in zeros
    # The row's shape, not round 8's figure: what that count reads is pinned
    # once, off the printed page, in tests/test_cli.py.
    assert [row[:3] for row in table if row[0] == "test-authoring"] == [
        ("test-authoring", "application", "python")
    ]
    assert "codebase-comprehension" not in zeros
    assert [row for row in table if row[0] == "codebase-comprehension"] == [
        ("codebase-comprehension", "application", "python", 5)
    ]

    python_rows = {row for row in table if row[2] == "python"}
    assert sum(row[3] for row in python_rows) == _PYTHON_TOTAL
    assert len(tasks) == _PYTHON_TOTAL + sum(_COUNTS.values())

    counted = prose()
    assert "exactly **five `typescript` × `application` rows**" in counted
    assert "**no `typescript` row** for `test-authoring` or for" in counted
    assert "zero by absence" in counted
    assert "**The lint is not changed**" in counted
    assert "The `python` column is **unchanged at 113**" in counted
    assert "reads **127 task(s)**" in counted


def test_the_readers_corpus_count_header_reads_the_python_column(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§59.8 predicted this line moves to 127; the round ruled the other way.

    The first two-language precheck showed the rows-only filter pooling
    fourteen TypeScript controls into the Python categories' published mixes
    and denominators — the pooling #97's stories 22/27/28 rule out — so the
    reader now narrows the *task set* with the rows (4874f89), and the
    header counts the selected language's corpus, against a loaded set
    `eval-v1 --replay`'s own count discloses; the record (#113) says both.

    Both figures are live reads of the corpus and both moved as later rounds
    authored into the Python column — round 8's three `test-authoring` tasks,
    round 10's three `investigation` ones, round 11's three
    `requirement-decomposition` ones, round 12's first explain-style
    `codebase-comprehension` one: 113 and 127 at the time §59.8 was written,
    123 and 137 with those tasks checked in. The section's own prose is
    quoted above and is unmoved — what round 7 did to the Python column is
    still nothing.
    """
    assert len(tasks) == _PYTHON_TOTAL + sum(_COUNTS.values())
    outcomes = reconcile_v1.observed_outcomes(
        list(tasks.values()), [], source="(no run log)"
    )
    header = reconcile_v1.corpus_header(
        "reconciliation", list(outcomes.values()), tasks_root=_TASKS, logs=[]
    )
    assert any(f"— {_PYTHON_TOTAL} task(s)" in line for line in header)
    ts = reconcile_v1.observed_outcomes(
        list(tasks.values()), [], source="(no run log)",
        language="typescript", language_explicit=False,
    )
    assert len(ts) == 14
