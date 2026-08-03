"""Tests at the unified-dataset seam: raw mapping in -> validated Record or clear error."""

import pytest

from ai_benchmark.schema import Record, RecordValidationError, validate_record


def valid_record_data() -> dict:
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
