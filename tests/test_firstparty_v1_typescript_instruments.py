"""The lint's runner-dispatched instruments, on a TypeScript task (#101).

Ticket 03 admitted the rules that only *read* a task's files. This is the rest:
everything the lint does by **running** something, or by **reading source
structure**, dispatched on the task's declared runner — so a TypeScript
fault-location or code-review task is held to the same authoring bar as a Python
one, by the same code and not by a second copy of it.

What that covers, in the order the lint reaches it:

- the source primitives the TypeScript runner answers with a declaration scan —
  the symbols a file defines (a method both qualified and bare), the classes it
  defines at its own top level, and whether the scan can read it at all;
- the repository the terrain rules read, found by the runner's `source_glob`,
  which is the one failure this ticket has a test of its own for: under a `.py`
  glob a TypeScript repository reads as *empty* and every terrain rule passes
  vacuously, which is a green lint that checked nothing;
- the three terrain rules and the waivers that silence them;
- the constructed negatives — the four synthesised answers and the near-miss for
  an accepted-answer key, and the set-shaped ones for a findings key — graded
  through the real pipeline and required to come out unresolved;
- all three existence-proof forms: a partner `bug-fix` task's pristine failure, a
  held-out proof test per planted finding run against `repo/` and `corrected/`,
  and an accepted location resolving in the starting repository;
- must-fail-on-pristine and behaviour-tests-pass-pristine, the two runs at the
  tail of `lint_task_set`.

Every rule is asserted in **both** directions — the tree that trips it and the
tree that does not — because a rule proved one way is a rule that could be
firing on everything. Everything is a synthetic TypeScript task tree under
`tmp_path`, built on ticket 02's helper (`tests/typescript_tasks.py`) or on the
keyed writers below, and put through the real pipeline: there is no live agent,
no LLM and no network anywhere in this suite.

Node is required on the machine running it, as pytest is. Probed at v22.22.2 on
2026-08-19.

`tests/test_firstparty_v1_existence_proofs.py` is the Python half of the proof
rules and is the shape this suite's proof half is written against.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from typescript_tasks import typescript_task

from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    ANSWER_MODULE,
    ANSWER_TEST_FILE,
    CORRECTED_DIR,
    EXISTENCE_PROOFS,
    FINDINGS_KEY_FILE,
    FINDINGS_MODULE,
    FINDINGS_TEST_FILE,
    GRADE_TIMEOUT_S,
    GRADING_DIR,
    HASH_GATE_FILE,
    PROOFS_DIR,
    REPO_DIR,
    REVIEW_DIFF_FILE,
    Task,
    _answer_key_problems,
    _discrimination_problems,
    _existence_proof_problems,
    _findings_discrimination_problems,
    _load_task,
    _near_miss,
    _proof_test_passes,
    _repo_lines,
    _terrain_problems,
    answer_key,
    answer_module_source,
    answer_test_source,
    findings_key,
    findings_module_source,
    findings_test_source,
    hash_gate_source,
    lint_task_set,
    proof_test_name,
)
from ai_benchmark.language_runners import PYTHON, TYPESCRIPT, SourceUnreadable

# --- the repository every keyed fixture here starts from -------------------------
#
# Two flat modules, which is what a keyed TypeScript task's `repo/` has to be
# (the hash gate holds a keyed task to answering rather than repairing, and it
# hashes top-level files). The planted defect is in `overtimePay`: overtime is
# owed on the hours past the threshold, and this pays double on every hour once
# the threshold is passed, so a nine-hour stretch is billed at eighteen.
#
# Written in the subset of TypeScript that Node's strip-only mode runs — no
# parameter properties, no enums — because the lint imports every `.ts` file a
# task ships for real (`typescript_load_problems`).
PAYROLL = """\
export const RATE_PENCE = 1200;
export const OVERTIME_AFTER_HOURS = 8;

export function overtimePay(hours: number): number {
  if (hours > OVERTIME_AFTER_HOURS) {
    return hours * RATE_PENCE * 2;
  }
  return hours * RATE_PENCE;
}

export function weekPay(worked: number[]): number {
  return worked.reduce((running, each) => running + overtimePay(each), 0);
}
"""

# What the defect should have been: the plain rate on every hour, and the extra
# on the hours past the threshold alone.
CORRECTED_PAYROLL = PAYROLL.replace(
    "    return hours * RATE_PENCE * 2;",
    "    return hours * RATE_PENCE + (hours - OVERTIME_AFTER_HOURS) * RATE_PENCE;",
)

# Two classes, deliberately: terrain rule 3 refuses an accepted class-level
# location in a file that defines only one, so a fixture used to prove anything
# else needs a second class here.
SHIFTS = """\
export const MIN_REST_HOURS = 11;

export class Shift {
  who: string;
  start: number;
  end: number;

  constructor(who: string, start: number, end: number) {
    this.who = who;
    this.start = start;
    this.end = end;
  }

  get length(): number {
    return this.end - this.start;
  }
}

export class Rota {
  taken: Shift[] = [];

