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
    "README.md": "4d4ab9ca759dc47b6b9089b01acc2e4bed14448d981d25d6af0f3e4f81d7cde7",
    "charges.test.ts": "69339277cbf7db5905c02998ed2dcbca770cbe2f1d55beb0faad08f2468875c3",
    "charges.ts": "c5d7ad86d6aa847ce74aa358bceb188e6a019e1a334d5a8dc8001a6630c158ba",
    "messages.test.ts": "926771866450b9b541a3753607f442549eae65138b1dd77bd8c5c62bed421f70",
    "messages.ts": "d8c61dc6df81e63c192cde5de49652904c9e05efefb1974c859951f95e07bbf5",
    "office.test.ts": "71d704f38ce7f642adeead8410b57aef624fcd7bc006f67eaa5b7e56d5fc6670",
    "office.ts": "7d6f83c6e1800bd5891f883a4190d497eaee0f424a1fd0d8009b9a26cc0c33ad",
    "sheet.test.ts": "4c2b4904e35412d05ad4a69757f1ce622c4f9b1764412ad9c50ee84729e57ff7",
    "sheet.ts": "f79126ed112f764514fe787be5f7d5cd5dbf4b273b32a7ad5187ad14d1e4e704",
    "tape.test.ts": "0870f9b4a2559e7ead8dcfbff7c6cbc9857ed480238aa1f330e435ea37d51e21",
    "tape.ts": "f7c4612740f304c83e13670c6495c240d339bf3cbd3b11aef53b1bf81d74a9b4",
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
