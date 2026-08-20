"""Round 7's third TypeScript planted defect (#107): one stage of a stream
pipeline that holds part of its input back across chunks and then throws away
what it is still holding when the input ends, authored as two tasks that share
it.

`telegraph-write-up-the-last-message-of-the-day` asks for the fix and
`telegraph-locate-the-message-left-on-the-tape` asks only for the location,
over one hand-authored stream pipeline holding one planted defect:
`Cutter._flush` clears the tape it has read past the last mark instead of
giving it out. Every message with a mark after it is read off, charged and
written up exactly as it should be; the last message of the day — the one with
no mark after it, because nothing was sent after it — is held until the drum
stops and is then dropped. Nothing throws, nothing is left half done, and the
run settles as it always did: what is wrong with the page is only what is not
on it. Same terrain, same defect, two actions, which is what makes "what does
locating cost, as against fixing?" a reading of the two actions rather than of
two repositories.

This is `tests/test_firstparty_v1_ts_http_service.py`'s suite over the third
TypeScript scenario, and it proves the same things over terrain that is a
stream pipeline rather than a service or an event flow. What it checks that no
other suite can:

- **The two members really do share one repository**, byte for byte. Those
  shared bytes are how the lint finds the `bug-fix` partner that is the locate
  member's registered existence proof; the lint reads them for *finding* the
  partner rather than for holding the two trees identical, so this is still
  the only thing that says they have not drifted.
- **The defect the fix removes is the defect the key names.** The lint proves
  the answer key discriminates and the reference solution proves the fix
  works, but nothing joins them: here the file the fix touches and the file
  every accepted answer names are asserted to be one file.
- **No verdict on either side is decided by wall-clock timing, and every
  held-out test terminates.** This is the rule the ticket sets and the spec
  does not, and it has two halves because a stream has two ways to be graded
  badly. A defect graded by writing, sleeping and then looking is a verdict
  about the scheduler on the grading machine, and round 1 already paid for one
  of those; a test that waits on a stream nobody ends is a grading timeout,
  which reads as unresolved and tells nobody anything. So: no test on either
  side of the verdict names a timer or a clock, every held-out test reads its
  verdict off the promise the day's work hands back, and the whole held-out
  suite is run against the reference solution under a small fraction of the
  grader's own budget and required to finish inside it.
- **The repository is what ADR-0003 says a TypeScript task ships**: flat, no
  manifest and no installed tree, `node:` builtins and relative `.ts` imports
  only, and an entry point guarded the way Node 22 allows, so that every
  module is side-effect-free at import.
- **The scenario is a real stream pipeline**, which is the reason this task
  exists rather than a ninth Python one: `node:stream` transforms strung end to
  end by `node:stream/promises`' `pipeline`, a source that gives out a length
  of tape only when one is asked for, and a sink whose high-water mark is what
  keeps the whole day's traffic from standing in the office at once. Disclosed
  in the prompt rather than as a task field, and the back-pressure is proved by
  running it rather than by reading the constructor arguments.
- **The repository reproduces the symptom nowhere the agent can see it.** The
  visible suite exercises the holding-back at length — a message spread over
  two lengths of tape, a message spread over three, a mark landing on the seam
  — and every one of those tapes ends at a mark, so the cutter is never still
  holding anything when the drum stops. Proved by making a remainder at the end
  an outright error and watching the suite stay green, with the vacuous reading
  refused first by making the hook throw unconditionally and watching it go
  red.
- **What the key accepts and refuses on this task's own terrain**: both
  description levels the author wrote down resolve, and every other symbol of
  the defective file does not.
- **The terrain leaves the locating to be done**, the half the task-set lint
  cannot see: a stream stage's end-of-input hook is a shape a grep finds in one
  pass, so the repository holds four more of them across three modules and
  every one is correct; both answers to "what does a stage owe when the input
  ends?" are written correctly somewhere, so the shape decides nothing; and the
  contract the defect breaks is written a file's length from the line that
  breaks it.
- **What no pattern can tell apart**, which is this defect's whole
  discrimination: `Repeats._flush` holds something across the whole day and
  gives out nothing at the end, and is correct, because what it holds went down
  the office as it came. Asserted by running the two under the Node that grades
  them.
- **The two repairs that are not the fix**: the same edit made to the twin, and
  a repair that gives out whatever it is holding without asking whether it is
  holding anything. Both graded through the real pipeline rather than argued
  about.
- **The hash gate**, generated by the CLI flag and never typed, holding the
  locate member to answering rather than repairing.

The rest is what every checked-in task has to prove — lints clean, reference
solution grades resolved, the empty diff grades unresolved — all through the
same execution-verified pipeline real runs go through.
"""

