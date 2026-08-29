"""Round 13's pre-registration, pinned: what section 118 of the design note
commits to before the round's first paid call.

Round 13 is the first round since round 9 whose verdict path spends **no
grader dollar**. There is no calibration experiment and there is no instrument:
§117.1 ruled the truth of an optimisation to be asserted growth behaviour, so
every verdict this round produces is two held-out suites run against a
collected diff — offline, replayable and free. What §118 registers is
therefore the authoring-and-sweep half alone, plus the verdict shape it is
built on: the round's one hard gate (the task-set lint's two pristine
invariants), three authoring disciplines, the single loader move, the run-time
limit, the nine cells and one price range. §46 did the one-half job for round
5, §52 for round 6, §59 for round 7, §68 for round 8, §83 for round 10, §95 for
round 11 and §107 for round 12; §77 did the two-half job for round 9, and the
shape here is §107's a round on.

Three disciplines are inherited from `test_firstparty_v1_round12_cells.py`
rather than re-argued.

**The register is the design note**, not a constant in code — the note is what
a reader of the round consults and what a reviewer holds the round to — so
every test below parses section 118's own fenced blocks and its own prose and
then re-derives each claim from the corpus: from the task set, from the price
table, from the live loader registries and from the checked-in run logs. A
registration whose arithmetic cannot be reproduced is a number somebody wrote
down, and a register that drifts from the corpus it registers is the exact
defect this file exists to catch.

**No test here selects a run log by filename.** Logs are collected wholesale
and rows are keyed on what they carry — a task, an agent, a model, a sweep
id — which is the sweep protocol's rule after the first pass of the round-1
analysis silently dropped two paid cells by filtering on a name.

**The section is sliced deliberately**, from §118's own top-level heading to
the next top-level heading, and never to `## Open questions`
(`docs/agents/runbook-grader-v2-gate.md:153`): a slice that runs to the note's
trailing headings swallows whole sections silently, and every pin in this file
would then read as met on text §118 never wrote.

**This suite carries no §80.5 freezing line, and the omission is deliberate
rather than forgotten.** §80.5's rule freezes a pin suite's reach into the live
`point_grader` module — the version tuple, the prompt template — to whatever
the instrument stood at when the record was computed, the next time the
instrument moves. This suite reaches none of it: it does not import
`point_grader`, it asserts nothing about a grader version or a prompt, and
§118's own slice quotes neither. There is nothing here for a moved checkpoint
to invalidate, which is 118.1's claim about the round said again about the
suite that pins it.

Nothing here calls the grader, runs a live cell or spends a dollar. Three tests
read the round forwards, and they were three rather than one because they die
at different tickets — two are now retired to their landed forms:

- **the corpus** — retired: ticket 04 landed the first
  `performance-optimisation` task and ticket 05 the second and third, so the
  test now reads all three present with no fourth, and the table's `- - 0`
  rows down to `unclassified`'s structural one alone;
- **the rows** — retired: the sweep landed (2026-08-29-r13-a..d, dry cell
  first), so the test now holds the cells carrying sweep id `round-13` to be
  exactly the nine §118.10 registered, each with a verdict computed from
  execution and no rulings archive anywhere;
- **the register** — retired: §118 left the three ids explicitly to be filled
  in, ticket 05 filled it, and the test now holds the register to the corpus
  with the ids-match-the-corpus check §107.8's suite carries today.

Two more read the round forwards and no longer do, both retired by the round's
machinery ticket and both now asserted in their landed form rather than
dropped:

- **the limit** — §118 registers `performance-optimisation: 600`, which is a
  claim about the section's text and is permanent; the live
  `LIVE_RUN_LIMITS_S` now carries the entry, and the test below reads the
  category present, at 600, and the registered set grown by exactly one;
- **the ADR** — §118's verdict-shape pin held that ADR-0006 was owed and not
  yet written; it is written, so the pin now asserts it present beside
  ADR-0004 and ADR-0005.
"""

import re
from pathlib import Path
from typing import get_args

import pytest

from ai_benchmark import (
    agents,
    firstparty,
    firstparty_v1,
    pricing,
    reconcile_v1,
)
from ai_benchmark.schema import TaskCategory

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_RULINGS = _REPO / "data" / "first-party-v1-rulings"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

_HEADING = "## Round 13 cells and cost — registered 2026-08-29"

# The rulings §118 registers, sliced the same deliberate way so that anything
# §118 claims §117 ruled is checked against §117's own words.
_RULINGS_HEADING = "## Round 13 rulings — 2026-08-29"

# Round 12's own pre-registration, which this section is a round on, and the
# record the sweep band's anchor rows were read in: sliced only to keep them
# apart from this round's text, never read as if they were it.
_PREVIOUS_HEADING = "## Round 12 cells and cost — registered 2026-08-28"

_SWEEP = "round-13"

# The three standing columns, unchanged from rounds 7, 8, 10, 11 and 12 and
# written agent-first because that is what a combination is.
_COMBINATIONS = (
    ("claude-code", "claude-haiku-4-5"),
    ("claude-code", "claude-sonnet-5"),
    ("codex", "gpt-5.6-terra"),
)

# The round the sweep's per-cell anchor comes from, named by its sweep id
# because that is what identifies a round. Round 12 swept nine cells of heap
# 3's last action, so it is the nearest anchor and it is one round back.
_ANCHOR_ROUND = "round-12"

# The action the round sweeps, and how many tasks of it it authors. Typed as
# the corpus's own category literal, because it indexes registries keyed on it.
# It is the corpus's last unfilled action and heap 4's only one.
_CATEGORY: TaskCategory = "performance-optimisation"

# The category whose behaviour/structural split the loader move of 118.8
# extends, and the one category the loader refuses outright — whose `- - 0`
# row therefore survives every round.
_SPLIT_CATEGORY: TaskCategory = "refactor"
_STRUCTURAL_ZERO: TaskCategory = "unclassified"

_CELLS = 3

# The number 118.9 registers for the action, which is also the flat default's
# own value — so the entry buys no seconds and takes none away.
_LIMIT_S = 600

# The four categories `LIVE_RUN_LIMITS_S` carried before this round: round 4's
# two by §37 and round 5's two by §46. §118.9's entry is the fifth, landed by
# the round's machinery ticket, and the limit test below holds the grown set
# exactly — four inherited plus this action and nothing else.
_INHERITED_LIMITS = {"bug-fix", "fault-location", "code-review",
                     "codebase-comprehension"}

# §118.11's band. The floor is the flat extrapolation off round 12's rows
# rounded down; the ceiling is the first round number at or above the corpus's
# own upper comparator for three tasks of a write-code-and-run-tests action.
# Both are re-derived in the sweep-band test rather than trusted here.
_FLOOR = 0.9
_CEILING = 2.8


