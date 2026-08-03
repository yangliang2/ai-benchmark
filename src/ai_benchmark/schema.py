"""The record schema — the validation gate on the unified dataset.

One Record = one combination's result on one benchmark instance, or an
aggregate when per-instance data is unavailable. See ADR-0001 and CONTEXT.md
for the vocabulary. Non-Python consumers use the exported record.schema.json.
"""

from collections.abc import Mapping
from datetime import date
from typing import Annotated, Any, Literal, Self

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

NonEmptyStr = Annotated[str, Field(min_length=1)]

# Lowercase language identifiers per CONTEXT.md: python, typescript, c++, c#, ...
LanguageStr = Annotated[str, Field(pattern=r"^[a-z][a-z0-9+#.-]*$")]


class RecordValidationError(ValueError):
    """A raw mapping does not form a valid unified-dataset record."""


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: TaskCategory
    scale: Scale
    language: LanguageStr | None = None

    agent: NonEmptyStr
    agent_version: str | None = None
    model: NonEmptyStr

    benchmark: NonEmptyStr
    instance_id: str | None = None

    quality_metric: NonEmptyStr
    quality_value: float

    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    latency_s: float | None = Field(default=None, ge=0)
    turns: int | None = Field(default=None, ge=1)

    source: NonEmptyStr
    source_type: SourceType
    confidence: Confidence
    as_of: date

    @model_validator(mode="after")
    def cross_field_rules(self) -> Self:
        if self.source_type != "aggregate" and self.instance_id is None:
            raise ValueError(
                f"instance_id is required for source_type={self.source_type!r}; "
                "only aggregate records may omit it"
            )
        if self.source_type == "first-party" and self.confidence != "high":
            raise ValueError(
                "confidence must be 'high' for first-party records (ADR-0001); "
                f"got {self.confidence!r}"
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
