# ADR-0002: Categories name engineering actions

Status: accepted
Date: 2026-08-17

## Context

This ADR records a decision already taken and already implemented — it
decides nothing new; it puts the reasoning in one findable place instead of
leaving it spread across design-note sections (round-4 design note, §45.7).

The task taxonomy (`ai_benchmark.schema.TaskCategory`) exists to fill one
axis of the capability matrix: category × combination × dimension. Early in
the taxonomy's life, two of its members — `frontend-ui` and `infra-config` —
named *where* work happens rather than *what* is done. That put a frontend
bug fix in the position of having to pick one of two boxes that had nothing
to do with the action it performed, and it left no box at all for a backend
refactor or a CI configuration feature. `CONTEXT.md`'s "Task taxonomy" and
"Task annotations" sections hold the current, authoritative wording; this
ADR explains why the taxonomy landed there.

## Decision

A **category is one engineering action**: what is done, never what kind of
ticket the work arrived as, and never where it happens. Every benchmark
instance and first-party eval task is classified into exactly one category,
because a benchmark task needs one gradeable deliverable and can therefore
only measure one action. A real ticket, by contrast, is a *sequence* of
actions — investigate, then edit, then test — and that relation is
documented rather than keyed on: there is no multi-label category and no
category tuple. Where a task's work spans several actions, the **primary
deliverable** decides which category it is filed under.

`frontend-ui` and `infra-config` are retired. They named *where* work
happens, not what was done, so they are `surface` values now (`frontend`,
`infrastructure` respectively — `ai_benchmark.schema.Surface`). A record or
task that still names one of the two retired values is refused, by name,
with the value it became (`RETIRED_CATEGORIES` in
`src/ai_benchmark/schema.py:46`, enforced by `_reject_retired_category`
before the `Literal` validator would otherwise turn it into an anonymous
"not one of these eleven").

## Rationale

- **One action per task, because grading needs one deliverable.** A task
  that tried to measure "fix this bug in the frontend" as two facts at once
  would need two gradeable outcomes; splitting the "what" (category) from
  the "where" (surface) keeps each task's deliverable singular.
- **Where is orthogonal to what.** A bug can be fixed, a feature added, or a
  refactor performed in a frontend, in infrastructure, or in the
  application proper — `surface` crosses every category rather than
  competing with two of its members for the same slot.
- **The primary deliverable resolves ambiguity mechanically.** A ticket that
  touches several actions is common in reality; picking the deliverable that
  the task is graded on gives a single, repeatable rule for filing it,
  rather than leaving classification to judgement calls that would drift
  between authors.

## Alternatives considered

- **Multi-label categories** (a task may carry more than one category).
  Rejected: it would let a task's deliverable be ambiguous, which breaks
  grading (one task, one gradeable outcome) and breaks the capability
  matrix's row key, which groups strictly by category.
- **A category tuple** (e.g. `(action, surface)` as the unit that keys the
  matrix). Rejected for the same reason `frontend-ui`/`infra-config` were
  retired in the other direction: it would force every category to be
  authored against every surface, inflating the taxonomy combinatorially for
  a distinction (where) that most categories don't need disclosed as part of
  their identity — `surface` already carries it as an annotation, not a key.
- **Renaming the field rather than retiring the two values** (e.g. calling
  the existing field something broader that could hold both actions and
  locations). Rejected: it would leave "what" and "where" merged inside one
  vocabulary indefinitely, so the underlying confusion — a frontend bug fix
  having to pick one box instead of two independent facts — would persist
  under a new name instead of being resolved.

## Consequences

- The one machine-readable definition of the action vocabulary is
  `ai_benchmark.schema.TaskCategory`; `CONTEXT.md`'s "Task taxonomy" section
  glosses what each action means for human readers.
- `frontend-ui` and `infra-config` are refused wherever a category is
  validated — not silently coerced — via `RETIRED_CATEGORIES` in
  `src/ai_benchmark/schema.py:46`; the refusal message names the `surface`
  value the record or task should use instead.
- `surface` (`ai_benchmark.schema.Surface`: `application`, `frontend`,
  `infrastructure`, `unknown`) is an orthogonal annotation, optional
  everywhere and defaulting to `unknown`. It is disclosed on a record or
  task rather than grouped by: the capability matrix and the calibration
  view key on category (and scale), not on surface.
- Because `surface` defaults rather than being required, no stored record
  needed migrating when it arrived — the two retired categories are refused
  only going forward, at the validation seam.