def note_section() -> str:
    """Section 118, from its own heading to the next top-level one.

    Deliberately sliced: a slice that ran to `## Open questions` would swallow
    every section written after this one, and each pin below would then pass on
    text §118 never wrote. `docs/agents/runbook-grader-v2-gate.md:153` is where
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
    """Every fenced block of §118 whose every line is an id line — §83.7's
    register form, looked for by shape rather than by position or by a quoted
    id.

    §118.10 left the register explicitly to be filled in before the sweep, so
    this found none until the round's second authoring ticket filled it; the
    same shape check now finds exactly one, and a second id-shaped block
    appearing anywhere in the section is caught as the ambiguity it would be.
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


_ITEM = re.compile(r"^\*\*118\.(\d*) ", re.MULTILINE)


def item(number: str) -> str:
    """One numbered item of §118, collapsed, from its own bold number to the
    next one — so that a claim registered about the gate can be checked
    *inside the gate's clause* rather than anywhere in the section."""
    section = note_section()
    found = list(_ITEM.finditer(section))
    assert found, "§118 numbers its items"
    for index, match in enumerate(found):
        if (match.group(1) or "0") != number:
            continue
        end = found[index + 1].start() if index + 1 < len(found) else len(section)
        return " ".join(section[match.start():end].split())
    raise AssertionError(f"§118 carries no item {number!r}")