  add(shift: Shift): void {
    const last = this.taken[this.taken.length - 1];
    if (last !== undefined && shift.start - last.end < MIN_REST_HOURS) {
      throw new Error("that stretch begins too soon after the previous");
    }
    this.taken.push(shift);
  }
}
"""

REPO: dict[str, str] = {"payroll.ts": PAYROLL, "shifts.ts": SHIFTS}

# Where a keyed fixture's prompt tells the agent to write, and what its key
# declares: one path, named in both.
ANSWER_PATH = "ANSWER.json"

LOCATE_ID = "payroll-locate-the-doubled-stretch"

# Says what goes wrong without naming any location out of the key, and in words
# the repository does not use only in the accepted module — which is what the
# terrain rules hold every keyed task's prompt to.
LOCATE_PROMPT = f"""\
A week of work is billed for more than it should be as soon as a stretch runs
late. Say where that goes wrong: write the file and the symbol to {ANSWER_PATH}
in the repository root.
"""

# A prompt that says as little as this one can, for the fixtures whose accepted
# module is not `payroll` — the narrowing rule reads the prompt against whichever
# module the key names, so a fixture about some other rule needs a prompt with no
# word of the repository in it at all.
BARE_PROMPT = f"""\
Something in the round is billed wrongly. Say where that happens: write the file
and the symbol to {ANSWER_PATH} in the repository root.
"""

ACCEPTED: list[dict[str, object]] = [{"file": "payroll.ts", "symbol": "overtimePay"}]

# The plausible wrong file: the method that refuses a stretch, which is where a
# reader following the symptom lands and is not where the defect is.
REJECTED: list[dict[str, object]] = [{"file": "shifts.ts", "symbol": "Rota.add"}]


def write_keyed(
    root: Path,
    *,
    task_id: str = LOCATE_ID,
    category: str = "fault-location",
    accepted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
    prompt: str = LOCATE_PROMPT,
    repo: dict[str, str] | None = None,
    answer_test: bytes | None = None,
    extra_grading: dict[str, str] | None = None,
    **spec: Any,
) -> Path:
    """A keyed TypeScript task, written into `root` ready to load.

    Everything a keyed task ships and nothing else: the starting repository, the
    answer comparison and its canonical held-out test byte for byte, the key, and
    the hash gate generated from the repository this just wrote. A control,
    because a task outside the frozen baseline declares how it was built or that
    it claims nothing, and a fixture that declared neither would carry a second
    problem in every message count below.

    The harness-side half of the grading suite is canonical *Python* here, as it
    is in every task of every language: the answer-key test and the hash gate
    read JSON and file digests out of the workdir and never the repository's
    language. What makes this task TypeScript is what the lint reads its
    repository through, which is the whole of what this suite is about.
    """
    task_dir = root / task_id
    (task_dir / REPO_DIR).mkdir(parents=True)
    (task_dir / GRADING_DIR).mkdir()
    fields: dict[str, Any] = {
        "id": task_id,
        "category": category,
        "scale": "single-file",
        "surface": "application",
        "language": "typescript",
        "control": True,
        "prompt": prompt,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    for name, source in (REPO if repo is None else repo).items():
        (task_dir / REPO_DIR / name).write_text(source)
    (task_dir / GRADING_DIR / ANSWER_TEST_FILE).write_bytes(
        answer_test_source() if answer_test is None else answer_test
    )
    (task_dir / GRADING_DIR / ANSWER_MODULE).write_bytes(answer_module_source())
    for name, source in (extra_grading or {}).items():
        (task_dir / GRADING_DIR / name).write_text(source)
    (task_dir / GRADING_DIR / ANSWER_KEY_FILE).write_text(
        json.dumps(
            {
                "answer_path": ANSWER_PATH,
                "accepted": ACCEPTED if accepted is None else accepted,
                "rejected": REJECTED if rejected is None else rejected,
            },
            indent=2,
        )
        + "\n"
    )
    # Last, because it hashes everything above it in `repo/`.
    (task_dir / GRADING_DIR / HASH_GATE_FILE).write_bytes(
        hash_gate_source(task_dir / REPO_DIR)
    )
    return task_dir


def keyed_task(root: Path, **overrides: Any) -> Task:
    """One keyed TypeScript task, written and then loaded through the real
    loader, so it goes through every check a checked-in task does."""
    return _load_task(write_keyed(root, **overrides))


# --- the bug-fix partner: a fault-location task's existence proof ----------------

PARTNER_ID = "payroll-pay-the-extra-on-the-hours-past-the-threshold"

PARTNER_PROMPT = """\
A nine-hour stretch is billed at eighteen hours. Put it right, and change
nothing else.
"""

# The partner's held-out test, in the task's own language: it fails on the
# starting repository the two share — nine hours is billed 21600 where 12000 is
# owed — and that failure is the proof the locate member is keyed on.
PARTNER_TEST = """\
import test from "node:test";
import assert from "node:assert";

import { overtimePay } from "./payroll.ts";

