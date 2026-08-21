"""Round 9's pre-registration, pinned: what section 77 of the design note
commits to before the round's first paid call.

Round 9 is two halves rather than one — a calibration experiment that gates,
and, only if it opens, a sweep of three tasks under a brand-new verdict shape.
Its registration therefore has to come *before* the experiment, which is the
first paid call of either half, and it registers both: the stratum split and
the bar as counts, both cost ranges, the nine cells, the limits in force and
the grader's pinned version. §46 did the one-half job for round 5, §52 for
round 6, §59 for round 7 and §68 for round 8; the shape here is §68's with the
second half added.

Two disciplines are inherited from `test_firstparty_v1_round8_cells.py` rather
than re-argued.

**The register is the design note**, not a constant in code — the note is what
a reader of the round consults and what a reviewer holds the round to — so
every test below parses section 77's own fenced blocks and its own prose and
then re-derives each claim from the archive, from the task set, from the price
table and from the checked-in run logs. A registration whose arithmetic cannot
be reproduced is a number somebody wrote down, and a register that drifts from
the corpus it registers is the exact defect this file exists to catch.

**No test here selects a run log by filename.** Logs are collected wholesale
and rows are keyed on what they carry — a task, an agent, a model, a sweep id —
which is the sweep protocol's rule after the first pass of the round-1 analysis
silently dropped two paid cells by filtering on a name.

Nothing here calls the grader, runs a live cell or spends a dollar. The
stratum-A verdicts the bar is read over are recomputed the way `--split-only`
computes them, by replaying each archived diff against its task's held-out
tests, which is offline and free. The last test is the forward-reading one: no
`round-9` row exists yet, and no `investigation` task does either, because
authoring is gated on the experiment this section registers.
"""

import re
from pathlib import Path

import pytest

from ai_benchmark import (
    agents,
    firstparty,
    firstparty_v1,
    grader_calibration_v1,
    point_grader,
    pricing,
    reconcile_v1,
)

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 9 cells and cost — registered 2026-08-21"

_SWEEP = "round-9"

# The three standing columns, unchanged from rounds 7 and 8 and written
# agent-first because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the sweep's per-cell anchor comes from, named by its sweep id
# because that is what identifies a round. It is the nearest anchor the corpus
# has: the same three columns over the same nine-cell shape, one round ago.
_ANCHOR_ROUND = "round-8"

# The action the round sweeps, and how many tasks of it it authors.
_CATEGORY = "investigation"
_CELLS = 3

# The one number in force for every cell of this round, reached by the fallback
# rather than by a row: `investigation` registers nothing.
_LIMIT_S = 600

# The four categories `LIVE_RUN_LIMITS_S` carries, which this registration does
# not touch: round 4's two by §37 and round 5's two by §46.
_REGISTERED_LIMITS = {"bug-fix", "fault-location", "code-review",
                      "codebase-comprehension"}

# The convention the experiment's token arithmetic is done at, and the one
# assumption standing between its input half and a certainty.
_CHARS_PER_TOKEN = 4

# What the pricing page's `Claude Opus 5` row said when it was fetched, per
# million tokens. Read from that fetch and registered in §77.4; the section
# carries the URL and the as-of date beside them.
_OPUS_INPUT_PER_MTOK = 5.0
_OPUS_OUTPUT_PER_MTOK = 25.0
_PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
_AS_OF = "2026-08-21"


def note_section() -> str:
    """Section 77, from its heading to the next top-level one."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{_HEADING}\n")
    assert len(body) == 2, f"the note carries exactly one {_HEADING!r}"
    return body[1].split("\n## ")[0]


def prose() -> str:
    """The section with its wrapping collapsed. What a sentence says is the
    pin; where the line happens to break is not, and a pin on the break would
    fail the next time a word is added upstream of it."""
    return " ".join(note_section().split())


def blocks() -> list[str]:
    """The section's fenced blocks, in order."""
    return note_section().split("```")[1::2]


