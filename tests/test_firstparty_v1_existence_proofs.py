"""The existence proof: what says a planted truth is there at all (#71, design
note §45.4).

Every other gate the task-set lint runs on a keyed task asks whether its grading
*discriminates* — whether the held-out test can tell a correct answer from a
wrong one. None of them asks the prior question. A key naming a location no
defect lives at, a review whose "planted" findings are correct code, a question
about behaviour the repository does not have: each lints clean under everything
else and then grades every agent unresolved for a reason that says nothing about
the agent.

Round 4 answered it for `fault-location` by convention — the locate member was
authored beside a `bug-fix` partner whose held-out tests fail on the same
pristine repository — and named its own trigger to revisit: the first
fault-location-style task with no partner. Round 5 authors exactly that, so the
convention is a rule here, with a **registry** of proof forms per action:

- `fault-location` → the partner `bug-fix` task exists and fails pristine, found
  by the bytes of the starting repository the two share, because the two are
  deliberately neither a task family nor a pair and so declare no link to read;
- `code-review` → per planted finding, a held-out test that fails on the
  starting repository (which ships the change under review applied) and passes
  on the author's corrected tree;
- `codebase-comprehension` → every accepted (file, symbol) resolves in the
  starting repository, which was already a rule of the key and is registered as
  this action's form so that a fourth keyed action cannot be added without one;
- `test-authoring` → the author's reference suite passes on the pristine
  starting repository and fails on every planted mutant, checked per mutant
  (round 8, design note §67.5) — the fourth keyed action, registered here
  because the rule above said it had to be, and owned by
  `test_firstparty_v1_mutation_lint.py`.

Where the proofs live is what keeps them the lint's and never grading's: beside
`repo/` and outside `grading/`, which the loader enforces rather than leaving to
an author's discipline.

The fixtures are the ones the suites that own each action already build — this
suite adds the rule, not a fourth repository to keep in step — and the six
checked-in round-4 fault-location tasks are put to the new partner check
unchanged, because the convention they were authored under is exactly what this
rule is supposed to have been all along.
"""

import shutil
from functools import cache
from pathlib import Path

import pytest
from firstparty_v1_tasks import TASKS
from test_firstparty_v1_code_review import FIXTURE_ID as REVIEW_ID
from test_firstparty_v1_code_review import PAYROLL, PROOFS, REST_PROOF
from test_firstparty_v1_code_review import every_planted_finding, resolves
from test_firstparty_v1_code_review import fixture_task as review_fixture
from test_firstparty_v1_code_review import write_fixture as write_review_fixture
from test_firstparty_v1_codebase_comprehension import (
    FIXTURE_ID as COMPREHENSION_ID,
)
from test_firstparty_v1_codebase_comprehension import (
    fixture_task as comprehension_fixture,
)
from test_firstparty_v1_fault_location import FIXTURE_ID as LOCATE_ID
from test_firstparty_v1_fault_location import PARTNER_ID
from test_firstparty_v1_fault_location import fixture_task as fault_location_fixture
from test_firstparty_v1_fault_location import write_partner

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    CORRECTED_DIR,
    EXISTENCE_PROOFS,
    FINDINGS_TEST_FILE,
    HASH_GATE_FILE,
    GRADE_TIMEOUT_S,
    GRADING_DIR,
    PROOFS_DIR,
    REPO_DIR,
    Task,
    _existence_proof_problems,
    _proof_test_passes,
    findings_key,
    lint_task_set,
    load_task_set,
    proof_test_name,
)

# Every action that carries a key, and so every action that owes a proof form.
# Spelled out rather than derived from the registry it is read against, because
# a test that computed both sides from one source would pass however wrong that
# source was.
KEYED_ACTIONS = {
    "fault-location",
    "codebase-comprehension",
    "code-review",
    "test-authoring",
    "investigation",
}

# A partner whose held-out tests *pass* on the starting repository the two
# share: a bug-fix task with nothing to fix, which is what a locate member built
# on a repository with no defect in it would be paired with.
PARTNER_THAT_PROVES_NOTHING = '''\
"""A held-out test that passes on the pristine repository."""

import checkout


def test_the_rate_is_the_one_the_till_was_given():
    assert checkout.TAX_PERCENT == 15
'''

# A proof test that passes wherever it is run — on the starting repository as
# readily as on the corrected tree — so the only thing wrong with it is the
# direction this suite is about. `RATE_PENCE` is untouched by the correction.
PROOF_THAT_PASSES_ON_THE_STARTING_REPOSITORY = '''\
"""A proof test that demonstrates nothing was wrong."""

from payroll import RATE_PENCE


def test_the_rate_is_what_it_was():
    assert RATE_PENCE == 1200
'''

