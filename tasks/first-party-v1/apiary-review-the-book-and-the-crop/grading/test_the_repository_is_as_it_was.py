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
    "README.md": "eee5bf7ac17763adf4bd6fc26387c860fa87345038b183baa4f140457a8c3564",
    "apiary.py": "daf9ad0772262fad48cb4ad975588326920e1a47f199d35d83da320b11af49a4",
    "crop.py": "1b00d7676097bcba351e4484b8df8e9da9c04d8a5191d016274ff64a24fa95a1",
    "harvest.py": "c6dcd306ce267b5a2ede8148cc20c8d179b0cb81fae5aca349260f92eca83c1a",
    "keepers.py": "e10fe881c8d9480259e520187894e6d5b96251ae8eb061e595a8825bd296be64",
    "review.diff": "b593d9825a14e109a4ea63189a44f4482f13facd3f0f778b895e672b56680cc1",
    "test_apiary.py": "16512bbb4a65c043884ef772170e6c49bee16e146e5ead41d6ee4fc367c17ab6",
    "test_crop.py": "e290bc4fce4e34aad43342adc66b0dc19f34f1952b5d9fb3368579ab9e8f027d",
    "test_harvest.py": "7abc9caa201513e8142f4ef79976285a2f04f22641181d4b8b814d7558fb2f05",
    "test_keepers.py": "27fc52d58037651636656f190556e255256aa717d269d38f9fdc2719dd895571",
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