def block_holding(*needles: str) -> str:
    """The one fenced block holding all of these, found by what it contains
    rather than by its position — so adding a block above it does not silently
    move the read."""
    found = [
        block for block in blocks()
        if all(needle in block for needle in needles)
    ]
    assert len(found) == 1, f"exactly one fenced block holds {needles!r}"
    return found[0]


@pytest.fixture(scope="module")
def tasks() -> dict[str, firstparty_v1.Task]:
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def logs() -> list[Path]:
    """Every log under the run-log directory, collected wholesale. A filename
    says nothing about which sweep a row belongs to, and selecting on one is
    what the sweep protocol forbids."""
    return reconcile_v1.collect_logs([_LOGS])


@pytest.fixture(scope="module")
def runs(logs: list[Path]) -> list[firstparty_v1.Run]:
    return [run for log in logs for run in firstparty_v1.load_runs(log)]


@pytest.fixture(scope="module")
def stratum_a(
    tasks: dict[str, firstparty_v1.Task], runs: list[firstparty_v1.Run]
) -> list[firstparty_v1.Run]:
    """The archived answers the gate is read over: every row whose task ships a
    key the grader can be run against in exactly its production mode.

    Derived from the key shape the task ships, never from its category, which
    is `grader_calibration_v1.split`'s own rule read here without the replay it
    does for stratum B as well.
    """
    return [run for run in runs if firstparty_v1.carries_a_key(tasks[run.task_id])]


