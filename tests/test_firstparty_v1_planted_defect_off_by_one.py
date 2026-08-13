"""The first planted defect (#51): one off-by-one at a boundary, authored as
two tasks that share it.

`noticeboard-show-every-notice` asks for the fix and `noticeboard-locate-the-
lost-notice` asks only for the location, over one hand-authored starting
repository holding one planted defect: `Paginator.page_count` floors instead of
rounding up, so a partial last page is not a page at all and the notices on it
are unreachable. Same terrain, same defect, two actions — which is what makes
"what does locating cost, as against fixing?" a reading of the two actions
rather than of two repositories.

Four things this suite checks that no other one can:

- **The two members really do share one repository**, byte for byte. The
  pairing is a convention rather than a checked relation (design note 36.2):
  the members are deliberately neither a task family nor a pair, so the lint
  compares nothing between them and only a test can.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them: a key naming a perfectly correct method
  passes every gate the corpus has (36.1). Here the file the fix touches and
  the file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.** A
  visible failing test would hand over the answer and delete the action being
  measured, so the repository's own suite is green on the pristine tree — and
  stays green on the fix, which is what says the fix breaks nothing.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and the other arithmetic
  in the defective file does not.
- **The terrain leaves the locating to be done.** Four properties the lint
  cannot see and #52–#56 copy the shape of: the defective module defines more
  than the defective class *and more than one class*, so the accepted
  class-level answer says strictly less than the filename it would otherwise
  restate and is a choice rather than a restatement (36.6); the defect's
  arithmetic shape appears elsewhere in the repository *correctly*, so it
  cannot be found by pattern alone; the contract the defect breaks is written
  a file's length away from the line that breaks it rather than three lines
  above it; and no distinctive word of either prompt narrows to the defective
  module, so the prompts cannot be grepped into an answer.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, the empty diff grades unresolved — all through the
same execution-verified pipeline real runs go through.
"""

import ast
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from firstparty_v1_tasks import (
    run_for,
    solution_diff,
    solved_tree,
    task_by_id,
    visible_tests_pass,
    workdir_diff,
)

from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    Task,
    _tree_bytes,
    answer_key,
    evaluate,
    is_control,
    lint_task_set,
)

BUG_FIX = "noticeboard-show-every-notice"
FAULT_LOCATION = "noticeboard-locate-the-lost-notice"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "paging.py"
DEFECTIVE_SYMBOL = "Paginator.page_count"

ANSWER_PATH = "ANSWER.json"

# The line the defect is on, and the same arithmetic where it is right.
DEFECTIVE_LINE = "return len(self.items) // self.per_page"
CORRECT_TWIN = ("noticeboard.py", "return len(self.posted) // self.per_board")

# The contract the defect breaks, in the repository's own words — which are
# deliberately not the prompts' words. See the vocabulary test below.
CONTRACT = "the final one takes\nthe remainder"


def repo_source(file: str) -> str:
    return (task_by_id(FAULT_LOCATION).repo_dir / file).read_text(encoding="utf-8")


def top_level_symbols(source: str) -> set[str]:
    """What a module defines at its top level — the level a filename names."""
    defined = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defined.add(node.name)
        elif isinstance(node, ast.Assign):
            defined.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
    return defined


def classes(source: str) -> set[str]:
    """The classes a module defines at its top level — the level an accepted
    answer naming a class is answering at."""
    return {
        node.name for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
    }


def symbol_lines(source: str, symbol: str) -> range:
    """The line numbers `Class.method` occupies, its `def` line included."""
    enclosing, _, name = symbol.rpartition(".")
    [holder] = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == enclosing
    ]
    [method] = [
        node
        for node in holder.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == name
    ]
    assert method.end_lineno is not None
    return range(method.lineno, method.end_lineno + 1)


def answers(payload: str, *, at: str = ANSWER_PATH) -> Callable[[Path], None]:
    """The edit a run that wrote this answer file would log."""

    def write(workdir: Path) -> None:
        target = workdir / at
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload)

    return write


