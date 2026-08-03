# ADR-0001: Unified record schema with mandatory provenance and confidence

Status: accepted
Date: 2026-08-03

## Context

The project aggregates results from heterogeneous places — public leaderboards with only summary numbers, benchmarks with per-instance dumps, and our own eval runs with exact cost measurements. All three layers (meta-aggregation, first-party benchmark, selection views) must read and write one store, and views must be able to weigh a first-party measurement above a scraped leaderboard number. The spec (#1) fixes a single test seam: the unified dataset.

## Decision

One flat record shape for every result, defined once in `ai_benchmark.schema.Record` (pydantic) and enforced at ingest time via `validate_record`. One record = one combination's result on one benchmark instance; aggregates use the same shape.

Field groups:

- **Task**: `category` (taxonomy v0, `unclassified` allowed), `scale`, `language?`
- **Combination**: `agent`, `agent_version?`, `model`
- **Task identity**: `benchmark`, `instance_id?`
- **Quality**: `quality_metric` (named, e.g. `resolved`, `resolution-rate`), `quality_value`
- **Cost dimensions** (all optional — most second-hand sources lack them): `tokens_in`, `tokens_out`, `cost_usd`, `latency_s`, `turns`. `cost_usd` is always **USD per benchmark instance**; sources that publish whole-run cost are normalized at ingest using the published case count (e.g. Aider's `total_cost / test_cases`) — one field must not hold two units.
- **Provenance** (all mandatory): `source`, `source_type`, `confidence`, `as_of`

Cross-field rules: `instance_id` is required unless `source_type` is `aggregate`; `first-party` records must have `confidence: high` (enforced at the seam, not by convention).

`category` additionally admits `unclassified` — an escape hatch beyond taxonomy v0's seven categories so ingestion never force-fits and unclassified counts stay visible (spec #1 story 13; ticket #3 ingests before classification exists).

For non-Python consumers, the schema is exported as JSON Schema to `record.schema.json` at the repo root; a test keeps the export in sync with the pydantic model.

### Provenance/confidence model

- `source_type` states *how the number was produced*: `first-party` | `per-instance` | `aggregate`. It is structural fact, not judgement.
- `confidence` (`high`/`medium`/`low`) states *how much to trust it*, set by the ingester: first-party runs are `high` (schema-enforced); per-instance second-hand data defaults to `medium`; aggregates and anything with known contamination or methodology doubts get `low`. Views filter or weight by it; records never get silently dropped.

## Rationale

- **Flat over normalized**: no separate tables for agents/models/benchmarks. The dataset is analytical, append-mostly, and consumed by pandas-style slicing; joins would buy nothing and cost a database.
- **Optional cost fields over a separate cost table**: absence of cost data is the norm for second-hand sources, and "gap visible in the same row" is exactly what the capability matrix needs.
- **Named quality metric over a universal score**: resolution rate, pass rate, and edit accuracy are not comparable; pretending one `score` field exists would be false precision. Cross-metric comparison is a views-layer concern.
- **Provenance mandatory from day one**: retrofitting provenance after mixing sources is near-impossible; making it required is the cheap moment.
- **Validation at the seam**: every ingester funnels through `validate_record`, so malformed source data fails loudly at ingest, and the seam is the only place tests need to live.

## Consequences

- Every future ingester (#3, #5) and the first-party runner (#7) must emit records through `validate_record`; schema changes are ADR-worthy events.
- Aggregate and per-instance rows coexist; queries must group with `source_type` in mind to avoid double counting (a combination may appear both ways).
- The schema will grow (e.g. multi-turn fields); `extra="forbid"` means additions are explicit migrations, not silent drift.
