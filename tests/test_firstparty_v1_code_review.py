"""`code-review`: the set-shaped findings key and the verdict it decides
(#69, design note §45.2-45.3).

The round's one new instrument. A review task hands the agent a change that is
already applied to its starting repository, plus a unified diff of that change
as a file the prompt names, and asks which of it is wrong; the deliverable is
an answer file listing findings, one (file, symbol) location each. What grades
it is a key whose two halves are *sets*: every planted finding has to be
matched by some finding of the answer, and no finding of the answer may match a
rejected one.

Everything mechanical is borrowed. The answer file reaches grading in the
workdir diff with no new seam; the pair model and its refusals are
`fault-location`'s `Answer`; the location forgiveness is `_answer.py`, imported
by `_findings.py` rather than copied, so a review answer and a locate answer
forgive the same spellings. What is new is the quantifier — a locate verdict
asks whether the one answer is *in* the accepted set, a review verdict asks
whether the answer's findings *cover* it — and the two consequences of it that
these tests are mostly about: an unregistered extra finding is archived rather
than scored, and one missing planted finding is unresolved with no partial
credit.

Everything here is proved on a **fixture** task built into tmp_path, the way
`tests/test_firstparty_v1_fault_location.py` proves the mechanism it owns: no
`code-review` task is authored here, and the lint rules over this key are a
later ticket. The diffs are built with git by the shared task-test helper, the
way the live runner builds one, and graded by `grade` — the same call replay
grades a logged run through — so an answer file reaches the verdict exactly as
an agent's would.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import run_for, workdir_diff

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    ANSWER_MODULE,
    CORRECTED_DIR,
    FINDINGS_KEY_FILE,
    FINDINGS_MODULE,
    FINDINGS_TEST_FILE,
    GRADING_DIR,
    REPO_DIR,
    REVIEW_DIFF_FILE,
    Answer,
    Task,
    answer_module_source,
    evaluate,
    findings_key,
    findings_module_source,
    findings_test_source,
    grade,
    is_findings_keyed,
    is_keyed,
    lint_task_set,
    load_task_set,
)

FIXTURE_ID = "rota-review-the-overtime-change"

# Where the fixture's prompt tells the agent to write its findings, and what the
# key declares. One declared path, named in both, is the whole of the contract
# between the prompt and the grading test.
ANSWER_PATH = "FINDINGS.json"

# The starting repository ships the change under review *already applied*, so
# both planted defects are in these two modules. There is no second tree the
# agent can see: the diff below is how it is told what changed.
#
# Defect one, in `overtime_pay`: overtime is meant to be paid on the hours past
# the threshold, and this pays it on every hour once the threshold is passed,
# so a nine-hour shift is billed at eighteen hours rather than ten.
PAYROLL = '''\
"""What a week of work comes to."""

RATE_PENCE = 1200
OVERTIME_AFTER_HOURS = 8
OVERTIME_MULTIPLIER = 2


def overtime_pay(hours):
    """What one stretch of work earns, in pence."""
    if hours > OVERTIME_AFTER_HOURS:
        return hours * RATE_PENCE * OVERTIME_MULTIPLIER
    return hours * RATE_PENCE


def total_pay(rota):
    """What the whole week comes to, in pence."""
    return sum(overtime_pay(shift.hours) for shift in rota.shifts)
'''

# Defect two, in `Rota.add`: the gap is measured from the start of the previous
# stretch rather than from its end, so a stretch that ran late is treated as
# though it had never happened.
SHIFTS = '''\
"""Who is on, and when."""

MIN_REST_HOURS = 11


class Shift:
    """One person's stretch of work, in whole hours from midnight."""

    def __init__(self, who, start, end):
        self.who = who
        self.start = start
        self.end = end

    @property
    def hours(self):
        return self.end - self.start


class Rota:
    """Every stretch of one week, in the order they were taken on."""

    def __init__(self):
        self.shifts = []

    def add(self, shift):
        """Take a stretch on, unless it crowds the one before it."""
        previous = self.latest_for(shift.who)
        if previous is not None and shift.start - previous.start < MIN_REST_HOURS:
            raise ValueError(f"{shift.who} needs {MIN_REST_HOURS} hours off")
        self.shifts.append(shift)

    def latest_for(self, who):
        theirs = [shift for shift in self.shifts if shift.who == who]
        return theirs[-1] if theirs else None
