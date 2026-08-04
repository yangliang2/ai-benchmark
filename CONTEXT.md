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

- **task set** — the checked-in collection of first-party benchmark instances (the file `tasks/first-party-v0.yaml`; the directory `tasks/first-party-v1/`). Versioned as a whole; its name is the benchmark name.
- **task** — one first-party benchmark instance. v0: a self-contained prompt plus a **check**. v1: a **task directory**.
- **check** — the static regex that grades a run's final output as resolved or not. v0 limitation: checks demand task-specific content but do not execute anything, so `resolved` on a first-party-v0 record is pattern-verified — weaker evidence than SWE-bench's test-verified `resolved`. Grouping by benchmark keeps v0, v1 and SWE-bench from ever pooling.
- **run** — one task × combination execution with exact measurements (tokens in/out, cost USD, latency, turns) as reported by the claude CLI. A v1 run also carries its **workdir diff**.
- **raw run log** — JSONL, one row per run, appended as each run completes. The provenance boundary: live runs write it, evaluation and replay only ever read it, and a record's source is the log itself.
- **instance-level** — umbrella for the two source types that carry per-instance rows and may pool into rates (`per-instance`, `first-party`). Rows of different source types never pool together (ADR-0001).

### v1: execution-verified grading

- **task directory** — one v1 task: `task.yaml` (id, category, scale, language, prompt, grading config), `repo/`, and `grading/`.
- **starting repository** — the `repo/` directory, a small hand-authored stdlib-only repo copied fresh into the agent's workdir. What the agent sees and edits. Its top-level modules must **not be named after standard-library modules** (no `queue.py`, `types.py`, `calendar.py`) — the loader rejects such a task. Grading keeps the standard library ahead of the workdir on `sys.path`, so at grade time such a module is invisible, the standard-library one is imported instead, and the task is unsolvable however good the agent is. The loader has to enforce this because the lint cannot see it: when the standard-library module does not happen to satisfy the grading tests, the task fails pristine exactly like a good task, lints clean, and then grades every agent unresolved — indistinguishable from a merely hard task.
- **grading tests** — the held-out tests in `grading/`, which the agent never sees. Canonical: at grade time they are copied *over* the workdir, so a file the agent wrote at a grading test's path is overwritten. They must be **self-contained**: grading runs with conftest loading disabled and its pytest config pinned outside the workdir, so a grading test that relies on a `conftest.py` will not work (and the task-set lint catches it on the pristine repository).
- **workdir diff** — the graded artifact of a v1 run: the workdir's full diff (modified, added and deleted files) against the live runner's initial commit of the pristine starting repository, captured as `git add -A` + `git diff --cached --binary` against that commit's recorded id, with the operator's global and system git configuration masked out so the artifact cannot vary with the machine. A runner-owned `.gitignore` (`__pycache__/`, `*.pyc`, `.pytest_cache/`), written before the initial commit and restored before capture, keeps test-run byproducts out of the diff and never itself appears in it (which is also why a task may not ship its own). What makes replay exact; a v1 run's final message is metadata, not evidence.
- **execution-verified** — the v1 grading standard, replacing v0's pattern-verified checks: copy `repo/` to a fresh temp directory, apply the run's workdir diff, overlay `grading/`, run the grading tests with a timeout. `resolved` is 1.0 iff every one of them ran and passed — the same standard as SWE-bench's `resolved`.
  The verdict ignores what the agent wrote *around* the grading tests. pytest runs with `--noconftest` and a config pinned outside the workdir, so `conftest.py` hooks and `addopts` smuggled through `pytest.ini` / `tox.ini` / `setup.cfg` / `pyproject.toml` can neither forge a pass nor sink a correct solution; the workdir is kept *behind* the standard library on `sys.path`, so a file the agent added cannot shadow a stdlib module a grading test measures against; and the verdict reads a test report written outside the workdir rather than the exit status alone, so a run that ends before the tests finish cannot pass by accident.
  Accepted limitation: grading executes agent-written code in a **local subprocess with a timeout, not a sandbox** — the same exposure as any local SWE-bench-style eval. The live run is part of the same stance: headless claude-code auto-denies tool use not granted up front, so the v1 runner grants the agent file edits and shell commands (`--permission-mode acceptEdits --allowedTools Bash` — the narrowest grant that makes realistic coding work possible, not `bypassPermissions`) inside its throwaway workdir; a run the environment still blocked (non-empty `permission_denials`) is a broken run and fails loudly rather than logging a verdict. **The boundary this draws:** those defences stop an honest-but-messy agent, not a deliberately adversarial one — grading runs the agent's code in the same process tree as the oracle, so code that means to can still reach the report the verdict is read from and forge a pass; ruling that out needs process-level isolation, which this grader does not have. Starting repositories are stdlib-only, so grading needs no network and no installs.
- **behaviour tests / structural assertions** — the two halves of a refactor task's grading suite. Behaviour tests, named explicitly in `task.yaml`, assert the behaviour the restructuring must preserve; every other grading test is a structural assertion that the restructuring actually happened.
- **task-set lint** — the authoring invariants, checked by running the grading tests on the pristine starting repository before any paid run: grading tests must fail pristine (nothing is left to do otherwise), and a refactor task's behaviour tests must pass pristine (only its structural assertions may fail).
- **instance-level** — umbrella for the two source types that carry per-instance rows and may pool into rates (`per-instance`, `first-party`). Rows of different source types never pool together (ADR-0001).

## Provenance vocabulary

- **source** — where a record's number came from: a URL, report name, or run id (not: origin, provider).
- **source type** — how the number was produced: `first-party` (we ran it, exact measurements), `per-instance` (second-hand but instance-level), `aggregate` (second-hand summary number only).
- **confidence** — how much a record should be trusted when views weight or filter: `high` / `medium` / `low`. First-party records are high by construction; see ADR-0001 for the model.
- **as-of date** — when the underlying result was produced (not when we ingested it). Views must surface it; stale data is shown, never hidden.