# An additional held-out grading test, run inside the graded workdir, asserting
# that neither tree the lint reads was overlaid into it. Held-out means held out
# of the agent's workdir; these two are held out of the *graded* workdir as
# well, and this is the assertion that says so from inside it.
NOTHING_THE_LINT_READS_REACHED_THE_WORKDIR = f'''\
"""An additional held-out test: what grading did and did not copy."""

from pathlib import Path


def test_neither_the_proofs_nor_the_corrected_tree_was_overlaid():
    workdir = Path.cwd()
    assert not (workdir / "{PROOFS_DIR}").exists()
    assert not (workdir / "{CORRECTED_DIR}").exists()
'''


@cache
def checked_in_fault_location_tasks() -> tuple[tuple[Task, ...], tuple[Task, ...]]:
    """The whole checked-in task set, and the fault-location tasks in it.

    Cached because the partner check is parametrized over the six, and loading a
    hundred task directories once per parameter is the slow half of that."""
    tasks = tuple(load_task_set(TASKS))
    return tasks, tuple(task for task in tasks if task.category == "fault-location")


# --- the registry ---------------------------------------------------------------


def test_every_action_that_carries_a_key_registers_a_proof_form() -> None:
    """The registry is the whole of what is registered: four actions carry a
    key, and each names what would prove its truth exists."""
    assert set(EXISTENCE_PROOFS) == KEYED_ACTIONS
    assert all(proof.form.strip() for proof in EXISTENCE_PROOFS.values())


