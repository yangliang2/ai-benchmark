"""The point grader instrument: prompt shape, version pinning, span mechanics,
and the live-client seam — mirrors tests/test_llm.py one seam later."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from ai_benchmark.point_grader import (
    GRADER_MODEL,
    GRADER_VERSION,
    PROMPT,
    PROMPT_HASH,
    Point,
    Ruling,
    anthropic_point_grader,
    normalise_whitespace,
    span_in_deliverable,
)


def fake_grader(deliverable: str, point: Point) -> Ruling:
    return Ruling(point_id=point["id"], covered=True, span="x", grader_version="fake")


def test_prompt_asks_one_narrow_question_and_requires_a_verbatim_quote() -> None:
    prompt = PROMPT.lower()

    assert "judge this one point only" in prompt
    assert "do not judge" in prompt
    assert "verbatim" in prompt
    assert "quote" in prompt


def test_prompt_never_asks_whether_the_task_is_resolved() -> None:
    assert "resolved" not in PROMPT.lower()
    assert "resolve" not in PROMPT.lower()


def test_prompt_hash_is_recomputed_from_the_prompt_text() -> None:
    assert PROMPT_HASH == hashlib.sha256(PROMPT.encode()).hexdigest()[:12]
    assert GRADER_VERSION == f"{GRADER_MODEL}:{PROMPT_HASH}"


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


def test_fake_grader_never_constructs_a_live_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The `never_called` pattern of tests/test_classify.py:19 — using a fake
    grader must never reach the live Anthropic client, whose construction
    would fail on this machine (no ANTHROPIC_API_KEY, no stored profile)."""
    import anthropic

    def never_constructed(*args: object, **kwargs: object) -> object:
        raise AssertionError("live Anthropic client must not be constructed")

    monkeypatch.setattr(anthropic, "Anthropic", never_constructed)

    point: Point = {"id": "p1", "text": "does the thing"}
    ruling = fake_grader("the thing was done", point)

    assert ruling.covered


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeResponse:
    stop_reason: str
    content: list[_FakeTextBlock] = field(default_factory=list)


class _FakeMessages:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        return self._response


class _FakeBeta:
    def __init__(self, messages: _FakeMessages) -> None:
        self.messages = messages


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.beta = _FakeBeta(_FakeMessages(response))


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch, response: _FakeResponse
) -> _FakeClient:
    import anthropic

    client = _FakeClient(response)
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: client)
    return client


def test_request_carries_no_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(json.dumps({"covered": True, "span": "quote"}))],
    )
    client = _install_fake_client(monkeypatch, response)

    grader = anthropic_point_grader()
    grader("deliverable text with quote", {"id": "p1", "text": "point text"})

    assert len(client.beta.messages.calls) == 1
    assert "temperature" not in client.beta.messages.calls[0]


def test_grade_returns_ruling_stamped_with_the_grader_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(json.dumps({"covered": True, "span": "the quote"}))],
    )
    _install_fake_client(monkeypatch, response)

    grader = anthropic_point_grader()
    ruling = grader("deliverable with the quote", {"id": "p1", "text": "point text"})

    assert ruling == Ruling(
        point_id="p1", covered=True, span="the quote", grader_version=GRADER_VERSION
    )


def test_refusal_returns_an_uncovered_ruling(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(stop_reason="refusal")
    _install_fake_client(monkeypatch, response)

    grader = anthropic_point_grader()
    ruling = grader("deliverable text", {"id": "p1", "text": "point text"})

    assert ruling == Ruling(
        point_id="p1", covered=False, span=None, grader_version=GRADER_VERSION
    )


def test_max_tokens_stop_raises_rather_than_parses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _FakeResponse(stop_reason="max_tokens")
    _install_fake_client(monkeypatch, response)

    grader = anthropic_point_grader()

    with pytest.raises(RuntimeError, match="max_tokens"):
        grader("deliverable text", {"id": "p1", "text": "point text"})
