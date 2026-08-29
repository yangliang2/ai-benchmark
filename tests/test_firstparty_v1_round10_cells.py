"""Round 10's pre-registration, pinned: what section 83 of the design note
commits to before the round's first paid call.

Round 10 is one half rather than two. §82.1 keeps the instrument whole, so the
repaired read of the archive costs no new call and there is no paid experiment
to register in front of the authoring — what §83 registers is the reopen that
licenses the round, the instrument it runs on, the A″ readings that gate
nothing, the round's one hard gate (the two-sided proofs), both prices, the
nine cells and the limits in force. §46 did the one-half job for round 5, §52
for round 6, §59 for round 7 and §68 for round 8; §77 did the two-half job for
round 9, and the shape here is §77's with the experiment half gone.

Three disciplines are inherited from `test_firstparty_v1_round9_cells.py`
rather than re-argued.

**The register is the design note**, not a constant in code — the note is what
a reader of the round consults and what a reviewer holds the round to — so
every test below parses section 83's own fenced blocks and its own prose and
then re-derives each claim from the corpus: from the task set, from the price
table, from the live grader module and from the checked-in run logs. A
registration whose arithmetic cannot be reproduced is a number somebody wrote
down, and a register that drifts from the corpus it registers is the exact
defect this file exists to catch.

**No test here selects a run log by filename.** Logs are collected wholesale
and rows are keyed on what they carry — a task, an agent, a model, a sweep
id — which is the sweep protocol's rule after the first pass of the round-1
analysis silently dropped two paid cells by filtering on a name.

**The section is sliced deliberately**, from §83's own top-level heading to the
next top-level heading, and never to `## Open questions`
(`docs/agents/runbook-grader-v2-gate.md:153`): a slice that runs to the note's
trailing headings swallows whole sections silently, and every pin in this file
would then read as met on text §83 never wrote.

Nothing here calls the grader, runs a live cell or spends a dollar. The last
two tests read the round forwards: no `round-10` row exists yet, and the id
register §83.7 left to be filled now names the three `investigation` tasks —
checked against the corpus, which holds those three and no fourth.
"""

import json
import re
from pathlib import Path

import pytest

from ai_benchmark import (
    agents,
    firstparty,
    firstparty_v1,
    point_grader,
    pricing,
    reconcile_v1,
)
from ai_benchmark.schema import TaskCategory

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_RULINGS = _REPO / "data" / "first-party-v1-rulings"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 10 cells and cost — registered 2026-08-23"

# The record §83.1 reopens a sentence of. Sliced the same deliberate way, so
# that the quote below is checked against §81's own words rather than against a
# string typed twice in this file.
_V2_RECORD_HEADING = "## Round 9 v2 record — 2026-08-23"

_SWEEP = "round-10"

# The three standing columns, unchanged from rounds 7 and 8 and written
# agent-first because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the sweep's per-cell anchor comes from, named by its sweep id
# because that is what identifies a round. Round 9 never swept, so round 8 is
# still the nearest anchor the corpus has.
_ANCHOR_ROUND = "round-8"

# The action the round sweeps, and how many tasks of it it authors. Typed as
# the corpus's own category literal, because it indexes registries keyed on it.
_CATEGORY: TaskCategory = "investigation"
_CELLS = 3

# The one number in force for every cell of this round, reached by the fallback
# rather than by a row: `investigation` registers nothing.
_LIMIT_S = 600

# The four categories `LIVE_RUN_LIMITS_S` carried when this round ran, which
# its own registration does not touch: round 4's two by §37 and round 5's
# two by §46.
_REGISTERED_LIMITS = {"bug-fix", "fault-location", "code-review",
                      "codebase-comprehension"}

# Registered after this round, and subtracted from the live table below rather
# than swallowed by it: round 13 (design note 118.9) registers
# `performance-optimisation` at the same 600. Every limit claim here is about
# the rows in force when this round ran, so the later entry is named explicitly
# and the next addition has to be a visible edit here too.
_LATER_LIMITS = {"performance-optimisation"}

# The convention the proofs' token arithmetic is done at.
_CHARS_PER_TOKEN = 4

# What the pricing page's `deepseek-v4-pro` column said when §83.5's pinned
# `curl` was run, per million tokens. **Peak-hour** prices, which is what the
# round is registered at — the conservative end of the vendor's peak/off-peak
# schedule — and the **cache-miss** input price, which is the conservative end
# a second time. The section carries the URL and the as-of date beside them,
# and both are asserted to be inside §83's own slice.
_DEEPSEEK_INPUT_PER_MTOK = 1.32
_DEEPSEEK_OUTPUT_PER_MTOK = 3.96
_DEEPSEEK_CACHE_HIT_PER_MTOK = 0.044
_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"
_AS_OF = "2026-08-23"

