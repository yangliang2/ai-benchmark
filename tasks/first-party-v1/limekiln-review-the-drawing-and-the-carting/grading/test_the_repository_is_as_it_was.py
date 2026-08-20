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
    "README.md": "b399561120ffd3b3e1202ae2745e5f2b05a44fbecf34d6f9456eb7e6fe3e46fc",
    "carting.test.ts": "f1c1e71cc590bc503674216f78ae348654f6c9fd9f718e442f376d901b34022f",
    "carting.ts": "2112d6e19ccaf4b4371caf49224740f788b8ee508ed3fa9a0c05f03f41df963e",
    "dockets.test.ts": "25320a585cd03f51e614a0a150b7f2c47ab4fe49b6bc73b86844f9cd3e6f43b0",
    "dockets.ts": "724177913d7a4aff61323d9f1f3c6b0a623f3c233baf1487af06ef954d78924e",
    "kilns.test.ts": "17a9c7ccf6bea48d3bc9e9044006e1ba7d8f20af5263c9b1fb4c75e5d81c269a",
    "kilns.ts": "7d347843b9d78b399fdfcb9e0d2a87d577ceb718c88fa15e8ea58f77cd60ef32",
    "review.diff": "6bf7347531305abc34f4e5669a647050b99e24444d316c7b90845343cfa358ab",
    "spells.test.ts": "63314a9714e73c0ac6061dbf745a5e83b5971da770e946f6c7086a91cd35dd51",
    "spells.ts": "4456f4a1b81c0a8bf0089ae27c7ca357dadfa557cfee64be3ee02f0650e8a3ae",
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
