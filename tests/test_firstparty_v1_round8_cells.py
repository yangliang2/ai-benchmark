"""Round 8's pre-registration, pinned: what section 68 of the design note
commits to before the first paid `test-authoring` run.

Round 8 authors three tasks under a brand-new verdict shape — the mutation
gate — and sweeps them under the three standing columns. Its registration is
therefore a *list*: which three, on which three combinations, under what
ceiling, for how much, invoked how. §46 did that job for round 5, §52 for
round 6 and §59 for round 7; the shape here is deliberately §59's, one round
on and one instrument later.

Two disciplines are inherited from that file rather than re-argued.

**The register is the design note**, not a constant in code — the note is what
a reader of the round consults and what a reviewer holds the sweep to — so
every test below parses section 68's own fenced blocks and its own prose and
then re-derives each claim from the task set, from the lint's coverage table
and from the checked-in run logs. A register that drifts from the corpus it
registers is the exact defect this file exists to catch, and prose is what
nothing else checks.

**No test here selects a run log by filename.** Runs are found by scanning
every log under the run-log directory and keying on task x agent x model,
which is the sweep protocol's rule after the first pass of the round-1
analysis silently dropped two paid cells that way. The round's cost anchor is
likewise recomputed from round 7's own rows rather than quoted out of §61,
because a registration whose arithmetic cannot be re-derived is a number
somebody wrote down.

Nothing here runs a live cell and nothing here grades one. Until the sweep
landed the last test said the round had not been swept at all; it now says the
forward-reading version of the same claim — the nine cells the logs carry under
this sweep id are the nine this section registered, and nothing else. Every
verdict, gate and dollar the round produced belongs to its record and is pinned
in `test_firstparty_v1_round8_record.py`.
"""

import re
from pathlib import Path

import pytest

from ai_benchmark import agents, firstparty, firstparty_v1, pricing, reconcile_v1

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 8 cells and cost — registered 2026-08-20"

_SWEEP = "round-8"

# The three standing columns, unchanged from round 7 and written agent-first
# because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the per-cell cost anchor comes from, named by its sweep id because
# that is what identifies a round. It is the most recent selection in the
# corpus that priced all three of the above over one sweep.
_ANCHOR_ROUND = "round-7"

# The one number in force for every cell of this round, reached by the fallback
# rather than by a row: `test-authoring` registers nothing.
_LIMIT_S = 600

# The action the round is, and how many tasks of it the corpus holds. Both are
# re-derived below; these are what the section claims.
_CATEGORY = "test-authoring"
_CELLS = 3

# The four categories `LIVE_RUN_LIMITS_S` carries, which this ticket does not
# touch: round 4's two by §37 and round 5's two by §46.
_REGISTERED_LIMITS = {"bug-fix", "fault-location", "code-review",
                      "codebase-comprehension"}

# The mutant counts the register's own parenthesised notes carry, spelled the
# way the note spells them.
_NUMBER_WORDS = {"three": 3, "four": 4, "five": 5, "six": 6}


def note_section() -> str:
    """Section 68, from its heading to the next top-level one."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{_HEADING}\n")
    assert len(body) == 2, f"the note carries exactly one {_HEADING!r}"
    return body[1].split("\n## ")[0]


def prose() -> str:
    """The section with its wrapping collapsed. What a sentence says is the
    pin; where the line happens to break is not, and a pin on the break would
    fail the next time a word is added upstream of it."""
    return " ".join(note_section().split())


# One line of the register: a task id — lowercase words joined by hyphens —
# alone or followed by a parenthesised note on the scenario and its mutant
# count. Two of the section's three fenced blocks are not lists of cells (the
# summed columns of §68.4 and the sweep's command line), and neither has a line
# shaped like this. A block that is neither wholly register lines nor wholly
# not is a malformed register rather than something to read half of.
_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def registered() -> dict[str, str]:
    """The three task ids and their parenthesised notes, read out of the
    section's own fenced blocks. The register is the list in the note."""
    found: dict[str, str] = {}
    for block in note_section().split("```")[1::2]:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        listed = [
            match for line in lines
            if (match := _REGISTER_LINE.fullmatch(line)) is not None
        ]
        if not listed:
            continue
        assert len(listed) == len(lines), (
            f"a fenced block mixes register lines with other lines: {lines}"
        )
        for match in listed:
            found[match.group(1)] = match.group(2) or ""
    return found


