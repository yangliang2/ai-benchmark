# ai-benchmark

A three-layer system for understanding coding agents: which agent × model combination is best for which category of task, at what cost.

- **Meta-aggregation layer** — ingest per-instance results from existing public benchmarks, re-sliced by our task taxonomy
- **First-party benchmark** — run targeted evals to fill cells second-hand data can't (cost, latency, harness-vs-model attribution, multi-turn tasks)
- **Selection tool** — query surface over the unified dataset: per-task-category Pareto frontiers of quality vs cost

## Agent skills

### Issue tracker

Issues and specs live in this repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Sweep protocol

Paid runs of the first-party v1 task set: isolated worktree, one agent version
per sweep, guard backups, and no `-dry` in a log's name. Read
`docs/agents/sweep-protocol.md` before launching one.

### Ticket runs (qap)

Issues are turned into graded, metered agent runs by `qap`: `qap queue add --issue N` for a
single issue, `qap plan --issue N` for a round-level parent, then `qap run`. Read
`docs/agents/qap.md` first — it says where a ticket's acceptance command comes from, which
commands in this repo are real judges (not `ruff`), why the timeouts need raising, and why a
sweep is never queued. It takes precedence over the auto-injected section below.

<!-- qap:begin -->
## qap — AI cost governance (auto-injected by `qap init`; remove with `qap init --remove`)

This project is wired into [qap](/Users/peter/projects/ai-cost-solution/README.md) (Quota Autopilot) for ticket-driven AI
development and cross-pool (Claude + ChatGPT/Codex) cost governance. Any AI session that
opens this directory can pick this up with zero extra explanation:

- **Cut the spec into tickets**: `qap plan` — one AI session turns specs/spec.md into ticket
  files under tickets/ and prints a summary (tiers, order, warnings). It writes files only;
  nothing is queued until you `qap queue add` it yourself.
- **Queue this project's tickets**: `qap queue add tickets/` — adds every `*.md` in
  filename order, skipping any ticket already queued, so it is safe to re-run after
  writing new ones.
- **Run the ticket queue**: `qap run` — no arguments needed from anywhere inside this
  project: the spec, the working directory and the queue/ledger location all come from
  .qap/config.json below. Drains tickets/, one clean session per ticket, routed by tier,
  with an automatic cascade retry on failure.
- **Check spend**: `qap report --days 7` — dual-pool cost, cache-invalidation forensics,
  governance actions. Add `--json` for machine-readable output.
- **Inspect the queue**: `qap queue list` (optionally filter: queued|running|done|failed).
- **Ticket format**: a ticket is a markdown file under tickets/ with optional YAML
  front-matter (`acceptance`, `tier`, `group`, `pool`) plus a `# Title` /
  `**What to build:**` / checklist body. See tickets/00-example.md.disabled in this
  project for the full format.
- **Config**: .qap/config.json in this project holds the default spec path, tickets
  directory, pool and tier — edit it directly; qap re-reads it on every run. Its presence
  is also what makes this directory a qap *project*: the queue and the usage ledger live
  in .qap/ next to it, so this project's tickets and spend never mix with another
  project's. `--root DIR` overrides that if you ever need it to.
- **Full command reference and AI-operator SOP**: see the qap repo's README at
  /Users/peter/projects/ai-cost-solution/README.md

This section only (between the begin/end markers) is what `qap init --remove` deletes;
.qap/ and tickets/ are this project's own data and are never touched by it.
<!-- qap:end -->