def other_section(heading: str) -> str:
    """Another top-level section of the note, sliced the same deliberate way
    and collapsed — so a sentence §118 says it quotes is checked against the
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
    """§118 is the next free number, it is a pre-registration, and it sits
    where a section of the note goes.

    The note numbers its sections once and never renumbers them, so a section
    taking a number already spent is a citation collision every later record
    inherits. §117 (round 13's rulings) is what this follows, and the round's
    record takes what is free after it — which the section says in a line, so
    that whoever writes it does not have to re-derive the frontier. The live
    frontier itself is the round-9 suite's one moved assertion and is
    deliberately not copied here; this suite carries the contiguity claim
    instead, extended over §118, which is the round-12 cells suite's own
    pattern.
    """
    text = _NOTE.read_text(encoding="utf-8")
    numbered = sorted(
        {int(match) for match in re.findall(r"^### (\d+)\.", text, re.MULTILINE)}
        | {int(match) for match in re.findall(r"^\*\*(\d+)\. ", text, re.MULTILINE)}
    )
    assert numbered.count(117) == 1, "the round-13 rulings, spent once"
    assert numbered.count(118) == 1, "this pre-registration, spent once"
    assert all(numbered.count(number) == 1 for number in range(108, 117)), (
        "round 12's record, §108-§116, each spent once and not renumbered"
    )
    # §119-§127 (round 13's record, 2026-08-29) have since landed after this
    # pre-registration: the contiguity claim extends over them, and the live
    # frontier stays the round-9 suite's one moved assertion.
    assert [number for number in numbered if number > 68] == list(range(69, 128)), (
        "the rounds since 68 are contiguous and nothing was renumbered"
    )

    # And it lands after §117's own heading and before the note's trailing
    # headings rather than after them.
    headings = re.findall(r"^## .+$", text, re.MULTILINE)
    assert headings.index(_HEADING) == headings.index(_RULINGS_HEADING) + 1, (
        "§118 follows §117's own heading"
    )
    # The heading after this section was `## Open questions` until the
    # round's record landed there (§119-§127, 2026-08-29); the claim that
    # survives is that §118 sits inside the note's numbered run, before the
    # trailing headings — this adjacency pin moved in the commit that landed
    # the record, exactly as the round-12 cells suite's did when §108-§116
    # landed.
    assert headings[headings.index(_HEADING) + 1].startswith("## Round 13 record"), (
        "round 13's record is what landed after it"
    )

    counted = prose()
    assert "This is round 13's pre-registration and nothing else" in counted
    assert "written down before the first paid call" in counted
    assert "**no paid experiment at all**" in counted
    assert "**no paid instrument either**" in counted
    assert "**No argument is reopened here.**" in counted
    assert "**the next free section numbers**, §119 onward" in counted
    assert "nothing below is a result, and nothing above is renumbered" in counted


def test_the_round_registers_no_instrument_and_prices_no_grader_dollar() -> None:
    """§118.1 and §118.13: the round with nothing in the instrument's ledger.

    This is the one structural difference between §118 and every
    pre-registration since §77, and it is checked twice over. First
    negatively: the section's own slice makes **no claim about a pinned grader
    version at all** — a registration that quoted one would be registering an
    instrument it does not run, and the next reader would go looking for the
    round's grader spend. Then positively: the round says in as many words
    that its verdict path is execution-only, that the standing
    checkpoint-movement stop cannot stop it because no ruling of it depends on
    the instrument, and that no key is needed by any column.

    The suite that pins all this reaches no grader either — it imports no
    `point_grader` — which is why it carries no §80.5 freezing line, as its
    own docstring says.
    """
    section = note_section()
    assert "GRADER_VERSION" not in section, (
        "a round with no instrument registers no version string"
    )
    assert "GRADER_MODEL" not in section
    assert "api-docs.deepseek.com" not in section, (
        "and fetches no price for a call it does not make"
    )
    # The two marks a registered grader price leaves — the vendor's model
    # column and its per-million unit — are absent, and the only mention
    # §118 makes of a pricing block is 118.11's sentence saying it carries
    # none.
    assert "deepseek-v4-pro" not in section
    assert "MTok" not in section
    assert section.count("`source_url`/`as_of`") == 1
    assert "no `source_url`/`as_of` pricing block" in prose()

    instrument = item("1")
    assert (
        "**118.1 The instrument, which this round does not have.**"
    ) in instrument
    assert "verdict path is **execution-only**" in instrument
    assert "**no cell is point-graded**" in instrument
    assert (
        "**round 13 is the first round since round 9 whose verdict path "
        "spends no grader dollar**"
    ) in instrument

    # The claim is §117's own opening sentence, held against §117's own words.
    rulings = other_section(_RULINGS_HEADING)
    assert (
        "round 13 is the first round since round 9 whose verdict path spends "
        "no grader dollar"
    ) in rulings

    # The standing checkpoint-movement stop, registered as inapplicable rather
    # than left unmentioned — and registered as inapplicable to *this* round.
    assert "**cannot stop this round**" in instrument
    assert "because no ruling of it depends on the instrument" in instrument
    assert "**this round has nothing in that ledger**" in instrument
    assert (
        "the stop stands unmoved for the next round that runs the gate"
    ) in instrument

    # And the payment path, stated by its absence rather than by silence.
    payment = item("13")
    assert (
        "**No `DEEPSEEK_API_KEY` is needed by any column and no cell is "
        "point-graded**"
    ) in payment
    assert "**not owed by this round**" in payment
    assert "the owner's ruling of **2026-08-23**" in payment
    assert (
        "stays where it was used, in the round-10, round-11 and round-12 "
        "runbooks and records"
    ) in payment


def test_the_action_is_registered_with_the_last_authorable_zero_row(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """§118.2: heap 4's one action, and the zero row that is not the last one.

    The correction of 2026-08-29 is the load-bearing part and is checked
    against the live table rather than against the note's own account of it:
    the coverage table prints **two** `- - 0` rows today, and only one of them
    is a round's to close. `unclassified`'s row is structural — the loader
    refuses the category outright — so the honest claim is that this round
    closes the last *authorable* zero row, and a section claiming the table
    goes zero-row-free would be claiming something the loader makes
    impossible.
    """
    what = item("2")
    assert "heap 4's one action" in what
    assert f"`{_CATEGORY}` on **Python**" in what
    assert "**Three fresh tasks**" in what
    assert (
        "**Heap 4 closes with this round if the machinery proves out**"
    ) in what
    assert "the coverage table's last **authorable** `- - 0` row" in what
    assert (
        f"the only `- - 0` row the table prints is **`{_STRUCTURAL_ZERO}`'s**"
    ) in what
    assert "**permanent and structural**" in what
    assert "(`classified_and_split_by_category`)" in what
    assert "no task may ever fill it and no round may ever close it" in what
    assert "does **not** claim the table goes zero-row-free" in what
    assert "the plan review's correction of 2026-08-29" in what

    # The non-Python scope, disclosed the standing way: by the absence of a row.
    assert "**any non-Python language stays out of scope**" in what
    assert "disclosed as a zero **by the absence of its row**" in what

    # The live loader is what makes the structural row structural: the
    # category is a `TaskCategory` the coverage table therefore always prints
    # a row for, and a task declaring it is refused outright. Checked by
    # taking a task the corpus actually holds and moving only its category,
    # so the refusal is the category's and not some other field's.
    assert _STRUCTURAL_ZERO in get_args(TaskCategory)
    declared = dict(next(iter(tasks.values())).model_dump())
    declared["category"] = _STRUCTURAL_ZERO
    with pytest.raises(ValueError, match="classified up front"):
        firstparty_v1.Task.model_validate(declared)


def test_the_verdict_is_two_suites_and_wall_clock_is_prohibited() -> None:
    """§118.3: the shape §117.1 ruled, registered and not re-argued.

    Two held-out suites, `resolved` computed as both passing, and — the claim
    this test exists for — **wall-clock nowhere in the verdict path**, stated
    as a prohibition rather than as a preference. That is checked both ways:
    the prohibition sentence has to be present, and the verdict clause has to
    carry **no timing figure at all**, because a registered threshold is
    exactly what a later round would read as licence to time something. The
    round's one number-with-a-unit lives in 118.9, where it bounds the agent's
    run and not the verdict.

    The two declined alternatives and the deferred hybrid are registered too:
    a shape declined without its price recorded is a shape the next round
    re-argues from scratch.
    """
    verdict = item("3")

    assert "a **behaviour suite** — correctness unchanged —" in verdict
    assert (
        "**must pass on the pristine repository and on the reference "
        "solution**"
    ) in verdict
    assert "a **complexity suite** — operation counts across held-out input" in verdict
    assert "ratio-bounded or ceiling-bounded" in verdict
    assert "**seams the task repository already owns**" in verdict
    assert (
        "**must fail on the pristine repository and pass on the reference "
        "solution**"
    ) in verdict
    assert "`resolved` is **both suites passing**" in verdict
    assert (
        "binary, execution-verified, computed rather than spoken, and "
        "replayable offline"
    ) in verdict

    # The prohibition, in as many words, and then mechanically.
    assert (
        "**Wall-clock never enters the verdict path, and that is registered "
        "as a prohibition rather than as a preference.**"
    ) in verdict
    assert "**No wall-clock reading is taken anywhere this round**" in verdict
    assert (
        "**not even as a disclosed non-gating reading beside the verdict**"
    ) in verdict
    assert not re.search(
        r"\d+(?:\.\d+)?\s*(?:ms|s|secs?|seconds?|minutes?|hours?)\b", verdict
    ), "no timing figure is registered in the verdict clause"
    assert "wall-clock threshold" not in verdict.lower().replace(
        "thresholds over elapsed time", ""
    )

    # The three shapes put, the two declined at their price, the hybrid queued.
    assert "**Measured speedup**" in verdict
    assert "measurement noise on shared hardware" in verdict
    assert "a threshold is a tuning knob" in verdict
    assert "a verdict that re-times on replay can flip" in verdict
    assert "**Point-keyed explain-the-optimisation**" in verdict
    assert "it grades the explanation and not the optimisation" in verdict
    assert "a fake optimisation with a good essay resolves" in verdict
    assert "§115's addendum has opened a live false-red mechanism" in verdict
    assert "**hybrid**" in verdict
    assert "**one-new-instrument-per-round discipline**" in verdict
    assert "**free to queue for a later round**" in verdict

    # And the ADR the shape owes, which landed with the machinery ticket —
    # asserted as present now that it has, beside the two it is written to sit
    # with. This was the fifth claim this suite read forwards.
    assert "**ADR-0006 is owed for this shape**" in verdict
    assert "**lands with the machinery ticket**" in verdict
    assert "beside ADR-0004's mutation gate and ADR-0005's point gate" in verdict
    for number, slug in (
        ("0004", "the-mutation-gate-verdict-shape"),
        ("0005", "the-point-gate-verdict-shape"),
        ("0006", "the-complexity-proxy-verdict-shape"),
    ):
        assert (_REPO / "docs" / "adr" / f"{number}-{slug}.md").is_file()

    # The ruling this quotes, held against §117's own words.
    rulings = other_section(_RULINGS_HEADING)
    assert "wall-clock never enters the verdict path" in rulings


def test_the_gate_is_the_lints_two_pristine_invariants_as_a_quantifier() -> None:
    """§118.4: the round's single hard gate, stated as a universal quantifier.

    A gate stated as a quantifier has nothing in it to round and nothing in it
    to tune, which is what §82.5 wanted of one; writing it as a percentage
    would give it both back, so no `%` and no ratio belongs anywhere in this
    item's clause and this test says so mechanically.

    The other half of the claim is that the gate is **not new machinery**: the
    two invariants already run in `lint_task_set`'s per-task tail, and the
    section names them by symbol and by their own messages rather than by a
    line number — §83.4's precedent, because a line number in the note goes
    stale the next time the file is edited. Both messages are checked against
    the live source, so a reworded invariant cannot leave the note quoting a
    string the lint no longer emits.
    """
    gate = item("4")

    assert (
        "**118.4 The round's single hard gate: the task-set lint's two "
        "pristine invariants, over all three tasks, before the first sweep "
        "dollar.**"
    ) in gate
    assert "the only gate round 13 has" in gate

    # The bar, as a quantifier over every task and both invariants.
    assert (
        "**The bar is stated as a universal quantifier and never as a "
        "percentage.**"
    ) in gate
    assert f"**every one of the three `{_CATEGORY}` tasks**" in gate
    assert "**whole grading suite must not pass** on the pristine repository" in gate
    assert "**named behaviour half must pass** on it" in gate
    assert (
        "Every task, both invariants — no fraction met, no proportion "
        "computed, no threshold anywhere in the clause"
    ) in gate
    assert "%" not in gate
    assert not re.search(r"\d+\s*(?:of|/)\s*\d+", gate), (
        "a universal quantifier is not a ratio"
    )

    # Standing machinery, named by symbol and never by a line number.
    assert "**Both are invariants the lint already runs.**" in gate
    assert "`lint_task_set`'s per-task tail" in gate
    assert "(`src/ai_benchmark/firstparty_v1.py`)" in gate
    assert not re.search(r"firstparty_v1\.py:\d+", gate)
    assert "**grading-must-not-pass-on-pristine**" in gate
    assert f"`{_SPLIT_CATEGORY}`'s **behaviour-tests-pass-on-pristine**" in gate
    assert "reaching a second category through the loader move of 118.8" in gate
    assert "**standing machinery and not new machinery**" in gate
    assert "**the lint never calls an LLM**" in gate

    # Both quoted messages are the live lint's own, read out of the source.
    source = (_REPO / "src" / "ai_benchmark" / "firstparty_v1.py").read_text(
        encoding="utf-8"
    )
    assert hasattr(firstparty_v1, "lint_task_set")
    for message in (
        "the grading tests already pass on the pristine repo — there is "
        "nothing left for an agent to do",
        "the behaviour tests fail on the pristine repo — a refactor task must "
        "start from behaviour that already works",
    ):
        assert " ".join(message.split()) in gate, message
        assert message.split(" — ")[0] in " ".join(source.split()), message

    # The kill discipline, in its one standing sentence.
    assert (
        "**The kill discipline, in its one standing sentence: a failed gate "
        f"stops the round with a record, and `{_CATEGORY}` stays absent.**"
    ) in gate


def test_the_honest_proxy_and_prompt_rules_are_authoring_disciplines() -> None:
    """§118.5 and §118.6: two rules with no machinery behind either.

    Both are authoring disciplines, and both say so — a rule registered
    without naming what holds it reads as a rule something holds. What holds
    the honest-proxy rule is the spec review and the two pristine invariants
    of 118.4; what holds the prompt rule is the spec review alone. Each
    registers the failure mode it exists to prevent, because a discipline
    whose reason is not written down is re-argued the next time it is
    inconvenient.
    """
    proxy = item("5")
    assert (
        "**118.5 The honest-proxy rule, registered as an authoring "
        "discipline.**"
    ) in proxy
    assert (
        "**the counter counts a fact of the algorithm through a seam the "
        "repository owns — a comparator that counts its calls, a stub ledger "
        "that counts its reads — never a wall-clock and never an "
        "implementation constant.**"
    ) in proxy
    assert "**No machine lint holds it**" in proxy
    assert "the spec review, and the two pristine invariants of 118.4" in proxy
    assert (
        "**A proxy the unoptimised repository already satisfies is refused "
        "before any agent meets the task**"
    ) in proxy

    prompt = item("6")
    assert (
        "**118.6 The prompt rule: the observable requirement, never the "
        "counter's numbers.**"
    ) in prompt
    assert (
        "**names the hot operation and the scale requirement in observable "
        "behavioural terms**"
    ) in prompt
    assert "which listing must stay fast as which ledger grows" in prompt
    assert (
        "**never the counter's input sizes, ratios or ceilings**"
    ) in prompt
    assert "**silent on performance grades telepathy**" in prompt
    assert (
        "**naming the bound outright grades whether the agent can implement a "
        "named algorithm**"
    ) in prompt
    assert "**the deliverable is the code change itself**" in prompt
    assert "no answer file is asked for, none is collected" in prompt

    # Both are §117's, held against §117's own words.
    rulings = other_section(_RULINGS_HEADING)
    assert "never a wall-clock and never an implementation constant" in rulings
    assert "never the counter's input sizes, ratios or ceilings" in rulings


def test_the_disqualifier_rule_is_registered_forward_only_and_author_side() -> None:
    """§118.7: §117.4's rule, and the three rounds it does not reach back to.

    The rule costs this round nothing — nothing here is point-keyed — so the
    whole of what §118 owes is to state it in full, to say what polices it,
    and to say what it does *not* do: rounds 10, 11 and 12 stand as written
    and §115's addendum remains the permanent disclosure. A forward-only rule
    whose forward-onliness is left implicit is a rule the next reader takes as
    an invitation to re-author old keys.
    """
    rule = item("7")
    assert (
        "**118.7 The disqualifier surface-disjoint rule, registered "
        "forward-only.**"
    ) in rule
    assert (
        "**from this round on, a point-key disqualifier must name the wrong "
        "route in words surface-disjoint from the true mechanism's own**"
    ) in rule
    assert (
        "so that a correct statement of the true mechanism cannot match it"
    ) in rule
    assert "It is **author-side**" in rule
    assert "**no machinery moves for it**" in rule
    assert "no grader change, no new version tuple, no lint rule" in rule
    assert "And it is **forward-only**" in rule
    assert (
        "**round 10's, round 11's and round 12's keys, proofs, records and "
        "labels stand as written**"
    ) in rule
    assert (
        "**§115's addendum remains the permanent disclosure** of the adjacency "
        "the grocers key carries"
    ) in rule
    assert "**This round authors no point key**" in rule
    assert (
        "the rule costs this round nothing and binds future point-keyed "
        "authoring tickets' text"
    ) in rule

    rulings = other_section(_RULINGS_HEADING)
    assert (
        "a point-key disqualifier must name the wrong route in words "
        "surface-disjoint from the true mechanism's own"
    ) in rulings


def test_the_machinery_is_one_move_and_the_registries_gain_nothing() -> None:
    """§118.8: the loader move, and the two registries that do not move.

    The negative half is the one worth pinning mechanically, because it is the
    half a later ticket could quietly break: `EXISTENCE_PROOFS` owes no entry
    *because the category ships no key*, and the category joins no point
    machinery. Both are checked against the live registries rather than taken
    from the section's word, and the reason the first holds is checked too —
    `_unregistered_proof_form_problems` computes the keyed actions minus the
    registered ones, so an action outside that union is neither refused nor
    exempt, which is what the lint's own green run says.
    """
    machinery = item("8")
    assert "**118.8 The machinery, and that it is one move.**" in machinery
    assert (
        f"**behaviour/structural grading split — today `{_SPLIT_CATEGORY}`'s "
        "alone, held there by the loader's own two category validators — "
        f"extends to `{_CATEGORY}`**"
    ) in machinery
    assert "**The split's semantics are untouched**" in machinery
    assert "one more category allowed through them" in machinery

    assert "**Two things explicitly do not move.**" in machinery
    assert "**`EXISTENCE_PROOFS` gains no entry and owes none**" in machinery
    assert "**no key of any shape**" in machinery
    assert (
        "`_unregistered_proof_form_problems` computes the keyed actions minus "
        "the registered ones"
    ) in machinery
    assert "neither refused nor exempt" in machinery
    assert "**joins no point machinery**" in machinery
    assert "not `_POINT_CATEGORIES`, no points key, no terrain exemption" in machinery
    assert "**No new subcommand, no new flag**" in machinery
    assert (
        "no change to the runner, the readers, the point gate or the proofs "
        "writer"
    ) in machinery

    # The live registries, which say the same thing.
    assert _CATEGORY not in firstparty_v1.EXISTENCE_PROOFS
    assert _CATEGORY not in firstparty_v1._POINT_CATEGORIES
    assert _CATEGORY not in firstparty_v1._POINT_REQUIRED_CATEGORIES
    assert _CATEGORY != firstparty_v1._POINT_OPTIONAL_CATEGORY
    assert _CATEGORY not in firstparty_v1.TERRAIN_EXEMPT_ACTIONS
    # And the reason the first of those is not a gap: the action carries no
    # key, so it is not in the union the registry is checked against.
    assert firstparty_v1._unregistered_proof_form_problems() == []

    rulings = other_section(_RULINGS_HEADING)
    assert "gains no entry and owes none" in rulings


def test_the_limit_is_registered_as_registration_and_not_tuning() -> None:
    """§118.9's text: the number the machinery ticket must land, and why.

    This is the permanent half of the limit claim — what the *section* says —
    and it is separated from the live-dict half below because the two die at
    different tickets. What makes the entry worth registering when it changes
    no behaviour is that a number reached by a fallback is an inherited
    convention and a number in the dict is a considered commitment: §46's own
    distinction. The fallback's value is read out of the runner rather than
    trusted, because the whole claim rests on the two being the same number.
    """
    limit = item("9")
    assert (
        "**118.9 The run-time limit, registered before the sweep.**"
    ) in limit
    assert f"**`{_CATEGORY}: {_LIMIT_S}`**" in limit
    assert (
        "That is the flat default's own value (`RUN_TIMEOUT_S`, "
        "`src/ai_benchmark/firstparty.py:247`)"
    ) in limit
    assert (
        "the same envelope `bug-fix` ran its code-change-plus-tests loop in"
    ) in limit
    assert "**The entry is registration, not tuning.**" in limit
    assert "Behaviour is identical either way" in limit
    assert "**before the sweep**" in limit
    assert "**never adjusted per cell**" in limit
    assert (
        "a tier granted on no evidence could never be walked back honestly"
    ) in limit
    assert "**No cross-round caveat arises**" in limit
    assert "against round 12 or against any earlier round" in limit
    assert "are no part of the 600" in limit
    assert "**This ticket changes no code.**" in limit

    # The line the section cites for the fallback's value still says it, and
    # the fallback and the registered number are the same number.
    runner = (_REPO / "src" / "ai_benchmark" / "firstparty.py").read_text(
        encoding="utf-8"
    ).splitlines()
    assert f"RUN_TIMEOUT_S = {_LIMIT_S}" in runner[246]
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S.values()) == {_LIMIT_S}

    rulings = other_section(_RULINGS_HEADING)
    assert f"joins `LIVE_RUN_LIMITS_S` explicitly at **{_LIMIT_S}**" in rulings


def test_the_live_limits_carry_the_entry_the_section_registered() -> None:
    """The landed form of what was this suite's first forward-reading test.

    §118.9 registered the entry before a dollar was spent under it, and the
    round's machinery ticket landed it: `LIVE_RUN_LIMITS_S` now carries round
    4's two, round 5's two and this action, at the number the section named and
    at no other. The set is asserted whole rather than only for membership,
    because the claim §118.9 makes is that the round moved this one entry and
    nothing else in the dict.
    """
    assert set(firstparty_v1.LIVE_RUN_LIMITS_S) == _INHERITED_LIMITS | {_CATEGORY}
    assert firstparty_v1.LIVE_RUN_LIMITS_S[_CATEGORY] == _LIMIT_S
    # And the entry is registration rather than tuning: the fallback a category
    # with no row reaches is the same number, so the entry buys no seconds and
    # takes none away — only the commitment.
    assert firstparty.RUN_TIMEOUT_S == _LIMIT_S


def test_the_nine_cells_and_the_invocation_are_registered() -> None:
    """§118.10: three tasks × three columns, the sweep id, the dry cell, and
    the id register left explicitly to be filled in before the sweep.

    What this checks is the registration's shape: the columns, the count, the
    Python-only scope, the control declaration, the requirement that the three
    questions differ, the sweep's invocation, and the register — registered
    *as empty*, said to be left for the authoring tickets, with round 7's
    prefix pin named as the check the authoring runs first.
    """
    counted = prose()
    cells = item("10")

    assert agents.CODEX_REASONING_LEVELS["gpt-5.6-terra"] == "medium"
    assert (
        "`claude-code` × `claude-haiku-4-5`, `claude-code` × "
        "`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`"
    ) in cells
    assert (
        "**the three standing columns, unchanged from rounds 7, 8, 10, 11 and "
        "12**"
    ) in cells
    assert "three tasks × three combinations = **nine cells**" in cells
    assert f"three `{_CATEGORY}` tasks × the three standing columns" in cells

    # The two Claude columns are the ladder the reader already has; the Codex
    # one is the second harness and is deliberately not in it.
    assert reconcile_v1.LADDER_MODELS == ("claude-haiku-4-5", "claude-sonnet-5")

    assert "Each of the three is **Python**" in cells
    assert "stays out of scope this round" in cells
    assert "each is a **declared control**" in cells
    assert (
        "`control: true`, no construction block, no knob activation, no "
        "prediction"
    ) in cells
    assert (
        "**round 13 moves no knob's counter and the kill discipline does not "
        "count it**"
    ) in cells
    assert f"`calibrate-v1` gains no `{_CATEGORY}` multiplier row" in cells

    # The three questions differ, and the spec does not fix which three here.
    assert (
        "**The three tasks put three different performance questions**"
    ) in cells
    assert "**this section does not fix which three**" in cells
    assert "**requirement that they differ**" in cells
    assert (
        "three tasks that asked one performance question three times would "
        "measure one thing three times"
    ) in cells

    # The register, left where the authoring ticket picks it up.
    assert "**The three task ids do not exist yet**" in cells
    assert f"the corpus holds **no `{_CATEGORY}` task at all**" in cells
    assert "the category's coverage row reads `- - 0`" in cells
    assert (
        "**The id register for round 13 is left explicitly to be filled in, "
        "in this section, before the sweep, by the round's task-authoring "
        "tickets**"
    ) in cells
    assert (
        "**together with the three questions' one-line descriptions**"
    ) in cells
    assert "**Round 7's pin is the check the authoring runs first**" in cells
    assert "no task id may share a repo prefix with an existing task" in cells

    # The invocation.
    assert f"Sweep id **`{_SWEEP}`**" in cells
    assert "never queued" in cells
    assert (
        "A **dry cell first**, in its own invocation and **graded alone "
        "before the other eight**"
    ) in cells
    assert "**one paid cell rather than nine**" in cells
    assert "it is **not** a rehearsal to be re-run" in cells
    assert "bans `-dry` in a log's name" in cells
    assert "**`--task`**" in cells
    assert "**Nothing is re-run**" in cells

    command = block_holding("eval-v1")
    assert f"--sweep {_SWEEP}" in command
    assert "--agent claude-code" in command
    assert "--model claude-haiku-4-5" in command
    assert "-dry" not in command

    # The sweep id the round declares is one the archive has never carried.
    assert _SWEEP in counted


def test_the_register_names_every_performance_task_and_the_questions_differ(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """What was the second forward-reading test, in its final form: the
    register check.

    Its first form said no id-shaped block stood in §118 — the register was
    left explicitly to be filled in before the sweep. The round's second
    task-authoring ticket (ticket 05) landed tasks 2 and 3 and filled it, and
    this is §107.8's landed pattern a round on: the register is read against
    the corpus rather than restated — its three ids are exactly the
    `performance-optimisation` tasks the corpus holds, no fourth anywhere,
    and every one is the Python application-surface declared control §118.10
    registered. The three question-lines are present and distinct, each
    naming its task's kind of repetition — the axis §117.5 requires the three
    questions to differ on — with each kind carried exactly once across the
    three lines.
    """
    [register] = register_blocks()
    authored = sorted(
        task.id for task in tasks.values() if task.category == _CATEGORY
    )
    assert sorted(register) == authored, (
        "the register is the corpus's performance-optimisation set, whole"
    )
    assert len(register) == _CELLS, "and the corpus holds no fourth"

    # Each register line's gloss names its task's kind of repetition, and the
    # three kinds are three: a derivation re-taken inside a loop, a
    # whole-store scan per exact-match asking, an all-pairs reckoning over
    # one series. Each carried exactly once, and no gloss line repeated.
    kinds = (
        "re-derivation inside a loop",
        "scan per exact asking",
        "all-pairs reckoning",
    )
    for kind in kinds:
        assert len(
            [task_id for task_id, gloss in register.items() if kind in gloss]
        ) == 1, f"exactly one register gloss names {kind!r}"
    for task_id, gloss in register.items():
        assert gloss, f"{task_id}: its question-line is present"
    assert len(set(register.values())) == _CELLS, "and the three lines differ"

    for task_id in register:
        task = tasks[task_id]
        assert task.category == _CATEGORY
        assert task.language == "python"
        assert task.surface == "application"
        assert task.control is True
        assert task.construction is None


def test_the_corpus_holds_the_three_tasks_and_the_one_structural_zero(
    tasks: dict[str, firstparty_v1.Task],
) -> None:
    """What was the third forward-reading test, in its final form: the corpus
    with all three of the round's tasks landed.

    §118.2's claim about what the coverage table prints is a claim about the
    corpus, so it is read off the live table rather than off the note. Ticket
    04 authored the corpus's first `performance-optimisation` task — the last
    authorable `- - 0` row leaving the table — and ticket 05 the second and
    third, so the corpus holds exactly the **three fresh tasks** §118.2
    registered and no fourth. What stays is `unclassified`'s row, the one
    `- - 0` row left, permanent and structural exactly as §118.2 registers:
    the loader refuses any task declaring it, so no round can close it.
    """
    assert (
        len([task for task in tasks.values() if task.category == _CATEGORY])
        == _CELLS
    ), "the round's three tasks, whole, and no fourth"
    rows = firstparty_v1.coverage_table(list(tasks.values()))
    zeroes = [row[0] for row in rows if row[1:] == ("-", "-", 0)]
    assert zeroes == [_STRUCTURAL_ZERO], (
        "no authorable zero row left, and the structural one still printed"
    )


def test_the_sweep_band_is_derived_from_the_checked_in_round_12_rows(
    runs: list[firstparty_v1.Run],
) -> None:
    """§118.11's arithmetic, recomputed from the rows it claims to read.

    Round 12 swept nine cells of heap 3's last action, so the anchor is one
    round back — the same three combinations over the same nine-cell shape —
    selected by **sweep id** over every log in the directory and never by a log
    filename. Every figure the section quotes is re-derived here rather than
    lifted from §117.6, which is the whole point of re-deriving it there too: a
    registration that copied a ruling would inherit that ruling's arithmetic
    without ever checking that the anchor rows still say it.

    And this round the two do not agree. §117.6 and the round's spec name
    **$0.9185**, which is the three rounded columns added; the rows' own costs
    sum to **$0.9184** and the rounded-per-cell derivation comes to
    **$0.9183**. All three are checked here, and the section is required to
    register what the rows say and to flag the disagreement rather than adopt
    the spec's number — which is why the hundredth of a cent is asserted in
    both directions.

    Both ends of the caching bound are recomputed too, as is the ceiling's own
    comparator: §118.11 justifies its width by the corpus's own
    write-code-and-run-tests rows rather than by a hunch, and a justification
    that is arithmetic can be checked as arithmetic.
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
        ("claude-code", "claude-haiku-4-5"): 0.2113,
        ("claude-code", "claude-sonnet-5"): 0.4543,
        ("codex", "gpt-5.6-terra"): 0.2529,
    }
    per_cell = {
        combination: round(sum(run.cost_usd for run in found) / len(found), 4)
        for combination, found in anchor.items()
    }
    assert per_cell == {
        ("claude-code", "claude-haiku-4-5"): 0.0704,
        ("claude-code", "claude-sonnet-5"): 0.1514,
        ("codex", "gpt-5.6-terra"): 0.0843,
    }
    per_task = round(sum(per_cell.values()), 4)
    assert per_task == 0.3061
    flat = round(per_task * _CELLS, 4)
    assert flat == 0.9183
    landed = round(sum(sum(run.cost_usd for run in found)
                       for found in anchor.values()), 4)
    assert landed == 0.9184
    rounded_columns = round(sum(totals.values()), 4)
    assert rounded_columns == 0.9185

    # The three readings are three different numbers, which is the thing the
    # section has to flag rather than smooth over.
    assert len({flat, landed, rounded_columns}) == 3
    assert round(rounded_columns - landed, 4) == 0.0001
    assert round(landed - flat, 4) == 0.0001

    # And §117.6's own words are what the disagreement is against.
    rulings = other_section(_RULINGS_HEADING)
    assert f"${rounded_columns:.4f} landed" in rulings

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
    assert round(sum(columns.values()), 4) == flat
    assert f"total        ${flat:.4f}" in summed

    # The caching-aware envelope, at the checked-in price table — read, never
    # fetched, because this round fetches nothing.
    codex = anchor[("codex", "gpt-5.6-terra")]
    tokens_in = sum(run.tokens_in for run in codex)
    tokens_out = sum(run.tokens_out for run in codex)
    assert (tokens_in, tokens_out) == (361796, 7851)

    table = pricing.load_price_table(_REPO / "data" / "price-table.json")
    prices = table.models["gpt-5.6-terra"]
    logged = sum(run.cost_usd for run in codex)
    effective = (logged - tokens_out * prices.output_per_token) / tokens_in
    assert round(effective * 1e6, 4) == 0.4385

    output_cost = tokens_out * prices.output_per_token
    uncached = tokens_in * prices.input_uncached_per_token
    cached = tokens_in * prices.input_cached_per_token
    assert round(output_cost, 4) == 0.0942
    assert round(uncached, 4) == 0.7236
    assert round(cached, 4) == 0.0724
    assert (round(cached + output_cost, 2), round(uncached + output_cost, 2)) == (
        0.17, 0.82
    )
    assert round(tokens_in * effective + output_cost, 2) == 0.25

    claude = round(sum(columns[combination] for combination in _COMBINATIONS[:2]), 4)
    assert claude == 0.6654
    low = round(claude + cached + output_cost, 2)
    high = round(claude + uncached + output_cost, 2)
    assert (low, high) == (0.83, 1.48)

    # The registered band, re-derived. The floor is the flat extrapolation
    # rounded down to a round number; the ceiling is the first round number at
    # or above the corpus's own three-task figure for the dearest
    # write-code-and-run-tests round it holds.
    assert _FLOOR == round(flat - flat % 0.1, 1), "the floor is the anchor, rounded down"
    assert _FLOOR <= high <= _CEILING, (
        "the all-uncached bound must sit inside the registered range rather "
        "than at its ceiling — pricing the round at its upper bound is round "
        "6's error"
    )
    assert high < (_FLOOR + _CEILING) / 2, "and below its middle, which is §59.4's shape"
    # And §83.6's standing 1.8× multiple would *not* have kept that shape here,
    # which is the section's stated reason for the wider headroom.
    narrow = round(flat * 1.8, 2)
    assert narrow == 1.65
    assert (_FLOOR + narrow) / 2 < high, "1.8× this anchor puts its middle under the bound"

    # The two comparators the caveat and the ceiling are priced off, both
    # re-derived from the corpus's own rows rather than quoted.
    tasks = {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}
    bug_fix = {
        combination: round(
            sum(
                run.cost_usd for run in runs
                if (run.agent, run.model) == combination
                and run.task_id in tasks
                and tasks[run.task_id].category == "bug-fix"
            ) / len([
                run for run in runs
                if (run.agent, run.model) == combination
                and run.task_id in tasks
                and tasks[run.task_id].category == "bug-fix"
            ]), 4
        )
        for combination in _COMBINATIONS
    }
    assert list(bug_fix.values()) == [0.0949, 0.2201, 0.1103]
    assert round(sum(bug_fix.values()), 4) == 0.4253
    assert round(sum(bug_fix.values()) * _CELLS, 4) == 1.2759

    authoring = {
        combination: round(
            sum(
                run.cost_usd for run in runs
                if run.sweep == "round-8" and (run.agent, run.model) == combination
            ) / _CELLS, 4
        )
        for combination in _COMBINATIONS
    }
    assert list(authoring.values()) == [0.2412, 0.5893, 0.0899]
    per_task_authoring = round(sum(authoring.values()), 4)
    assert per_task_authoring == 0.9204
    three_tasks_authoring = round(per_task_authoring * _CELLS, 4)
    assert three_tasks_authoring == 2.7612
    assert _CEILING >= three_tasks_authoring, (
        "the ceiling is the first round number at or above the comparator"
    )
    assert round(_CEILING - 0.1, 1) < three_tasks_authoring, "and the first one"

    band = item("11")
    assert f"The sweep's price: ${_FLOOR}–{_CEILING}" in band
    assert "the round's only cost range" in band

    # No fetch performed, none owed.
    assert (
        "**No DeepSeek price fetch is performed and none is owed.**"
    ) in band
    assert "No grader call is priced because none is made" in band
    assert "**agent-run prices alone**" in band
    assert "**no `source_url`/`as_of` pricing block**" in band
    assert "`data/price-table.json`, which is checked in and read rather than fetched" in band

    assert f"selected by **sweep id `{_ANCHOR_ROUND}`**" in band
    assert "**never by a log's filename**" in band
    assert (
        "**Round 12 is the nearest anchor this corpus has and it is one round "
        "back**"
    ) in band
    assert "**$0.2113** on `claude-haiku-4-5`" in band
    assert "**$0.4543** on `claude-sonnet-5`" in band
    assert "**$0.2529** on `codex` × `gpt-5.6-terra`" in band
    assert "**$0.0704**, **$0.1514** and **$0.0843** a cell" in band
    assert "**$0.3061 a task across the three combinations**" in band
    assert f"three tasks come to **${flat:.4f}**" in band

    # The disagreement, flagged in as many words rather than absorbed.
    assert (
        "**The derivation disagrees with the figure §117.6 and the round's "
        "spec name, and the disagreement is flagged rather than absorbed.**"
    ) in band
    assert f"**$117.6 names ${rounded_columns:.4f}**" in band
    assert f"**the rows' own costs sum to ${landed:.4f}**" in band
    assert f"comes to **${flat:.4f}**" in band
    assert "the hundredth of a cent the rounding costs" in band
    assert (
        f"**What this section registers is what the rows say — ${landed:.4f} "
        f"landed, ${flat:.4f} flat-extrapolated**"
    ) in band

    assert "**361,796** input tokens and wrote **7,851**" in band
    assert "**$0.17 all-cached to $0.82 all-uncached**" in band
    assert "**$0.4385/M**" in band
    assert "expected figure near **$0.25**" in band
    assert "**$0.6654** together" in band
    assert "**$0.83 all-cached to $1.48 all-uncached**" in band

    # The anchor's caveat, in as many words, and priced rather than asserted.
    assert (
        "**The anchor's honest caveat, in as many words: a perf cell makes a "
        "real code change and runs tests, so it may run longer and dearer "
        "than an explain cell, and the band prices that rather than assuming "
        "the anchor transfers.**"
    ) in band
    assert "**$0.0949**, **$0.2201** and **$0.1103** on the three columns" in band
    assert "**$0.4253 a task**" in band
    assert f"**${round(sum(bug_fix.values()) * _CELLS, 4):.4f}** for three tasks" in band
    assert "**$0.2412**, **$0.5893** and **$0.0899** a cell" in band
    assert f"**${per_task_authoring:.4f} a task**" in band
    assert f"**${three_tasks_authoring:.4f}** for three tasks" in band

    # The band's two ends, each with the rule that set it.
    assert f"The **floor is ${_FLOOR}**" in band
    assert "rounded down to a round number" in band
    assert f"The **ceiling is ${_CEILING}**" in band
    assert f"the first round number at or above **${three_tasks_authoring:.4f}**" in band
    assert "**bound and not an expectation**" in band
    assert f"1.8× the anchor is **${narrow:.2f}**" in band
    assert f"the middle of ${_FLOOR}–{narrow:.2f} is **${(_FLOOR + narrow) / 2:.4f}**" in band
    assert f"the middle is **${(_FLOOR + _CEILING) / 2:.4f}**" in band

    # Both miss directions, pre-read before the sweep.
    assert "The **low** miss has two routes" in band
    assert "The range's floor *is* the flat extrapolation" in band
    assert "would be a genuine finding about the action" in band
    assert "**$0.07 under the floor**" in band
    assert (
        "an optimisation loop that re-runs a slow suite after every edit"
    ) in band
    assert f"**${_CEILING} is where the record is to stop and say so**" in band

    # The stance itself, unchanged: a ChatGPT-login account is not metered, so
    # the Codex figure is an equivalent and never an invoice.
    assert "authenticated by **ChatGPT login**, not by an API key" in band
    assert "**not billed per token**" in band
    assert "**list-price equivalent**" in band
    assert "`cost_source: table-derived`" in band
    assert "`cost_source: vendor-reported`" in band
    assert "sweep protocol's own item 2 (`docs/agents/sweep-protocol.md`)" in band
    assert "**There is no third kind of spend this round**" in band