def naming(file: str, symbol: str) -> str:
    return json.dumps({"file": file, "symbol": symbol}, indent=2) + "\n"


def verdict(task: Task, edit: Callable[[Path], None]) -> float:
    """What the pipeline a real run replays through makes of this run."""
    return evaluate(
        [task], [run_for(task, workdir_diff(task, edit))], source="run-log"
    )[0].quality_value


# --- one repository, one defect, two actions -----------------------------------


def test_the_two_members_share_one_starting_repository() -> None:
    """Byte for byte, and checked here because nothing else checks it: the two
    are deliberately neither a task family nor a pair — those constructs
    require one varied knob and an agreed category, and these vary no knob and
    differ in category — so the family lint's peer-to-peer tree comparison
    never runs over them."""
    fix, locate = task_by_id(BUG_FIX), task_by_id(FAULT_LOCATION)

    assert _tree_bytes(fix.repo_dir) == _tree_bytes(locate.repo_dir)


def test_the_defect_the_fix_removes_is_the_defect_the_key_names() -> None:
    """The join the corpus cannot make on its own.

    A fault-location task's grading proves only that its grading test tells an
    accepted answer from a wrong one; what proves there is a defect to find at
    all is the paired bug-fix member's held-out tests failing on the shared
    pristine repository (36.2). That pairing is a convention, so the two halves
    are tied together here: every file the accepted answers name is the one
    file the reference fix touches.
    """
    fix = task_by_id(BUG_FIX)
    key = answer_key(task_by_id(FAULT_LOCATION))

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(fix).splitlines()
        if line.startswith("diff --git ")
    }

    assert touched == {DEFECTIVE_FILE}
    assert {answer.file for answer in key.accepted} == {DEFECTIVE_FILE}


def test_neither_member_claims_anything_about_difficulty() -> None:
    """Both are coverage tasks: authored to fill a category, betting nothing.
    Outside the frozen 22 that has to be said outright, and saying it is also
    what keeps them out of every knob reading — a task declaring no
    construction can join no family, no pair and no effort claim, so neither
    can advance a knob's counter or move a published multiplier."""
    for task_id in MEMBERS:
        task = task_by_id(task_id)

        assert task.control
        assert is_control(task)
        assert task.construction is None


def test_each_member_is_declared_as_designed() -> None:
    fix, locate = task_by_id(BUG_FIX), task_by_id(FAULT_LOCATION)

    assert (fix.category, fix.scale, fix.language) == (
        "bug-fix", "single-file", "python",
    )
    assert (locate.category, locate.scale, locate.language) == (
        "fault-location", "single-file", "python",
    )


# --- the symptom is visible and its cause is not -------------------------------


def test_the_repository_reproduces_the_symptom_in_no_visible_test() -> None:
    """The convention this batch holds to: a failing test in the starting
    repository would point straight at the defect and delete the action both
    members measure. So the repository's own suite is green while the defect
    is in it — the symptom reaches the agent through the prompt alone."""
    for task_id in MEMBERS:
        assert visible_tests_pass(task_by_id(task_id))


def test_the_visible_suite_stays_green_on_the_fix() -> None:
    """The other direction: the fix is a fix and not a rewrite — everything
    the repository already asserted about itself still holds."""
    fix = task_by_id(BUG_FIX)

    assert visible_tests_pass(fix, edit=solved_tree(fix))


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "notices" in prompt
        for giveaway in (DEFECTIVE_FILE, "Paginator", "page_count"):
            assert giveaway not in prompt, f"{task_id} names {giveaway}"


def test_both_prompts_state_the_intended_behaviour() -> None:
    """Parity of information about what correct *is*, not identical text.

    The fix member was told the boards fill up and the last one carries the
    remainder; the locate member had to infer it. That asymmetry ran in the
    direction this round can least afford — it makes fixing cheaper relative to
    locating, understating the fix side of the very comparison the two members
    exist to produce. Saying what correct is leaks no location.
    """
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "left over" in prompt, f"{task_id} does not say what correct is"
        assert "every" in prompt


