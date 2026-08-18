"""The price table: checked-in per-token prices, and the arithmetic that turns
a Codex usage breakdown into `cost_usd` (CONTEXT.md's **price table**).

Used only where an agent adapter reports tokens and no dollar figure of its
own — `cost_source='table-derived'` (`ai_benchmark.agents`). claude-code needs
none of this: it prints its own `total_cost_usd`, `cost_source='vendor-reported'`.

**The usage shape and the derivation.** A Codex turn-completed event carries
five usage numbers: input tokens (the total), cached input tokens (a subset of
the total), cache-write input tokens (also a subset of the total), output
tokens (the total), and reasoning output tokens (a subset of the total). This
module's pricing function does not take those five; it takes the three a price
table actually prices — uncached input tokens, cached input tokens, and output
tokens — and the caller (the codex adapter) derives them:

- **uncached input = input total − cached input.** Cache-write tokens are
  already inside the uncached input total (they are a subset of it, the same
  way cached tokens are), and OpenAI publishes no separate cache-write price —
  caching is automatic and only *reads* are discounted — so they are priced at
  the plain uncached-input rate. There is no fourth price in this table.
- **output is priced as the output total.** Reasoning tokens are inside it and
  are never priced a second time.

Ticket 05's hand computation (the codex adapter's own cost derivation) must
use this exact mapping, not reinvent it.

**What is not carried on the run row.** A v1 run row keeps only `tokens_in`
and `tokens_out` — the totals, cached tokens counted once inside `tokens_in`
(CONTEXT.md's **run** entry) — because that is what claude-code's rows already
mean and a Codex row has to mean the same thing to pool with them. The
cached/uncached split used above exists only at write time, inside the
adapter, to compute `cost_usd`; it is never added to the row. So "recomputable
by hand from the row's tokens and the named table version" means recomputable
only as `tokens_in` priced at the *uncached* rate — a re-derivation from the
row is an upper bound on the true cost wherever any of that run's input was
cached, not a reproduction of the number the row carries.
"""

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_benchmark.dataset import IngestError
from ai_benchmark.schema import NonEmptyStr

DEFAULT_PRICE_TABLE_PATH = Path("data/price-table.json")


class ModelPrices(BaseModel):
    """Per-token USD prices one model needs to price a Codex usage breakdown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_uncached_per_token: float = Field(ge=0)
    input_cached_per_token: float = Field(ge=0)
    output_per_token: float = Field(ge=0)


class PriceTable(BaseModel):
    """A checked-in, as-of-dated table of per-token prices per model.

    `version` is what a run row's `price_table` field names. `as_of` and
    `source_url` make the numbers traceable to a published page rather than to
    whoever typed them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: NonEmptyStr
    as_of: date
    source_url: NonEmptyStr
    models: dict[str, ModelPrices]


def load_price_table(path: Path = DEFAULT_PRICE_TABLE_PATH) -> PriceTable:
    """Load and validate the checked-in price table.

    Raises IngestError, naming the offending field(s), on a missing or
    malformed table — a price table that fails to load must stop a sweep
    rather than let it run priced at nothing.
    """
    try:
        raw = json.loads(path.read_text())
    except OSError as error:
        raise IngestError(f"{path}: cannot read price table — {error}") from error
    except json.JSONDecodeError as error:
        raise IngestError(f"{path}: not valid JSON — {error}") from error
    try:
        return PriceTable.model_validate(raw)
    except ValidationError as error:
        raise IngestError(f"{path}: invalid price table — {error}") from error


def cost_usd(
    table: PriceTable,
    model: str,
    *,
    input_uncached_tokens: int,
    input_cached_tokens: int,
    output_tokens: int,
) -> float:
    """The dollar cost of one usage breakdown, under `table`.

    `input_uncached_tokens`, `input_cached_tokens` and `output_tokens` are
    already the three numbers a price table prices — see the module docstring
    for how a Codex usage event's five numbers collapse to these three
    (uncached input = input total − cached input, cache-write tokens included
    at the uncached rate; output is the output total, reasoning tokens
    included and not priced twice).

    Raises IngestError for a model the table does not price: a zero cost that
    looks like a free run is worse than a stopped sweep.
    """
    prices = table.models.get(model)
    if prices is None:
        registered = ", ".join(sorted(table.models)) or "(none)"
        raise IngestError(
            f"price table {table.version!r} prices no model {model!r} — "
            f"registered models: {registered}"
        )
    return (
        input_uncached_tokens * prices.input_uncached_per_token
        + input_cached_tokens * prices.input_cached_per_token
        + output_tokens * prices.output_per_token
    )