import json
import re
import shutil
import subprocess
import tempfile
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
    GRADE_TIMEOUT_S,
    HASH_GATE_FILE,
    Task,
    _run_grading,
    _tree_bytes,
    answer_key,
    evaluate,
    hash_gate_source,
    is_control,
    lint_task_set,
)
from ai_benchmark.language_runners import TYPESCRIPT

BUG_FIX = "telegraph-write-up-the-last-message-of-the-day"
FAULT_LOCATION = "telegraph-locate-the-message-left-on-the-tape"
MEMBERS = (BUG_FIX, FAULT_LOCATION)

# The file the defect lives in, and the one the fix touches. One name, asserted
# from both sides below.
DEFECTIVE_FILE = "messages.ts"
DEFECTIVE_SYMBOL = "Cutter._flush"

ANSWER_PATH = "ANSWER.json"

# The whole of the defect: the end-of-input hook that throws away the tape it
# is still holding, comment and body, exactly as the repository ships it.
DEFECTIVE_FLUSH = """\
  /**
   * The drum has stopped. The day is over, so the reel goes back on its shelf
   * as it came off it and nothing is carried over into tomorrow.
   */
  _flush(done: Done): void {
    this.held = "";
    done();
  }
"""

# The whole of the reference solution: the same hook, giving out what it holds.
FIXED_FLUSH = """\
  /**
   * The drum has stopped, so what is still held is the last message of the
   * day: sent, with nothing after it and nothing more to wait for. It goes
   * out now, and the reel goes back on its shelf with nothing carried over
   * into tomorrow.
   */
  _flush(done: Done): void {
    const left = this.held;
    this.held = "";
    if (left.trim() !== "") {
      this.push(readOff(left));
    }
    done();
  }
"""

# The nearest twin: a stage that holds something right through the day and
# gives out nothing when the day ends, in another module, and correct.
TWIN_FILE = "sheet.ts"
TWIN_FLUSH = """\
  _flush(done: Done): void {
    this.last = null;
    done();
  }
"""

# Every stream hook the repository's modules implement, as (file, hook) with
# the count of that pair — read and never added to. Named here because the
# terrain claim is that a grep for the end-of-input shape finds five sites
# across four modules and has to read all five.
HOOKS = {
    ("tape.ts", "_read"): 1,
    (DEFECTIVE_FILE, "_transform"): 1,
    (DEFECTIVE_FILE, "_flush"): 1,
    ("charges.ts", "_transform"): 1,
    (TWIN_FILE, "_transform"): 2,
    (TWIN_FILE, "_flush"): 2,
    (TWIN_FILE, "_write"): 1,
    (TWIN_FILE, "_final"): 1,
}

# The hooks that run when the input ends — where the defect is, and where the
# four correct answers to "what does a stage owe now?" are written.
END_OF_INPUT = ("_flush", "_final")

# The contract the defect breaks, in the repository's own words — deliberately
# not the prompt's, which the task-set lint's narrowing terrain rule checks.
CONTRACT = (
    "It is a message like any other, it costs what any other costs and it goes "
    "on the page where any other would, and the office has it as soon as the "
    "drum stops, because there is nothing more to wait for."
)

# The one held-out `.test.ts` file the bug-fix member is graded by.
HELD_OUT = "what_the_sheet_says.test.ts"

# What the whole held-out suite gets to run in, against the grader's own 300.
# Small enough that a test which waited on a stream nobody ended would fail
# here long before it became a grading timeout nobody could read.
TERMINATES_WITHIN_S = 30

# What a test would reach for if it decided a verdict by waiting: a timer, a
# clock, or a hop scheduled off one.
WALL_CLOCK = (
    "setTimeout",
    "setInterval",
    "setImmediate",
    "Date.now",
    "new Date",
    "performance.now",
    "hrtime",
    "sleep",
)

# The promise every held-out verdict is read off: the one `pipeline` hands the
# office, which settles when the drum has stopped, every stage has given out
# everything it had and the sheet has taken the last line.
THE_DAYS_PROMISE = "await office.work()"

# A stream hook: a method of a class, declared at the head of its own line.
_HOOK = re.compile(r"^  (_(?:read|write|final|transform|flush))\(", re.MULTILINE)


def repo_dir() -> Path:
    return task_by_id(FAULT_LOCATION).repo_dir


def repo_source(file: str) -> str:
    return (repo_dir() / file).read_text(encoding="utf-8")


def solution_source(task_id: str, file: str) -> str:
    solutions = task_by_id(task_id).directory.parent.parent / "first-party-v1-solutions"
    return (solutions / task_id / file).read_text(encoding="utf-8")


def code_files() -> list[Path]:
    """The repository's modules, its own test suite left out."""
    return [
        path
        for path in sorted(repo_dir().glob(TYPESCRIPT.source_glob))
        if not path.name.endswith(".test.ts")
    ]


