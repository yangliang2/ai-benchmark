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
note, __pycache__ from running the repository's own tests. Only the ten
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "7546b5015091f0937ef8eecd3350c0f1a35d8e7eec0028ee2c92511459fd1e46",
    "board.py": "7f4a0858d1a6caaebbb11b2170cc6ab64e397297942ff4bd2a642b92d7ecc85a",
    "peals.py": "f9bf15bee49299329b506a26ffd84d6275865b0a9d6d7cbab1f8560a5fc20f14",
    "review.diff": "7b3c616f9e9ebac26d9a239f915947d2c1621e983f84d87524232861942933a7",
    "ringers.py": "46489e1eb0771af5996514c58eb577a1abc0f8f62e20af404b63e4bdc20d67de",
    "test_board.py": "567600aebb10390ed7e4e50d5768f95a9b3cb0b4bc67ddd1bfa53f8b83b4ef3e",
    "test_peals.py": "6eac2cd485e9431e5e9573aacb986b081de5689b5988c776296227de755bcb38",
    "test_ringers.py": "e5c062724c3596b4f1f7571dcf806d8dfca15ae59b62176f62965ce93cafd78e",
    "test_tower.py": "5dced7ed87c2439225c8470a6d6b2db0e516350500349ced1db4ad151642cdff",
    "tower.py": "70fe832b6453a24e6fe706babf919ae82389cd9663a8eb4ddcc3733de4ef66aa",
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
