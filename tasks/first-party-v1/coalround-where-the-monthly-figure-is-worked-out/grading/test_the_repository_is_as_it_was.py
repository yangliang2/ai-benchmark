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
    "README.md": "63cea8b90f3334dd775aeeae5087268e0bb4b2da6435c113de54883c530e8f89",
    "deliveries.py": "a6e7a6463c604f768ae365a3b6aaf79bbdb365fa976fe747b18f8ece0b6d9efc",
    "grades.py": "e9bbc87f5c0759b2b791d1276e4f6455793bb7a035742b96a2c5307a491b4406",
    "statement.py": "cca8284c5a17c0e4318fac69933920e17b85468bf545bc5cd569922f9399f212",
    "test_deliveries.py": "f8aa15b63eeca90afff388d5075080e49067ace8e183d45028643c305db4b4d6",
    "test_grades.py": "f03922023aa29105e8be08f0105c41f7083dc4cbd0862a7062ee2a5a04786c7a",
    "test_statement.py": "c5b243eded3ff08347fdb8d8fb3efe2264f8bf490947fd23d1b26c1ded4c73e5",
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