def summed_columns() -> dict[tuple[str, str], float]:
    """§68.4's summed-columns block: the three-cell total per combination.

    The block is found by what it contains rather than by its position, so
    adding a fenced block above it does not silently move the read.
    """
    blocks = [
        block for block in note_section().split("```")[1::2] if "total" in block
    ]
    assert len(blocks) == 1, "one summed-columns block"
    columns: dict[tuple[str, str], float] = {}
    for line in blocks[0].splitlines():
        match = re.fullmatch(
            rf"(\S+) x (\S+)\s+{_CELLS} x \$\d+\.\d+ = \$(\d+\.\d+)", line.strip()
        )
        if match is not None:
            columns[(match.group(1), match.group(2))] = float(match.group(3))
    return columns


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
    """Round 7's cells, per combination: the anchor §68.4 prices from.

    The round is found by its sweep id and its rows are then grouped by
    combination — the same selection §59 registered and §61 reported,
    re-derived here rather than re-listed, so this file needs no copy of the
    fourteen ids.
    """
    swept = [run for run in rows.values() if run.sweep == _ANCHOR_ROUND]
    assert len(swept) == 42, "round 7 swept forty-two cells"
    grouped = {
        combination: [
            run for run in swept
            if (run.agent, run.model) == combination
        ]
        for combination in _COMBINATIONS
    }
    assert all(len(runs) == 14 for runs in grouped.values()), (
        "fourteen tasks under each of the three combinations"
    )
    return grouped


def test_the_section_takes_the_next_free_number_before_any_paid_run() -> None:
    """§68 is the next free number and it is a pre-registration.

    The note numbers its sections once and never renumbers them, so a section
    taking a number already spent is a citation collision every later record
    inherits. §67 (the round-8 rulings) is what this follows, and the record
    ticket takes what is free after this — which the section says in a line, so
    that whoever writes it does not have to re-derive the frontier.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert 67 in numbered, "the round-8 rulings"
    assert numbered.count(68) == 1
    # 68 was the last number the note spent until the round's record took what
    # was free after it. That the record opened at 69 — and did not renumber
    # anything — is the same discipline read one section on, and it is pinned
    # in full in `test_firstparty_v1_round8_record.py`.
    assert numbered[numbered.index(68) + 1] == 69, (
        "the record did not open at the number this section left free"
    )

    counted = prose()
    assert "written down before the first paid run" in counted
    assert "This is round 8's pre-registration and nothing else" in counted
    assert "**the next free section number**, §69 onward" in counted
    assert "nothing below is a result" in counted


def test_the_register_is_three_ids_the_task_set_actually_loads(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The first thing a register has to be: three real tasks, named once.

    A duplicated id would make the round two tasks while reading as three, and
    an id naming nothing would be a cell `--task` refuses before anything runs
    — which is the good failure, but it is one paid invocation later than this.

    The parenthesised mutant counts are checked against the planted sets on
    disk, because they are the one figure in the register a reader could use to
    sanity-check the gate's denominator, and a stale one there would read as a
    task that lost a mutant.
    """
    register = registered()

    assert len(register) == _CELLS, "the round is three tasks"
    unknown = sorted(set(register) - set(tasks))
    assert not unknown, f"the register names tasks the set does not load: {unknown}"

    for task_id, note in register.items():
        word = re.fullmatch(r".*; (\w+) mutants", note)
        assert word is not None, f"{task_id}'s note states its mutant count"
        planted = len(firstparty_v1.mutant_patches(tasks[task_id]))
        assert _NUMBER_WORDS[word.group(1)] == planted, task_id

    counted = prose()
    assert "three tasks × three combinations = nine cells" in counted
    assert "**This list is the register.**" in counted
    assert "**every `test-authoring` task the corpus holds**" in counted


