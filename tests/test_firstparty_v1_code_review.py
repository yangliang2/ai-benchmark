"""`code-review`: the set-shaped findings key, the verdict it decides, and the
lint that refuses a review task which cannot measure anything (#69, #70, design
note §45.2-45.3).

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
`code-review` task is authored here. The diffs are built with git by the shared
task-test helper, the way the live runner builds one, and graded by `grade` —
the same call replay grades a logged run through — so an answer file reaches
the verdict exactly as an agent's would.

What #70 adds is the proof, before a paid run, that the held-out test
discriminates. Must-fail-on-pristine cannot show it: a pristine repository
carries no answer file, so the check is unconditionally satisfied and a grading
test asking "did some finding match" passes it. So the lint reads the key
against the change under review — the accepted set describes the change and not
the repository at large — and then runs answers it expects to *fail* through
the real pipeline, two kinds of which are what a set verdict has to earn: every
planted finding but one, and every planted finding plus a rejected one. The
three terrain rules reach a review task here too, keyed on the task carrying a
key rather than on which key it carries.

What #85 adds is the shape a planted finding actually has: not one location but
a **set of alternatives**, matched if an answer matches any one of them, the
first of them the primary. That is the mitigation for this grading's expensive
assumption — that an agent which spots a defect describes it at a level the
author anticipated — and under the flat shape it was inexpressible, because the
accepted half is read under *every* and a second entry for one defect demanded
that the answer report it twice. Every read rule now runs per alternative, and
the lint *proves* the mitigation rather than trusting it: the answer reporting
any finding at any of its alternatives is required to grade resolved.

What #71 adds is the prior question none of that asks: whether the planted
findings are defects at all. The fixture therefore ships an **existence proof**
per planted finding — a held-out test in its own `proofs/` subtree that fails on
the starting repository and passes on the corrected tree — because that is what
a review task ships from now on, and a fixture that did not could not be used to
prove anything else about the lint. The rule itself, in both directions, is
`tests/test_firstparty_v1_existence_proofs.py`'s.
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
    _terrain_problems,
    Answer,
    ANSWER_MODULE,
    answer_module_source,
    CORRECTED_DIR,
    evaluate,
    findings_key,
    FINDINGS_KEY_FILE,
    FINDINGS_MODULE,
    findings_module_source,
    FINDINGS_TEST_FILE,
    findings_test_source,
    grade,
    GRADING_DIR,
    HASH_GATE_FILE,
    hash_gate_source,
    is_findings_keyed,
    is_keyed,
    lint_task_set,
    load_task_set,
    PlantedFinding,
    proof_test_name,
    PROOFS_DIR,
    REPO_DIR,
    REVIEW_DIFF_FILE,
    Task,
)
from ai_benchmark.language_runners import PYTHON

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

# Two modules the change under review does not touch. They are here for the
# same reason `checkout.py`'s `Till` is in the fault-location fixture: the
# terrain rules apply to a task carrying a findings key too, and the narrowing
# rule holds every distinctive prompt word to appearing in more than the modules
# the accepted findings name. "class" is a word the prompt has to use to say
# what a symbol may be, and without a module outside the key defining one it
# would appear in `shifts.py` and nowhere else.
#
# `people.py` is the one that carries classes and is never keyed by any test
# here, so it is what keeps "class" harmless even in the tests that key
# `swaps.py`. `swaps.py` is the untouched file those tests name, and holds no
# class for exactly that reason.
PEOPLE = '''\
"""Everybody a week may be built out of."""


class Person:
    """One name on the books, and where to reach them."""

    def __init__(self, name, contact):
        self.name = name
        self.contact = contact


class Roster:
    """The names, in the order they joined."""

    def __init__(self, members):
        self.members = list(members)

    def named(self, name):
        for member in self.members:
            if member.name == name:
                return member
        return None
'''

SWAPS = '''\
"""Handing a stretch over to somebody else."""


def hand_over(rota, from_who, to_who):
    """Give everything of one person's to another, in place."""
    for shift in rota.shifts:
        if shift.who == from_who:
            shift.who = to_who


def handed(rota, who):
    """How many stretches this person was given by somebody else."""
    return sum(1 for shift in rota.shifts if shift.who == who)
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

# Written to the terrain rules, which reach a review task through its findings
# key: it names no file and no symbol out of either half of the key, and its
# distinctive vocabulary — everything that is neither a closed-class function
# word nor a declared domain noun — appears in more than the modules the planted
# findings live in, so no grep of the prompt's own words lands on a defect.
PROMPT = f"""\
{REVIEW_DIFF_FILE} in the repository root is a change that has already been
applied to this repository: it pays more for a long stretch of work, and
refuses a shift that starts too soon after the last one. Review it, and do not
edit any code.

Write your findings to {ANSWER_PATH} in the repository root, as a JSON list
with one object per finding: "file" (the path, relative to the repository
root), "symbol" (the function, class or method the problem lives in) and,
optionally, "note" (a sentence on what is wrong). Report each problem the
change introduced, and nothing that is not one.
"""

