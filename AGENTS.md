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