test("the extra is owed on the hours past the threshold alone", () => {
  assert.strictEqual(overtimePay(9), 8 * 1200 + 1200 * 2);
});
"""

# The same test with the defect's own arithmetic in it: it *passes* on the
# starting repository, so the partner demonstrates nothing.
PARTNER_TEST_THAT_PROVES_NOTHING = PARTNER_TEST.replace(
    "8 * 1200 + 1200 * 2", "9 * 1200 * 2"
)


def write_partner(task: Task, *, grading_test: str = PARTNER_TEST) -> Task:
    """The bug-fix partner beside a keyed task, sharing `repo/` byte for byte.

    Copied rather than authored a second time, because shared bytes are the whole
    of the relation the existence proof looks a partner up by: the two members
    are deliberately neither a family nor a pair, so there is no declared link to
    read.
    """
    partner_dir = task.directory.parent / PARTNER_ID
    (partner_dir / GRADING_DIR).mkdir(parents=True)
    (partner_dir / REPO_DIR).mkdir()
    for source in sorted(task.repo_dir.iterdir()):
        (partner_dir / REPO_DIR / source.name).write_text(
            source.read_text(encoding="utf-8")
        )
    (partner_dir / GRADING_DIR / "payroll.test.ts").write_text(grading_test)
    (partner_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "id": PARTNER_ID,
                "category": "bug-fix",
                "scale": "single-file",
                "surface": "application",
                "language": "typescript",
                "control": True,
                "prompt": PARTNER_PROMPT,
            },
            sort_keys=False,
        )
    )
    return _load_task(partner_dir)


# --- the review fixture: a findings key, a corrected tree and a proof ------------

REVIEW_ID = "payroll-review-the-doubled-stretch"

REVIEW_DIFF = """\
--- a/payroll.ts
+++ b/payroll.ts
@@ -1,6 +1,12 @@
 export const RATE_PENCE = 1200;
+export const OVERTIME_AFTER_HOURS = 8;

