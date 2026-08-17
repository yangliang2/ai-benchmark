"""Fault-location tasks: the answer file, the accepted-answer key, the answer
comparison, and what a verdict makes of an answer (#49, #58).

The first action whose deliverable is prose rather than a code change, graded
without any new grading machinery. The task asks the agent to write a
structured answer file into the workdir; it lands in the workdir diff like any
other file the agent wrote; the existing pipeline copies the pristine
repository, applies the diff and overlays the held-out grading directory; and a
held-out grading test reads the answer file and compares it against the
accepted-answer key shipped inside that same directory. So the verdict stays
execution-verified rather than pattern-verified, and the provenance boundary
does not move: the run log still stores the agent's final message and the
verdict still never reads it.

Everything here is proved on a **fixture** task built into tmp_path, not on a
checked-in one. Round 4's real fault-location tasks come later, and a
production task shipped ahead of them would be swept as one — while the
mechanism they need has to be known to work first. The fixture is written from
scratch rather than cloned, because there is no fault-location seed to clone.

The diffs are built with git by the shared task-test helper, the way the live
runner builds one, and graded through `evaluate` — the same path replay grades
a logged run through — so an answer file reaches the verdict exactly as an
agent's would, and these tests cannot drift from what a live run would log.

What #58 adds is the half that makes a verdict mean something. Must-fail-on-
pristine cannot show it here — a pristine repository carries no answer file, so
the check is unconditionally satisfied, and a grading test that reads no key at
all passes it. So the lint runs answers it expects to *fail* through the real
pipeline and demands unresolved: four it constructs itself, plus the author's
`rejected` near-misses. Two fixtures below are the blind grading tests §36.1
caught, kept as tests of the lint that now catches them.
"""

import json
import shutil
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import TASKS, run_for, task_by_id, workdir_diff

from ai_benchmark import _answer
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    ANSWER_MODULE,
    ANSWER_TEST_FILE,
    HASH_GATE_EXEMPT,
    HASH_GATE_FILE,
    Answer,
    Task,
    _capture_workdir_diff,
    _commit_pristine,
    _defined_classes,
    _defined_symbols,
    _hash_gate_problems,
    _repo_file,
    _terrain_problems,
    answer_key,
    answer_module_source,
    answer_test_source,
    evaluate,
    hash_gate_source,
    is_control,
    is_keyed,
    lint_task_set,
    load_task_set,
    write_hash_gates,
)

FIXTURE_ID = "pricing-locate-the-rounding-fault"

# Where the fixture's prompt tells the agent to write its answer, and what the
# key declares. One declared path, named in both, is the whole of the contract
# between the prompt and the grading test.
ANSWER_PATH = "ANSWER.json"

# The defect: the tax is truncated by // rather than rounded to the nearest
# cent, so a 199-cent order taxed at 15% is billed 228 instead of 229. It sits
# in a method, so the author has two legitimately correct description levels to
# write down — the method and the class enclosing it.
#
# The fixture holds to the terrain rules the lint applies to every keyed task
# (#65), because a fixture that did not could not be used to prove anything
# else about the lint. `Coupon` is here so `Basket` is not the only class the
# file defines — an accepted class-level answer in a one-class module is
# determined by the filename alone — and `total_with_tax`'s docstring states
# what it is for in words the prompt does not use, so the prompt's own
# vocabulary is not one grep from the defective module.
PRICING = '''\
"""What an order costs."""


def line_total(unit_cents, quantity):
    """The cost of one order line, in cents."""
    return unit_cents * quantity


class Coupon:
    """A flat reduction, applied before tax."""

    def __init__(self, off):
        self.off = off

    def applied_to(self, amount):
        return max(0, amount - self.off)


class Basket:
    """The lines of one order, and what they come to."""

    def __init__(self):
        self.lines = []

    def add(self, unit_cents, quantity):
        self.lines.append((unit_cents, quantity))

    def subtotal(self):
        """Everything on the order, before tax."""
        return sum(line_total(unit, quantity) for unit, quantity in self.lines)

    def total_with_tax(self, tax_percent):
        """The subtotal with tax added, to the cent."""
        return self.subtotal() + self.subtotal() * tax_percent // 100
'''

# The module that *looks* responsible: it is where the tax rate lives and
# where the wrong number is returned from, and it is correct. The near-miss no
# lint can invent — the plausible wrong file — needs a second module to be
# written down at all, and its module-level TAX_PERCENT is what a fault in a
# constant, a dispatch table or a compiled pattern looks like. `Till` is here
# for terrain rather than for the defect: without a class of its own this
# module would leave "class", a word the prompt has to use to say what a
# symbol may be, appearing in the defective module and nowhere else.
CHECKOUT = '''\
"""Taking payment for an order."""

from pricing import Basket

TAX_PERCENT = 15


class Till:
    """Where an order is paid for."""

    def __init__(self, tax_percent=TAX_PERCENT):
        self.tax_percent = tax_percent

    def takings(self, orders):
        return sum(charge(order) for order in orders)


def charge(lines):
    """What to bill for these order lines, in cents."""
    basket = Basket()
    for unit_cents, quantity in lines:
        basket.add(unit_cents, quantity)
    return basket.total_with_tax(TAX_PERCENT)
'''

PROMPT = f"""\
A customer reports that a single 199-cent line taxed at 15% is billed 228
cents when it should be 229: the tax is truncated instead of being rounded to
the nearest cent. Say where the defect is. Do not fix it.

Write your answer to {ANSWER_PATH} in the repository root, as a JSON object
with "file" (the path, relative to the repository root) and "symbol" (the
function, class or method the defect lives in).
"""

# Every description level that is legitimately correct: the defective method,
# and the class it sits in. Never a line number — lines shift under any edit,
# and these two equally correct answers already land on different ones.
ACCEPTED: list[dict[str, object]] = [
    {"file": "pricing.py", "symbol": "Basket.total_with_tax"},
    {"file": "pricing.py", "symbol": "Basket"},
]

# The near-miss the lint cannot invent: the caller of the defective function,
# in the module that looks responsible because the rate lives there.
REJECTED: list[dict[str, object]] = [{"file": "checkout.py", "symbol": "charge"}]

# The nouns a prompt about what an order costs and a repository about what an
# order costs cannot help sharing — the half of the "unrevealing vocabulary"
# split that is a fact about this task's subject rather than about English, so
# the half a task declares for itself. Everything else the prompt says is
# distinctive, and the narrowing terrain rule holds it to appearing in more
# than the module the answer is in.
DOMAIN_NOUNS = ["basket", "cent", "cents", "line", "lines", "order", "orders", "tax"]

# Held out with the grading tests, and one line, because the comparison is
# `_answer.py` — shipped identically into every fault-location task's grading
# directory and read byte for byte by the lint. The canonical held-out test is
# itself shipped the same way now (#58): read straight off the package rather
# than duplicated here as a string, so this suite cannot drift from what
# `_answer_test_problems` requires a task to ship.
GRADING_TEST = answer_test_source().decode("utf-8")

# The grading test §36.1 caught: it never consults the key, so it grades a
# wrong answer — and an empty answer file — resolved.
BLIND_GRADING_TEST = '''\
"""A grading test that proves only that the agent wrote something."""

from pathlib import Path


def test_the_answer_names_an_accepted_location():
    assert (Path.cwd() / "ANSWER.json").is_file()
'''

# The floor of the two: a grading test that asserts nothing at all. It fails
# must-fail-on-pristine, so it is caught today — and it is here to show every
# negative the lint constructs, since it grades all of them resolved.
ALWAYS_RESOLVES_GRADING_TEST = '''\
"""A grading test that reads nothing and asserts nothing."""


def test_the_answer_names_an_accepted_location():
    assert True
'''

# The sloppier one: it reads the answer and checks the file, never the symbol,
# so every symbol in the right module grades resolved.
FILE_ONLY_GRADING_TEST = '''\
"""A grading test that checks the file and not the symbol."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))


def test_the_answer_names_an_accepted_location():
    answer = json.loads((WORKDIR / KEY["answer_path"]).read_text(encoding="utf-8"))
    assert answer["file"] in {entry["file"] for entry in KEY["accepted"]}
'''

