"""Round 12's explain-style `codebase-comprehension` tasks: what one of them
is, and that it is proved.

Heap 3's last action, taken as the mechanical fill §103's certification
sentence licensed (design note §106, registered §107). A task of it ships no
held-out grading test at all: the deliverable is one prose explanation at the
prompt-named answer path, and the ground truth is a points key the agent never
sees — four to six planted points read under "every", at most two
disqualifiers read under "none". The category also carries four locate-style
tasks on an accepted-answer key, and those are deliberately not here: which
shape a task is is read off the key on disk (§45.6, §106.5), so this suite is
parametrised over every **point-keyed** task of the category rather than over
the category or over a list written in this file — the round's later tasks are
covered by being authored.

§106.1's one-clause-tight rule governs every point of these keys — one point
is one fact of the code that a single evidence span can hit, and a consequence
is its own point, never a trailing clause — and **nothing below machine-asserts
it**: it is an authoring discipline, policed where authoring is already
policed, the spec review and the two-sided proofs whose archives this suite
reads back. What is asserted here is everything mechanical around it: the
declarations, the key's registered shape, the no-second-key rule, what the
prompt hands over and holds back, and the archived proofs.

**Nothing here calls the grader.** The two-sided proof was taken once, at
authoring time, by `ai-bench prove-points-v1`; everything below is a
recomputation over the archives it wrote, held to the pinned instrument and to
the hashes of the key and the answers — the same offline reading `ai-bench
lint-v1` performs, plus the verdict recomputed through `_point_verdict`, the
very function a run is graded by.
"""

import hashlib
import json
import re

import pytest
from firstparty_v1_tasks import SOLUTIONS, TASKS, task_by_id

from ai_benchmark import point_grader
from ai_benchmark.firstparty_v1 import (
    PROOF_SIDES,
    ProofRulings,
    _point_questions,
    _point_verdict,
    is_keyed,
    is_point_keyed,
    lint_task_set,
    load_task_set,
    points_key,
    points_key_sha256,
    proof_rulings_file,
)

# The words a prompt of this action may not contain. A smoke check and not the
# ruling: what actually keeps the mechanism undisclosed is the author writing a
# prompt that is a whole closed-world question and nothing else, and no word
# list can check that. This one catches the obvious slip — a sentence
# explaining how the answer will be judged — and is worth its few lines for
# that alone.
UNDISCLOSED = ("planted", "disqualif", "grader", "points key", "rubric")

# What §106.3 has a task of this round plant: below four the universal
# quantifier binds too little to be worth authoring, above six hand-planting
# plus the two-sided proof buys repetition. The lint's own floor is three,
# deliberately lower — it refuses what is unusable, this asserts what the
# round said it would ship. Disqualifiers are capped because §107.6 registered
# the round's price on 0-2 a task, and a third would be a silent overage.
PLANTED_RANGE = (4, 6)
DISQUALIFIER_LIMIT = 2

# The deliverable's shape, named by the prompt rather than enforced as format:
# a missing section is not a format crime, it is planted points going
# uncovered. The prompt has to name each section so that an answer missing one
# failed the requirement and not an instruction it was never given.
REQUIRED_SECTIONS = (
    "What happens",
    "Why it comes out that way",
    "Boundaries and edge behavior",
)


def explain_style_task_ids() -> list[str]:
    """The corpus's point-keyed `codebase-comprehension` tasks, in a stable
    order — selected by key shape and never by category alone, because the
    category's locate-style tasks are a different shape with a different
    ground truth."""
    return sorted(
        task.id
        for task in load_task_set(TASKS)
        if task.category == "codebase-comprehension" and is_point_keyed(task)
    )


TASK_IDS = explain_style_task_ids()


def names_as_a_token(prompt: str, path: str) -> bool:
    """Whether the prompt names this path as a whole token rather than as a
    substring of some longer word.

    Written out here rather than borrowed from the lint that reads the same
    question: a pin that calls the implementation it is pinning agrees with it
    by construction.
    """
    token = rf"(?<![A-Za-z0-9_-]){re.escape(path)}(?![A-Za-z0-9_-])"
    return bool(re.search(token, prompt))


# --- the round shipped some ----------------------------------------------------


def test_the_round_checked_in_at_least_one_explain_style_task() -> None:
    """Everything below is parametrised over the corpus, so an empty corpus
    would pass the whole file by having nothing to run."""
    assert TASK_IDS