# §83.5's per-call character assumptions, reused from §77.4 unchanged: a proof
# answer at 4,000 characters low and 8,000 high, and a 200-character point
# beside the template. The template's own length is **not** a literal here —
# it is read from `point_grader.PROMPT`, which is what §83.5 registers.
_PROOF_ANSWER_LOW = 4000
_PROOF_ANSWER_HIGH = 8000
_POINT_CHARS = 200

# §80.5's freezing rule, carried forward in one line: this suite reaches the
# live `point_grader.GRADER_VERSION` and `point_grader.PROMPT`, so when the
# instrument next moves it freezes to the tuple and the template length this
# registration was written under — literals with a comment naming this section,
# exactly as §77's suite froze to v1's.


def note_section() -> str:
    """Section 83, from its own heading to the next top-level one.

    Deliberately sliced: a slice that ran to `## Open questions` would swallow
    every section written after this one, and each pin below would then pass on
    text §83 never wrote. `docs/agents/runbook-grader-v2-gate.md:153` is where
    that rule is written down, after §79's suite came within one section of the
    accident.
    """
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


_REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def register_ids() -> dict[str, str]:
    """§83.7's filled id register: task id → gloss, parsed from the one
    fenced block whose every line is an id line.

    Found by shape rather than by position or by a quoted id — the same rule
    `block_holding` applies — so removing the register fails loudly and a
    second id-shaped block appearing in the section is caught as the
    ambiguity it would be. Before the fill, the same shape check asserted no
    such block existed anywhere in the section.
    """
    found: list[dict[str, str]] = []
    for block in blocks():
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        matches = [_REGISTER_LINE.fullmatch(line) for line in lines]
        if lines and all(matches):
            found.append({
                match.group(1): match.group(2) or ""
                for match in matches
                if match is not None
            })
    assert len(found) == 1, "exactly one fenced block of §83 is the id register"
    return found[0]


_ITEM = re.compile(r"^\*\*83\.(\d*) ", re.MULTILINE)


def item(number: str) -> str:
    """One numbered item of §83, collapsed, from its own bold number to the
    next one — so that a claim registered about the proofs gate can be checked
    *inside the proofs gate's clause* rather than anywhere in the section."""
    section = note_section()
    found = list(_ITEM.finditer(section))
    assert found, "§83 numbers its items"
    for index, match in enumerate(found):
        if (match.group(1) or "0") != number:
            continue
        end = found[index + 1].start() if index + 1 < len(found) else len(section)
        return " ".join(section[match.start():end].split())
    raise AssertionError(f"§83 carries no item {number!r}")


def v2_record() -> str:
    """§81, sliced the same deliberate way and collapsed. The sentence §83.1
    reopens is read out of here, so the quote is held against the record's own
    words."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{_V2_RECORD_HEADING}\n")
    assert len(body) == 2, f"the note carries exactly one {_V2_RECORD_HEADING!r}"
    return " ".join(body[1].split("\n## ")[0].split())


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


def test_the_section_takes_the_next_free_number_before_the_first_paid_call() -> None:
    """§83 is the next free number, it is a pre-registration, and it sits where
    a section of the note goes.

    The note numbers its sections once and never renumbers them, so a section
    taking a number already spent is a citation collision every later record
    inherits. §82 (round 10's rulings, including §82.5's same-day supersession)
    is what this follows; §84 is what the A″ readings took, which the section
    said in a line so that whoever wrote them did not re-derive the frontier —
    and they have since landed there, with the round's record (§85-§93) after
    them, which is why the heading after this one is theirs and the live
    frontier is the round-9 suite's assertion rather than this file's.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(82) == 1, "the round-10 rulings, spent once"
    assert numbered.count(83) == 1, "this pre-registration, spent once"
    assert numbered.count(84) == 1, "the A″ readings §83.3 sent to §84"
    # The frontier claim this test carried — §85 still free — was spent when
    # the round's record took §85-§93; the frontier itself is the round-9
    # suite's to assert (one assertion, moved deliberately, never copied).
    # What survives here is the claim that outlasts it: §83's number is spent
    # once and the record renumbered nothing above or below it.
    assert all(numbered.count(number) == 1 for number in range(85, 94)), (
        "round 10's record, §85-§93, each spent once"
    )
    # §94 (round 11's rulings, 2026-08-25), §95 (round 11's pre-registration),
    # §96 (round 11's amendment, both 2026-08-26), §97-§105 (round 11's
    # record, 2026-08-27), §106 (round 12's rulings), §107 (round 12's
    # pre-registration), §108-§116 (round 12's record, all 2026-08-28), §117
    # (round 13's rulings), §118 (round 13's pre-registration) and §119-§127
    # (round 13's record, all 2026-08-29) have since landed after the record:
    # the contiguity claim extends over all of them, and the live frontier
    # stays the round-9 suite's one moved assertion.
    assert [number for number in numbered if number > 68] == list(range(69, 128)), (
        "the rounds since 68 are contiguous and nothing was renumbered"
    )

    # And it lands before the note's trailing headings rather than after them.
    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    assert headings.index(_HEADING) == headings.index(
        "## Round 10 rulings — 2026-08-23"
    ) + 1, "§83 follows §82's own heading"
    assert headings[headings.index(_HEADING) + 1].startswith(
        "## Round 10 A″ readings"
    ), "§84 is what §83.3 sent to the next free number, and it lands next"

    counted = prose()
    assert "This is round 10's pre-registration and nothing else" in counted
    assert "written down before the first paid call" in counted
    assert "**no paid experiment at all**" in counted
    assert "**zero new paid calls**" in counted
    assert "**the next free section numbers**, §84 onward" in counted
    assert "nothing below is a result, and nothing above is renumbered" in counted


