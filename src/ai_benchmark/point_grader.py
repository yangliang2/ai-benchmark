"""The point grader: a live per-point ruling instrument, pinned and versioned.

Mirrors llm.py's shape for the classifier, one seam later: a callable
protocol, a live Anthropic client constructed in exactly one place and only
when an archived ruling is absent, and a prompt that is a pinned, versioned
constant of the instrument.

The grader is never asked "is this resolved?" — one narrow per-point
question, quote required. A single call per point, rulings archived, the
verdict downstream a pure function of the archive.
"""

import hashlib
import json
import re
from collections.abc import Callable
from typing import TypedDict

from pydantic import BaseModel, ConfigDict


class Point(TypedDict):
    id: str
    text: str


class Ruling(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    point_id: str
    covered: bool
    span: str | None
    grader_version: str


# (deliverable text, the planted point) -> one ruling. The same callable
# answers a disqualifier's question too — a disqualifier is a point-shaped
# question with the opposite polarity downstream, so this carries one shape.
PointGrader = Callable[[str, Point], Ruling]

# Strictly above both ladder rungs and a column in no sweep (§76.7): no cell
# is graded by the model that produced it.
GRADER_MODEL = "claude-opus-5"

PROMPT = """You are checking whether one required point is covered by a deliverable.
Judge this one point only — do not judge whether the deliverable as a whole
succeeds, and do not judge any point other than the one below.

Point id: {point_id}
Point: {point_text}

Deliverable:
{deliverable}

A point is covered only if you can quote a verbatim, contiguous span of the
deliverable's own text that establishes it. Never infer, never paraphrase,
and never answer based on what the deliverable *should* say — if no such
span exists, the point is not covered, with no exceptions.

Return covered (true or false) and span: when covered, the exact verbatim
quote from the deliverable that covers the point; null when not covered.
"""

RULING_SCHEMA = {
    "type": "object",
    "properties": {
        "covered": {"type": "boolean"},
        "span": {"type": ["string", "null"]},
    },
    "required": ["covered", "span"],
    "additionalProperties": False,
}

# Truncated to a readable prefix; a prompt edit moves this and everything
# downstream (re-proof, re-registration) rather than needing to be bumped by
# hand.
PROMPT_HASH = hashlib.sha256(PROMPT.encode()).hexdigest()[:12]
GRADER_VERSION = f"{GRADER_MODEL}:{PROMPT_HASH}"


def normalise_whitespace(text: str) -> str:
    """Collapse every run of whitespace to a single space and strip the ends.

    Defined once here; the gate and the lint both call this rather than
    reimplementing it.
    """
    return re.sub(r"\s+", " ", text).strip()


def span_in_deliverable(span: str, deliverable: str) -> bool:
    """Whether `span` appears in `deliverable`, modulo whitespace
    normalisation. §76.6: no quotable span, no coverage — this is the check;
    the refusal on a failing check belongs to the gate, not this module.
    """
    return normalise_whitespace(span) in normalise_whitespace(deliverable)


def anthropic_point_grader() -> PointGrader:
    import anthropic

    client = anthropic.Anthropic()

    def grade(deliverable: str, point: Point) -> Ruling:
        # Thinking is on by default on claude-opus-5 and max_tokens caps
        # thinking + response text together — keep generous headroom.
        response = client.beta.messages.create(
            model=GRADER_MODEL,
            max_tokens=16000,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": RULING_SCHEMA},
            },
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(
                        point_id=point["id"],
                        point_text=point["text"],
                        deliverable=deliverable,
                    ),
                }
            ],
        )
        if response.stop_reason == "refusal":
            return Ruling(
                point_id=point["id"],
                covered=False,
                span=None,
                grader_version=GRADER_VERSION,
            )
        if response.stop_reason == "max_tokens":
            # Truncated JSON must not be parsed into a half-right ruling (it
            # would be archived); fail loudly instead.
            raise RuntimeError(
                f"grading of point {point['id']!r} was truncated "
                "(stop_reason=max_tokens); raise max_tokens and re-run"
            )
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        return Ruling(
            point_id=point["id"],
            covered=data["covered"],
            span=data["span"],
            grader_version=GRADER_VERSION,
        )

    return grade
