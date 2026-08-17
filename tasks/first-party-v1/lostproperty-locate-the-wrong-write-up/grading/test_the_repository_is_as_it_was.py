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
note, __pycache__ from running the repository's own tests. Only the seven
files below are compared, and only against what they were.

Canonical for this task and generated rather than typed. Regenerate it with
`ai-bench lint-v1 --write-hash-gates` in the
ai-benchmark repository; the task-set lint reads it back and asserts these
digests still describe the checked-in starting repository, both ways round.
"""

import hashlib
from pathlib import Path

AS_HANDED_OVER = {
    "README.md": "f2e7774b635b1467c1bd29c078c89da609614b60d6f93c81c8737d9d19c40fb2",
    "handins.py": "4e3cab98ffbf7d54f2a500d22732ab90c9d2de5c06e92a83798d00a9ed6cc32a",
    "office.py": "f9d2d935ce6f9f0d7e18645f41af94d7f00bb456c56d9093950aa18578d83aa7",
    "sorting.py": "7a6cc3ffeb17d64a153663e3482c24d0e063e8daffd4359f00c7111bfe6eb68e",
    "test_handins.py": "4e4f7a30e89c305b25956bfbfcdea58e36d21d8b45800f2e28506dbe0e43f26f",
    "test_office.py": "4bac7fc554c11e098038879e2f0f76f0857ce3f933d5e3dd54678f4e3a9fff1f",
    "test_sorting.py": "bf8561f91fb86166baa4edd42611d3178b39d91590b5363d3b1b3ccc3cd45931",
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
