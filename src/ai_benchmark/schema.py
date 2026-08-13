"""The record schema — the validation gate on the unified dataset.

One Record = one combination's result on one benchmark instance, or an
aggregate when per-instance data is unavailable. See ADR-0001 and CONTEXT.md
for the vocabulary. Non-Python consumers use the exported record.schema.json.
"""

from collections.abc import Mapping
from datetime import date
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

# The one definition of the taxonomy: ten engineering *actions* plus the
# escape hatch. A category says what is done, never what kind of ticket the
# work arrived as; one task measures exactly one action, while a real ticket
# is a sequence of them (CONTEXT.md). Everything that needs the list — the v0
# and v1 task models, the classifier's prompt — reads it from here.
TaskCategory = Literal[
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
]

Surface = Literal["application", "frontend", "infrastructure", "unknown"]

# The categories that named *where* work happens rather than what is done: one
# can fix a bug, add a feature or refactor in each, so beside actions they
# forced a frontend bug fix to pick one of two boxes. They are the `surface`
# annotation now, and each maps to the value it became.
RETIRED_CATEGORIES: Mapping[str, Surface] = {
    "frontend-ui": "frontend",
    "infra-config": "infrastructure",
}


def _reject_retired_category(value: Any) -> Any:
    """Refuse a retired category by name, before the Literal turns it into an
    anonymous "not one of these eleven" — a stale row is a vocabulary change
    to follow, not a typo to correct."""
    if isinstance(value, str) and value in RETIRED_CATEGORIES:
        raise ValueError(
            f"{value!r} is no longer a task category: categories name "
            "engineering actions, and where the work happens is now the "
            f"'surface' annotation (surface: {RETIRED_CATEGORIES[value]})"
        )
    return value


# What models annotate `category` with: the vocabulary, plus the retirement
# notice. `TaskCategory` itself stays a bare Literal, so get_args() over it
# still yields exactly the vocabulary.
TaskCategoryField = Annotated[TaskCategory, BeforeValidator(_reject_retired_category)]

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

    category: TaskCategoryField
    scale: Scale
    surface: Surface = "unknown"
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

    @property
    def identity_key(self) -> tuple[str, str, str, str, str]:
        """What makes a record unique in the unified dataset — ingesters replace
        on this key, and the dataset is ordered by it."""
        return (
            self.benchmark,
            self.instance_id or "",
            self.agent,
            self.model,
            self.quality_metric,
        )

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
