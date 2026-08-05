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
  Accepted limitation: grading executes agent-written code in a **local subprocess with a timeout, not a sandbox** — the same exposure as any local SWE-bench-style eval. The live run is part of the same stance: headless claude-code auto-denies tool use not granted up front, so the v1 runner grants the agent full tool use (`--permission-mode bypassPermissions`) inside its throwaway workdir — a narrower per-tool allowlist was tried first and aborted a real sweep when a model read outside its workdir, and behaviour-driven denials recur on retry; a run the environment still blocked (non-empty `permission_denials`) is a broken run and fails loudly rather than logging a verdict. **The boundary this draws:** those defences stop an honest-but-messy agent, not a deliberately adversarial one — grading runs the agent's code in the same process tree as the oracle, so code that means to can still reach the report the verdict is read from and forge a pass; ruling that out needs process-level isolation, which this grader does not have. Starting repositories are stdlib-only, so grading needs no network and no installs.
- **behaviour tests / structural assertions** — the two halves of a refactor task's grading suite. Behaviour tests, named explicitly in `task.yaml`, assert the behaviour the restructuring must preserve; every other grading test is a structural assertion that the restructuring actually happened.
- **task-set lint** — the authoring invariants, checked before any paid run. Most are checked by running the grading tests on the pristine starting repository: grading tests must fail pristine (nothing is left to do otherwise), and a refactor task's behaviour tests must pass pristine (only its structural assertions may fail). The rest are read from **construction** metadata rather than run — a task outside the **zero-knob baseline** must declare one, a baseline task must not, and a **task family** must be one underlying change with exactly one knob moving across it.
- **reference solution** — a full solved copy of a task's starting repository, proving the task solvable: the test suite grades every checked-in task's reference solution `resolved` (and the empty diff unresolved) through the same execution-verified pipeline real runs go through. Lives in `tasks/first-party-v1-solutions/<task-id>/`, outside the task directory, so the loader, the runner, the lint and pytest collection never see it and it can never reach the agent.
- **instance-level** — umbrella for the two source types that carry per-instance rows and may pool into rates (`per-instance`, `first-party`). Rows of different source types never pool together (ADR-0001).

### Knob-experiment vocabulary

Task construction as experimental design: a task's difficulty is meant to come from named, independently settable causes rather than from whatever the author happened to write. Defined in full in `docs/design/task-difficulty-and-ex-ante-profiles.md` sections 8–10.

- **knob** — one named, independently settable cause of difficulty, `K1`–`K11`, each traceable to a step a human architect actually performs (K1 decision openness, K8 safety-net quality, K9 crux depth, …). A task **activates** a knob at a **level**; K1's and K8's levels are enumerated ladders, the rest are recorded as written until the experiment pins them down (not: dimension, factor).
- **construction** — the block in a task's `task.yaml` recording how the task was built: its knob activations, its **difficulty prediction**, its **task family** where it belongs to one, and — for a vendored starting repository — its **substrate provenance**. Validated by the task model, required by the lint on every task outside the baseline and refused on every task inside it.
- **zero-knob baseline** — the 22 tasks authored before the knob experiment. They carry no construction block, and that absence *is* their declaration: reconciliation reads round-1 outcomes against them as controls. The set is frozen in code, so a new task cannot join it by omission.
- **task family** — several task directories (at least two) built from one underlying change, varying exactly one knob and holding everything else constant (repo, grading tests, diff target). Variants are self-contained directories sharing a naming stem and a family id; the starting repositories and grading suites are identical copies, because self-containedness beats deduplication — and the lint reads them byte for byte, since copies drift silently. Their taxonomy annotations (category, scale, language) must agree too, or one family's variants scatter across capability-matrix cells that are never compared. What must *not* be identical is the prompt: with everything else held constant it is where a spec-side knob actually moves, so two variants sharing one prompt declare a gradient the agent never sees. The levels a family sets must be distinct, or a variant is duplicated rather than added, but they need not cover the whole ladder: a three-variant K8 family (covered → bare → misleading) simply says less than a full sweep would, which is the author's call.
- **difficulty prediction** — the task author's pre-registered expectation, recorded before the task's first paid run: the **rung** of the operational difficulty ladder it should land on (`haiku-solvable` / `sonnet-only` / `unsolved`) plus a one-line rationale. Pre-registration is what makes the knob theory falsifiable rather than fitted to the sweep afterwards; the raw run log's append-only timeline is the audit trail that the prediction came first, and the rationale is what a missed prediction teaches (not: estimate, difficulty score).
- **substrate** — the starting repository seen as raw material: hand-authored (an artifact we made) or a cold OSS repository vendored as a snapshot tree at a pinned commit and then surgically edited to set terrain knobs. **Substrate provenance** records origin URL, the pinned commit, the license, and every **modification**, each naming the knob it sets — and that knob must be one the task itself activates, because an edit answering to no declared knob is difficulty the task's profile does not account for.

## Provenance vocabulary

- **source** — where a record's number came from: a URL, report name, or run id (not: origin, provider).
- **source type** — how the number was produced: `first-party` (we ran it, exact measurements), `per-instance` (second-hand but instance-level), `aggregate` (second-hand summary number only).
- **confidence** — how much a record should be trusted when views weight or filter: `high` / `medium` / `low`. First-party records are high by construction; see ADR-0001 for the model.
- **as-of date** — when the underlying result was produced (not when we ingested it). Views must surface it; stale data is shown, never hidden.
