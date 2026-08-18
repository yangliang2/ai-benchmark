"""The checked-in price table (CONTEXT.md's **price table**): it loads and
names a version, an as-of date and a source URL; the pricing function's output
matches a hand computation; an unpriced model and a malformed table both fail
loudly.
"""

from pathlib import Path

import pytest

from ai_benchmark.dataset import IngestError
from ai_benchmark.pricing import (
    DEFAULT_PRICE_TABLE_PATH,
    cost_usd,
    load_price_table,
)

MODEL = "gpt-5.6-terra"


def test_checked_in_table_loads_and_names_its_provenance() -> None:
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)

    assert table.version
    assert table.as_of
    assert table.source_url == "https://platform.openai.com/docs/pricing"
    assert table.tier == "standard-short-context"
    assert MODEL in table.models

    prices = table.models[MODEL]
    # Read 2026-08-18 from platform.openai.com/docs/pricing, "Flagship
    # models — Prices per 1M tokens", Standard, short context:
    # gpt-5.6-terra $2.00 / $0.20 / $2.50 / $12.00 (input / cached input /
    # cache writes / output).
    assert prices.input_uncached_per_token == pytest.approx(2.00 / 1_000_000)
    assert prices.input_cached_per_token == pytest.approx(0.20 / 1_000_000)
    assert prices.input_cache_write_per_token == pytest.approx(2.50 / 1_000_000)
    assert prices.output_per_token == pytest.approx(12.00 / 1_000_000)


def test_cost_matches_a_hand_computation_over_a_worked_usage_breakdown() -> None:
    """The worked example: a Codex turn-completed event reporting an input
    total of 1000 tokens, 200 of them cached input and 50 of them cache-write
    input (disjoint from the 200 cached, and priced at its own cache-write
    rate — a fourth price), an output total of 500 tokens, 100 of them
    reasoning output (priced once, inside the output total).

    Plain input = 1000 − 200 − 50 = 750. The function takes exactly those
    four derived numbers — plain input, cached input, cache-write input,
    output total — not the stream's five.
    """
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)
    prices = table.models[MODEL]

    input_total = 1000
    cached_input = 200
    cache_write_input = 50
    # output_total's own 100 reasoning tokens are already inside it, per the
    # docstring's derivation — named here only in prose, since it is not a
    # separate argument.
    output_total = 500

    plain_input = input_total - cached_input - cache_write_input

    expected = (
        plain_input * prices.input_uncached_per_token
        + cached_input * prices.input_cached_per_token
        + cache_write_input * prices.input_cache_write_per_token
        + output_total * prices.output_per_token
    )

    got = cost_usd(
        table,
        MODEL,
        input_plain_tokens=plain_input,
        input_cached_tokens=cached_input,
        input_cache_write_tokens=cache_write_input,
        output_tokens=output_total,
    )

    assert got == pytest.approx(expected)
    # Pinned against the published numbers directly (input / cached input /
    # cache writes / output, $ per 1M tokens), so the test states the price
    # rather than merely echoing the table back at itself.
    assert got == pytest.approx(
        750 * (2.00 / 1_000_000)
        + 200 * (0.20 / 1_000_000)
        + 50 * (2.50 / 1_000_000)
        + 500 * (12.00 / 1_000_000)
    )


def test_unpriced_model_fails_loudly() -> None:
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)

    with pytest.raises(IngestError, match="no-such-model"):
        cost_usd(
            table,
            "no-such-model",
            input_plain_tokens=100,
            input_cached_tokens=0,
            input_cache_write_tokens=0,
            output_tokens=50,
        )


def test_negative_token_count_fails_loudly() -> None:
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)

    with pytest.raises(IngestError, match="negative"):
        cost_usd(
            table,
            MODEL,
            input_plain_tokens=-1,
            input_cached_tokens=0,
            input_cache_write_tokens=0,
            output_tokens=50,
        )


def test_cached_plus_cache_write_exceeding_the_input_total_fails_loudly() -> None:
    """A caller derives `input_plain_tokens` as
    `input total − cached − cache-write`. If cached + cache-write exceeds the
    input total, that derivation goes negative before it ever reaches
    `cost_usd` — and `cost_usd` refuses it, same as any other negative count.
    """
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)

    input_total = 100
    cached_input = 80
    cache_write_input = 30  # 80 + 30 = 110 > 100

    plain_input = input_total - cached_input - cache_write_input
    assert plain_input < 0

    with pytest.raises(IngestError, match="negative"):
        cost_usd(
            table,
            MODEL,
            input_plain_tokens=plain_input,
            input_cached_tokens=cached_input,
            input_cache_write_tokens=cache_write_input,
            output_tokens=50,
        )


def test_missing_table_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(IngestError):
        load_price_table(tmp_path / "does-not-exist.json")


def test_malformed_json_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "price-table.json"
    path.write_text("{not json")

    with pytest.raises(IngestError):
        load_price_table(path)


def test_table_missing_a_required_field_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "price-table.json"
    path.write_text(
        '{"as_of": "2026-08-18", "source_url": "https://example.com", "models": {}}'
    )

    with pytest.raises(IngestError):
        load_price_table(path)


def test_table_with_an_unknown_field_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "price-table.json"
    path.write_text(
        """
        {
          "version": "test-1",
          "as_of": "2026-08-18",
          "source_url": "https://example.com",
          "models": {},
          "unexpected": true
        }
        """
    )

    with pytest.raises(IngestError):
        load_price_table(path)


def test_model_with_a_negative_price_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "price-table.json"
    path.write_text(
        """
        {
          "version": "test-1",
          "as_of": "2026-08-18",
          "source_url": "https://example.com",
          "tier": "standard-short-context",
          "models": {
            "some-model": {
              "input_uncached_per_token": -0.000001,
              "input_cached_per_token": 0.0000005,
              "input_cache_write_per_token": 0.0000025,
              "output_per_token": 0.000008
            }
          }
        }
        """
    )

    with pytest.raises(IngestError):
        load_price_table(path)
