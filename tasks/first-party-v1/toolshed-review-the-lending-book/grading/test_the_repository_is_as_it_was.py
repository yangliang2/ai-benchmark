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
note, __pycache__ from running the repository's own tests. Only the eleven
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "61dce859db475087d0a43f984436e0581d33f5a0a8fb736efa47dc87a2ed8327",
    "desk.py": "d6569e43c7f1537c0ac341bd1374352c56a5049a0a6574cd4d5e9c5ef455951e",
    "labels.py": "f64bd604b7f1851dc4da3923d29273353a35a502ad86107091b13632df82cc0e",
    "loans.py": "020c1eefd410299433e7073ff606c1206848b845c873381b07723d83e3117a35",
    "review.diff": "268c61770783e62f1a97c3be4cf99d52f366586e34ba147eb4d7ddc0e993d981",
    "rota.py": "c168079146abac26fccc572614e4c62071616fe3ac81bf76b76e337a3f9b9b57",
    "shed.py": "40912474afc8dea01950cf0cfea69d4b9312d91303faf73fd7c3c4fac1780243",
    "test_labels.py": "3d55fd45fc5160ac1ea134ff2af2968005ded93cac28fcdfe602afbe0e33eb0d",
    "test_loans.py": "f461a612cdfc546dd18f487f57c3650268671e3e004749f488e75f4c149281ec",
    "test_rota.py": "c968577144d1bd210cdca098114fea0ce37ad1270e53f9d8ceec66c44d15065a",
    "test_shed.py": "33e00e9dcc127e8557b51389003abae43682f34d8d1ff10f889283f6aba6559c",
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