-export function overtimePay(hours: number): number {
+export function overtimePay(hours: number): number {
+  if (hours > OVERTIME_AFTER_HOURS) {
+    return hours * RATE_PENCE * 2;
+  }
   return hours * RATE_PENCE;
 }
--- a/shifts.ts
+++ b/shifts.ts
@@ -1,3 +1,5 @@
+export const MIN_REST_HOURS = 11;
+
 export class Shift {
"""

REVIEW_PROMPT = f"""\
{REVIEW_DIFF_FILE} in the repository root is a change that has already been
applied here: it bills more for a stretch that runs late, and it turns away a
booking made too soon after the last. Review it, and do not edit any code.

Write your findings to FINDINGS.json in the repository root, as a JSON list with
one object per finding: "file" (the path, relative to the repository root) and
"symbol" (the name the problem lives in — a top-level binding, a class or a
method).
"""

REVIEW_ANSWER_PATH = "FINDINGS.json"

# One planted finding, written as the set of locations that legitimately
# describe it, and one non-finding: the constant the change introduced, which is
# the number that was asked for.
REVIEW_ACCEPTED: list[dict[str, object]] = [
    {"any": [{"file": "payroll.ts", "symbol": "overtimePay"}]}
]
REVIEW_REJECTED: list[dict[str, object]] = [
    {"file": "shifts.ts", "symbol": "MIN_REST_HOURS"}
]

# The existence proof of the planted finding, in the task's own language: it
# fails on the starting repository, which ships the change under review already
# applied, and passes on the corrected tree.
OVERTIME_PROOF = """\
import test from "node:test";
import assert from "node:assert";

import { overtimePay } from "./payroll.ts";

test("the extra is owed on the hours past the threshold alone", () => {
  assert.strictEqual(overtimePay(9), 8 * 1200 + 1200 * 2);
});
"""

# A proof with nothing to demonstrate: the rate is what the change left it, so
# this passes on the starting repository as readily as on the corrected tree.
PROOF_THAT_PASSES_ON_THE_STARTING_REPOSITORY = """\
import test from "node:test";
import assert from "node:assert";

import { RATE_PENCE } from "./payroll.ts";

test("the rate is what it was", () => {
  assert.strictEqual(RATE_PENCE, 1200);
});
"""


def write_review(
    root: Path,
    *,
    task_id: str = REVIEW_ID,
    proofs: dict[str, str] | None = None,
    corrected: dict[str, str] | None = None,
    grading_test: bytes | None = None,
    **spec: Any,
) -> Path:
    """The fixture `code-review` task in TypeScript, written into `root`.

    What a review task ships: the starting repository with the change under
    review already applied, the unified diff of that change, the corrected tree
    the author's fix lives in, one existence proof per planted finding, and the
    findings comparison with the answer comparison it imports its forgiveness
    from — the last two byte for byte, as canonical Python, because the
    harness-side half of a grading suite is the same file in every language.
    """
    task_dir = root / task_id
    (task_dir / REPO_DIR).mkdir(parents=True)
    (task_dir / GRADING_DIR).mkdir()
    (task_dir / CORRECTED_DIR).mkdir()
    (task_dir / PROOFS_DIR).mkdir()
    fields: dict[str, Any] = {
        "id": task_id,
        "category": "code-review",
        "scale": "single-file",
        "surface": "application",
        "language": "typescript",
        "control": True,
        "prompt": REVIEW_PROMPT,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    for name, source in REPO.items():
        (task_dir / REPO_DIR / name).write_text(source)
    (task_dir / REPO_DIR / REVIEW_DIFF_FILE).write_text(REVIEW_DIFF)
    for name, source in (
        {"payroll.ts": CORRECTED_PAYROLL, "shifts.ts": SHIFTS}
        if corrected is None
        else corrected
    ).items():
        (task_dir / CORRECTED_DIR / name).write_text(source)
    for name, source in (
        {"payroll_ts_overtimePay.test.ts": OVERTIME_PROOF}
        if proofs is None
        else proofs
    ).items():
        (task_dir / PROOFS_DIR / name).write_text(source)
    (task_dir / GRADING_DIR / FINDINGS_TEST_FILE).write_bytes(
        findings_test_source() if grading_test is None else grading_test
    )
    (task_dir / GRADING_DIR / FINDINGS_MODULE).write_bytes(findings_module_source())
    (task_dir / GRADING_DIR / ANSWER_MODULE).write_bytes(answer_module_source())
    (task_dir / GRADING_DIR / FINDINGS_KEY_FILE).write_text(
        json.dumps(
            {
                "answer_path": REVIEW_ANSWER_PATH,
                "accepted": REVIEW_ACCEPTED,
                "rejected": REVIEW_REJECTED,
            },
            indent=2,
        )
        + "\n"
    )
    (task_dir / GRADING_DIR / HASH_GATE_FILE).write_bytes(
        hash_gate_source(task_dir / REPO_DIR)
    )
    return task_dir


def review_task(root: Path, **overrides: Any) -> Task:
    return _load_task(write_review(root, **overrides))


# --- the source primitives -------------------------------------------------------


def test_the_symbols_a_module_defines_are_the_declarations_it_carries() -> None:
    """Responsibility 6, answered by a declaration scan: the classes, the
    functions, the class members that are behaviour and the top-level bindings —
    and not the fields that hold a value, which are a state change inside
    something already keyable, exactly as a Python class-body assignment is."""
    assert TYPESCRIPT.defined_symbols(PAYROLL) == {
        "RATE_PENCE",
        "OVERTIME_AFTER_HOURS",
        "overtimePay",
        "weekPay",
    }
    symbols = TYPESCRIPT.defined_symbols(SHIFTS)

    assert {"MIN_REST_HOURS", "Shift", "Rota"} <= symbols
    assert "Rota.taken" not in symbols and "taken" not in symbols


def test_a_binding_is_read_at_the_modules_own_top_level_and_nowhere_else() -> None:
    """The boundary `PythonRunner.defined_symbols` draws around a module-level
    assignment, drawn again here: a fault can live in a rate, a table or a
    compiled pattern, so a top-level binding is keyable — with or without the
    semicolons a file may be written without — while a loop variable exists only
    while the loop runs and a key naming one would name nothing an agent could
    point at."""
    source = """\
export const RATE = 1200
const TABLE = { plain: 1 }

for (const each of [1, 2]) {
  TABLE.plain = each
}

export function run(rows: number[]): number {
  let running = 0
  return running
}
"""

    assert TYPESCRIPT.defined_symbols(source) == {"RATE", "TABLE", "run"}


def test_a_method_is_defined_both_qualified_and_bare() -> None:
    """The two levels an author writes a defect in a method down at — the method
    and the class enclosing it — and the bare spelling a locating agent actually
    phrases an answer with. `PythonRunner.defined_symbols` accepts both for the
    same reason; only a nested definition gets the bare form, a top-level one
    having no qualified form to be an alternative to."""
    symbols = TYPESCRIPT.defined_symbols(SHIFTS)

    assert {"Rota.add", "add", "Shift.length", "length"} <= symbols
    assert "Rota.MIN_REST_HOURS" not in symbols
    # The same, through the annotations a TypeScript method actually carries:
    # type parameters, a typed parameter list and a return type stand between
    # the name and the body, and none of them is what the name is.
    generic = """\
export class Box<T> {
  add<U>(item: U): void {}
  handle: (n: number) => void = (n) => {};
}
"""

    assert {"Box.add", "add", "Box.handle", "handle"} <= TYPESCRIPT.defined_symbols(
        generic
    )


def test_the_classes_a_module_defines_are_the_ones_at_its_own_top_level() -> None:
    """The companion reading, at the level an accepted answer naming a class is
    answering at: through an `if`, which does not change what level a
    declaration is at, and into neither a class body nor a function body."""
    assert TYPESCRIPT.defined_classes(SHIFTS) == {"Shift", "Rota"}
    nested = """\
if (true) {
  export class Guarded {}
}

export class Outer {
  make(): void {
    class Inner {}
    return;
  }
}
"""

    assert TYPESCRIPT.defined_classes(nested) == {"Guarded", "Outer"}


def test_a_comment_or_a_literal_declares_nothing() -> None:
    """What the scan reads is the file's declarations, so a brace inside a
    template, a `class` inside a comment and a `{` inside a regular expression
    are none of them one — and the declarations around them are still read."""
    source = """\
// export class Commented {}
/* export function inComment(): void {} */
const pattern = /[{}"]/;
const message = `a } brace and a ${pattern} inside`;

export class Real {
  run(): string {
    return "class NotThis {";
  }
}
"""

    assert TYPESCRIPT.defined_classes(source) == {"Real"}
    assert TYPESCRIPT.defined_symbols(source) == {
        "pattern",
        "message",
        "Real",
        "Real.run",
        "run",
    }


def test_a_file_the_scan_cannot_read_is_not_loadable() -> None:
    """`loads` is the reading instrument's own "can I see the declarations", and
    what it answers False to is a file the scan cannot get through. Its callers
    ask it before they ask for symbols, and the primitives themselves raise
    `SourceUnreadable` rather than returning an empty set — which would read as
    a file that defines nothing at all."""
    for unreadable in ('const s = "never closed;\n', "export class Half {\n"):
        assert not TYPESCRIPT.loads(unreadable)
        for call in (TYPESCRIPT.defined_symbols, TYPESCRIPT.defined_classes):
            try:
                call(unreadable)
            except SourceUnreadable:
                continue
            raise AssertionError(f"{call.__name__} read {unreadable!r}")
    assert TYPESCRIPT.loads(PAYROLL) and TYPESCRIPT.loads(SHIFTS)


# --- the callers reach the primitives through the runner -------------------------


def test_the_key_is_checked_against_what_the_typescript_file_defines(
    tmp_path: Path,
) -> None:
    """`_answer_key_problems` reads the accepted and rejected locations against
    the symbols the file actually defines, and reaches them through the task's
    runner: a key naming a symbol `payroll.ts` does not define is refused, and
    the message says what it does define."""
    task = keyed_task(
        tmp_path, accepted=[{"file": "payroll.ts", "symbol": "overtime_pay"}]
    )

    [problem] = _answer_key_problems(task)

    assert LOCATE_ID in problem and "overtime_pay" in problem
    assert "'overtimePay'" in problem


def test_a_bare_key_symbol_is_refused_where_the_qualified_spelling_exists(
    tmp_path: Path,
) -> None:
    """The rule that needs a method read at both levels, on a TypeScript file: an
    answer spelled bare matches a key spelled qualified and never the reverse, so
    a key naming `add` where `Rota.add` exists refuses the spelling an agent
    would most naturally give."""
    task = keyed_task(
        tmp_path,
        accepted=[{"file": "shifts.ts", "symbol": "add"}],
        rejected=[{"file": "payroll.ts", "symbol": "weekPay"}],
    )

    problems = _answer_key_problems(task)

    assert any(
        "Rota.add" in problem and "bare symbol" in problem for problem in problems
    ), problems


def test_a_keyed_typescript_task_reads_clean_end_to_end(tmp_path: Path) -> None:
    """The other direction of everything above, through the whole lint and with
    the partner beside it: a TypeScript fault-location task authored to the bar
    reports nothing at all. Every negative below bends exactly one thing about
    this tree."""
    task = keyed_task(tmp_path)
    partner = write_partner(task)

    assert lint_task_set([task, partner]) == []


# --- the repository the terrain rules read ---------------------------------------


def test_the_repository_is_read_through_the_runners_source_glob(
    tmp_path: Path,
) -> None:
    """The one failure of this ticket worth a test of its own: under a `.py` glob
    a TypeScript repository reads as empty, every terrain rule passes vacuously,
    and the lint is green having checked nothing. The lines are read, and a test
    file counts as part of the module it tests under this language's spelling of
    a test name as much as under pytest's."""
    task = keyed_task(
        tmp_path,
        repo=REPO | {"payroll.test.ts": "// the repository's own net\n"},
    )
    lines = _repo_lines(task)

    assert {file for _, file, _, _ in lines} == {
        "payroll.ts",
        "shifts.ts",
        "payroll.test.ts",
    }
    assert {module for module, _, _, _ in lines} == {"payroll", "shifts"}


def test_a_prompt_word_that_narrows_to_the_accepted_module_is_refused(
    tmp_path: Path,
) -> None:
    """Terrain rule 2 on a TypeScript repository, which is the rule that would
    pass vacuously if the repository were read as empty: `weekPay` is a word the
    prompt uses that appears in the accepted module and nowhere else, so one grep
    of the prompt's own vocabulary lands in the file the agent was asked to
    find."""
    task = keyed_task(
        tmp_path,
        prompt=LOCATE_PROMPT.replace("A week of work", "The weekPay of the round"),
    )

    problems = _terrain_problems(task)

    assert any(
        "prompt-word-narrows-to-the-accepted-module" in problem
        and "weekpay" in problem
        and "payroll.ts" in problem
        for problem in problems
    ), problems


def test_a_narrowing_word_a_waiver_names_is_silenced(tmp_path: Path) -> None:
    """A waiver silences a rule only for what it names, and a waiver naming
    something the rule does not fire on is itself reported — both properties
    reach a TypeScript task unchanged, the waiver being read against what the
    rule fired on and never against the repository it fired over."""
    prompt = LOCATE_PROMPT.replace("A week of work", "The weekPay of the round")
    waived = keyed_task(
        tmp_path / "waived",
        prompt=prompt,
        terrain_waiver=[
            {
                "rule": "prompt-word-narrows-to-the-accepted-module",
                "covers": ["weekpay"],
                "reason": "the fixture is naming the module on purpose",
            }
        ],
    )
    stale = keyed_task(
        tmp_path / "stale",
        terrain_waiver=[
            {
                "rule": "prompt-word-narrows-to-the-accepted-module",
                "covers": ["weekpay"],
                "reason": "the terrain this apologises for is no longer there",
            }
        ],
    )

    assert _terrain_problems(waived) == []
    [problem] = _terrain_problems(stale)
    assert "the rule does not fire on" in problem and "weekpay" in problem


def test_a_prompt_that_names_a_key_location_is_refused(tmp_path: Path) -> None:
    """Terrain rule 1, on the key's own spellings: a prompt naming the file or
    the symbol of either half hands the agent the reading it was supposed to
    do."""
    named = keyed_task(
        tmp_path / "named",
        prompt=LOCATE_PROMPT.replace("a stretch runs", "overtimePay runs"),
    )

    problems = _terrain_problems(named)

    assert any(
        "prompt-names-a-key-location" in problem and "overtimePay" in problem
        for problem in problems
    ), problems
    assert _terrain_problems(keyed_task(tmp_path / "quiet")) == []


def test_an_accepted_class_that_is_the_only_class_in_its_file_is_refused(
    tmp_path: Path,
) -> None:
    """Terrain rule 3, read through the runner's `defined_classes`: where a file
    defines exactly one class, an agent answering at class level has that answer
    determined by the filename alone. `shifts.ts` defines two, so the same key
    against it is quiet."""
    lone = keyed_task(
        tmp_path / "lone",
        prompt=BARE_PROMPT,
        repo={
            "payroll.ts": PAYROLL,
            "ledger.ts": "export class Ledger {\n  post(): void {}\n}\n",
        },
        accepted=[{"file": "ledger.ts", "symbol": "Ledger"}],
        rejected=[{"file": "payroll.ts", "symbol": "weekPay"}],
    )
    paired = keyed_task(
        tmp_path / "paired",
        prompt=BARE_PROMPT,
        accepted=[{"file": "shifts.ts", "symbol": "Rota"}],
        rejected=[{"file": "payroll.ts", "symbol": "weekPay"}],
    )

    problems = _terrain_problems(lone)

    assert any(
        "accepted-class-is-the-only-class" in problem and "ledger.ts:Ledger" in problem
        for problem in problems
    ), problems
    assert _terrain_problems(paired) == []


# --- the constructed negatives, through the declared runner ----------------------


def test_the_near_miss_is_a_symbol_the_typescript_file_defines(
    tmp_path: Path,
) -> None:
    """The negative no author has to write down, synthesised from the accepted
    file's own declarations: an accepted file paired with a symbol it defines and
    the key does not accept. Without the runner's reading of a `.ts` file there
    is no candidate at all, and the one negative that kills a grading test which
    reads the file and not the symbol could not be run."""
    task = keyed_task(tmp_path)

    assert _near_miss(task, answer_key(task)) == ("payroll.ts", "OVERTIME_AFTER_HOURS")


def test_the_four_synthesised_answers_grade_unresolved(tmp_path: Path) -> None:
    """The constructed negatives put through the real pipeline — the diff built
    by the live runner's own capture, graded exactly as replay grades a logged
    run — on a TypeScript task: a missing answer file, an empty one, a malformed
    one, and the accepted file paired with the near-miss all come out
    unresolved."""
    task = keyed_task(tmp_path)

    assert _discrimination_problems(task, timeout_s=GRADE_TIMEOUT_S) == []


# A held-out test of the task's own language, of the kind a keyed task may ship
# beside the harness-side half: resolution requires every half to pass, so an
# extra test can only make a task harder to resolve, never let a wrong answer
# through. With it, the negatives below are graded by both runners.
ANSWER_SHAPE_TEST = """\
import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";

test("the answer file is json", () => {
  assert.doesNotThrow(() => JSON.parse(fs.readFileSync("ANSWER.json", "utf8")));
});
"""


def test_the_negatives_are_graded_by_every_half_the_task_has(tmp_path: Path) -> None:
    """The dispatch where it is visible in the verdict: a keyed task shipping a
    held-out `.test.ts` beside the canonical Python half is graded by both
    runners, and each constructed negative is put to both — the empty and
    malformed answers failing under `node --test` as well, the near-miss failing
    where it has to, under the comparison that reads the key."""
    task = keyed_task(
        tmp_path, extra_grading={"answer_shape.test.ts": ANSWER_SHAPE_TEST}
    )

    assert [runner for runner, _ in task.grading_halves] == [PYTHON, TYPESCRIPT]
    assert _discrimination_problems(task, timeout_s=GRADE_TIMEOUT_S) == []


def test_a_grading_test_that_reads_the_file_and_not_the_symbol_is_caught(
    tmp_path: Path,
) -> None:
    """The load-bearing negative, in the direction that catches something: a
    held-out test asserting only that the answer names the accepted *file* is
    survived by the near-miss, and a verdict on that task would measure whether
    the agent named the right file rather than where it said the defect was."""
    task = keyed_task(
        tmp_path,
        answer_test=b'''\
"""A held-out test that reads the file and never the symbol."""

import json
from pathlib import Path


def test_the_answer_names_the_accepted_file():
    answer = json.loads(Path("ANSWER.json").read_text(encoding="utf-8"))
    assert answer["file"] == "payroll.ts"
''',
    )

    problems = _discrimination_problems(task, timeout_s=GRADE_TIMEOUT_S)

    assert any("OVERTIME_AFTER_HOURS" in problem for problem in problems), problems


def test_the_findings_key_negatives_grade_unresolved(tmp_path: Path) -> None:
    """The set-shaped key's own negatives on a TypeScript review task: every
    planted finding but one, the planted finding reported at a symbol of the
    right file the key registers on neither side, the rejected finding beside the
    planted ones and on its own — every one unresolved, and the positive that
    makes the alternatives real resolved."""
    task = review_task(tmp_path)

    assert _findings_discrimination_problems(task, timeout_s=GRADE_TIMEOUT_S) == []


def test_a_findings_test_that_asks_only_for_a_list_is_caught(tmp_path: Path) -> None:
    """The same negatives in the direction that catches something: a held-out
    test satisfied by any JSON list at all grades an answer that reported nothing
    resolved, which is a verdict measuring whether the agent wrote a file."""
    task = review_task(
        tmp_path,
        grading_test=b'''\
"""A held-out test that asks only for a list."""

import json
from pathlib import Path


def test_the_findings_are_a_list():
    assert isinstance(
        json.loads(Path("FINDINGS.json").read_text(encoding="utf-8")), list
    )
''',
    )

    problems = _findings_discrimination_problems(task, timeout_s=GRADE_TIMEOUT_S)

    assert any("grades resolved" in problem for problem in problems), problems


# --- the three existence-proof forms ---------------------------------------------


def test_a_typescript_locate_task_is_proved_by_its_partners_failure(
    tmp_path: Path,
) -> None:
    """`fault-location`'s form, run through the declared runner: the partner's
    held-out `.test.ts` fails on the starting repository the two share, and that
    failure is the proof. A partner whose tests pass there proves nothing, and a
    locate task with no partner at all has nothing saying there is a defect in it
    to find."""
    task = keyed_task(tmp_path)
    partner = write_partner(task)

    both = _existence_proof_problems(task, [task, partner], timeout_s=GRADE_TIMEOUT_S)

    assert both == []
    [alone] = _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S)
    assert LOCATE_ID in alone and "bug-fix" in alone


def test_a_partner_that_passes_on_the_pristine_repository_is_refused(
    tmp_path: Path,
) -> None:
    """The other direction of the same form, and the one that needs the partner
    actually run by `node --test`: its tests pass on the shared repository, so
    the locate task asks where a defect lives that its own partner cannot
    demonstrate."""
    task = keyed_task(tmp_path)
    partner = write_partner(task, grading_test=PARTNER_TEST_THAT_PROVES_NOTHING)

    [problem] = _existence_proof_problems(
        task, [task, partner], timeout_s=GRADE_TIMEOUT_S
    )

    assert PARTNER_ID in problem and "pass on the starting repository" in problem


def test_each_planted_finding_is_proved_in_both_directions(tmp_path: Path) -> None:
    """`code-review`'s form, run by the task's own runner against two trees: the
    proof fails on the starting repository, where the change under review ships
    applied, and passes on the author's corrected tree. The proof is a test of the
    task's language, so it is named the way that language names one — `.test.ts`
    and not `.py`, which the runner could not run at all."""
    task = review_task(tmp_path)
    [finding] = findings_key(task).accepted
    proof = task.proofs_dir / proof_test_name(finding, task.runner)

    assert proof.name == "payroll_ts_overtimePay.test.ts"
    assert not _proof_test_passes(
        task.repo_dir, proof, runner=task.runner, timeout_s=GRADE_TIMEOUT_S
    )
    assert _proof_test_passes(
        task.corrected_dir, proof, runner=task.runner, timeout_s=GRADE_TIMEOUT_S
    )
    assert _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S) == []


def test_a_proof_that_passes_on_the_starting_repository_is_refused(
    tmp_path: Path,
) -> None:
    """The starting repository ships the change under review already applied, so
    a proof that passes there says the finding is not a defect at all — and the
    verdict would fail every agent that declined to report it."""
    task = review_task(
        tmp_path,
        proofs={
            "payroll_ts_overtimePay.test.ts": (
                PROOF_THAT_PASSES_ON_THE_STARTING_REPOSITORY
            )
        },
    )

    problems = _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S)

    assert any(
        "passes on the starting repository" in problem for problem in problems
    ), problems