def test_no_new_sweep_row_lands_before_the_rounds_own_sweep(
    logs: list[Path], runs: list[firstparty_v1.Run]
) -> None:
    """§118.12: the anchor the sweep's band is derived over, held still.

    §80.4's guardrail carried forward, for this round's own reason: §118.11's
    band is derived over the nine `round-12` rows as they stand, so a sweep row
    landing between this registration and the round's own sweep would move the
    anchor out from under a range already registered against it.

    Landed form: the round's own sweep (2026-08-29-r13-a..d) is the one
    arrival the registered sentence allowed, and nothing else landed.

    The archive's size is re-derived here from the logs themselves —
    wholesale, keyed on what the rows carry and never on a filename — rather
    than taken from the section's prose, which is what makes the registered
    sentence a claim about the corpus and not about itself.
    """
    # Landed form: the archive grew by exactly the round's own sweep and by
    # nothing else — 49 logs and 333 rows at registration, plus the sweep's
    # four logs and nine `round-13` rows, keyed on what the rows carry.
    assert len(logs) == 53
    assert len(runs) == 342
    late = [run for run in runs if run.sweep == _SWEEP]
    assert len(late) == _CELLS * 3
    assert len(runs) - len(late) == 333, "nothing else landed in between"
    assert len([run for run in runs if run.sweep == _ANCHOR_ROUND]) == _CELLS * 3

    band = item("12")
    assert (
        "**118.12 No new sweep row lands between this registration and the "
        "round's own sweep.**"
    ) in band
    assert (
        f"derived over the **nine `{_ANCHOR_ROUND}` rows as they stand**"
    ) in band
    assert "**the rows this section registers**" in band
    assert "Run before the round's own sweep it must print nothing" in band

    check = block_holding("-newermt").strip()
    assert check == "find data/first-party-v1-runs -type f -newermt 2026-08-29"


