"""The one canonical reading of `docs/design/task-difficulty-and-ex-ante-profiles.md`.

Before this module, the same handful of readers were hand-copied into most of
the `test_firstparty_v1_round*` suites (survey: `2407f02`). This is the kit
they migrate to; `tests/test_note_reading_equivalence.py` is the harness that
proves the migration changes no suite's reading before a single local copy is
deleted.
"""

import re
from pathlib import Path

NOTE = Path(__file__).parent.parent / "docs" / "design" / "task-difficulty-and-ex-ante-profiles.md"

# Byte-identical across nine files (round8_cells, round9..13_cells where
# present, round10..13_record) — confirmed by grep before this constant was
# exported. round7_cells's own copy drops the second capturing group and so
# is not this constant; it stays local.
REGISTER_LINE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)+)(?:\s+\((.+)\))?$")


def section(heading: str, *, note: Path = NOTE) -> str:
    """One section of the note, from its own heading line to the next heading
    of the same or shallower level.

    `heading` is the heading line verbatim, `#` markers included. Deliberately
    never sliced to `## Open questions` or any other named landmark
    (`docs/agents/runbook-grader-v2-gate.md:153`): a slice that runs to the
    note's trailing headings swallows whole sections silently.
    """
    text = note.read_text(encoding="utf-8")
    body = text.split(f"{heading}\n")
    assert len(body) == 2, f"the note carries exactly one {heading!r}"
    rest = body[1]
    if heading.startswith("### "):
        rest = rest.split("\n### ")[0]
    return rest.split("\n## ")[0]


def prose(text: str) -> str:
    """A passage with its wrapping collapsed: the sentence is the pin, the
    line break is not."""
    return " ".join(text.split())


def fenced_blocks(text: str) -> list[str]:
    """Every fenced code block of a passage, in order."""
    return text.split("```\n")[1::2]


def block_holding(text: str, *needles: str) -> str:
    """The one fenced block holding all of these, found by what it contains
    rather than by its position — so adding a block above it does not
    silently move the read."""
    found = [
        block for block in fenced_blocks(text)
        if all(needle in block for needle in needles)
    ]
    assert len(found) == 1, f"exactly one fenced block holds {needles!r}"
    return found[0]
