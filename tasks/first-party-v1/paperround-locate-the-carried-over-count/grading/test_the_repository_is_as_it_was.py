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
    "README.md": "29f3a45b7932612ab55a7052a4130fb7f7f43815698ff0d577092508ed16b91b",
    "houses.py": "dad2bb69c676ef7c734a7f5e07bdfbcb5398ffd3b53489823a65ea8a98a0b73f",
    "newsagent.py": "6c939d023b84565a4ae9ddca7dd7d9c889629c48d83009682760260b54b0a139",
    "rounds.py": "e49132fbac3cab725fe750d39d2f880ced4e6120da3cc7887c720e24b0c1bddc",
    "tallying.py": "7e6122109e2eeddacdf8f3b123dc67ddb6261c3ae3eb6bec40016e47427bf737",
    "test_houses.py": "649bbfa1cfd22a1352685124c9c4528c98e579e5d4474164c4c812d3ac16e532",
    "test_newsagent.py": "3de0d0c7277266fa86dc7bd322f11c5c3dfe399d660fb10074282f8ac9a14301",
    "test_rounds.py": "d3a3fb287f77761e678dd37cef93602aa945313fc8c3244bb3187f2dfa560a53",
    "test_tallying.py": "8f81d06db44a8c4d10a85ab39b870e862c6b6c9e6dd678de3082cd811d8f16ba",
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