def test_the_round_13_cells_are_the_nine_registered(
    tasks: dict[str, firstparty_v1.Task], runs: list[firstparty_v1.Run],
) -> None:
    """The fourth forward-reading test, in its landed form.

    Its first form said no `round-13` row existed yet — a registration, not a
    record — and was retired by the sweep it foresaw (2026-08-29-r13-a..d,
    dry cell first). What it holds the round to now is the landed version of
    the same claim: the cells carrying sweep id `round-13` are exactly the
    nine §118.10 registered — the register's three tasks under the three
    standing combinations — none repeated. Each cell's verdict is computed
    from execution, §118.3's shape: the two held-out suites recompute offline
    from the logged diff, and no rulings archive exists for any of the nine,
    because the round authors no point key and grades through no instrument.
    The verdicts' own reading — who resolved, at what dollar — belongs to the
    round's record, not here.

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
    for run in swept:
        # Computable offline, with no grader anywhere: a diff that cannot
        # grade raises rather than returning, so each call is the claim that
        # the cell's verdict is a pure function of what is checked in.
        assert isinstance(
            firstparty_v1.grade(tasks[run.task_id], run.diff), bool
        ), f"{run.task_id} x {run.agent} x {run.model}: verdict computes"
    for task_id, agent, model in sorted(cells):
        assert not firstparty_v1.rulings_file(
            _RULINGS, task_id, agent, model
        ).is_file(), (
            f"{task_id} x {agent} x {model}: no rulings archive — the "
            "verdict is execution, not an instrument's ruling"
        )

    assert {run.sweep for run in runs} == {
        None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
        "round-8", "round-10", "round-11", _ANCHOR_ROUND, _SWEEP,
    }, "`None` is round 1, which predates `--sweep` and is keyed on `as_of`"
