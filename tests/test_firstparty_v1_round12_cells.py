"""Round 12's pre-registration, pinned: what section 107 of the design note
commits to before the round's first paid call.

Round 12 is one half rather than two, the way rounds 10 and 11 were. §103
confirmed the instrument's record on heap 3's second action, so there is no
paid experiment to register in front of the authoring — what §107 registers is
the instrument the round runs on, the action and the sentence that licenses it,
§106.1's recall ruling as an authoring rule, the deliverable's shape, the
round's one hard gate (the two-sided proofs), both prices, the nine cells, the
limits in force and the guardrail on the anchor. §46 did the one-half job for
round 5, §52 for round 6, §59 for round 7, §68 for round 8, §83 for round 10
and §95 for round 11; §77 did the two-half job for round 9, and the shape here
is §95's a round on.

Three disciplines are inherited from `test_firstparty_v1_round11_cells.py`
rather than re-argued.

**The register is the design note**, not a constant in code — the note is what
a reader of the round consults and what a reviewer holds the round to — so
every test below parses section 107's own fenced blocks and its own prose and
then re-derives each claim from the corpus: from the task set, from the price
table, from the live grader module and from the checked-in run logs. A
registration whose arithmetic cannot be reproduced is a number somebody wrote
down, and a register that drifts from the corpus it registers is the exact
defect this file exists to catch.

**No test here selects a run log by filename.** Logs are collected wholesale
and rows are keyed on what they carry — a task, an agent, a model, a sweep
id — which is the sweep protocol's rule after the first pass of the round-1
analysis silently dropped two paid cells by filtering on a name.

**The section is sliced deliberately**, from §107's own top-level heading to
the next top-level heading, and never to `## Open questions`
(`docs/agents/runbook-grader-v2-gate.md:153`): a slice that runs to the note's
trailing headings swallows whole sections silently, and every pin in this file
would then read as met on text §107 never wrote.

Nothing here calls the grader, runs a live cell or spends a dollar. The last
two tests read the round forwards, and they are two tests rather than one
because they die at different tickets: no `round-12` row exists yet — retired
by the ticket that landed the sweep (2026-08-28-r12-a..d, dry cell first) and
replaced with the landed form of the same claim, the nine cells carrying sweep
id `round-12` being exactly the nine §107 registered — and, as originally
written, no
`codebase-comprehension` task was point-keyed yet. That second half was
retired by the ticket that landed the round's first task, caught up to "task 1
and no second or third yet", and then replaced by the ticket that landed tasks
2 and 3 with its final form: §107.8's register — filled by that same ticket —
names exactly the point-keyed `codebase-comprehension` tasks the corpus holds,
each proved both ways and each carrying its kind of question. The claim is
still written **by key shape and never as a task count of the category**,
because the four locate-style comprehension tasks stay where they are and a
count would go red on their account rather than on the explain shape's.
"""

import json
import re
from pathlib import Path
from typing import get_args

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

_HEADING = "## Round 12 cells and cost — registered 2026-08-28"

# The rulings §107 registers, sliced the same deliberate way so that anything
# §107 claims §106 ruled is checked against §106's own words.
_RULINGS_HEADING = "## Round 12 rulings — 2026-08-28"

# The record §107.2's licence sentence is quoted out of: §103 lives inside
# round 11's record, and the quote is held against that record rather than
# against a string typed twice in this file.
_RECORD_HEADING = "## Round 11 record — 2026-08-27"

# Round 11's own pre-registration, which this section is a round on: sliced
# only to keep the two apart, never read as if it were this round's text.
_PREVIOUS_HEADING = "## Round 11 cells and cost — registered 2026-08-26"

_SWEEP = "round-12"

# The three standing columns, unchanged from rounds 7, 8, 10 and 11 and written
# agent-first because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the sweep's per-cell anchor comes from, named by its sweep id
# because that is what identifies a round. Round 11 swept nine cells of heap
# 3's second action, so it is the nearest anchor and it is one round back.
_ANCHOR_ROUND = "round-11"

# The action the round sweeps, and how many tasks of it it authors. Typed as
# the corpus's own category literal, because it indexes registries keyed on it.
# The category is not new to the corpus — it carries locate-style tasks today —
# and what this round adds is its explain shape, on a points key.
_CATEGORY: TaskCategory = "codebase-comprehension"
_ANCHOR_CATEGORY: TaskCategory = "requirement-decomposition"
_CELLS = 3

# The one number in force for every cell of this round, and — unlike round
# 11's action — reached by the category's own registered row rather than by the
# fallback. It is numerically the flat default's own value.
_LIMIT_S = 600

# The four categories `LIVE_RUN_LIMITS_S` carried when this round ran, which
# its own registration does not touch: round 4's two by §37 and round 5's
# two by §46. This round's action is already one of them, so the pin is that
# nothing moves.
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

# What the pricing page's `deepseek-v4-pro` column said when §107.6's pinned
# `curl` was run, per million tokens. **Peak-hour** prices, which is what the
# round is registered at — the conservative end of the vendor's peak/off-peak
# schedule — and the **cache-miss** input price, which is the conservative end
# a second time. The section carries the URL and the as-of date beside them,
# and both are asserted to be inside §107's own slice.
_DEEPSEEK_INPUT_PER_MTOK = 1.32
_DEEPSEEK_OUTPUT_PER_MTOK = 3.96
_DEEPSEEK_CACHE_HIT_PER_MTOK = 0.044
_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"
_AS_OF = "2026-08-28"
# §95.5's own fetch date. This round's prices had to be fetched again rather
# than carried, so the date §107 records must be this round's and not that
# one's — the figures coming back unchanged is exactly why a stale date would
# go unnoticed.
_PREVIOUS_AS_OF = "2026-08-26"

