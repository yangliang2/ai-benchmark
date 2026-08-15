"""The third planted defect (#53): one missing early return, authored as two
tasks that share it.

`lostproperty-write-up-what-happened` asks for the fix and `lostproperty-
locate-the-wrong-write-up` asks only for the location, over one hand-authored
starting repository holding one planted defect: `Desk.verdict` throws out a
thing that will not keep and then *falls through* into the branch below,
because the branch that binned it drops its answer instead of returning it. So
the same thing is settled twice — once into the bin, where it belongs, and once
onto the shelf or into the sale room, which is the answer the book is written
up from. Same terrain, same defect, two actions — which is what makes "what
does locating cost, as against fixing?" a reading of the two actions rather
than of two repositories.

This suite is #52's, re-aimed at a defect of a different shape — the guard
suite #53 was to have inherited and did not, recovered here by #59. It checks
the same things no other suite can:

- **The two members really do share one repository**, byte for byte. The
  pairing is a convention rather than a checked relation (design note 36.2):
  the members are deliberately neither a task family nor a pair, so the lint
  compares nothing between them and only a test can.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them (36.1). Here the file the fix touches and the
  file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.** A
  dropped answer is invisible until something that will not keep is put
  through the chain, and nothing visible ever does — through this chain or
  through either of the two beside it, so the defective one is not the odd one
  out. The repository's own suite is green while the defect is in it, and
  stays green on the fix, which is what says the fix breaks nothing.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done.** The defective module defines
  more than the defective class *and more than one class*, so the accepted
  class-level answer says strictly less than the filename it would otherwise
  restate (36.6); the guard chain the defect breaks is written three times
  over elsewhere in the repository *correctly*, so the shape cannot be found by
  pattern alone; and the contract the fall-through breaks is written a file's
  length away from the line that breaks it.
- **This batch's own held-out gate**, which #52's tasks did not carry: the
  fault-location member hashes the repository it handed over and grades a run
  that edited any of it unresolved, so an agent cannot do the fix work and
  charge it to the locating member. Nothing asserted those digests still
  describe the checked-in tree — the grading test's own docstring says the
  task's suite does — and now something does.

Where this terrain falls short of #52's, the shortfall is pinned rather than
asserted away: see `KNOWN_PROMPT_BAIT` and the vocabulary test below, reported
as a finding on #59.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, the empty diff grades unresolved — all through the
same execution-verified pipeline real runs go through.
"""

import ast
import hashlib
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

BUG_FIX = "lostproperty-write-up-what-happened"
FAULT_LOCATION = "lostproperty-locate-the-wrong-write-up"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "sorting.py"
DEFECTIVE_SYMBOL = "Desk.verdict"

ANSWER_PATH = "ANSWER.json"

# The line the defect is on: the answer of the branch that bins a thing, thrown
# away instead of returned.
DEFECTIVE_LINE = "self.thrown_out(handin)"

# The three guard chains this repository writes correctly, in the shape the
# defective one is written in. Named here because the terrain claim is that the
# defective chain is not the odd one out — an agent that finds the shape finds
# four sites and has to read all four.
CORRECT_TWINS = (
    (DEFECTIVE_FILE, "Desk.held_over"),
    ("handins.py", "ticket_for"),
    ("office.py", "wording"),
)

# The three of those four that ask a handin whether it will keep — the chains
# the untested branch is a branch of. `office.wording` is the fourth site of the
# shape but asks about a verdict rather than a handin, so it takes no part in
# the "nothing visible brings one that will not keep" claim.
KEEPS_CHAINS = (
    (DEFECTIVE_FILE, DEFECTIVE_SYMBOL),
    (DEFECTIVE_FILE, "Desk.held_over"),
    ("handins.py", "ticket_for"),
)

# The contract the fall-through breaks, in the repository's own words.
CONTRACT = (
    "a thing nobody has been in for and that will not keep is settled as "
    "BINNED and never as anything else"
)

# The grading test that hashes the handed-over repository, and the file it
# hashes them into. This batch's, and not #52's.
AS_HANDED_OVER_TEST = "test_the_repository_is_as_it_was.py"


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


