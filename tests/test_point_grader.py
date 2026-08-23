"""The point grader instrument: prompt shape, version pinning, span mechanics,
and the live-client seam — mirrors tests/test_llm.py one seam later."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from ai_benchmark.point_grader import (
    DEEPSEEK_BASE_URL,
    GRADER_CHECKPOINT,
    GRADER_MODEL,
    GRADER_VERSION,
    PROMPT,
    PROMPT_HASH,
    Point,
    Ruling,
    deepseek_point_grader,
    normalise_whitespace,
    span_in_deliverable,
    strip_markdown,
)


def fake_grader(deliverable: str, point: Point) -> Ruling:
    return Ruling(point_id=point["id"], covered=True, span="x", grader_version="fake")


def test_prompt_asks_one_narrow_question_and_requires_a_verbatim_quote() -> None:
    prompt = PROMPT.lower()

    assert "judge this one point only" in prompt
    assert "do not judge" in prompt
    assert "verbatim" in prompt
    assert "quote" in prompt


def test_prompt_names_json_and_shows_the_ruling_shape() -> None:
    """This vendor's JSON mode has no schema parameter: the JSON-output guide
    requires the word "json" in the prompt together with an example of the
    desired shape, so the shape RULING_SCHEMA used to carry rides the prompt —
    which is why a change of it moves PROMPT_HASH and the version with it."""
    prompt = PROMPT.lower()

    assert "json" in prompt
    assert '{{"covered": true, "span": ' in PROMPT
    assert '"covered" is false and "span" is null' in PROMPT


def test_prompt_never_asks_whether_the_task_is_resolved() -> None:
    assert "resolved" not in PROMPT.lower()
    assert "resolve" not in PROMPT.lower()


def test_prompt_hash_is_recomputed_from_the_prompt_text() -> None:
    assert PROMPT_HASH == hashlib.sha256(PROMPT.encode()).hexdigest()[:12]
    assert GRADER_VERSION == f"{GRADER_MODEL}:{GRADER_CHECKPOINT}:{PROMPT_HASH}"


def test_the_version_is_alias_plus_announced_checkpoint_plus_prompt_hash() -> None:
    """§78.3: this vendor accepts only moving aliases and no dated checkpoint
    id, so the announced checkpoint joins the tuple to make a checkpoint
    announcement under the alias a version change."""
    assert GRADER_MODEL == "deepseek-v4-pro"
    assert GRADER_CHECKPOINT == "DeepSeek-V4-Pro-0813"
    assert GRADER_VERSION.split(":") == [GRADER_MODEL, GRADER_CHECKPOINT, PROMPT_HASH]


def test_normalise_whitespace_collapses_runs_and_strips_ends() -> None:
    assert normalise_whitespace("  a   b\n\nc \t d  ") == "a b c d"


def test_span_matches_across_different_internal_spacing() -> None:
    deliverable = "The cache is warm and\nnever touches the network."
    span = "warm  and never   touches\nthe network"

    assert span_in_deliverable(span, deliverable)


def test_span_not_present_does_not_match() -> None:
    deliverable = "The cache is warm and never touches the network."
    span = "the cache is always cold"

    assert not span_in_deliverable(span, deliverable)


def test_prompt_carries_the_location_equivalence_rule() -> None:
    """§80.2's first revision, aimed at §79.2(a): the machine's own matcher
    accepts prose, backticked and `file.py:Class.method` renderings of one
    location, and the grader is now told the same rule in as many words."""
    prompt = " ".join(PROMPT.split())

    assert (
        "A deliverable names a location whether it writes it as "
        "`file.py:Class.method`, backticks it, or names the same method and "
        "file in prose" in prompt
    )
    assert (
        "coverage is judged on the location named, never on the rendering"
        in prompt
    )


def test_prompt_carries_the_span_discipline_rule() -> None:
    """§80.2's second revision, aimed at §79.2(b)'s fifteen refused quotes: a
    span stripped of the deliverable's markdown is not the deliverable's
    text."""
    prompt = " ".join(PROMPT.split())

    assert (
        "Copy the span out of the deliverable character for character, "
        "including any markdown markers (**, backticks, #, list dashes) the "
        "deliverable carries" in prompt
    )
    assert "a quote with the formatting stripped is not the deliverable's text" in prompt


# --- §80.3's fallback: the markdown strip, pinned by example ------------------


@pytest.mark.parametrize(
    ("marker", "deliverable", "span"),
    [
        (
            "**",
            "**dues.py: owed_by** — Silently skips zero-rate graziers.",
            "dues.py: owed_by — Silently skips zero-rate graziers.",
        ),
        (
            "backticks",
            "The defect is in `yard.py`, method `Yard.book_in`.",
            "The defect is in yard.py, method Yard.book_in.",
        ),
        (
            "#",
            "The ledger was read whole.\n## Findings\nIt double-counts the "
            "standing charge.",
            "The ledger was read whole. Findings It double-counts the "
            "standing charge.",
        ),
        (
            "list dashes",
            "- the total is rounded once here\n- and rounded again on export",
            "the total is rounded once here and rounded again on export",
        ),
    ],
)
def test_a_span_stripped_of_its_markdown_matches_through_the_fallback(
    marker: str, deliverable: str, span: str
) -> None:
    """§80.3: the whitespace-only comparison refuses each of these — that is
    §79.2(b)'s mechanism — and the markdown-stripped comparison accepts them.
    One example per marker class the section names."""
    assert normalise_whitespace(span) not in normalise_whitespace(deliverable), (
        f"the {marker} example must fail the raw comparison, or it proves "
        "nothing about the fallback"
    )
    assert span_in_deliverable(span, deliverable)


def test_strip_markdown_removes_the_four_marker_classes_once() -> None:
    """The strip is one definition in the implementation rather than a regex
    at the call site, so it is pinned directly too."""
    assert strip_markdown("**bold**") == "bold"
    assert strip_markdown("a `code` span") == "a code span"
    assert strip_markdown("### Heading\nbody") == "Heading body"
    assert strip_markdown("- one\n- two") == "one two"


def test_a_paraphrased_span_fails_both_comparisons() -> None:
    """§76.6 survives §80.3: the fallback forgives a rendering, never a
    paraphrase. No quotable span, no coverage."""
    deliverable = "**dues.py: owed_by** — Silently skips zero-rate graziers."
    span = "the owed_by function ignores graziers whose rate is zero"

    assert normalise_whitespace(span) not in normalise_whitespace(deliverable)
    assert strip_markdown(span) not in strip_markdown(deliverable)
    assert not span_in_deliverable(span, deliverable)



def test_fake_grader_never_constructs_a_live_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The `never_called` pattern of tests/test_classify.py:19 — using a fake
    grader must never reach the live DeepSeek client, whose construction would
    fail on this machine (no DEEPSEEK_API_KEY in the test environment)."""
    import openai

    def never_constructed(*args: object, **kwargs: object) -> object:
        raise AssertionError("live DeepSeek client must not be constructed")

    monkeypatch.setattr(openai, "OpenAI", never_constructed)

    point: Point = {"id": "p1", "text": "does the thing"}
    ruling = fake_grader("the thing was done", point)

    assert ruling.covered


