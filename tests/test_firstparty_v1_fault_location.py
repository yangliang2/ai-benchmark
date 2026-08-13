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
from firstparty_v1_tasks import run_for, workdir_diff

from ai_benchmark import _answer
from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    ANSWER_MODULE,
    ANSWER_TEST_FILE,
    Answer,
    Task,
    _capture_workdir_diff,
    _commit_pristine,
    _defined_symbols,
    _repo_file,
    answer_key,
    answer_module_source,
    answer_test_source,
    evaluate,
    is_control,
    lint_task_set,
    load_task_set,
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
PRICING = '''\
"""What an order costs."""


def line_total(unit_cents, quantity):
    """The cost of one order line, in cents."""
    return unit_cents * quantity


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
        """The subtotal plus tax, rounded to the nearest cent."""
        return self.subtotal() + self.subtotal() * tax_percent // 100
'''

# The module that *looks* responsible: it is where the tax rate lives and
# where the wrong number is returned from, and it is correct. The near-miss no
# lint can invent — the plausible wrong file — needs a second module to be
# written down at all, and its module-level TAX_PERCENT is what a fault in a
# constant, a dispatch table or a compiled pattern looks like.
CHECKOUT = '''\
"""Taking payment for an order."""

from pricing import Basket

TAX_PERCENT = 15


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
    """
    task_dir = root / FIXTURE_ID
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "grading").mkdir()
    fields: dict[str, object] = {
        "id": FIXTURE_ID,
        "category": "fault-location",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "prompt": prompt,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    (task_dir / "repo" / "pricing.py").write_text(PRICING)
    (task_dir / "repo" / "checkout.py").write_text(CHECKOUT)
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
    assert task.grading_test_paths == (ANSWER_TEST_FILE,)


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
    task_dir = write_fixture(
        tmp_path,
        accepted=[{"file": "tiny.py", "symbol": "only"}],
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
    )
    (task_dir / "repo" / "tiny.py").write_text("def only():\n    return 1\n")
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
    )
    (task_dir / "repo" / "tiny.py").write_text("def only():\n    return 1\n")
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
    task_dir = write_fixture(
        tmp_path,
        accepted=[{"file": "lower.py", "symbol": "zz.aa"}],
        rejected=[{"file": "pricing.py", "symbol": "line_total"}],
    )
    (task_dir / "repo" / "lower.py").write_text(
        "class zz:\n    def aa(self):\n        return 1\n"
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