'''

# The corrected tree: the same repository with both planted defects put right.
# It ships beside `repo/` and outside `grading/`, is read only by the lint, and
# is what a held-out proof test per finding will be run against.
CORRECTED_PAYROLL = PAYROLL.replace(
    "        return hours * RATE_PENCE * OVERTIME_MULTIPLIER\n",
    "        beyond = hours - OVERTIME_AFTER_HOURS\n"
    "        base = OVERTIME_AFTER_HOURS * RATE_PENCE\n"
    "        return base + beyond * RATE_PENCE * OVERTIME_MULTIPLIER\n",
)
CORRECTED_SHIFTS = SHIFTS.replace("previous.start <", "previous.end <")

# The change under review, as the repository ships it. Nothing in this ticket
# reads it — what does is the lint rule holding the key's findings to the files
# the change actually touched — so it is written to be read: the agent is told
# where it is and reviews it against the code it is applied to.
REVIEW_DIFF = '''\
--- a/payroll.py
+++ b/payroll.py
@@ -1,11 +1,17 @@
 """What a week of work comes to."""

 RATE_PENCE = 1200
+OVERTIME_AFTER_HOURS = 8
+OVERTIME_MULTIPLIER = 2


-def pay(hours):
+def overtime_pay(hours):
     """What one stretch of work earns, in pence."""
+    if hours > OVERTIME_AFTER_HOURS:
+        return hours * RATE_PENCE * OVERTIME_MULTIPLIER
     return hours * RATE_PENCE


 def total_pay(rota):
     """What the whole week comes to, in pence."""
-    return sum(pay(shift.hours) for shift in rota.shifts)
+    return sum(overtime_pay(shift.hours) for shift in rota.shifts)
--- a/shifts.py
+++ b/shifts.py
@@ -1,5 +1,7 @@
 """Who is on, and when."""

+MIN_REST_HOURS = 11
+

 class Shift:
     """One person's stretch of work, in whole hours from midnight."""
@@ -24,6 +26,9 @@ class Rota:
     def add(self, shift):
         """Take a stretch on, unless it crowds the one before it."""
+        previous = self.latest_for(shift.who)
+        if previous is not None and shift.start - previous.start < MIN_REST_HOURS:
+            raise ValueError(f"{shift.who} needs {MIN_REST_HOURS} hours off")
         self.shifts.append(shift)