def function(source: str, symbol: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """The `def` a bare name or a `Class.method` spelling names."""
    enclosing, _, name = symbol.rpartition(".")
    body = ast.parse(source).body
    if enclosing:
        [holder] = [
            node
            for node in body
            if isinstance(node, ast.ClassDef) and node.name == enclosing
        ]
        body = holder.body
    [found] = [
        node
        for node in body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == name
    ]
    return found


def symbol_lines(source: str, symbol: str) -> range:
    """The line numbers a symbol occupies, its `def` line included."""
    found = function(source, symbol)
    assert found.end_lineno is not None
    return range(found.lineno, found.end_lineno + 1)


def functions(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function a module defines, methods spelled `Class.method`."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                    found[f"{node.name}.{member.name}"] = member
    return found


def code_files() -> list[Path]:
    """The repository's modules, its own test suite left out."""
    return [
        path
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("*.py"))
        if not path.name.startswith("test_")
    ]


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


def test_the_fix_is_the_dropped_answer_returned_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the one `return`, so the terrain the fault-location member is
    measured over holds exactly one thing to find."""
    changed = [
        line
        for line in solution_diff(task_by_id(BUG_FIX)).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]

    assert changed == [
        f"-            {DEFECTIVE_LINE}",
        f"+            return {DEFECTIVE_LINE}",
    ]


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


def guarding(file: str, symbol: str, condition: str) -> Callable[[Path], None]:
    """This function with an assertion at the head of it, so that the
    repository's own suite reports what reaches it.

    Placed after the docstring rather than in front of the defective line,
    because the claim being tested is about the arguments the visible suite
    brings to the whole chain and not about one branch of it.
    """

    def edit(workdir: Path) -> None:
        source = workdir / file
        lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
        body = function("".join(lines), symbol).body
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            first = body[1]
        lines.insert(first.lineno - 1, f"{' ' * first.col_offset}assert {condition}\n")
        source.write_text("".join(lines), encoding="utf-8")

    return edit


@pytest.mark.parametrize("file,symbol", KEEPS_CHAINS)
def test_no_visible_test_puts_something_that_will_not_keep_through_a_chain(
    file: str, symbol: str
) -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    A dropped answer is invisible until the branch that drops it is taken, and
    that branch is taken only by a thing that will not keep. Nothing visible
    brings one to the defective chain — which is this defect's version of #52's
    "every visible call stands at the boundary", and is the whole of what keeps
    the repository's own tests from reproducing the symptom.

    Run over the two correct chains that ask the same question as well as the
    defective one, because the terrain claim is the stronger one: the branch is
    untested in *all three*, so an agent cannot find the defect by noticing
    which chain the repository's own suite happens to leave alone. A gap in one
    place is a signpost; the same gap in three is the shape of the suite.

    The vacuous reading is refused first: a tripwire that always fires has to
    turn the suite red, or the function is not reached at all and the claim is
    about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(locate, edit=guarding(file, symbol, "False"))
    assert visible_tests_pass(locate, edit=guarding(file, symbol, "handin.keeps"))


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "lost property office" in prompt
        for giveaway in (
            DEFECTIVE_FILE, "sorting", "Desk", "verdict", "BINNED", "SHELF",
            "outstayed", "held_over", "return",
        ):
            assert giveaway not in prompt, f"{task_id} names {giveaway}"


def test_both_prompts_state_the_intended_behaviour() -> None:
    """Parity of information about what correct *is*, not identical text.

    #51 found the fix member told what correct was while the locate member had
    to infer it, which understates the fix side of the very comparison the two
    members exist to produce. Here the symptom paragraph is one text in both
    and the rule is stated in both: what separates them is the deliverable
    paragraph alone. Saying what correct is leaks no location.
    """
    prompts = [task_by_id(task_id).prompt for task_id in MEMBERS]
    symptom = "Something has gone wrong at the lost property office."

    for prompt in prompts:
        assert "has been thrown away that same night" in prompt, (
            "does not say what correct is"
        )
        assert "however new or old it is" in prompt
        assert prompt.startswith(symptom)
    reported = {"\n\n".join(prompt.split("\n\n")[:2]) for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def test_the_defective_module_holds_more_than_the_defective_class() -> None:
    """`{"file": "sorting.py", "symbol": "Desk"}` is an accepted answer, so it
    has to say strictly less than the filename does.

    36.6 refuses an accepted answer naming a file with no symbol, because on a
    repository this small a bare filename is barely a location. A module whose
    only top-level symbol is the accepted class defeats that by the back door:
    the class level *is* the file level, and an agent that grepped its way into
    the file and named the class without reading the method would resolve. So
    the four verdicts, the keeping reckoning and a second class live beside
    `Desk` at the top level of the same module, and naming the class rules out
    seven siblings.
    """
    top_level = top_level_symbols(repo_source(DEFECTIVE_FILE))

    assert top_level == {
        "KEEPING_DAYS", "RETURNED", "BINNED", "AUCTION", "SHELF",
        "Piles", "outstayed", "Desk",
    }
    assert len(top_level) > 1


def test_an_accepted_class_is_chosen_from_several_and_not_the_only_one() -> None:
    """The same back door, one gap narrower — and the gap the top-level count
    above does not close.

    An agent electing to answer at class level answers with the class, and if
    the module defines exactly one, that answer is determined by the filename
    alone: one grep to the file, the only class there, resolved, with the
    defective method never read. So wherever the key accepts a class, that
    class is one of at least two the file defines — `Piles`, which is what an
    evening's sorting comes to, is as plausible a home for a thing landing in
    the wrong pile as `Desk` is, and telling them apart takes reading both.
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
    assert classes(repo_source(DEFECTIVE_FILE)) == {"Piles", "Desk"}


# The words a prompt cannot be blamed for sharing with the repository: the
# closed-class words English sentences are built out of, and the domain nouns a
# prompt about a lost property office and a repository about a lost property
# office have no way not to both use. Everything else either prompt says is
# distinctive — and distinctive vocabulary is grep bait.
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
    "office lost property handin handins thing things day days owner shelf "
    "book desk counter".split()
)
UNREVEALING = FUNCTION_WORDS | DOMAIN_NOUNS

