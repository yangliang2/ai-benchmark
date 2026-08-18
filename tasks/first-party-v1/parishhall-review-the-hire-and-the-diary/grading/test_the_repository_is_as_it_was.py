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
    "README.md": "5a7652e521ed13d2e7e264687698d8f11a07d3dae93d745fb46f89eb102d4763",
    "caretaker.py": "9ad64c1c82a0fd9f1bea2c66efc840b1a49bbb7b8a1a7393355cf09a8cd10f91",
    "charges.py": "ce8832a5005cfaf137954d4bc22fa0bc6361d03307b9a9984e1ddcca8772d4bd",
    "diary.py": "d719c270910cd324c371abbacbf3f5627fd5fa7f923b43fc8a80c7c53aff7b43",
    "hall.py": "29b2170cd4572db0d33eff4a65abb887af64d3d63346d04907282e801571b3db",
    "review.diff": "ea9bf8bfded819596ab4ad081e7080ab1c31d52965934a7482e1fdd8ae1c12dd",
    "test_caretaker.py": "82ee4691fe526cc918b2b11b562f5b0aa1db25b34f2ced5b9bc1e913685cf09d",
    "test_charges.py": "bc534d2c38cd6b7651224f8a38ee8565368c09953149fc14c345f03f25de3a7f",
    "test_diary.py": "020cfdc5bf10a43b591e62da7def915a9c31df341218b6fe8b9c829b7cd8f767",
    "test_hall.py": "9e4f211328bc7a6b08d22952d8d945d564858737eb20b7e216d149dce669da0f",
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