# --- what a task of this action declares ---------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_declares_the_action_and_registers_no_prediction(
    task_id: str,
) -> None:
    """The declarations the gate and the coverage table read.

    `control: true` is not decoration: this action registers no difficulty
    prediction, and a task declaring neither a construction block nor itself a
    control is refused as a control by omission. The round declares no
    contrast, so it moves no knob's counter.
    """
    task = task_by_id(task_id)

    assert task.category == "codebase-comprehension"
    assert task.language == "python"
    assert task.surface == "application"
    assert task.control is True
    assert task.construction is None


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_points_key_reads_and_holds_what_the_round_registered(
    task_id: str,
) -> None:
    """Four to six planted points and at most two disqualifiers, behind a
    declared answer path — the shape §107.6 priced the round's proofs on."""
    key = points_key(task_by_id(task_id))
    low, high = PLANTED_RANGE

    assert key.answer_path
    assert low <= len(key.points) <= high
    assert len(key.disqualifiers) <= DISQUALIFIER_LIMIT


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_ships_no_second_ground_truth(task_id: str) -> None:
    """The no-second-key rule, from the corpus's side: a point-keyed
    comprehension task ships no accepted-answer key and no executable grading
    suite at all. The loader refuses a task carrying both keys as two ground
    truths for one deliverable (§106.5); this is the checked-in corpus saying
    the refusal never had to fire."""
    task = task_by_id(task_id)

    assert not is_keyed(task)
    assert not task.grading_test_paths


# --- what the prompt hands over, and what it holds back ------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_names_the_answer_path_and_each_required_section(
    task_id: str,
) -> None:
    """The answer file is the whole deliverable and the sections are the
    deliverable's shape: an agent told neither cannot solve the task however
    well it read the code."""
    task = task_by_id(task_id)
    key = points_key(task)

    assert names_as_a_token(task.prompt, key.answer_path)
    for section in REQUIRED_SECTIONS:
        assert section.lower() in task.prompt.lower(), section


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_prompt_quotes_no_planted_point_and_discloses_no_mechanism(
    task_id: str,
) -> None:
    """The points are the key and are held out: a prompt quoting one hands the
    agent a required element of the answer, and a prompt explaining the
    mechanism grades a different capability than the one registered."""
    task = task_by_id(task_id)
    key = points_key(task)
    prompt = task.prompt.lower()

    for planted in (*key.points, *key.disqualifiers):
        assert planted.text.lower() not in prompt, planted.id
        assert planted.id.lower() not in prompt, planted.id
    assert [word for word in UNDISCLOSED if word in prompt] == []


# --- the ground truth is held out, and there is no second one ------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_key_and_the_two_answers_are_held_out_of_the_repository(
    task_id: str,
) -> None:
    """The other direction of the same rule: a copy of the key or of either
    proof answer inside `repo/` is the answer handed over with the question."""
    task = task_by_id(task_id)
    held_out = {"points-key.json", "reference-answer.md", "foil-answer.md"}

    assert not [
        path
        for path in task.repo_dir.rglob("*")
        if path.is_file() and path.name in held_out
    ]
    assert not (task.repo_dir / points_key(task).answer_path).exists()


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_ships_no_reference_solution_directory(task_id: str) -> None:
    """Solvability is proved by the archived reference-answer rulings, and a
    checked-in "solution" would need a live grader call to grade."""
    assert not (SOLUTIONS / task_id).exists()


# --- the two-sided proof, read from the archive --------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_archived_proofs_answer_this_key_under_the_pinned_instrument(
    task_id: str,
) -> None:
    """Both archives exist, were taken under the pinned grader version against
    exactly these answers and this key, and rule on every planted point and
    every disqualifier — nothing missing, nothing the key does not ask."""
    task = task_by_id(task_id)
    key = points_key(task)
    asked = {(kind, planted.id) for kind, planted in _point_questions(key)}

    for side in PROOF_SIDES:
        answer = (task.proofs_dir / side.answer_file).read_text(encoding="utf-8")
        assert answer.strip(), side.name
        raw = proof_rulings_file(task, side).read_text(encoding="utf-8")
        archive = ProofRulings.model_validate(json.loads(raw))

        assert archive.grader_version == point_grader.GRADER_VERSION
        assert archive.answer_sha256 == hashlib.sha256(
            answer.encode("utf-8")
        ).hexdigest()
        assert archive.points_key_sha256 == points_key_sha256(key)
        ruled = {(entry.kind, entry.point_id) for entry in archive.rulings}
        assert ruled == asked, side.name


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_reference_answer_resolves_and_the_foil_answer_fails(
    task_id: str,
) -> None:
    """The round's one hard gate, recomputed rather than reprinted: the verdict
    over each archive is taken through `_point_verdict` — the very function a
    run is graded by, spans re-checked against the answer's own bytes — and
    the reference must resolve where the foil must not."""
    task = task_by_id(task_id)
    questions = _point_questions(points_key(task))

    for side in PROOF_SIDES:
        answer = (task.proofs_dir / side.answer_file).read_text(encoding="utf-8")
        raw = proof_rulings_file(task, side).read_text(encoding="utf-8")
        archive = ProofRulings.model_validate(json.loads(raw))

        assert _point_verdict(questions, archive, answer) is side.resolves, side.name


# --- and the lint agrees, offline ----------------------------------------------


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_the_task_is_lint_clean(task_id: str) -> None:
    """The whole of the authoring account in one read: the key's rules, the
    terrain, the answer path, and the registered existence proof over the
    archived rulings — with no grader call, which is the lint's own property."""
    assert lint_task_set([task_by_id(task_id)]) == []
