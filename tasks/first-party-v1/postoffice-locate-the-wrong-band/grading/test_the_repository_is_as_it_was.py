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

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "9ab2bb810f9559240a91668e0f4025ca673dcc717f5c2650cc36e43fcb6d590f",
    "card.py": "102b52dd0e8775aee789c0b057c5252e5dd0c52e206108c60c00bc720c748b17",
    "counter.py": "6212ed5a77548a9f8d8de250b9b1df8843a3ae0671ffa9fe068dfbc0129e7f49",
    "office.py": "b0c25769b674fc1c566259e784fd01cd32b16b4ff3e1725b7839a554525ae644",
    "parcels.py": "b6359567d6492c5420ed6d19771ad2d206271b878bd1e2e44beabb013ba5233d",
    "test_card.py": "a73bea1b5c39251dccf50f94715c55bc31a2d8ed36e1c72085913a45cb0a099f",
    "test_counter.py": "69d6f48956203a4fc0dbdcea5e7b90c653c93e7574452802729fc71f749cd630",
    "test_office.py": "abe72e18df1a75706a2ab7398040b809af6a002150ee4662004416d6a60a5a13",
    "test_parcels.py": "d8464455fb59820539c888e176ae83f97d6b588ab14a90b31dfeb710e7b954cd",
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
