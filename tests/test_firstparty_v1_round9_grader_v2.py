"""Grader v2's re-registration, pinned: what §80.4 commits to before the
second experiment's first paid call.

Round 9's first experiment failed its gate (§79). §80 is the replan — the
prompt revised, the model, the settings and the bar left alone — and §80.4 is
its register, the second experiment's equivalent of §77's and §78.4's: the
version tuple, the split, the bar and the price, all written down while not
one paid call has been made under the new instrument. This file is that
register's pin.

The disciplines are `test_firstparty_v1_round9_cells.py`'s and are inherited
rather than re-argued.

**The register is the design note**, not a constant in code, so every test
below reads §80.4's own fenced blocks and its own prose and then re-derives
what they claim — from the task set, from the checked-in run logs, from the
live `point_grader` constants and from the prices the section records having
fetched. A figure that cannot be reproduced from the corpus is a number
somebody wrote down.

**No test here selects a run log by filename**, and no string the register
must earn is typed here: the version tuple is read off
`point_grader.GRADER_VERSION`, the split is recomputed the way `--split-only`
recomputes it, and the price arithmetic is redone over the live
`point_grader.PROMPT`.

Nothing here calls the grader or spends a dollar. The last two tests are the
guardrail ones: the run-log directory the split was registered over still
holds exactly what it held, no `round-9` row has appeared under it, and
nothing from calibration has reached `data/unified.jsonl`. (§81's run has
since spent the registration, and round 10's sweep landed the first rows
after it on 2026-08-24; the guardrail carries that claim in its landed form,
with the registered corpus scoped back out by sweep id.)
"""

import hashlib
import json
from pathlib import Path

import pytest

from ai_benchmark import (
    firstparty_v1,
    grader_calibration_v1,
    point_grader,
    reconcile_v1,
)

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"
_NOTE = _REPO / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"
_UNIFIED = _REPO / "data" / "unified.jsonl"
_ARCHIVES = _REPO / "data" / "point-gate-calibration"

# §80.4 runs from its own bolded number to §80.5's. Slicing to the next
# top-level heading would swallow §80.5 and §80.6 whole and these pins would
# stop being assertions about the register.
_ITEM = "**80.4 The re-registration"
_NEXT_ITEM = "**80.5 What §79 keeps"

# The sweep id that must not appear before §81's run, and the eight the logs
# carried at the registration. `None` is round 1, which predates `--sweep`.
# Round 10's later sweep is admitted only where the landed-form guardrail
# below names it, never here.
_SWEEP = "round-9"
_SWEPT_SO_FAR = {
    None, "round-2", "round-3", "round-4", "round-5", "round-6", "round-7",
    "round-8",
}

# The corpus the split was registered over, as counts (§77.2, re-derived by
# §80.4 and required identical).
_LOGS_HELD = 37
_ANSWERS = 306
_STRATUM_A = 63
_POINTS_A = 115
_REVIEW_POINTS = 78
_STRATUM_B = 243
_CALLS = 358
_RESOLVED = 55
_UNRESOLVED = 8

# §77.3's bar, unchanged by §80 and restated by §80.4 so a reader need not
# chase it. A revised prompt re-argues no bar.
_OVERALL_BAR = 57
_UNRESOLVED_BAR = 7

# The convention the token arithmetic is done at, as in §77.4.
_CHARS_PER_TOKEN = 4

# What the `deepseek-v4-pro` column said when §80.4's own fetch read it, per
# million tokens: **peak-hour** prices and the **cache-miss** input price,
# which is what §78.4 registers this round at and §80.4 re-derives at.
_INPUT_PER_MTOK = 1.32
_OUTPUT_PER_MTOK = 3.96
_CACHE_HIT_PER_MTOK = 0.044
_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"
_AS_OF = "2026-08-23"

# The range §77.4 registered, which §80.4 either reaffirms or replaces.
_RANGE_LOW = 0.25
_RANGE_HIGH = 1.5