# **A finding, reported on #59 rather than asserted away.** #52's terrain holds
# that no distinctive prompt term selects the defective module alone: the ferry
# repository states its contract in deliberately different words from the
# prompt's, so reading the prompt is not one grep away from the defective file.
# This repository does not hold to that. `sorting.py`'s module docstring
# paraphrases the prompt's contract close to word for word — "here longer than
# the office keeps things", "what will not keep is thrown out" — and those
# phrases appear in no other module, so a solver grepping the prompt lands in
# the defective file.
#
# What it does *not* do is name the defective symbol: every one of these terms
# lands in the module docstring or in a sibling method, so the symbol-level
# assertion below — the half that decides a fault-location verdict, since a
# bare filename is not an accepted answer — passes outright. The bait is pinned
# to its exact current set instead: this cannot get worse without turning red,
# and the terrain cost is written down where the next author reads it.
KNOWN_PROMPT_BAIT = frozenset({
    "answers", "anything", "end", "end of", "everything", "here longer",
    "is thrown", "keeps things", "left", "longer", "longer than", "new",
    "not keep", "office keeps", "say", "say where", "something", "the end",
    "went", "whoever",
})


def prompt_terms() -> set[str]:
    """The distinctive vocabulary of the two prompts.

    Every content word, and every adjacent pair of words at least one of which
    is a content word — a pair as well as a word because "not keep" and "here
    longer" narrow as hard as any single word does and neither half of either
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

    A test file counts as part of the module it tests, because `test_sorting.py`
    points at `sorting.py` as surely as `sorting.py` does. `README.md` counts as
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


def test_no_distinctive_prompt_word_narrows_to_the_defective_symbol() -> None:
    """The prompts must not be greppable into the answer.

    Two ways a term can narrow: selecting the defective module and no other,
    and — inside that module — selecting the defective symbol and nothing else.
    The second is refused outright. The first is pinned to the set it is
    already at, and reported as a finding: see `KNOWN_PROMPT_BAIT` above.

    Matched on word boundaries rather than as substrings, which is where this
    departs from #52's version of the same test: under substring matching the
    prompt's "night" reads as narrowing to `Desk.verdict` because the method's
    docstring says "tonight", which is an artifact of the matcher and not a
    path any solver could walk.
    """
    lines = repo_lines()
    defect = symbol_lines(repo_source(DEFECTIVE_FILE), DEFECTIVE_SYMBOL)

    to_the_module: dict[str, list[str]] = {}
    to_the_symbol: dict[str, list[str]] = {}
    for term in sorted(prompt_terms()):
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        found = [line for line in lines if pattern.search(line[3])]
        if not found:
            continue
        where = [f"{file}:{number}" for _, file, number, _ in found]
        if {module for module, *_ in found} == {DEFECTIVE_FILE.removesuffix(".py")}:
            to_the_module[term] = where
        in_module = [line for line in found if line[1] == DEFECTIVE_FILE]
        if in_module and all(number in defect for *_, number, _ in in_module):
            to_the_symbol[term] = where

    assert to_the_symbol == {}, (
        f"prompt words selecting {DEFECTIVE_SYMBOL} alone: {to_the_symbol}"
    )
    assert set(to_the_module) == KNOWN_PROMPT_BAIT, (
        "the prompt vocabulary reaching only the defective module has moved: "
        f"{sorted(set(to_the_module) ^ KNOWN_PROMPT_BAIT)}"
    )


def falls_through() -> set[tuple[str, str]]:
    """Every guard branch in the repository whose body does not answer.

    A guard chain is a run of `if`s with no `else`, each deciding the whole
    question and returning; the defect is one such branch that decides and then
    lets the chain carry on. Read structurally rather than by name, so the
    inventory cannot drift from the code.
    """
    dropped = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            for statement in node.body:
                if isinstance(statement, ast.If) and not statement.orelse:
                    if not isinstance(statement.body[-1], ast.Return):
                        dropped.add((path.name, name))
    return dropped


def guard_chains() -> set[tuple[str, str]]:
    """Every function written as a guard chain of at least two branches."""
    chains = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            guards = [
                statement
                for statement in node.body
                if isinstance(statement, ast.If) and not statement.orelse
            ]
            if len(guards) > 1:
                chains.add((path.name, name))
    return chains


def test_the_defect_is_not_the_only_guard_chain_of_its_shape() -> None:
    """A single guard chain in the whole repository makes locating a grep.

    The same chain, over the same two conditions in the same order, is written
    three times over and every one of them is right: `Desk.held_over` beside the
    defect in the same class, `handins.ticket_for` and `office.wording`
    elsewhere. So the shape names four sites across three files, and which of
    them is wrong is decided by whether the branch answers rather than by the
    pattern.

    The other half of the same claim, and the one that says the defect is
    really there: exactly one branch in the whole repository decides and does
    not answer, and it is the planted one.
    """
    chains = guard_chains()

    assert chains == {(DEFECTIVE_FILE, DEFECTIVE_SYMBOL), *CORRECT_TWINS}
    assert len({file for file, _ in chains}) == 3
    assert falls_through() == {(DEFECTIVE_FILE, DEFECTIVE_SYMBOL)}


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Whether the binning branch answers is the whole of the inference, so a
    docstring saying "and never as anything else" three lines above the branch
    that lets it be something else removes the last step of the work. It is
    stated once, in the module docstring at the top of the file, and the defect
    is at the bottom: a reader has to carry it there. The defective method's
    own docstring says which four verdicts it stands between, which is honest
    about what the method is for and silent about whether every branch answers.

    What is *not* forbidden nearby is the word `BINNED` itself: `thrown_out`
    returns it seven lines up, which is the verdict the dropped answer came
    from and not a statement of the rule that it is the last word.
    """
    source = repo_source(DEFECTIVE_FILE)
    lines = source.splitlines()
    defect = next(
        at for at, line in enumerate(lines) if line.strip() == DEFECTIVE_LINE
    )
    docstring = " ".join((ast.get_docstring(ast.parse(source)) or "").split())

    assert " ".join(CONTRACT.split()) in docstring
    assert not any(
        word in line
        for line in lines[max(0, defect - 12):defect]
        for word in (
            "never as anything else", "thrown out that evening", "new in or long in",
        )
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


def test_binning_without_binning_it_is_not_the_fix() -> None:
    """The careless fix: answer `BINNED` from the branch instead of returning
    what the bin answered, and the thing is written up correctly while never
    reaching the bin beside the desk. The prompt says what is thrown away by
    the end of the night does not change, and the held-out tests say so."""
    fix = task_by_id(BUG_FIX)

    def careless(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        source.write_text(
            source.read_text().replace(
                f"return {DEFECTIVE_LINE}", "return BINNED"
            )
        )

    diff = solution_diff(fix, mutate=careless)

    [record] = evaluate([fix], [run_for(fix, diff)], source="run-log")
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Desk.verdict", "Desk", "verdict"])
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
        "Desk.held_over", "held_over", "Desk.thrown_out", "thrown_out",
        "Desk.evening", "evening", "outstayed", "KEEPING_DAYS",
        "RETURNED", "BINNED", "AUCTION", "SHELF",
        "Piles", "Piles.everything", "everything",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Desk.held_over` is the correct twin of the very chain
    that is wrong, `thrown_out` is what the dropped answer came from and the
    most plausible wrong answer in the file, `evening` is where the wrong
    verdict is filed into a pile, `outstayed` and `KEEPING_DAYS` are the
    reckoning the fall-through lands in, the four constants are the verdicts
    themselves, and `Piles` — the second class, the one that makes naming
    `Desk` a choice — is what an evening comes to, at both its spellings and
    bare. All of them are correct, so an answer naming one has read the right
    file and not found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    `office.py` is the module the symptom points at first: the book the prompt
    quotes is written up there, and every word it quotes — "on the shelf",
    "sent to the sale room" — actually lives in `wording`. `handins.py` is the
    other chain that asks whether a thing will keep, and answers with the wrong
    thing if it is read too fast. Every one of them is run through the real
    pipeline by the lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {"office.py", "handins.py"}
    assert ("handins.py", "ticket_for") in {
        (answer.file, answer.symbol) for answer in key.rejected
    }
    assert ("office.py", "Office.written_up") in {
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


# --- this batch's own gate: locating is not fixing -----------------------------


def as_handed_over() -> dict[str, str]:
    """The digests the fault-location member's second held-out test compares
    the workdir against, read out of that test rather than restated here."""
    source = (task_by_id(FAULT_LOCATION).grading_dir / AS_HANDED_OVER_TEST).read_text(
        encoding="utf-8"
    )
    [assignment] = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "AS_HANDED_OVER"
            for target in node.targets
        )
    ]
    digests = ast.literal_eval(assignment.value)
    assert isinstance(digests, dict)
    return digests


def test_the_hashed_repository_is_the_repository_that_is_checked_in() -> None:
    """The claim that grading test's own docstring makes about this suite.

    It hashes the starting repository so that a fault-location run which edited
    the code grades unresolved. Digests are generated rather than typed, and
    nothing re-derives them: a later edit to `repo/` would leave the task
    lint-clean and the reference solution resolving, while grading *every* real
    run unresolved — the same silent failure the loader's stdlib-name rule
    exists to prevent. So the table is checked against the tree here, both ways
    round: every file it names is what it says it is, and no file of the
    starting repository is missing from it.
    """
    repo = task_by_id(FAULT_LOCATION).repo_dir
    digests = as_handed_over()

    assert set(digests) == {path.name for path in repo.iterdir() if path.is_file()}
    assert digests == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(repo.iterdir())
        if path.is_file()
    }


def test_a_correct_answer_that_also_repaired_the_code_is_unresolved() -> None:
    """What the second held-out test is for, and what nothing else can show.

    The two members exist to produce one number — what locating costs, as
    against fixing — so a run that does the fix work and then writes a correct
    answer would resolve at fix-member cost with nothing in the log to say it
    happened. The prompt forbids it and this makes the prompt binding: the same
    answer that resolves on its own grades unresolved once the repair rides
    along with it.
    """
    locate = task_by_id(FAULT_LOCATION)
    accepted = naming(DEFECTIVE_FILE, DEFECTIVE_SYMBOL)

    def answered_and_repaired(workdir: Path) -> None:
        answers(accepted)(workdir)
        source = workdir / DEFECTIVE_FILE
        source.write_text(
            source.read_text().replace(
                f"            {DEFECTIVE_LINE}", f"            return {DEFECTIVE_LINE}"
            )
        )

    assert verdict(locate, answers(accepted)) == 1.0
    assert verdict(locate, answered_and_repaired) == 0.0


def test_reading_the_repository_leaves_it_as_it_was_found() -> None:
    """What the gate does *not* forbid, which is as much of it as what it does:
    a scratch file or a note left behind by an agent that read the code is not
    a repair, and only the files handed over are compared. A gate that failed
    on those would grade an honest run unresolved for having taken notes."""
    locate = task_by_id(FAULT_LOCATION)
    accepted = naming(DEFECTIVE_FILE, DEFECTIVE_SYMBOL)

    def answered_with_notes(workdir: Path) -> None:
        answers(accepted)(workdir)
        (workdir / "notes.md").write_text("verdict falls through to the shelf\n")

    assert verdict(locate, answered_with_notes) == 1.0
