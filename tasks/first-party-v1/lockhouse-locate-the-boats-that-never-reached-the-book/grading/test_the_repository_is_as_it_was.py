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
    "README.md": "bba8bc19448147793df3f97ba9bec6aae1d737b54fe3d12d8ab5af856500424b",
    "book.test.ts": "bb02650ddd42c896a4adc019fdede7108501df62e2a6f3498d2a9f0ccbef1bba",
    "book.ts": "340db11e4bd52063ab70d630eec478fe2d76a28caaa7c6a51f5dc14af7d87c91",
    "keeper.test.ts": "ed6e005b1c8d84917ef514fdd600da12a3e808c7a646c1b9ce43429990ac097b",
    "keeper.ts": "53c2f6cf4f639757ea711978166c380467813f31b59b751dd2918a3167fdee76",
    "lock.test.ts": "22e6e10e250769f92a287ec109a163ec0f0f4d9a9d4f5aa5ea182550b4692ff3",
    "lock.ts": "d9b0f79bc03d86c405751ede71ee971dbf5e27eead057c9c09aaa334929254a2",
    "water.test.ts": "20be6bedf12ee26ad8fe880c9218ce800ef7a5e007d230be19338823ebbfeb08",
    "water.ts": "9191e05ba8c0dde9b45f9db3a366af8cd260468a683acdf992179bba7dc3bec7",
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