def item() -> str:
    """§80.4, from its own number to §80.5's."""
    text = _NOTE.read_text(encoding="utf-8")
    start = text.index(_ITEM)
    return text[start : text.index(_NEXT_ITEM, start)]


def prose() -> str:
    """The item with its wrapping collapsed. What a sentence says is the pin;
    where the line happens to break is not."""
    return " ".join(item().split())


def blocks() -> list[str]:
    """The item's fenced blocks, in order."""
    return item().split("```")[1::2]


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


def register_line(label: str) -> str:
    """One line of the register block, by its label, with the label stripped
    and the continuation lines folded in."""
    register = block_holding("grader v2 version tuple:")
    lines = [line for line in register.splitlines() if line.strip()]
    starts = [i for i, line in enumerate(lines) if line.startswith(label)]
    assert len(starts) == 1, f"exactly one register line reads {label!r}"
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if not lines[i].startswith(" ")
        ),
        len(lines),
    )
    body = [lines[start][len(label):]] + lines[start + 1 : end]
    return " ".join(" ".join(body).split())


@pytest.fixture(scope="module")
def tasks() -> dict[str, firstparty_v1.Task]:
    return {task.id: task for task in firstparty_v1.load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def logs() -> list[Path]:
    """Every log under the run-log directory, collected wholesale. Selecting
    on a filename is what the sweep protocol forbids."""
    return reconcile_v1.collect_logs([_LOGS])


@pytest.fixture(scope="module")
def runs(logs: list[Path]) -> list[firstparty_v1.Run]:
    return [run for log in logs for run in firstparty_v1.load_runs(log)]


@pytest.fixture(scope="module")
def registered(runs: list[firstparty_v1.Run]) -> list[firstparty_v1.Run]:
    """The corpus §80.4 registered the split over, which §81's run then spent:
    every sweep before round 10's, which landed the first `investigation` rows
    on 2026-08-24. Scoped by sweep id, never by a log filename; the registered
    counts below stay §80.4's own, unretyped."""
    return [run for run in runs if run.sweep != "round-10"]


@pytest.fixture(scope="module")
def stratum_a(
    tasks: dict[str, firstparty_v1.Task],
    registered: list[firstparty_v1.Run],
) -> list[firstparty_v1.Run]:
    """The archived answers the gate is read over: every row whose task ships
    a key the grader can be run against in exactly its production mode."""
    return [
        run for run in registered
        if firstparty_v1.carries_a_key(tasks[run.task_id])
    ]


def test_the_register_quotes_the_live_version_tuple() -> None:
    """§80.4: the v2 tuple, quoted verbatim out of `GRADER_VERSION`.

    A bar met at one grader version says nothing about a bar met at another,
    which is exactly the sentence §77.8 registered and exactly why the second
    experiment needs its own register rather than a footnote on the first. So
    the tuple is read here off the live constant and never typed: the string
    in the note must be what the code computes today, its three parts must be
    the three constants the code assembles it from, and the prompt hash must
    be the hash of the prompt that will actually be sent.

    Which part moved is the whole claim of the item. The alias and the
    checkpoint are asserted unchanged against v1's own tuple — read off the v1
    rulings archive's filename rather than typed, since that file is v1's
    record and cannot drift — and the hash is asserted to have moved.
    """
    quoted = register_line("grader v2 version tuple:")
    assert quoted == point_grader.GRADER_VERSION
    assert quoted == (
        f"{point_grader.GRADER_MODEL}:{point_grader.GRADER_CHECKPOINT}"
        f":{point_grader.PROMPT_HASH}"
    )
    assert len(quoted.split(":")) == 3

    # The hash is the prompt's, re-derived rather than trusted.
    assert point_grader.PROMPT_HASH == (
        hashlib.sha256(point_grader.PROMPT.encode()).hexdigest()[:12]
    )

    # v1's tuple, read off the archive it named rather than typed here. §81's
    # run has since happened (the named exception this suite absorbs once),
    # so the directory holds exactly the two instruments' files — v1's and
    # the live tuple's — and v1's is the one that is not the live tuple.
    archived = sorted(path.stem for path in _ARCHIVES.glob("*.json"))
    assert len(archived) == 2, "v1's rulings file and §81's v2 file, no more"
    assert point_grader.GRADER_VERSION in archived
    (v1_tuple,) = [one for one in archived if one != point_grader.GRADER_VERSION]
    v1_alias, v1_checkpoint, v1_hash = v1_tuple.split(":")
    assert v1_alias == point_grader.GRADER_MODEL, "the alias did not move"
    assert v1_checkpoint == point_grader.GRADER_CHECKPOINT, (
        "the checkpoint did not move"
    )
    assert v1_hash != point_grader.PROMPT_HASH, "the prompt hash is what moved"

    counted = prose()
    assert "`point_grader.GRADER_VERSION`" in counted
    assert "**The alias is unchanged**" in counted
    assert "**The checkpoint is unchanged**" in counted
    assert "**The prompt hash is what moved**" in counted
    assert f"`{v1_hash}` becomes `{point_grader.PROMPT_HASH}`" in counted
    assert "**a different instrument**" in counted
    assert (
        "a new version string, a new rulings file named by it, and the same "
        "bar met afresh or not at all"
    ) in counted
    # §77.8 records the v1 instrument and is not edited again.
    assert "**§77.8 is not edited**" in counted
    # The checkpoint was re-verified against a fresh fetch, and a moved one
    # would have stopped the registration rather than been absorbed by it.
    assert "re-verified against the fresh pinned fetch" in counted
    assert "`MODEL VERSION` cell still announces it" in counted
    assert "stopped this registration rather than being absorbed" in counted


def test_the_split_re_derived_offline_equals_the_registered_counts(
    tasks: dict[str, firstparty_v1.Task],
    logs: list[Path],
    registered: list[firstparty_v1.Run],
    stratum_a: list[firstparty_v1.Run],
) -> None:
    """§80.4: the split, re-derived and required identical to §77.2's.

    Two experiments read over one corpus is what makes the v1 and v2 verdicts
    comparable, so the register does not carry §77.2's counts across — it
    re-derives them and stops if any of them moved. This recomputes the same
    derivation offline: the strata from the key shape each task ships, the
    points from the keys themselves, and the resolved/unresolved verdicts the
    way `--split-only` computes them, by replaying each archived diff against
    its own task's held-out tests. No grader is built and no call is made,
    which is what lets the register be written before the first paid ruling.
    """
    # 41 files since round 10's four sweep logs joined the directory on
    # 2026-08-24. The corpus §80.4 registered — `_LOGS_HELD` logs' rows — is
    # scoped from every row by sweep id and re-derived below at its own
    # counts, unretyped; that its rows sit in exactly `_LOGS_HELD` of the
    # files is asserted with the guardrail test below.
    assert len(logs) == 41
    assert len(registered) == _ANSWERS
    assert len(stratum_a) == _STRATUM_A
    assert len(registered) - len(stratum_a) == _STRATUM_B

    points = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
    )
    review_points = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
        if tasks[run.task_id].category == "code-review"
    )
    assert (points, review_points) == (_POINTS_A, _REVIEW_POINTS)
    assert points + _STRATUM_B == _CALLS

    resolved = [
        firstparty_v1.grade(tasks[run.task_id], run.diff) for run in stratum_a
    ]
    assert (resolved.count(True), resolved.count(False)) == (
        _RESOLVED, _UNRESOLVED,
    )

    # The command's own printed table, as the item quotes it. Read row by row
    # with each row's column padding collapsed: what the table pins is the
    # counts it carries, not the widths the command aligned them to.
    printed = {
        " ".join(line.split())
        for line in block_holding("stratum  answers  points", "(all)").splitlines()
    }
    for row in (
        f"A {_STRATUM_A} {_POINTS_A} the task's planted key, run in production mode",
        f'B {_STRATUM_B} {_STRATUM_B} the synthetic point "the asked-for work '
        'was done"',
        "code-review 26 78 19 7",
        "codebase-comprehension 10 10 10 0",
        "fault-location 27 27 26 1",
        f"(all) {_STRATUM_A} {_POINTS_A} {_RESOLVED} {_UNRESOLVED}",
        f"grader calls: {_POINTS_A} on stratum A + {_STRATUM_B} on stratum B "
        f"= {_CALLS} in all",
    ):
        assert row in printed, row

    # And the register's own line carries the counts and the date it was run.
    quoted = register_line("split re-derived:")
    assert quoted.startswith(_AS_OF)
    for count in (
        f"{_STRATUM_A} answers / {_POINTS_A} points",
        f"{_RESOLVED} resolved / {_UNRESOLVED} unresolved",
        f"stratum B {_STRATUM_B}",
        f"{_CALLS} archive calls",
    ):
        assert count in quoted, count

    counted = prose()
    assert "--split-only" in counted
    assert "no grader built, no call made" in counted
    assert f"was run on **{_AS_OF}** and printed" in counted
    assert (
        f"over the same **{_ANSWERS}** archived answers in the same "
        f"**{_LOGS_HELD}** run logs"
    ) in counted
    assert "**Every count matches §77.2's to the answer**" in counted
    assert "stopped this registration by design" in counted
    # The command's own instrument line is a second place to read the tuple
    # from, named as such and not used as the source.
    assert "printed the v2 tuple above" in counted


