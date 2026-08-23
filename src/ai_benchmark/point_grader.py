"""The point grader: a live per-point ruling instrument, pinned and versioned.

Mirrors llm.py's shape for the classifier, one seam later: a callable
protocol, a live client constructed in exactly one place and only when an
archived ruling is absent, and a prompt that is a pinned, versioned constant
of the instrument.

The grader is never asked whether the task as a whole succeeded — one narrow
per-point question, quote required. A single call per point, rulings
archived, the verdict downstream a pure function of the archive.

The instrument (§78.2): `deepseek-v4-pro` over the vendor's OpenAI-compatible
endpoint, low reasoning effort, temperature 0, JSON output. Round 9 parked at
its calibration gate because this machine holds no Anthropic credentials;
§78.1 reopened §76.7 on that premise failure and re-pinned the instrument
here.

**`temperature=0` is not this instrument's determinism story.** The vendor's
thinking-mode guide (https://api-docs.deepseek.com/guides/thinking_mode,
fetched 2026-08-22) states, in as many words: "Thinking mode does not support
the temperature, top_p, presence_penalty, or frequency_penalty parameters.
Please note that, for compatibility with existing software, setting these
parameters will not trigger an error but will also have no effect." Thinking
mode is enabled by default on this model, so the `temperature=0` the request
below carries is accepted and inert. It is sent because §78.2 pins it and §78
is the authority — not because it buys determinism. The determinism story is
§76.6's, unchanged by the change of vendor: a single call per point, rulings
archived, the verdict a pure function of the archive.

**The pin is weak, and disclosed (§78.3).** This vendor's API accepts only
moving aliases (`deepseek-v4-pro`, `deepseek-v4-flash`) and no dated
checkpoint id, so the snapshot pin §76.7 promised is not available from it.
Compensated rather than accepted silently: the vendor announces checkpoints
publicly, and the announced checkpoint — `GRADER_CHECKPOINT`, read from the
`MODEL VERSION` cell of https://api-docs.deepseek.com/quick_start/pricing on
2026-08-22, where it stands at the `DeepSeek-V4-Pro-0813` §78.3 recorded —
joins the version tuple. A checkpoint announcement under the alias is
thereby a version change, which re-triggers every task's proofs (§76.10) and
opens a new rulings file (§77.8). What the tuple cannot catch is an
**unannounced swap under the alias**: that is the residual exposure, named
rather than hidden. It is bounded by the fact that replay never re-calls —
archived rulings and archived proofs are immune, and only new gradings and
new proofs ride the alias.
"""

import hashlib
import json
import os
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

# A column in no sweep and a vendor shared with neither swept vendor (§78.1):
# no cell is graded by the model that produced it, and the grader's own
# capability claim sits on the calibration bar rather than on a tier argument.
GRADER_MODEL = "deepseek-v4-pro"

# The `MODEL VERSION` cell the alias announces, fetched 2026-08-22. Its own
# constant so that GRADER_VERSION below is assembled rather than spelled.
GRADER_CHECKPOINT = "DeepSeek-V4-Pro-0813"

# The `BASE URL (OpenAI Format)` cell of the same page.
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

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