def test_a_planted_finding_with_no_proof_is_refused(tmp_path: Path) -> None:
    """A "finding" nothing demonstrates is a preference, and the verdict would
    grade every agent against it. The proof is looked up by the name the runner
    derives, so a `.py` proof beside a TypeScript task is a proof that is not
    there."""
    task = review_task(
        tmp_path, proofs={"test_payroll_ts_overtimePay.py": "assert True\n"}
    )

    problems = _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S)

    assert any("has no existence proof" in problem for problem in problems), problems


def test_an_accepted_location_that_does_not_resolve_is_refused(
    tmp_path: Path,
) -> None:
    """`codebase-comprehension`'s form, which runs nothing and reads the very
    rule the key is already held to — through the runner, so what "resolves"
    means is what a `.ts` file declares. There is no defect behind a locate-style
    comprehension task and so no partner that could fail on its repository: what
    has to exist is the behaviour the question asks after."""
    task = keyed_task(
        tmp_path / "missing",
        category="codebase-comprehension",
        accepted=[{"file": "payroll.ts", "symbol": "holidayPay"}],
    )
    present = keyed_task(tmp_path / "present", category="codebase-comprehension")

    problems = EXISTENCE_PROOFS["codebase-comprehension"].check(
        task, [task], GRADE_TIMEOUT_S
    )

    assert any("holidayPay" in problem for problem in problems), problems
    assert (
        EXISTENCE_PROOFS["codebase-comprehension"].check(
            present, [present], GRADE_TIMEOUT_S
        )
        == []
    )