# --- the terrain leaves the locating to be done --------------------------------


def test_the_defective_module_holds_more_than_the_defective_class() -> None:
    """`{"file": "paging.py", "symbol": "Paginator"}` is an accepted answer, so
    it has to say strictly less than the filename does.

    36.6 refuses an accepted answer naming a file with no symbol, because on a
    repository this small a bare filename is barely a location. A module whose
    only top-level symbol is the accepted class defeats that by the back door:
    the class level *is* the file level, and an agent that grepped its way into
    the file and named the class without reading the method would resolve. So
    the page arithmetic lives beside `Paginator` at the top level of the same
    module, and naming the class rules out four siblings.
    """
    top_level = top_level_symbols(repo_source(DEFECTIVE_FILE))

    assert top_level == {"FIRST_PAGE", "page_of", "bounds", "PageSpan", "Paginator"}
    assert len(top_level) > 1


def test_an_accepted_class_is_chosen_from_several_and_not_the_only_one() -> None:
    """The same back door, one gap narrower — and the gap the top-level count
    above does not close.

    Counting *symbols* is satisfied by a module holding one class beside some
    functions, which is what `paging.py` was. But an agent electing to answer
    at class level answers with the class, and if the module defines exactly
    one, that answer is determined by the filename alone: one grep to the file,
    the only class there, resolved, with the defective method never read. So
    wherever the key accepts a class, that class is one of at least two the
    file defines — `PageSpan`, which cuts the stretch a page covers, is as
    plausible a home for notices going missing as `Paginator` is, and telling
    them apart takes reading the arithmetic in both.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    named_at_class_level = [
        answer for answer in key.accepted
        if answer.symbol in classes(repo_source(answer.file))
    ]

    assert named_at_class_level, "the key is expected to accept the enclosing class"
    for answer in named_at_class_level:
        defined = classes(repo_source(answer.file))
        assert len(defined) > 1, f"{answer.file} defines only {answer.symbol}"
    assert classes(repo_source(DEFECTIVE_FILE)) == {"PageSpan", "Paginator"}


# The words a prompt cannot be blamed for sharing with the repository: the
# closed-class words English sentences are built out of, and the domain nouns
# a prompt about a noticeboard and a repository about a noticeboard have no
# way not to both use. Everything else either prompt says is distinctive — and
# distinctive vocabulary is grep bait.
FUNCTION_WORDS = frozenset("""
    a about after all also an and any are as at be been being both but by can
    could did do does each either few for from get given goes had has have he
    her his how i if in into is it its just like made make many may me might
    more most much must my no nor not now of off on once one only or other our
    out over own per same she should since so some such than that the their
    them then there these they this those through to too under until up us
    very was we well were what when where whether which while who whom why
    will with within would you your s t