def test_the_three_are_every_test_authoring_task_and_each_is_a_control(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§68.1 and §68.2: what the three are, and that there is no fourth.

    A **declared control** with no construction block is what gives each cell a
    category baseline to be read against and what stops the round being misread
    as a knob result it never registered a contrast for. The action, the
    language and the surface are the other three claims: the round closes one
    action in one language on one surface, and a task in the register declaring
    otherwise would be a cell no reading of the round covers.

    That the three are *every* `test-authoring` task is the claim that ties the
    register to the corpus: a fourth outside it would be a task the round
    authored and does not sweep, which is the drift this file exists to catch.
    """
    for task_id in registered():
        task = tasks[task_id]
        assert task.category == _CATEGORY, task_id
        assert task.language == "python", task_id
        assert task.surface == "application", task_id
        assert firstparty_v1.is_control(task), task_id
        assert task.control is True, task_id
        assert task.construction is None, task_id
        assert task_id not in firstparty_v1.BASELINE_TASK_IDS, task_id
        assert firstparty_v1.is_mutation_keyed(task), task_id

    authored = {
        task_id for task_id, task in tasks.items() if task.category == _CATEGORY
    }
    assert authored == set(registered())

    counted = prose()
    assert "each is a **declared control**" in counted
    assert "**round 8 moves no knob's counter and the kill discipline does " \
        "not count it**" in counted
    assert "`calibrate-v1` gains no `test-authoring` multiplier row" in counted
    assert "stays a **disclosed zero**" in counted


def test_the_coverage_table_carries_the_python_row_and_no_typescript_one(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§68.2's Python-only claim, against `coverage_table` itself.

    The table carries a row per populated (category, surface, language) plus a
    `(category, "-", "-", 0)` row only for a category with no task in *any*
    language. So `test-authoring` now prints its Python row and no TypeScript
    one, and its language zero is disclosed by §68.2 and by absence — the same
    shape `codebase-comprehension` has carried since round 7. Pinning it here
    is what keeps the register's "three, all Python" honest against the table
    the round's acceptance is read off.
    """
    table = firstparty_v1.coverage_table(list(tasks.values()))

    rows = [row for row in table if row[0] == _CATEGORY]
    assert rows == [(_CATEGORY, "application", "python", _CELLS)]
    assert not [row for row in table if row[0] == _CATEGORY and row[2] == "typescript"]

    zeros = {row[0] for row in table if row[1:] == ("-", "-", 0)}
    assert _CATEGORY not in zeros, "the round filled the registered empty cell"


def test_every_cell_runs_at_the_flat_default_and_no_row_is_registered(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§68.5: one ceiling over the round, reached by the fallback.

    `test-authoring` joins no `LIVE_RUN_LIMITS_S` row, so its nine cells run at
    the flat default — numerically the same 600 seconds the four registered
    categories carry, which is what keeps the round free of a ceiling
    difference and free of a cross-round caveat. The distinction matters
    anyway, because only a registered category's cell can later be described as
    running "under the registered 600 s", and the record is to say "at the flat
    default" instead.

    The keying claim is the one this round adds: the limit is looked up on
    category alone and handed to the adapter, so a suite gets no more seconds
    than a patch and the gate that grades it afterwards is no part of the 600.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == _REGISTERED_LIMITS, (
        "this ticket registers nothing new"
    )
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S, "the flat default is the same number"

    for task_id in registered():
        assert firstparty_v1.live_run_limit_s(tasks[task_id]) == _LIMIT_S, task_id

    # And the fallback is what answers, not a row that happens to agree: the
    # lookup that decides is `live_run_limit_s`, and what comes back for a
    # category with no row of its own is `RUN_TIMEOUT_S` itself.
    sample = tasks[next(iter(registered()))]
    assert sample.category not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert firstparty_v1.live_run_limit_s(sample) == firstparty.RUN_TIMEOUT_S

    counted = prose()
    assert "**`test-authoring` joins none of them**" in counted
    assert "This ticket adds no row" in counted
    assert "all nine cells run at the **flat default**" in counted
    assert "§46's registered sense of the distinction" in counted
    assert "**no cross-round caveat arises**" in counted
    assert "keyed on a task's **category** alone" in counted


def test_the_section_registers_the_three_standing_combinations() -> None:
    """§68.3: what is swept, and that it is what round 7 swept.

    Three combinations, not one and not two, and they are §45.13's own ruling
    carried unchanged — changing a column beside a new verdict shape would
    confound the round's one instrument with its grid. The reasoning level is
    checked against the registry rather than only quoted, because it is as much
    a property of what was measured as the model name is.
    """
    counted = prose()

    assert agents.CODEX_REASONING_LEVELS["gpt-5.6-terra"] == "medium"
    assert (
        "`claude-code` × `claude-haiku-4-5`, `claude-code` × `claude-sonnet-5`, "
        "and `codex` × `gpt-5.6-terra` at reasoning `medium`"
    ) in counted
    assert "**the three standing columns, unchanged from round 7**" in counted
    assert "three tasks × three combinations = **nine cells**" in counted

    # The two Claude columns are the ladder the reader already has; the Codex
    # one is the second harness and is deliberately not in it.
    assert reconcile_v1.LADDER_MODELS == ("claude-haiku-4-5", "claude-sonnet-5")


def test_the_invocation_plan_is_registered_with_its_dry_cell() -> None:
    """§68.6: the sweep id, the dry cell, and how cells are chosen.

    The dry cell is the rule this round exists for: a brand-new gate meeting
    its first paid diff, found wrong on one cell rather than nine. Its being
    *graded alone before the other eight* is the part that buys anything — a
    dry cell run beside the rest and graded with them discovers the same defect
    one invocation too late — and the ban on `-dry` in its filename is the
    round-1 lesson that a paid cell hidden in a rehearsal-shaped name gets
    dropped from the analysis.
    """
    counted = prose()

    assert f"Sweep id **`{_SWEEP}`**" in counted
    assert "never queued" in counted
    assert "A **dry cell first**, in its own invocation and **graded alone " \
        "before the other eight**" in counted
    assert "one `claude-code` × `claude-haiku-4-5` cell, **the cheapest of " \
        "the nine**" in counted
    assert "**one paid cell rather than nine**" in counted
    assert "it is **not** a rehearsal to be re-run" in counted
    assert "bans `-dry` in a log's name" in counted
    assert "**`--task`**" in counted
    assert f"--sweep {_SWEEP}" in counted
    assert "--agent claude-code" in note_section()
    assert "--model claude-haiku-4-5" in note_section()


def test_the_cost_range_is_derived_from_round_sevens_own_rows(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """§68.4's arithmetic, recomputed from the rows it claims to read.

    The anchor is round 7's spend on all three combinations over one task
    selection, which is the most recent place the corpus prices this round's
    whole grid. Every figure the section quotes for it — the three column
    totals, the three per-cell dollars, their sum, the three-cell columns and
    the flat extrapolation — is re-derived here from the logs rather than
    lifted from §61, because a registration whose arithmetic cannot be
    reproduced is a number somebody wrote down rather than an estimate anybody
    can check.
    """
    anchor = anchor_rows(rows)
    totals = {
        combination: round(sum(run.cost_usd for run in runs), 4)
        for combination, runs in anchor.items()
    }
    assert totals == {
        ("claude-code", "claude-haiku-4-5"): 1.4532,
        ("claude-code", "claude-sonnet-5"): 4.2344,
        ("codex", "gpt-5.6-terra"): 1.6046,
    }
    per_cell = {
        combination: round(sum(run.cost_usd for run in runs) / len(runs), 4)
        for combination, runs in anchor.items()
    }
    assert per_cell == {
        ("claude-code", "claude-haiku-4-5"): 0.1038,
        ("claude-code", "claude-sonnet-5"): 0.3025,
        ("codex", "gpt-5.6-terra"): 0.1146,
    }

    per_task = round(sum(per_cell.values()), 4)
    assert per_task == 0.5209
    assert round(per_task * _CELLS, 4) == 1.5627

    # The section's own summed-columns block, against the same arithmetic.
    assert summed_columns() == {
        combination: round(figure * _CELLS, 4)
        for combination, figure in per_cell.items()
    }
    assert round(sum(summed_columns().values()), 4) == 1.5627

    counted = prose()
    assert "**$1.4532** on `claude-haiku-4-5`" in counted
    assert "**$4.2344** on `claude-sonnet-5`" in counted
    assert "**$1.6046** on `codex` × `gpt-5.6-terra`" in counted
    assert "**$0.1038**, **$0.3025** and **$0.1146** a cell" in counted
    assert "**$0.5209 — about $0.52 — a task across the three combinations**" \
        in counted
    assert "**$1.5627, about $1.56**" in counted
    assert "Cost, stated before anyone spends: $1.5–5, at list price" in counted
    assert "the registered range is **$1.5–5**" in counted
    assert "roughly **3.2×** it at the high end" in counted

    # The headroom, in §67.8's own two terms.
    assert "**Fresh repositories cache worse**" in counted
    assert "**a whole test suite is a larger write than a locate answer**" in counted


def test_the_registered_bound_is_caching_aware_at_both_ends(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """§68.4's two bounds, against the price table and round 7's tokens.

    Round 6 missed its range 2.3× low by pricing every input token as uncached,
    which put the registration on that round's upper bound; §59.4 fixed the
    estimate rather than the stance, and this section keeps the fix. The check
    that it *is* a fix rather than a sentence about one is that the
    all-uncached total lands inside the registered range instead of at its
    ceiling. Both ends are recomputed here from the checked-in price table and
    from the token counts round 7's own rows carry, and so is the effective
    input rate the section quotes as its caching evidence — which is derivable
    from a logged row because the output half of the bill is not in doubt.
    """
    anchor = anchor_rows(rows)
    codex = anchor[("codex", "gpt-5.6-terra")]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == (2169811, 30396)

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    prices = table.models["gpt-5.6-terra"]
    assert table.version == "openai-pricing-2026-08-18.1"

    # What round 7 actually paid per input token, once its output is priced
    # out: the caching evidence §68.4 leans on, not a figure quoted from §61.
    logged = sum(run.cost_usd for run in codex)
    effective = (logged - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1e6, 4) == 0.5714

    projected_in = tokens_in / len(codex) * _CELLS
    projected_out = tokens_out / len(codex) * _CELLS
    assert tokens_in / len(codex) == 154986.5
    assert round(tokens_out / len(codex)) == 2171
    assert (round(projected_in), round(projected_out)) == (464960, 6513)

    output_cost = projected_out * prices.output_per_token
    uncached = projected_in * prices.input_uncached_per_token
    cached = projected_in * prices.input_cached_per_token
    assert round(output_cost, 4) == 0.0782
    assert round(uncached, 4) == 0.9299
    assert round(cached, 4) == 0.0930
    assert (round(cached + output_cost, 2), round(uncached + output_cost, 2)) == (
        0.17, 1.01
    )
    assert round(projected_in * effective + output_cost, 2) == 0.34

    # The Claude columns are projected from the per-cell figures the section
    # states, not from an unrounded re-sum: the arithmetic is what a reader can
    # redo, and a reader has the rounded cents.
    claude = round(sum(
        round(sum(run.cost_usd for run in anchor[combination]) / 14, 4) * _CELLS
        for combination in _COMBINATIONS[:2]
    ), 4)
    assert claude == 1.2189
    low = round(claude + cached + output_cost, 2)
    high = round(claude + uncached + output_cost, 2)
    assert (low, high) == (1.39, 2.23)
    assert 1.5 <= high <= 5, (
        "the all-uncached bound must sit inside the registered range rather "
        "than at its ceiling — pricing the round at its upper bound is round "
        "6's error"
    )

    counted = prose()
    assert "**2,169,811** input tokens and wrote **30,396**" in counted
    assert "154,986.5 in and 2,171 out a cell" in counted
    assert "**464,960 input** and **6,513 output** tokens" in counted
    assert "**$0.17 all-cached to $1.01 all-uncached**" in counted
    assert "expected figure near **$0.34**" in counted
    assert "**$1.2189** together" in counted
    assert "**$1.39 all-cached to $2.23 all-uncached**" in counted
    assert "**$0.5714/M**" in counted and "**$0.3996/M**" in counted
    assert "**The one way this round misses is registered here too**" in counted
    assert "the range's floor *is* the flat extrapolation" in counted

    # And the stance itself, unchanged: a ChatGPT-login account is not metered,
    # so the Codex figure is an equivalent and never an invoice.
    assert "authenticated by **ChatGPT login**, not by an API key" in counted
    assert "**not billed per token**" in counted
    assert "**list-price equivalent**" in counted
    assert "`cost_source: table-derived`" in counted
    assert "`cost_source: vendor-reported`" in counted


def test_what_the_round_cannot_say_is_registered_in_advance() -> None:
    """§68.7: four readings ruled out now rather than argued about later.

    Each is a reading the round's own shape makes tempting. The TypeScript one
    because the corpus has two languages and only one of them is here; the kill
    rate because every mutation-testing tool in the industry reports one; the
    cross-action comparison because a resolution rate looks like a resolution
    rate whatever produced it; and the Codex rung because a column with one
    model in it looks like a ladder with one rung.
    """
    counted = prose()

    assert "Four readings are ruled out now" in counted
    assert "Nothing about `test-authoring` × `typescript`.**" in counted
    assert "mechanical follow-on for a later round" in counted
    assert "**No kill-rate reading of any kind.**" in counted
    assert "The verdict is **binary by ruling**" in counted
    assert "**which gate failed**" in counted
    assert "no fraction over mutants is computed anywhere" in counted
    assert "**No cross-action difficulty comparison.**" in counted
    assert "**different deliverables**" in counted
    assert "**No Codex rung.**" in counted
    assert "**one model is not a ladder**" in counted


def test_the_register_is_exactly_what_the_sweep_then_did(
    rows: dict[tuple[str, str, str], firstparty_v1.Run],
) -> None:
    """The registration was kept: every registered cell swept, once, and no other.

    This test used to say the opposite — that no round-8 row existed yet — and
    it was right until the sweep landed. Catching a pre-registration suite up
    to the swept truth is the round-7 pattern, and the shape it catches up to
    is the same claim read forwards: three registered ids under three
    registered combinations is nine cells, and the log directory holds exactly
    those nine under this sweep id. What the round *measured* — the verdicts,
    the gates, the spend — belongs to the record and is pinned in
    `test_firstparty_v1_round8_record.py`; what belongs here is only that the
    thing swept is the thing registered.

    Selected by **sweep id** over every log in the directory and never by a log
    filename, which is the discipline the whole round is run under.
    """
    swept = {key: run for key, run in rows.items() if run.sweep == _SWEEP}
    assert len(swept) == _CELLS * len(_COMBINATIONS) == 9

    register = set(registered())
    assert {task_id for task_id, _, _ in swept} == register, (
        "the cells swept are not the cells registered before the sweep"
    )
    assert {(agent, model) for _, agent, model in swept} == set(_COMBINATIONS)
    for task_id in register:
        for agent, model in _COMBINATIONS:
            assert (task_id, agent, model) in swept, (task_id, agent, model)

    # None of the three was ever run under any other sweep id: they were
    # authored for this round, and a cell is only ever swept once.
    assert not [
        key for key, run in rows.items()
        if key[0] in register and run.sweep != _SWEEP
    ]

    # `None` is round 1, which predates `--sweep` and is keyed on `as_of`.
    assert {run.sweep for run in rows.values()} == {
        None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
        _SWEEP,
    }
