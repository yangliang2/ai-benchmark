# Ticket runs: qap

[qap](/Users/peter/projects/ai-cost-solution/README.md) (Quota Autopilot) drives ticket work
through headless agent sessions and meters what every ticket cost, across both the Claude and
the ChatGPT/Codex pool. This repo is wired into it (`.qap/config.json` at the root); the
auto-injected section at the bottom of `AGENTS.md` is qap's own generic blurb, and **this file
overrides it wherever the two differ**, because this repo's specs live in GitHub Issues rather
than in a `specs/` file.

Local state (`.qap/`, holding the queue and the usage ledger) and the ticket files derived from
issues (`tickets/`) are both git-ignored: the issue is the source of truth, a ticket is a
derived artefact.

## The two paths from an issue to a ticket

An issue in this repo is already written at ticket granularity — one `## What to build`, one
`## Acceptance criteria` checklist, one `## Blocked by`. So the default path is the direct one:

- **One issue, one ticket**: `qap queue add --issue 52` — fetches the issue, writes
  `tickets/issue-52.md`, and enqueues it. The issue body's own front-matter block, if it has
  one, is kept verbatim (see below); the H1 becomes the ticket title. Never overwrites an
  existing ticket file.
- **One issue, many tickets**: `qap plan --issue 46` — for a round-level parent issue (#1, #16,
  #27, #36, #46) that holds a batch rather than a unit of work. One session cuts it into ticket
  files under `tickets/`, then two zero-context review sessions check the cut for coverage and
  for factual claims about this codebase. It writes files only, never queues. Exit code 3 means
  a human has to read `.qap/plan-review.md` before queueing anything.

Then `qap run` from anywhere inside the repo — spec, working directory, queue and ledger all
come from `.qap/config.json`. `qap run --close-issues` closes each ticket's source issue once
its acceptance command goes green, with a comment recording provider, model and cost.

## Give the ticket a hard acceptance command

A ticket with no `acceptance:` in its front-matter is treated as a **judgment ticket**: pinned
to the top tier and parked for human review instead of being graded. Every issue in this repo
that ends in "`uv run pytest`, `uv run mypy` all green" has a hard judge available, so say so —
otherwise a perfectly gradeable ticket burns top-tier tokens and still waits on a human.

The clean place to put it is **the issue body itself**: a front-matter block at the very top is
carried into the ticket verbatim, so the issue stays the single source of truth.

```markdown
---
acceptance: "uv run pytest tests/test_firstparty_v1_planted_defects.py && uv run mypy && uv run ai-bench lint-v1"
tier: T3
group: round4-defects
---

## Parent

#46
...
```

Failing that, edit `tickets/issue-N.md` after `queue add` writes it and re-add it.

### What counts as a hard judge here

| Command | Use it |
|---|---|
| `uv run pytest <the ticket's own test files>` | **Yes** — this is the per-ticket judge. |
| `uv run mypy` | Yes. Strict, whole-repo, seconds. |
| `uv run ai-bench lint-v1` | Yes, for anything touching `tasks/first-party-v1`. Seconds. |
| `uv run pytest` (whole suite) | Only with a raised timeout — see below. |
| `uv run ruff check` | **No.** `ruff` is not in the dev dependency group and the repo carries no ruff config, so it resolves to default rules over the whole tree — including the deliberately defective sample repos under `tasks/` — and reports thousands of findings. Fix the tooling before putting it in an acceptance command. |

Note the last row against the acceptance checklists in older issues, which name `ruff`.

### The suite is slow — raise the timeouts

qap's defaults are a 900 s session budget and a 600 s acceptance budget. The full pytest suite
in this repo runs real `git` and real subprocesses per task and does not fit in 600 s. Two ways
out, in order of preference:

1. **Scope the acceptance command to the ticket's own tests** (plus `mypy` and `lint-v1`). Fast,
   and a failure points at the ticket rather than at the repo.
2. **Raise the budget** when the whole suite really is the judge:

   ```bash
   qap run --acceptance-timeout 2400 --timeout 1800
   ```

   These are command-line flags only — `.qap/config.json` has no field for them, so a bare
   `qap run` cannot carry them.

### Run the targeted suites in-session; the full suite is the harness's

A ticket session verifies its own change with the suites its ticket names (plus `mypy`, plus
`lint-v1`) — never the whole suite. The acceptance command runs the whole suite, if the ticket's
checklist calls for it, after the session ends, under its own (raised) budget. #98's session
spent 26 of its 45 minutes inside two full-suite runs and was killed mid-run with its work
already done: the session budget and the acceptance budget are not the same clock, and burning
the session's clock on a check the acceptance command is about to run anyway buys nothing.

This holds even now that the suite runs under `pytest-xdist` (`-n auto`, `addopts` in
`pyproject.toml`) and is fast — a session still shouldn't assume it owns every core, since the
harness may be running other sessions' acceptance commands at the same time.

## Do not queue a sweep

Paid runs of the first-party task set (e.g. #57) go through
[`sweep-protocol.md`](sweep-protocol.md): isolated worktree, one agent version per sweep, guard
backups, human at the wheel. They are not ticket work and must never be handed to `qap run`,
which would spend real sweep money unattended and outside the protocol. Queue the tickets that
*build* tasks; run the sweeps by hand.

## Cost

`qap report` inside this repo is automatically scoped to this project (that is what
`.qap/config.json` buys). `qap report --days 7`, `--json` for machine reading, `--all` to see
every project. `By ticket` shows what each ticket run cost; `Cache-invalidation forensics` is
where the wasted money shows up.

`qap export --out results.jsonl` emits one record per ticket (every attempt of a cascade folded
into `attempts`) in qap's own export schema, currently version 2. Its `category` and `scale`
vocabularies are this repo's taxonomy verbatim — that is the join key — but the record shape is
qap's, not `record.schema.json`, and **nothing in `src/ai_benchmark` ingests it yet**. Writing
that ingest is the open piece of work: it would put real ticket work, cost included, into the
same matrix as the benchmark tasks.