""".split())
DOMAIN_NOUNS = frozenset(
    "notice notices noticeboard board boards page pages".split()
)
UNREVEALING = FUNCTION_WORDS | DOMAIN_NOUNS


def prompt_terms() -> set[str]:
    """The distinctive vocabulary of the two prompts.

    Every content word, and every adjacent pair of words at least one of which
    is a content word — a pair as well as a word because "at most" and "left
    over" narrow as hard as any single word does and neither half of either
    narrows on its own.
    """
    terms: set[str] = set()
    for task_id in MEMBERS:
        words = re.findall(r"[a-z]+", task_by_id(task_id).prompt.lower())
        terms |= {word for word in words if word not in UNREVEALING}
        terms |= {
            f"{first} {second}"
            for first, second in zip(words, words[1:], strict=False)
            if not (first in UNREVEALING and second in UNREVEALING)
        }
    return terms


def repo_lines() -> list[tuple[str, str, int, str]]:
    """Every line of the repository's code, as (module, file, number, text).

    A test file counts as part of the module it tests, because `test_paging.py`
    points at `paging.py` as surely as `paging.py` does. `README.md` counts as
    no module at all: it is the index that names every module, so a word found
    only there has selected the whole repository rather than one file — which
    is why the README cannot rescue a word that otherwise narrows.
    """
    lines = []
    for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("*.py")):
        module = path.stem.removeprefix("test_")
        for number, text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            lines.append((module, path.name, number, text.lower()))
    return lines


def test_no_distinctive_prompt_word_narrows_to_the_defective_code() -> None:
    """The prompts must not be greppable into the answer.

    The `//` decoy makes the defect's *arithmetic* name two sites, and this is
    the other half of the same job: the repository's own prose must not name
    one. It is written by paraphrasing the contract the prompt states, so the
    two say the same thing, and left alone they say it in the same words —
    which is a one-step path from reading the prompt to the defective symbol,
    reopened by four English words after the decoy closed it. The repository
    documents the contract honestly and in different words, and the same
    distinctive word appears in more than one module wherever it appears at
    all.

    Two ways a word can narrow, and both are refused: selecting the defective
    module and no other, and — inside that module — selecting the defective
    symbol and nothing else. Reintroduce "fill" to `page_count`'s docstring and
    this fails on both counts.
    """
    lines = repo_lines()
    defect = symbol_lines(repo_source(DEFECTIVE_FILE), DEFECTIVE_SYMBOL)

    to_the_module: dict[str, list[str]] = {}
    to_the_symbol: dict[str, list[str]] = {}
    for term in sorted(prompt_terms()):
        found = [line for line in lines if term in line[3]]
        if not found:
            continue
        where = [f"{file}:{number}" for _, file, number, _ in found]
        if {module for module, *_ in found} == {DEFECTIVE_FILE.removesuffix(".py")}:
            to_the_module[term] = where
        in_module = [line for line in found if line[1] == DEFECTIVE_FILE]
        if in_module and all(number in defect for *_, number, _ in in_module):
            to_the_symbol[term] = where

    assert to_the_module == {}, (
        f"prompt words selecting {DEFECTIVE_FILE} alone: {to_the_module}"
    )
    assert to_the_symbol == {}, (
        f"prompt words selecting {DEFECTIVE_SYMBOL} alone: {to_the_symbol}"
    )


def test_the_defect_is_not_the_only_arithmetic_of_its_shape() -> None:
    """A single floor division in the whole repository makes locating a grep.

    The one in `Noticeboard.full_boards` is the same expression written the
    same way — `len(...) // ...` over the same two quantities — and it is
    right, because how many boards are *full* is exactly the question floor
    division answers. So the shape names two sites, and which of them is wrong
    is decided by the question each is asked rather than by the pattern.
    """
    sites = {
        path.name: [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if "//" in line
        ]
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("*.py"))
        if not path.name.startswith("test_")
    }

    assert sum(len(lines) for lines in sites.values()) >= 3
    assert len([name for name, lines in sites.items() if lines]) >= 2
    assert DEFECTIVE_LINE in sites[DEFECTIVE_FILE]
    twin_file, twin_line = CORRECT_TWIN
    assert twin_line in sites[twin_file]


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    What a partial last page is owed is the whole of the inference, so a
    docstring stating it three lines above the line that breaks it removes the
    last step of the work. It is stated once, in the module docstring at the
    top of the file, and the defect is at the bottom: a reader has to carry it
    there. The defective method's own docstring says how many pages there are,
    which is honest about what the method is for and silent about the boundary.

    It is stated in the repository's words rather than the prompt's — see the
    vocabulary test above, which is why the phrase this looks for is
    "the final one takes the remainder" and not the prompts' "left over".
    """
    source = repo_source(DEFECTIVE_FILE)
    lines = source.splitlines()
    defect = next(at for at, line in enumerate(lines) if DEFECTIVE_LINE in line.strip())
    docstring = " ".join((ast.get_docstring(ast.parse(source)) or "").split())

    assert " ".join(CONTRACT.split()) in docstring
    assert not any(
        word in line
        for line in lines[max(0, defect - 12):defect]
        for word in ("remainder", "packed solid", "left over")
    )
    assert defect > 30


