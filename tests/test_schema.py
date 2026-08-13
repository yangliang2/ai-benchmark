"""Tests at the unified-dataset seam: raw mapping in -> validated Record or clear error."""

import json
from pathlib import Path
from typing import Any, get_args

import pytest

from ai_benchmark.schema import (
    Record,
    RecordValidationError,
    Surface,
    TaskCategory,
    validate_record,
)


def valid_record_data() -> dict[str, Any]:
    """A well-formed per-instance record, as a raw mapping (e.g. one JSONL row)."""
    return {
        "category": "bug-fix",
        "scale": "cross-file",
        "language": "python",
        "agent": "claude-code",
        "agent_version": "2.1.0",
        "model": "claude-sonnet-5",
        "benchmark": "swe-bench-verified",
        "instance_id": "django__django-11099",
        "quality_metric": "resolved",
        "quality_value": 1.0,
        "tokens_in": 184000,
        "tokens_out": 9200,
        "cost_usd": 1.42,
        "latency_s": 312.5,
        "turns": 1,
        "source": "https://github.com/swe-bench/experiments",
        "source_type": "per-instance",
        "confidence": "medium",
        "as_of": "2026-07-15",
    }


def test_well_formed_record_validates_and_round_trips() -> None:
    record = validate_record(valid_record_data())

    assert isinstance(record, Record)
    assert record.category == "bug-fix"
    assert record.agent == "claude-code"
    assert record.model == "claude-sonnet-5"
    assert record.source_type == "per-instance"
    assert record.cost_usd == 1.42
    assert record.as_of.isoformat() == "2026-07-15"


def test_optional_measurements_may_be_absent() -> None:
    data = valid_record_data()
    for optional in ("agent_version", "language", "tokens_in", "tokens_out",
                     "cost_usd", "latency_s", "turns"):
        del data[optional]

    record = validate_record(data)

    assert record.cost_usd is None
    assert record.turns is None


def test_aggregate_record_needs_no_instance_id() -> None:
    data = valid_record_data()
    del data["instance_id"]
    data["source_type"] = "aggregate"
    data["quality_metric"] = "resolution-rate"
    data["quality_value"] = 0.63

    record = validate_record(data)

    assert record.instance_id is None


def test_the_category_vocabulary_is_the_ten_engineering_actions() -> None:
    """A category names what is done, not what kind of ticket it came from —
    one task measures exactly one action (CONTEXT.md, design note 34.2)."""
    assert get_args(TaskCategory) == (
        "bug-fix",
        "feature-dev",
        "refactor",
        "test-authoring",
        "codebase-comprehension",
        "fault-location",
        "code-review",
        "investigation",
        "requirement-decomposition",
        "performance-optimisation",
        "unclassified",
    )


def test_every_action_in_the_vocabulary_validates() -> None:
    for category in get_args(TaskCategory):
        data = valid_record_data()
        data["category"] = category

        assert validate_record(data).category == category


@pytest.mark.parametrize(
    ("retired", "surface"),
    [("frontend-ui", "frontend"), ("infra-config", "infrastructure")],
)
def test_retired_category_is_refused_naming_the_annotation_it_moved_to(
    retired: str, surface: str
) -> None:
    """The two members that named *where* work happens left the vocabulary;
    the error has to say where they went, or a stale row looks like a typo."""
    data = valid_record_data()
    data["category"] = retired

    with pytest.raises(RecordValidationError, match=f"surface.*{surface}"):
        validate_record(data)


def test_record_without_surface_reads_unknown() -> None:
    """No migration: every record written before the annotation existed stays
    valid and answers `unknown`."""
    assert validate_record(valid_record_data()).surface == "unknown"


def test_surface_annotates_where_the_work_happened() -> None:
    data = valid_record_data()
    data["surface"] = "infrastructure"

    assert validate_record(data).surface == "infrastructure"


def test_surface_outside_the_vocabulary_is_rejected() -> None:
    data = valid_record_data()
    data["surface"] = "backend"

    with pytest.raises(RecordValidationError) as excinfo:
        validate_record(data)
    # Not just the field name: the message must actually enumerate the
    # vocabulary a valid surface has to come from, or this passes however
    # the rejection is (mis)implemented.
    message = str(excinfo.value)
    assert "surface" in message
    for surface in get_args(Surface):
        assert surface in message


def test_unknown_category_is_rejected_with_clear_error() -> None:
    data = valid_record_data()
    data["category"] = "vibe-coding"

    with pytest.raises(RecordValidationError, match="category"):
        validate_record(data)


def test_missing_required_field_is_rejected_with_clear_error() -> None:
    data = valid_record_data()
    del data["model"]

    with pytest.raises(RecordValidationError, match="model"):
        validate_record(data)


def test_negative_cost_is_rejected() -> None:
    data = valid_record_data()
    data["cost_usd"] = -0.5

    with pytest.raises(RecordValidationError, match="cost_usd"):
        validate_record(data)


def test_per_instance_record_without_instance_id_is_rejected() -> None:
    data = valid_record_data()
    del data["instance_id"]

    with pytest.raises(RecordValidationError, match="instance_id"):
        validate_record(data)


def test_non_lowercase_language_is_rejected() -> None:
    data = valid_record_data()
    data["language"] = "Python"

    with pytest.raises(RecordValidationError, match="language"):
        validate_record(data)


def test_first_party_record_must_have_high_confidence() -> None:
    data = valid_record_data()
    data["source_type"] = "first-party"
    data["confidence"] = "low"

    with pytest.raises(RecordValidationError, match="confidence"):
        validate_record(data)


def test_checked_in_json_schema_matches_the_model() -> None:
    """record.schema.json is the schema for non-Python consumers; it must not drift."""
    checked_in = json.loads(
        (Path(__file__).parent.parent / "record.schema.json").read_text()
    )

    assert checked_in == Record.model_json_schema()