def test_the_section_takes_the_next_free_number_before_the_first_paid_call() -> None:
    """§77 is the next free number, it is a pre-registration, and it registers
    both halves.

    The note numbers its sections once and never renumbers them, so a section
    taking a number already spent is a citation collision every later record
    inherits. §76 (the round-9 rulings) is what this follows, and the record
    takes what is free after it — which the section says in a line, so that
    whoever writes it does not have to re-derive the frontier.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(76) == 1, "the round-9 rulings, spent once"
    assert numbered.count(77) == 1
    assert numbered[-1] == 77, "nothing above this section exists yet"
    assert [number for number in numbered if number > 68] == list(range(69, 78)), (
        "the rounds since 68 are contiguous and nothing was renumbered"
    )

    counted = prose()
    assert "This is round 9's pre-registration and nothing else" in counted
    assert "written down before the first paid call" in counted
    assert "**pre-registration comes before the calibration experiment**" in counted
    assert "it registers *both* halves" in counted
    assert "**the next free section number**, §78 onward" in counted
    assert "nothing below is a result, and nothing above is renumbered" in counted

    # 77.1: the order the two ranges hang off, and what a failed bar means.
    assert "The calibration experiment runs first and gates" in counted
    assert (
        "**if the bar fails, the round closes as a record of the failure and "
        "heap 3 stays empty, disclosed**"
    ) in counted
    assert "no authoring call is made until the first is spent and read" in counted


def test_the_split_is_re_derived_from_the_logs_and_not_copied(
    tasks: dict[str, firstparty_v1.Task],
    logs: list[Path],
    runs: list[firstparty_v1.Run],
    stratum_a: list[firstparty_v1.Run],
) -> None:
    """§77.2's counts, against a fresh derivation from the archive itself.

    The section is required to re-derive the split mechanically rather than
    copy it out of §76.3, and this is the check that it did: every count it
    quotes — the answers, the logs, the two strata, the three actions inside
    stratum A, its points and its replay-computed verdicts — is recomputed here
    from the task set and the run logs, with no grader built and no call made.

    The verdicts are the expensive half and are computed the way `--split-only`
    computes them: replay each archived diff against its own task's held-out
    tests. That is the machine verdict the grader will be scored against, and
    computing it before the grader runs peeks at nothing the grader will see.
    """
    assert len(logs) == 37
    assert len(runs) == 306

    by_category = {
        category: [
            run for run in stratum_a if tasks[run.task_id].category == category
        ]
        for category in ("code-review", "codebase-comprehension", "fault-location")
    }
    assert {name: len(found) for name, found in by_category.items()} == {
        "code-review": 26,
        "codebase-comprehension": 10,
        "fault-location": 27,
    }
    assert len(stratum_a) == 63
    assert len(runs) - len(stratum_a) == 243

    points = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
    )
    assert points == 115

    resolved = [
        firstparty_v1.grade(tasks[run.task_id], run.diff) for run in stratum_a
    ]
    assert (resolved.count(True), resolved.count(False)) == (55, 8)

    # The command's own printed table, as the section quotes it.
    printed = block_holding("stratum  answers  points", "(all)")
    for line in (
        "A        63       115     the task's planted key, run in production mode",
        "B        243      243     the synthetic point "
        '"the asked-for work was done"',
        "code-review             26       78      19        7",
        "codebase-comprehension  10       10      10        0",
        "fault-location          27       27      26        1",
        "(all)                   63       115     55        8",
    ):
        assert line in printed, line

    counted = prose()
    assert "--split-only" in counted
    assert "no grader built, no call made" in counted
    assert "**306** archived answers read out of the **37** run logs" in counted
    assert "**stratum A = 63**" in counted
    assert (
        "27 `fault-location`, 26 `code-review` and 10 locate-style "
        "`codebase-comprehension`"
    ) in counted
    assert "**stratum B = 243**" in counted
    assert "**55 resolved / 8 unresolved**" in counted
    assert "**Every count the command printed matches §76.3's to the answer**" in counted
    assert "**the gate reads stratum A alone**" in counted
    assert "**with its confound named and gating nothing**" in counted
    assert "**transfer gap**" in counted
    assert "never as a second gate" in counted


def test_the_bar_is_registered_as_counts_with_its_rounding_shown() -> None:
    """§77.3: two percentages turned into two counts, once, in advance.

    §76.4 registered percentages; a percentage is not a thing a reader can
    check by hand against a stratum of 63, and rounding one the wrong way moves
    the bar by a whole answer. So the section does the arithmetic in the open
    and the counts are checked here against `registered_count`, which is what
    the gate itself will compare integers with.

    The unresolved clause is the load-bearing one and the section has to say
    why: the always-covered grader scores the resolved class free and is
    refused only by the second clause.
    """
    assert grader_calibration_v1.OVERALL_BAR_PERCENT == 90
    assert grader_calibration_v1.UNRESOLVED_BAR_PERCENT == 80
    assert grader_calibration_v1.registered_count(90, 63) == 57
    assert grader_calibration_v1.registered_count(80, 8) == 7

    # Rounded up, and never to the nearest: the counts one below are both under
    # the percentage the ruling registered.
    assert 56 / 63 < 0.90 <= 57 / 63
    assert 6 / 8 < 0.80 <= 7 / 8

    shown = block_holding("0.90 x 63", "0.80 x")
    assert "0.90 x 63 = 56.7" in shown
    assert ">= 57 of 63" in shown
    assert "0.80 x  8 =  6.4" in shown
    assert ">=  7 of  8" in shown

    counted = prose()
    assert "check by hand: ≥ 57 of 63, and ≥ 7 of 8.**" in counted
    assert "Rounding **up** in both lines, and never to the nearest" in counted
    assert "56 of 63 is 88.9% and 6 of 8 is 75%" in counted
    assert "**The unresolved clause is the load-bearing one**" in counted
    assert "a grader that always says \"covered\" collects the resolved class free" \
        in counted
    assert "scores 55 of 63, which is 87.3%" in counted
    assert "**0 of 8** and is refused outright" in counted
    assert "one honest key-mismatch" in counted
    assert "absorbed at 7 of 8, while two sink the instrument at 6 of 8" in counted

    # And the three figures that sentence leans on are the split's own.
    assert round(55 / 63 * 100, 1) == 87.3
    assert round(56 / 63 * 100, 1) == 88.9
    assert 6 / 8 == 0.75


def test_the_experiment_is_priced_over_calls_at_prices_that_were_fetched(
    tasks: dict[str, firstparty_v1.Task],
    stratum_a: list[firstparty_v1.Run],
    runs: list[firstparty_v1.Run],
) -> None:
    """§77.4: 358 calls, priced from the fetched page, with both ends stated.

    The unit is the call and not the answer, because production mode is one
    call per planted point and a three-finding key costs three of them — which
    is exactly the gap between 63 stratum-A answers and 115 stratum-A calls,
    and the reason pricing this experiment over answers would underprice it by
    a sixth. The call count is re-derived here from the keys the stratum-A
    tasks actually ship, and the character totals from the prompt template
    filled the way the grader fills it.

    A model's memory of a pricing page is not a source, so the section records
    the URL the prices were read from and the date they were read on; those two
    are checked for here, and the per-MTok figures they carry are what the
    arithmetic below is redone at.
    """
    keyed_calls = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
    )
    review_calls = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
        if tasks[run.task_id].category == "code-review"
    )
    synthetic_calls = len(runs) - len(stratum_a)
    assert (keyed_calls, review_calls, synthetic_calls) == (115, 78, 243)
    assert keyed_calls + synthetic_calls == 358

    counts = block_holding("archive calls in all")
    for line in (
        "27 fault-location   x 1 point  =  27",
        "26 code-review      x 3 points =  78",
        "10 comprehension    x 1 point  =  10",
        "115 calls",
        "243 answers          x 1 point  = 243 calls",
        "358 archive calls in all",
    ):
        assert line in counts, line

    # The characters the calls carry, filled the way the grader fills them.
    prompt_chars = 0
    deliverable_chars = 0
    for run in runs:
        for point in grader_calibration_v1.points_for(tasks[run.task_id]):
            prompt_chars += len(
                point_grader.PROMPT.format(
                    point_id=point["id"],
                    point_text=point["text"],
                    deliverable=run.output,
                )
            )
            deliverable_chars += len(run.output)
    assert (prompt_chars, deliverable_chars) == (491246, 212658)
    assert len(point_grader.PROMPT) == 714

    lengths = sorted(len(run.output) for run in stratum_a)
    assert (lengths[0], lengths[-1]) == (45, 1379)
    assert lengths[len(lengths) // 2] == 352

    per_input = _OPUS_INPUT_PER_MTOK / 1e6
    per_output = _OPUS_OUTPUT_PER_MTOK / 1e6

    input_tokens = prompt_chars // _CHARS_PER_TOKEN
    quoted_tokens = deliverable_chars // _CHARS_PER_TOKEN
    assert (input_tokens, quoted_tokens) == (122811, 53164)

    low_out = 358 * 100
    high_out = 358 * 300 + quoted_tokens
    assert (low_out, high_out) == (35800, 160564)

    archive_low = round(input_tokens * per_input + low_out * per_output, 4)
    archive_high = round(input_tokens * per_input + high_out * per_output, 4)
    assert round(input_tokens * per_input, 4) == 0.6141
    assert round(low_out * per_output, 4) == 0.8950
    assert round(high_out * per_output, 4) == 4.0141
    assert (archive_low, archive_high) == (1.5091, 4.6282)

    # The proofs: contingent on the bar, priced over points *and* disqualifiers
    # because the writer calls once per each against both answers.
    assert (3 * (4 + 0) * 2, 3 * (6 + 2) * 2) == (24, 48)
    proof_low_in = 24 * 4914 // _CHARS_PER_TOKEN
    proof_high_in = 48 * 8914 // _CHARS_PER_TOKEN
    assert (proof_low_in, proof_high_in) == (29484, 106968)
    proof_low_out = 24 * 100
    proof_high_out = 48 * (8000 // _CHARS_PER_TOKEN + 300)
    assert (proof_low_out, proof_high_out) == (2400, 110400)
    proofs_low = round(proof_low_in * per_input + proof_low_out * per_output, 4)
    proofs_high = round(proof_high_in * per_input + proof_high_out * per_output, 4)
    assert round(proof_low_in * per_input, 4) == 0.1474
    assert round(proof_high_in * per_input, 4) == 0.5348
    assert round(proof_high_out * per_output, 4) == 2.7600
    assert (proofs_low, proofs_high) == (0.2074, 3.2948)

    total_low = round(archive_low + proofs_low, 4)
    total_high = round(archive_high + proofs_high, 4)
    assert (total_low, total_high) == (1.7165, 7.9230)
    # The registered range holds the arithmetic, rounded outward at both ends.
    assert 1.5 <= total_low and total_high <= 8

    arithmetic = block_holding("round total")
    for line in (
        "input   491,246 chars / 4                    = 122,811 tok  "
        "x $5/M  = $0.6141",
        "output  low   358 calls x 100 tok thinking   =  35,800 tok  "
        "x $25/M = $0.8950",
        "        high  358 x 300 tok + 53,164 quoted  = 160,564 tok  "
        "x $25/M = $4.0141",
        "archive half  $1.5091 - $4.6282",
        "proofs  low   24 calls x 4,914 chars / 4     =  29,484 tok  "
        "x $5/M  = $0.1474",
        "        high  48 calls x 8,914 chars / 4     = 106,968 tok  "
        "x $5/M  = $0.5348",
        "              48 x (2,000 quoted + 300)      = 110,400 tok  "
        "x $25/M = $2.7600",
        "proofs half   $0.2074 - $3.2948",
        "round total   $1.7165 - $7.9230",
    ):
        assert line in arithmetic, line

    proofs = block_holding("reference + foil")
    assert "3 tasks x (4-6 points + 0-2 disqualifiers) x (reference + foil)" in proofs
    assert "= 8-16 calls a task = 24-48 calls for the round" in proofs

    # The fetch itself, pinned as a command rather than as a remembered number.
    fetched = block_holding("curl")
    assert f"curl -sL {_PRICING_URL}" in fetched

    counted = prose()
    assert "The experiment's price: $1.5–8" in counted
    assert "counted in calls and not in answers" in counted
    assert "underprice the experiment by a sixth" in counted
    assert "**The prices were read, not remembered.**" in counted
    assert f"`source_url`: `{_PRICING_URL}`" in counted
    assert f"`as_of`: **{_AS_OF}**" in counted
    assert "row **Claude Opus 5**" in counted
    assert "**$5 / MTok** base input" in counted
    assert "**$25 / MTok** output" in counted
    assert "**$5/MTok in and $25/MTok out**" in counted
    assert "the registered range is **$1.5–8**" in counted
    assert "**The assumed disqualifier count is 0–2 a task**" in counted
    assert "forces a re-registration rather than being absorbed by it" in counted
    assert "**45–1379 characters, median 352**" in counted
    assert "**491,246 characters**" in counted
    assert "**212,658 characters**" in counted

    # The cached/uncached split the sweep protocol's item 2 asks for, settled
    # as a fact about the instrument: the grader sets no breakpoint.
    assert "and it is all uncached" in counted
    assert "sets no `cache_control` breakpoint" in counted
    assert "**every input token in this half is priced at the base rate**" in counted
    assert "cache_control" not in point_grader.PROMPT
    assert "cache_control" not in (
        (_REPO / "src" / "ai_benchmark" / "point_grader.py").read_text(
            encoding="utf-8"
        )
    )

    # Which half is an assumption, said in as many words.
    assert "**The output half is the half with no anchor**" in counted
    assert "The high end is a bound and not an expectation" in counted
    assert "**The one way this half misses is the grader thinking longer than " \
        "it is registered to.**" in counted
    assert "**never enter `unified.jsonl`**" in counted


def test_the_sweep_range_is_derived_from_the_checked_in_round_8_rows(
    runs: list[firstparty_v1.Run],
) -> None:
    """§77.5's arithmetic, recomputed from the rows it claims to read.

    The anchor is round 8's nine cells — the same three combinations over the
    same nine-cell shape, one round ago — selected by **sweep id** over every
    log in the directory and never by a log filename. Every figure the section
    quotes is re-derived here rather than lifted from §69's record, because a
    registration whose arithmetic cannot be reproduced is a number somebody
    wrote down.

    Both ends of the bound are recomputed too. Round 9 sweeps three cells on
    the Codex column and round 8 swept three, so the projection is that round's
    own token totals rather than a rate scaled up, and the caching split is the
    only thing that moves between the two ends.
    """
    anchor = {
        combination: [
            run for run in runs
            if run.sweep == _ANCHOR_ROUND and (run.agent, run.model) == combination
        ]
        for combination in _COMBINATIONS
    }
    assert all(len(found) == _CELLS for found in anchor.values()), (
        "three tasks under each of the three combinations"
    )
    assert sum(len(found) for found in anchor.values()) == 9

    totals = {
        combination: round(sum(run.cost_usd for run in found), 4)
        for combination, found in anchor.items()
    }
    assert totals == {
        ("claude-code", "claude-haiku-4-5"): 0.7237,
        ("claude-code", "claude-sonnet-5"): 1.7679,
        ("codex", "gpt-5.6-terra"): 0.2698,
    }
    per_cell = {
        combination: round(sum(run.cost_usd for run in found) / len(found), 4)
        for combination, found in anchor.items()
    }
    assert per_cell == {
        ("claude-code", "claude-haiku-4-5"): 0.2412,
        ("claude-code", "claude-sonnet-5"): 0.5893,
        ("codex", "gpt-5.6-terra"): 0.0899,
    }
    per_task = round(sum(per_cell.values()), 4)
    assert per_task == 0.9204
    assert round(per_task * _CELLS, 4) == 2.7612

    # §68.4's summed-columns form, against the same arithmetic.
    summed = block_holding("total", "claude-code x claude-haiku-4-5")
    columns: dict[tuple[str, str], float] = {}
    for line in summed.splitlines():
        match = re.fullmatch(
            rf"(\S+) x (\S+)\s+{_CELLS} x \$\d+\.\d+ = \$(\d+\.\d+)", line.strip()
        )
        if match is not None:
            columns[(match.group(1), match.group(2))] = float(match.group(3))
    assert columns == {
        combination: round(figure * _CELLS, 4)
        for combination, figure in per_cell.items()
    }
    assert round(sum(columns.values()), 4) == 2.7612
    assert "total        $2.7612" in summed

    # The caching-aware envelope, at the checked-in price table.
    codex = anchor[("codex", "gpt-5.6-terra")]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == (361275, 8122)

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    prices = table.models["gpt-5.6-terra"]
    logged = sum(run.cost_usd for run in codex)
    effective = (logged - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1e6, 4) == 0.4771

    output_cost = tokens_out * prices.output_per_token
    uncached = tokens_in * prices.input_uncached_per_token
    cached = tokens_in * prices.input_cached_per_token
    assert round(output_cost, 4) == 0.0975
    assert round(uncached, 4) == 0.7225
    assert round(cached, 4) == 0.0723
    assert (round(cached + output_cost, 2), round(uncached + output_cost, 2)) == (
        0.17, 0.82
    )
    assert round(tokens_in * effective + output_cost, 2) == 0.27

    claude = round(sum(columns[combination] for combination in _COMBINATIONS[:2]), 4)
    assert claude == 2.4915
    low = round(claude + cached + output_cost, 2)
    high = round(claude + uncached + output_cost, 2)
    assert (low, high) == (2.66, 3.31)
    assert 2.5 <= high <= 5, (
        "the all-uncached bound must sit inside the registered range rather "
        "than at its ceiling — pricing the round at its upper bound is round "
        "6's error"
    )
    assert high < (2.5 + 5) / 2, "and below its middle, which is §59.4's shape"

    counted = prose()
    assert "The sweep's price: $2.5–5" in counted
    assert "in round 8's band" in counted
    assert "selected by sweep id `round-8`" in counted
    assert "never by a log's filename" in counted
    assert "**$0.7237** on `claude-haiku-4-5`" in counted
    assert "**$1.7679** on `claude-sonnet-5`" in counted
    assert "**$0.2698** on `codex` × `gpt-5.6-terra`" in counted
    assert "**$0.2412**, **$0.5893** and **$0.0899** a cell" in counted
    assert "**$0.9204 a task across the three combinations**" in counted
    assert "three tasks come to **$2.7612**" in counted
    assert "round 8's own **$2.7614**" in counted
    assert "**361,275** input tokens and wrote **8,122**" in counted
    assert "**$0.17 all-cached to $0.82 all-uncached**" in counted
    assert "**$0.4771/M**" in counted
    assert "expected figure near **$0.27**" in counted
    assert "**$2.4915** together" in counted
    assert "**$2.66 all-cached to $3.31 all-uncached**" in counted

    # The headroom, and both ways this range misses, registered in advance.
    assert "this one is **1.8×**" in counted
    assert "the range's floor *is* the flat extrapolation" in counted
    assert "a finding about the action and not an accounting surprise" in counted
    assert "an investigation that reads the whole repository on every turn" in counted

    # The stance itself, unchanged: a ChatGPT-login account is not metered, so
    # the Codex figure is an equivalent and never an invoice.
    assert "authenticated by **ChatGPT login**, not by an API key" in counted
    assert "**not billed per token**" in counted
    assert "**list-price equivalent**" in counted
    assert "`cost_source: table-derived`" in counted
    assert "`cost_source: vendor-reported`" in counted


def test_the_nine_cells_and_the_invocation_are_registered(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§77.6: three tasks × three columns, the sweep id, the dry cell, and an
    id register deliberately left empty.

    The three ids do not exist yet — authoring is gated on the experiment — so
    what this checks is the shape: the columns, the count, the language, the
    control declaration and the sweep's invocation, plus the one thing that
    makes the empty register honest rather than an omission, that the section
    says outright it is to be filled in here before the sweep.

    The dry cell is the rule this round exists for a second time: a brand-new
    gate meeting its first paid diff, found wrong on one cell rather than nine.
    """
    counted = prose()

    assert agents.CODEX_REASONING_LEVELS["gpt-5.6-terra"] == "medium"
    assert (
        "`claude-code` × `claude-haiku-4-5`, `claude-code` × "
        "`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`"
    ) in counted
    assert "**the three standing columns, unchanged from rounds 7 and 8**" in counted
    assert "three tasks × three combinations = **nine cells**" in counted
    assert f"three `{_CATEGORY}` tasks × the three standing columns" in counted

    # The two Claude columns are the ladder the reader already has; the Codex
    # one is the second harness and is deliberately not in it.
    assert reconcile_v1.LADDER_MODELS == ("claude-haiku-4-5", "claude-sonnet-5")

    assert "Each of the three is **Python**" in counted
    assert "each is a **declared control**" in counted
    assert "`control: true`, no construction block, no knob activation, no " \
        "prediction" in counted
    assert (
        "**round 9 moves no knob's counter and the kill discipline does not "
        "count it**"
    ) in counted
    assert f"`calibrate-v1` gains no `{_CATEGORY}` multiplier row" in counted

    # The register, left for the authoring ticket and said to be left.
    assert "**The three task ids do not exist yet" in counted
    assert (
        "**the id register for round 9 is left explicitly to be filled in, in "
        "this section, before the sweep, by the round's task-authoring ticket**"
    ) in counted
    assert f"the corpus holds no `{_CATEGORY}` task as this is written" in counted
    assert "**disclosed zero**" in counted

    # And that claim, against the corpus: no task of the action, and the
    # coverage table still carries its zero row.
    assert not [task for task in tasks.values() if task.category == _CATEGORY]
    table = firstparty_v1.coverage_table(list(tasks.values()))
    assert (_CATEGORY, "-", "-", 0) in table
    assert not [row for row in table if row[0] == _CATEGORY and row[3]]

    # No fenced block of the section is a register of task ids: an id listed
    # here before the tasks exist would be a cell nothing can sweep.
    id_line = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")
    for block in blocks():
        for line in block.splitlines():
            assert id_line.fullmatch(line.strip()) is None, line

    # The invocation.
    assert f"Sweep id **`{_SWEEP}`**" in counted
    assert "never queued" in counted
    assert (
        "A **dry cell first**, in its own invocation and **graded alone before "
        "the other eight**"
    ) in counted
    assert "**one paid cell rather than nine**" in counted
    assert "it is **not** a rehearsal to be re-run" in counted
    assert "bans `-dry` in a log's name" in counted
    assert "**`--task`**" in counted
    assert "**Nothing is re-run**" in counted

    command = block_holding("eval-v1")
    assert f"--sweep {_SWEEP}" in command
    assert "--agent claude-code" in command
    assert "--model claude-haiku-4-5" in command