# Fixture (A) from the adversarial review that found #58's gap: exact
# (file, symbol) set membership, never importing `_answer.py` at all. Every
# spelling `_answer.py` forgives — the bare method name, a leading "./", a
# trailing "()" — is refused by this test, and the pre-#58 lint was blind to
# it because the constructed negatives only ever demand that wrong answers
# fail, never that a *correctly* spelled right answer, in every spelling
# `_answer.py` forgives, passes.
EXACT_MEMBERSHIP_GRADING_TEST = '''\
"""A grading test that never imports _answer.py: exact set membership."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))
ACCEPTED = {(entry["file"], entry["symbol"]) for entry in KEY["accepted"]}


def test_the_answer_names_an_accepted_location():
    answer = json.loads((WORKDIR / KEY["answer_path"]).read_text(encoding="utf-8"))
    assert (answer.get("file"), answer.get("symbol")) in ACCEPTED
'''

# Fixture (B): memorises the lint's own constructed negatives (the near-miss
# it synthesises) and the key's own rejected pairs, and is blind to every
# other wrong location in the file — so an undeclared wrong symbol still
# grades resolved. Hardcodes the near-miss `_near_miss` deterministically
# synthesises for the fixture's default ACCEPTED set: `sorted(candidates)[0]`
# over pricing.py's unaccepted symbols is `Basket.__init__`.
MEMORIZED_NEGATIVES_GRADING_TEST = '''\
"""A grading test that memorises the lint's own negatives, and nothing else."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))
BLOCKED = {("pricing.py", "Basket.__init__")} | {
    (entry["file"], entry["symbol"]) for entry in KEY["rejected"]
}


def test_the_answer_names_an_accepted_location():
    answer_path = WORKDIR / KEY["answer_path"]
    assert answer_path.is_file(), "no answer file"
    text = answer_path.read_text(encoding="utf-8")
    assert text.strip(), "empty answer file"
    answer = json.loads(text)
    assert isinstance(answer, dict) and "file" in answer and "symbol" in answer, (
        "malformed answer file"
    )
    assert (answer["file"], answer["symbol"]) not in BLOCKED
'''

# Fixture (C): ships `_answer.py` byte-identical and imports `one_location`
# from it, but then does its own case-insensitive last-dotted-component match
# instead of calling `matches()` — precisely the drift §36.4 exists to close,
# and it lints clean under `_answer_module_problems` alone because the
# module's bytes are never touched.
CASE_INSENSITIVE_MATCH_GRADING_TEST = '''\
"""A grading test that imports _answer.py but re-implements the match."""

import json
from pathlib import Path

from _answer import one_location

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))


def test_the_answer_names_an_accepted_location():
    answer = json.loads((WORKDIR / KEY["answer_path"]).read_text(encoding="utf-8"))
    located = one_location(answer)
    assert located is not None
    file, symbol = located
    assert any(
        file.lower() == entry["file"].lower()
        and symbol.lower().rsplit(".", 1)[-1] == entry["symbol"].lower().rsplit(".", 1)[-1]
        for entry in KEY["accepted"]
    )
'''

# A deliberately inverted grading test, for the F11 regression below: it
# resolves exactly when the declared answer_path is missing, and fails
# otherwise. It exists only to observe whether a negative that is supposed to
# leave the declared path missing actually does.
RESOLVES_WHEN_ANSWER_MISSING_GRADING_TEST = '''\
"""Resolves exactly when the declared answer path is missing."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))


def test_the_answer_names_an_accepted_location():
    assert not (WORKDIR / KEY["answer_path"]).is_file()
'''


