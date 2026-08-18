"""The findings comparison: the whole of what a `code-review` verdict makes of
an answer file.

The set-shaped counterpart of `_answer.py`, and it ships the way that module
ships — byte for byte into every `code-review` task's held-out grading
directory as `grading/_findings.py`, with the one-line held-out test that reads
it (`grading/test_findings.py`) shipped the same way, so that a task cannot
quietly stop consulting this module while still shipping an unedited copy of
it. Both are owned rather than hand-written per task because the half of the
verdict that discriminates is the half worth not miscopying.

What this module does *not* own is the forgiveness. Where an answer names a
location it imports `_answer.py` — `one_location`, `matches`, `resolve` and its
duplicate-key refusal — rather than restating them, because the two verdicts
have to forgive the same spellings: a review that reports `./pricing.py`,
`Basket.total_with_tax()` names the location a locate answer of those words
names, and two copies of that rule would eventually disagree about it. So a
review task's grading directory ships `_answer.py` beside this file, and the
byte-for-byte check the task-set lint runs over this module has to cover that
one as well.

The import is written flat (`from _answer import ...`) because flat is how the
two files sit beside each other in a grading directory, which is the only place
this module is ever executed: it is a shipped artifact rather than a package
API, so `import ai_benchmark._findings` does not work and is not meant to. The
package reads it as bytes (`findings_module_source()`) and mypy type-checks it
where it lies.

Standard library only, and everything it reads is resolved against the
directory grading runs pytest in — the workdir the overlay copied this module,
`_answer.py` and the findings key into. Grading runs with conftest loading
disabled and its config pinned outside the workdir, so a grading file that
imported anything of this project's would not work at grade time.

What the verdict is: resolved iff **every** planted finding is matched by at
least one finding of the answer *and* **no** finding of the answer matches a
rejected one. The two quantifiers are what makes this key set-shaped rather
than a second accepted-answer key — a locate verdict asks whether the one
answer is in a set, a review verdict asks whether one set covers another. A
finding matching neither half is ignored: it stays in the workdir diff as
archived evidence, because a real problem the author did not plant must not
fail the run, while every-line-is-a-finding still fails on the rejected half.
And there is no partial score, because a recall rate would be a new quality
metric where `resolved` is the one this benchmark reports.

A planted finding is itself a *set*: `{"any": [location, ...]}`, a non-empty
list of the alternative locations the author is prepared to have that one
defect described at — typically the defective method and the class enclosing
it — and it is matched when some finding of the answer matches **any one** of
them. So the quantifier over the accepted half is "every finding, at some
alternative": an inner *any* under an outer *every*. The flat shape this
replaced made a planted finding one location, which meant a key could not
write down a second legitimately-correct description level without demanding
that the answer report the same defect twice, once at each. The first
alternative is the **primary** — the most specific location, and the one the
finding is named after wherever a name is needed.

A finding may carry a free-text note beside its location, and nothing here ever
reads it: `one_location` tolerates a flat extra field and refuses a nested list
or object, so a note is carried into the archive while a second location
smuggled into one finding is refused.
"""

import json
from pathlib import Path

from _answer import _no_duplicate_keys, matches, one_location, resolve  # type: ignore

# The findings key, beside this module in the workdir: both get there by the
# overlay that copies the held-out grading directory wholesale.
KEY_FILE = "findings-key.json"


def findings_problem(workdir: Path | None = None) -> str | None:
    """Why this answer file is not an acceptable review of the change under
    review, or None where it is — the verdict a `code-review` task is graded
    on.

    A reason rather than a bool, for the reason `answer_problem()` gives one:
    the held-out test's single assertion is all a swept run leaves behind, and
    an "unresolved" that cannot say whether the answer was missing, malformed,
    one planted finding short, or reporting something the key rejects is a
    verdict nobody can read back off the log.
    """
    root = Path.cwd() if workdir is None else workdir
    key = json.loads((root / KEY_FILE).read_text(encoding="utf-8"))
    declared: str = key["answer_path"]
    # Read with .get rather than subscripted, and at both levels: the key model
    # defaults an omitted half to empty, a planted finding is a set of
    # alternatives keyed under "any", and the task-set lint is what names either
    # of those missing — so a half-written key has to reach that lint as the
    # lint problem it is rather than crash a grading run here with a KeyError.
    accepted: list[list[tuple[str, str]]] = [
        [
            (alternative["file"], alternative["symbol"])
            for alternative in planted.get("any", [])
        ]
        for planted in key.get("accepted", [])
    ]
    rejected: list[tuple[str, str]] = [
        (entry["file"], entry["symbol"]) for entry in key.get("rejected", [])
    ]
    path = resolve(root, declared)
    if path is None:
        return f"no answer file at {declared}"
    try:
        answer = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return f"{declared} is not readable JSON: {error}"
    reported = locations(answer)
    if reported is None:
        return (
            f"{declared} does not list findings, each one object naming a "
            f"(file, symbol) pair: {answer!r}"
        )
    for alternatives in accepted:
        if not alternatives:
            return (
                "the findings key plants a finding with no location to match "
                "it against — a planted finding is a non-empty set of "
                'alternative locations, {"any": [{"file": ..., "symbol": ...}]}'
            )
        if not any(
            matches(found, alternative)
            for alternative in alternatives
            for found in reported
        ):
            primary, *rest = alternatives
            named = f" (or {rest})" if rest else ""
            return (
                f"no finding names {primary}{named}, which the change under "
                f"review does contain — {declared} reports {reported}"
            )
    for found in reported:
        for non_finding in rejected:
            if matches(found, non_finding):
                return (
                    f"{declared} reports {found}, and {non_finding} is not a "
                    "defect: the change under review is correct there"
                )
    return None


def locations(answer: object) -> list[tuple[str, str]] | None:
    """Every (file, symbol) pair this answer file reports, normalised and in
    the order it reports them — or None where it is not a list of findings at
    all.

    A list is the shape here, where a fault-location answer refuses one: a
    review names as many findings as the change holds, so the list *is* the
    answer rather than a shotgun of guesses at one location. What is refused
    inside it is what `one_location` refuses — a member that is not an object
    naming a `file` and a `symbol`, or one carrying a nested list or object,
    which is how a second location arrives inside a single finding.
    """
    if not isinstance(answer, list):
        return None
    reported: list[tuple[str, str]] = []
    for finding in answer:
        located = one_location(finding)
        if located is None:
            return None
        reported.append(located)
    return reported