# §107.6's per-call character assumptions, reused from §83.5 unchanged for the
# third round running: a proof answer at 4,000 characters low and 8,000 high,
# and a 200-character point beside the template. The template's own length is
# **not** a literal here — it is read from `point_grader.PROMPT`, which is what
# §107.6 registers.
_PROOF_ANSWER_LOW = 4000
_PROOF_ANSWER_HIGH = 8000
_POINT_CHARS = 200

# The deliverable §106.3 ruled and §107.4 registers: one prose answer file at
# the standing heap-3 path, three sections required by name.
_ANSWER_PATH = "ANSWER.md"
_SECTIONS = (
    "What happens",
    "Why it comes out that way",
    "Boundaries and edge behavior",
)

# §80.5's freezing rule, carried forward in one line: this suite reaches the
# live `point_grader.GRADER_VERSION` and `point_grader.PROMPT`, so when the
# instrument next moves it freezes to the tuple and the template length this
# registration was written under — literals with a comment naming this section,
# exactly as §95's suite carried §83's rule forward.


def note_section() -> str:
    """Section 107, from its own heading to the next top-level one.

    Deliberately sliced: a slice that ran to `## Open questions` would swallow
    every section written after this one, and each pin below would then pass on
    text §107 never wrote. `docs/agents/runbook-grader-v2-gate.md:153` is where
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


def register_blocks() -> list[dict[str, str]]:
    """Every fenced block of §107 whose every line is an id line — §83.7's
    register form, looked for by shape rather than by position or by a quoted
    id.

    §107.8 left the register explicitly to be filled in before the sweep, and
    before the fill this found none; now that the round's second authoring
    ticket has filled it, the same shape check finds exactly one, and a second
    id-shaped block appearing anywhere in the section is caught as the
    ambiguity it would be.
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
    return found


_ITEM = re.compile(r"^\*\*107\.(\d*) ", re.MULTILINE)


def item(number: str) -> str:
    """One numbered item of §107, collapsed, from its own bold number to the
    next one — so that a claim registered about the proofs gate can be checked
    *inside the proofs gate's clause* rather than anywhere in the section."""
    section = note_section()
    found = list(_ITEM.finditer(section))
    assert found, "§107 numbers its items"
    for index, match in enumerate(found):
        if (match.group(1) or "0") != number:
            continue
        end = found[index + 1].start() if index + 1 < len(found) else len(section)
        return " ".join(section[match.start():end].split())
    raise AssertionError(f"§107 carries no item {number!r}")