def test_importing_the_module_constructs_no_client() -> None:
    """The import and the client both live inside the factory, so importing
    this module needs no credentials — what keeps the lint, replay and every
    suite keyless.

    Checked in a subprocess with the key scrubbed from the environment: a
    fresh keyless interpreter imports the module and reads the version, so a
    client constructed at import time would fail loudly. An in-process
    ``importlib.reload`` is exactly wrong here — it rebinds the module's
    classes in place, and every later ``Ruling`` equality in the same worker
    then compares instances of the old class against the new one (pydantic
    equality is class-identity-aware), a poisoning that surfaces only when
    xdist co-locates this test with a Ruling-asserting one.
    """
    import os
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k != "DEEPSEEK_API_KEY"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ai_benchmark import point_grader; print(point_grader.GRADER_VERSION)",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == GRADER_VERSION


# --- the live seam, on the vendor's OpenAI-compatible response shape ----------


@dataclass
class _FakeMessage:
    content: str | None = None
    refusal: str | None = None


@dataclass
class _FakeChoice:
    finish_reason: str
    message: _FakeMessage = field(default_factory=_FakeMessage)


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]


class _FakeCompletions:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.chat = _FakeChat(_FakeCompletions(response))
        self.kwargs: dict[str, Any] = {}


def _response(finish_reason: str = "stop", **message: Any) -> _FakeResponse:
    return _FakeResponse([_FakeChoice(finish_reason, _FakeMessage(**message))])