def test_the_vendor_closure_is_reopened_on_premise_failure_in_as_many_words() -> None:
    """§83.1: §81's own sentence, quoted, and reopened the way §78.1 reopened
    §76.7.

    A closure ruled on a premise its own evidence later falsified is not
    reversed and is not quietly ignored: it is reopened, and the premise that
    failed is named. That pattern has a precedent in this note and §83.1 cites
    it rather than inventing a second shape for the same move.

    What makes the quote a quote is checked rather than trusted: both fragments
    are read out of §81's own slice and asserted to be verbatim substrings of
    it, so a paraphrase drifting into §83 fails here instead of standing as a
    quotation of words the record never used.
    """
    reopened = item("1")
    record = v2_record()

    for fragment in (
        "closes the question of this vendor's grader",
        "no third run is attempted under this vendor",
    ):
        assert fragment in record, f"§81's own words: {fragment!r}"
        assert fragment in reopened, f"§83.1 quotes them: {fragment!r}"

    # Quoted as one sentence with its elision marked, not stitched silently.
    assert (
        '"closes the question of this vendor\'s grader… no third run is '
        'attempted under this vendor"'
    ) in reopened

    # The premise, and that it failed rather than was overruled.
    assert "**before the pointer finding existed**" in reopened
    assert "on the premise that a second failure would be the instrument's" in reopened
    assert "**thirteen of the seventeen disagreements**" in reopened
    assert (
        "**§78.1 reopened §76.7: not a reversal, a premise failure**"
    ) in reopened
    assert "recorded in as many words" in reopened

    # And §81 is left alone, which is what keeps the reopen honest.
    assert "**§81 itself is not edited.**" in reopened
    assert "its 358 rulings untouched" in reopened
    assert (
        "no round-9 section, archive or pin suite is altered by this "
        "registration"
    ) in reopened


def test_the_instrument_is_quoted_from_the_code_and_does_not_move() -> None:
    """§83.2: the pinned tuple, read out of `point_grader.GRADER_VERSION`.

    §82.1 keeps the instrument whole, so this round registers what §80.4
    registered — the same alias, the same announced checkpoint, the same prompt
    hash — and the register's honesty is that the string was read rather than
    retyped. That is what is checked: the fenced block equals the live tuple,
    and its three parts equal the module's own three constants.

    The stop is the other half. This vendor's API takes only a moving alias, so
    a checkpoint that moves under it is a version change, and a version change
    mid-round would forfeit the round's one material asset — §81's 358 archived
    rulings, readable by deliverable hash only while the version they were
    archived under is the version in force.
    """
    registered = block_holding(point_grader.GRADER_MODEL).strip()
    assert registered == point_grader.GRADER_VERSION
    alias, checkpoint, prompt_hash = registered.split(":")
    assert (alias, checkpoint) == (
        point_grader.GRADER_MODEL, point_grader.GRADER_CHECKPOINT,
    )
    assert prompt_hash and len(registered.split(":")) == 3

    # Read, not remembered: the command the register was filled from.
    read_with = block_holding("GRADER_VERSION").strip()
    assert read_with == (
        "uv run python -c 'from ai_benchmark import point_grader as p; "
        "print(p.GRADER_VERSION)'"
    )

    quoted = item("2")
    assert "quoted from the code and never retyped" in quoted
    assert "**the same alias**" in quoted
    assert "**the same announced checkpoint**" in quoted
    assert "**the same prompt hash**" in quoted
    assert "**low reasoning effort, temperature 0, JSON output**" in quoted
    assert "nothing about it moves" in quoted

    # The stop, and what a movement would cost.
    assert (
        "**checkpoint movement discovered en route is a version change**"
    ) in quoted
    assert "**stops the round for re-registration**" in quoted
    assert (
        "**the 358 archived rulings of §81's run stay readable by deliverable "
        "hash**"
    ) in quoted
    assert "opens a new rulings file (§77.8)" in quoted

    # And the settings are the settings the client actually sends.
    grader_source = (_REPO / "src" / "ai_benchmark" / "point_grader.py").read_text(
        encoding="utf-8"
    )
    for setting in (
        'reasoning_effort="low"',
        "temperature=0",
        'response_format={"type": "json_object"}',
    ):
        assert setting in grader_source, setting


