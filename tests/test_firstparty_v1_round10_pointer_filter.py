"""The two pointer-prose filters, pinned by example on the real corpus.

§82.2 ruled the definition and §82.5 ruled the second operationalisation of it,
and both are semantic claims about agent-written prose: a deliverable that
merely points at the artifact carrying the answer is not an answer. A definition
like that cannot be checked against a fixture — a fixture is a sentence someone
wrote to make the filter say what they already decided it should say. So the
pins below are **the archived messages four real cells actually logged**, which
is the only evidence that says whether the mechanics chosen for "file-shaped
token" and "names a symbol defined in the tree" read the corpus the way the
rulings meant.

The four rows are §82.5's own border cases, and they come in two pairs.

- **Two agreeing-row true pointers** — `apiary-review-the-book-and-the-crop` ×
  codex and `paperround-locate-the-carried-over-count` × sonnet. Both messages
  say only that the answer file was written. §81.1's inspection never saw them
  because it read the disagreeing rows and these two agree; the filter is
  verdict-blind and finds them anyway, which is the filter doing the one thing
  an inspection cannot.
- **Two symbol-only narrations** — `belfry-review-the-peals-and-the-board` ×
  haiku and `parishhall-review-the-hire-and-the-diary` × haiku. Both narrate
  their findings by symbol (`Book.rung_by`, `Diary.cancel`) and name no file.
  They are what **splits the two operationalisations**: file-reference calls
  them pointer prose, file-or-symbol does not, and §82.5 refused to pick between
  the two readings with the outcomes in view.

**§82.5's preview counts are anchors, not registrations.** That section reported
the file-reference filter catching 17 of the 63 stratum-A rows and the
symbol-aware one 15. What this file pins is what the *implemented* filters say;
the counts are asserted because they are re-derivable from the corpus, not
because the preview reported them, and a divergence would have been a finding in
the ticket's closing note rather than a reason to move a definition. (There was
none: both filters land on the preview's numbers and on its four border rows.)

Nothing here calls a grader, reads the rulings archive for a verdict or spends a
dollar. The filters take a deliverable and a task, so there is no verdict in
reach of them to read — which is the verdict-blindness claim made structural,
and is tested at the fixture seams in `test_grader_calibration_v1.py`.

The stratum-A row set is read off the **committed rulings archive** under the
live `GRADER_VERSION` rather than re-derived by replay: replaying 306 diffs to
learn which rows the archive registered would cost minutes to answer a question
the archive answers by being read. §80.5's freezing rule applies here as
everywhere — when the instrument next moves, this suite freezes to the version
tuple these counts were taken under.
"""

from pathlib import Path

import pytest

from ai_benchmark import grader_calibration_v1, point_grader, reconcile_v1
from ai_benchmark.firstparty_v1 import Run, Task, load_runs, load_task_set
from ai_benchmark.grader_calibration_v1 import (
    FILE_OR_SYMBOL,
    FILE_REFERENCE,
    is_pointer_prose_by_file_or_symbol,
    is_pointer_prose_by_file_reference,
)

_REPO = Path(__file__).parent.parent
_TASKS = _REPO / "tasks" / "first-party-v1"
_LOGS = _REPO / "data" / "first-party-v1-runs"

# The two counts §82.5's preview reported, held here as what the implemented
# filters are checked to say over the archive's stratum A. Not a tuning target:
# the ticket's rule was to report a divergence rather than move a definition
# toward these, and there was none to report.
_FILE_REFERENCE_CATCHES = 17
_FILE_OR_SYMBOL_CATCHES = 15

# §82.5's four border rows, task x agent x model.
_APIARY_CODEX = (
    "apiary-review-the-book-and-the-crop", "codex", "gpt-5.6-terra",
)
_PAPERROUND_SONNET = (
    "paperround-locate-the-carried-over-count", "claude-code", "claude-sonnet-5",
)
_BELFRY_HAIKU = (
    "belfry-review-the-peals-and-the-board", "claude-code", "claude-haiku-4-5",
)
_PARISHHALL_HAIKU = (
    "parishhall-review-the-hire-and-the-diary", "claude-code", "claude-haiku-4-5",
)