def _ruling_content(covered: bool, span: str | None) -> dict[str, Any]:
    return {"content": json.dumps({"covered": covered, "span": span})}


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch, response: _FakeResponse
) -> _FakeClient:
    import openai

    client = _FakeClient(response)

    def construct(*args: Any, **kwargs: Any) -> _FakeClient:
        client.kwargs = kwargs
        return client

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(openai, "OpenAI", construct)
    return client


def test_a_missing_key_fails_with_a_message_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The calibration run's pre-flight is a human step; this is the message it
    reads, so it names the variable rather than raising a library auth error."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        deepseek_point_grader()


def test_the_client_is_built_against_the_fetched_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_fake_client(monkeypatch, _response(**_ruling_content(True, "q")))

    deepseek_point_grader()

    assert client.kwargs["base_url"] == DEEPSEEK_BASE_URL == "https://api.deepseek.com"
    assert client.kwargs["api_key"] == "test-key"


def test_request_carries_the_pinned_instrument_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§78.2's settings are part of the pin: the alias, low reasoning effort,
    temperature 0 (accepted and inert in thinking mode — see the module
    docstring) and the vendor's json_object response format."""
    client = _install_fake_client(
        monkeypatch, _response(**_ruling_content(True, "quote"))
    )

    grader = deepseek_point_grader()
    grader("deliverable text with quote", {"id": "p1", "text": "point text"})

    assert len(client.chat.completions.calls) == 1
    request = client.chat.completions.calls[0]
    assert request["model"] == GRADER_MODEL
    assert request["reasoning_effort"] == "low"
    assert request["temperature"] == 0
    assert request["response_format"] == {"type": "json_object"}


def test_grade_returns_ruling_stamped_with_the_grader_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _response(**_ruling_content(True, "the quote")))

    grader = deepseek_point_grader()
    ruling = grader("deliverable with the quote", {"id": "p1", "text": "point text"})

    assert ruling == Ruling(
        point_id="p1", covered=True, span="the quote", grader_version=GRADER_VERSION
    )


def test_a_content_filter_returns_an_uncovered_ruling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _response(finish_reason="content_filter"))

    grader = deepseek_point_grader()
    ruling = grader("deliverable text", {"id": "p1", "text": "point text"})

    assert ruling == Ruling(
        point_id="p1", covered=False, span=None, grader_version=GRADER_VERSION
    )


def test_a_refusal_returns_an_uncovered_ruling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _response(refusal="I cannot help with that"))

    grader = deepseek_point_grader()
    ruling = grader("deliverable text", {"id": "p1", "text": "point text"})

    assert ruling == Ruling(
        point_id="p1", covered=False, span=None, grader_version=GRADER_VERSION
    )


def test_a_truncated_response_raises_rather_than_parses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Truncated JSON must not be parsed into a half-right ruling: it would be
    archived."""
    _install_fake_client(monkeypatch, _response(finish_reason="length", content="{"))

    grader = deepseek_point_grader()

    with pytest.raises(RuntimeError, match="truncated"):
        grader("deliverable text", {"id": "p1", "text": "point text"})


@pytest.mark.parametrize("content", [None, "", "   "])
def test_empty_content_raises_rather_than_becoming_a_ruling(
    monkeypatch: pytest.MonkeyPatch, content: str | None
) -> None:
    """The vendor's JSON-output guide warns the API "may occasionally return
    empty content" — a failed call, never an uncovered ruling."""
    _install_fake_client(monkeypatch, _response(content=content))

    grader = deepseek_point_grader()

    with pytest.raises(RuntimeError, match="empty content"):
        grader("deliverable text", {"id": "p1", "text": "point text"})


def test_unparseable_content_raises_rather_than_becoming_a_ruling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _response(content="not json at all"))

    grader = deepseek_point_grader()

    with pytest.raises(RuntimeError, match="unparseable"):
        grader("deliverable text", {"id": "p1", "text": "point text"})
