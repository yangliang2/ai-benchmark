"""Held out: whether the repository is exactly as the agent was handed it.

The deliverable of a fault-location task is the location, and this task's
prompt says so outright: do not fix it, leave every file as you found it. That
went unenforced until this batch, and for a task read on its own it would not
matter. It matters here, because this task and the bug-fix task built on the
same starting repository exist to produce one number — what locating a defect
costs, as against fixing it — and an agent that does the fix work and then
writes a correct answer would grade resolved at fix-member cost, with nothing
in the run log to show that it happened.

So the files the agent was handed are hashed here, and a run that changed,
deleted or replaced any of them grades unresolved however well it answered.
What it does not forbid is what a reader leaves behind: a scratch file, a
note, __pycache__ from running the repository's own tests. Only the nine
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed (.qap/regen_hashes.py
in the ai-benchmark repository); the task's own suite asserts these digests
still describe the checked-in starting repository.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "148379a20bab3aa36c59355c01f3bd72534d065f4db0bf4073620e416bc80ff6",
    "cards.py": "bd464fcc3e6460e2522ccc547a3c954725318cd3bf931eff0349efead6b606c4",
    "ledger.py": "04816fe26b6a4fbb65325d7592fc5cad44491400b09cfca3e16258b798b991d6",
    "plots.py": "49e95d6743c76f9da6e2a11112fe12f00dd60e114fab0259583dd6c0b8c59c01",
    "society.py": "1696cc25c8a22b2e0fbf4c60cc2a8b94658e8d08ec7db43a4416d21639245556",
    "test_cards.py": "328d526a2c368ba9f2c4c1d318ab708ea3e7866b752e73cf6788d22ec9e7b134",
    "test_ledger.py": "6d1983bfe449ecac271122bb1465a410606a20237828f87599ab76608b02b2da",
    "test_plots.py": "0188e2118432a9a38ea5b8c27461d99e89dd4e5d80ca4eb74b5285952dfb8023",
    "test_society.py": "392dc9677051fc7e0411355c47022e50489f548cceb04380c4d3161d65fafe9c",
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