A deliverable names a location whether it writes it as `file.py:Class.method`,
backticks it, or names the same method and file in prose (for example "the
`book_in` method in `yard.py`"). Those renderings are one answer: coverage is
judged on the location named, never on the rendering.

Copy the span out of the deliverable character for character, including any
markdown markers (**, backticks, #, list dashes) the deliverable carries — a
quote with the formatting stripped is not the deliverable's text.

Return covered (true or false) and span: when covered, the exact verbatim
quote from the deliverable that covers the point; null when not covered.

Reply with a json object and nothing else, in exactly this shape.

EXAMPLE JSON OUTPUT:
{{"covered": true, "span": "a verbatim contiguous quote from the deliverable"}}

When the point is not covered, "covered" is false and "span" is null.
"""

# Truncated to a readable prefix; a prompt edit moves this and everything
# downstream (re-proof, re-registration) rather than needing to be bumped by
# hand.
PROMPT_HASH = hashlib.sha256(PROMPT.encode()).hexdigest()[:12]
GRADER_VERSION = f"{GRADER_MODEL}:{GRADER_CHECKPOINT}:{PROMPT_HASH}"

# The markers §80.3 names, stripped line by line: `**`, backticks, and — at the
# start of a line, where they are structure rather than text — heading hashes
# and list dashes.
_INLINE_MARKERS = ("**", "`")
_LINE_LEAD = re.compile(r"^\s*(?:#{1,6}\s*|-\s+)")


def normalise_whitespace(text: str) -> str:
    """Collapse every run of whitespace to a single space and strip the ends.

    Defined once here; the gate and the lint both call this rather than
    reimplementing it.
    """
    return re.sub(r"\s+", " ", text).strip()


def strip_markdown(text: str) -> str:
    """`text` with §80.3's markdown markers removed and whitespace normalised.

    Defined once here rather than inlined at the call site, so that the
    fallback comparison in `span_in_deliverable` has one definition a test can
    pin by example: `**`, backticks, heading `#`s and list dashes.
    """
    for marker in _INLINE_MARKERS:
        text = text.replace(marker, "")
    stripped = [_LINE_LEAD.sub("", line) for line in text.splitlines()]
    return normalise_whitespace("\n".join(stripped))


def span_in_deliverable(span: str, deliverable: str) -> bool:
    """Whether `span` appears in `deliverable`, modulo whitespace
    normalisation and — failing that — modulo markdown markers too. §76.6: no
    quotable span, no coverage — this is the check; the refusal on a failing
    check belongs to the gate, not this module.

    The fallback is §80.3's ruling, taken with its trade stated: §79.2(b)
    showed the grader quoting deliverables with their markdown stripped
    (`dues.py: owed_by — …` for `**dues.py: owed_by** — …`), and the
    whitespace-only rule refused those quotes exactly as specified. The v2
    prompt aims at the model's quoting habit; this fallback absorbs whatever
    of the habit survives it, deliberately overlapping, because §80.6 makes a
    second failure terminal for this vendor's grader and a terminal gate
    should not hang on prompt obedience alone. §76.6 survives it: a span must
    still be mechanically locatable in the deliverable, and a paraphrase fails
    both comparisons.

    **The loosening is not calibration-only.** This same function is the
    production point gate's span check (`firstparty_v1`) and the point lint's,
    as well as the calibration reader's, so every future point-gate verdict
    inherits it — disclosed here rather than discovered later.
    """
    if normalise_whitespace(span) in normalise_whitespace(deliverable):
        return True
    return strip_markdown(span) in strip_markdown(deliverable)


def deepseek_point_grader() -> PointGrader:
    # The SDK import and the client both live in here, so importing this
    # module, running the lint, running any test and replaying any run all
    # work with no credentials present.
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set; export it in the invoking shell and "
            "re-run — the point grader is a live client"
        )
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    def grade(deliverable: str, point: Point) -> Ruling:
        # Thinking is on by default on deepseek-v4-pro and max_tokens caps
        # thinking + response text together — keep generous headroom.
        # temperature is pinned by §78.2 and inert here; see the module
        # docstring.
        response = client.chat.completions.create(
            model=GRADER_MODEL,
            max_tokens=16000,
            reasoning_effort="low",
            temperature=0,
            response_format={"type": "json_object"},
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
        choice = response.choices[0]
        if choice.finish_reason == "length":
            # Truncated JSON must not be parsed into a half-right ruling (it
            # would be archived); fail loudly instead.
            raise RuntimeError(
                f"grading of point {point['id']!r} was truncated "
                "(finish_reason=length); raise max_tokens and re-run"
            )
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            return Ruling(
                point_id=point["id"],
                covered=False,
                span=None,
                grader_version=GRADER_VERSION,
            )
        content = choice.message.content
        # The vendor's JSON-output guide warns that with this response_format
        # "the API may occasionally return empty content" — that is a failed
        # call, never an uncovered ruling, so it raises like a truncation.
        if content is None or not content.strip():
            raise RuntimeError(
                f"grading of point {point['id']!r} returned empty content; "
                "re-run"
            )
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"grading of point {point['id']!r} returned unparseable "
                f"content: {content!r}"
            ) from exc
        return Ruling(
            point_id=point["id"],
            covered=data["covered"],
            span=data["span"],
            grader_version=GRADER_VERSION,
        )

    return grade
