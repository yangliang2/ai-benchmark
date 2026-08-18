"""The answer comparison: the whole of what a fault-location verdict makes of
an answer.

This module is the one implementation of that comparison, and it ships
byte-for-byte identical into every fault-location task's held-out grading
directory as `grading/_answer.py`. The held-out grading test that reads it is
itself shipped the same way, as `grading/test_answer.py` (see
`ANSWER_TEST_FILE` and `_answer_test_problems` in `firstparty_v1.py`): a
one-line assertion over `answer_problem()`, so a task's grading test cannot
quietly stop consulting this module while still shipping an unedited copy of
it. The task-set lint reads both shipped copies — this module and the test —
byte for byte against the copies this package owns (`answer_module_source()`
and `answer_test_source()`), which is a *stronger* check than the one the
family lint runs: a family compares its members' repositories and grading
suites peer-to-peer, each against the alphabetically-first member, because a
lone fault-location task has no sibling to compare against — this module and
its test compare against bytes the package itself owns instead. It is owned
rather than hand-written per task because the half of the verdict that
discriminates is the half worth not miscopying.

Standard library only, and everything it reads is resolved against the
directory grading runs pytest in — the workdir the overlay copied both this
module and the accepted-answer key into. Grading runs with conftest loading
disabled and its config pinned outside the workdir, so a grading file that
imported anything of this project's would not work at grade time.

What the comparison forgives is spelling, not identity. Surrounding
whitespace, one or more leading "./" segments on the file (forgiving a doubled
slash after the last one, so ".//pricing.py" and "././pricing.py" both answer
"pricing.py") and a trailing parenthesised argument list on the symbol (so
"Basket.total_with_tax(self)" and even "Basket.total_with_tax()()" both answer
"Basket.total_with_tax") are stripped, and a bare symbol matches the last
dotted component of an accepted one, so `total_with_tax` answers
`Basket.total_with_tax`. File and symbol stay case-exact: Python is
case-sensitive, and a case-insensitive match here would make a verdict depend
on the filesystem the grader ran on — the same defect that made a wrong-case
answer *path* resolve on macOS and replay unresolved on Linux.

And an answer names exactly one (file, symbol) pair, never a list: a task
measures whether the agent located the fault, and a shotgun of every plausible
location would be breadth rewarded as accuracy. A flat extra field alongside
the pair — an agent's `"reason"` — is tolerated and ungraded, so a hedge
carries no second guess; only a list or a nested object anywhere in the answer
smuggles one in.
"""

import json
import re
from pathlib import Path

# The accepted-answer key, beside this module in the workdir: both get there
# by the overlay that copies the held-out grading directory wholesale.
KEY_FILE = "accepted-answer.json"


def answer_problem(workdir: Path | None = None) -> str | None:
    """Why the answer file does not name an accepted location, or None if it
    does — the verdict a fault-location task is graded on.

    A reason rather than a bool, because the grading test's one assertion is
    all the agent's diff leaves behind: "unresolved" that cannot say whether
    the answer was missing, malformed or merely wrong is a verdict nobody can
    read back off a swept log.
    """
    root = Path.cwd() if workdir is None else workdir
    key = json.loads((root / KEY_FILE).read_text(encoding="utf-8"))
    declared: str = key["answer_path"]
    accepted: list[tuple[str, str]] = [
        (entry["file"], entry["symbol"]) for entry in key["accepted"]
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
    located = one_location(answer)
    if located is None:
        return (
            f"{declared} does not name exactly one (file, symbol) pair: {answer!r}"
        )
    if any(matches(located, pair) for pair in accepted):
        return None
    return f"{located} is not one of the accepted locations {accepted}"


def one_location(answer: object) -> tuple[str, str] | None:
    """The single (file, symbol) pair this answer names, normalised — or None
    where it names none, or more than one.

    More than one is refused by shape rather than by counting: a list of
    answers is not an object at all, and an object carrying a list or a nested
    object anywhere in it is how a second guess arrives beside the first. What
    is left alone is a flat extra field — an agent that writes its reasoning
    beside the answer has still named one location.
    """
    if not isinstance(answer, dict):
        return None
    if any(isinstance(value, list | dict) for value in answer.values()):
        return None
    file, symbol = answer.get("file"), answer.get("symbol")
    if not isinstance(file, str) or not isinstance(symbol, str):
        return None
    return _normalised_file(file), _normalised_symbol(symbol)


def matches(located: tuple[str, str], accepted: tuple[str, str]) -> bool:
    """Whether this normalised answer names this accepted location.

    Case-exact on both halves. The one thing forgiven beyond spelling is the
    description level an agent actually phrases an answer at: a bare symbol
    answers an accepted one qualified by its enclosing class. Only that
    direction — an answer of `Basket.total_with_tax` against an accepted bare
    `total_with_tax` names a class the author did not write down, and reading
    the two as the same would be inventing an acceptance rather than
    forgiving a spelling.
    """
    file, symbol = located
    accepted_file, accepted_symbol = accepted
    if file != accepted_file:
        return False
    if symbol == accepted_symbol:
        return True
    return symbol == accepted_symbol.rsplit(".", 1)[-1]


def resolve(root: Path, name: str) -> Path | None:
    """The named file under root, or None if it is not there — checked
    component-by-component against the actual directory listing rather than
    opened directly.

    Path.is_file() is case-insensitive on macOS, the platform the sweeps run
    on, so an answer written as "answer.json" would otherwise resolve here
    against a key declaring "ANSWER.json", while the identical logged workdir
    diff replays to a different verdict on Linux. Listing the directory keeps
    the lookup case-exact on every platform, including one where the two
    spellings really are different files.
    """
    current = root
    for part in Path(name).parts:
        try:
            entries = {entry.name for entry in current.iterdir()}
        except OSError:
            return None
        if part not in entries:
            return None
        current = current / part
    return current if current.is_file() else None


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """A `json.loads(object_pairs_hook=...)` that refuses a JSON object naming
    the same key twice.

    Plain `json.loads` keeps the *last* value for a duplicate key, so
    `{"file": "pricing.py", "symbol": "line_total", "symbol": "Basket"}`
    would resolve as "Basket" while the same document with the two values
    swapped would resolve as "line_total" — a verdict that depends on which
    guess happened to load last rather than on the document smuggling in a
    second one, which is exactly what a single (file, symbol) pair exists to
    rule out.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
    return dict(pairs)


# One or more leading "./" segments, forgiving one doubled slash after the
# last of them — so ".//pricing.py" and "././pricing.py" both strip down to
# "pricing.py". Anchored at the start and requiring a literal "./" to lead,
# so a genuinely absolute path ("/etc/passwd") is left alone rather than
# forgiven into a relative one it was never a spelling of.
_LEADING_DOT_SLASH = re.compile(r"^(\./)+/?")

# A trailing parenthesised argument list with no nested parentheses, so a
# symbol can be stripped of a call — repeatedly, since an agent might answer
# "Basket.total_with_tax(self)" (writing the signature) or even
# "Basket.total_with_tax()()".
_TRAILING_CALL = re.compile(r"\([^()]*\)$")


def _normalised_file(value: str) -> str:
    file = value.strip()
    return _LEADING_DOT_SLASH.sub("", file, count=1)


def _normalised_symbol(value: str) -> str:
    symbol = value.strip()
    while _TRAILING_CALL.search(symbol):
        symbol = _TRAILING_CALL.sub("", symbol).strip()
    return symbol
