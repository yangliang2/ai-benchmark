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
    "README.md": "b46f2563486072c7643ae91095e608d71655791268a027f813b99a00d5c4cd42",
    "clocking.py": "9adeecefca9edf5c03cf748510dd35ee8931d240b48948a3afa4604eceb19e8b",
    "entries.py": "eb9e594fce2b264d932161f7c03a5789232e8dabddb91983a7fc568ec360e8a4",
    "rings.py": "9e9786f01b4036f682a31b842a86192f3bc189a82ec1107fc4d38f384277e8e8",
    "test_clocking.py": "46631f1b2d3c7b698efc56c909b34adf4c95ef1bce3f369f33c344a8bec7c6e5",
    "test_entries.py": "712ee89ff84f75b1f607e534e492e3efd95fd2b51c304c2d076ea5f09311c950",
    "test_rings.py": "ffe138497f7d7c8bc4c51dff7b1dc0f189031ff93873d69138aec950558c2c8e",
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
