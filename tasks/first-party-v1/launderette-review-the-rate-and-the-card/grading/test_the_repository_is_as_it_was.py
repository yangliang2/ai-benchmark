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
    "README.md": "32352f13f6958fdcf7667b3c9785be8d427d1adcc72998de2353511c4288b6af",
    "machines.py": "8754cc342bea7f925c13735427aaf7b73bf6fc99e0dac1eb5a486814739fb733",
    "openings.py": "ad956336086fa6abe54ac5af2559811deb1e1a6325abd6eaa0df66301ead456f",
    "review.diff": "99d998f02b8d832cbb221bca6ea3dee8eb9febbc8061688d114147e56afc699e",
    "stamps.py": "974edd2894b218fd14d5c76fd2d91f63615b8e7a1af963e8ddd6d879c31fc229",
    "tariff.py": "ae2825c6a5c76c2469c0f8f984cab262fc3f4ea6d9fa2d369a074d8bdd4b6e30",
    "test_machines.py": "fe4d99e2d13007118c9e4f300ba0f7a7a657f44234361e2b57459205b6ee205b",
    "test_openings.py": "1dddd87c354f6fa172238c680d1426df3d64abbf927f414bb14e856c585e7af2",
    "test_stamps.py": "5060af48164ea5e4847ee53804536076e1d723bffa78f5713d685ab0f28d21db",
    "test_washes.py": "888cc476ad8dc34b93d1e77955ce484a6462faa37fd709cf13133347a145d6ef",
    "washes.py": "7fff034602592b4e79f8c6089bbb42a400c702f5a5f293641f9a3952b0ecb6f2",
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