# The planted findings: one defect each, written as the *set* of locations that
# legitimately describe it, primary first (#85). The first plants a defect in a
# module-level function, which has no enclosing class to be a second description
# of it. The second plants one in a method, and names the class enclosing it as
# a second alternative — which `shifts.py` allows, defining `Shift` beside
# `Rota`, so terrain rule 3 does not refuse a class-level location there.
ACCEPTED: list[dict[str, object]] = [
    {"any": [{"file": "payroll.py", "symbol": "overtime_pay"}]},
    {
        "any": [
            {"file": "shifts.py", "symbol": "Rota.add"},
            {"file": "shifts.py", "symbol": "Rota"},
        ]
    },
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

# The nouns a prompt about a week of work and a repository about a week of work
# cannot help sharing — the half of the "unrevealing vocabulary" split that is a
# fact about this task's subject rather than about English, and so the half a
# task declares for itself. Everything else the prompt says is distinctive, and
# the narrowing terrain rule holds it to appearing in more than the modules the
# planted findings live in.
DOMAIN_NOUNS = [
    "change", "hour", "hours", "overtime", "pay", "rota", "shift", "stretch",
    "week", "work",
]

# The existence proof of each planted finding (#71): a held-out test that fails
# on the starting repository — which ships the change under review already
# applied — and passes on the corrected tree. Neither direction is optional. A
# proof that passed on the starting repository would say the finding is not a
# defect at all; one that failed on the corrected tree would say the author's own
# correction does not fix what the finding claims.
#
# They live in the task's `proofs/` subtree, beside `corrected/` and outside
# `grading/`, so the lint runs them and grading can neither overlay nor collect
# them.
OVERTIME_PROOF = '''\
"""Overtime is owed on the hours past the threshold, not on every hour."""

from payroll import overtime_pay


def test_a_nine_hour_stretch_pays_eight_flat_and_the_ninth_at_the_multiplier():
    assert overtime_pay(9) == 8 * 1200 + 1200 * 2
'''

REST_PROOF = '''\
"""The gap is measured from the end of the previous stretch, not its start."""

from shifts import Rota, Shift


def test_a_stretch_starting_too_soon_after_the_last_one_ended_is_refused():
    rota = Rota()
    rota.add(Shift("ada", 0, 12))
    try:
        rota.add(Shift("ada", 14, 20))
    except ValueError:
        return
    raise AssertionError("a stretch two hours after the last one ended was taken on")
'''

# Named after the findings they prove, by the very function the lint looks them
# up with, so a proof test and its finding cannot drift apart here. One proof
# per *finding*, named after its **primary** — the two-alternative finding above
# owes one proof, not one for the method and another for the class enclosing it.
PROOFS: dict[str, str] = {
    proof_test_name(
        PlantedFinding(any=(Answer(file="payroll.py", symbol="overtime_pay"),)), PYTHON
    ): OVERTIME_PROOF,
    proof_test_name(
        PlantedFinding(
            any=(
                Answer(file="shifts.py", symbol="Rota.add"),
                Answer(file="shifts.py", symbol="Rota"),
            )
        ),
        PYTHON,
    ): REST_PROOF,
}

GRADING_TEST = findings_test_source().decode("utf-8")

# An additional held-out test, of the kind a task may legitimately ship beside
# the canonical one: resolution requires every grading test to pass, so this can
# only make the task harder to resolve, never let a wrong review through.
EXTRA_GRADING_TEST = f'''\
"""An additional held-out test, beside the canonical one."""

import json
from pathlib import Path


def test_the_findings_are_a_json_list():
    findings = json.loads(
        (Path.cwd() / "{ANSWER_PATH}").read_text(encoding="utf-8")
    )
    assert isinstance(findings, list)
'''

# The floor: a grading test that reads nothing and asserts nothing. It fails
# must-fail-on-pristine, so it is caught anyway — it is here to make every
# negative the lint constructs report separately, since it grades all of them
# resolved.
ALWAYS_RESOLVES_GRADING_TEST = '''\
"""A grading test that reads nothing and asserts nothing."""


def test_the_answer_reports_every_planted_finding():
    assert True
'''

# The hand-written comparison a review author reaches for, and the one this key
# exists to be more than: it asks whether *some* planted finding was reported,
# which turns "every" into "any" and resolves a review that found one defect of
# two.
ANY_MATCH_GRADING_TEST = f'''\
"""A grading test that resolves when any one planted finding was reported."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "{FINDINGS_KEY_FILE}").read_text(encoding="utf-8"))
PLANTED = {{
    (alternative["file"], alternative["symbol"])
    for planted in KEY["accepted"]
    for alternative in planted["any"]
}}
REFUSED = {{(entry["file"], entry["symbol"]) for entry in KEY["rejected"]}}


def test_the_answer_reports_every_planted_finding():
    answer_path = WORKDIR / KEY["answer_path"]
    assert answer_path.is_file(), "no answer file"
    reported = {{
        (entry["file"], entry["symbol"])
        for entry in json.loads(answer_path.read_text(encoding="utf-8"))
    }}
    assert reported & PLANTED and not reported & REFUSED
'''

# The sloppier one, and what the synthesised near-miss exists to kill: it holds
# the answer to naming every planted *file* and never reads a symbol.
FILE_ONLY_GRADING_TEST = f'''\
"""A grading test that checks each finding's file and not its symbol."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "{FINDINGS_KEY_FILE}").read_text(encoding="utf-8"))
PLANTED = {{planted["any"][0]["file"] for planted in KEY["accepted"]}}
REFUSED = {{(entry["file"], entry["symbol"]) for entry in KEY["rejected"]}}


def test_the_answer_reports_every_planted_finding():
    answer_path = WORKDIR / KEY["answer_path"]
    assert answer_path.is_file(), "no answer file"
    reported = {{
        (entry["file"], entry["symbol"])
        for entry in json.loads(answer_path.read_text(encoding="utf-8"))
    }}
    assert PLANTED <= {{file for file, _ in reported}}
    assert not reported & REFUSED
'''

# One quantifier of the two: it checks coverage of the planted findings and
# never reads the rejected half, so every-line-is-a-finding passes it.
COVERAGE_ONLY_GRADING_TEST = f'''\
"""A grading test that checks coverage and never the rejected half."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "{FINDINGS_KEY_FILE}").read_text(encoding="utf-8"))
PLANTED = {{
    (planted["any"][0]["file"], planted["any"][0]["symbol"])
    for planted in KEY["accepted"]
}}


def test_the_answer_reports_every_planted_finding():
    answer_path = WORKDIR / KEY["answer_path"]
    assert answer_path.is_file(), "no answer file"
    reported = {{
        (entry["file"], entry["symbol"])
        for entry in json.loads(answer_path.read_text(encoding="utf-8"))
    }}
    assert PLANTED <= reported
'''

# The comparison a key with alternatives exists to be more than, and what the
# per-alternative *positive* gate is for: it reads each planted finding's first
# alternative and no other, so a review that describes the second defect at the
# class the author wrote down as legitimately correct grades unresolved.
PRIMARY_ONLY_GRADING_TEST = f'''\
"""A grading test that reads each planted finding's primary and no other."""

import json
from pathlib import Path

WORKDIR = Path.cwd()
KEY = json.loads((WORKDIR / "{FINDINGS_KEY_FILE}").read_text(encoding="utf-8"))
PLANTED = {{
    (planted["any"][0]["file"], planted["any"][0]["symbol"])
    for planted in KEY["accepted"]
}}
REFUSED = {{(entry["file"], entry["symbol"]) for entry in KEY["rejected"]}}


def test_the_answer_reports_every_planted_finding():
    answer_path = WORKDIR / KEY["answer_path"]
    assert answer_path.is_file(), "no answer file"
    reported = {{
        (entry["file"], entry["symbol"])
        for entry in json.loads(answer_path.read_text(encoding="utf-8"))
    }}
    assert PLANTED <= reported
    assert not reported & REFUSED
'''

# A module whose one symbol the key accepts, so no near-miss can be synthesised
# for a finding planted in it, and the change that introduces it.
TINY = "def only():\n    return 1\n"

TINY_REVIEW_DIFF = '''\
--- a/payroll.py
+++ b/payroll.py
@@ -6,6 +6,8 @@
 def overtime_pay(hours):
     """What one stretch of work earns, in pence."""
+    if hours > OVERTIME_AFTER_HOURS:
+        return hours * RATE_PENCE * OVERTIME_MULTIPLIER
     return hours * RATE_PENCE
--- /dev/null
+++ b/tiny.py
@@ -0,0 +1,2 @@
+def only():
+    return 1
'''

# A module defining exactly one class, for the terrain rule that refuses a
# planted finding named at class level there.
SOLO = '''\
"""One thing, on its own."""


class Solo:
    """The only class its module defines."""

    def go(self):
        return 1
'''

# A prompt naming a planted finding's symbol outright: the review handed over.
NAMES_A_PLANTED_LOCATION_PROMPT = (
    f"The change in {REVIEW_DIFF_FILE} broke overtime_pay. Review it and write\n"
    f"your findings to {ANSWER_PATH}.\n"
)

# A prompt naming a *rejected* finding: the non-finding the key exists to refuse,
# handed over from the other side.
NAMES_A_REJECTED_LOCATION_PROMPT = (
    f"Something in {REVIEW_DIFF_FILE} bills the wrong number, and total_pay is\n"
    f"not where it is. Write your findings to {ANSWER_PATH}.\n"
)

# "pence" is a word of payroll.py and of no other module in the fixture
# repository, so a prompt that uses it is one grep from a planted finding.
NARROWING_PROMPT = (
    f"A week of work is coming out in the wrong pence. Review the change in\n"
    f"{REVIEW_DIFF_FILE} and write your findings to {ANSWER_PATH}.\n"
)


def write_fixture(
    root: Path,
    *,
    accepted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
    answer_path: str = ANSWER_PATH,
    prompt: str = PROMPT,
    grading_test: str | None = GRADING_TEST,
    extra_grading_tests: dict[str, str] | None = None,
    findings_module: bytes | None = None,
    answer_module: bytes | None = None,
    repo_files: dict[str, str] | None = None,
    review_diff: str | None = REVIEW_DIFF,
    key_text: str | None = None,
    ship_key: bool = True,
    task_id: str = FIXTURE_ID,
    corrected_files: dict[str, str] | None = None,
    ship_gate: bool = True,
    proof_tests: dict[str, str] | None = None,
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
    this package owns. `findings_module` and `answer_module` write other bytes
    in their place, and `grading_test=None` ships no canonical test at all —
    each for the test about the one drift it is.

    `extra_grading_tests` ships further held-out tests beside the canonical
    one, which is allowed and has to stay allowed: resolution requires every
    grading test to pass, so an extra test can only make a task harder to
    resolve.

    `key_text` writes the key file's raw bytes instead of building one, for the
    tests about a key that cannot be read at all; `ship_key=False` ships none.
    `review_diff=None` ships no diff of the change under review, and
    `repo_files` adds modules to the starting repository — passed in here
    rather than written afterwards so that a test naming one in its key gets a
    repository the whole lint agrees about.

    `proof_tests` ships the existence proof of each planted finding, keyed by
    the filename `proof_test_name` derives from the finding it proves — the
    default two, or `{}` for a task shipping none, or a bent one for the test
    about the direction it is bent in. `corrected_files` overrides what the
    corrected tree holds, for the test about a correction that does not correct.

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
    (task_dir / REPO_DIR / "people.py").write_text(PEOPLE)
    (task_dir / REPO_DIR / "swaps.py").write_text(SWAPS)
    for name, source in (repo_files or {}).items():
        (task_dir / REPO_DIR / name).write_text(source)
    if review_diff is not None:
        (task_dir / REPO_DIR / REVIEW_DIFF_FILE).write_text(review_diff)
    corrected = {
        "payroll.py": CORRECTED_PAYROLL,
        "shifts.py": CORRECTED_SHIFTS,
        "people.py": PEOPLE,
        "swaps.py": SWAPS,
    } | (corrected_files or {})
    for name, source in corrected.items():
        (task_dir / CORRECTED_DIR / name).write_text(source)
    proofs = PROOFS if proof_tests is None else proof_tests
    if proofs:
        (task_dir / PROOFS_DIR).mkdir()
        for name, source in proofs.items():
            (task_dir / PROOFS_DIR / name).write_text(source)
    if grading_test is not None:
        (task_dir / GRADING_DIR / FINDINGS_TEST_FILE).write_text(grading_test)
    for name, source in (extra_grading_tests or {}).items():
        (task_dir / GRADING_DIR / name).write_text(source)
    (task_dir / GRADING_DIR / FINDINGS_MODULE).write_bytes(
        findings_module_source() if findings_module is None else findings_module
    )
    (task_dir / GRADING_DIR / ANSWER_MODULE).write_bytes(
        answer_module_source() if answer_module is None else answer_module
    )
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
    if ship_gate:
        # The hash gate the lint requires of every task carrying a key of
        # either shape (`carries_a_key`): generated from the starting
        # repository as just written, so it is exactly what the CLI flag would
        # write. Last, because it hashes everything above.
        (task_dir / GRADING_DIR / HASH_GATE_FILE).write_bytes(
            hash_gate_source(task_dir / REPO_DIR)
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


def planted(*locations: tuple[str, str]) -> dict[str, object]:
    """One planted finding, as the key writes it: the set of alternative
    locations that legitimately describe one defect, primary first."""
    return {"any": [{"file": file, "symbol": symbol} for file, symbol in locations]}


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
    # A planted finding is a set of alternative locations, and the first of them
    # is the primary — the most specific one, and what the finding is named
    # after wherever a name is needed.
    assert key.accepted == (
        PlantedFinding(any=(Answer(file="payroll.py", symbol="overtime_pay"),)),
        PlantedFinding(
            any=(
                Answer(file="shifts.py", symbol="Rota.add"),
                Answer(file="shifts.py", symbol="Rota"),
            )
        ),
    )
    assert [found.primary for found in key.accepted] == [
        Answer(file="payroll.py", symbol="overtime_pay"),
        Answer(file="shifts.py", symbol="Rota.add"),
    ]
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
    assert task.grading_test_paths == (FINDINGS_TEST_FILE, HASH_GATE_FILE)


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
    assert task.grading_test_paths == (FINDINGS_TEST_FILE, HASH_GATE_FILE)


def test_a_review_task_inherits_none_of_the_accepted_answer_keys_rules(
    tmp_path: Path,
) -> None:
    """Every gate the fault-location key owns is gated on *that* key being on
    disk, so a review task inherits none of them: it ships no
    `accepted-answer.json`, no `test_answer.py` and no hash gate, and none of
    that is a lint problem. What it also shows is the invariant a review task
    does keep — its grading test fails on the pristine repository, which
    carries no answer file at all — and, now that the findings key has rules of
    its own, that the fixture is clean under every one of them and under all
    seven discrimination negatives."""
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
    any edit, and a key keyed on one would grade a correct finding wrong. Read
    per alternative, since that is where a location now lives."""
    with pytest.raises(IngestError, match="names a line number"):
        fixture_task(
            tmp_path,
            accepted=[
                {"any": [
                    {"file": "payroll.py", "symbol": "overtime_pay", "line": 9}
                ]}
            ],
        )


def test_a_finding_naming_a_file_alone_is_refused(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="names a file with no symbol"):
        fixture_task(tmp_path, accepted=[{"any": [{"file": "payroll.py"}]}])


def test_a_planted_finding_written_flat_is_refused_with_the_shape(
    tmp_path: Path,
) -> None:
    """A planted finding is a set of alternative locations and never one pair,
    so the flat spelling the key used to carry is refused outright — with the
    shape it should have had, because a key an author has to guess the shape of
    is a key authored by trial against a lint. There is one checked-in review
    task and it is migrated, so there is no compatibility shim to fall back
    on."""
    with pytest.raises(IngestError, match="names one location flat") as excinfo:
        fixture_task(
            tmp_path,
            accepted=[{"file": "payroll.py", "symbol": "overtime_pay"}],
        )

    assert '{"any": [{"file": ..., "symbol": ...}, ...]}' in str(excinfo.value)


def test_a_planted_finding_with_no_alternatives_is_refused(tmp_path: Path) -> None:
    """Non-empty, because a finding with no location is one no answer can match
    and every answer therefore fails."""
    with pytest.raises(IngestError, match="names no location at all"):
        fixture_task(tmp_path, accepted=[{"any": []}])


def test_no_location_is_named_twice_anywhere_in_the_key(tmp_path: Path) -> None:
    """Sets, still — and one set across the whole key rather than one per half.
    Two alternatives of one finding that name the same location claim nothing a
    single one would; two findings sharing one let a single answer satisfy both,
    so a review that spotted one defect would be graded as having spotted two;
    and a location in both halves makes every answer unresolved whatever it
    says. Refused at load, because `ai-bench run-live` loads a task set and
    never lints it."""
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path / "within-one-finding",
            accepted=[
                planted(("payroll.py", "overtime_pay")),
                planted(("shifts.py", "Rota.add"), ("shifts.py", "Rota.add")),
            ],
        )
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path / "across-two-findings",
            accepted=[*ACCEPTED, planted(("payroll.py", "overtime_pay"))],
        )
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path / "rejected-twice", rejected=REJECTED + [REJECTED[1]]
        )


def test_a_rejected_location_equal_to_an_alternative_is_refused(
    tmp_path: Path,
) -> None:
    """The two halves are read under opposite quantifiers, so a location in both
    makes every answer unresolved whatever it says: reporting it fails on the
    rejected half, and leaving it out fails on the accepted one. Read over every
    alternative, not the primaries alone — a non-primary alternative the key also
    rejects is the same contradiction one level down."""
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path / "primary",
            rejected=[*REJECTED, {"file": "payroll.py", "symbol": "overtime_pay"}],
        )
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path / "alternative",
            rejected=[*REJECTED, {"file": "shifts.py", "symbol": "Rota"}],
        )


def test_an_alternative_shared_through_the_comparison_is_refused(
    tmp_path: Path,
) -> None:
    """Stronger than equality, and it has to be: the comparison forgives a
    description level, so an answer of `add` matches an alternative spelled
    `Rota.add`. A key naming both would let that one answer cover two planted
    findings, and a review that spotted one defect would be graded as having
    spotted both — while the two spellings are not equal and a set check by
    equality would let it through."""
    with pytest.raises(IngestError, match="the same location twice over"):
        fixture_task(
            tmp_path,
            accepted=[*ACCEPTED, planted(("shifts.py", "add"))],
        )


def test_only_a_code_review_task_may_ship_a_findings_key(tmp_path: Path) -> None:
    """Gated the way the accepted-answer key is gated on its two actions: a key
    shipped by another action would hold that task to the review rules while
    its own grading never consulted the key at all."""
    with pytest.raises(IngestError, match="a feature-dev task ships"):
        fixture_task(tmp_path, category="feature-dev")


def test_a_code_review_task_names_no_behaviour_tests(tmp_path: Path) -> None:
    """Only the two split categories — `refactor` and, from round 13,
    `performance-optimisation` — split their grading suite: behaviour tests are
    exempt from must-fail-on-pristine, and a review task naming one would
    exempt the only test its verdict is made of.

    The match string moved with round 13's widening of the refusal itself
    (design note 117.6): the message names both actions now, because prose
    saying "refactor" where the code means two things is prose that misleads
    the next author of a third."""
    with pytest.raises(
        IngestError,
        match="only refactor or performance-optimisation tasks split grading",
    ):
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


def test_an_answer_at_a_non_primary_alternative_resolves(tmp_path: Path) -> None:
    """The point of the whole shape (#85). A planted finding is a set of
    alternative locations and is matched if an answer matches *any* one of them,
    so a review that describes the second defect at the class enclosing the
    defective method — a level the author wrote down as legitimately correct —
    resolves exactly as the primary does, and does not have to report the defect
    twice to do it."""
    task = fixture_task(tmp_path)

    assert resolves(
        task,
        reporting(
            finding("payroll.py", "overtime_pay"),
            finding("shifts.py", "Rota", "the rest check compares the wrong end"),
        ),
    )
    # And the alternatives are alternatives, not a second demand: one finding
    # per defect is enough, whichever level it is described at.
    assert resolves(
        task,
        reporting(
            finding("payroll.py", "overtime_pay"), finding("shifts.py", "Rota.add")
        ),
    )


def test_an_answer_at_no_alternative_of_a_finding_does_not_resolve(
    tmp_path: Path,
) -> None:
    """The alternatives widen what answers a finding; they do not stop it being
    a finding. A symbol of the right file that is none of them leaves the
    finding unmatched, so the run is unresolved."""
    task = fixture_task(tmp_path)

    assert not resolves(
        task,
        reporting(
            finding("payroll.py", "overtime_pay"), finding("shifts.py", "Shift")
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


# --- the lint: what the findings key has to say, read rather than run ----------
#
# Every rule below is proved in both directions: the fixture above lints clean
# under all of them (`test_a_review_task_inherits_none_of_the_accepted_answer_
# keys_rules`), and each test here bends it in exactly one way and asserts the
# message names the task and the finding that is wrong.


def test_lint_refuses_a_findings_key_that_plants_nothing(tmp_path: Path) -> None:
    """The loader refuses this too, so the fixture is built without going
    through it: `lint_task_set` takes an already-loaded list of tasks, and a
    key planting nothing grades *every* agent resolved, because "every planted
    finding was reported" is vacuously true of no planted findings."""
    task_dir = write_fixture(tmp_path, accepted=[])
    spec = yaml.safe_load((task_dir / "task.yaml").read_text())
    task = Task.model_validate(spec | {"directory": task_dir})

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "plants no findings" in problem


def test_lint_requires_at_least_one_rejected_finding(tmp_path: Path) -> None:
    """The rejected half is what a review verdict cannot be built without: the
    accepted half on its own is survived by an answer that reports every line
    of the change as a defect, and must-fail-on-pristine says nothing here
    because a pristine repository carries no answer file at all."""
    task = fixture_task(tmp_path, rejected=[])

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "no rejected findings" in problem


def test_lint_refuses_a_planted_finding_outside_the_change_under_review(
    tmp_path: Path,
) -> None:
    """A review judges a change. `swaps.py` is a module of the repository the
    change does not touch, so a finding planted there is a defect the agent was
    never asked to look at — and the key would describe the repository at large
    rather than the change, which is the one thing the shipped diff exists to
    tell them apart by."""
    task = fixture_task(
        tmp_path, accepted=[*ACCEPTED, planted(("swaps.py", "hand_over"))]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'hand_over'" in problem
    assert "does not touch 'swaps.py'" in problem


def test_lint_refuses_a_rejected_finding_outside_the_change_under_review(
    tmp_path: Path,
) -> None:
    """The same rule over the other half, and it belongs there: a rejected
    finding outside the change fails a run for reporting a real problem of the
    repository the author did not plant, which the verdict archives everywhere
    else."""
    task = fixture_task(
        tmp_path, rejected=[*REJECTED, {"file": "swaps.py", "symbol": "handed"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'handed'" in problem
    assert "does not touch 'swaps.py'" in problem


def test_lint_refuses_a_review_task_that_ships_no_diff_of_the_change(
    tmp_path: Path,
) -> None:
    """The change under review is applied to the starting repository, so the
    shipped diff is the only thing that says which of that repository is the
    change: without it the key cannot be held to describing one."""
    task = fixture_task(tmp_path, review_diff=None)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and REVIEW_DIFF_FILE in problem
    assert "the repository at large" in problem


def test_lint_refuses_a_finding_naming_a_file_that_is_not_in_the_repository(
    tmp_path: Path,
) -> None:
    task = fixture_task(tmp_path, accepted=[planted(("wages.py", "overtime_pay"))])

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    assert any(
        "wages.py" in problem and "starting repository" in problem
        for problem in problems
    )


def test_lint_refuses_a_finding_naming_a_file_matching_only_by_case(
    tmp_path: Path,
) -> None:
    """`Path.is_file()` is case-insensitive on macOS, the platform the sweeps
    run on, so "payroll.PY" must not silently resolve to "payroll.py" — the
    comparison that later reads the agent's findings is case-exact on both
    halves and would never match."""
    task = fixture_task(tmp_path, accepted=[planted(("payroll.PY", "overtime_pay"))])

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    assert any(
        "payroll.PY" in problem and "starting repository" in problem
        for problem in problems
    )


def test_lint_refuses_a_finding_naming_a_symbol_the_file_does_not_define(
    tmp_path: Path,
) -> None:
    """A rename or a typo: a planted finding no correct review can report."""
    task = fixture_task(tmp_path, accepted=[planted(("payroll.py", "overtime_py"))])

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "overtime_py" in problem
    assert "does not define" in problem


def test_lint_refuses_a_bare_finding_where_a_qualified_spelling_exists(
    tmp_path: Path,
) -> None:
    """`matches()` is one-directional: a bare *answer* matches a qualified key,
    never the reverse. So a key spelled `add` would refuse the `Rota.add` a
    reviewer would most naturally write, and grade a correct review
    unresolved."""
    task = fixture_task(
        tmp_path, accepted=[ACCEPTED[0], planted(("shifts.py", "add"))]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'add'" in problem
    assert "'Rota.add'" in problem


@pytest.mark.parametrize(
    "answer_path",
    [
        FINDINGS_KEY_FILE,  # collides with the key itself
        FINDINGS_TEST_FILE,  # collides with the held-out grading test
        "/tmp/abs.json",  # absolute, outside the workdir
        "../ESCAPE.json",  # escapes the workdir
    ],
)
def test_lint_refuses_an_answer_path_that_cannot_reach_the_verdict(
    tmp_path: Path, answer_path: str
) -> None:
    """Two of these collide with a file the grading overlay writes over the
    workdir, so the agent's findings are silently overwritten before the
    verdict reads them; two never land in the workdir diff at all. The prompt
    is made to name the path exactly, so the only problem reported is the one
    this test targets."""
    task = fixture_task(
        tmp_path,
        answer_path=answer_path,
        prompt=(
            f"Review the change in {REVIEW_DIFF_FILE} and write your findings "
            f"to {answer_path}.\n"
        ),
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and answer_path in problem


def test_lint_accepts_an_answer_path_inside_a_directory_of_its_own(
    tmp_path: Path,
) -> None:
    """The other direction of the four refusals above, and it runs the whole
    gate: a relative path inside the workdir that names neither the key nor a
    grading file lints clean, negatives and all."""
    task = fixture_task(
        tmp_path,
        answer_path="notes/FINDINGS.json",
        prompt=(
            f"Review the change in {REVIEW_DIFF_FILE} and write your findings "
            "to notes/FINDINGS.json.\n"
        ),
    )

    assert lint_task_set([task]) == []


def test_lint_refuses_a_prompt_that_never_names_the_answer_file(
    tmp_path: Path,
) -> None:
    """A task cannot be unsolvable because the agent was never told where to
    write: the answer file is the whole deliverable of a review."""
    task = fixture_task(
        tmp_path,
        prompt=(
            f"Review the change in {REVIEW_DIFF_FILE} and write down each "
            "problem it introduced.\n"
        ),
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and ANSWER_PATH in problem
    assert "prompt" in problem


# --- the lint: the canonical bytes a review task ships -------------------------


def test_lint_refuses_an_edited_copy_of_the_findings_comparison(
    tmp_path: Path,
) -> None:
    """One byte is enough. The comparison is the half of the verdict that
    discriminates, so six review authors must not be able to hand-copy six
    comparisons that quietly disagree about what a finding is."""
    task = fixture_task(tmp_path, findings_module=findings_module_source() + b"\n")

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and FINDINGS_MODULE in problem
    assert "not the comparison this project ships" in problem


def test_lint_refuses_an_edited_copy_of_the_answer_comparison_beside_it(
    tmp_path: Path,
) -> None:
    """The findings comparison imports its forgiveness rather than restating
    it, so `_answer.py` ships beside it and is as load-bearing: a copy that
    forgave case, or stopped stripping the trailing "()", would grade this task
    by rules no other task is graded by."""
    task = fixture_task(tmp_path, answer_module=answer_module_source() + b"\n")

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and ANSWER_MODULE in problem
    assert "not the comparison this project ships" in problem


def test_lint_refuses_a_grading_directory_without_the_canonical_held_out_test(
    tmp_path: Path,
) -> None:
    """Shipping `_findings.py` byte for byte proves nothing about whether the
    task's grading test still calls it, which is why the test is canonical
    too."""
    task = fixture_task(
        tmp_path,
        grading_test=None,
        extra_grading_tests={"test_review.py": EXTRA_GRADING_TEST},
    )

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    assert any(
        FINDINGS_TEST_FILE in problem and "missing or unreadable" in problem
        for problem in problems
    )


def test_lint_refuses_a_hand_written_grading_test_under_the_canonical_name(
    tmp_path: Path,
) -> None:
    """Both halves of the same refusal, on one fixture: the bytes are not the
    ones this project ships, and what the hand-written test actually does — ask
    whether *some* planted finding was reported — is caught by the negative a
    set verdict has to earn."""
    task = fixture_task(tmp_path, grading_test=ANY_MATCH_GRADING_TEST)

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    assert any(
        "not the held-out grading test this project ships" in problem
        for problem in problems
    )
    assert any("every planted finding but" in problem for problem in problems)


def test_an_additional_grading_test_beside_the_canonical_one_is_allowed(
    tmp_path: Path,
) -> None:
    """Not a ban on other grading tests, only a requirement that the canonical
    one is among them, unedited: resolution requires every grading test to
    pass, so an extra test can only make a task harder to resolve, never let a
    wrong review through. The reference solution still resolves, and the whole
    discrimination gate still comes out clean."""
    task = fixture_task(
        tmp_path, extra_grading_tests={"test_review.py": EXTRA_GRADING_TEST}
    )

    assert task.grading_test_paths == (FINDINGS_TEST_FILE, "test_review.py", HASH_GATE_FILE)
    assert lint_task_set([task]) == []
    assert resolves(task, every_planted_finding())


# --- the lint: the discrimination gate, run through the real pipeline ----------


def test_lint_runs_every_discrimination_negative_through_the_real_pipeline(
    tmp_path: Path,
) -> None:
    """What a review task has to earn before a paid run. Shown on a grading
    test that grades everything resolved, so each negative reports separately:
    the three a locate task is held to, and the four a set-shaped verdict adds
    — every planted finding but one, the synthesised near-miss per planted
    finding per alternative's file, every planted finding plus a rejected one,
    and each rejected finding on its own. Every finding is named by its
    **primary**, including the one two alternatives describe: what "all planted
    but one" drops is a whole finding, alternatives and all, because dropping
    one alternative and leaving another would leave an answer the verdict is
    supposed to resolve."""
    task = fixture_task(tmp_path, grading_test=ALWAYS_RESOLVES_GRADING_TEST)

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    for negative in (
        "wrote no answer file at all",
        "an empty answer file",
        "a malformed answer file",
        "every planted finding but ('payroll.py', 'overtime_pay')",
        "every planted finding but ('shifts.py', 'Rota.add')",
        "registers on neither side",
        "reported beside them",
        "on its own",
    ):
        assert any(negative in problem for problem in problems), negative
    # No negative drops half of the two-alternative finding and keeps the rest:
    # that answer resolves by design, so requiring it unresolved would be
    # requiring the mitigation not to work.
    assert not any(
        "every planted finding but ('shifts.py', 'Rota')" in problem
        for problem in problems
    )


def test_lint_requires_every_alternative_of_every_finding_to_resolve(
    tmp_path: Path,
) -> None:
    """The one gate here that demands *resolved*, and the point of the whole
    shape: each alternative is the author's written claim that a review
    describing the defect there is correct, and until this ran that claim was
    trusted rather than checked. Shown on a comparison that reads each planted
    finding's primary and no other — a key whose second alternative it cannot
    match reads as a mitigation and is none."""
    task = fixture_task(tmp_path, grading_test=PRIMARY_ONLY_GRADING_TEST)

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    assert any(
        "reported at its alternative ('shifts.py', 'Rota')" in problem
        and "grades unresolved" in problem
        for problem in problems
    ), problems


def test_lint_refuses_a_comparison_that_asks_whether_some_finding_matched(
    tmp_path: Path,
) -> None:
    """The load-bearing negative of a set verdict, and the whole reason this
    key is a second key rather than a second use of the first: a comparison
    reading the accepted half under "any" instead of "every" resolves a review
    that found one of two defects, and only "all planted findings but one"
    catches it."""
    task = fixture_task(tmp_path, grading_test=ANY_MATCH_GRADING_TEST)

    problems = lint_task_set([task])

    assert any(
        "every planted finding but ('payroll.py', 'overtime_pay')" in problem
        for problem in problems
    )


def test_lint_refuses_a_comparison_that_reads_the_file_and_not_the_symbol(
    tmp_path: Path,
) -> None:
    """The synthesised near-miss, per planted finding: the right file, a symbol
    of it the key registers on neither side. A comparison checking that every
    planted *file* was named resolves it, and nothing the author wrote down
    would have caught that."""
    task = fixture_task(tmp_path, grading_test=FILE_ONLY_GRADING_TEST)

    problems = lint_task_set([task])

    assert any("registers on neither side" in problem for problem in problems)


def test_lint_refuses_a_comparison_that_never_reads_the_rejected_half(
    tmp_path: Path,
) -> None:
    """The other quantifier: a comparison that only checks coverage resolves an
    answer that reported every planted finding *and* a place the change is
    correct, which is every-line-is-a-finding passing."""
    task = fixture_task(tmp_path, grading_test=COVERAGE_ONLY_GRADING_TEST)

    problems = lint_task_set([task])

    assert any("reported beside them" in problem for problem in problems)


def test_lint_reports_a_planted_finding_it_cannot_construct_a_near_miss_for(
    tmp_path: Path,
) -> None:
    """The near-miss is the load-bearing negative, so a planted finding whose
    file leaves no unregistered symbol behind has to say so rather than have
    one check quietly not run. `tiny.py` defines one symbol and the key accepts
    it, so there is nowhere else in that file a reviewer could have pointed."""
    task = fixture_task(
        tmp_path,
        accepted=[ACCEPTED[0], planted(("tiny.py", "only"))],
        rejected=[REJECTED[0]],
        repo_files={"tiny.py": TINY},
        review_diff=TINY_REVIEW_DIFF,
    )

    problems = lint_task_set([task])

    assert any(
        "no near-miss can be constructed for the planted finding "
        "('tiny.py', 'only') in tiny.py" in problem
        for problem in problems
    )
    assert all(FIXTURE_ID in problem for problem in problems)


def test_lint_synthesises_a_near_miss_per_alternatives_file(tmp_path: Path) -> None:
    """The near-miss is built per finding *per alternative's file*, not per
    finding. A finding whose alternatives sit in two files is read the file way
    in two places, so a near-miss in the primary's file alone would leave the
    second unchecked. Shown by a finding whose second alternative is in a file
    that leaves no unregistered symbol behind: the primary's file has a
    near-miss and reports nothing, and the problem names the other file."""
    task = fixture_task(
        tmp_path,
        accepted=[planted(("payroll.py", "overtime_pay"), ("tiny.py", "only"))],
        rejected=[REJECTED[0]],
        repo_files={"tiny.py": TINY},
        review_diff=TINY_REVIEW_DIFF,
    )

    problems = lint_task_set([task])

    assert any(
        "no near-miss can be constructed for the planted finding "
        "('payroll.py', 'overtime_pay') in tiny.py" in problem
        for problem in problems
    )
    assert not any(
        "('payroll.py', 'overtime_pay') in payroll.py" in problem
        for problem in problems
    )


# --- the lint: the three terrain rules reach a review task too (#65, #70) ------
#
# Keyed on the task carrying a key rather than on which key it carries, because
# the reason does not distinguish them: a review task's findings key names the
# very locations its answer file has to report, so a prompt that names one, or
# that uses a word one grep from the module a defect was planted in, measures
# grepping rather than reviewing.
#
# The first test below runs the whole lint, because the wiring is the claim.
# The rest read `_terrain_problems`, which is the very function `lint_task_set`
# calls, so that proving four more rules does not pay for four more runs of the
# whole discrimination gate, negatives, positives and all.


def test_lint_refuses_a_prompt_naming_a_planted_findings_location(
    tmp_path: Path,
) -> None:
    """Terrain rule 1, through the whole lint: a review task carrying a
    findings key is held to the rules a keyed task is held to, and the prompt
    that names a planted finding's symbol has handed over the review."""
    task = fixture_task(tmp_path, prompt=NAMES_A_PLANTED_LOCATION_PROMPT)

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "'overtime_pay'" in problem
    assert "prompt-names-a-key-location" in problem


def test_the_terrain_rules_read_a_rejected_finding_too(tmp_path: Path) -> None:
    """The same rule from the other side: a prompt naming a *rejected* finding
    has told the agent which non-finding to avoid, which makes the review
    unfair in the agent's favour as surely as naming a planted one does."""
    task = fixture_task(tmp_path, prompt=NAMES_A_REJECTED_LOCATION_PROMPT)

    [problem] = _terrain_problems(task)

    assert FIXTURE_ID in problem and "'total_pay'" in problem
    assert "rejected" in problem


def test_the_terrain_rules_refuse_a_prompt_word_that_narrows_to_a_planted_module(
    tmp_path: Path,
) -> None:
    """Terrain rule 2. "pence" is a word of `payroll.py` and of no other module
    here, so one grep of the prompt's own vocabulary lands in a module a defect
    was planted in."""
    task = fixture_task(tmp_path, prompt=NARROWING_PROMPT)

    [problem] = _terrain_problems(task)

    assert FIXTURE_ID in problem and "'pence'" in problem
    assert "prompt-word-narrows-to-the-accepted-module" in problem


def test_the_terrain_rules_refuse_a_planted_class_that_is_its_files_only_class(
    tmp_path: Path,
) -> None:
    """Terrain rule 3. An agent electing to report a finding at class level
    reports the class, and where the module defines exactly one, that finding
    is determined by the filename alone."""
    task = fixture_task(
        tmp_path,
        accepted=[ACCEPTED[0], planted(("solo.py", "Solo"))],
        repo_files={"solo.py": SOLO},
    )

    [problem] = _terrain_problems(task)

    assert FIXTURE_ID in problem and "solo.py:Solo" in problem
    assert "accepted-class-is-the-only-class" in problem


def test_a_terrain_waiver_silences_exactly_its_own_violation_on_a_review_task(
    tmp_path: Path,
) -> None:
    """The waiver reaches a review task unchanged, and both properties that
    make it a declaration rather than a mute button come with it: it silences
    only what it names, and one naming something the rule did not fire on is
    itself a problem."""
    waived = fixture_task(
        tmp_path / "waived",
        prompt=NARROWING_PROMPT,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": ["pence"],
            "reason": "the sum in question is stated in pence and nothing else",
        }],
    )
    elsewhere = fixture_task(
        tmp_path / "elsewhere",
        prompt=NARROWING_PROMPT,
        terrain_waiver=[{
            "rule": "prompt-word-narrows-to-the-accepted-module",
            "covers": ["midnight"],
            "reason": "a word this prompt does not in fact use",
        }],
    )

    assert _terrain_problems(waived) == []

    problems = _terrain_problems(elsewhere)

    assert any("'pence'" in problem for problem in problems)
    assert any(
        "'midnight'" in problem and "the rule does not fire on" in problem
        for problem in problems
    )


# --- the hash gate reaches a review task too (#72) ------------------------------


def test_a_review_task_that_ships_no_hash_gate_is_reported(tmp_path: Path) -> None:
    """The gate is discovered off either key (`carries_a_key`): a review's
    deliverable is the findings file, and a run that repaired the change and
    then reviewed it correctly is the same exposure the locate tasks' gate
    closes. #72's first session shipped a prompt promising the gate and no
    gate, and the lint let it through — this is what closes that."""
    task = fixture_task(tmp_path, ship_gate=False)

    problems = [p for p in lint_task_set([task]) if HASH_GATE_FILE in p]

    assert len(problems) == 1
    assert FIXTURE_ID in problems[0]


def test_a_review_that_also_repaired_the_change_is_unresolved(tmp_path: Path) -> None:
    """What the gate buys on a review: the same complete, correct answer that
    resolves on its own grades unresolved once the repair rides along with it."""
    task = fixture_task(tmp_path)
    corrected = (task.corrected_dir / "payroll.py").read_text()

    def reviewed_and_repaired(workdir: Path) -> None:
        (workdir / ANSWER_PATH).write_text(every_planted_finding())
        (workdir / "payroll.py").write_text(corrected)

    assert resolves(task, every_planted_finding())
    assert not grade(task, workdir_diff(task, reviewed_and_repaired))
