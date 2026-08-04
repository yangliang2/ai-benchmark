# Domain glossary

The vocabulary this project uses. Skills and contributors should use these terms exactly; synonyms noted as "not: …" are deliberately avoided.

## Core concepts

- **Unified dataset** — the single store all three layers read and write: one JSONL file of validated **records**. It is the project's only test seam (not: database, results table).
- **Record** — one row of the unified dataset: one **combination**'s result on one **benchmark instance**, or an aggregate result when per-instance data is unavailable. Machine-readable schema: `ai_benchmark.schema.Record` (see ADR-0001).
- **Combination** — an agent × model pairing, e.g. claude-code × claude-sonnet-5. The unit being evaluated (not: setup, config).
- **Agent** — the coding harness/scaffold (claude-code, aider, cursor, …), independent of the model driving it (not: assistant, tool).
- **Benchmark instance** — one task inside a source benchmark, e.g. one SWE-bench issue (not: problem, sample).
- **Capability matrix** — the conceptual grid task category × combination × dimension the whole project exists to fill. Empty cells are as informative as full ones.
- **Quality metric** — the named measure a record's quality value is expressed in (e.g. `resolved`, `resolution-rate`, `pass-rate`). Values under different quality metrics are never directly comparable (not: score).
- **Pareto frontier** — within one task category, the set of combinations not dominated on both quality and cost.

## Task taxonomy v0

Every benchmark instance and first-party eval task is classified into exactly one category. When two categories seem to apply, the **primary deliverable** of the task decides.

- **bug-fix** — correct existing behaviour that is wrong.
  Includes: SWE-bench-style issue→patch tasks; regression fixes.
  Excludes: adding a missing capability someone filed as a "bug" (feature-dev); making newly written tests pass (test-authoring or feature-dev).
- **feature-dev** — add new user-visible capability.
  Includes: new endpoints, commands, options; extending behaviour to new cases.
  Excludes: pure restructuring (refactor); UI-only work (frontend-ui).
- **refactor** — behaviour-preserving restructuring.
  Includes: renames, module splits, interface reshaping with unchanged behaviour.
  Excludes: any change with intended behaviour difference (bug-fix or feature-dev).
- **test-authoring** — tests are the primary deliverable.
  Includes: writing missing tests for existing behaviour; hardening flaky tests.
  Excludes: tests written incidentally while implementing a feature (feature-dev).
- **frontend-ui** — visual interface implementation.
  Includes: components, layout, styling, implementing a mockup.
  Excludes: backend API work supporting the UI (feature-dev).
- **infra-config** — build, CI/CD, deployment, dependencies, configuration.
  Includes: pipeline fixes, dependency upgrades, Dockerfiles, lint/tooling setup.
  Excludes: application-code changes those upgrades force (usually refactor).
- **codebase-comprehension** — answer questions about code without changing it.
  Includes: explain-this-module, locate-where-X-happens, review-style analysis.
  Excludes: any task whose deliverable is an edit.
- **unclassified** — not yet classified, or genuinely unclassifiable. Never force-fit; count of unclassified instances must stay visible.

## Task annotations

Orthogonal to category:

- **scale** — `single-file` (edits confined to one file), `cross-file` (edits span files), `unknown`.
- **language** — primary language of the task's repo (lowercase, e.g. `python`, `typescript`), absent when not meaningful.

## Classification vocabulary

- **Label** — the classification verdict for one benchmark instance: a task category plus the task annotations (scale, language). Labels fill gaps in a record; they never overwrite source-derived facts (not: tag, annotation set).
- **Classification cache** — the committed JSON file keyed by `benchmark/instance_id` holding one label per instance. A warm cache makes classification deterministic and free; an unclassifiable verdict is cached too, so it is never re-asked and never force-fitted.
- **Instance context** — the committed JSON file (`data/instance-context.json`, keyed like the classification cache) holding what an instance actually asked for: its **problem statement** and the **patch file list** (files changed by the reference solution). The problem statement is classifier evidence; the patch file list makes scale mechanical (one file → `single-file`, several → `cross-file`) with no LLM call, and a mechanical scale always beats an LLM guess.

## First-party eval vocabulary

- **task set** — the checked-in file of first-party benchmark instances (e.g. `tasks/first-party-v0.yaml`). Versioned as a whole; its name is the benchmark name.
- **task** — one first-party benchmark instance: a self-contained prompt plus a **check**.
- **check** — the static regex that grades a run's final output as resolved or not. v0 limitation: checks demand task-specific content but do not execute anything, so `resolved` on a first-party-v0 record is pattern-verified — weaker evidence than SWE-bench's test-verified `resolved`. Grouping by benchmark keeps the two from ever pooling; a v1 task set should grade by running tests.
- **run** — one task × combination execution with exact measurements (tokens in/out, cost USD, latency, turns) as reported by the claude CLI.
- **raw run log** — JSONL, one row per run, appended as each run completes. The provenance boundary: live runs write it, evaluation and replay only ever read it, and a record's source is the log itself.
- **instance-level** — umbrella for the two source types that carry per-instance rows and may pool into rates (`per-instance`, `first-party`). Rows of different source types never pool together (ADR-0001).

## Provenance vocabulary

- **source** — where a record's number came from: a URL, report name, or run id (not: origin, provider).
- **source type** — how the number was produced: `first-party` (we ran it, exact measurements), `per-instance` (second-hand but instance-level), `aggregate` (second-hand summary number only).
- **confidence** — how much a record should be trusted when views weight or filter: `high` / `medium` / `low`. First-party records are high by construction; see ADR-0001 for the model.
- **as-of date** — when the underlying result was produced (not when we ingested it). Views must surface it; stale data is shown, never hidden.