def test_the_a_double_prime_readings_are_readings_and_gate_nothing() -> None:
    """§83.3: two operationalisations, both reported, neither gating.

    §82.5 superseded §82.3's first gate the same day it was ruled, because a
    gate whose verdict flips on tokenisation minutiae certifies nothing. So the
    re-read is registered as **readings**, computed offline under both
    mechanical definitions, and the honesty of registering a derivation whose
    outcome is already knowable is carried by saying so rather than by pretending
    otherwise.

    What this test refuses is a bar sneaking back in: no threshold, no count and
    no outcome figure belongs in a registration whose report is a section away.
    """
    readings = item("3")

    assert "**readings and not a gate**" in readings
    assert "**The A″ readings gate nothing**" in readings
    assert "the round's only gate is 83.4's" in readings
    assert "**file-reference**" in readings
    assert "**file-or-symbol**" in readings
    assert "**both** operationalisations" in readings
    assert "**neither is tuned into gating**" in readings
    assert "committed v2 archive" in readings
    assert "computed **offline**" in readings

    # The disclosure, in as many words.
    assert (
        "**The A″ read is a derivation over spent rulings, and its outcome is "
        "knowable at registration time.**"
    ) in readings
    assert (
        "It is not a blind pre-registration and does not claim to be one."
    ) in readings
    assert "the filter's independence from every verdict" in readings

    # Where they land, and that this section does not report them.
    assert "**Where they land: §84**" in readings
    assert "the next free number after this section" in readings
    assert "**No reading's numbers appear here**" in readings
    assert "§83 registers and §84 reports" in readings

    # No bar and no outcome: §82.5's own figures stay in §82.5 and in §84.
    for outcome in ("42 of 46", "44 of 48", "≥ 42", "≥ 44", "%"):
        assert outcome not in readings, outcome
    assert not re.search(r"\bbar\b", readings), "a reading has no bar"


def test_the_proofs_are_the_rounds_one_gate_stated_as_a_quantifier() -> None:
    """§83.4: the round's single hard gate, and the bar it is read at.

    §82.5 moved the round's gate onto the two-sided proofs, and a proofs gate
    has one property the calibration bar never had: it is a **universal
    quantifier**, so there is nothing in it to round and nothing in it to tune.
    Writing it as a percentage would give it both back, which is why no `%`
    belongs anywhere in this item's clause and this test says so mechanically.

    The check is not new code and this test proves it is not: the rule the
    section names is a live function of the lint, and the lint that calls it is
    offline by construction.
    """
    gate = item("4")

    assert "The round's single hard gate: the two-sided proofs, before the " \
        "first sweep dollar.**" in gate
    assert "it is the only gate round 10 has" in gate
    assert (
        "stated as a quantifier and never as a percentage"
    ) in gate
    assert (
        "**every planted point of every task's reference answer resolves, and "
        "every foil answer fails**"
    ) in gate
    assert "read offline from the archived rulings" in gate
    assert "no fraction met, no proportion computed, no threshold" in gate

    # Stated as a quantifier means no percentage anywhere in the clause.
    assert "%" not in gate
    assert not re.search(r"\d+\s*(?:of|/)\s*\d+", gate), (
        "a universal quantifier is not a ratio"
    )

    # The named check exists, is the lint's, and reaches no network.
    assert "`_the_reference_resolves_and_the_foil_fails`" in gate
    assert "(`src/ai_benchmark/firstparty_v1.py`)" in gate
    assert "**`ai-bench lint-v1`**" in gate
    assert "**never calls the LLM**" in gate
    assert "`ai-bench prove-points-v1`" in gate
    assert (
        firstparty_v1.EXISTENCE_PROOFS[_CATEGORY].check
        is firstparty_v1._the_reference_resolves_and_the_foil_fails
    ), "the rule §83.4 names is the one the lint runs for this action"
    assert hasattr(firstparty_v1, "prove_points"), (
        "and the writer the archived rulings come from"
    )

    # The kill discipline, in its one standing sentence.
    assert (
        "**The kill discipline, in its one standing sentence: a failed proof "
        "stops the round with a record, heap 3 stays empty, disclosed.**"
    ) in gate


