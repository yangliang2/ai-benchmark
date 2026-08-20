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
    "README.md": "67049bd8774d9f4d96521b1065179c5d8038a7a25051c8ad4748d2570af2222e",
    "account.test.ts": "cfebeb8f48bed555767a68038dcc7f5d3bb38241c5488ea116a4aa7d9f5f6151",
    "account.ts": "b9f90eac022234907e45af12c29f041db5cbdcc4879479c959cc60891cf0b181",
    "inscription.test.ts": "49fb9d4569ed25906f627b09f87fc7d5fcbea72fc27e3c2ddfcfb784d954372c",
    "inscription.ts": "7a3a50c34e2d3d9b73f1d7bd7051508abcb1b7515a2222ac3378700abb004c2d",
    "orders.test.ts": "e1640cfb9830521bf8a3e09aa1ca262b5a47e5d80b7017fc709b6f7f7feb4b08",
    "orders.ts": "6bfacd052eb9b01cd0879fe5a5caca7ba953e14ea620c30e5904551ced854908",
    "review.diff": "f33ffc114c2121e050b46560acf19ed28381fe6fe664cce4b1240f74e6c4c20d",
    "stones.test.ts": "c71b0b4c94847413522d3e3873c9ab07eba50d2102b31497006e38e8fff6b9ce",
    "stones.ts": "9843596622f7fbcacc8928e3ed9c3bcb07e21297ae600441b5f52ecc4e559eb3",
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