def test_the_bar_is_restated_unchanged_and_re_argued_by_nothing() -> None:
    """§80.4: ≥ 57 of 63 and ≥ 7 of 8, §77.3's counts verbatim.

    The bar is the one part of the instrument §80 deliberately does not touch,
    and restating it inside the register is what stops a reader of the second
    experiment from having to chase §77.3 — or, worse, from re-deriving it
    beside a result. The rounding that produced the two counts is §77.3's and
    is pointed at rather than repeated: doing that arithmetic twice invites
    two answers.
    """
    printed = {
        " ".join(line.split())
        for line in block_holding("overall agreement").splitlines()
    }
    assert f"overall agreement >= {_OVERALL_BAR} of {_STRATUM_A}" in printed
    assert (
        f"unresolved-class agreement >= {_UNRESOLVED_BAR} of {_UNRESOLVED}"
    ) in printed

    counted = prose()
    assert (
        f"**The bar, unchanged: ≥ {_OVERALL_BAR} of {_STRATUM_A} overall and "
        f"≥ {_UNRESOLVED_BAR} of {_UNRESOLVED} unresolved-class.**"
    ) in counted
    assert "§77.3's counts verbatim" in counted
    assert "**A revised prompt re-argues no bar.**" in counted
    assert "a bar fitted to a result" in counted
    # Pointed at, not re-derived: the rounding lines live in §77.3 and the
    # register must not carry a second copy of them.
    assert "0.90 x 63" not in item()
    assert "0.80 x  8" not in item()


