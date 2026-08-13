"""Fault-location tasks: the answer file, the accepted-answer key, and what a
verdict makes of an answer (#49).

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
"""

import json
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import run_for, workdir_diff

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    AcceptedAnswer,
    Task,
    answer_key,
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

# Held out with the grading tests, and self-contained because grading runs
# with conftest loading disabled and its config pinned outside the workdir. It
# reads both files from its own directory, which is the workdir the overlay
# copied it into.
GRADING_TEST = '''\
"""Held out: the agent's answer file, against the accepted-answer key."""

import json
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent
KEY = json.loads((WORKDIR / "accepted-answer.json").read_text(encoding="utf-8"))


def test_the_answer_names_an_accepted_location():
    answer_file = WORKDIR / KEY["answer_path"]
    assert answer_file.is_file(), f"no answer file at {KEY['answer_path']}"
    try:
        answer = json.loads(answer_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AssertionError(f"{KEY['answer_path']} is not JSON: {error}") from error
    assert isinstance(answer, dict), f"{KEY['answer_path']} is not a JSON object"
    located = {"file": answer.get("file"), "symbol": answer.get("symbol")}
    assert located in KEY["accepted"], (
        f"{located} is not one of the accepted locations {KEY['accepted']}"
    )
'''


def write_fixture(
    root: Path,
    *,
    accepted: list[dict[str, object]] | None = None,
    answer_path: str = ANSWER_PATH,
    prompt: str = PROMPT,
    **spec: object,
) -> Path:
    """The fixture fault-location task, written into root ready to load.

    A coverage task rather than a knob experiment, so it declares itself a
    control: it claims nothing about difficulty, and saying so is the only way
    to say it outside the frozen 22.
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
    (task_dir / "grading" / "test_located_fault.py").write_text(GRADING_TEST)
    (task_dir / "grading" / ANSWER_KEY_FILE).write_text(
        json.dumps(
            {
                "answer_path": answer_path,
                "accepted": ACCEPTED if accepted is None else accepted,
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
        AcceptedAnswer(file="pricing.py", symbol="Basket.total_with_tax"),
        AcceptedAnswer(file="pricing.py", symbol="Basket"),
    )


def test_the_key_ships_in_the_grading_directory_without_being_collected(
    tmp_path: Path,
) -> None:
    """It reaches the workdir by the overlay that copies that directory
    wholesale, and collection globs test files only, so nothing runs it."""
    task = fixture_task(tmp_path)

    assert (task.grading_dir / ANSWER_KEY_FILE).is_file()
    assert task.grading_test_paths == ("test_located_fault.py",)


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
        tmp_path, grading={"behaviour_tests": ["test_located_fault.py"]}
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


def test_an_answer_written_at_another_path_is_unresolved(tmp_path: Path) -> None:
    """The declared path is the contract the prompt states; a correct answer
    filed somewhere else is one the grader was never told to look for.

    Written into a subdirectory rather than under a differently-cased name,
    because a case-insensitive filesystem would resolve that back to the
    declared path and the test would pass for a reason that is not the rule."""
    task = fixture_task(tmp_path)
    correct = naming("pricing.py", "Basket.total_with_tax")

    assert verdict(task, answers(correct, at=f"report/{ANSWER_PATH}")) == 0.0


def test_the_pristine_repository_carries_no_answer_file(tmp_path: Path) -> None:
    """Which is why the must-fail-on-pristine invariant needs no special case
    here: with no answer to read, the grading test fails, exactly as the lint
    demands of every task. A clean lint is that invariant holding."""
    task = fixture_task(tmp_path)

    assert not (task.repo_dir / ANSWER_PATH).exists()
    assert lint_task_set([task]) == []


# --- the lint: what the accepted-answer key has to say --------------------------


def test_lint_rejects_an_empty_accepted_set(tmp_path: Path) -> None:
    """A key accepting nothing grades every agent unresolved, and does it
    while looking exactly like a very hard task."""
    task = fixture_task(tmp_path, accepted=[])

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


def test_lint_rejects_a_key_naming_a_symbol_the_file_does_not_define(
    tmp_path: Path,
) -> None:
    """A renamed symbol, a typo, or a method written without its class: all
    three accept an answer no correct agent can give."""
    task = fixture_task(
        tmp_path, accepted=[{"file": "pricing.py", "symbol": "total_with_tax"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "total_with_tax" in problem
    assert "does not define" in problem


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
