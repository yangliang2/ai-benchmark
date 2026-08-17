"""The fifth planted defect (#55): one swallowed exception, authored as two
tasks that share it.

`allotments-go-back-for-what-nobody-could-read` asks for the fix and
`allotments-locate-the-swallowed-reading` asks only for the location, over one
hand-authored starting repository holding one planted defect: `Quarter.used_on`
wraps the one call that turns what is written on a card into a figure in
`try: ... except Unreadable: return NOTHING_USED`. `cards.figure` raises
exactly as it is meant to when the ink has run; the handler throws that away
and hands the caller nought instead. A failure comes back as a success, and as
a reading indistinguishable from a standpipe read and found not to have moved,
so the handler in `Society.read` that exists to put such a plot on the list to
go back to never sees an exception and never fires. Same terrain, same defect,
two actions — which is what makes "what does locating cost, as against
fixing?" a reading of the two actions rather than of two repositories.

This suite is #52's, re-aimed at a defect of a different shape and following
#54's, which #59 recovered. It checks the same things no other suite can:

- **The two members really do share one repository**, byte for byte. The
  pairing is a convention rather than a checked relation (design note 36.2):
  the members are deliberately neither a task family nor a pair, so the lint
  compares nothing between them and only a test can.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them (36.1). Here the file the fix touches and the
  file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.** The
  visible suite exercises a card nobody can make out at the level *below* the
  swallow — `cards.figure` raises and `cards.written_up` writes the card up as
  unread — and never puts one into a `Quarter`, so the shape is legitimised
  without the symptom ever being reproduced. Proved here by making the handler
  refuse outright and watching the suite stay green, and the vacuous reading
  refused first by making the guarded call fail and watching it go red.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done.** The defective module defines
  more than the defective class *and more than one class*, so the accepted
  class-level answer says strictly less than the filename it would otherwise
  restate (36.6); a caught exception is a shape a grep finds in one pass, so
  the repository holds five more handlers across all four modules and every
  one is correct; and the contract the defect breaks is written a file's
  length away from the line that breaks it.
- **What no pattern can tell apart**, which is this defect's whole
  discrimination: `cards.written_up` catches the same exception in the same
  shape and is correct, because what it falls back to says the card was not
  read rather than that the plot used nothing. Asserted by running both on one
  unreadable card.
- **This batch's own held-out gate**, carried over from #53: the
  fault-location member hashes the repository it handed over and grades a run
  that edited any of it unresolved, so an agent cannot do the fix work and
  charge it to the locating member. Nothing asserts those digests still
  describe the checked-in tree but this suite.

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

BUG_FIX = "allotments-go-back-for-what-nobody-could-read"
FAULT_LOCATION = "allotments-locate-the-swallowed-reading"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "ledger.py"
DEFECTIVE_SYMBOL = "Quarter.used_on"

ANSWER_PATH = "ANSWER.json"

# The two lines the defect is: the handler that catches what `cards.figure`
# raised, and the figure it hands back in its place.
DEFECTIVE_HANDLER = "        except Unreadable:\n            return NOTHING_USED\n"

# The call the handler guards — where the failure is raised that it throws away.
GUARDED_CALL = "            return figure(self.card_for(plot).written)\n"

# Every exception handler in the repository, as (file, symbol, exception) —
# read and never added to. Named here because the terrain claim is that a grep
# for the shape finds six sites and has to read all six.
HANDLERS = {
    ("plots.py", "number_of", "ValueError"),
    ("cards.py", "written_up", "Unreadable"),
    (DEFECTIVE_FILE, DEFECTIVE_SYMBOL, "Unreadable"),
    (DEFECTIVE_FILE, "Quarter.read_before", "KeyError"),
    ("society.py", "Society.note_on", "KeyError"),
    ("society.py", "Society.read", "Unreadable"),
}

# The ones that neither re-raise nor write the failure down anywhere: the
# handler catches, falls back to a value and says nothing. Four of the six, so
# "catches and returns a constant" names four sites and decides nothing.
SILENT = {
    ("cards.py", "written_up", "Unreadable"),
    (DEFECTIVE_FILE, DEFECTIVE_SYMBOL, "Unreadable"),
    (DEFECTIVE_FILE, "Quarter.read_before", "KeyError"),
    ("society.py", "Society.note_on", "KeyError"),
}

# The contract the defect breaks, in the repository's own words — deliberately
# not the prompt's, so that reading the prompt is not one grep away from the
# defective file. See `KNOWN_PROMPT_BAIT` below, which is empty because of this.
CONTRACT = (
    "These books carry only what was read. Where the writing on a card defeats "
    "the society altogether, that plot has no total for the run and none is "
    "invented for it: the books would sooner run a plot light than stand "
    "behind a total nobody wrote down."
)

# A card the rain got to: what `cards.figure` refuses and the defect turns into
# a reading of nought.
UNREADABLE = "   "


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


def test_the_fix_is_the_swallow_removed_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the handler taken off the guarded call — and the import that
    handler was the only user of — so the terrain the fault-location member is
    measured over holds exactly one thing to find."""
    changed = [
        line
        for line in solution_diff(task_by_id(BUG_FIX)).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]

    assert changed == [
        "-from cards import Unreadable, figure",
        "+from cards import figure",
        "-        try:",
        f"-{GUARDED_CALL.rstrip()}",
        *[f"-{line}" for line in DEFECTIVE_HANDLER.splitlines()],
        "+        return figure(self.card_for(plot).written)",
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


def swapping(what: str, into: str) -> Callable[[Path], None]:
    """One exact substitution in the defective module."""

    def edit(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        text = source.read_text(encoding="utf-8")
        changed = text.replace(what, into)
        assert changed != text, f"{what!r} is no longer in {DEFECTIVE_FILE}"
        source.write_text(changed, encoding="utf-8")

    return edit


def test_no_visible_test_puts_a_card_nobody_can_read_through_the_swallow() -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    A swallowed exception is invisible to every test that never makes the
    guarded call fail, and the repository is written so that nothing visible
    ever puts a card nobody can make out into a `Quarter`. It exercises such a
    card one level down instead — `cards.figure` raises on it and
    `cards.written_up` writes it up as unread — which legitimises the shape in
    the repository's own voice without reproducing the symptom. That is this
    defect's version of #52's "every visible fixture stands at the boundary",
    and it is a property of the fixtures rather than of the code, which would
    be silently lost the first time a visible test handed a smudged card to the
    society.

    Asserted by making the handler refuse outright: if the suite stays green
    with the swallow turned into an error, nothing visible reaches it.

    The vacuous reading is refused first: with the guarded call made to fail
    every time, the suite has to go red, or nothing visible calls the defective
    method at all and the refusal above is about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(
        locate,
        edit=swapping(GUARDED_CALL, '            raise Unreadable("every card")\n'),
    )
    assert visible_tests_pass(
        locate,
        edit=swapping(
            DEFECTIVE_HANDLER,
            '        except Unreadable:\n'
            '            raise AssertionError("the swallow was reached") from None\n',
        ),
    )


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "allotments" in prompt
        for giveaway in (
            DEFECTIVE_FILE, "ledger", "Quarter", "quarter", "used_on", "Reading",
            "Unreadable", "NOTHING_USED", "except", "exception", "raise",
            "caught", "swallow",
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
    symptom = "Something has gone wrong at the allotments."

    for prompt in prompts:
        flowed = " ".join(prompt.split())
        assert "has no figure for that plot at all" in flowed, "no rule stated"
        assert "nothing whatever is put in its place" in flowed
        assert prompt.startswith(symptom)
    reported = {"\n\n".join(prompt.split("\n\n")[:2]) for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def test_the_defective_module_holds_more_than_the_defective_class() -> None:
    """`{"file": "ledger.py", "symbol": "Quarter"}` is an accepted answer, so it
    has to say strictly less than the filename does.

    36.6 refuses an accepted answer naming a file with no symbol, because on a
    repository this small a bare filename is barely a location. A module whose
    only top-level symbol is the accepted class defeats that by the back door:
    the class level *is* the file level, and an agent that grepped its way into
    the file and named the class without reading the method would resolve. So
    what one plot's standpipe comes to, which plot got through the most, what a
    plot that has not moved reads and what the books have for a plot they never
    had live beside `Quarter` at the top level of the same module, and naming
    the class rules out four siblings.
    """
    top_level = top_level_symbols(repo_source(DEFECTIVE_FILE))

    assert top_level == {
        "NOTHING_USED", "NOT_READ_BEFORE", "Reading", "most_used", "Quarter",
    }
    assert len(top_level) > 1


def test_an_accepted_class_is_chosen_from_several_and_not_the_only_one() -> None:
    """The same back door, one gap narrower — and the gap the top-level count
    above does not close.

    An agent electing to answer at class level answers with the class, and if
    the module defines exactly one, that answer is determined by the filename
    alone: one grep to the file, the only class there, resolved, with the
    defective method never read. So wherever the key accepts a class, that
    class is one of at least two the file defines — `Reading`, one plot's
    standpipe once its card has been made out, is as plausible a home for a
    plot showing nothing as `Quarter` is, and telling them apart takes reading
    both.
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
    assert classes(repo_source(DEFECTIVE_FILE)) == {"Reading", "Quarter"}


# The words a prompt cannot be blamed for sharing with the repository: the
# closed-class words English sentences are built out of, and the domain nouns a
# prompt about an allotment site and a repository about an allotment site have
# no way not to both use. Everything else either prompt says is distinctive —
# and distinctive vocabulary is grep bait.
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
    "allotment allotments plot plots card cards standpipe standpipes society "
    "site sheet reader read book books figure".split()
)
UNREVEALING = FUNCTION_WORDS | DOMAIN_NOUNS

# Nothing, so far — see #54's version of this test, where the same terrain
# claim held everywhere but three collisions that were pinned rather than
# asserted away. The prompt here states the contract in the society's words
# ("no figure for that plot at all", "put in its place") and the defective
# module states it in the books' ("nothing stands in these books that was not
# read"), so reading the prompt is not one grep away from the defective file.
KNOWN_PROMPT_BAIT: frozenset[str] = frozenset()


def prompt_terms() -> set[str]:
    """The distinctive vocabulary of the two prompts.

    Every content word, and every adjacent pair of words at least one of which
    is a content word — a pair as well as a word because "make out" and "go
    back" narrow as hard as any single word does and neither half of either
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

    A test file counts as part of the module it tests, because `test_ledger.py`
    points at `ledger.py` as surely as `ledger.py` does. `README.md` counts as
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
    Both are refused outright here, which is where this stands where #54's
    stood at a pinned set of three: see `KNOWN_PROMPT_BAIT` above.

    Matched on word boundaries rather than as substrings, for #54's reason:
    substring matching reads a term as narrowing to a symbol whose docstring
    merely contains it inside a longer word, which is an artifact of the
    matcher and not a path any solver could walk.
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


def handlers() -> set[tuple[str, str, str]]:
    """Every (file, symbol, exception) the repository catches."""
    found = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            for handler in ast.walk(node):
                if isinstance(handler, ast.ExceptHandler):
                    caught = handler.type
                    assert isinstance(caught, ast.Name), (
                        f"{path.name}:{name} catches something unnamed"
                    )
                    found.add((path.name, name, caught.id))
    return found


def silent_handlers() -> set[tuple[str, str, str]]:
    """The handlers that neither re-raise nor write the failure down: they
    catch, fall back to a value and say nothing about what happened."""
    silent = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            for handler in ast.walk(node):
                if not isinstance(handler, ast.ExceptHandler):
                    continue
                assert isinstance(handler.type, ast.Name)
                said = any(
                    isinstance(statement, ast.Raise)
                    or isinstance(statement, ast.Assign | ast.AugAssign)
                    or (
                        isinstance(statement, ast.Call)
                        and isinstance(statement.func, ast.Attribute)
                    )
                    for body in handler.body
                    for statement in ast.walk(body)
                )
                if not said:
                    silent.add((path.name, name, handler.type.id))
    return silent


def test_the_defect_is_not_the_only_caught_exception_in_the_repository() -> None:
    """A single `except` in the whole repository makes locating a grep.

    It is a shape a grep finds in one pass, so the repository writes five more
    handlers, across all four modules, and every one of them is correct:
    `plots.number_of` re-raises what it caught as the site's own `NotAPlot`,
    `Society.read` writes down the plot it could not read, and
    `cards.written_up`, `Quarter.read_before` and `Society.note_on` fall back
    to a value that says outright there was nothing to be had. Three of the six
    catch `Unreadable` itself, and the defective module holds a correct handler
    of its own, so reaching the right file finishes nothing.

    The other half of the same claim: four of the six catch and fall back
    silently, so the shape a reader would filter on — a handler that says
    nothing — still names four sites, and which of them is wrong is decided by
    what the fallback *means* rather than by the pattern.
    """
    found = handlers()

    assert found == HANDLERS
    assert len({file for file, *_ in found}) == 4
    assert len([caught for *_, caught in found if caught == "Unreadable"]) == 3
    assert silent_handlers() == SILENT
    assert (DEFECTIVE_FILE, DEFECTIVE_SYMBOL, "Unreadable") in SILENT


def test_the_repository_declares_the_shape_it_uses_correctly() -> None:
    """Why the five correct ones are not merely five more places to look.

    Three of them are asserted by the repository's own tests, so the shape is
    *legitimised* rather than left ambiguous: an agent reading the visible
    suite is told, in the repository's own voice, that catching here is how the
    site says there was nothing to be had. And the visible suite says outright
    what a card nobody could make out is worth — `cards.figure` refuses it and
    `cards.written_up` writes it up as unread — so the concept is present
    everywhere except where it is thrown away.
    """
    suite = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("test_*.py"))
    )

    for declared in (
        "def test_what_nobody_can_make_out_is_not_a_plot_number",
        "def test_a_card_nobody_can_make_out_is_not_a_figure",
        "def test_a_card_nobody_could_make_out_is_written_up_as_unread",
        "def test_a_plot_the_books_have_nothing_for_stood_at_nothing_they_know_of",
        "def test_a_plot_with_nothing_written_against_it_has_nothing_written",
    ):
        assert declared in suite, f"the visible suite no longer says {declared}"


def test_the_nearest_twin_is_the_same_shape_written_correctly() -> None:
    """This defect's whole discrimination, run rather than described.

    `cards.written_up` and `Quarter.used_on` catch the same exception, raised
    by the same call, in the same `except Unreadable: return <constant>` shape.
    One is correct and one is the defect, and what separates them is only what
    the constant *means*: `written_up` falls back to a value saying the card
    was not read, and `used_on` falls back to a figure, which is a reading like
    any other. Nothing a grep or a linter sees tells them apart — so this is
    asserted by running both over one card the rain got to.
    """
    import shutil
    import subprocess
    import sys
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ai-bench-twin-") as name:
        # A throwaway copy, because importing writes bytecode and the
        # checked-in `repo/` trees of swept tasks are immutable.
        workdir = Path(name)
        shutil.copytree(
            task_by_id(FAULT_LOCATION).repo_dir, workdir, dirs_exist_ok=True
        )
        asked = subprocess.run(
            [
                sys.executable,
                "-c",
                "from cards import Card, written_up\n"
                "from ledger import Quarter\n"
                f"card = Card(7, {UNREADABLE!r})\n"
                "print(written_up(card))\n"
                "print(Quarter([card]).used_on(7))\n",
            ],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()

    assert asked == ["plot", "7:", "not", "read", "0"]


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Whether a card nobody could make out may come back as a figure is the whole
    of the inference, so a docstring saying so three lines above the handler
    that does it removes the last step of the work. It is stated once, in the
    module docstring at the top of the file, and the defect is well down it: a
    reader has to carry it there. The defective method's own docstring says
    what the method is for and is silent about what happens when the card
    cannot be made out.
    """
    source = repo_source(DEFECTIVE_FILE)
    lines = source.splitlines()
    defect = next(
        at for at, line in enumerate(lines) if line.strip() == "except Unreadable:"
    )
    docstring = " ".join((ast.get_docstring(ast.parse(source)) or "").split())

    assert " ".join(CONTRACT.split()) in docstring
    assert not any(
        word in line
        for line in lines[max(0, defect - 12):defect]
        for word in (
            "only what was read", "no total for the run", "invented for it",
            "a plot light",
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


def test_a_fix_that_only_stops_reporting_nought_is_not_the_fix() -> None:
    """The near-miss this defect invites, graded rather than assumed.

    The symptom is a plot on the sheet at nothing, so the shortest thing that
    looks like a cure is to leave the plot off the sheet and stop there — the
    figure is no longer wrong, and the list to go back to is still empty, so
    nobody ever goes back for a fresh card. The prompt says outright that the
    plot goes on that list, and the held-out tests grade the half-cure
    unresolved.
    """
    fix = task_by_id(BUG_FIX)

    def half_cured(workdir: Path) -> None:
        source = workdir / "society.py"
        text = source.read_text()
        changed = text.replace(
            "                going_back.append(plot)\n", "                pass\n"
        )
        assert changed != text, "Society.read moved"
        source.write_text(changed)

    diff = solution_diff(fix, mutate=half_cured)

    [record] = evaluate([fix], [run_for(fix, diff)], source="run-log")
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Quarter.used_on", "Quarter", "used_on"])
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
        "Quarter.read_before", "read_before", "Quarter.card_for", "card_for",
        "Quarter.carded", "Reading", "Reading.since", "since", "most_used",
        "NOTHING_USED", "NOT_READ_BEFORE",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Quarter.read_before` carries the module's other
    handler and is correct, `Quarter.card_for` is what the swallowed call reads
    its card from, `Quarter.carded` decides which plots are asked about at all,
    `Reading` — the second class, the one that makes naming `Quarter` a choice
    — is one plot's standpipe once its card has been made out, `Reading.since`
    is the other place a figure of nought is arrived at deliberately,
    `most_used` reads a run whole, and the two constants are what the module
    puts where there is nothing. All of them are correct, so an answer naming
    one has read the right file and not found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    `society.py` is the module the symptom points at first: the sheet the
    prompt quotes and the list to go back to are both made up there, and
    `Society.read` even catches `Unreadable` and would put the plot on the list
    — correct code that can never fire, because the exception is thrown away a
    layer below it. `cards.py` is where a card becomes a figure at all, and
    where the exception the defect discards is raised. Every one of them is run
    through the real pipeline by the lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {"society.py", "cards.py"}
    named = {(answer.file, answer.symbol) for answer in key.rejected}
    assert ("society.py", "Society.read") in named
    assert ("cards.py", "figure") in named
    assert ("cards.py", "written_up") in named


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
        swapping(DEFECTIVE_HANDLER, "")(workdir)

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
        (workdir / "notes.md").write_text("the failure never reaches the caller\n")

    assert verdict(locate, answered_with_notes) == 1.0