_TRUE_POINTERS = (_APIARY_CODEX, _PAPERROUND_SONNET)
_SYMBOL_ONLY = (_BELFRY_HAIKU, _PARISHHALL_HAIKU)

Cell = tuple[str, str, str]


@pytest.fixture(scope="module")
def tasks() -> dict[str, Task]:
    return {task.id: task for task in load_task_set(_TASKS)}


@pytest.fixture(scope="module")
def rows() -> dict[Cell, Run]:
    """Every archived run row, keyed on what it carries.

    Logs are collected wholesale and never selected by filename — the sweep
    protocol's rule, after the round-1 analysis silently dropped two paid cells
    by filtering on a name.
    """
    collected: dict[Cell, Run] = {}
    for log in reconcile_v1.collect_logs([_LOGS]):
        for run in load_runs(log):
            cell = (run.task_id, run.agent, run.model)
            assert cell not in collected, f"{cell}: two rows of one cell"
            collected[cell] = run
    return collected


@pytest.fixture(scope="module")
def registered_stratum_a() -> list[Cell]:
    """The stratum-A rows the committed archive holds rulings for — the row set
    both readings are taken over."""
    archive = grader_calibration_v1.read_rulings(
        grader_calibration_v1.rulings_file(
            grader_calibration_v1.DEFAULT_RULINGS_DIR, point_grader.GRADER_VERSION
        )
    )
    assert archive is not None, "the committed rulings archive is missing"
    return [
        (one.task_id, one.agent, one.model)
        for one in archive.answers
        if one.stratum == "A"
    ]


def caught_by(
    operationalisation: grader_calibration_v1.Operationalisation,
    cells: list[Cell],
    tasks: dict[str, Task],
    rows: dict[Cell, Run],
) -> set[Cell]:
    return {
        cell
        for cell in cells
        if operationalisation.catches(rows[cell].output, tasks[cell[0]])
    }


# --- the two agreeing-row true pointers -----------------------------------------


@pytest.mark.parametrize("cell", _TRUE_POINTERS, ids=lambda cell: cell[0])
def test_a_true_pointer_is_caught_by_both_operationalisations(
    cell: Cell, tasks: dict[str, Task], rows: dict[Cell, Run]
) -> None:
    """The rows §81.1's verdict-aware inspection could not see.

    Both messages say the answer file was written and nothing else — `apiary` ×
    codex names it twice, once as a markdown link to a temporary workdir path,
    and `paperround` × sonnet names it once in backticks. Both rows *agree* with
    their machine verdict, which is why an inspection that read the seventeen
    disagreements never reached them, and both are pointer prose under either
    operationalisation: after the answer file's own mentions are removed there is
    no file of the tree left named, and no symbol of it either.
    """
    task, run = tasks[cell[0]], rows[cell]

    assert is_pointer_prose_by_file_reference(run.output, task)
    assert is_pointer_prose_by_file_or_symbol(run.output, task)


def test_the_answer_files_own_path_does_not_rescue_a_pointer(
    tasks: dict[str, Task], rows: dict[Cell, Run]
) -> None:
    """§82.2's removal clause, pinned on the message that needs it.

    `apiary` × codex spells its pointer as a markdown link whose target is an
    absolute path through a temporary workdir. The whole reference goes — "the
    bare name and any path ending in it" — rather than only the visible name, so
    the directories the pointer pointed along cannot come back as tokens that
    rescue it.
    """
    task, run = tasks[_APIARY_CODEX[0]], rows[_APIARY_CODEX]

    assert "workdir/FINDINGS.json" in run.output
    assert grader_calibration_v1.answer_file(task) == "FINDINGS.json"
    remaining = grader_calibration_v1._remaining_tokens(run.output, task)
    assert not any("FINDINGS.json" in token for token in remaining)
    assert "workdir" not in remaining


# --- the two symbol-only narrations, which split the two readings ---------------