def test_every_cell_runs_at_the_flat_default_and_no_row_is_registered() -> None:
    """§77.7: one ceiling over the round, reached by the fallback.

    `investigation` joins no `LIVE_RUN_LIMITS_S` row, so its nine cells run at
    the flat default — numerically the same 600 seconds the four registered
    categories carry, which is what keeps the round free of a ceiling
    difference and free of a cross-round caveat. The distinction matters
    anyway, because only a registered category's cell can later be described as
    running "under the registered 600 s", and the record is to say "at the flat
    default" instead.

    Registering is a deliberate act: §76 rules nothing about run-time limits,
    and §68.5's precedent one round ago was that a new action joins no register
    for exactly that reason. So this is a test that a row was *not* added.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == _REGISTERED_LIMITS, (
        "this registration adds nothing new"
    )
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S, "the flat default is the same number"

    counted = prose()
    assert "**`investigation` joins none of them**" in counted
    assert "This ticket adds no row" in counted
    assert "`test-authoring` joined no register" in counted
    assert "all nine cells run at the **flat default**" in counted
    assert "§46's registered sense of the distinction" in counted
    assert "**no cross-round caveat arises**" in counted
    assert "its grader calls are no part of the 600" in counted

    # And the line the section cites for the fallback's value still says it.
    runner = (_REPO / "src" / "ai_benchmark" / "firstparty.py").read_text(
        encoding="utf-8"
    ).splitlines()
    assert f"RUN_TIMEOUT_S = {_LIMIT_S}" in runner[246]
    assert "`src/ai_benchmark/firstparty.py:247`" in counted


def test_the_grader_version_is_quoted_verbatim() -> None:
    """§77.8: the instrument, pinned as the string the code computes.

    A bar met at one grader version says nothing about a bar met at another, so
    the version is written into the registration rather than left to be read
    off the rulings archive afterwards. Quoted verbatim means exactly that: the
    string in the note is `GRADER_VERSION`, model id and prompt hash both, and
    a prompt edit moves it — which is what makes a later grader change visibly
    a different instrument.
    """
    version = block_holding("claude-opus-5").strip()
    assert version == point_grader.GRADER_VERSION
    assert version == f"{point_grader.GRADER_MODEL}:{point_grader.PROMPT_HASH}"
    assert point_grader.GRADER_MODEL == "claude-opus-5"

    counted = prose()
    assert "`point_grader.GRADER_VERSION`" in counted
    assert "the first twelve hex digits of the SHA-256 of the prompt" in counted
    assert "**a later grader change is visibly a different instrument**" in counted
    assert "one file per version" in counted


def test_nothing_of_round_9_has_been_swept_and_no_task_exists_yet(
    tasks: dict[str, firstparty_v1.Task], runs: list[firstparty_v1.Run]
) -> None:
    """The forward-reading test, until the sweep lands: this is a registration
    and not a record.

    Round 8's file said the same thing here until its sweep landed, and was
    then caught up to the swept truth. Until then the claim worth pinning is
    that the registration came first: no row carries this sweep id, no task of
    the action exists to have produced one, and the sweep-id set the logs carry
    is the eight rounds that precede this one.

    Selected by **sweep id** over every log in the directory and never by a log
    filename, which is the discipline the whole round is run under.
    """
    assert not [run for run in runs if run.sweep == _SWEEP], (
        "a round-9 row exists: this file's last test is now the round-8 "
        "catch-up one, and the record's own suite takes the verdicts"
    )
    assert not [task for task in tasks.values() if task.category == _CATEGORY]

    # `None` is round 1, which predates `--sweep` and is keyed on `as_of`.
    assert {run.sweep for run in runs} == {
        None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
        "round-8",
    }
