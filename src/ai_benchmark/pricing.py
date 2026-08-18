"""The price table: checked-in per-token prices, and the arithmetic that turns
a Codex usage breakdown into `cost_usd` (CONTEXT.md's **price table**).

Used only where an agent adapter reports tokens and no dollar figure of its
own — `cost_source='table-derived'` (`ai_benchmark.agents`). claude-code needs
none of this: it prints its own `total_cost_usd`, `cost_source='vendor-reported'`.

**The usage shape and the derivation.** A Codex turn-completed event carries
five usage numbers: input tokens (the total), cached input tokens (a subset of
the total), cache-write input tokens (also a subset of the total, disjoint
from cached input), output tokens (the total), and reasoning output tokens (a
subset of the total). This module's pricing function does not take those
five; it takes the four a price table actually prices — plain (uncached,
non-cache-write) input tokens, cached input tokens, cache-write input tokens,
and output tokens — and the caller (the codex adapter) derives them:

- **plain input = input total − cached input − cache-write input.** Cached
  and cache-write tokens are both subsets of the input total, and disjoint
  from each other; what is left over is priced at the plain input rate.
- **cache-write input is priced at its own published rate.** The pricing page
  publishes a "Cache writes" price distinct from plain input and cached
  input — there is a fourth price in this table.
- **output is priced as the output total.** Reasoning tokens are inside it and
  are never priced a second time.

**Standard, short context.** The published page prices each model across
tiers (Standard/Batch/Flex) and context lengths (short/long); this table
prices every run at Standard, short context, because that is what
`codex exec` runs under in this corpus — no run here reaches the long-context
threshold, and Batch/Flex are asynchronous or discounted tiers `codex exec`
does not use.

Ticket 05's hand computation (the codex adapter's own cost derivation) must
use this exact mapping, not reinvent it.

**What is not carried on the run row.** A v1 run row keeps only `tokens_in`
and `tokens_out` — the totals, cached and cache-write tokens counted once
inside `tokens_in` (CONTEXT.md's **run** entry) — because that is what
claude-code's rows already mean and a Codex row has to mean the same thing to
pool with them. The plain/cached/cache-write split used above exists only at
write time, inside the adapter, to compute `cost_usd`; it is never added to
the row. So "recomputable by hand from the row's tokens and the named table
version" means recomputable only as `tokens_in` priced at the *plain input*
rate — a re-derivation from the row is an approximation of the true cost
wherever any of that run's input was cached or cache-written, not a
reproduction of the number the row carries: cached tokens are over-counted at
the plain rate (it is higher than the cached rate) and cache-write tokens are
under-counted (the plain rate is lower than the cache-write rate), so the
re-derivation is neither a reliable upper nor lower bound, just an estimate.
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
    input_cache_write_per_token: float = Field(ge=0)
    output_per_token: float = Field(ge=0)


class PriceTable(BaseModel):
    """A checked-in, as-of-dated table of per-token prices per model.

    `version` is what a run row's `price_table` field names. `as_of` and
    `source_url` make the numbers traceable to a published page rather than to
    whoever typed them. `tier` names the pricing tier and context length the
    numbers were read at (e.g. `standard-short-context`) — the choice of tier
    lives on the data rather than in a comment.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: NonEmptyStr
    as_of: date
    source_url: NonEmptyStr
    tier: NonEmptyStr
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
    input_plain_tokens: int,
    input_cached_tokens: int,
    input_cache_write_tokens: int,
    output_tokens: int,
) -> float:
    """The dollar cost of one usage breakdown, under `table`.

    `input_plain_tokens`, `input_cached_tokens`, `input_cache_write_tokens`
    and `output_tokens` are already the four numbers a price table prices —
    see the module docstring for how a Codex usage event's five numbers
    collapse to these four (plain input = input total − cached input −
    cache-write input; cache-write input is priced at its own published
    cache-write rate, distinct from plain input and cached input; output is
    the output total, reasoning tokens included and not priced twice).

    Raises IngestError for a model the table does not price: a zero cost that
    looks like a free run is worse than a stopped sweep. Also raises
    IngestError for a negative token count in any of the four arguments —
    in particular, a caller that derived `input_plain_tokens` as
    `input total − cached − cache-write` and got a negative number (because
    cached + cache-write exceeded the input total) has a broken usage
    breakdown, not a free run.
    """
    prices = table.models.get(model)
    if prices is None:
        registered = ", ".join(sorted(table.models)) or "(none)"
        raise IngestError(
            f"price table {table.version!r} prices no model {model!r} — "
            f"registered models: {registered}"
        )
    negative = {
        "input_plain_tokens": input_plain_tokens,
        "input_cached_tokens": input_cached_tokens,
        "input_cache_write_tokens": input_cache_write_tokens,
        "output_tokens": output_tokens,
    }
    for name, value in negative.items():
        if value < 0:
            raise IngestError(
                f"cost_usd: {name}={value} is negative — a caller deriving "
                "input_plain_tokens as input total − cached − cache-write "
                "got a negative number, which means cached + cache-write "
                "exceeded the input total"
            )
    return (
        input_plain_tokens * prices.input_uncached_per_token
        + input_cached_tokens * prices.input_cached_per_token
        + input_cache_write_tokens * prices.input_cache_write_per_token
        + output_tokens * prices.output_per_token
    )
