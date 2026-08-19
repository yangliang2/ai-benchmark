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
note, __pycache__ from running the repository's own tests. Only the nine
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "f8f6e0d543da8c5e8b4b9bc46c2d6e8880b6515c00b8494e3ba0c8127e31cfed",
    "charges.test.ts": "17a70b37d66ec0e1949c041b4ee7a71060c782935c00353abac7369eb799e40f",
    "charges.ts": "55693ecb707c9a4bd68dc5f8835276c2234b842aba077c6641b398067cb48441",
    "desk.test.ts": "52e25f2987f9ec6a98a8487284fd3ad64b79ad1081892bffc128289d5132b4d1",
    "desk.ts": "09ee4f32a984717564c6662314658f8104da874830d8d08d584de083a9e48dfa",
    "shelf.test.ts": "c11e78ffbfd31d5d5812b1121b9f6967abd033dcad6bb479c751e5a83bc10f53",
    "shelf.ts": "9e9b4ae907ff78038c8a394462b3b488ded356eab1bf7317a2e07823e79f0e87",
    "tickets.test.ts": "488ac648408746465a399a6d55421949ff6fbcdfc8cb71efd2c85a421d04d19b",
    "tickets.ts": "3819e904bebfcab3b4c78f95c420f27580744fafbff297663a026b24d94fa508",
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