def test_the_price_is_re_derived_from_the_live_prompt_at_fetched_prices(
    tasks: dict[str, firstparty_v1.Task],
    stratum_a: list[firstparty_v1.Run],
    registered: list[firstparty_v1.Run],
) -> None:
    """§80.4: §77.4's method over the v2 prompt, inside the registered range.

    The prompt moved with §80.2's revisions, so the filled-prompt arithmetic
    is redone rather than carried: every character total below is recomputed
    from the live `point_grader.PROMPT`, filled the way the grader fills it,
    over every archived answer. What did not move is the archive, and it is
    checked here rather than assumed — the deliverable characters, the
    stratum-A answer lengths and the whole call table are re-derived and must
    still be what §77.4 registered.

    A model's memory of a pricing page is not a source, so the item records
    the command the prices were read with and the date they were read on;
    those two are checked for here, and the per-MTok figures they carry are
    what the arithmetic is done at — peak-hour and cache-miss, the
    conservative end twice over.
    """
    keyed_calls = sum(
        len(grader_calibration_v1.points_for(tasks[run.task_id]))
        for run in stratum_a
    )
    # The arithmetic is the registered corpus's — every row before round 10's
    # sweep, scoped by sweep id — so the figures stay §80.4's own.
    synthetic_calls = len(registered) - len(stratum_a)
    assert keyed_calls + synthetic_calls == _CALLS

    prompt_chars = 0
    deliverable_chars = 0
    for run in registered:
        for point in grader_calibration_v1.points_for(tasks[run.task_id]):
            prompt_chars += len(
                point_grader.PROMPT.format(
                    point_id=point["id"],
                    point_text=point["text"],
                    deliverable=run.output,
                )
            )
            deliverable_chars += len(run.output)

    # Derived from the archive, and unmoved by the revision.
    assert deliverable_chars == 212658
    lengths = sorted(len(run.output) for run in stratum_a)
    assert (lengths[0], lengths[-1]) == (45, 1379)
    assert lengths[len(lengths) // 2] == 352

    # Derived from the live prompt, and moved by it.
    assert prompt_chars == 757956
    assert len(point_grader.PROMPT) == 1461
    # The shared prefix a detected common prefix could cover: the template up
    # to the point id. It did not move, so §77.4's cache paragraph carries.
    assert len(point_grader.PROMPT.split("{point_id}")[0]) == 223

    per_input = _INPUT_PER_MTOK / 1e6
    per_output = _OUTPUT_PER_MTOK / 1e6

    input_tokens = prompt_chars // _CHARS_PER_TOKEN
    quoted_tokens = deliverable_chars // _CHARS_PER_TOKEN
    assert (input_tokens, quoted_tokens) == (189489, 53164)

    low_out = _CALLS * 100
    high_out = _CALLS * 300 + quoted_tokens
    assert (low_out, high_out) == (35800, 160564)

    input_cost = round(input_tokens * per_input, 4)
    archive_low = round(input_tokens * per_input + low_out * per_output, 4)
    archive_high = round(input_tokens * per_input + high_out * per_output, 4)
    assert input_cost == 0.2501
    assert round(low_out * per_output, 4) == 0.1418
    assert round(high_out * per_output, 4) == 0.6358
    assert (archive_low, archive_high) == (0.3919, 0.8860)

    # The proofs: contingent on the bar, over the same 24-48 calls; only the
    # surround moved, and it moved with the template.
    assert (3 * (4 + 0) * 2, 3 * (6 + 2) * 2) == (24, 48)
    surround = len(point_grader.PROMPT) + 200
    assert surround == 1661
    proof_low_in = 24 * (4000 + surround) // _CHARS_PER_TOKEN
    proof_high_in = 48 * (8000 + surround) // _CHARS_PER_TOKEN
    assert (proof_low_in, proof_high_in) == (33966, 115932)
    proof_low_out = 24 * 100
    proof_high_out = 48 * (8000 // _CHARS_PER_TOKEN + 300)
    assert (proof_low_out, proof_high_out) == (2400, 110400)
    proofs_low = round(proof_low_in * per_input + proof_low_out * per_output, 4)
    proofs_high = round(
        proof_high_in * per_input + proof_high_out * per_output, 4
    )
    assert round(proof_low_in * per_input, 4) == 0.0448
    assert round(proof_high_in * per_input, 4) == 0.1530
    assert round(proof_high_out * per_output, 4) == 0.4372
    assert (proofs_low, proofs_high) == (0.0543, 0.5902)

    total_low = round(archive_low + proofs_low, 4)
    total_high = round(archive_high + proofs_high, 4)
    assert (total_low, total_high) == (0.4462, 1.4762)
    # The registered range still holds the arithmetic at both ends, which is
    # what "reaffirmed" means and what the register claims.
    assert _RANGE_LOW <= total_low and total_high <= _RANGE_HIGH

    arithmetic = block_holding("round total")
    for line in (
        f"input   {prompt_chars:,} chars / 4                    "
        f"= {input_tokens:,} tok  x ${_INPUT_PER_MTOK}/M = ${input_cost:.4f}",
        f"output  low   {_CALLS} calls x 100 tok thinking   =  {low_out:,} tok  "
        f"x ${_OUTPUT_PER_MTOK}/M = $0.1418",
        f"        high  {_CALLS} x 300 tok + {quoted_tokens:,} quoted  "
        f"= {high_out:,} tok  x ${_OUTPUT_PER_MTOK}/M = $0.6358",
        f"archive half  ${archive_low:.4f} - ${archive_high:.4f}",
        f"proofs  low   24 calls x {4000 + surround:,} chars / 4     "
        f"=  {proof_low_in:,} tok  x ${_INPUT_PER_MTOK}/M = $0.0448",
        f"        high  48 calls x {8000 + surround:,} chars / 4     "
        f"= {proof_high_in:,} tok  x ${_INPUT_PER_MTOK}/M = $0.1530",
        f"              48 x (2,000 quoted + 300)      = {proof_high_out:,} tok  "
        f"x ${_OUTPUT_PER_MTOK}/M = $0.4372",
        f"proofs half   ${proofs_low:.4f} - ${proofs_high:.4f}",
        f"round total   ${total_low:.4f} - ${total_high:.4f}",
    ):
        assert line in arithmetic, line

    # The fetch itself, pinned as the command that was run.
    assert block_holding(_PRICING_URL).strip() == f"curl -sL {_PRICING_URL}"

    counted = prose()
    assert "**The prices were read, not remembered.**" in counted
    assert f"Fetched on **{_AS_OF}** with" in counted
    assert f"`source_url`: `{_PRICING_URL}`" in counted
    assert f"`as_of`: **{_AS_OF}**" in counted
    assert f"column **{point_grader.GRADER_MODEL}**" in counted
    assert f"**${_INPUT_PER_MTOK} / MTok** peak input on a cache miss" in counted
    assert (
        f"**${_CACHE_HIT_PER_MTOK} / MTok** peak input on a cache hit"
    ) in counted
    assert f"**${_OUTPUT_PER_MTOK} / MTok** peak output" in counted
    assert f"`{point_grader.GRADER_CHECKPOINT}`" in counted
    assert "peak-hour list pricing, cache-miss" in counted

    # The footnote as this fetch read it — the schedule moved and the prices
    # did not, and both facts are on the record rather than one of them.
    assert (
        '"Off-peak rates are half of the peak rates. Peak hours are 01:00 - '
        '04:00 and 06:00 - 10:00 UTC, Monday through Friday (all other hours '
        'are off-peak)."'
    ) in counted
    assert "**The schedule moved and the prices did not**" in counted

    # What was redone and what was checked, said in as many words.
    assert "redone rather than carried" in counted
    assert (
        f"goes from **954** to **{len(point_grader.PROMPT):,}** characters"
    ) in counted
    assert f"to **{prompt_chars:,}**" in counted
    assert f"**{deliverable_chars:,} characters**" in counted
    assert "**45–1379 characters, median 352**" in counted
    assert (
        f"27 × 1 + 26 × 3 + 10 × 1 = {_POINTS_A} on stratum A plus "
        f"{_STRATUM_B} on stratum B = **{_CALLS}**"
    ) in counted
    assert "template's leading **223** characters" in counted

    # Reaffirmed, not re-registered — and the thinner headroom disclosed.
    quoted = register_line("price:")
    assert quoted.startswith(f"${_RANGE_LOW}–{_RANGE_HIGH} reaffirmed")
    assert f"${total_low:.4f}–{total_high:.4f}" in quoted
    assert "**The registered range holds**" in counted
    assert "**reaffirmed rather than re-registered**" in counted
    assert "no range is superseded by this item" in counted
    assert "The headroom at the top is thinner than it was" in counted


def test_no_new_sweep_row_has_landed_under_the_run_log_directory(
    logs: list[Path], runs: list[firstparty_v1.Run]
) -> None:
    """§80.4's standing guardrail, pinned rather than trusted.

    The split above is only a registration if the corpus it was registered
    over is the corpus §81 reads. A row landing under the run-log directory
    between this registration and the paid run would move the split silently
    — the answers, the points and the calls all count rows — so the guardrail
    is stated in the item and checked here: the same 37 logs, the same 306
    answers, and no `round-9` row, selected by **sweep id** over every log in
    the directory and never by a log filename.

    Landed form: §81's run has since spent the registration, and round 10's
    sweep then landed the first rows after it, on 2026-08-24 — every one
    carrying sweep id `round-10`. What stays checkable is that the corpus
    held still between the registration and the run: the registered logs
    still hold exactly the registered answers, nothing beyond them carries
    any sweep id but round 10's, and no `round-9` row ever appeared.
    """
    # The directory grew by round 10's four sweep logs and nine rows, keyed
    # on what the rows carry; the registered corpus is scoped back out by
    # sweep id, its counts unretyped.
    assert len(logs) == 41
    late = [run for run in runs if run.sweep == "round-10"]
    assert len(late) == 9
    assert len(runs) - len(late) == _ANSWERS
    # A registered log is one no round-10 row landed in — keyed on what its
    # rows carry, and counting round 7's two empty logs the way the register
    # did (a file with no rows is still a file the split was registered over).
    held = [
        log for log in logs
        if all(
            run.sweep != "round-10" for run in firstparty_v1.load_runs(log)
        )
    ]
    assert len(held) == _LOGS_HELD
    assert not [run for run in runs if run.sweep == _SWEEP], (
        "a round-9 row exists: the split §80.4 registered has moved under it, "
        "which is a stop-and-report rather than a re-registration"
    )
    # `round-10` is the one sweep id the landed form admits beyond §80.4's
    # eight; the registered census constant stays as registered.
    assert {run.sweep for run in runs} == _SWEPT_SO_FAR | {"round-10"}

    counted = prose()
    assert (
        "**no new sweep row lands under `data/first-party-v1-runs/` between "
        "this registration and §81's run.**"
    ) in counted


def test_nothing_from_calibration_is_in_the_unified_dataset() -> None:
    """A record keeps meaning one thing: a combination's result on a benchmark
    instance. Calibration rulings are instrument data and stay under `data/`
    with the grader's version (§76.11), so the second experiment inherits the
    first's rule and it is pinned before the run rather than after it."""
    text = _UNIFIED.read_text(encoding="utf-8")
    for line in filter(None, text.splitlines()):
        row = json.loads(line)
        flat = json.dumps(row)
        assert "point-gate-calibration" not in flat
        assert point_grader.GRADER_MODEL not in flat
        assert _SWEEP not in json.dumps(row.get("sweep_id", ""))


def test_the_register_was_written_before_the_first_paid_call() -> None:
    """§80.4 registered; §81 has since recorded — the run session's named
    exception, updated here once, when the v2 rulings file landed.

    As written by ticket 16 this test asserted the absence of any v2 rulings
    file, which was the checkable form of the register's honesty claim — not
    one paid call made under the instrument being registered. §81's one paid
    run of 2026-08-23 then happened, so the absence claim expired by design;
    what stays checkable is that the register still *says* it was filled
    before the first paid call (the historical claim §81 leans on) and that
    the run wrote exactly the file the register's tuple named.

    (The design-note frontier — now §81 — is pinned once, in
    `tests/test_firstparty_v1_round9_cells.py`, and is not asserted twice.)
    """
    archived = sorted(path.name for path in _ARCHIVES.glob("*.json"))
    assert f"{point_grader.GRADER_VERSION}.json" in archived, (
        "§81's run archives under the tuple §80.4 registered"
    )

    counted = prose()
    assert "before the first paid call" in counted
    assert "not one grader call has been made under this instrument" in counted