@pytest.mark.parametrize("cell", _SYMBOL_ONLY, ids=lambda cell: cell[0])
def test_a_symbol_only_narration_splits_the_two_operationalisations(
    cell: Cell, tasks: dict[str, Task], rows: dict[Cell, Run]
) -> None:
    """§82.5's divergence between the ruled definition and the ruled meaning.

    Both messages report their findings at symbol level and name no file at all,
    so the file-reference operationalisation — §82.2's own words — calls them
    pointer prose, while the term's semantic ("naming no location *and no
    finding*") plainly does not. The symbol-aware operationalisation is that
    semantic made checkable, and it leaves both rows inside A″.
    """
    task, run = tasks[cell[0]], rows[cell]

    assert is_pointer_prose_by_file_reference(run.output, task)
    assert not is_pointer_prose_by_file_or_symbol(run.output, task)


def test_a_dotted_symbol_resolves_against_the_repository_tree(
    tasks: dict[str, Task], rows: dict[Cell, Run]
) -> None:
    """The mechanics the split turns on: `Book.rung_by` and `Diary.cancel` are
    what keep their rows out of the symbol-aware filter's catch, and they resolve
    whole rather than by their last dotted part — the language runner reports both
    the qualified and the bare spelling, so membership is the only rule needed.
    """
    belfry = grader_calibration_v1._repository_symbols(tasks[_BELFRY_HAIKU[0]])
    parishhall = grader_calibration_v1._repository_symbols(tasks[_PARISHHALL_HAIKU[0]])

    assert "Book.rung_by" in belfry and "rung_by" in belfry
    assert "Diary.cancel" in parishhall and "cancel" in parishhall
    assert "Book.rung_by" in rows[_BELFRY_HAIKU].output
    assert "Diary.cancel" in rows[_PARISHHALL_HAIKU].output
    # And neither message names a file of its own tree, which is why the
    # file-reference reading caught them in the first place.
    for cell in _SYMBOL_ONLY:
        names = grader_calibration_v1._repository_file_names(tasks[cell[0]])
        remaining = grader_calibration_v1._remaining_tokens(
            rows[cell].output, tasks[cell[0]]
        )
        assert not any(token in names for token in remaining)


# --- what the two filters say over the whole registered stratum A ---------------


def test_both_filters_catch_what_the_preview_anchored_them_at(
    registered_stratum_a: list[Cell],
    tasks: dict[str, Task],
    rows: dict[Cell, Run],
) -> None:
    """The two counts, re-derived from the corpus rather than quoted.

    63 stratum-A rows, 17 caught by file-reference and 15 by file-or-symbol —
    §82.5's preview numbers, reproduced by the implemented filters. The
    symbol-aware catch is a strict subset of the other by construction (it is
    file-reference plus one more clause), and the two rows in the difference are
    exactly the symbol-only narrations above.
    """
    assert len(registered_stratum_a) == 63
    by_file = caught_by(FILE_REFERENCE, registered_stratum_a, tasks, rows)
    by_symbol = caught_by(FILE_OR_SYMBOL, registered_stratum_a, tasks, rows)

    assert len(by_file) == _FILE_REFERENCE_CATCHES
    assert len(by_symbol) == _FILE_OR_SYMBOL_CATCHES
    assert by_symbol < by_file
    assert by_file - by_symbol == set(_SYMBOL_ONLY)
    assert set(_TRUE_POINTERS) <= by_symbol


def test_the_symbol_side_reads_each_language_through_its_own_runner(
    registered_stratum_a: list[Cell], tasks: dict[str, Task]
) -> None:
    """The clause that keeps the symbol side honest across the corpus's two
    languages.

    Five of the keyed tasks are TypeScript, and a symbol rule written as a Python
    pattern would read them as defining nothing — every TypeScript row would then
    be pointer prose the moment it narrated by symbol, silently and only because
    of the language it was written in. The extractor is the task's own language
    runner, so both languages report symbols and neither is read by an instrument
    that cannot see it.
    """
    keyed = {tasks[cell[0]] for cell in registered_stratum_a}
    typescript = [task for task in keyed if task.language == "typescript"]

    assert len(typescript) == 5
    for task in sorted(keyed, key=lambda one: one.id):
        assert grader_calibration_v1._repository_symbols(task), task.id