# --- the gates every checked-in task passes ------------------------------------


@pytest.mark.parametrize("task_id", MEMBERS)
def test_task_lints_clean(task_id: str) -> None:
    assert lint_task_set([task_by_id(task_id)]) == []


@pytest.mark.parametrize("task_id", MEMBERS)
def test_reference_solution_resolves_and_doing_nothing_does_not(
    task_id: str,
) -> None:
    task = task_by_id(task_id)
    runs = [
        run_for(task, solution_diff(task), model="reference"),
        run_for(task, "", model="empty"),
    ]

    records = evaluate([task], runs, source="run-log")

    graded = {record.model: record.quality_value for record in records}
    assert graded == {"reference": 1.0, "empty": 0.0}


@pytest.mark.parametrize("task_id", MEMBERS)
def test_declared_scale_matches_the_reference_solution(task_id: str) -> None:
    """Single-file both ways, and for different reasons: the fix is one edit to
    one module, and the located fault is one answer file written into the
    workdir."""
    task = task_by_id(task_id)

    touched = {
        line.split(" b/")[-1]
        for line in solution_diff(task).splitlines()
        if line.startswith("diff --git ")
    }

    assert len(touched) == 1


# --- what each member's grading makes of a near-miss ---------------------------


def test_a_count_that_is_right_about_the_partial_page_and_wrong_about_none(
) -> None:
    """The careless fix: `len(items) // per_page + 1` reaches the notices on
    the partial last page and invents a page for an empty board and for a
    board that divides exactly. The held-out tests say so."""
    fix = task_by_id(BUG_FIX)

    def careless(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        source.write_text(
            source.read_text().replace(
                "return -(-len(self.items) // self.per_page)",
                "return len(self.items) // self.per_page + 1",
            )
        )

    diff = solution_diff(fix, mutate=careless)

    [record] = evaluate([fix], [run_for(fix, diff)], source="run-log")
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Paginator.page_count", "Paginator", "page_count"])
def test_every_description_level_the_author_wrote_down_resolves(
    symbol: str,
) -> None:
    """The defective method and the class enclosing it are both legitimately
    correct descriptions of this defect, so both are in the key — and the bare
    method name, which is how an agent phrases an answer about something
    nested, answers the qualified one it is spelled from."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 1.0


@pytest.mark.parametrize(
    "symbol",
    [
        "Paginator.page", "page_of", "bounds", "FIRST_PAGE",
        "PageSpan", "PageSpan.cut", "cut",
    ],
)
def test_the_other_arithmetic_in_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Paginator.page` slices the page the count decides on,
    `page_of` and `bounds` are the page arithmetic it is cut with, `FIRST_PAGE`
    is where the numbering starts, and `PageSpan` — the second class, the one
    that makes naming `Paginator` a choice — is what a page is cut with, at
    both its spellings and bare. All of them are correct, so an answer naming
    one has read the right file and not found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    The prompt's own "the oldest notice is on neither of them" makes the order
    the notices are read in the first suspect, so `notices.py`/`newest_first`
    is written down. `noticeboard.py` is the module that looks responsible
    twice over: it is where the wrong count is displayed, and where the
    defect's own arithmetic appears again and is right. Every one of them is
    run through the real pipeline by the lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {"noticeboard.py", "notices.py"}
    assert ("notices.py", "newest_first") in {
        (answer.file, answer.symbol) for answer in key.rejected
    }


def test_the_answer_key_ships_held_out_and_the_repository_carries_no_answer(
) -> None:
    """Held out of the workdir: the key travels with the grading directory the
    overlay copies at grade time, and the pristine repository the agent is
    given carries neither it nor an answer file."""
    locate = task_by_id(FAULT_LOCATION)

    assert (locate.grading_dir / ANSWER_KEY_FILE).is_file()
    assert not (locate.repo_dir / ANSWER_KEY_FILE).exists()
    assert not (locate.repo_dir / ANSWER_PATH).exists()
