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
    assert table.source_url.startswith("http")
    assert MODEL in table.models


def test_cost_matches_a_hand_computation_over_a_worked_usage_breakdown() -> None:
    """The worked example: a Codex turn-completed event reporting an input
    total of 1000 tokens, 200 of them cached input and 50 of them cache-write
    input (a subset of the uncached 800, priced at the uncached rate — there
    is no fourth price), an output total of 500 tokens, 100 of them reasoning
    output (priced once, inside the output total).

    Uncached input = 1000 − 200 = 800 (the 50 cache-write tokens ride along
    inside it, already accounted for). The function takes exactly those three
    derived numbers — uncached input, cached input, output total — not the
    stream's five.
    """
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)
    prices = table.models[MODEL]

    input_total = 1000
    cached_input = 200
    # cache_write_input = 50, output_total's own 100 reasoning tokens: both
    # already inside the totals above, per the docstring's derivation — named
    # here only in prose, since neither is a separate argument.
    output_total = 500

    uncached_input = input_total - cached_input

    expected = (
        uncached_input * prices.input_uncached_per_token
        + cached_input * prices.input_cached_per_token
        + output_total * prices.output_per_token
    )

    got = cost_usd(
        table,
        MODEL,
        input_uncached_tokens=uncached_input,
        input_cached_tokens=cached_input,
        output_tokens=output_total,
    )

    assert got == pytest.approx(expected)
    # Pinned against the checked-in numbers directly, so the test states the
    # price rather than merely echoing the table back at itself.
    assert got == pytest.approx(
        800 * 0.000002 + 200 * 0.0000005 + 500 * 0.000008
    )


def test_unpriced_model_fails_loudly() -> None:
    table = load_price_table(DEFAULT_PRICE_TABLE_PATH)

    with pytest.raises(IngestError, match="no-such-model"):
        cost_usd(
            table,
            "no-such-model",
            input_uncached_tokens=100,
            input_cached_tokens=0,
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
          "models": {
            "some-model": {
              "input_uncached_per_token": -0.000001,
              "input_cached_per_token": 0.0000005,
              "output_per_token": 0.000008
            }
          }
        }
        """
    )

    with pytest.raises(IngestError):
        load_price_table(path)
