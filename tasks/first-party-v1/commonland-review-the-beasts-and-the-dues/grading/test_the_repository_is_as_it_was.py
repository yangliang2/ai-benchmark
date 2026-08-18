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
    "README.md": "70b10d4684edadef08625c4df2963dd9d673c626945e2c3207a6159f107d8efa",
    "common.py": "f87dc4308b571b7e62162b9ea7a08f0284a58a5c550f47cea954696671b3ac72",
    "dues.py": "5338a745f4718d9df0e00f52f5c3c46db88a778a628384bb12565341264e3313",
    "graziers.py": "9fc815eb13992a95b0a60ec46002e9299f8d18265fecd3627ab331bdc274d8f6",
    "reeve.py": "e10354d4ae207ae15264460c437c66951a1772cc61d824c625c92dc882b6ce23",
    "review.diff": "b66232d2d7e580d99daee291f1334ada8a7914b48e18998e55e15ff118e085f0",
    "test_common.py": "9a2dfebb7b596514c0f243f10a38541807d872be0a1eb7556ce4c981332a0864",
    "test_dues.py": "ae60c9ef802bdeec1ac58cf34e3800e32bae11fdc0532937196a2caea04b0f12",
    "test_graziers.py": "43f6b5fa995fa65f56338ea88974f4086797b77621e384ece4381ea036f4012a",
    "test_reeve.py": "79e701796a657caea29625924fbbed66572d39e503efe3c80c05c4538becea29",
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