def write_fixture(
    root: Path,
    *,
    accepted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
    answer_path: str = ANSWER_PATH,
    prompt: str = PROMPT,
    grading_test: str = GRADING_TEST,
    task_id: str = FIXTURE_ID,
    repo_files: dict[str, str] | None = None,
    **spec: object,
) -> Path:
    """The fixture fault-location task, written into root ready to load.

    A coverage task rather than a knob experiment, so it declares itself a
    control: it claims nothing about difficulty, and saying so is the only way
    to say it outside the frozen 22.

    The answer comparison and the held-out grading test that asserts over it
    are both copied in rather than written here, because that is what a real
    task does: two owned files, shipped identically, read back byte for byte
    by the lint (`_answer_module_problems`, `_answer_test_problems`).

    It declares `domain_nouns` for the same reason a real keyed task does: the
    narrowing terrain rule holds every distinctive prompt word to appearing in
    more than the accepted module, and "cent", "line" and "tax" are words a
    prompt about what an order costs and a repository about what an order
    costs cannot help sharing.

    The hash gate is generated from the repository this function just wrote,
    by the very generator the CLI flag runs, because that is what a keyed task
    ships (#67) — a fixture without one could not be used to prove anything
    else about the lint. The tests that need a task *without* a sound gate
    break it afterwards, each in the one way it is about.

    That is also why a test wanting a third module in the repository passes it
    as `repo_files` rather than writing it in afterwards: the gate hashes the
    starting repository, so a file added after the gate was written is a file
    the gate does not name, and the task would carry a second, unrelated lint
    problem.
    """
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "grading").mkdir()
    fields: dict[str, object] = {
        "id": task_id,
        "category": "fault-location",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "domain_nouns": DOMAIN_NOUNS,
        "prompt": prompt,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    (task_dir / "repo" / "pricing.py").write_text(PRICING)
    (task_dir / "repo" / "checkout.py").write_text(CHECKOUT)
    for name, source in (repo_files or {}).items():
        (task_dir / "repo" / name).write_text(source)
    (task_dir / "grading" / ANSWER_TEST_FILE).write_text(grading_test)
    (task_dir / "grading" / ANSWER_MODULE).write_bytes(answer_module_source())
    (task_dir / "grading" / ANSWER_KEY_FILE).write_text(
        json.dumps(
            {
                "answer_path": answer_path,
                "accepted": ACCEPTED if accepted is None else accepted,
                "rejected": REJECTED if rejected is None else rejected,
            },
            indent=2,
        )
        + "\n"
    )
    (task_dir / "grading" / HASH_GATE_FILE).write_bytes(
        hash_gate_source(task_dir / "repo")
    )
    return task_dir


def fixture_task(root: Path, **overrides: Any) -> Task:
    write_fixture(root, **overrides)
    [task] = load_task_set(root)
    return task


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
    diff = workdir_diff(task, edit)
    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    return record.quality_value


# --- the task and its key ------------------------------------------------------


def test_a_fault_location_task_loads_carrying_its_accepted_answer_key(
    tmp_path: Path,
) -> None:
    task = fixture_task(tmp_path)
    key = answer_key(task)

    assert task.category == "fault-location"
    assert is_control(task)
    assert key.answer_path == ANSWER_PATH
    assert key.accepted == (
        Answer(file="pricing.py", symbol="Basket.total_with_tax"),
        Answer(file="pricing.py", symbol="Basket"),
    )
    assert key.rejected == (Answer(file="checkout.py", symbol="charge"),)


def test_the_key_ships_in_the_grading_directory_without_being_collected(
    tmp_path: Path,
) -> None:
    """It reaches the workdir by the overlay that copies that directory
    wholesale, and collection globs test files only, so nothing runs it."""
    task = fixture_task(tmp_path)

    assert (task.grading_dir / ANSWER_KEY_FILE).is_file()
    assert task.grading_test_paths == (ANSWER_TEST_FILE, HASH_GATE_FILE)


def test_an_accepted_answer_naming_a_line_number_fails_loudly(
    tmp_path: Path,
) -> None:
    """Lines shift under any edit, and the two accepted levels of this very
    fixture already land on different ones."""
    write_fixture(
        tmp_path,
        accepted=[{"file": "pricing.py", "symbol": "Basket", "line": 24}],
    )

    with pytest.raises(IngestError, match="line number"):
        load_task_set(tmp_path)


def test_a_fault_location_task_naming_behaviour_tests_fails_loudly(
    tmp_path: Path,
) -> None:
    """The behaviour/structural split stays reserved to refactor: a
    fault-location task exempting a grading test from the must-fail-on-pristine
    invariant would be exempting the one test that reads the answer."""
    write_fixture(
        tmp_path, grading={"behaviour_tests": [ANSWER_TEST_FILE]}
    )

    with pytest.raises(IngestError, match="behaviour_tests"):
        load_task_set(tmp_path)


def test_a_fault_location_task_without_a_key_fails_loudly(tmp_path: Path) -> None:
    task_dir = write_fixture(tmp_path)
    (task_dir / "grading" / ANSWER_KEY_FILE).unlink()

    with pytest.raises(IngestError, match=ANSWER_KEY_FILE):
        load_task_set(tmp_path)


# --- what the verdict makes of an answer ---------------------------------------


@pytest.mark.parametrize("symbol", ["Basket.total_with_tax", "Basket"])
def test_an_answer_naming_an_accepted_location_resolves(
    tmp_path: Path, symbol: str
) -> None:
    """Both description levels the author wrote down are correct answers: the
    defective method, and the class enclosing it."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers(naming("pricing.py", symbol))) == 1.0


def test_the_answer_file_travels_in_the_workdir_diff(tmp_path: Path) -> None:
    """No new grading seam: the deliverable is a file the agent wrote, so it
    reaches the grader through the artifact every v1 run already logs."""
    task = fixture_task(tmp_path)

    diff = workdir_diff(task, answers(naming("pricing.py", "Basket")))

    assert ANSWER_PATH in diff


def test_a_plausible_but_wrong_location_is_unresolved(tmp_path: Path) -> None:
    """The other arithmetic in the module, and not where the tax is lost."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers(naming("pricing.py", "line_total"))) == 0.0


def test_a_malformed_answer_file_is_unresolved(tmp_path: Path) -> None:
    """Prose where the structured answer the prompt asked for should be."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers("the tax rounding in Basket\n")) == 0.0


def test_a_missing_answer_file_is_unresolved(tmp_path: Path) -> None:
    """A run that did the reading and wrote its answer nowhere the task asked."""
    task = fixture_task(tmp_path)

    def leave_a_note(workdir: Path) -> None:
        (workdir / "NOTES.md").write_text("looked at pricing.py\n")

    assert verdict(task, leave_a_note) == 0.0


@pytest.mark.parametrize(
    "at",
    [
        pytest.param(f"report/{ANSWER_PATH}", id="different-directory"),
        pytest.param(ANSWER_PATH.lower(), id="different-case"),
    ],
)
def test_an_answer_written_at_another_path_is_unresolved(
    tmp_path: Path, at: str
) -> None:
    """The declared path is the contract the prompt states; a correct answer
    filed somewhere else is one the grader was never told to look for.

    Checked with a case-variant name (`answer.json` against a key declaring
    `ANSWER.json`) as well as a differently-shaped one, because the
    filesystem the sweeps run on (macOS) is case-insensitive: opening the
    declared path directly would resolve the case-variant answer and grade
    it 1.0 there, while the identical logged workdir diff replays to 0.0 on
    Linux. The grading test's own resolution has to stay case-exact on every
    platform for the verdict to be portable and the replay deterministic."""
    task = fixture_task(tmp_path)
    correct = naming("pricing.py", "Basket.total_with_tax")

    assert verdict(task, answers(correct, at=at)) == 0.0


def test_the_pristine_repository_carries_no_answer_file(tmp_path: Path) -> None:
    """Which is exactly why must-fail-on-pristine proves nothing here: with no
    answer file to read, the grading test fails whatever it asserts, so the
    invariant is unconditionally satisfied. What a clean lint means for this
    task is the negatives below, not this."""
    task = fixture_task(tmp_path)

    assert not (task.repo_dir / ANSWER_PATH).exists()
    assert lint_task_set([task]) == []


# --- the lint: what the accepted-answer key has to say --------------------------


def test_a_fault_location_task_with_an_empty_accepted_set_fails_to_load(
    tmp_path: Path,
) -> None:
    """`ai-bench run-live` (cli.py) loads a task set but never lints it, so
    the empty set has to be refused at load too, or an unsolvable key would
    reach a paid run."""
    with pytest.raises(IngestError, match="accepts no"):
        fixture_task(tmp_path, accepted=[])


def test_lint_rejects_an_empty_accepted_set(tmp_path: Path) -> None:
    """The same refusal, worded the same way, for a Task built without going
    through the loader's own layout check — `lint_task_set` takes an
    already-loaded list of tasks, so it has to catch this on its own rather
    than lean on `_check_task_layout` having already run."""
    task_dir = write_fixture(tmp_path, accepted=[])
    spec = yaml.safe_load((task_dir / "task.yaml").read_text())
    task = Task.model_validate(spec | {"directory": task_dir})

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "accepts no" in problem


def test_lint_rejects_a_key_naming_a_file_that_is_not_in_the_repo(
    tmp_path: Path,
) -> None:
    task = fixture_task(
        tmp_path, accepted=[{"file": "billing.py", "symbol": "Basket"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "billing.py" in problem
    assert "starting repository" in problem


def test_lint_rejects_a_key_naming_a_file_matching_only_by_case(
    tmp_path: Path,
) -> None:
    """`Path.is_file()` is case-insensitive on macOS, the platform the sweeps
    run on, so "pricing.PY" must not silently resolve to "pricing.py" — the
    grading test that later reads the agent's answer compares exact strings
    and would never match."""
    task = fixture_task(
        tmp_path, accepted=[{"file": "pricing.PY", "symbol": "Basket"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "pricing.PY" in problem
    assert "starting repository" in problem


def test_lint_rejects_a_key_naming_a_symbol_the_file_does_not_define(
    tmp_path: Path,
) -> None:
    """A renamed symbol or a typo: an answer no correct agent can give."""
    task = fixture_task(
        tmp_path, accepted=[{"file": "pricing.py", "symbol": "total_wth_tax"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "total_wth_tax" in problem
    assert "does not define" in problem


def test_lint_refuses_a_bare_method_name_where_a_qualified_spelling_exists(
    tmp_path: Path,
) -> None:
    """`matches()` is deliberately one-directional (#58, F4): a bare *answer*
    matches a qualified *accepted* symbol, never the reverse — making it
    symmetric would let `Other.total_with_tax` match a key that merely says
    `total_with_tax`, a false positive worse than the false negative it would
    fix. So the key itself has to use the qualified spelling wherever one
    exists: a key written bare (`total_with_tax`) makes the answer
    `total_with_tax` grade 1.0 while the most natural qualified spelling an
    agent could give, `Basket.total_with_tax`, grades 0.0 — and the
    near-miss the lint synthesises never surfaces it, because a symbol that
    already matches an accepted one is never a candidate. `_defined_symbols`
    yields both the bare and the qualified form for a nested definition, so
    the lint can tell the qualified spelling exists and require it."""
    task = fixture_task(
        tmp_path, accepted=[{"file": "pricing.py", "symbol": "total_with_tax"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "total_with_tax" in problem
    assert "Basket.total_with_tax" in problem


def test_lint_rejects_the_same_accepted_pair_named_twice(tmp_path: Path) -> None:
    """AC 2 calls the accepted set a *set*: a pair named twice claims nothing
    an unrepeated one would not."""
    write_fixture(
        tmp_path,
        accepted=[
            {"file": "pricing.py", "symbol": "Basket"},
            {"file": "pricing.py", "symbol": "Basket"},
        ],
    )

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert FIXTURE_ID in str(excinfo.value)
    assert "more than once" in str(excinfo.value)


def test_lint_rejects_a_prompt_that_never_names_the_answer_file(
    tmp_path: Path,
) -> None:
    """A task cannot be unsolvable because the agent was never told where to
    write: the answer file is the whole deliverable."""
    task = fixture_task(
        tmp_path,
        prompt=textwrap.dedent("""\
            A 199-cent line taxed at 15% is billed 228 cents when it should be
            229. Say where the defect is, and write down the file and the
            symbol it lives in. Do not fix it.
            """),
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and ANSWER_PATH in problem
    assert "prompt" in problem


def test_lint_rejects_a_prompt_where_the_path_is_only_a_substring(
    tmp_path: Path,
) -> None:
    """"ANSWER.json" is a substring of "MYANSWER.jsonx", but naming the
    substring buried inside a different filename is not naming the file — a
    plain substring test would let this lint clean while leaving the agent
    with no correct place to write."""
    task = fixture_task(
        tmp_path,
        prompt="Say where the defect is. Write your answer to MYANSWER.jsonx.\n",
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "prompt" in problem


# --- the lint: the declared answer_path itself -----------------------------


@pytest.mark.parametrize(
    "answer_path",
    [
        ANSWER_KEY_FILE,  # collides with the key itself
        ANSWER_TEST_FILE,  # collides with the held-out grading test
        "/tmp/abs.json",  # absolute, outside the workdir
        "../ESCAPE.json",  # escapes the workdir
    ],
)
def test_lint_rejects_an_answer_path_that_cannot_reach_the_verdict(
    tmp_path: Path, answer_path: str
) -> None:
    """Four spellings of answer_path that each produce an unsolvable task
    while lintng clean today: two collide with a file the grading overlay
    writes over the workdir (so the agent's answer is silently overwritten),
    and two never land in the workdir diff at all (so the agent's answer
    never reaches the grader). The prompt is made to name the path exactly,
    so the only problem reported is the one this test targets."""
    task = fixture_task(
        tmp_path,
        answer_path=answer_path,
        prompt=f"Say where the defect is. Write your answer to {answer_path}.\n",
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem


def test_lint_accepts_an_answer_path_that_is_safe(tmp_path: Path) -> None:
    """The other direction of the four refusals above: a relative path inside
    the workdir that names neither the key nor a grading test lints clean."""
    task = fixture_task(
        tmp_path,
        answer_path="report/ANSWER.json",
        prompt="Say where the defect is. Write your answer to report/ANSWER.json.\n",
    )

    assert lint_task_set([task]) == []


# --- the answer comparison: one owned module, copied ---------------------------


def test_the_answer_comparison_ships_into_the_grading_directory(
    tmp_path: Path,
) -> None:
    """The comparison is the half of the verdict that discriminates, so it is
    owned rather than hand-copied six times: `grading/_answer.py` is the
    project's own module, byte for byte, and the held-out test is a one-line
    assertion over it."""
    task = fixture_task(tmp_path)

    assert (task.grading_dir / ANSWER_MODULE).read_bytes() == answer_module_source()
    assert lint_task_set([task]) == []


def test_the_comparison_and_the_loader_name_the_same_key_file() -> None:
    """The comparison has to be self-contained — it runs with the project
    unimportable — so it carries its own spelling of the key's filename. The
    two agreeing is what makes the file the lint reads and the file the
    verdict reads one file."""
    assert _answer.KEY_FILE == ANSWER_KEY_FILE


def test_lint_rejects_a_grading_directory_without_the_answer_comparison(
    tmp_path: Path,
) -> None:
    task_dir = write_fixture(tmp_path)
    (task_dir / "grading" / ANSWER_MODULE).unlink()
    [task] = load_task_set(tmp_path)

    problems = lint_task_set([task])

    assert any(FIXTURE_ID in problem and ANSWER_MODULE in problem for problem in problems)


def test_lint_rejects_an_edited_copy_of_the_answer_comparison(
    tmp_path: Path,
) -> None:
    """Copies drift silently, which is the stated reason the family lint reads
    a family's repositories and grading suites byte for byte. A copy that
    forgave case, or stopped reading the symbol, would grade every task that
    shipped it differently from every task that did not."""
    task_dir = write_fixture(tmp_path)
    shipped = task_dir / "grading" / ANSWER_MODULE
    shipped.write_text(
        shipped.read_text(encoding="utf-8").replace(
            "if file != accepted_file:", "if file.lower() != accepted_file.lower():"
        ),
        encoding="utf-8",
    )
    [task] = load_task_set(tmp_path)

    problems = lint_task_set([task])

    assert any(FIXTURE_ID in problem and ANSWER_MODULE in problem for problem in problems)


# --- the held-out grading test itself: one owned file, copied (#58 F1-F3) ------
#
# #49 shipped `_answer.py` byte for byte and left the grading test that reads
# it a string a task author would hand-write. Nothing then bound a task's
# *grading test* to `_answer.py`: three fixtures below, all linting clean
# under #49's own checks, prove it — (A) never imports `_answer.py` at all,
# (B) imports nothing and simply memorises the lint's own negatives, and (C)
# imports `_answer.py`'s `one_location()` but reimplements the match its own,
# looser way. All three ship `_answer.py` byte-identical, so
# `_answer_module_problems` alone has nothing to say about any of them.


def test_lint_rejects_a_grading_directory_without_the_held_out_test(
    tmp_path: Path,
) -> None:
    task_dir = write_fixture(tmp_path)
    (task_dir / "grading" / ANSWER_TEST_FILE).unlink()
    # A task still has to ship at least one test_*.py to load at all; this
    # one is unrelated to the held-out test and just has to fail pristine.
    (task_dir / "grading" / "test_placeholder.py").write_text(
        "def test_placeholder():\n    assert False\n"
    )
    [task] = load_task_set(tmp_path)

    problems = lint_task_set([task])

    assert any(
        FIXTURE_ID in problem and ANSWER_TEST_FILE in problem for problem in problems
    )


@pytest.mark.parametrize(
    ("grading_test", "fixture_name"),
    [
        pytest.param(EXACT_MEMBERSHIP_GRADING_TEST, "A", id="A-exact-set-membership"),
        pytest.param(
            MEMORIZED_NEGATIVES_GRADING_TEST, "B", id="B-memorised-negatives"
        ),
        pytest.param(
            CASE_INSENSITIVE_MATCH_GRADING_TEST, "C", id="C-reimplemented-match"
        ),
    ],
)
def test_lint_refuses_a_hand_written_grading_test_even_with_answer_py_intact(
    tmp_path: Path, grading_test: str, fixture_name: str
) -> None:
    """The three fixtures from the adversarial review that found #58's gap,
    reconstructed: each ships `grading/_answer.py` byte-identical and
    `grading/accepted-answer.json` untouched, and each lints clean under
    #49's checks alone because nothing there ever asked whether the grading
    *test* consults `_answer.py`. #58's fix is `_answer_test_problems`: the
    held-out test is itself shipped canonically and read back byte for byte,
    so any hand-written replacement — however it is broken — is refused by
    that single check, independent of what `_discrimination_problems` would
    or would not have caught."""
    task = fixture_task(tmp_path, grading_test=grading_test)

    problems = lint_task_set([task])

    assert problems and all(FIXTURE_ID in problem for problem in problems)
    assert any(ANSWER_TEST_FILE in problem for problem in problems), fixture_name


# --- what counts as the same answer --------------------------------------------


@pytest.mark.parametrize(
    ("file", "symbol"),
    [
        pytest.param("pricing.py", "Basket.total_with_tax", id="as-written"),
        pytest.param("./pricing.py", "Basket.total_with_tax", id="leading-dot-slash"),
        pytest.param(" pricing.py\n", " Basket \n", id="surrounding-whitespace"),
        pytest.param("pricing.py", "Basket.total_with_tax()", id="trailing-parens"),
        pytest.param("pricing.py", "total_with_tax", id="bare-symbol"),
        pytest.param("pricing.py", "total_with_tax()", id="bare-symbol-called"),
    ],
)
def test_an_answer_spelled_differently_still_resolves(
    tmp_path: Path, file: str, symbol: str
) -> None:
    """What the comparison forgives is spelling, not identity. Every one of
    these graded unresolved on #49's fixture, and over six tasks that is a
    false-negative floor that would read as models being bad at locating
    faults."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers(naming(file, symbol))) == 1.0


@pytest.mark.parametrize(
    ("file", "symbol"),
    [
        pytest.param("Pricing.py", "Basket", id="file-case"),
        pytest.param("pricing.py", "basket", id="symbol-case"),
        pytest.param("pricing.py", "BASKET.TOTAL_WITH_TAX", id="qualified-case"),
    ],
)
def test_a_case_variant_answer_is_unresolved(
    tmp_path: Path, file: str, symbol: str
) -> None:
    """Python is case-sensitive, and a case-insensitive match on the grading
    side would make a verdict depend on the filesystem the grader ran on."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers(naming(file, symbol))) == 0.0


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            json.dumps(
                [
                    {"file": "pricing.py", "symbol": "Basket.total_with_tax"},
                    {"file": "pricing.py", "symbol": "line_total"},
                ]
            ),
            id="a-list-of-answers",
        ),
        pytest.param(
            json.dumps({"file": ["pricing.py"], "symbol": ["Basket"]}),
            id="list-valued-fields",
        ),
        pytest.param(
            json.dumps(
                {
                    "file": "pricing.py",
                    "symbol": "Basket.total_with_tax",
                    "alternatives": [{"file": "pricing.py", "symbol": "line_total"}],
                }
            ),
            id="a-second-guess-beside-the-first",
        ),
        pytest.param(json.dumps({"file": "pricing.py"}), id="no-symbol"),
        pytest.param(json.dumps("pricing.py: Basket"), id="a-bare-string"),
    ],
)
def test_an_answer_naming_other_than_one_pair_is_unresolved(
    tmp_path: Path, payload: str
) -> None:
    """A task measures whether the agent located the fault, so a shotgun of
    every plausible location would be breadth rewarded as accuracy — including
    the one that names a correct location first and hedges after it."""
    task = fixture_task(tmp_path)

    assert verdict(task, answers(payload)) == 0.0


def test_an_answer_carrying_flat_prose_beside_the_pair_still_resolves(
    tmp_path: Path,
) -> None:
    """The other direction of the rule above: refusing more than one guess is
    refused by shape — a list or a nested object — not by refusing any field
    the prompt did not ask for. An agent that writes its reasoning beside the
    answer has still named exactly one location."""
    task = fixture_task(tmp_path)
    payload = json.dumps(
        {
            "file": "pricing.py",
            "symbol": "Basket.total_with_tax",
            "reason": "the tax is truncated by // instead of rounded",
        }
    )

    assert verdict(task, answers(payload)) == 1.0


def test_a_module_level_constant_can_be_keyed(tmp_path: Path) -> None:
    """A `def` and a `class` were the only symbols #49 could see, so a fault in
    a constant, a dispatch table or a compiled pattern was unkeyable — which
    would have quietly steered a task whose defect is a wrong key in a lookup
    into being written about something else."""
    task = fixture_task(
        tmp_path,
        accepted=[{"file": "checkout.py", "symbol": "TAX_PERCENT"}],
        # A rejected file distinct from the accepted one, as F5 requires: the
        # default REJECTED also names checkout.py, which would otherwise be
        # the only rejected file and collide with the accepted set here.
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
    )

    assert lint_task_set([task]) == []
    assert verdict(task, answers(naming("checkout.py", "TAX_PERCENT"))) == 1.0


def test_an_accepted_answer_naming_a_file_with_no_symbol_is_refused(
    tmp_path: Path,
) -> None:
    """The other direction of what can be named: on repositories this small a
    bare filename is barely a location, and would resolve for an agent that
    located nothing."""
    write_fixture(tmp_path, accepted=[{"file": "pricing.py"}])

    with pytest.raises(IngestError, match="no symbol"):
        load_task_set(tmp_path)


# --- the lint: negatives run through the real pipeline -------------------------


def test_lint_runs_four_constructed_negatives_and_the_authors_rejected_set(
    tmp_path: Path,
) -> None:
    """What a fault-location task has to earn: four answers the lint builds
    itself, each required to grade unresolved through the real pipeline, plus
    every near-miss the author wrote down. Shown on a grading test that grades
    everything resolved, so each negative reports separately."""
    task = fixture_task(tmp_path, grading_test=ALWAYS_RESOLVES_GRADING_TEST)

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    for negative in (
        "no answer file",
        "an empty answer file",
        "a malformed answer file",
        "does not accept",
        "rejected answer",
    ):
        assert any(negative in problem for problem in problems), negative


def test_lint_refuses_a_grading_test_that_never_consults_the_key(
    tmp_path: Path,
) -> None:
    """§36.1's first fixture: `assert ANSWER.json.is_file()` graded a wrong
    answer resolved and an empty answer file too, while linting clean and
    passing every gate the corpus had — because a pristine repository carries
    no answer file, so must-fail-on-pristine is satisfied by anything."""
    task = fixture_task(tmp_path, grading_test=BLIND_GRADING_TEST)

    problems = lint_task_set([task])

    assert problems and all(FIXTURE_ID in problem for problem in problems)
    assert any("empty" in problem for problem in problems)


def test_lint_refuses_a_grading_test_that_checks_the_file_but_not_the_symbol(
    tmp_path: Path,
) -> None:
    """The sloppier one, and what the synthesised near-miss exists to kill: an
    accepted file paired with a symbol the key does not accept."""
    task = fixture_task(tmp_path, grading_test=FILE_ONLY_GRADING_TEST)

    problems = lint_task_set([task])

    assert problems and all(FIXTURE_ID in problem for problem in problems)
    assert any("does not accept" in problem for problem in problems)


def test_lint_requires_a_non_empty_rejected_set(tmp_path: Path) -> None:
    """The near-miss no lint can invent is the author's to write down: the
    plausible wrong file, the caller of the defective function, the module
    that looks responsible."""
    task = fixture_task(tmp_path, rejected=[])

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "rejected" in problem


def test_lint_requires_a_rejected_answer_naming_a_file_not_already_accepted(
    tmp_path: Path,
) -> None:
    """(#58, F5) `rejected` being non-empty is not the same as it saying
    anything: §36.3 and CONTEXT.md both name the near-miss the lint cannot
    invent as the plausible wrong *file*, the one place the design spends
    author judgement. A rejected set confined to files the accepted set
    already names never supplies it, however many entries it carries — here,
    a second symbol in the very file the answer already lives in — so the
    lint refuses it."""
    task = fixture_task(
        tmp_path,
        rejected=[{"file": "pricing.py", "symbol": "Basket.add"}],
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "pricing.py" in problem


def test_lint_refuses_a_rejected_answer_equal_to_the_synthesised_near_miss(
    tmp_path: Path,
) -> None:
    """(#58, F5) The lint already synthesises one negative from the accepted
    set alone (`_near_miss`) — an accepted file paired with a symbol it
    defines and the key does not accept. An author who writes that exact
    pair down as `rejected` has spent their judgement on a symbol the lint
    already checks for nothing, not on the one thing only the author can
    supply: the plausible wrong file. A second, genuinely distinct rejected
    file is included so this fires in isolation from the "no distinct file"
    check above."""
    task = fixture_task(
        tmp_path,
        rejected=[
            {"file": "pricing.py", "symbol": "Basket.__init__"},
            {"file": "checkout.py", "symbol": "charge"},
        ],
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "Basket.__init__" in problem


def test_lint_refuses_a_rejected_answer_the_comparison_actually_accepts(
    tmp_path: Path,
) -> None:
    """Every rejected answer is run through the same pipeline and required to
    grade unresolved, so a near-miss the comparison in fact accepts — spelled
    here with the leading "./" `_answer.py` forgives on the file half, naming
    the very symbol that is accepted — is caught rather than believed.

    Spelled with "./pricing.py" rather than the bare method name: F4 now
    statically refuses a *bare* rejected symbol wherever a qualified spelling
    exists, before this ever reaches the pipeline, so this fixture exercises
    a spelling F4 has nothing to say about and only the real pipeline can
    catch — the file half of the normalisation, not the symbol half."""
    task = fixture_task(
        tmp_path,
        rejected=[{"file": "./pricing.py", "symbol": "Basket.total_with_tax"}],
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "Basket.total_with_tax" in problem


def test_lint_refuses_a_rejected_answer_that_is_not_in_the_repository(
    tmp_path: Path,
) -> None:
    """A near-miss has to be a location the agent could plausibly have given:
    an answer naming a file the repository does not hold grades unresolved for
    a reason that says nothing about the grading test."""
    task = fixture_task(
        tmp_path, rejected=[{"file": "billing.py", "symbol": "charge"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "billing.py" in problem
    assert "starting repository" in problem


def test_lint_reports_when_it_cannot_construct_the_near_miss(
    tmp_path: Path,
) -> None:
    """The synthesised near-miss is the load-bearing negative, so a key whose
    accepted set leaves no unaccepted symbol in the file it names has to say
    so rather than quietly running one check fewer."""
    write_fixture(
        tmp_path,
        accepted=[{"file": "tiny.py", "symbol": "only"}],
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
        repo_files={"tiny.py": "def only():\n    return 1\n"},
    )
    [task] = load_task_set(tmp_path)

    problems = lint_task_set([task])

    assert any(FIXTURE_ID in problem and "near-miss" in problem for problem in problems)


def test_near_miss_skips_a_fully_accepted_file_and_tries_the_next(
    tmp_path: Path,
) -> None:
    """(#58, F15) `_near_miss` walks the accepted files in order and moves on
    when one leaves no unaccepted symbol behind — only the all-files-
    exhausted case (above) was covered before. tiny.py's one symbol is
    itself accepted, so the near-miss has to come from pricing.py, the
    second accepted file."""
    task_dir = write_fixture(
        tmp_path,
        accepted=[
            {"file": "tiny.py", "symbol": "only"},
            {"file": "pricing.py", "symbol": "Basket.total_with_tax"},
            {"file": "pricing.py", "symbol": "Basket"},
        ],
        rejected=[{"file": "checkout.py", "symbol": "charge"}],
        repo_files={"tiny.py": "def only():\n    return 1\n"},
    )
    [task] = load_task_set(tmp_path)

    assert lint_task_set([task]) == []


def test_the_missing_answer_negative_leaves_the_declared_path_missing_even_when_it_is_named_notes_md(
    tmp_path: Path,
) -> None:
    """(#58, F11) The "wrote no answer file at all" negative used to write its
    note to a fixed NOTES.md. A task that happens to declare NOTES.md as its
    own answer_path would then have this negative *create* the declared
    answer file rather than leave it missing, collapsing it into a second
    "malformed answer file" negative with nothing reporting the collapse.

    Proved with a deliberately inverted grading test that resolves exactly
    when the declared path is *missing*: unless this negative genuinely
    leaves the declared path missing, the lint has no way to catch this test
    wrongly resolving, and would report the task clean."""
    task = fixture_task(
        tmp_path,
        answer_path="NOTES.md",
        prompt="Say where the defect is. Write your answer to NOTES.md.\n",
        grading_test=RESOLVES_WHEN_ANSWER_MISSING_GRADING_TEST,
    )

    problems = lint_task_set([task])

    assert any(
        FIXTURE_ID in problem and "no answer file" in problem for problem in problems
    ), problems


# --- the lint: the three terrain rules, and the waiver (#65) ----------------
#
# Terrain is what makes locating a fault work rather than a grep, and round 4
# proved it per task: the same three assertions, hand-copied into six suites,
# so that a seventh keyed task inherited none of them. They are rules of the
# task-set lint here, applied to every task carrying an accepted-answer key —
# each caught in both directions below, on a fixture that is otherwise
# lint-clean, so that what fires is the rule under test and nothing else.

# A prompt naming the accepted class outright. "Basket" is a declared domain
# noun, so the narrowing rule has nothing to say about it and the location
# rule fires alone.
NAMES_THE_ACCEPTED_CLASS_PROMPT = (
    "The defect is in Basket. Say where it lives, and do not fix it.\n"
    "Write your answer to ANSWER.json.\n"
)

# A prompt naming a *rejected* location: the near-miss the key exists to
# refuse, handed over in the prompt.
NAMES_A_REJECTED_LOCATION_PROMPT = (
    "Something is wrong with what we bill, and charge is not where it is.\n"
    "Say where the defect lives. Write your answer to ANSWER.json.\n"
)

# "subtotal" is a word of pricing.py and of no other module in the fixture
# repository, so a prompt that uses it is one grep from the answer.
NARROWING_PROMPT = (
    "A subtotal is coming out wrong. Say where the defect lives, and do not\n"
    "fix it. Write your answer to ANSWER.json.\n"
)


def test_lint_refuses_a_prompt_naming_an_accepted_location(tmp_path: Path) -> None:
    """Terrain rule 1, the accepted half: locating the fault is the whole
    deliverable, so a prompt naming a location out of the key hands the agent
    the reading it was supposed to do. Convention until now — six suites
    asserted it by hand — and mechanical here."""
    task = fixture_task(tmp_path, prompt=NAMES_THE_ACCEPTED_CLASS_PROMPT)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'Basket'" in problem
    assert "prompt-names-a-key-location" in problem


def test_lint_refuses_a_prompt_naming_a_rejected_location(tmp_path: Path) -> None:
    """The same rule from the other side, and why it reads both halves of the
    key: a prompt that names the plausible wrong file has told the agent which
    near-miss to avoid, which makes the task unfair in the agent's favour just
    as surely as naming the answer does."""
    task = fixture_task(tmp_path, prompt=NAMES_A_REJECTED_LOCATION_PROMPT)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'charge'" in problem
    assert "rejected" in problem


def test_the_declared_answer_path_is_never_read_as_bait(tmp_path: Path) -> None:
    """The prompt is *required* to name the answer path, so the location rule
    has to exempt it: a task whose key happened to name a file spelled like
    its own answer_path would otherwise be caught coming and going, told to
    name the path by one rule and not to name it by another."""
    task = fixture_task(tmp_path)

    assert ANSWER_PATH in task.prompt
    assert lint_task_set([task]) == []


def test_lint_refuses_a_prompt_word_that_narrows_to_the_accepted_module(
    tmp_path: Path,
) -> None:
    """Terrain rule 2: a content word of the prompt that appears in the
    accepted module and in no other is one grep from the answer, and the task
    then measures whether the agent greps rather than whether it locates."""
    task = fixture_task(tmp_path, prompt=NARROWING_PROMPT)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'subtotal'" in problem
    assert "pricing.py:" in problem


def test_a_declared_domain_noun_does_not_narrow(tmp_path: Path) -> None:
    """The other direction, and what `domain_nouns` is for: "cent", "line" and
    "tax" all appear in pricing.py and nowhere else in this repository, and a
    prompt about what an order costs cannot avoid them. Declared, they are
    vocabulary rather than bait — and the rule is still live for everything
    else the same prompt says."""
    task = fixture_task(tmp_path)

    assert {"cent", "line", "tax"} <= set(task.domain_nouns)
    assert lint_task_set([task]) == []


def test_the_narrowing_rule_reads_only_the_keyed_tasks_own_prompt(
    tmp_path: Path,
) -> None:
    """Round 4's suites computed prompt vocabulary over both members of a
    locate/fix pair, which made a word the *fix* prompt used count as bait in
    the locate task that never said it. The agent solving a task sees that
    task's prompt, so that is the rule's input: a sibling task in the same set
    whose prompt narrows is a problem reported against the sibling, and
    changes nothing about this one."""
    write_fixture(tmp_path)
    write_fixture(tmp_path, task_id="pricing-fix-the-rounding-fault",
                  prompt=NARROWING_PROMPT)
    tasks = load_task_set(tmp_path)

    problems = lint_task_set(tasks)

    assert {task.id for task in tasks} == {
        FIXTURE_ID, "pricing-fix-the-rounding-fault"
    }
    assert not any(problem.startswith(f"{FIXTURE_ID}:") for problem in problems)
    assert any(
        problem.startswith("pricing-fix-the-rounding-fault:") and "'subtotal'" in problem
        for problem in problems
    )


def test_lint_refuses_an_accepted_class_that_is_the_only_class_in_its_file(
    tmp_path: Path,
) -> None:
    """Terrain rule 3: an agent electing to answer at class level answers with
    the class, and where the module defines exactly one, that answer is
    determined by the filename alone — one grep to the file, the only class
    there, resolved, with the defective method never read."""
    write_fixture(
        tmp_path,
        accepted=[
            {"file": "lone.py", "symbol": "Lone"},
            {"file": "lone.py", "symbol": "Lone.slip"},
        ],
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
        repo_files={
            "lone.py": "class Lone:\n"
            "    def slip(self):\n"
            "        return 1\n"
            "\n"
            "    def other(self):\n"
            "        return 2\n"
        },
    )
    [task] = load_task_set(tmp_path)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "lone.py:Lone" in problem
    assert "accepted-class-is-the-only-class" in problem


def test_an_accepted_class_chosen_from_several_lints_clean(tmp_path: Path) -> None:
    """The other direction: pricing.py defines `Coupon` beside `Basket`, so
    telling them apart takes reading both, and the accepted class level is a
    location rather than a restatement of the filename."""
    task = fixture_task(tmp_path)

    assert Answer(file="pricing.py", symbol="Basket") in answer_key(task).accepted
    assert _defined_classes(PRICING) == {"Basket", "Coupon"}
    assert lint_task_set([task]) == []


def test_a_terrain_waiver_silences_exactly_what_it_names(tmp_path: Path) -> None:
    """The waiver is the only sanctioned way past a terrain rule, and it
    applies only to what it names: the word it covers stops being reported and
    nothing else does."""
    task = fixture_task(
        tmp_path,
        prompt=NARROWING_PROMPT,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": ["subtotal"],
            "reason": "the repository states what it computes in the one word "
                      "the symptom has to be reported in",
        }],
    )

    assert lint_task_set([task]) == []


def test_a_terrain_waiver_does_not_silence_a_word_it_does_not_name(
    tmp_path: Path,
) -> None:
    """What makes a waiver a declaration rather than a mute button: waiving
    one word leaves the rule live for every other, and the waiver that missed
    is itself reported for naming something the rule never fired on."""
    task = fixture_task(
        tmp_path,
        prompt=NARROWING_PROMPT,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": ["coupon"],
            "reason": "a word this prompt does not in fact use",
        }],
    )

    problems = lint_task_set([task])

    assert any("'subtotal'" in problem for problem in problems)
    assert any("'coupon'" in problem and "does not fire" in problem for problem in problems)


def test_a_waiver_naming_a_rule_that_did_not_fire_is_a_lint_problem(
    tmp_path: Path,
) -> None:
    """A waiver cannot rot silently once the terrain it apologised for has
    been improved: the fixture's prompt never says "subtotal", so the waiver
    covering it silences nothing and says so."""
    task = fixture_task(
        tmp_path,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": ["subtotal"],
            "reason": "terrain that was improved out from under this waiver",
        }],
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'subtotal'" in problem
    assert "does not fire" in problem


def test_a_waiver_naming_an_unknown_rule_fails_to_load(tmp_path: Path) -> None:
    """The rules are named one by one so a waiver names exactly one of them: a
    misspelled rule refuses to load rather than waiving nothing quietly."""
    write_fixture(
        tmp_path,
        terrain_waiver=[{
            "rule": "prompt-word-narrows",
            "covers": ["subtotal"],
            "reason": "misspelled",
        }],
    )

    with pytest.raises(IngestError, match="terrain_waiver"):
        load_task_set(tmp_path)


def test_a_waiver_covering_nothing_fails_to_load(tmp_path: Path) -> None:
    """A waiver applies only to what it names, so one naming nothing is a
    reason written down beside a rule that is still firing."""
    write_fixture(
        tmp_path,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": [],
            "reason": "covers nothing at all",
        }],
    )

    with pytest.raises(IngestError, match="covers nothing"):
        load_task_set(tmp_path)


def test_one_rule_cannot_carry_two_waivers(tmp_path: Path) -> None:
    """Two waivers for one rule are two reasons for one exception, with
    nothing saying which covers what."""
    write_fixture(
        tmp_path,
        terrain_waiver=[
            {
                "rule": "prompt-word-narrows-to-the-accepted-module",
                "covers": ["subtotal"],
                "reason": "one reason",
            },
            {
                "rule": "prompt-word-narrows-to-the-accepted-module",
                "covers": ["coupon"],
                "reason": "another reason",
            },
        ],
    )

    with pytest.raises(IngestError, match="waived more than once"):
        load_task_set(tmp_path)


def test_the_round_four_waiver_is_declared_where_the_rule_fires() -> None:
    """The one declared exception round 4 carried, as it reads now: a waiver
    naming the two words the locate prompt actually produces. "already" was
    the *fix* member's word — round 4 computed the set over both prompts —
    and under a per-task rule a waiver naming it would itself be a lint
    problem, so it survives in the reason and not in `covers`."""
    task = task_by_id("paperround-locate-the-carried-over-count")

    [waiver] = task.terrain_waiver

    assert waiver.rule == "prompt-word-narrows-to-the-accepted-module"
    assert waiver.covers == ("ask", "every ask")
    assert "already" in waiver.reason
    assert _terrain_problems(task) == []


# --- the hash gate: the repository is as it was handed over (#67) -----------


def gate_of(task: Task) -> Path:
    return task.grading_dir / HASH_GATE_FILE


def test_a_keyed_fixture_ships_a_generated_gate_and_lints_clean(
    tmp_path: Path,
) -> None:
    """What the rest of this section is measured against: the gate a keyed
    task ships is what the generator produces from its `repo/` bytes, and the
    lint has nothing to say about it."""
    task = fixture_task(tmp_path)

    assert is_keyed(task)
    assert gate_of(task).read_bytes() == hash_gate_source(task.repo_dir)
    assert _hash_gate_problems(task) == []


def test_the_checked_in_gates_are_exactly_what_the_generator_writes() -> None:
    """Generation reproduces what is on disk, over the whole keyed corpus.

    This is the claim that lets the round-4 script the gates were written by
    be retired: the CLI flag is not a second generator that happens to agree
    with the checked-in files, it is the one generator. Read over every keyed
    task rather than over the four that were gated by hand, so a keyed task
    authored tomorrow is covered by it without this test being edited.
    """
    keyed = [
        task
        for task in load_task_set(TASKS)
        if is_keyed(task) and task.id not in HASH_GATE_EXEMPT
    ]

    assert keyed
    for task in keyed:
        assert gate_of(task).read_bytes() == hash_gate_source(task.repo_dir), task.id


def test_regenerating_the_checked_in_corpus_writes_nothing() -> None:
    """The no-op that makes the flag safe to run: over an unchanged corpus the
    generator rewrites no file, so its result in a diff is exactly what
    changed and nothing else."""
    assert write_hash_gates(load_task_set(TASKS)) == []


def test_the_lint_reports_a_keyed_task_that_ships_no_gate(tmp_path: Path) -> None:
    """The hole this closes: round 4 gated the four tasks whose author
    remembered, and a fifth keyed task inherited nothing."""
    task = fixture_task(tmp_path)
    gate_of(task).unlink()

    [problem] = _hash_gate_problems(task)

    assert task.id in problem
    assert HASH_GATE_FILE in problem


def test_the_lint_reports_a_digest_that_no_longer_describes_the_repository(
    tmp_path: Path,
) -> None:
    """The silent failure the gate is otherwise wide open to: `repo/` edited
    after the gate was written leaves the task lint-clean and its reference
    solution resolving, while grading every real run unresolved."""
    task = fixture_task(tmp_path)
    edited = task.repo_dir / "checkout.py"
    edited.write_text(edited.read_text() + "\n# a later tidy-up\n")

    [problem] = _hash_gate_problems(task)

    assert task.id in problem
    assert "checkout.py" in problem


def test_the_lint_reports_a_repository_file_the_gate_does_not_hash(
    tmp_path: Path,
) -> None:
    """The other direction, which correct digests say nothing about: a file
    added to `repo/` after the gate was written is one an agent may edit and
    still grade resolved."""
    task = fixture_task(tmp_path)
    (task.repo_dir / "receipts.py").write_text('"""What a till prints."""\n')

    [problem] = _hash_gate_problems(task)

    assert task.id in problem
    assert "receipts.py" in problem


def test_the_generator_repairs_every_way_the_gate_can_be_wrong(
    tmp_path: Path,
) -> None:
    """One flag, and the lint reads the repaired corpus clean — including the
    task that shipped no gate at all, which is how a keyed task authored
    tomorrow gets one."""
    task = fixture_task(tmp_path)
    gate_of(task).unlink()
    (task.repo_dir / "receipts.py").write_text('"""What a till prints."""\n')

    assert write_hash_gates([task]) == [gate_of(task)]
    assert _hash_gate_problems(task) == []


def test_the_frozen_exemption_is_exactly_the_two_round_four_tasks() -> None:
    """Pinned, because the set is frozen and the only way to widen it is to
    edit this test.

    The two were authored before the gate existed. Gating them now would let a
    replay of round 4's logs turn a recorded verdict over — a run that
    answered correctly and also edited the code is recorded resolved — and
    rewriting recorded verdicts is out of scope. That is a fact about those
    two runs, so nothing authored afterwards can qualify.
    """
    assert HASH_GATE_EXEMPT == frozenset({
        "ferry-locate-the-idle-boat",
        "noticeboard-locate-the-lost-notice",
    })


def test_the_exempt_tasks_are_keyed_ship_no_gate_and_still_read_clean() -> None:
    """Exempt rather than accidentally passing: they carry the key the rule is
    keyed on, they ship no gate, and the lint says nothing about them."""
    exempt = [task_by_id(task_id) for task_id in sorted(HASH_GATE_EXEMPT)]

    for task in exempt:
        assert is_keyed(task), task.id
        assert not gate_of(task).exists(), task.id
        assert _hash_gate_problems(task) == [], task.id


def test_the_generator_leaves_the_exempt_tasks_alone(tmp_path: Path) -> None:
    """Skipped rather than merely not required: writing a gate for these two
    would change what a replay of round 4 computes.

    Run over a copy, because a generator that did not skip them would write
    into the checked-in corpus and this test would prove it by doing the very
    damage it is here to rule out.
    """
    for task_id in sorted(HASH_GATE_EXEMPT):
        shutil.copytree(TASKS / task_id, tmp_path / task_id)
    copies = load_task_set(tmp_path)

    assert write_hash_gates(copies) == []
    for task in copies:
        assert not gate_of(task).exists(), task.id


def test_every_other_keyed_task_in_the_corpus_ships_a_gate() -> None:
    """The exemption is two names and not a category: every keyed task outside
    it carries the gate."""
    ungated = sorted(
        task.id
        for task in load_task_set(TASKS)
        if is_keyed(task) and not (task.grading_dir / HASH_GATE_FILE).is_file()
    )

    assert ungated == sorted(HASH_GATE_EXEMPT)


# --- mutation guards: behaviours the suite claims but did not test ----------


def test_defined_symbols_finds_a_definition_guarded_by_an_if_or_try() -> None:
    """Guards the `else: walk(child, prefix)` branch of `_defined_symbols`: a
    `def` inside an `if` or `try` is still defined at its enclosing scope, and
    the walk has to keep descending into every node, not only into the
    definitions it has already found, or a conditionally-defined symbol
    becomes invisible to the key."""
    source = textwrap.dedent("""\
        class Basket:
            try:
                def total_with_tax(self, tax_percent):
                    return 0
            except Exception:
                pass
        """)

    symbols = _defined_symbols(source)

    assert "Basket.total_with_tax" in symbols


def test_defined_symbols_finds_module_level_assignment_targets() -> None:
    """A module-level assignment target is a defined symbol, so a fault in a
    constant, a dispatch table or a compiled pattern can be keyed. The
    boundary is module level, which is what the ruling names: an assignment in
    a class body or a function is a state change inside something already
    keyable, and accepting `Basket.RATE` would key a location the author never
    wrote down."""
    source = textwrap.dedent("""\
        import re

        TAX_PERCENT = 15
        PATTERN = re.compile(r"x")
        HANDLERS: dict = {}
        FIRST, SECOND = 1, 2
        HEAD, *TAIL = [1, 2, 3]
        if TAX_PERCENT:
            GUARDED = 1


        class Basket:
            RATE = 15


        def charge():
            local = 1
            return local
        """)

    symbols = _defined_symbols(source)

    assert {
        "TAX_PERCENT", "PATTERN", "HANDLERS", "FIRST", "SECOND", "GUARDED",
        "HEAD", "TAIL",
    } <= symbols
    assert "Basket.RATE" not in symbols
    assert "RATE" not in symbols
    assert "charge.local" not in symbols
    assert "local" not in symbols


def test_near_miss_uses_the_forgiving_comparison_not_plain_equality(
    tmp_path: Path,
) -> None:
    """(#58, F13) `_near_miss` filters candidates through `matches()`, not
    through plain (file, symbol) equality — load-bearing, but only visible
    when the bare method name sorts before the class name it belongs to.
    Here the class `zz` sorts before its own method `aa`: with the correct,
    forgiving filter the near-miss is `('lower.py', 'zz')`, a genuine
    negative, and the lint is clean. Plain equality would instead pick `aa`
    — the *bare* spelling of the accepted `zz.aa` — which `matches()` in fact
    accepts, so the lint would wrongly demand a legitimate answer grade
    unresolved."""
    write_fixture(
        tmp_path,
        accepted=[{"file": "lower.py", "symbol": "zz.aa"}],
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
        repo_files={"lower.py": "class zz:\n    def aa(self):\n        return 1\n"},
    )
    [task] = load_task_set(tmp_path)

    assert lint_task_set([task]) == []


def test_repo_file_refuses_a_name_that_climbs_out_of_the_repository(
    tmp_path: Path,
) -> None:
    """Guards the is_absolute()/".." guard in `_repo_file`: without it, a name
    climbing out of repo_dir could resolve to a real file sitting just
    outside it — here, the task's own held-out grading directory, which
    `repo/../grading/accepted-answer.json` genuinely reaches on disk."""
    task = fixture_task(tmp_path)
    escaping = f"../grading/{ANSWER_KEY_FILE}"
    # The file really is there, so a check that only asked "does this exist"
    # (rather than also refusing '..') would find it.
    assert (task.grading_dir / ANSWER_KEY_FILE).is_file()

    assert _repo_file(task, escaping) is None


@pytest.mark.parametrize("field", ["lineno", "line_number", "lines", "line_numbers"])
def test_an_accepted_answer_naming_any_line_field_fails_loudly(
    tmp_path: Path, field: str
) -> None:
    """Guards the width of `_LINE_FIELDS`: shrinking it to `("line",)` would
    let every other spelling of a line number through silently."""
    write_fixture(
        tmp_path,
        accepted=[{"file": "pricing.py", "symbol": "Basket", field: 24}],
    )

    with pytest.raises(IngestError, match="line number"):
        load_task_set(tmp_path)


@pytest.mark.parametrize("field", ["Line", "LINE", "at_line", "line_at", "AT_LINE"])
def test_an_accepted_answer_naming_a_line_field_under_any_case_fails_loudly(
    tmp_path: Path, field: str
) -> None:
    """Case, and the `at_line`/`line_at` shapes, must fall into this
    explanatory refusal rather than through to pydantic's generic
    extra="forbid" message."""
    write_fixture(
        tmp_path,
        accepted=[{"file": "pricing.py", "symbol": "Basket", field: 24}],
    )

    with pytest.raises(IngestError, match="line number"):
        load_task_set(tmp_path)


# --- the path the sweep actually captures through ---------------------------


def test_the_answer_file_survives_the_real_capture_path(tmp_path: Path) -> None:
    """Every verdict test above builds its diff with `workdir_diff`, which
    writes no .gitignore and passes no --binary to `git diff`. The live
    runner's own capture (`_commit_pristine` + `_capture_workdir_diff`) does
    both, and nothing else here exercises that exact path — a future addition
    to `_WORKDIR_IGNORE` could stop capturing answer files with every other
    test in this file still green."""
    task = fixture_task(tmp_path)
    workdir = tmp_path / "live-workdir"
    shutil.copytree(task.repo_dir, workdir)
    initial = _commit_pristine(task, workdir)
    (workdir / ANSWER_PATH).write_text(naming("pricing.py", "Basket"))

    diff = _capture_workdir_diff(task, workdir, initial)

    assert ANSWER_PATH in diff
    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    assert record.quality_value == 1.0


def test_a_nested_grading_test_still_finds_the_workdir_root(tmp_path: Path) -> None:
    """The idiom the fixture's own grading test uses (`WORKDIR = Path.cwd()`)
    has to survive a grading test nested under a subdirectory of grading/,
    which `task.grading_test_paths`' rglob permits and which a production
    fault-location task may do."""
    task_dir = write_fixture(tmp_path)
    nested = task_dir / "grading" / "nested"
    nested.mkdir()
    (nested / "test_nested_located_fault.py").write_text(GRADING_TEST)
    [task] = load_task_set(tmp_path)

    assert verdict(task, answers(naming("pricing.py", "Basket"))) == 1.0
