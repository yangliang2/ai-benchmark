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
    "README.md": "ab64de242cd58baef62e3a23c248ef7599af6a4eaa723c1ab7a198b8f20ff918",
    "cradles.py": "db3ae9683b4d3ffadd5aa3fabd25e4bf9ebeaf7a2954fbca8913e13f1b8ba5bd",
    "slipway.py": "c9d526f52bd8c449bc50ec9de170e02a5b3066ba744aa67cb97467132f8b880d",
    "test_cradles.py": "7d35cf9242fbf11d9e783ee434d1f752d5316cb72d3c0ed0afa22218c77dcbb9",
    "test_slipway.py": "15a27f3f2db2e75cef4092f91d69e42da6c84e8d102d8586c033e00c59c4dbba",
    "test_yard.py": "cf3a170a0991b55cf387f9064c17130e98e4b58e60dfa4fdb9b7b805d118bd4d",
    "yard.py": "65b96983f5fedceddd5fcd29b23878a7dd141ee594fa63f73850f36c0c436e0d",
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