# --- the two runs at the tail of the lint ----------------------------------------


def test_a_typescript_task_whose_tests_already_pass_is_caught(tmp_path: Path) -> None:
    """Must-fail-on-pristine, dispatched onto `node --test`: the verdict the lint
    reads here is the task's own runner's, so a TypeScript task whose held-out
    tests already pass before the agent touches it is caught rather than swept."""
    already = typescript_task(
        tmp_path / "already",
        control=True,
        grading={
            "calc.test.ts": """\
import test from "node:test";
import assert from "node:assert";

import { half } from "./calc.ts";

test("half halves", () => {
  assert.strictEqual(half(4), 2);
});
"""
        },
    )

    [problem] = lint_task_set([already])

    assert already.id in problem and "already pass on the pristine repo" in problem
    assert lint_task_set([typescript_task(tmp_path / "waiting", control=True)]) == []


# What the refactor fixture starts from: two conversions rounding separately,
# which is the duplication its structural test asks to have pulled out.
CALC = """\
export function pence(pounds: number): number {
  return Math.round(pounds * 100);
}

export function pounds(pence: number): number {
  return Math.round(pence) / 100;
}
"""

# The structural half: it fails on the pristine repository, which is what leaves
# the agent something to do.
SHAPE_TEST = """\
import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";

test("the two conversions round in one place", () => {
  const source = fs.readFileSync("calc.ts", "utf8");
  assert.strictEqual(source.split("Math.round").length - 1, 1);
});
"""

