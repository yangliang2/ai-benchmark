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
    "README.md": "fed1633ac87ca94d70f565f8cde568c4e810c1030ccf17660484259b7235ae7b",
    "grist.py": "c98ac0dee8f0e50cf765547dec430ece64804dbcb28bf28a7f5020792943aab0",
    "growers.py": "4deeb72c9de7b1ecf2ffe6941d8705ecaeff19860c4e5a3fb6f434e58bc13b7e",
    "mill.py": "ee97e2213b151c444f593a920a47899a6aec97acc16b791b5c1e58d5a121e420",
    "review.diff": "419cc73bc0a4517e90698dc5e19e1c295ab0402a588e4a859d17589c56a50228",
    "test_grist.py": "4b9f8cc376334580a9d07099ead934f1a1c4d1b48d2a174e1659352d2141c12a",
    "test_growers.py": "25e23b0a525fe3e2e175f8401202e7685671dafd1e43c5e0a6f9ba1e0d1e2e8b",
    "test_mill.py": "14d38dd7239de9e26d23bf79b67ad74e5e843e34c5f59c3bea33c22412a9efdd",
    "test_toll.py": "65e14f7298bf6eb1f4b5f6ae37bb044268cea5395bab458ee3a28b63382763c6",
    "toll.py": "e818c47bf84d6234d3bc1fa6e2618c0a39e739e274940abb80d38e42de54f130",
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
