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
    "README.md": "d8f0ec03455fcaeffd1e5c05d4d0c5b6d75a93a7b18eb3b6fe3045ee85787aa1",
    "entries.py": "46f8d5980df10ade7867248b8735bbfca0da2049c3c77aaef824132cf37d1935",
    "points.py": "8881e23172539ce8c467402304b94d6c04115181bd7bbb3a9f1e4122cb629015",
    "review.diff": "de6d46db64a169e79b6b88f72af98fc669c74340875ec7647dafb129b84dd803",
    "show.py": "815e6b779a044fa7bdafaa1b8c0e0e5359f811decd79dd392c82c7cf1d7c8f10",
    "stewards.py": "3476e67d031f2f64abd2a0e871ec9039279634a2930062006012b5c20eb8467f",
    "test_entries.py": "593357d16028e3c186f60893d911a0be0c901279d9480fee22b1464da9ffe0c3",
    "test_points.py": "2f24c548e4dd971f56bcc49a37641fc124c54746b43e824b1490b666e3952596",
    "test_show.py": "fd0969d40c704eae04e1f478e563ea02cdf23104993f42fd6f6d22240578f445",
    "test_stewards.py": "9a8ea50a2c3db973c2c16732425070a3f12013704d05a6ce15da568eedb64124",
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