# The behaviour half: what must still work once the restructuring is done, and
# so what has to pass on the pristine repository already.
BEHAVIOUR_TEST = """\
import test from "node:test";
import assert from "node:assert";

import { pence, pounds } from "./calc.ts";

test("a price converts both ways", () => {
  assert.strictEqual(pence(1.5), 150);
  assert.strictEqual(pounds(150), 1.5);
});
"""


def refactor_task(root: Path, *, behaviour: str = BEHAVIOUR_TEST) -> Task:
    """A refactor task in TypeScript: a behaviour half named in the spec and a
    structural half beside it.

    Written here rather than through ticket 02's helper because a refactor task
    declares a `grading` block, which that helper's own `grading` parameter — the
    files of the grading directory — has no room for.
    """
    task_dir = root / "calc-round-in-one-place"
    (task_dir / REPO_DIR).mkdir(parents=True)
    (task_dir / GRADING_DIR).mkdir()
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "calc-round-in-one-place",
                "category": "refactor",
                "scale": "single-file",
                "surface": "application",
                "language": "typescript",
                "control": True,
                "prompt": "Round in one place in calc.ts, changing nothing else.\n",
                "grading": {"behaviour_tests": ["behaviour.test.ts"]},
            },
            sort_keys=False,
        )
    )
    (task_dir / REPO_DIR / "calc.ts").write_text(CALC)
    (task_dir / GRADING_DIR / "shape.test.ts").write_text(SHAPE_TEST)
    (task_dir / GRADING_DIR / "behaviour.test.ts").write_text(behaviour)
    return _load_task(task_dir)


