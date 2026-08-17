"""The second planted defect (#52): one comparison used the wrong way round in
a branch, authored as two tasks that share it.

`ferry-cast-off-when-it-should` asks for the fix and `ferry-locate-the-idle-
boat` asks only for the location, over one hand-authored starting repository
holding one planted defect: `Line.call` asks whether the waiting line is *at
most* a load deep where it should ask whether it is *at least* that, so the
threshold rule admits exactly the lines it should hold and holds exactly the
ones it should serve. Nine on the jetty and a boat that seats four never casts
off; two, and nobody at all, are taken across. Same terrain, same defect, two
actions — which is what makes "what does locating cost, as against fixing?" a
reading of the two actions rather than of two repositories.

This suite is #51's, re-aimed at a defect of a different shape, and it checks
the same things no other suite can:

- **The two members really do share one repository**, byte for byte. The
  pairing is a convention rather than a checked relation (design note 36.2):
  the members are deliberately neither a task family nor a pair, so the lint
  compares nothing between them and only a test can.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them (36.1). Here the file the fix touches and the
  file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.** The
  boundary a reversed comparison hides at is the one length where "at most"
  and "at least" agree: every visible fixture that reaches the call stands
  exactly a load deep, so the repository's own suite is green on the pristine
  tree — and stays green on the fix, which is what says the fix breaks
  nothing.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done**, the half of it #51 fixed and
  this ticket copies that the task-set lint cannot see: the defect's
  comparison appears elsewhere in the repository *correctly*, spelled the same
  way over the same two quantities, so it cannot be found by pattern alone;
  and the contract the defect breaks is written a file's length away from the
  line that breaks it. The class-level answer and the prompt's vocabulary are
  the task-set lint's terrain rules now (#65).

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, the empty diff grades unresolved — all through the
same execution-verified pipeline real runs go through.
"""

import ast
import json
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

BUG_FIX = "ferry-cast-off-when-it-should"
FAULT_LOCATION = "ferry-locate-the-idle-boat"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "loading.py"
DEFECTIVE_SYMBOL = "Line.call"

ANSWER_PATH = "ANSWER.json"

# The line the defect is on, and the same comparison where it is right.
DEFECTIVE_LINE = "if len(self.waiting) <= self.size:"
CORRECT_TWIN = ("ferry.py", "return len(self.waiting) <= self.seats")

# The contract the defect breaks, in the repository's own words — which are
# deliberately not the prompts' words. See the vocabulary test below.
CONTRACT = "a line as long as one load takes, or longer, is served"


def repo_source(file: str) -> str:
    return (task_by_id(FAULT_LOCATION).repo_dir / file).read_text(encoding="utf-8")


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