def repo_files() -> list[Path]:
    """Every `.ts` file the agent is handed, its own tests included."""
    return sorted(repo_dir().glob(TYPESCRIPT.source_glob))


def held_out_source() -> str:
    return (task_by_id(BUG_FIX).grading_dir / HELD_OUT).read_text(encoding="utf-8")


def visible_source() -> str:
    return "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(repo_dir().glob(TYPESCRIPT.visible_test_glob))
    )


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


def swapping(what: str, into: str, *, file: str = DEFECTIVE_FILE) -> Callable[
    [Path], None
]:
    """One exact substitution in a module of the workdir."""

    def edit(workdir: Path) -> None:
        source = workdir / file
        text = source.read_text(encoding="utf-8")
        changed = text.replace(what, into)
        assert changed != text, f"{what!r} is no longer in {file}"
        source.write_text(changed, encoding="utf-8")

    return edit


def under_node(probe: str) -> list[str]:
    """What this probe prints, run in a throwaway copy of the repository under
    the Node that grades the task.

    A copy, because the checked-in `repo/` trees of swept tasks are immutable —
    replay of a logged run applies its diff to those exact bytes — and this
    writes a probe module into the tree.
    """
    with tempfile.TemporaryDirectory(prefix="ai-bench-probe-") as name:
        workdir = Path(name)
        shutil.copytree(repo_dir(), workdir, dirs_exist_ok=True)
        (workdir / "probe.ts").write_text(probe, encoding="utf-8")
        return subprocess.run(
            ["node", "probe.ts"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()


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
    pristine repository — its registered existence proof. What that proof does
    not reach is whether the two are about the *same* defect, so the two halves
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


def test_the_fix_is_one_end_of_input_hook_and_nothing_else() -> None:
    """One planted defect and no other seeded fault: the whole of the reference
    solution is the hook that throws the held tape away rewritten to give it
    out, so the terrain the fault-location member is measured over holds
    exactly one thing to find."""
    pristine = repo_source(DEFECTIVE_FILE)

    assert DEFECTIVE_FLUSH in pristine
    assert pristine.replace(DEFECTIVE_FLUSH, FIXED_FLUSH) == solution_source(
        BUG_FIX, DEFECTIVE_FILE
    )


def test_neither_member_claims_anything_about_difficulty() -> None:
    """Both are coverage tasks: authored to fill a category × language cell,
    betting nothing. Outside the frozen 22 that has to be said outright, and
    saying it is also what keeps them out of every knob reading — a task
    declaring no construction can join no family, no pair and no effort claim,
    so neither can advance a knob's counter or move a published multiplier."""
    for task_id in MEMBERS:
        task = task_by_id(task_id)

        assert task.control
        assert is_control(task)
        assert task.construction is None


def test_each_member_is_declared_as_designed() -> None:
    """The round's zero-knob TypeScript baseline: same surface, same language,
    the two actions one planted defect is authored under."""
    fix, locate = task_by_id(BUG_FIX), task_by_id(FAULT_LOCATION)

    assert (fix.category, fix.scale, fix.surface, fix.language) == (
        "bug-fix", "single-file", "application", "typescript",
    )
    assert (locate.category, locate.scale, locate.surface, locate.language) == (
        "fault-location", "single-file", "application", "typescript",
    )
    assert fix.runner is TYPESCRIPT
    assert locate.runner is TYPESCRIPT


# --- what ADR-0003 says a typescript task ships --------------------------------


def test_the_repository_is_flat_and_installs_nothing() -> None:
    """ADR-0003 on the author, plus the flatness a keyed task owes its gate.

    The lint refuses a manifest or a vendored tree at any depth and refuses a
    directory under a keyed task's `repo/`; both are asserted here as the
    property they are, because a reader arriving at the third TypeScript
    scenario should not have to go back to the first to see the shape.
    """
    for task_id in MEMBERS:
        repo = task_by_id(task_id).repo_dir

        assert not [entry for entry in repo.iterdir() if entry.is_dir()]
        assert not list(repo.rglob("package.json"))
        assert not list(repo.rglob("node_modules"))


def test_every_import_is_a_builtin_or_one_of_the_task_s_own_files() -> None:
    """The other half of the stdlib-only rule, which the lint reads over
    held-out tests and this reads over the repository itself: a specifier is a
    `node:` builtin under its explicit prefix, or a file of this repository
    reached relatively and with the extension Node actually resolves."""
    for path in repo_files():
        source = path.read_text(encoding="utf-8")
        for specifier in re.findall(r"""from\s+["']([^"']+)["']""", source):
            if specifier.startswith("node:"):
                continue
            assert specifier.startswith("./"), f"{path.name} imports {specifier!r}"
            assert specifier.endswith(".ts"), f"{path.name} imports {specifier!r}"
            assert (repo_dir() / specifier).is_file()


def test_the_scenario_is_a_pipeline_and_its_entry_point_is_guarded() -> None:
    """A stream pipeline with no streams in it is not one, and a module that
    works a day when it is merely imported cannot be graded: the lint imports
    every `.ts` file this task ships, for real, in a throwaway subprocess. Node
    22 has no `import.meta.main`, so the entry point is guarded by comparing
    `process.argv[1]` against this module's own URL."""
    office, tape, sheet = (
        repo_source("office.ts"), repo_source("tape.ts"), repo_source(TWIN_FILE)
    )

    assert 'from "node:stream/promises"' in office
    assert "await pipeline(" in office
    assert 'from "node:stream"' in tape
    assert "extends Readable" in tape
    assert "extends Transform" in repo_source(DEFECTIVE_FILE)
    assert "extends Writable" in sheet
    assert "process.argv[1] === fileURLToPath(import.meta.url)" in office
    assert 'from "node:url"' in office


def test_nothing_is_given_out_until_the_far_end_asks_for_it() -> None:
    """Back-pressure, which is half of what makes this scenario a pipeline
    rather than a loop, proved by running it rather than by reading a
    constructor argument.

    The source hands out a length of tape when the office asks for one and not
    before — so a day that is never worked has had nothing off the drum at all,
    and a day that is worked has had every length and no more. Both readings
    are counts of what happened rather than of when, which is what keeps this
    off the clock the way every other verdict here is.
    """
    assert "highWaterMark: 1" in repo_source("tape.ts")
    assert "highWaterMark: 1" in repo_source(TWIN_FILE)

    printed = under_node(
        'import { Office } from "./office.ts";\n'
        'import { Sheet } from "./sheet.ts";\n'
        'import { Drum, MARK, inLengths } from "./tape.ts";\n'
        "\n"
        "const tape = `A one${MARK}B two${MARK}C three${MARK}`;\n"
        "const lengths = inLengths(tape, 8);\n"
        "const drum = new Drum(lengths);\n"
        "const office = new Office(drum, new Sheet());\n"
        "\n"
        "console.log(`before ${drum.given()}`);\n"
        "await office.work();\n"
        "console.log(`after ${drum.given()} of ${lengths.length}`);\n"
    )

    assert printed == ["before", "0", "after", "3", "of", "3"]


def test_the_scenario_is_disclosed_in_the_prompt_and_is_not_a_task_field() -> None:
    """What makes this task worth authoring is its scenario — a stream
    pipeline, which the Python corpus has nothing like — and a scenario is
    disclosed rather than keyed on: there is no `scenario:` field, and both
    prompts say what the agent is looking at."""
    for task_id in MEMBERS:
        task = task_by_id(task_id)
        flowed = " ".join(task.prompt.split())

        assert "comes off the drum a length at a time" in flowed
        assert "no faster than the far end will take it" in flowed
        assert "Node standard library" in flowed
        assert not hasattr(task, "scenario")


def test_the_readme_names_the_way_the_visible_suite_is_actually_run() -> None:
    """`node --test` with no arguments really does discover `*.test.ts` on the
    Node that grades this, so the README is honest — and this suite runs the
    visible tests exactly that way, which is what makes the claim checkable
    rather than a sentence in a file."""
    readme = repo_source("README.md")

    assert "Run the tests with `node --test`." in readme
    assert "node office.ts" in readme
    assert visible_tests_pass(task_by_id(BUG_FIX))


# --- no verdict is a fact about the scheduler, and every one of them arrives ---


def test_no_test_on_either_side_of_the_verdict_waits_on_a_length_of_time() -> None:
    """The first half of the rule this ticket sets, and the reason for it.

    A stream defect can always be graded the lazy way: write the tape in, wait
    a moment, look at the page. That verdict is a fact about how loaded the
    grading machine was — a sleep long enough today is short enough on a slower
    box, and round 1 already paid for a gate that turned on scheduler luck. So
    neither suite names a timer or a clock at all, and neither does the
    repository: what the office waits on is the promise `pipeline` hands it,
    which settles on the work being done.
    """
    for source in (held_out_source(), visible_source()):
        for reached_for in WALL_CLOCK:
            assert reached_for not in source, reached_for
    for reached_for in WALL_CLOCK:
        assert reached_for not in "".join(
            path.read_text(encoding="utf-8") for path in code_files()
        ), reached_for


def test_every_held_out_verdict_is_read_off_the_day_s_own_promise() -> None:
    """The same half, stated positively: every held-out test waits on the
    promise the day's work hands back, which settles when the drum has stopped,
    every stage has given out everything it had and the sheet has taken the
    last line. A test that read the page without waiting on that would be
    asserting about a moment nobody defined."""
    source = held_out_source()
    cases = source.split("\ntest(")[1:]

    assert len(cases) >= 5
    for case in cases:
        assert THE_DAYS_PROMISE in case, case.splitlines()[0]


def test_every_held_out_test_terminates_because_the_tape_does() -> None:
    """The second half of the rule, and the one a stream scenario has to earn
    that an event flow does not.

    A held-out test that waits on a stream nobody ends does not fail: it hangs,
    the grader's timeout expires, and the run is written down as unresolved
    with nothing to say whether the agent was wrong or the test was. So the
    whole held-out suite is run against the reference solution under a small
    fraction of the grader's own budget and required to finish inside it — a
    hang under this bound is a red test here rather than a silent unresolved
    on a paid sweep.
    """
    fix = task_by_id(BUG_FIX)

    assert TERMINATES_WITHIN_S < GRADE_TIMEOUT_S
    assert _run_grading(
        fix,
        solution_diff(fix),
        list(fix.language_test_paths),
        timeout_s=TERMINATES_WITHIN_S,
    )


# --- the symptom is visible and its cause is not -------------------------------


def test_the_repository_reproduces_the_symptom_in_no_visible_test() -> None:
    """The convention this corpus holds to: a failing test in the starting
    repository would point straight at the defect and delete the action both
    members measure. So the repository's own suite is green while the defect is
    in it — the symptom reaches the agent through the prompt alone."""
    for task_id in MEMBERS:
        assert visible_tests_pass(task_by_id(task_id))


def test_the_visible_suite_stays_green_on_the_fix() -> None:
    """The other direction: the fix is a fix and not a rewrite — everything the
    repository already asserted about itself still holds."""
    fix = task_by_id(BUG_FIX)

    assert visible_tests_pass(fix, edit=solved_tree(fix))


def test_no_visible_test_ends_a_tape_anywhere_but_at_a_mark() -> None:
    """*Why* the visible suite is green, asserted rather than hoped for.

    A stage that drops what it is holding when the input ends is invisible to
    every test that leaves it holding nothing, and the repository is written so
    that every tape a visible test sends ends at a mark. It exercises the
    holding-back at length all the same — a message spread over two lengths, a
    message spread over three, a mark landing on the seam between them — which
    legitimises the buffer in the repository's own voice without reproducing
    the symptom. That is a property of the fixtures rather than of the code,
    and it would be silently lost the first time a visible test ended a tape
    mid-message.

    Asserted by making a remainder at the end an outright error: if the suite
    stays green with the hook throwing whenever anything is still held, nothing
    visible reaches it.

    The vacuous reading is refused first: with the hook throwing whatever it
    holds, the suite has to go red, or nothing visible reaches the end of a
    tape at all and the reading above is about nothing.
    """
    locate = task_by_id(FAULT_LOCATION)

    assert not visible_tests_pass(
        locate,
        edit=swapping(
            '    this.held = "";\n    done();',
            '    throw new Error("the drum stopped");',
        ),
    )
    assert visible_tests_pass(
        locate,
        edit=swapping(
            '    this.held = "";\n    done();',
            '    if (this.held.trim() !== "") {\n'
            '      throw new Error("something was left on the tape");\n'
            "    }\n"
            '    this.held = "";\n'
            "    done();",
        ),
    )


def test_each_prompt_states_the_symptom_and_not_its_cause() -> None:
    """Both members do the same detective work; only the deliverable differs.
    A prompt naming the defective module or method would make the
    fault-location task a transcription exercise.

    Read on word boundaries, because the words this defect is *about* are
    ordinary English a prompt about a day sheet is entitled to: "the foot
    counts what the sheet holds" says what the page is for and nothing about a
    stage keeping something back, and a substring test that read "hold" out of
    "holds" would be refusing the prompt for the matcher's reasons rather than
    for the task's.
    """
    for task_id in MEMBERS:
        prompt = task_by_id(task_id).prompt

        assert "telegraph office" in prompt
        for giveaway in (
            DEFECTIVE_FILE, "Cutter", "flush", "held", "holding", "buffer",
            "Transform", "stream", "chunk", "Wire", "remainder", "carried over",
        ):
            assert not re.search(rf"\b{re.escape(giveaway)}\b", prompt), (
                f"{task_id} names {giveaway}"
            )


def test_both_prompts_state_the_intended_behaviour() -> None:
    """Parity of information about what correct *is*, not identical text.

    A fix member that is told what correct is while the locate member has to
    infer it understates the fix side of the very comparison the two members
    exist to produce. Here the symptom paragraphs are one text in both and the
    rule is stated in both: what separates them is the deliverable paragraph
    alone. Saying what correct is leaks no location.
    """
    prompts = [task_by_id(task_id).prompt for task_id in MEMBERS]
    symptom = "Something has gone wrong at the telegraph office."

    for prompt in prompts:
        flowed = " ".join(prompt.split())
        assert "every message on the day's tape" in flowed, "no rule stated"
        assert "in the order it was sent" in flowed
        assert prompt.startswith(symptom)
    reported = {"\n\n".join(prompt.split("\n\n")[:3]) for prompt in prompts}
    assert len(reported) == 1, "the two members report different symptoms"


# --- the terrain leaves the locating to be done --------------------------------


def hooks() -> dict[tuple[str, str], int]:
    """Every stream hook the repository's modules implement."""
    found: dict[tuple[str, str], int] = {}
    for path in code_files():
        for hook in _HOOK.findall(path.read_text(encoding="utf-8")):
            key = (path.name, hook)
            found[key] = found.get(key, 0) + 1
    return found


def test_the_defect_is_not_the_only_end_of_input_hook_in_the_repository() -> None:
    """A single end-of-input hook in the whole repository makes locating a grep.

    It is a shape a grep finds in one pass, so the repository writes four more,
    across three modules, and every one of them is correct: the page's foot is
    given out when the last message has gone by, the stage that marks a repeat
    gives out nothing and is right to, the sheet has nothing owing because
    every line went down as it arrived, and the drum says the tape has run out.

    The other half of the same claim, and the harder one: both answers to "what
    does a stage owe when the input ends?" are written correctly somewhere in
    the repository. So the shape decides nothing at all — not even "the odd one
    out" — and what decides it is whether the stage is still holding something
    nobody downstream has seen, which no pattern shows.
    """
    found = hooks()

    assert found == HOOKS
    assert len({file for file, _ in found}) == 4
    ending = {
        (file, hook): count
        for (file, hook), count in found.items()
        if hook in END_OF_INPUT
    }
    assert sum(ending.values()) == 4
    assert len({file for file, _ in ending}) == 2
    assert sum(count for (file, _), count in ending.items() if file == TWIN_FILE) == 3


def test_both_answers_to_what_a_stage_owes_are_written_correctly() -> None:
    """The claim above, read off the hooks themselves rather than counted.

    One correct end-of-input hook gives something out — the foot of the page,
    which is nobody's message and is on no line yet — and two give nothing out
    and are right to, because what they held went down the office as it came.
    So an agent that finds the shape has found four correct uses of it and one
    wrong one, and telling them apart is reading rather than matching.
    """
    twin = repo_source(TWIN_FILE)

    assert "    done(null, footed(this.messages, this.pence));\n" in twin
    assert TWIN_FLUSH in twin
    assert "  _final(done: Done): void {\n    done();\n  }\n" in twin


def test_the_repository_declares_the_shape_it_uses_correctly() -> None:
    """Why the four correct ones are not merely four more places to look.

    Several of them are asserted by the repository's own tests, so the shape is
    *legitimised* rather than left ambiguous: an agent reading the visible
    suite is told, in the repository's own voice, that a stage giving something
    out when the input ends is how this repository foots a page — and that a
    message spread over several lengths of tape is one message, so the holding
    back is declared too. The concept is present everywhere except where it is
    thrown away.
    """
    suite = visible_source()

    for declared in (
        'test("the page is footed when the last message has gone by"',
        'test("a day nobody sent anything on is footed all the same"',
        'test("a message spread over two lengths is one message all the same"',
        'test("a message spread over three lengths is one message all the same"',
        'test("this stage prices every message it is given and holds none of them"',
        'test("the drum gives out nothing until a length is asked for"',
    ):
        assert declared in suite, f"the visible suite no longer says {declared}"


def test_the_nearest_twin_is_the_same_shape_written_correctly() -> None:
    """This defect's whole discrimination, run rather than described.

    `Repeats._flush` and `Cutter._flush` both end a day holding something and
    both give out nothing. One is correct and one is the defect, and what
    separates them is only whether what is held has been seen downstream
    already: the hand a repeat is measured against went down the office with
    the message it came on, while the tape read past the last mark has been
    nowhere at all. Nothing a grep or a linter sees tells them apart — so this
    is asserted by running both under the Node that grades the task, over one
    day whose tape ends at a mark and one whose tape ends in the middle of a
    message.
    """
    printed = under_node(
        'import { Readable } from "node:stream";\n'
        'import { pipeline } from "node:stream/promises";\n'
        "\n"
        'import { Charge } from "./charges.ts";\n'
        'import { Office } from "./office.ts";\n'
        'import { Repeats, Sheet } from "./sheet.ts";\n'
        'import { Drum, MARK, inLengths } from "./tape.ts";\n'
        "\n"
        "// What the twin holds is carried right through the day...\n"
        "const marked: boolean[] = [];\n"
        "await pipeline(\n"
        '  Readable.from([new Charge("A", 8), new Charge("A", 8)]),\n'
        "  new Repeats(),\n"
        "  async (charges) => {\n"
        "    for await (const charge of charges) {\n"
        "      marked.push((charge as Charge).again);\n"
        "    }\n"
        "  },\n"
        ");\n"
        "console.log(`carried ${marked.filter(Boolean).length}`);\n"
        "\n"
        "// ...and giving out none of it at the end costs the page nothing,\n"
        "// while the same silence in the cutter costs it a whole line.\n"
        "const worked = async (tape) =>\n"
        "  (await new Office(new Drum(inLengths(tape, 8)), new Sheet()).work())"
        ".length;\n"
        "console.log(`atMark ${await worked(`A one${MARK}B two${MARK}`)}`);\n"
        "console.log(`midMessage ${await worked(`A one${MARK}B two`)}`);\n"
    )

    assert printed == ["carried", "1", "atMark", "3", "midMessage", "2"]


def test_the_contract_is_not_written_on_top_of_the_defect() -> None:
    """Honest, and not in one glance.

    Whether the tape read past the last mark is owed to the page is the whole
    of the inference, so a comment saying so three lines above the line that
    throws it away removes the last step of the work. It is stated once, in the
    module comment at the top of the file, and the defect is well down it: a
    reader has to carry it there. The defective hook's own comment says what
    the end of the day means for the reel and is silent about what is on it.
    """
    lines = repo_source(DEFECTIVE_FILE).splitlines()
    defect = next(at for at, line in enumerate(lines) if line == "  _flush(done: Done): void {")
    comment = " ".join(" ".join(lines[: lines.index(" */")]).replace("*", " ").split())

    assert " ".join(CONTRACT.split()) in comment
    assert not any(
        word in line
        for line in lines[max(0, defect - 12):defect]
        for word in (
            "like any other", "nothing more to wait for", "as soon as the drum",
            "on the page where any other",
        )
    )
    assert defect > 60


# --- the gates every checked-in task passes ------------------------------------


def test_the_two_members_lint_clean_together() -> None:
    """Linted as the two members they are rather than one at a time: the locate
    member's existence proof is the bug-fix member's failure on the starting
    repository they share, so a set holding only one of them is one in which
    the locate task has nothing saying there is a defect in it to find."""
    assert lint_task_set([task_by_id(member) for member in MEMBERS]) == []


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
    assert task.scale == "single-file"


def test_the_reference_solutions_live_outside_the_task_directories() -> None:
    """Where nothing overlays them, collects them or hands them to an agent:
    the loader, the runner, the lint and pytest collection all read the task
    directory, and a solved copy of the repository is not in one."""
    for task_id in MEMBERS:
        task = task_by_id(task_id)
        solution = task.directory.parent.parent / "first-party-v1-solutions" / task_id

        assert solution.is_dir()
        assert solution not in task.directory.parents
        assert not list(task.directory.rglob("first-party-v1-solutions"))


# --- what each member's grading makes of a near-miss ---------------------------


def test_the_same_repair_made_to_the_twin_fixes_nothing() -> None:
    """The near-miss this defect invites, graded rather than assumed.

    An agent that greps the shape, reads the twin first and decides *that* is
    the stage dropping something has done work that looks exactly like the fix
    — a hook that held something and gave nothing out, made to give it out —
    and has changed nothing about the day except to put a hand nobody asked for
    on the end of the page. The held-out tests grade it as what it is.
    """
    fix = task_by_id(BUG_FIX)
    repaired_twin = swapping(
        TWIN_FLUSH,
        "  _flush(done: Done): void {\n"
        "    const last = this.last;\n"
        "    this.last = null;\n"
        '    done(null, last === null ? undefined : `${last}: carried`);\n'
        "  }\n",
        file=TWIN_FILE,
    )

    [record] = evaluate(
        [fix], [run_for(fix, workdir_diff(fix, repaired_twin))], source="run-log"
    )
    assert record.quality_value == 0.0


def test_a_repair_that_gives_out_whatever_it_holds_is_not_the_fix() -> None:
    """The other near-miss, and the one this scenario exists to be able to
    refuse.

    Giving out what is held when the input ends is most of the fix; the rest is
    that a stage holding *nothing* owes nothing, and a tape that ended at a
    mark leaves the cutter holding nothing at all. A repair that gives out its
    buffer unasked puts a message nobody sent at the foot of every day that
    ended tidily — so the half-repair grades unresolved, and no test had to
    guess how long to wait to say so.
    """
    fix = task_by_id(BUG_FIX)
    unguarded = swapping(
        '    this.held = "";\n    done();',
        "    const left = this.held;\n"
        '    this.held = "";\n'
        "    this.push(readOff(left));\n"
        "    done();",
    )

    [record] = evaluate(
        [fix], [run_for(fix, workdir_diff(fix, unguarded))], source="run-log"
    )
    assert record.quality_value == 0.0


@pytest.mark.parametrize("symbol", ["Cutter._flush", "Cutter", "_flush"])
def test_every_description_level_the_author_wrote_down_resolves(
    symbol: str,
) -> None:
    """The hook the tape is thrown away in and the class enclosing it are both
    legitimately correct descriptions of this defect, so both are in the key —
    and the bare hook name, which is how an agent phrases an answer about
    something nested, answers the qualified one it is spelled from."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 1.0


@pytest.mark.parametrize(
    "symbol",
    [
        "Wire", "Wire.count", "count", "readOff", "UNADDRESSED",
        "Cutter._transform", "_transform",
    ],
)
def test_every_other_symbol_of_the_defective_file_is_unresolved(
    symbol: str,
) -> None:
    """Every other site in the defective module, each of which an agent has to
    read and rule out: `Wire` — the second class, the one that makes naming
    `Cutter` a choice — and `Wire.count` say what a message is and what is paid
    for, `readOff` is where a piece of tape becomes a message, `UNADDRESSED` is
    what stands for an address nobody sent, and `Cutter._transform` is the loop
    that finds the marks and holds back what comes after the last of them — the
    place the tape is *correctly* kept. All of them are right, so an answer
    naming one has read the right file and not found the defect."""
    locate = task_by_id(FAULT_LOCATION)

    assert verdict(locate, answers(naming(DEFECTIVE_FILE, symbol))) == 0.0


def test_the_key_writes_down_the_plausible_wrong_files() -> None:
    """The near-misses no lint can invent, and the judgement that has to be
    spent on files the accepted set does not name.

    `sheet.ts` is where the page the symptom is about is written and where the
    foot that says three against a tape that carried four is added up — correct
    code, and the loudest thing in the repository — and it holds two of the
    four correct end-of-input hooks, `Totting._flush` and the twin
    `Repeats._flush`. `tape.ts` is where the tape stops, which is where an
    agent reading the symptom backwards arrives first. `office.ts` is where the
    stages are strung together, which is what looks responsible for a stage
    that never gets something. Every one of them is run through the real
    pipeline by the lint and required to grade unresolved.
    """
    key = answer_key(task_by_id(FAULT_LOCATION))

    assert key.rejected
    assert {answer.file for answer in key.rejected} == {
        TWIN_FILE, "tape.ts", "office.ts",
    }
    named = {(answer.file, answer.symbol) for answer in key.rejected}
    assert (TWIN_FILE, "Repeats._flush") in named
    assert (TWIN_FILE, "Totting._flush") in named
    assert ("tape.ts", "Drum._read") in named
    assert ("office.ts", "Office.work") in named


def test_the_key_names_no_line_number_anywhere() -> None:
    """A pair and never a line: lines shift under any edit — including the
    agent's own reading notes — and the two description levels the key accepts
    start on different ones anyway. The model refuses one at load; this reads
    the checked-in file, which is the artifact an author edits."""
    raw = json.loads(
        (task_by_id(FAULT_LOCATION).grading_dir / ANSWER_KEY_FILE).read_text(
            encoding="utf-8"
        )
    )

    for half in ("accepted", "rejected"):
        for entry in raw[half]:
            assert set(entry) == {"file", "symbol"}


def test_the_answer_key_ships_held_out_and_the_repository_carries_no_answer(
) -> None:
    """Held out of the workdir: the key travels with the grading directory the
    overlay copies at grade time, and the pristine repository the agent is
    given carries neither it nor an answer file."""
    locate = task_by_id(FAULT_LOCATION)

    assert (locate.grading_dir / ANSWER_KEY_FILE).is_file()
    assert not (locate.repo_dir / ANSWER_KEY_FILE).exists()
    assert not (locate.repo_dir / ANSWER_PATH).exists()


# --- locating is not fixing ----------------------------------------------------


def test_the_hash_gate_is_the_generated_one_and_it_is_current() -> None:
    """Generated by `ai-bench lint-v1 --write-hash-gates` and never typed: the
    shipped bytes are a pure function of the starting repository's bytes, so an
    unchanged corpus regenerates identically and a `repo/` edited after the
    gate was written is visible in a diff. The lint holds the digests to the
    tree both ways round; what this adds is that the file itself is the
    generator's output rather than something hand-repaired into agreement."""
    locate = task_by_id(FAULT_LOCATION)
    gate = locate.grading_dir / HASH_GATE_FILE

    assert gate.read_bytes() == hash_gate_source(locate.repo_dir)
    assert not (task_by_id(BUG_FIX).grading_dir / HASH_GATE_FILE).exists()


def test_a_correct_answer_that_also_repaired_the_code_is_unresolved() -> None:
    """What the hash gate is for, and what nothing else can show.

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
        swapping(DEFECTIVE_FLUSH, FIXED_FLUSH)(workdir)

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
        (workdir / "notes.md").write_text("the last message never left the tape\n")

    assert verdict(locate, answered_with_notes) == 1.0
