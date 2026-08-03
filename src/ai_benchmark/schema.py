"""The unified record schema — the single seam all three layers read and write.

One Record = one (agent x model) combination's result on one benchmark instance,
or an aggregate when per-instance data is unavailable. See ADR-0001 and CONTEXT.md
for the vocabulary.
"""

from collections.abc import Mapping
from datetime import date
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TaskCategory = Literal[
    "bug-fix",
    "feature-dev",
    "refactor",
    "test-authoring",
    "frontend-ui",
    "infra-config",
    "codebase-comprehension",
    "unclassified",
]

Scale = Literal["single-file", "cross-file", "unknown"]

SourceType = Literal["first-party", "per-instance", "aggregate"]

Confidence = Literal["high", "medium", "low"]


class RecordValidationError(ValueError):
    """A raw mapping does not form a valid unified-dataset record."""


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: TaskCategory
    scale: Scale
    language: str | None = None

    agent: str = Field(min_length=1)
    agent_version: str | None = None
    model: str = Field(min_length=1)

    benchmark: str = Field(min_length=1)
    instance_id: str | None = None

    quality_metric: str = Field(min_length=1)
    quality_value: float

    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    latency_s: float | None = Field(default=None, ge=0)
    turns: int | None = Field(default=None, ge=1)

    source: str = Field(min_length=1)
    source_type: SourceType
    confidence: Confidence
    as_of: date

    @model_validator(mode="after")
    def instance_id_required_unless_aggregate(self) -> Self:
        if self.source_type != "aggregate" and self.instance_id is None:
            raise ValueError(
                f"instance_id is required for source_type={self.source_type!r}; "
                "only aggregate records may omit it"
            )
        return self


def validate_record(data: Mapping[str, Any]) -> Record:
    """Validate one raw mapping (e.g. a parsed JSONL row) into a Record.

    Raises RecordValidationError naming the offending field(s).
    """
    try:
        return Record.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc']) or 'record'}: {issue['msg']}"
            for issue in error.errors()
        )
        raise RecordValidationError(f"invalid record — {problems}") from error
