"""The fourth planted defect (#54): one mutable default argument, authored as
two tasks that share it.

`paperround-count-each-walk-on-its-own` asks for the fix and `paperround-
locate-the-carried-over-count` asks only for the location, over one
hand-authored starting repository holding one planted defect: `Slate.bundles`
takes the list it counts a walk's bundles onto as `so_far=[]`, so every ask
that passes no list of its own counts onto the one list the `def` line built,
once, at import. The first ask is right, the second comes back with the first's
bundles in front of its own, and by Saturday most of what the shop says to make
up is other days. Same terrain, same defect, two actions — which is what makes
"what does locating cost, as against fixing?" a reading of the two actions
rather than of two repositories.

This suite is #52's, re-aimed at a defect of a different shape — the guard
suite #54 was to have inherited and did not, recovered here by #59. It checks
the same things no other suite can:

- **The two members really do share one repository**, byte for byte. The
  pairing is a convention rather than a checked relation (design note 36.2):
  the members are deliberately neither a task family nor a pair, so the lint
  compares nothing between them and only a test can.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them (36.1). Here the file the fix touches and the
  file every accepted answer names are asserted to be one file.
- **The repository reproduces the symptom nowhere the agent can see it.**
  Carried-over state is invisible to a test that asks whether what it expected
  is *in* what came back, and every visible test that lets the count default
  asks exactly that; the two callers that read a count whole pass a list of
  their own, which is the parameter used as it was meant to be. So the
  repository's own suite is green while the defect is in it — proved here by
  seeding the shared default with a bundle nobody asked for and watching the
  suite stay green — and stays green on the fix, which is what says the fix
  breaks nothing.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done**, the half of it the task-set
  lint cannot see: a mutable default is a shape a grep finds in one pass, so
  the repository holds six more of them and every one is correct; and the
  contract the defect breaks is written a file's length away from the line
  that breaks it. The class-level answer and the prompt's vocabulary are the
  task-set lint's terrain rules now (#65).
- **This batch's own held-out gate**, which #52's tasks did not carry: the
  fault-location member hashes the repository it handed over and grades a run
  that edited any of it unresolved, so an agent cannot do the fix work and
  charge it to the locating member. Nothing asserted those digests still
  describe the checked-in tree — the grading test's own docstring says the
  task's suite does — and now something does.

Where this terrain falls short of #52's, the shortfall is a declared
`terrain_waiver` on `paperround-locate-the-carried-over-count` rather than
asserted away, reported as a finding on #59.

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

BUG_FIX = "paperround-count-each-walk-on-its-own"
FAULT_LOCATION = "paperround-locate-the-carried-over-count"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "tallying.py"
DEFECTIVE_SYMBOL = "Slate.bundles"
DEFECTIVE_PARAMETER = "so_far"

ANSWER_PATH = "ANSWER.json"

# The line the defect is on: the `def` whose default is built once, at import.
DEFECTIVE_LINE = f"def bundles(self, round_, {DEFECTIVE_PARAMETER}=[]):"

# The same shape, everywhere it is written correctly — read and never added to.
# Named here because the terrain claim is that a grep for the shape finds seven
# sites and has to read all seven.
CORRECT_TWINS = (
    ("houses.py", "in_order", "streets"),
    ("newsagent.py", "counter_line", "notes"),
    ("newsagent.py", "Newsagent.bundle_list", "notes"),
    ("newsagent.py", "Newsagent.how_many", "apart_from"),
    ("rounds.py", "Round.drops", "skipping"),
    (DEFECTIVE_FILE, "added_up", "apart_from"),
)

# The contract the defect breaks, in the repository's own words.
CONTRACT = (
    "Every ask is worked out on a clean slate: what was counted up for the ask "
    "before belongs to that ask, and none of it is still lying there to come "
    "back with the next one."
)

# What a call that pollutes the shared default leaves behind: a bundle for a
# street nobody on this round takes papers in.
POLLUTION = 'Bundle("brick hill", 99)'


def repo_source(file: str) -> str:
    return (task_by_id(FAULT_LOCATION).repo_dir / file).read_text(encoding="utf-8")


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


def test_the_fix_is_the_default_moved_inside_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the sentinel and the two lines that build the list per call, so
    the terrain the fault-location member is measured over holds exactly one
    thing to find."""
    changed = [
        line
        for line in solution_diff(task_by_id(BUG_FIX)).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]

    assert changed == [
        f"-    {DEFECTIVE_LINE}",
        f"+    def bundles(self, round_, {DEFECTIVE_PARAMETER}=None):",
        f"+        if {DEFECTIVE_PARAMETER} is None:",
        f"+            {DEFECTIVE_PARAMETER} = []",
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


def defaulting(to: str, *, refusing: bool = False) -> Callable[[Path], None]:
    """`Slate.bundles` with a different default, and optionally an assertion at
    the head of its body refusing the defaulted call outright.

    The edit is made through the signature rather than the body because that is
    where this defect lives: what the tripwire has to reach is the one list the
    `def` line built.
    """

    def edit(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        text = source.read_text(encoding="utf-8")
        signature = DEFECTIVE_LINE.replace(
            f"{DEFECTIVE_PARAMETER}=[]", f"{DEFECTIVE_PARAMETER}={to}"
        )
        changed = text.replace(DEFECTIVE_LINE, signature)
        assert changed != text, "the defective signature moved"
        if refusing:
            lines = changed.splitlines(keepends=True)
            body = function(changed, DEFECTIVE_SYMBOL).body
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                first = body[1]
            lines.insert(
                first.lineno - 1,
                f"{' ' * first.col_offset}assert {DEFECTIVE_PARAMETER} is not None\n",
            )
            changed = "".join(lines)
        source.write_text(changed, encoding="utf-8")

    return edit


def test_no_visible_test_reads_a_defaulted_count_whole() -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    Carried-over state is invisible to a test that asks whether what it
    expected is *in* what came back, and that is what every visible test which
    lets the count default asks. That is this defect's version of #52's "every
    visible fixture stands at the boundary", and it is the whole of what keeps
    the repository's own tests from reproducing the symptom — a property of the
    assertions rather than of the code, which would be silently lost the first
    time one of them was tightened to an equality.

    Asserted by seeding the shared default with a bundle for a street nobody
    asked about. If the suite stays green with somebody else's papers already
    on the slate, no visible test is reading a defaulted count whole.

    The vacuous reading is refused first: a default the method refuses outright
    has to turn the suite red, or nothing visible lets the count default at all
    and the seeding claim is about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(locate, edit=defaulting("None", refusing=True))
    assert visible_tests_pass(locate, edit=defaulting(f"[{POLLUTION}]"))


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise."""
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "newsagent" in prompt
        for giveaway in (
            DEFECTIVE_FILE, "tallying", "Slate", "slate", "Bundle", "bundle",
            DEFECTIVE_PARAMETER, "default", "argument",
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
    symptom = "Something has gone wrong at the newsagent's."

    for prompt in prompts:
        assert "answer every ask on its own" in prompt, "does not say what correct is"
        assert "nothing whatever left over from an earlier one" in prompt
        assert prompt.startswith(symptom)
    reported = {"\n\n".join(prompt.split("\n\n")[:2]) for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def mutable_defaults() -> set[tuple[str, str, str]]:
    """Every (file, symbol, parameter) in the repository whose default value is
    built once, at import: a list, a dict or a set written into a `def` line."""
    found = set()
    for path in code_files():
        for name, node in functions(path.read_text(encoding="utf-8")).items():
            positional = node.args.posonlyargs + node.args.args
            defaulted = positional[len(positional) - len(node.args.defaults):]
            for parameter, default in zip(
                defaulted, node.args.defaults, strict=True
            ):
                if isinstance(default, ast.List | ast.Dict | ast.Set):
                    found.add((path.name, name, parameter.arg))
    return found


def adds_to_its_default() -> set[tuple[str, str, str]]:
    """The ones that do not only read it. A default read and never written to
    is correct however mutable it is; one that is added to is the defect."""
    written = set()
    for file, name, parameter in mutable_defaults():
        node = function(repo_source(file), name)
        for statement in ast.walk(node):
            if (
                isinstance(statement, ast.Call)
                and isinstance(statement.func, ast.Attribute)
                and isinstance(statement.func.value, ast.Name)
                and statement.func.value.id == parameter
                and statement.func.attr
                in {"append", "extend", "insert", "update", "add", "setdefault"}
            ):
                written.add((file, name, parameter))
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == parameter
                for target in statement.targets
            ):
                written.add((file, name, parameter))
    return written


def test_the_defect_is_not_the_only_mutable_default_in_the_repository() -> None:
    """A single mutable default in the whole repository makes locating a grep.

    It is the most greppable defect shape there is — one `=[]` in a `def` line
    — so the repository writes six more, across four files, and every one of
    them is correct because it is read and never added to: the order the shop
    has written down for its streets, the numbers left off this week, the
    streets left out of a reckoning, and the pad by the till, twice. So the
    shape names seven sites and which of them is wrong is decided by what the
    body does with it rather than by the pattern.

    The other half of the same claim, and the one that says the defect is
    really there: exactly one of the seven is added to, and it is the planted
    one.
    """
    defaults = mutable_defaults()

    assert defaults == {(DEFECTIVE_FILE, DEFECTIVE_SYMBOL, DEFECTIVE_PARAMETER),
                        *CORRECT_TWINS}
    assert len({file for file, *_ in defaults}) == 4
    assert adds_to_its_default() == {
        (DEFECTIVE_FILE, DEFECTIVE_SYMBOL, DEFECTIVE_PARAMETER)
    }


def test_the_repository_declares_the_shape_it_uses_correctly() -> None:
    """Why the six correct ones are not merely six more places to look.

    Three of them are asserted read-only by the repository's own tests, so the
    shape is *legitimised* rather than left ambiguous: an agent reading the
    visible suite is told, in the repository's own voice, that a mutable
    default here is the shop's way of passing something in to be read. And the
    defective parameter is the one the visible suite says is added to on
    purpose — so its lack of a "is not added to" test is not the anomaly that
    would give it away, but the opposite claim, stated outright.
    """
    suite = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(task_by_id(FAULT_LOCATION).repo_dir.glob("test_*.py"))
    )

    for declared in (
        "def test_the_order_the_shop_wrote_down_is_not_added_to",
        "def test_the_numbers_left_off_are_not_added_to",
        "def test_the_pad_by_the_till_is_not_written_to",
        "def test_a_count_already_begun_is_added_to_and_comes_back",
    ):
        assert declared in suite, f"the visible suite no longer says {declared}"
    assert f"def test_the_{DEFECTIVE_PARAMETER}_is_not_added_to" not in suite


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Whether a defaulted count starts empty every time is the whole of the
    inference, so a docstring saying "on a clean slate" three lines above the
    `def` line that keeps one list forever removes the last step of the work.
    It is stated once, in the module docstring at the top of the file, and the
    defect is well down it: a reader has to carry it there. The defective
    method's own docstring says what the parameter is for — a count already
    begun may be put on the slate — which is honest about the parameter and
    silent about what happens when nobody passes one.
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
        for word in ("clean slate", "belongs to that ask", "lying there", "on its own")
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


def test_rebuilding_the_count_instead_of_adding_to_it_is_not_the_fix() -> None:
    """The one false negative this task knowingly carries, pinned so that it is
    a known cost rather than a surprise.

    `so_far = list(so_far)` cures the symptom the prompt reports — every ask is
    about its own walk again — and breaks what the parameter is for: a count
    handed in is the one added to, in place, and handed back. The repository
    says so rather than the prompt, in `Newsagent.every_bundle`, which throws
    the return value away and reads the list it passed; the fix member's
    task.yaml declares it; and the held-out tests grade it unresolved.
    """
    fix = task_by_id(BUG_FIX)

    def rebuilt(workdir: Path) -> None:
        source = workdir / DEFECTIVE_FILE
        text = source.read_text()
        changed = text.replace(
            f"        if {DEFECTIVE_PARAMETER} is None:\n"
            f"            {DEFECTIVE_PARAMETER} = []\n",
            f"        {DEFECTIVE_PARAMETER} = list({DEFECTIVE_PARAMETER} or [])\n",
        )
        assert changed != text, "the reference fix moved"
        source.write_text(changed)

    diff = solution_diff(fix, mutate=rebuilt)

    [record] = evaluate([fix], [run_for(fix, diff)], source="run-log")
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Slate.bundles", "Slate", "bundles"])
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
        "Slate.walked", "walked", "Slate.busiest", "busiest",
        "added_up", "Bundle", "NOTHING_YET",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Slate.walked` is where a walk's houses come from,
    `Slate.busiest` is the other caller of the defective method and one of the
    two that pass a list of their own, `added_up` carries a mutable default of
    its own and is correct, `NOTHING_YET` is what a street's count starts at,
    and `Bundle` — the second class, the one that makes naming `Slate` a
    choice — is what a street's papers tied together comes to. All of them are
    correct, so an answer naming one has read the right file and not found the
    defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement 36.3 asks be spent
    on files the accepted set does not name.

    `newsagent.py` is the module the symptom points at first: the list the
    prompt quotes is made up there, by `Newsagent.bundle_list`, and its lines
    are written by `counter_line`. `rounds.py` is what the prompt's own word
    for the thing asked about names, and `Round.drops` is the other reckoning
    of which houses a walk takes in. Every one of them is run through the real
    pipeline by the lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {"newsagent.py", "rounds.py"}
    assert ("rounds.py", "Round.drops") in {
        (answer.file, answer.symbol) for answer in key.rejected
    }
    assert ("newsagent.py", "Newsagent.bundle_list") in {
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
        defaulting("None")(workdir)

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
        (workdir / "notes.md").write_text("the count carries over between asks\n")

    assert verdict(locate, answered_with_notes) == 1.0