def test_the_fix_is_the_comparison_turned_round_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the one operator, so the terrain the fault-location member is
    measured over holds exactly one thing to find."""
    changed = [
        line
        for line in solution_diff(task_by_id(BUG_FIX)).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]

    assert changed == [
        f"-        {DEFECTIVE_LINE}",
        "+        if len(self.waiting) >= self.size:",
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


def guarding(condition: str) -> Callable[[Path], None]:
    """The defective branch with an assertion in front of it, so that the
    repository's own suite reports what reaches it."""

    def edit(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        text = source.read_text(encoding="utf-8")
        guarded = text.replace(
            f"        {DEFECTIVE_LINE}",
            f"        assert {condition}\n        {DEFECTIVE_LINE}",
        )
        assert guarded != text, "the defective line moved"
        source.write_text(guarded, encoding="utf-8")

    return edit


def test_every_visible_call_of_the_defective_branch_stands_at_the_boundary(
) -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    A comparison turned round agrees with the one it should be at exactly one
    length: a line standing a whole load deep is served either way. That is
    this defect's version of #51's "every fixture divides exactly", and it is
    the whole of what keeps the repository's own tests from reproducing the
    symptom — a property of the fixtures rather than of the code, which would
    be silently lost the first time a case was added to them.

    Asserted by running the visible suite against a tripwire in front of the
    defective branch. The vacuous reading is refused first: a tripwire that
    always fires has to turn the suite red, or the branch is not reached at all
    and the boundary claim is about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(locate, edit=guarding("False"))
    assert visible_tests_pass(
        locate, edit=guarding("len(self.waiting) == self.size")
    )


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "jetty" in prompt
        for giveaway in (DEFECTIVE_FILE, "loading", "Line", "SERVE", "HOLD"):
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
    symptom = "Something has gone wrong"

    for prompt in prompts:
        assert "fill every seat" in prompt, "does not say what correct is"
        assert "fewer than that" in prompt
        assert prompt.startswith(symptom)
    reported = {prompt.split("\n\n")[0] for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def test_the_defect_is_not_the_only_comparison_of_its_shape() -> None:
    """A single threshold comparison in the whole repository makes locating a
    grep.

    The one in `Ferry.one_crossing` is the same comparison written the same
    way — `len(...) <= ...` over a count of the same people and a boatful — and
    it is right, because whether one crossing would clear the jetty is exactly
    the question "at most" answers. `Ferry.crowded` and
    `passengers.waited_at_least` put the operator the fix needs in two further
    places, both correct. So the shape names four sites across three files, and
    which of them is wrong is decided by the question each is asked rather than
    by the pattern.
    """
    sites = {
        path.name: [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if "<=" in line or ">=" in line
        ]
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("*.py"))
        if not path.name.startswith("test_")
    }

    assert sum(len(lines) for lines in sites.values()) >= 4
    assert len([name for name, lines in sites.items() if lines]) >= 2
    assert sites[DEFECTIVE_FILE] == [DEFECTIVE_LINE]
    twin_file, twin_line = CORRECT_TWIN
    assert twin_line in sites[twin_file]
    assert any(">=" in line for lines in sites.values() for line in lines)


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Which way round the threshold is read is the whole of the inference, so a
    docstring stating it three lines above the line that breaks it removes the
    last step of the work. It is stated once, in the module docstring at the
    top of the file, and the defect is at the bottom: a reader has to carry it
    there. The defective method's own docstring says which two verdicts it
    stands between, which is honest about what the method is for and silent
    about which way the comparison runs.

    It is stated in the repository's words rather than the prompt's — see the
    vocabulary test above, which is why the phrase this looks for is "as long
    as one load takes, or longer" and not the prompts' "fill every seat".
    """
    source = repo_source(DEFECTIVE_FILE)
    lines = source.splitlines()
    defect = next(at for at, line in enumerate(lines) if DEFECTIVE_LINE in line.strip())
    docstring = " ".join((ast.get_docstring(ast.parse(source)) or "").split())

    assert " ".join(CONTRACT.split()) in docstring
    assert not any(
        word in line
        for line in lines[max(0, defect - 12):defect]
        for word in ("at least", "as long as", "or longer", "deep")
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


def test_a_comparison_turned_round_but_left_strict_is_not_the_fix() -> None:
    """The careless fix: `>` reaches the crowd left on the jetty and holds the
    boat for a jetty holding exactly a boatful, which is the one length the
    repository's own tests do cover. The held-out tests say so."""
    fix = task_by_id(BUG_FIX)

    def careless(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        source.write_text(
            source.read_text().replace(
                "if len(self.waiting) >= self.size:",
                "if len(self.waiting) > self.size:",
            )
        )

    diff = solution_diff(fix, mutate=careless)

    [record] = evaluate([fix], [run_for(fix, diff)], source="run-log")
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Line.call", "Line", "call"])
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
        "Line.load", "load", "short_by", "EMPTY",
        "SERVE", "HOLD", "Load", "Load.whole_line", "whole_line",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Line.load` makes up the load the call decides on,
    `short_by` and `EMPTY` are the shortfall reckoning a held line is reported
    by, `SERVE` and `HOLD` are the two verdicts the defective branch chooses
    between, and `Load` — the second class, the one that makes naming `Line` a
    choice — is what a turn of the line comes to, at both its spellings and
    bare. All of them are correct, so an answer naming one has read the right
    file and not found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    `ferry.py` is the module that looks responsible twice over: it is where the
    verdict is asked for and printed, and where the defect's own comparison
    appears again and is right. The prompt's own "the order people are taken
    in" makes the ordering the other suspect, so `passengers.py`/`in_turn` is
    written down. Every one of them is run through the real pipeline by the
    lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {"ferry.py", "passengers.py"}
    assert ("passengers.py", "in_turn") in {
        (answer.file, answer.symbol) for answer in key.rejected
    }
    assert ("ferry.py", "Ferry.one_crossing") in {
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