'''

PROMPT = f"""\
{REVIEW_DIFF_FILE} in the repository root is a change that has already been
applied to this repository: it pays people more for a long stretch of work, and
refuses one taken on too soon after the last. Review it. Do not change any
code.

Write your findings to {ANSWER_PATH} in the repository root, as a JSON list
with one object per finding: "file" (the path, relative to the repository
root), "symbol" (the function, class or method the problem lives in) and,
optionally, "note" (a sentence on what is wrong). Report every problem the
change introduced, and nothing that is not one.
"""

# The planted findings: one defect each, at the level the author is prepared to
# have them described at.
ACCEPTED: list[dict[str, object]] = [
    {"file": "payroll.py", "symbol": "overtime_pay"},
    {"file": "shifts.py", "symbol": "Rota.add"},
]

# The non-findings: the two places a reviewer plausibly points at and is wrong
# to. `total_pay` is the caller that returns the wrong number and is itself
# correct; `MIN_REST_HOURS` is the constant the change introduced, and eleven
# hours is what was asked for.
REJECTED: list[dict[str, object]] = [
    {"file": "payroll.py", "symbol": "total_pay"},
    {"file": "shifts.py", "symbol": "MIN_REST_HOURS"},
]

# A location the key registers on neither side: a real symbol of the repository
# that the change under review did not introduce a defect into and that no
# rejected finding names. What a reviewer reports when it has seen something
# the author did not plant — archived in the diff, ignored by the verdict.
UNREGISTERED = ("payroll.py", "RATE_PENCE")

DOMAIN_NOUNS = [
    "change", "hour", "hours", "pay", "rota", "shift", "stretch", "week", "work",
]

GRADING_TEST = findings_test_source().decode("utf-8")


def write_fixture(
    root: Path,
    *,
    accepted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
    answer_path: str = ANSWER_PATH,
    prompt: str = PROMPT,
    grading_test: str = GRADING_TEST,
    key_text: str | None = None,
    ship_key: bool = True,
    task_id: str = FIXTURE_ID,
    **spec: object,
) -> Path:
    """The fixture `code-review` task, written into root ready to load.

    A coverage task rather than a knob experiment, so it declares itself a
    control: it claims nothing about difficulty, and saying so is the only way
    to say it outside the frozen 22.

    The findings comparison, the answer comparison it imports its forgiveness
    from, and the held-out grading test that asserts over it are all copied in
    rather than written here, because that is what a real review task ships:
    three owned files, shipped identically, byte-comparable against the bytes
    this package owns.

    `key_text` writes the key file's raw bytes instead of building one, for the
    tests about a key that cannot be read at all; `ship_key=False` ships none.

    `scale` is read off the reference solution's diff, as every task's is, and
    a review's reference solution is one answer file: `single-file`, whatever
    the change under review spans.
    """
    task_dir = root / task_id
    (task_dir / REPO_DIR).mkdir(parents=True)
    (task_dir / GRADING_DIR).mkdir()
    (task_dir / CORRECTED_DIR).mkdir()
    fields: dict[str, object] = {
        "id": task_id,
        "category": "code-review",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "domain_nouns": DOMAIN_NOUNS,
        "prompt": prompt,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    (task_dir / REPO_DIR / "payroll.py").write_text(PAYROLL)
    (task_dir / REPO_DIR / "shifts.py").write_text(SHIFTS)
    (task_dir / REPO_DIR / REVIEW_DIFF_FILE).write_text(REVIEW_DIFF)
    (task_dir / CORRECTED_DIR / "payroll.py").write_text(CORRECTED_PAYROLL)
    (task_dir / CORRECTED_DIR / "shifts.py").write_text(CORRECTED_SHIFTS)
    (task_dir / GRADING_DIR / FINDINGS_TEST_FILE).write_text(grading_test)
    (task_dir / GRADING_DIR / FINDINGS_MODULE).write_bytes(findings_module_source())
    (task_dir / GRADING_DIR / ANSWER_MODULE).write_bytes(answer_module_source())
    if ship_key:
        declared = json.dumps(
            {
                "answer_path": answer_path,
                "accepted": ACCEPTED if accepted is None else accepted,
                "rejected": REJECTED if rejected is None else rejected,
            },
            indent=2,
        )
        (task_dir / GRADING_DIR / FINDINGS_KEY_FILE).write_text(
            declared + "\n" if key_text is None else key_text
        )
    return task_dir


def fixture_task(root: Path, **overrides: Any) -> Task:
    write_fixture(root, **overrides)
    [task] = load_task_set(root)
    return task


def reporting(*findings: dict[str, object]) -> str:
    """One answer file's contents: a list with one object per finding."""
    return json.dumps(list(findings), indent=2) + "\n"


def finding(file: str, symbol: str, note: str | None = None) -> dict[str, object]:
    reported: dict[str, object] = {"file": file, "symbol": symbol}
    if note is not None:
        reported["note"] = note
    return reported


def every_planted_finding() -> str:
    """The reference solution: the answer file a correct review leaves behind,
    which for an answer-file-only deliverable is the whole of it."""
    return reporting(
        finding(
            "payroll.py",
            "overtime_pay",
            "the multiplier is applied to every hour, not to the hours past "
            "the threshold",
        ),
        finding(
            "shifts.py",
            "Rota.add",
            "the gap is measured from the previous stretch's start rather "
            "than its end",
        ),
    )


def answers(payload: str, *, at: str = ANSWER_PATH) -> Callable[[Path], None]:
    """The edit a run that wrote this answer file would log."""

    def write(workdir: Path) -> None:
        target = workdir / at
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload)

    return write


def resolves(task: Task, payload: str) -> bool:
    """What the pipeline a real run replays through makes of this answer."""
    return grade(task, workdir_diff(task, answers(payload)))


# --- the task and its key ------------------------------------------------------


def test_a_code_review_task_loads_carrying_its_findings_key(tmp_path: Path) -> None:
    task = fixture_task(tmp_path)
    key = findings_key(task)

    assert task.category == "code-review"
    assert is_findings_keyed(task)
    # The two keys are different files and different verdicts: a review task
    # ships no accepted-answer key, and nothing gated on that one reaches it.
    assert not is_keyed(task)
    assert key.answer_path == ANSWER_PATH
    assert key.accepted == (
        Answer(file="payroll.py", symbol="overtime_pay"),
        Answer(file="shifts.py", symbol="Rota.add"),
    )
    assert key.rejected == (
        Answer(file="payroll.py", symbol="total_pay"),
        Answer(file="shifts.py", symbol="MIN_REST_HOURS"),
    )


def test_the_key_ships_in_the_grading_directory_without_being_collected(
    tmp_path: Path,
) -> None:
    """It reaches the workdir by the overlay that copies that directory
    wholesale, and collection globs test files only, so nothing runs it."""
    task = fixture_task(tmp_path)

    assert (task.grading_dir / FINDINGS_KEY_FILE).is_file()
    assert task.grading_test_paths == (FINDINGS_TEST_FILE,)


def test_the_corrected_tree_lives_beside_the_repository_and_outside_grading(
    tmp_path: Path,
) -> None:
    """The grading directory is overlaid into the workdir wholesale, so a
    corrected tree kept inside it would hand the agent the answers — its source
    files would land in the graded workdir, and any test among them would be
    collected as a verdict test."""
    task = fixture_task(tmp_path)

    assert task.corrected_dir.is_dir()
    assert task.corrected_dir.parent == task.repo_dir.parent
    assert task.grading_dir not in task.corrected_dir.parents
    assert (task.corrected_dir / "payroll.py").read_text() == CORRECTED_PAYROLL
    # Nothing of it is overlaid or collected: the overlay copies `grading/`,
    # and the grading suite is the one held-out test.
    assert not list(task.grading_dir.rglob(f"{CORRECTED_DIR}*"))
    assert task.grading_test_paths == (FINDINGS_TEST_FILE,)


def test_a_review_task_inherits_none_of_the_accepted_answer_keys_rules(
    tmp_path: Path,
) -> None:
    """Every gate the fault-location key owns is gated on *that* key being on
    disk, so a review task inherits none of them: it ships no
    `accepted-answer.json`, no `test_answer.py` and no hash gate, and none of
    that is a lint problem. What it also shows is the invariant a review task
    does keep — its grading test fails on the pristine repository, which
    carries no answer file at all. The findings key's own lint rules are a
    later ticket's."""
    task = fixture_task(tmp_path)

    assert not is_keyed(task)
    assert lint_task_set([task]) == []


def test_the_starting_repository_ships_the_change_under_review(
    tmp_path: Path,
) -> None:
    """There is no second tree the agent can see: the change is applied, and
    the diff of it is a file of the repository the prompt names."""
    task = fixture_task(tmp_path)

    assert (task.repo_dir / REVIEW_DIFF_FILE).read_text() == REVIEW_DIFF
    assert REVIEW_DIFF_FILE in task.prompt
    assert ANSWER_PATH in task.prompt


def test_the_findings_comparison_and_its_test_are_the_bytes_this_project_owns(
    tmp_path: Path,
) -> None:
    """Both are owned rather than hand-written per task, and both accessors
    return what a task has to ship byte for byte — which is what the lint
    reads the shipped copies back against."""
    task = fixture_task(tmp_path)

    assert (task.grading_dir / FINDINGS_MODULE).read_bytes() == (
        findings_module_source()
    )
    assert (task.grading_dir / FINDINGS_TEST_FILE).read_bytes() == (
        findings_test_source()
    )
    # The findings comparison imports its forgiveness rather than restating it,
    # so the answer comparison ships beside it, unedited.
    assert (task.grading_dir / ANSWER_MODULE).read_bytes() == answer_module_source()
    assert b"findings_problem" in findings_test_source()
    assert b"from _answer import" in findings_module_source()


# --- what fails at load, before a paid run -------------------------------------


def test_a_code_review_task_with_no_findings_key_fails_to_load(
    tmp_path: Path,
) -> None:
    """Mandatory, the way a fault-location task's accepted-answer key is: the
    findings *are* the deliverable of a review, so a review task with no key
    has no ground truth at all."""
    with pytest.raises(IngestError, match="missing or unreadable"):
        fixture_task(tmp_path, ship_key=False)


def test_an_unparseable_findings_key_fails_to_load(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="is not JSON"):
        fixture_task(tmp_path, key_text="the overtime one, and the rest gap\n")


def test_a_findings_key_that_plants_nothing_fails_to_load(tmp_path: Path) -> None:
    """`ai-bench run-live` loads a task set but never lints it, so this has to
    be refused at load: "every planted finding was reported" is satisfied by
    any answer at all when none were planted, so the task would grade every
    agent resolved."""
    with pytest.raises(IngestError, match="plants no findings"):
        fixture_task(tmp_path, accepted=[])


def test_a_finding_written_as_a_line_number_is_refused(tmp_path: Path) -> None:
    """The pair model is fault-location's, refusals and all: lines shift under
    any edit, and a key keyed on one would grade a correct finding wrong."""
    with pytest.raises(IngestError, match="names a line number"):
        fixture_task(
            tmp_path,
            accepted=[{"file": "payroll.py", "symbol": "overtime_pay", "line": 9}],
        )


def test_a_finding_naming_a_file_alone_is_refused(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="names a file with no symbol"):
        fixture_task(tmp_path, accepted=[{"file": "payroll.py"}])


def test_neither_half_may_name_one_pair_twice(tmp_path: Path) -> None:
    """Both halves are sets. A planted finding named twice would have to be
    reported twice by an answer that is a set as well, or counted twice by a
    verdict that is not."""
    with pytest.raises(IngestError, match="accepted names the same"):
        fixture_task(tmp_path / "accepted-twice", accepted=ACCEPTED + [ACCEPTED[0]])
    with pytest.raises(IngestError, match="rejected names the same"):
        fixture_task(tmp_path / "rejected-twice", rejected=REJECTED + [REJECTED[1]])


def test_only_a_code_review_task_may_ship_a_findings_key(tmp_path: Path) -> None:
    """Gated the way the accepted-answer key is gated on its two actions: a key
    shipped by another action would hold that task to the review rules while
    its own grading never consulted the key at all."""
    with pytest.raises(IngestError, match="a feature-dev task ships"):
        fixture_task(tmp_path, category="feature-dev")


def test_a_code_review_task_names_no_behaviour_tests(tmp_path: Path) -> None:
    """Only a refactor splits its grading suite: behaviour tests are exempt
    from must-fail-on-pristine, and a review task naming one would exempt the
    only test its verdict is made of."""
    with pytest.raises(IngestError, match="only refactor tasks split grading"):
        fixture_task(
            tmp_path, grading={"behaviour_tests": [FINDINGS_TEST_FILE]}
        )


# --- the verdict ---------------------------------------------------------------


def test_the_reference_solution_resolves_and_the_empty_diff_does_not(
    tmp_path: Path,
) -> None:
    """The two ends of the pipeline every checked-in task is held to: the
    reference solution — which for an answer-file-only deliverable is the
    answer file itself — grades resolved, and a run that changed nothing does
    not."""
    task = fixture_task(tmp_path)

    assert resolves(task, every_planted_finding())
    assert not grade(task, "")


def test_an_answer_listing_every_planted_finding_resolves(tmp_path: Path) -> None:
    """Spelled without notes and at the bare description level an agent would
    most naturally use, so this also proves the forgiveness is `_answer.py`'s:
    `add` answers the accepted `Rota.add`, and `./payroll.py` answers
    `payroll.py`."""
    task = fixture_task(tmp_path)

    assert resolves(
        task,
        reporting(
            finding("./payroll.py", "overtime_pay()"),
            finding("shifts.py", " add "),
        ),
    )


def test_an_unregistered_extra_finding_is_ignored_and_stays_in_the_diff(
    tmp_path: Path,
) -> None:
    """A real problem the author did not plant must not fail the run: a finding
    matching neither half is archived evidence, not a verdict. It is in the
    workdir diff, which is what the log carries, and the verdict is the one the
    planted findings alone decide."""
    task = fixture_task(tmp_path)
    file, symbol = UNREGISTERED
    payload = reporting(
        finding("payroll.py", "overtime_pay"),
        finding("shifts.py", "Rota.add"),
        finding(file, symbol, "and this rate looks out of date to me"),
    )

    diff = workdir_diff(task, answers(payload))

    assert symbol in diff
    assert grade(task, diff)


def test_an_answer_missing_one_planted_finding_does_not_resolve(
    tmp_path: Path,
) -> None:
    """The load-bearing half of a set verdict, and the one a comparison asking
    "did some finding match" cannot survive: one planted finding of two is
    unresolved, and there is nothing between the two verdicts, because a
    partial recall rate would be a new quality metric."""
    task = fixture_task(tmp_path)

    assert not resolves(task, reporting(finding("payroll.py", "overtime_pay")))
    assert not resolves(task, reporting(finding("shifts.py", "Rota.add")))
    assert not resolves(task, reporting())


def test_an_answer_reporting_a_rejected_finding_does_not_resolve(
    tmp_path: Path,
) -> None:
    """The other half: every planted finding reported *and* a non-finding
    reported beside them is unresolved, which is what stops
    every-line-is-a-finding from passing."""
    task = fixture_task(tmp_path)
    complete = [
        finding("payroll.py", "overtime_pay"),
        finding("shifts.py", "Rota.add"),
    ]

    assert resolves(task, reporting(*complete))
    assert not resolves(task, reporting(*complete, finding("payroll.py", "total_pay")))
    assert not resolves(
        task, reporting(*complete, finding("shifts.py", "MIN_REST_HOURS"))
    )


def test_an_answer_that_is_not_a_list_of_findings_does_not_resolve(
    tmp_path: Path,
) -> None:
    """A review names as many findings as the change holds, so the list is the
    answer — and what is refused inside it is what a fault-location answer
    refuses: a nested list or object, which is how a second location arrives
    inside one finding."""
    task = fixture_task(tmp_path)

    assert not resolves(task, "")
    assert not resolves(task, "the overtime one, and the rest gap\n")
    assert not resolves(task, json.dumps({"file": "payroll.py", "symbol": "x"}))
    assert not resolves(
        task,
        json.dumps([
            {"file": "payroll.py", "symbol": "overtime_pay",
             "also": {"file": "shifts.py", "symbol": "Rota.add"}},
        ]),
    )


def test_no_answer_file_at_the_declared_path_does_not_resolve(
    tmp_path: Path,
) -> None:
    """A run that reviewed the change and wrote its findings somewhere else is
    a run with no deliverable, however good the review was."""
    task = fixture_task(tmp_path)
    diff = workdir_diff(
        task, answers(every_planted_finding(), at="notes/review.md")
    )

    assert not grade(task, diff)


# --- the free text the verdict never reads -------------------------------------


def test_a_findings_note_is_carried_into_the_diff_and_never_read(
    tmp_path: Path,
) -> None:
    """A note is a flat extra field beside the location, tolerated and ungraded:
    two answers naming the same locations under different notes grade
    identically, and both notes reach the diff the log archives."""
    task = fixture_task(tmp_path)
    locations = [
        finding("payroll.py", "overtime_pay", "the multiplier hits every hour"),
        finding("shifts.py", "Rota.add", "measured from the wrong end"),
    ]
    reworded = [
        finding("payroll.py", "overtime_pay", "surely this over-pays a long day"),
        finding("shifts.py", "Rota.add", "I think this compares the wrong field"),
    ]

    one = workdir_diff(task, answers(reporting(*locations)))
    other = workdir_diff(task, answers(reporting(*reworded)))

    assert one != other
    assert "over-pays a long day" in other
    assert {grade(task, one), grade(task, other)} == {True}


def test_a_persuasive_note_cannot_rescue_a_wrong_finding(tmp_path: Path) -> None:
    """The verdict reads locations, not prose: a finding the key rejects is
    rejected however persuasively it is written up, and a planted finding left
    out is still left out however well the rest is argued."""
    task = fixture_task(tmp_path)

    assert not resolves(
        task,
        reporting(
            finding("payroll.py", "overtime_pay", "this one is real"),
            finding(
                "payroll.py",
                "total_pay",
                "and this is certainly wrong too: it sums the wrong thing, it "
                "has always summed the wrong thing, and any reviewer would say "
                "so",
            ),
        ),
    )


def test_two_runs_with_one_diff_and_different_final_messages_get_one_verdict(
    tmp_path: Path,
) -> None:
    """The provenance boundary does not move for this action either: the run
    log still stores the agent's final message and the verdict still never
    reads it. Same diff, opposite prose, one verdict."""
    task = fixture_task(tmp_path)
    diff = workdir_diff(task, answers(every_planted_finding()))
    runs = [
        run_for(task, diff, model="claude-sonnet-5").model_copy(
            update={"output": "Two problems: the overtime maths and the rest gap."}
        ),
        run_for(task, diff, model="claude-haiku-4-5").model_copy(
            update={"output": "I could not find anything wrong with this change."}
        ),
    ]

    records = evaluate([task], runs, source="run-log")

    assert [record.quality_value for record in records] == [1.0, 1.0]
    assert {record.category for record in records} == {"code-review"}
