"""Held out: whether the repository is exactly as the agent was handed it.

The deliverable of a task that carries a key — a located fault, a review's
findings, a located behaviour — is an answer file and never a repair, and this
task's prompt says so outright: do not put anything right, leave every file as
you found it. Unenforced, that would not matter for a task read on its own. It
matters because these tasks are read against the ones that ask for the edit —
what locating a defect costs, as against fixing it; what reviewing a change
costs, as against making it — and an agent that does the fix work and then
writes a correct answer would grade resolved at answer-file cost, with nothing
in the run log to show that it happened.

So the files the agent was handed are hashed here, and a run that changed,
deleted or replaced any of them grades unresolved however well it answered.
What it does not forbid is what a reader leaves behind: a scratch file, a
note, __pycache__ from running the repository's own tests. Only the seven
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "6ce56a111fc4b71941d9dcd3c02c27076adedaa7d0ea1836ccd439cf68266b9f",
    "bands.py": "7ce153e49818d26f85cd8bc6c4559e005f544501bde6a25e8584d225575d2aaa",
    "diary.py": "141fdf200a4cb39891d07d98acc4724a393566a4f59e24dbacce1d2d6c09711c",
    "sheet.py": "27dee68403e4a4f645b5d6934ce866d9c295766c37e0aa579051badc4eba84b1",
    "test_bands.py": "eba32336a4dff0ff9b188383f0db94b44073505197fe791d27565f1d93efe707",
    "test_diary.py": "57b88de52ff7dbc586d4167194e6346c19adef8c69cdb808eacaab1c7c319400",
    "test_sheet.py": "536d17c8538ca27d5cbecd06520c758e7b9d1c7f91b22dce3ae1f454c68a740c",
}


def test_the_repository_is_exactly_as_it_was_handed_over():
    changed = {}
    for name, digest in sorted(AS_HANDED_OVER.items()):
        found = Path.cwd() / name
        if not found.is_file():
            changed[name] = "gone"
        elif hashlib.sha256(found.read_bytes()).hexdigest() != digest:
            changed[name] = "edited"
    assert not changed, (
        f"the repository was not left as it was handed over: {changed} — this "
        "task asks for the location of the defect and not a repair"
    )