def test_the_proofs_are_priced_over_counted_calls_at_prices_that_were_fetched() -> None:
    """§83.5: 24–48 calls, priced from the fetched page, with both ends stated.

    The unit is the **call**, because the writer calls once per planted point
    *and* once per disqualifier against each of the two answers. The call range
    is re-derived here from the section's own registered assumption rather than
    read off its total, which is the point of restating the 0–2 disqualifier
    count in the register: a task that declares a third puts the round outside
    this registration instead of being absorbed by it.

    The characters are re-derived from `point_grader.PROMPT` rather than carried
    from §77.4, because the template moved with grader v2 and a price counted
    over a stale template is a price for a different instrument. §80.5's
    freezing rule applies to that read: when the instrument next moves, this
    figure freezes to a literal with a comment naming §83.

    A model's memory of a pricing page is not a source, so the URL and the date
    are asserted to be inside §83's own slice and the arithmetic is redone at
    the figures they carry.
    """
    # The call range, re-derived from the registered assumption.
    counts = block_holding("reference + foil")
    match = re.search(
        r"(\d+) tasks x \((\d+)-(\d+) points \+ (\d+)-(\d+) disqualifiers\) "
        r"x \(reference \+ foil\)",
        counts,
    )
    assert match is not None, counts
    tasks_n, points_low, points_high, disq_low, disq_high = (
        int(group) for group in match.groups()
    )
    assert (tasks_n, disq_low, disq_high) == (_CELLS, 0, 2)
    per_task_low = (points_low + disq_low) * 2
    per_task_high = (points_high + disq_high) * 2
    low_calls = tasks_n * per_task_low
    high_calls = tasks_n * per_task_high
    assert (per_task_low, per_task_high) == (8, 16)
    assert (low_calls, high_calls) == (24, 48)
    assert (
        f"= {per_task_low}-{per_task_high} calls a task = "
        f"{low_calls}-{high_calls} calls for the round"
    ) in counts

    counted = prose()
    assert "**The assumed disqualifier count is 0–2 a task**" in counted
    assert "forces a re-registration rather than being absorbed by it" in counted

    # The fetch itself, pinned as the command that was run.
    assert block_holding(_PRICING_URL).strip() == f"curl -sL {_PRICING_URL}"
    assert f"`source_url`: `{_PRICING_URL}`" in counted
    assert f"`as_of`: **{_AS_OF}**" in counted
    assert f"column **{point_grader.GRADER_MODEL}**" in counted
    assert f"**${_DEEPSEEK_INPUT_PER_MTOK} / MTok** peak input on a cache" in counted
    assert (
        f"**${_DEEPSEEK_CACHE_HIT_PER_MTOK} / MTok** peak input on a cache hit"
    ) in counted
    assert f"**${_DEEPSEEK_OUTPUT_PER_MTOK} / MTok** peak output" in counted
    assert (
        f"**${_DEEPSEEK_INPUT_PER_MTOK}/MTok in and "
        f"${_DEEPSEEK_OUTPUT_PER_MTOK}/MTok out**"
    ) in counted
    assert "**This round is registered at peak-hour list pricing, cache-miss " \
        "throughout**" in counted
    assert "**no hit rate is claimed here**" in counted

    # The off-peak rule, recorded as read from this fetch.
    assert (
        '"Off-peak rates are half of the peak rates. Peak hours are 01:00 - '
        '04:00 and 06:00 - 10:00 UTC, Monday through Friday (all other hours '
        'are off-peak)."'
    ) in counted

    # The arithmetic, redone at the live template's length.
    template = len(point_grader.PROMPT)
    surround = template + _POINT_CHARS
    assert f"**{template:,}** characters" in counted
    assert f"**{surround:,}** characters a call" in counted

    per_input = _DEEPSEEK_INPUT_PER_MTOK / 1e6
    per_output = _DEEPSEEK_OUTPUT_PER_MTOK / 1e6
    low_in = low_calls * (_PROOF_ANSWER_LOW + surround) // _CHARS_PER_TOKEN
    high_in = high_calls * (_PROOF_ANSWER_HIGH + surround) // _CHARS_PER_TOKEN
    low_out = low_calls * 100
    high_out = high_calls * (_PROOF_ANSWER_HIGH // _CHARS_PER_TOKEN + 300)
    assert (low_in, high_in) == (33966, 115932)
    assert (low_out, high_out) == (2400, 110400)

    total_low = round(low_in * per_input + low_out * per_output, 4)
    total_high = round(high_in * per_input + high_out * per_output, 4)
    assert (total_low, total_high) == (0.0543, 0.5902)
    # The registered range holds the arithmetic, rounded outward at both ends.
    assert 0.05 <= total_low and total_high <= 0.6

    arithmetic = block_holding("round total")
    for line in (
        f"proofs  low   {low_calls} calls x "
        f"{_PROOF_ANSWER_LOW + surround:,} chars / {_CHARS_PER_TOKEN}     "
        f"=  {low_in:,} tok  x ${_DEEPSEEK_INPUT_PER_MTOK}/M = "
        f"${round(low_in * per_input, 4):.4f}",
        f"              {low_calls} x 100 tok thinking          "
        f"=   {low_out:,} tok  x ${_DEEPSEEK_OUTPUT_PER_MTOK}/M = "
        f"${round(low_out * per_output, 4):.4f}",
        f"        high  {high_calls} calls x "
        f"{_PROOF_ANSWER_HIGH + surround:,} chars / {_CHARS_PER_TOKEN}     "
        f"= {high_in:,} tok  x ${_DEEPSEEK_INPUT_PER_MTOK}/M = "
        f"${round(high_in * per_input, 4):.4f}",
        f"              {high_calls} x (2,000 quoted + 300)      "
        f"= {high_out:,} tok  x ${_DEEPSEEK_OUTPUT_PER_MTOK}/M = "
        f"${round(high_out * per_output, 4):.4f}",
        f"round total   ${total_low:.4f} - ${total_high:.4f}",
    ):
        assert line in arithmetic, line

    assert "The proofs' price: $0.05–0.6" in counted
    assert "at peak-hour list price" in counted
    assert "counted over calls" in counted
    assert "the registered range is **$0.05–0.6**" in counted

    # Which half is an assumption, named — and this round both halves are,
    # because the answers the input half is counted over do not exist yet.
    assert "**Which half is an assumption, named — and this round both halves " \
        "are.**" in counted
    assert "**This round's do not**" in counted
    assert f"at **{_PROOF_ANSWER_LOW:,} characters** at the low end" in counted
    assert f"and **{_PROOF_ANSWER_HIGH:,}** at the high" in counted
    assert "**The output half is the half with no anchor**" in counted
    assert "The high end is a bound and not an expectation" in counted
    assert "**never enter `unified.jsonl`**" in counted


def test_the_sweep_range_is_derived_from_the_checked_in_round_8_rows(
    runs: list[firstparty_v1.Run],
) -> None:
    """§83.6's arithmetic, recomputed from the rows it claims to read.

    Round 9 never swept, so the anchor is still round 8's nine cells — the same
    three combinations over the same nine-cell shape — selected by **sweep id**
    over every log in the directory and never by a log filename. Every figure
    the section quotes is re-derived here rather than lifted from §77.5, which
    is the whole point of re-deriving it there too: a registration that copied
    its predecessor would inherit its predecessor's arithmetic without ever
    checking that the anchor rows still say it.

    Both ends of the bound are recomputed too. Round 10 sweeps three cells on
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
    assert "**Round 9 never swept**" in counted
    assert f"selected by sweep id `{_ANCHOR_ROUND}`" in counted
    assert "**never by a log's filename**" in counted
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
    assert "roughly **1.8×** the flat extrapolation" in counted
    assert "the range's floor *is* the flat extrapolation" in counted
    assert "a finding about the action and not an accounting surprise" in counted
    assert "an investigation that reads the whole repository on every turn" in counted
    assert "**$5 is where the record is to stop and say so**" in counted

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
    """§83.7: three tasks × three columns, the sweep id, the dry cell, and the
    id register — registered empty, filled by the round's second authoring
    ticket exactly where the section left it.

    What this checks is the registration's shape: the columns, the count, the
    language, the control declaration and the sweep's invocation, plus both
    halves of the register's story — the section's own record that the
    register was left explicitly to be filled in before the sweep, and the
    filled register now standing where it said it would. What the register's
    ids claim about the corpus is the forward-reading test's at the end of
    this file.
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
        "**round 10 moves no knob's counter and the kill discipline does not "
        "count it**"
    ) in counted
    assert f"`calibrate-v1` gains no `{_CATEGORY}` multiplier row" in counted

    # The register: left for the authoring ticket, said to be left, and now
    # filled where the section said it would be. The registration-time prose
    # stays as the record it is — it was true as written — and the fill is
    # dated and attributed rather than blended into it.
    assert "**The three task ids do not exist yet.**" in counted
    assert (
        "**the id register for round 10 is left explicitly to be filled in, in "
        "this section, before the sweep, by the round's second task-authoring "
        "ticket**"
    ) in counted
    assert f"corpus holds no `{_CATEGORY}` task as this is written" in counted
    assert "**disclosed zero**" in counted
    assert (
        "**Filled in 2026-08-24, by that ticket, exactly where this section "
        "left it.**"
    ) in counted
    assert "**This list is the register.**" in counted
    assert f"**every `{_CATEGORY}` task the corpus holds**" in counted
    assert (
        "the round sweeps the action entire and re-runs nothing any "
        "combination has already answered"
    ) in counted

    # That claim was true of the corpus when §83 was registered and stayed
    # true until the round's first authoring ticket landed task 1; the prose
    # stays a record of the registration, and the live half of the claim is
    # caught up to the landed truth: the zero row is gone, the category
    # counts, and how many it counts is the forward-reading test's below.
    table = firstparty_v1.coverage_table(list(tasks.values()))
    assert (_CATEGORY, "-", "-", 0) not in table
    assert [row for row in table if row[0] == _CATEGORY and row[3]]

    # Exactly one fenced block of the section is a register of task ids —
    # the one the fill wrote, in §68.1's form: an id a line, each with a
    # one-line gloss. Before the fill this asserted no such block existed;
    # what the ids claim about the corpus is the forward-reading test's.
    assert len(register_ids()) == _CELLS
    for task_id, gloss in register_ids().items():
        assert gloss, f"{task_id}: a register line carries its gloss"

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
    """§83.8: one ceiling over the round, reached by the fallback.

    `investigation` joins no `LIVE_RUN_LIMITS_S` row, so its nine cells run at
    the flat default — numerically the same 600 seconds the four registered
    categories carry, which is what keeps the round free of a ceiling
    difference and free of a cross-round caveat. The distinction matters
    anyway, because only a registered category's cell can later be described as
    running "under the registered 600 s", and the record is to say "at the flat
    default" instead.

    Registering is a deliberate act: §82 rules nothing about run-time limits,
    and §68.5's precedent is that a new action joins no register for exactly
    that reason. So this is a test that a row was *not* added.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) - _LATER_LIMITS == _REGISTERED_LIMITS, (
        "this registration adds nothing new"
    )
    assert _CATEGORY not in firstparty_v1.LIVE_RUN_LIMITS_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S, "the flat default is the same number"

    counted = prose()
    assert "**`investigation` joins none of them**" in counted
    assert "This ticket adds no row and **changes no code**" in counted
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


def test_no_new_sweep_row_lands_before_the_rounds_own_sweep(
    logs: list[Path], runs: list[firstparty_v1.Run]
) -> None:
    """§83.9: the archive the A″ readings are derived over, held still.

    Landed form: the round's own sweep (2026-08-24-r10-a..d) is the one
    arrival the registered sentence allowed, and nothing else landed before
    it; round 11's sweep, landing after, is scoped back out by sweep id.

    §80.4's guardrail carried forward, for this round's own reason: §84's
    readings are a derivation over the archive as it stands, so a sweep row
    landing between this registration and the round's own sweep would move the
    denominator out from under a reading already registered as knowable.

    The split is re-derived here from the logs themselves — wholesale, keyed on
    what the rows carry and never on a filename — rather than taken from the
    section's prose, which is what makes the registered sentence a claim about
    the corpus and not about itself.
    """
    # Landed form: the archive grew by exactly the round's own sweep and by
    # nothing else — 37 logs and 306 rows at registration, plus the sweep's
    # four logs and nine `round-10` rows, keyed on what the rows carry.
    # Round 11's sweep has since landed nine `round-11` rows in four more
    # logs (2026-08-26), round 12's nine `round-12` rows in four more
    # (2026-08-28) and round 13's nine `round-13` rows in four more
    # (2026-08-29); a claim about what stood between this registration and
    # the round's own sweep scopes them back out by sweep id, never by a log
    # filename.
    assert len(logs) == 53
    assert len(runs) == 342
    late = [run for run in runs if run.sweep == _SWEEP]
    assert len(late) == _CELLS * 3
    since = [
        run for run in runs
        if run.sweep in {"round-11", "round-12", "round-13"}
    ]
    assert len(since) == 27
    assert len(runs) - len(late) - len(since) == 306, (
        "nothing else landed in between"
    )

    counted = prose()
    assert (
        "No new sweep row lands between this registration and the round's "
        "own sweep.**"
    ) in counted
    assert "**306 archived answers in 37 run logs, stratum A 63 of them**" in counted
    assert "**the split this section registers**" in counted
    assert "Run before the round's own sweep it must print nothing" in counted

    check = block_holding("-newermt").strip()
    assert check == f"find data/first-party-v1-runs -type f -newermt {_AS_OF}"


def test_the_round_10_cells_are_the_nine_registered(
    runs: list[firstparty_v1.Run],
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The first forward-reading test, in its landed form.

    Its first form said no `round-10` row existed yet — a registration, not a
    record — and was retired by the sweep it foresaw (2026-08-24-r10-a..d,
    dry cell first). What it holds the round to now is the landed version of
    the same claim: the cells carrying sweep id `round-10` are exactly the
    nine §83.7 registered — the register's three tasks under the three
    standing combinations — none repeated, and every one has archived
    per-run rulings, so its verdict is a pure function of what is checked in.

    Selected by **sweep id** over every log in the directory and never by a log
    filename, which is the discipline the whole round is run under.
    """
    swept = [run for run in runs if run.sweep == _SWEEP]
    cells = {(run.task_id, run.agent, run.model) for run in swept}
    assert len(swept) == len(cells) == _CELLS * 3, "nine cells, none repeated"
    assert cells == {
        (task_id, agent, model)
        for task_id in register_ids()
        for agent, model in (
            ("claude-code", "claude-haiku-4-5"),
            ("claude-code", "claude-sonnet-5"),
            ("codex", "gpt-5.6-terra"),
        )
    }
    for task_id, agent, model in sorted(cells):
        assert firstparty_v1.rulings_file(
            _RULINGS, task_id, agent, model
        ).is_file(), f"{task_id} x {agent} x {model}: archived rulings"

    # `None` is round 1, which predates `--sweep` and is keyed on `as_of`;
    # `round-11` joined on 2026-08-26, when heap 3's second action's sweep
    # landed, `round-12` on 2026-08-28, when its last action's did, and
    # `round-13` on 2026-08-29, when heap 4's one action's did.
    assert {run.sweep for run in runs} == {
        None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
        "round-8", _SWEEP, "round-11", "round-12", "round-13",
    }