def other_section(heading: str) -> str:
    """Another top-level section of the note, sliced the same deliberate way
    and collapsed — so a sentence §107 says it quotes is checked against the
    section that actually wrote it."""
    body = _NOTE.read_text(encoding="utf-8").split(f"{heading}\n")
    assert len(body) == 2, f"the note carries exactly one {heading!r}"
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
    """§107 is the next free number, it is a pre-registration, and it sits
    where a section of the note goes.

    The note numbers its sections once and never renumbers them, so a section
    taking a number already spent is a citation collision every later record
    inherits. §106 (round 12's rulings) is what this follows, and the round's
    record takes what is free after it — which the section says in a line, so
    that whoever writes it does not have to re-derive the frontier. The live
    frontier itself is the round-9 suite's one moved assertion and is
    deliberately not copied here; this suite carries the contiguity claim
    instead, extended over §107, which is the round-11 cells suite's own
    pattern.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(106) == 1, "the round-12 rulings, spent once"
    assert numbered.count(107) == 1, "this pre-registration, spent once"
    assert all(numbered.count(number) == 1 for number in range(97, 106)), (
        "round 11's record, §97-§105, each spent once and not renumbered"
    )
    # §108-§116 (round 12's record, 2026-08-28), §117 (round 13's rulings)
    # and §118 (round 13's pre-registration, both 2026-08-29) have since
    # landed after this pre-registration: the contiguity claim extends over
    # them, and the live frontier stays the round-9 suite's one moved
    # assertion.
    assert [number for number in numbered if number > 68] == list(range(69, 119)), (
        "the rounds since 68 are contiguous and nothing was renumbered"
    )

    # And it lands after §106's own heading and before the note's trailing
    # headings rather than after them.
    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    assert headings.index(_HEADING) == headings.index(_RULINGS_HEADING) + 1, (
        "§107 follows §106's own heading"
    )
    # The heading after this registration was `## Open questions` until the
    # round's own record landed there (§108-§116, 2026-08-28); the claim that
    # survives is that the registration sits inside the note's numbered run,
    # before the trailing headings — this adjacency pin moved in the commit
    # that landed the record, exactly as the round-11 cells suite's did when
    # §97-§105 landed.
    assert headings[headings.index(_HEADING) + 1].startswith("## Round 12 record"), (
        "the round's own record is what landed after it"
    )

    counted = prose()
    assert "This is round 12's pre-registration and nothing else" in counted
    assert "written down before the first paid call" in counted
    assert "**no paid experiment at all**" in counted
    assert "**No argument is reopened here.**" in counted
    assert "**the next free section numbers**, §108 onward" in counted
    assert "nothing below is a result, and nothing above is renumbered" in counted


def test_the_instrument_is_quoted_from_the_code_and_does_not_move() -> None:
    """§107.1: the pinned tuple, read out of `point_grader.GRADER_VERSION`.

    §106's opening paragraph says the instrument is §83.2's, unmoved, so this
    round registers what that section registered — the same alias, the same
    announced checkpoint, the same prompt hash — and the register's honesty is
    that the string was read rather than retyped. That is what is checked: the
    fenced block equals the live tuple, and its three parts equal the module's
    own three constants.

    The other half is what the round declined. §106.1 considered the
    instrument-side widening of the coverage question and refused it at
    §77.8's price, so this registration touches no part of the grader, and the
    section has to say so — a round that quietly moved the instrument beside a
    new action would confound the two.
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

    quoted = item("1")
    assert "quoted from the code and never retyped" in quoted
    assert "the instrument is §83.2's, unmoved" in quoted
    assert "**the same alias**" in quoted
    assert "**the same announced checkpoint**" in quoted
    assert "**the same prompt hash**" in quoted
    assert "**low reasoning effort, temperature 0, JSON output**" in quoted
    assert "nothing about it moves" in quoted

    # The declined widening, registered as declined and not re-argued.
    assert (
        "**The instrument-side widening was considered and declined**, at "
        "§106.1"
    ) in quoted
    assert "**nothing in this round touches the grader**" in quoted
    rulings = other_section(_RULINGS_HEADING)
    assert "is declined at its own price" in rulings, "§106.1's own words"

    # The stop, and what a movement would cost this round.
    assert (
        "**checkpoint movement discovered en route is a version change**"
    ) in quoted
    assert "**stops the round for re-registration**" in quoted
    assert (
        "**round 10's and round 11's proof rulings and their eighteen graded "
        "cells stay readable under the version string they were archived "
        "under**"
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


def test_the_action_and_its_licence_are_registered_without_reopening_them() -> None:
    """§107.2: the action, §103's licensing sentence quoted, and the two
    disclosed zeros.

    §106.2 is short because §103's sentence did the arguing, and this
    registration is shorter still: it names the action, quotes the licence and
    says what stays a zero. What makes the quote a quote is checked rather than
    trusted — the sentence is read out of round 11's own record slice and
    asserted to be a verbatim substring of it, so a paraphrase drifting into
    §107 fails here instead of standing as a quotation of words §103 never
    used.

    The two disclosed zeros are the other half, and they are zeros of different
    kinds: `codebase-comprehension × typescript` is a cell §76.10 keeps shut
    until the grader has a record behind it, and `performance-optimisation` is
    a whole heap this round does not take — the coverage table's own zero row,
    which is where that claim is checked.
    """
    action = item("2")
    record = other_section(_RECORD_HEADING)

    licence = (
        "the instrument's record is confirmed, so explain-style "
        "`codebase-comprehension` follows as the last mechanical fill"
    )
    assert licence in record, "§103's own words"
    assert f'"{licence}"' in action, "§107.2 quotes them, marked as a quotation"

    assert f"Explain-style `{_CATEGORY}`, on Python" in action
    assert "heap 3's **last** action" in action
    assert "the mechanical fill §103's certification sentence licensed" in action
    assert "**No design argument is reopened by this registration**" in action
    assert "**Heap 3 closes with this action**" in action

    # The two zeros, each named as the kind of zero it is.
    assert f"`{_CATEGORY} × typescript` stays a **disclosed zero**" in action
    assert "§76.10's rule keeps heap 3 on Python" in action
    assert (
        "`performance-optimisation` stays the **disclosed zero row it is**"
    ) in action

    # And the category is the corpus's own literal, not a phrase in prose.
    assert _CATEGORY in get_args(TaskCategory)
    assert "performance-optimisation" in get_args(TaskCategory)


def test_the_recall_ruling_is_registered_as_a_forward_only_authoring_rule(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§107.3: one-clause-tight points, held by nobody's lint and applied to
    nothing already written.

    §106.1 ruled the author's side of the recall fork, and the danger in
    registering it is that a reader takes it for machinery — a rule the lint
    enforces, or a rule that reaches back over round 10's and round 11's keys.
    It is neither, and the section has to say both: it is policed where
    authoring is already policed, and it is forward-only, with §104's addendum
    left standing as the permanent disclosure of the gap the older keys carry.

    The rule's own sentence is checked against §106.1's text rather than
    retyped, the same way §107.2's licence is.
    """
    recall = item("3")
    rulings = other_section(_RULINGS_HEADING)

    rule = (
        "from this round on, a planted point is written one-clause-tight — "
        "one point is one fact of the code that a single evidence span can "
        "hit, and a consequence is its own point, never a trailing clause."
    )
    assert rule in rulings, "§106.1's own words"
    assert f"**{rule}**" in recall, "§107.3 registers the sentence in full"

    # Authoring-side, and held by no machinery.
    assert "**No lint rule holds it** this round" in recall
    assert "it is an authoring discipline" in recall
    assert "the spec review and the two-sided proofs" in recall
    assert "this registration adds no machinery for it and no code" in recall

    # Forward-only, with the permanent disclosure named.
    assert "it is **forward-only**" in recall
    assert (
        "round 10's and round 11's keys, proofs, records and labels **stand "
        "as written**"
    ) in recall
    assert (
        "**§104's addendum remains the permanent disclosure**"
    ) in recall
    assert "§76.2's owner-labels check rides this round's nine cells" in recall

    # And the older keys really are still on disk, unedited by this round:
    # the point-keyed set spans the two earlier actions the ruling reaches
    # back over — which "forward-only" leaves untouched — plus, since the
    # round's first task landed, this round's own category beside them.
    keyed = {
        task.category for task in tasks.values()
        if firstparty_v1.is_point_keyed(task)
    }
    assert keyed == {"investigation", _ANCHOR_CATEGORY, _CATEGORY}


def test_the_deliverable_is_one_answer_file_with_three_named_sections(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§107.4: `ANSWER.md`, three sections by name, and the key's 4-6 / 0-2
    shape.

    The path is not this round's invention and the register says so: it is the
    standing `answer_path` of every heap-3 task the corpus already holds, so
    the check is against the corpus's own keys rather than against the
    section's word for it. A prompt that named a different file would put the
    round's answers somewhere the collector does not look.

    The three section names are pinned individually and as an ordered list,
    because a deliverable "with three sections" and a deliverable with *these*
    three sections are different registrations, and the key is written against
    the second.
    """
    deliverable = item("4")

    keyed = [task for task in tasks.values() if firstparty_v1.is_point_keyed(task)]
    assert keyed, "the corpus holds heap-3 tasks to read the standing path off"
    assert {firstparty_v1.points_key(task).answer_path for task in keyed} == {
        _ANSWER_PATH
    }, "one standing answer path across heap 3"
    assert f"**`{_ANSWER_PATH}`**" in deliverable
    assert "names the answer file's path" in deliverable
    assert (
        "tasks/first-party-v1/granary-decide-how-to-answer-for-a-past-day/"
        "grading/points-key.json"
    ) in deliverable

    assert "requires the deliverable's parts **by name**, three of them" in deliverable
    for name in _SECTIONS:
        assert f"**{name}**" in deliverable, name
    # In order, and in the order §106.3 ruled them.
    positions = [deliverable.index(f"**{name}**") for name in _SECTIONS]
    assert positions == sorted(positions), "the three sections in §106.3's order"
    rulings = other_section(_RULINGS_HEADING)
    for name in _SECTIONS:
        assert f"**{name}**" in rulings, f"§106.3 named it first: {name}"

    # The key's shape, written under 107.3's discipline, and proved both ways.
    assert (
        "**one fact of the code a single evidence span can hit**"
    ) in deliverable
    assert (
        "with consequences planted as points of their own"
    ) in deliverable
    assert (
        "**the plausible misreading the code refutes**"
    ) in deliverable
    assert (
        "**the fluent explanation that reads well and misses the planted "
        "facts**"
    ) in deliverable
    assert "**4–6 planted points and 0–2 disqualifiers**" in deliverable
    assert "**proved both ways at authoring**" in deliverable

    # The repository is the evidence and stays unmodified: the write-up is all
    # of the deliverable.
    assert (
        "**The repository is the whole of the evidence and is left "
        "unmodified.**"
    ) in deliverable
    assert "**the write-up is the entire deliverable**" in deliverable
    assert "no edit to the repository is asked for, none is graded" in deliverable


def test_the_proofs_are_the_rounds_one_gate_stated_as_a_quantifier() -> None:
    """§107.5: the round's single hard gate, the bar it is read at, and the
    shape-aware form the category gets.

    §106.5 keeps §83.4's clause verbatim, and a proofs gate has one property no
    calibration bar ever had: it is a **universal quantifier**, so there is
    nothing in it to round and nothing in it to tune. Writing it as a
    percentage would give it both back, which is why no `%` belongs anywhere in
    this item's clause and this test says so mechanically.

    The check is not new code and this test proves it is not: the rule the
    section names is a live function registered in the lint's own proof
    registry, and the lint that calls it is offline by construction. What *is*
    new this round is the dispatch — the category carries locate-style tasks
    today and takes point-keyed ones next, so its existence proof is decided by
    the key on disk — and the registration has to name both halves before a
    task is authored, which is what is checked here.
    """
    gate = item("5")

    assert (
        "The round's single hard gate: the two-sided proofs, before the first "
        "sweep dollar.**"
    ) in gate
    assert "it is the only gate round 12 has" in gate
    assert "stated as a quantifier and never as a percentage" in gate
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
    # Named by symbol and never by a line number, which §83.4 set the precedent
    # for: a number in the note goes stale the next time the file is edited.
    assert not re.search(r"firstparty_v1\.py:\d+", gate)
    registered = [
        category for category, proof in firstparty_v1.EXISTENCE_PROOFS.items()
        if proof.check is firstparty_v1._the_reference_resolves_and_the_foil_fails
    ]
    assert registered, "the rule §107.5 names is registered in the lint's registry"
    assert hasattr(firstparty_v1, "prove_points"), (
        "and the writer the archived rulings come from"
    )
    # And the category already has an entry, which is the thing the round's
    # loader ticket makes shape-aware rather than adds.
    assert _CATEGORY in firstparty_v1.EXISTENCE_PROOFS

    # The shape-aware form, both halves named.
    assert "**dispatched by the key on disk**" in gate
    assert (
        "**every accepted location resolving in the starting repository**"
    ) in gate
    assert "**`investigation`'s registered two-sided form**" in gate
    assert f"`{_CATEGORY}` joins `_POINT_CATEGORIES`" in gate
    assert "**point-optional**" in gate
    assert (
        "refused as two ground truths for one deliverable"
    ) in gate

    # The kill discipline, in its one standing sentence, written for this
    # round's action.
    assert (
        "**The kill discipline, in its one standing sentence: a failed proof "
        f"stops the round with a record, explain-style `{_CATEGORY}` stays "
        "absent.**"
    ) in gate


def test_the_proofs_are_priced_over_counted_metered_calls_at_fetched_prices() -> None:
    """§107.6: 24-48 metered calls, priced from the fetched page, with both
    ends stated and §96's two amendments in force.

    The unit is the **call**, because the writer calls once per planted point
    *and* once per disqualifier against each of the two answers. The call range
    is re-derived here from the section's own registered assumption rather than
    read off its total, which is the point of restating the 0-2 disqualifier
    count in the register: a task that declares a third puts the round outside
    this registration instead of being absorbed by it.

    §96's amendments are what makes the count a count of the meter rather than
    of the archives: the writer has no resume, so every invocation carries
    `--task`, and a re-ask that rewrites an archive to the same bytes is still
    money. Round 11 then missed its own re-registered line on operational
    retries, so this round registers those as counted rather than as slack.

    The characters are re-derived from `point_grader.PROMPT` rather than
    carried from §95.5, because a price counted over a stale template is a
    price for a different instrument. §80.5's freezing rule applies to that
    read: when the instrument next moves, this figure freezes to a literal with
    a comment naming §107.

    A model's memory of a pricing page is not a source, so the URL and the date
    are asserted to be inside §107's own slice — and the date is asserted to be
    **this round's** fetch and not §95.5's, because the figures came back
    unchanged and a stale date is exactly what that would hide.
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
    assert (tasks_n, points_low, points_high) == (_CELLS, 4, 6)
    assert (disq_low, disq_high) == (0, 2)
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
    assert "counted over metered calls" in counted
    assert "**The assumed disqualifier count is 0–2 a task**" in counted
    assert "forces a re-registration rather than being absorbed by it" in counted

    # §96's two amendments, restated in the same paragraph as the count.
    priced = item("6")
    assert "The proofs writer **has no resume**" in priced
    assert (
        "**every invocation of this round's proofs carries `--task`**"
    ) in priced
    assert (
        "a count of **metered calls, not of archived rulings**"
    ) in priced
    assert (
        "**Operational retries are expected and are counted against this "
        "line**"
    ) in priced
    assert "the way §99 read round 11's overage" in priced

    # The fetch itself, pinned as the command that was run.
    assert block_holding(_PRICING_URL).strip() == f"curl -sL {_PRICING_URL}"
    assert f"`source_url`: `{_PRICING_URL}`" in priced
    assert f"`as_of`: **{_AS_OF}**" in priced
    assert f"Fetched on **{_AS_OF}**" in priced
    assert _PREVIOUS_AS_OF not in note_section(), (
        "the recorded as-of is this round's fetch, not §95.5's"
    )
    assert _PREVIOUS_AS_OF in other_section(_PREVIOUS_HEADING), (
        "and that date is round 11's, where it belongs"
    )
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
    assert (
        "**This round is registered at peak-hour list pricing, cache-miss "
        "throughout**"
    ) in counted
    assert "**no hit rate is claimed here**" in counted

    # The off-peak rule, recorded as read from this fetch.
    assert (
        '"Off-peak rates are half of the peak rates. Peak hours are 01:00 - '
        '04:00 and 06:00 - 10:00 UTC, Monday through Friday (all other hours '
        'are off-peak)."'
    ) in counted

    # The checkpoint, re-verified against this fetch rather than a memory of one.
    assert f"`MODEL VERSION` cell reads `{point_grader.GRADER_CHECKPOINT}`" in counted

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

    total_low = round(low_in * per_input + low_out * per_output, 4)
    total_high = round(high_in * per_input + high_out * per_output, 4)
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
    assert "the registered range is **$0.05–0.6**" in counted

    # Which half is an assumption, named — and the input half's reuse is now
    # measured against every proof answer the corpus holds.
    assert (
        "**Which half is an assumption, named — and the input half now has "
        "two rounds behind it.**"
    ) in counted
    assert "are **not written yet**" in counted
    assert f"at **{_PROOF_ANSWER_LOW:,} characters** at the low end" in counted
    assert f"and **{_PROOF_ANSWER_HIGH:,}** at the high" in counted
    assert "**The output half is the half with no anchor**" in counted
    assert "The high end is a bound and not an expectation" in counted
    assert "**never enter `unified.jsonl`**" in counted

    # The payment path, disclosed where the key is used.
    assert (
        "**The payment path, disclosed where it is used.**"
    ) in counted
    assert "**session memory**" in counted
    assert "the owner's ruling of **2026-08-23**" in counted
    assert "a disclosed exception to the stored-nowhere rule" in counted
    assert "**never printed**" in counted


def test_the_checked_in_proof_answers_are_what_the_input_half_is_measured_at(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§107.6's named assumption, re-derived from the answers on disk.

    The section reuses §83.5's 4,000/8,000 character assumption for a third
    round, and says what the reuse now rests on: twelve checked-in proof
    answers across six point-keyed tasks, none of them near the 8,000 ceiling.
    That is a claim about the corpus, so it is recomputed from the corpus
    rather than read off the prose — a figure that drifted as tasks were
    revised would otherwise sit in the register unchallenged.

    Recomputed over the answers the registration measured: the two earlier
    actions' twelve. The round's own proof answers land after this
    registration was written and are what the assumption is spent on, not
    part of what it rested on — so they are excluded here by category.
    """
    measured = [
        task for task in tasks.values()
        if firstparty_v1.is_point_keyed(task) and task.category != _CATEGORY
    ]
    lengths = sorted(
        len((task.proofs_dir / side.answer_file).read_text(encoding="utf-8"))
        for task in measured
        for side in firstparty_v1.PROOF_SIDES
    )
    references = sorted(
        len((task.proofs_dir / side.answer_file).read_text(encoding="utf-8"))
        for task in measured
        for side in firstparty_v1.PROOF_SIDES if side.resolves
    )
    assert (len(lengths), len(references)) == (12, 6)

    counted = prose()
    assert (
        "the corpus now holds **twelve** checked-in proof answers across six "
        "point-keyed tasks"
    ) in counted
    assert f"between **{min(lengths):,}** and **{max(lengths):,}**" in counted
    assert f"between {min(references):,} and {max(references):,}" in counted
    assert max(lengths) < _PROOF_ANSWER_HIGH, (
        "the 8,000 ceiling has never been approached, which is what the "
        "section says it rests on"
    )


def test_the_sweep_range_is_derived_from_the_checked_in_round_11_rows(
    runs: list[firstparty_v1.Run],
) -> None:
    """§107.7's arithmetic, recomputed from the rows it claims to read.

    Round 11 swept nine cells of heap 3's second action, so the anchor is one
    round back — the same three combinations over the same nine-cell shape,
    graded under the same point gate — selected by **sweep id** over every log
    in the directory and never by a log filename. Every figure the section
    quotes is re-derived here rather than lifted from §99, which is the whole
    point of re-deriving it there too: a registration that copied a record
    would inherit that record's arithmetic without ever checking that the
    anchor rows still say it.

    Both ends of the bound are recomputed too. Round 12 sweeps three cells on
    the Codex column and round 11 swept three, so the projection is that
    round's own token totals rather than a rate scaled up, and the caching
    split is the only thing that moves between the two ends. The ceiling's
    multiple is re-derived as well, because §107.7 justifies its width by
    §59.4's shape rather than by precedent, and a justification that is
    arithmetic can be checked as arithmetic.
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
        ("claude-code", "claude-haiku-4-5"): 0.2385,
        ("claude-code", "claude-sonnet-5"): 0.8253,
        ("codex", "gpt-5.6-terra"): 0.2568,
    }
    per_cell = {
        combination: round(sum(run.cost_usd for run in found) / len(found), 4)
        for combination, found in anchor.items()
    }
    assert per_cell == {
        ("claude-code", "claude-haiku-4-5"): 0.0795,
        ("claude-code", "claude-sonnet-5"): 0.2751,
        ("codex", "gpt-5.6-terra"): 0.0856,
    }
    per_task = round(sum(per_cell.values()), 4)
    assert per_task == 0.4402
    flat = round(per_task * _CELLS, 4)
    assert flat == 1.3206
    landed = round(sum(sum(run.cost_usd for run in found)
                       for found in anchor.values()), 4)
    assert landed == flat, (
        "this round's rounded per-cell figures reproduce the landed total "
        "exactly, unlike §95.6's pair"
    )

    # The figures §106.5 named, reproduced rather than adopted: the derivation
    # above is what the section registers, and it agrees with the ruling.
    rulings = other_section(_RULINGS_HEADING)
    assert f"${landed:.4f} landed" in rulings

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
    assert columns == totals, "the rounded columns are the rows' own totals"
    assert round(sum(columns.values()), 4) == flat
    assert f"total        ${flat:.4f}" in summed

    # The caching-aware envelope, at the checked-in price table.
    codex = anchor[("codex", "gpt-5.6-terra")]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == (312819, 7547)

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    prices = table.models["gpt-5.6-terra"]
    logged = sum(run.cost_usd for run in codex)
    effective = (logged - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1e6, 4) == 0.5314

    output_cost = tokens_out * prices.output_per_token
    uncached = tokens_in * prices.input_uncached_per_token
    cached = tokens_in * prices.input_cached_per_token
    assert round(output_cost, 4) == 0.0906
    assert round(uncached, 4) == 0.6256
    assert round(cached, 4) == 0.0626
    assert (round(cached + output_cost, 2), round(uncached + output_cost, 2)) == (
        0.15, 0.72
    )
    assert round(tokens_in * effective + output_cost, 2) == 0.26

    claude = round(sum(columns[combination] for combination in _COMBINATIONS[:2]), 4)
    assert claude == 1.0638
    low = round(claude + cached + output_cost, 2)
    high = round(claude + uncached + output_cost, 2)
    assert (low, high) == (1.22, 1.78)

    # The registered band, re-derived: the floor is the flat extrapolation
    # rounded down to a round number, and the ceiling keeps §59.4's shape — the
    # all-uncached end inside the band and below its middle.
    floor, ceiling = 1.3, 2.5
    assert floor == round(flat - flat % 0.1, 1), "the floor is the anchor, rounded down"
    assert floor <= high <= ceiling, (
        "the all-uncached bound must sit inside the registered range rather "
        "than at its ceiling — pricing the round at its upper bound is round "
        "6's error"
    )
    assert high < (floor + ceiling) / 2, "and below its middle, which is §59.4's shape"
    # And unlike round 11, §83.6's standing 1.8× multiple would itself have
    # kept that shape this round, which is the section's stated reason for a
    # narrower headroom than §95.6's.
    narrow = round(flat * 1.8, 2)
    assert (floor + narrow) / 2 > high, "1.8× this anchor keeps its middle above the bound"
    assert ceiling >= narrow, "the ceiling is the first round number at or above it"

    counted = prose()
    assert "The sweep's price: $1.3–2.5" in counted
    assert "re-anchored on round 11's own nine cells" in counted
    assert (
        "**Round 11 is the nearest anchor this corpus has and it is one round "
        "back**"
    ) in counted
    assert f"selected by sweep id `{_ANCHOR_ROUND}`" in counted
    assert "**never by a log's filename**" in counted
    assert "**$0.2385** on `claude-haiku-4-5`" in counted
    assert "**$0.8253** on `claude-sonnet-5`" in counted
    assert "**$0.2568** on `codex` × `gpt-5.6-terra`" in counted
    assert "**$0.0795**, **$0.2751** and **$0.0856** a cell" in counted
    assert "**$0.4402 a task across the three combinations**" in counted
    assert f"three tasks come to **${flat:.4f}**" in counted
    assert f"round 11's own **${landed:.4f}**" in counted
    assert "with no disagreement to flag" in counted
    assert "**312,819** input tokens and wrote **7,547**" in counted
    assert "**$0.15 all-cached to $0.72 all-uncached**" in counted
    assert "**$0.5314/M**" in counted
    assert "expected figure near **$0.26**" in counted
    assert "**$1.0638** together" in counted
    assert "**$1.22 all-cached to $1.78 all-uncached**" in counted

    # The headroom's width, justified by §59.4's shape rather than by precedent.
    assert f"§83.6's **1.8×** multiple is ${narrow:.2f}" in counted
    assert f"the middle of $1.3–{narrow:.2f} is **$1.84**" in counted
    assert f"The ceiling is set at **${ceiling:.1f}**" in counted

    # Both miss directions, pre-read before the sweep.
    assert "The **low** miss is again the likelier" in counted
    assert "The range's floor *is* the flat extrapolation" in counted
    assert "a finding about the action and not an accounting surprise" in counted
    assert "**$0.08 under the floor**" in counted
    assert (
        "an explanation that re-reads the repository for every edge it names"
    ) in counted
    assert "**$2.5 is where the record is to stop and say so**" in counted

    # The stance itself, unchanged: a ChatGPT-login account is not metered, so
    # the Codex figure is an equivalent and never an invoice.
    assert "authenticated by **ChatGPT login**, not by an API key" in counted
    assert "**not billed per token**" in counted
    assert "**list-price equivalent**" in counted
    assert "`cost_source: table-derived`" in counted
    assert "`cost_source: vendor-reported`" in counted
    assert "sweep protocol's own item 2 (`docs/agents/sweep-protocol.md`)" in counted


def test_the_nine_cells_and_the_invocation_are_registered() -> None:
    """§107.8: three tasks × three columns, the three kinds of question, the
    sweep id, the dry cell, and the id register left explicitly to be filled in
    before the sweep — and now filled exactly where the section left it.

    What this checks is the registration's shape: the columns, the count, the
    three kinds of question §106.4 fixes, the language, the control
    declaration, the sweep's invocation, and the id register — registered *as
    empty*, said to be left for the authoring tickets, with round 7's prefix
    pin named as the check the authoring runs first, and filled by the
    round's second task-authoring ticket, dated and attributed rather than
    blended into the registration-time prose. What the filled ids claim about
    the corpus is the forward-reading test's at the end of this file; the pin
    here is that exactly one id-shaped block stands in the section and each
    of its lines carries a gloss naming the kind of question its task asks.
    """
    counted = prose()

    assert agents.CODEX_REASONING_LEVELS["gpt-5.6-terra"] == "medium"
    assert (
        "`claude-code` × `claude-haiku-4-5`, `claude-code` × "
        "`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`"
    ) in counted
    assert (
        "**the three standing columns, unchanged from rounds 7, 8, 10 and 11**"
    ) in counted
    assert "three tasks × three combinations = **nine cells**" in counted
    assert f"three explain-style `{_CATEGORY}` tasks × the three standing columns" in counted

    # The two Claude columns are the ladder the reader already has; the Codex
    # one is the second harness and is deliberately not in it.
    assert reconcile_v1.LADDER_MODELS == ("claude-haiku-4-5", "claude-sonnet-5")

    assert "Each of the three is **Python**" in counted
    assert "**one closed-world question to explain**" in counted
    assert "**three different kinds of question**" in counted
    # §106.4's three kinds, each named and each checked against the ruling.
    rulings = other_section(_RULINGS_HEADING)
    for kind in (
        "one end-to-end mechanism",
        "one surprising behaviour",
        "one divergence",
    ):
        assert f"**{kind}**" in counted, kind
        assert kind in rulings, f"§106.4 named it first: {kind}"

    assert "Each is a **declared control**" in counted
    assert (
        "`control: true`, no construction block, no knob activation, no "
        "prediction"
    ) in counted
    assert (
        "**round 12 moves no knob's counter and the kill discipline does not "
        "count it**"
    ) in counted
    assert "`calibrate-v1` gains no explain-style multiplier row" in counted

    # The register: left for the authoring tickets, said to be left, and now
    # filled where the section said it would be. The registration-time prose
    # stays as the record it is — it was true as written — and the fill is
    # dated and attributed rather than blended into it.
    assert "**The three task ids do not exist yet.**" in counted
    assert (
        f"**The id register for round 12 is left explicitly to be filled in, "
        f"in this section, before the sweep, by the round's task-authoring "
        f"tickets**"
    ) in counted
    assert (
        f"holds **four locate-style `{_CATEGORY}` tasks and no point-keyed "
        "one**"
    ) in counted
    assert "**Round 7's pin is the check the authoring runs first**" in counted
    assert "no task id may share a repo prefix with an existing task" in counted
    assert (
        "**Filled in 2026-08-28, by the round's second task-authoring ticket, "
        "exactly where this section left it.**"
    ) in counted
    assert "**This list is the register.**" in counted
    assert (
        f"**every point-keyed `{_CATEGORY}` task the corpus holds**"
    ) in counted
    assert (
        "the round sweeps the action entire and re-runs nothing any "
        "combination has already answered"
    ) in counted

    # Exactly one fenced block of the section is a register of task ids — the
    # one the fill wrote, in §68.1's form: an id a line, each with a one-line
    # gloss naming the kind of question its task asks. Before the fill this
    # asserted no such block existed; what the ids claim about the corpus is
    # the forward-reading test's below.
    [register] = register_blocks()
    assert len(register) == _CELLS
    for task_id, gloss in register.items():
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


def test_every_cell_runs_at_the_registered_limit_and_no_entry_moves() -> None:
    """§107.9: one ceiling over the round, reached by the category's own row.

    Unlike round 11's action, this one is already in `LIVE_RUN_LIMITS_S` and
    has been since round 5, so the registration's whole content is that
    **nothing moves**: no row is added, no number is changed, and no code is
    touched. The nine cells therefore run at 600 seconds *under the
    registration the category already carries* — a description only a
    registered category's cell can be given — while 600 is also the flat
    default's own value, which is why no cross-round caveat arises.

    So this is a test that an entry was *not* moved, and that the number the
    section quotes for the fallback is still the number the runner holds.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) - _LATER_LIMITS == _REGISTERED_LIMITS, (
        "this registration adds nothing new"
    )
    assert firstparty_v1.LIVE_RUN_LIMITS_S[_CATEGORY] == _LIMIT_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S, "the flat default is the same number"

    counted = prose()
    assert (
        f"**`{_CATEGORY}` is already one of them, at {_LIMIT_S}, and has been "
        "since round 5**"
    ) in counted
    assert "**No entry moves**" in counted
    assert "**changes no code**" in counted
    assert (
        f"all nine cells run at **{_LIMIT_S} seconds under the registration "
        "the category already carries**"
    ) in counted
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
    """§107.10: the anchor the sweep's band is derived over, held still.

    Landed form: the round's own sweep (2026-08-28-r12-a..d) is the one
    arrival the registered sentence allowed, and nothing else landed.

    §80.4's guardrail carried forward, for this round's own reason: §107.7's
    band is derived over the nine `round-11` rows as they stand, so a sweep row
    landing between this registration and the round's own sweep would move the
    anchor out from under a range already registered against it.

    The split is re-derived here from the logs themselves — wholesale, keyed on
    what the rows carry and never on a filename — rather than taken from the
    section's prose, which is what makes the registered sentence a claim about
    the corpus and not about itself.
    """
    # Landed form: the archive grew by exactly the round's own sweep and by
    # nothing else — 45 logs and 324 rows at registration, plus the sweep's
    # four logs and nine `round-12` rows, keyed on what the rows carry.
    assert len(logs) == 49
    assert len(runs) == 333
    late = [run for run in runs if run.sweep == _SWEEP]
    assert len(late) == _CELLS * 3
    assert len(runs) - len(late) == 324, "nothing else landed in between"
    assert len([run for run in runs if run.sweep == _ANCHOR_ROUND]) == _CELLS * 3

    counted = prose()
    assert (
        "No new sweep row lands between this registration and the round's "
        "own sweep.**"
    ) in counted
    assert (
        f"derived over the **nine `{_ANCHOR_ROUND}` rows as they stand**"
    ) in counted
    assert "**the rows this section registers**" in counted
    assert "Run before the round's own sweep it must print nothing" in counted

    check = block_holding("-newermt").strip()
    assert check == f"find data/first-party-v1-runs -type f -newermt {_AS_OF}"


def test_the_round_12_cells_are_the_nine_registered(
    runs: list[firstparty_v1.Run],
) -> None:
    """The first forward-reading test, in its landed form.

    Its first form said no `round-12` row existed yet — a registration, not a
    record — and was retired by the sweep it foresaw (2026-08-28-r12-a..d,
    dry cell first). What it holds the round to now is the landed version of
    the same claim: the cells carrying sweep id `round-12` are exactly the
    nine §107.8 registered — the register's three tasks under the three
    standing combinations — none repeated, and every one has archived
    per-run rulings, so its verdict is a pure function of what is checked in.

    Selected by **sweep id** over every log in the directory and never by a log
    filename, which is the discipline the whole round is run under.
    """
    swept = [run for run in runs if run.sweep == _SWEEP]
    cells = {(run.task_id, run.agent, run.model) for run in swept}
    assert len(swept) == len(cells) == _CELLS * 3, "nine cells, none repeated"
    [register] = register_blocks()
    assert cells == {
        (task_id, agent, model)
        for task_id in register
        for agent, model in _COMBINATIONS
    }
    for task_id, agent, model in sorted(cells):
        assert firstparty_v1.rulings_file(
            _RULINGS, task_id, agent, model
        ).is_file(), f"{task_id} x {agent} x {model}: archived rulings"

    assert {run.sweep for run in runs} == {
        None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
        "round-8", "round-10", _ANCHOR_ROUND, _SWEEP,
    }, "`None` is round 1, which predates `--sweep` and is keyed on `as_of`"


def test_the_register_names_every_point_keyed_comprehension_task_and_each_is_proved(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """The second forward-reading test, in its final form: the register check.

    Its first form said no `codebase-comprehension` task was point-keyed yet;
    the round's first authoring ticket caught it up to "task 1 and no second
    or third yet"; the second authoring ticket landed the other two and filled
    §107.8's register, which is the form this test now holds the round to. The
    register is read against the corpus rather than restated: the three ids
    exist, they are exactly the point-keyed `codebase-comprehension` tasks the
    corpus holds — no fourth anywhere — every one is the Python
    application-surface declared control §107.8 registered, each carries its
    kind of question in its register gloss, §106.4's three kinds each carried
    exactly once, and each ships a points key and a two-sided proof that is
    green under the pinned instrument, the verdicts recomputed through
    `_point_verdict` rather than taken on the archives' word.

    Still selected **by key shape and never as a task count of the
    category**. The category's four locate-style tasks on an accepted-answer
    key are staying, so a count would go red on their account rather than on
    the thing this test watches — the explain shape the register names.
    """
    comprehension = [
        task for task in tasks.values() if task.category == _CATEGORY
    ]
    assert len(comprehension) > len(
        [task for task in comprehension if firstparty_v1.is_point_keyed(task)]
    ), (
        "the corpus carries the category's locate-style tasks beside the "
        "explain shape"
    )

    [register] = register_blocks()
    authored = sorted(
        task.id for task in comprehension if firstparty_v1.is_point_keyed(task)
    )
    assert sorted(register) == authored, (
        "the register is the corpus's point-keyed comprehension set, whole"
    )
    assert len(register) == _CELLS, "and the corpus holds no fourth"

    # Each register line's gloss names its task's kind of question, §106.4's
    # three kinds, each carried exactly once across the three lines.
    kinds = ("end-to-end mechanism", "surprising behaviour", "divergence")
    for kind in kinds:
        assert [
            task_id for task_id, gloss in register.items() if kind in gloss
        ], f"one register gloss names {kind!r}"
    for task_id, gloss in register.items():
        assert [kind for kind in kinds if kind in gloss], (
            f"{task_id}: its gloss names its kind of question"
        )

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
            assert (
                firstparty_v1._point_verdict(questions, archive, answer)
                is side.resolves
            ), f"{task_id}: {side.name}"

    # The loader has been taught the shape — §106.5's move, landed by the
    # round's loader ticket ahead of any task, and §107.5 registers it as the
    # form the gate will take. What it taught the loader is *point-optional*
    # membership and nothing more: the category may ship a points key — task 1
    # asserted just now is the first that does — and the two actions above it
    # must.
    assert _CATEGORY in firstparty_v1._POINT_CATEGORIES
    assert _CATEGORY == firstparty_v1._POINT_OPTIONAL_CATEGORY
    assert _CATEGORY not in firstparty_v1._POINT_REQUIRED_CATEGORIES
    assert _ANCHOR_CATEGORY in firstparty_v1._POINT_CATEGORIES
    assert _ANCHOR_CATEGORY in firstparty_v1._POINT_REQUIRED_CATEGORIES