def test_an_action_with_no_registered_proof_form_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the registry buys: a fourth keyed action cannot be added without
    saying what would prove its truth exists. Shown by taking a registered form
    away — the corpus-level refusal names the action, and the task that would
    have been swept under it is refused in its own right rather than passing
    through a gate that checked nothing."""
    task = fault_location_fixture(tmp_path)
    partner = write_partner(task)
    monkeypatch.delitem(EXISTENCE_PROOFS, "fault-location")

    problems = lint_task_set([task, partner])

    assert any(
        "carry a key and register no existence proof" in problem
        and "fault-location" in problem
        for problem in problems
    )
    assert any(
        LOCATE_ID in problem and "registers no existence proof" in problem
        for problem in problems
    )


def test_the_lint_dispatches_off_the_registry(tmp_path: Path) -> None:
    """What a task is held to is the entry its action registers, and nothing
    else: dispatched off the registry rather than off a chain of category tests,
    so the three forms are one list a reader can see the whole of."""
    task = comprehension_fixture(
        tmp_path, accepted=[{"file": "push.py", "symbol": "PushChannel"}]
    )
    registered = EXISTENCE_PROOFS[task.category]

    dispatched = _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S)

    assert dispatched
    assert dispatched == registered.check(task, [task], GRADE_TIMEOUT_S)


# --- fault-location: the partner, found by shared bytes and run ------------------


def test_a_fault_location_task_with_no_partner_is_refused(tmp_path: Path) -> None:
    """The trigger the convention named, and the whole reason this is a rule: a
    locate task authored alone has nothing saying there is a defect in it to
    find. Everything else about this fixture is clean, so the one problem
    reported is this one."""
    task = fault_location_fixture(tmp_path)

    [problem] = lint_task_set([task])

    assert LOCATE_ID in problem
    assert "bug-fix" in problem and REPO_DIR in problem


def test_a_partner_sharing_the_starting_repository_is_the_proof(
    tmp_path: Path,
) -> None:
    """The other direction: with the partner in the set, the same fixture lints
    clean — and the partner is found by the bytes of the repository the two
    share, there being no declared link between them to read."""
    task = fault_location_fixture(tmp_path)
    partner = write_partner(task)

    assert partner.category == "bug-fix"
    assert lint_task_set([task, partner]) == []


def test_a_partner_that_passes_on_the_pristine_repository_is_refused(
    tmp_path: Path,
) -> None:
    """Existing is not enough. A partner whose held-out tests pass on the
    repository the two share says the repository has nothing wrong with it, so
    the locate task asks where a defect lives that its own partner cannot
    demonstrate."""
    task = fault_location_fixture(tmp_path)
    partner = write_partner(task)
    (partner.grading_dir / "test_tax.py").write_text(PARTNER_THAT_PROVES_NOTHING)

    problems = lint_task_set([task, partner])

    assert any(
        problem.startswith(f"{LOCATE_ID}:")
        and PARTNER_ID in problem
        and "pass on the starting repository" in problem
        for problem in problems
    ), problems


def test_a_bug_fix_task_on_a_different_repository_is_not_the_partner(
    tmp_path: Path,
) -> None:
    """Shared bytes are the whole of the relation, so a bug-fix task that starts
    from a different repository proves nothing about this one — which is what
    stops the rule from being satisfied by any bug-fix task that happens to be
    in the set."""
    task = fault_location_fixture(tmp_path)
    partner = write_partner(task)
    (partner.repo_dir / "elsewhere.py").write_text("SOMETHING_ELSE = 1\n")

    [problem] = lint_task_set([task, partner])

    assert LOCATE_ID in problem and "bug-fix" in problem


@pytest.mark.parametrize(
    "task_id",
    [
        "allotments-locate-the-swallowed-reading",
        "ferry-locate-the-idle-boat",
        "lostproperty-locate-the-wrong-write-up",
        "noticeboard-locate-the-lost-notice",
        "paperround-locate-the-carried-over-count",
        "postoffice-locate-the-wrong-band",
    ],
)
def test_every_round_four_locate_task_passes_the_partner_check_unchanged(
    task_id: str,
) -> None:
    """The six tasks authored under the convention, put to the rule that
    replaced it. Nothing about them changes: each was already authored beside a
    bug-fix member sharing `repo/` byte for byte, which is exactly what the lint
    now goes looking for."""
    tasks, located = checked_in_fault_location_tasks()
    [task] = [candidate for candidate in located if candidate.id == task_id]

    assert _existence_proof_problems(task, tasks, timeout_s=GRADE_TIMEOUT_S) == []


def test_the_checked_in_corpus_holds_exactly_the_six_locate_tasks() -> None:
    """What the parametrization above is a list of, asserted rather than
    trusted: a seventh fault-location task added without a line here would
    otherwise be swept with its partner check never run."""
    _, located = checked_in_fault_location_tasks()

    # Nine since round 7: round 4's six Python locate tasks and the three
    # TypeScript ones (#105-#107), each still authored beside a bug-fix partner
    # on a shared starting repository.
    assert len(located) == 9


# --- code-review: a proof test per planted finding, run against two trees --------


def test_each_planted_finding_is_proved_in_both_directions(tmp_path: Path) -> None:
    """What a review task's proof form asserts, on the proofs themselves: each
    fails on the starting repository, where the change under review ships
    applied, and passes on the author's corrected tree. Both halves matter, and
    for different reasons — a proof that passed on the starting repository would
    say the finding is not a defect, and one that failed on the corrected tree
    would say the author cannot fix what they planted."""
    task = review_fixture(tmp_path)

    for finding in findings_key(task).accepted:
        proof = task.proofs_dir / proof_test_name(finding, task.runner)
        assert proof.is_file(), finding
        assert not _proof_test_passes(
            task.repo_dir,
            proof,
            runner=task.runner,
            timeout_s=GRADE_TIMEOUT_S,
        ), finding
        assert _proof_test_passes(
            task.corrected_dir,
            proof,
            runner=task.runner,
            timeout_s=GRADE_TIMEOUT_S,
        ), finding
    assert lint_task_set([task]) == []


def test_a_planted_finding_with_no_proof_test_is_refused(tmp_path: Path) -> None:
    """A "finding" nothing demonstrates is a preference, and the verdict would
    grade every agent against it."""
    [_, rest] = list(PROOFS)
    task = review_fixture(tmp_path, proof_tests={rest: REST_PROOF})

    [problem] = lint_task_set([task])

    assert REVIEW_ID in problem
    assert "('payroll.py', 'overtime_pay')" in problem
    assert "has no existence proof" in problem


def test_a_proof_test_that_passes_on_the_starting_repository_is_refused(
    tmp_path: Path,
) -> None:
    """The starting repository ships the change under review already applied, so
    a proof that passes there demonstrates that nothing is wrong — and a verdict
    on this task would fail every agent that declined to report the finding."""
    [overtime, _] = list(PROOFS)
    task = review_fixture(
        tmp_path,
        proof_tests=PROOFS | {overtime: PROOF_THAT_PASSES_ON_THE_STARTING_REPOSITORY},
    )

    [problem] = lint_task_set([task])

    assert REVIEW_ID in problem
    assert "('payroll.py', 'overtime_pay')" in problem
    assert "passes on the starting repository" in problem


def test_a_proof_test_that_fails_on_the_corrected_tree_is_refused(
    tmp_path: Path,
) -> None:
    """The other direction, on the same proof test: the corrected tree here
    leaves `payroll.py` exactly as the change under review left it, so the proof
    still fails there — the author has planted a finding they have not shown how
    to put right."""
    task = review_fixture(tmp_path, corrected_files={"payroll.py": PAYROLL})

    [problem] = lint_task_set([task])

    assert REVIEW_ID in problem
    assert "('payroll.py', 'overtime_pay')" in problem
    assert "fails on the corrected tree" in problem


def test_a_review_task_with_no_corrected_tree_is_refused(tmp_path: Path) -> None:
    """Half of every finding's proof is the tree the correction lives in, so
    without it nothing can be shown to have been fixed."""
    task_dir = write_review_fixture(tmp_path)
    shutil.rmtree(task_dir / CORRECTED_DIR)
    [task] = load_task_set(tmp_path)

    [problem] = lint_task_set([task])

    assert REVIEW_ID in problem and CORRECTED_DIR in problem


def test_a_proof_test_is_named_after_the_primary_of_the_finding_it_proves() -> None:
    """Derived from the finding rather than declared in the key, so that a proof
    and the finding it proves cannot drift apart — there is no third place
    saying which is which. Named after the finding's **primary** alternative,
    the most specific location it carries, so adding a second alternative to a
    finding renames nothing. Case is kept, because the key's symbols are matched
    case-exactly."""
    [overtime, rest] = list(PROOFS)

    assert overtime == "test_payroll_py_overtime_pay.py"
    assert rest == "test_shifts_py_Rota_add.py"


def test_a_finding_with_two_alternatives_owes_one_proof_and_not_two(
    tmp_path: Path,
) -> None:
    """A planted finding is one defect however many locations legitimately
    describe it, so it carries one existence proof: a second proof for the class
    enclosing the defective method would demonstrate the same failure twice, and
    demanding one would make every alternative an author added cost a test.
    The fixture's second finding names both `Rota.add` and `Rota`, ships the one
    proof named after `Rota.add`, and is proved."""
    task = review_fixture(tmp_path)
    both = findings_key(task).accepted[1]

    assert len(both.any) == 2
    assert proof_test_name(both, task.runner) == "test_shifts_py_Rota_add.py"
    assert sorted(path.name for path in task.proofs_dir.iterdir()) == sorted(PROOFS)
    assert _existence_proof_problems(task, [task], timeout_s=GRADE_TIMEOUT_S) == []


# --- codebase-comprehension: the accepted location resolves ----------------------


def test_a_comprehension_answer_that_does_not_resolve_is_refused(
    tmp_path: Path,
) -> None:
    """This action's registered form, in the direction that catches something: a
    question about behaviour the repository does not have. There is no defect
    behind a locate-style comprehension task and so no partner that could fail
    on its repository — what has to exist is the behaviour the question asks
    after, and a location that resolves is that."""
    task = comprehension_fixture(
        tmp_path, accepted=[{"file": "push.py", "symbol": "PushChannel"}]
    )

    problems = EXISTENCE_PROOFS["codebase-comprehension"].check(
        task, [task], GRADE_TIMEOUT_S
    )

    assert any(
        COMPREHENSION_ID in problem and "push.py" in problem for problem in problems
    )
    # And through the whole lint, which reads the same rule off the key before
    # the proof is reached rather than reporting it twice.
    assert any(
        COMPREHENSION_ID in problem and "push.py" in problem
        for problem in lint_task_set([task])
    )


# --- the layout: what the lint reads and grading never sees ----------------------


def test_the_proofs_and_the_corrected_tree_sit_outside_grading(
    tmp_path: Path,
) -> None:
    """Both are beside `repo/` in the task directory, and neither is a grading
    test — so nothing collects them and the verdict cannot depend on one."""
    task = review_fixture(tmp_path)

    assert task.proofs_dir.parent == task.directory
    assert task.corrected_dir.parent == task.directory
    assert task.grading_dir not in task.proofs_dir.parents
    assert task.grading_test_paths == (FINDINGS_TEST_FILE, HASH_GATE_FILE)


@pytest.mark.parametrize("subtree", [PROOFS_DIR, CORRECTED_DIR])
def test_the_loader_refuses_a_proof_or_a_corrected_tree_under_grading(
    tmp_path: Path, subtree: str
) -> None:
    """Enforced by the layout rather than by discipline: `grading/` is overlaid
    into the workdir wholesale, so a corrected tree kept there would hand the
    agent the answers and a proof test kept there would be collected as a
    verdict test."""
    task_dir = write_review_fixture(tmp_path)
    misplaced = task_dir / GRADING_DIR / subtree
    misplaced.mkdir()
    (misplaced / "test_smuggled.py").write_text(
        "def test_smuggled():\n    assert True\n"
    )

    with pytest.raises(IngestError) as excinfo:
        load_task_set(tmp_path)

    assert REVIEW_ID in str(excinfo.value) and subtree in str(excinfo.value)


def test_nothing_the_lint_reads_is_overlaid_into_the_graded_workdir(
    tmp_path: Path,
) -> None:
    """Said from inside the graded workdir, by an additional held-out test run
    through the real pipeline: grading copies `repo/` and `grading/` and nothing
    else, so neither the proofs nor the corrected tree is there to be read — and
    a correct review still resolves."""
    task = review_fixture(
        tmp_path,
        extra_grading_tests={
            "test_layout.py": NOTHING_THE_LINT_READS_REACHED_THE_WORKDIR
        },
    )

    assert task.grading_test_paths == (FINDINGS_TEST_FILE, "test_layout.py", HASH_GATE_FILE)
    assert resolves(task, every_planted_finding())