def test_the_behaviour_half_of_a_refactor_task_is_run_by_its_own_runner(
    tmp_path: Path,
) -> None:
    """Behaviour-tests-pass-pristine, dispatched onto `node --test`: a refactor
    task must start from behaviour that already works, and what says whether it
    does is the task's own runner. Bent the one way it can be — a behaviour test
    that fails before anything is restructured — the lint says so."""
    working = refactor_task(tmp_path / "working")
    broken = refactor_task(
        tmp_path / "broken",
        behaviour=BEHAVIOUR_TEST.replace("pence(1.5), 150", "pence(1.5), 999"),
    )

    assert working.behaviour_test_paths == ("behaviour.test.ts",)
    assert lint_task_set([working]) == []
    [problem] = lint_task_set([broken])
    assert "the behaviour tests fail on the pristine repo" in problem


def test_the_harness_side_half_stays_pytests_whatever_the_task_declares(
    tmp_path: Path,
) -> None:
    """The other half of the dispatch, and the reason none of this is "run
    everything with the declared runner": the answer-key test and the hash gate
    are canonical Python found by pytest's glob, and a keyed TypeScript task is
    graded by both runners or by pytest alone where it ships no `.test.ts` of its
    own."""
    task = keyed_task(tmp_path)

    assert task.runner is TYPESCRIPT
    assert task.harness_test_paths == (ANSWER_TEST_FILE, HASH_GATE_FILE)
    assert task.language_test_paths == ()
    assert [runner for runner, _ in task.grading_halves] == [PYTHON]