def test_the_register_names_every_investigation_task_and_each_is_proved(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The second forward-reading test, in its final form: the register check.

    Its first form said the corpus held no `investigation` task; ticket 05
    caught it up to "task 1 and no second or third yet"; the round's second
    authoring ticket landed the other two and filled §83.7's register, which
    is the form this test now holds the round to. The register is read
    against the corpus rather than restated: the three ids exist, they are
    exactly the `investigation` tasks the corpus holds — no fourth anywhere —
    every one is the Python application-surface declared control §83.7
    registered, and each ships a points key and a two-sided proof that is
    green under the pinned instrument, the verdicts recomputed through
    `_point_verdict` rather than taken on the archives' word.
    """
    register = register_ids()
    authored = sorted(
        task_id for task_id, task in tasks.items() if task.category == _CATEGORY
    )
    assert sorted(register) == authored, "the register is the corpus, whole"
    assert len(register) == _CELLS, "and the corpus holds no fourth"

    for task_id in register:
        task = tasks[task_id]
        assert task.category == _CATEGORY
        assert task.language == "python"
        assert task.surface == "application"
        assert task.control is True
        assert task.construction is None

        key = firstparty_v1.points_key(task)
        questions = firstparty_v1._point_questions(key)
        for side in firstparty_v1.PROOF_SIDES:
            answer = (task.proofs_dir / side.answer_file).read_text(
                encoding="utf-8"
            )
            raw = firstparty_v1.proof_rulings_file(task, side).read_text(
                encoding="utf-8"
            )
            archive = firstparty_v1.ProofRulings.model_validate(json.loads(raw))
            assert archive.grader_version == point_grader.GRADER_VERSION
            assert firstparty_v1._point_verdict(
                questions, archive, answer
            ) is side.resolves, f"{task_id}: {side.name}"
