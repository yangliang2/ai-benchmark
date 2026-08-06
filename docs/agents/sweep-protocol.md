# Sweep protocol

How a paid sweep of the first-party v1 task set is run. Read this before
launching one: every rule here is here because breaking it cost something —
paid runs destroyed, contrasts that cross an agent version, cells silently
dropped from an analysis.

A **sweep** is one round of the knob experiment: `ai-bench eval-v1 --live` over
a set of tasks, on the ladder's models, however many invocations that takes.
Reconciliation counts rounds by the sweep id the runs carry, so the sweep is
the unit this document is about.

## Before the sweep

1. **Lint clean.** `uv run ai-bench lint-v1` over the task set, and the full
   test suite green. A sweep is paid for once; an authoring mistake found
   afterwards cannot be repaired by re-running the cell, because a task ×
   agent × model cell is only ever swept once.
2. **Predictions registered.** Every task's `construction.prediction` is
   committed *before* the first paid run. The run log's append-only timeline
   is the audit trail that it came first.
3. **Name the sweep.** Pick the id now and write it down: `--sweep` has no
   default, and every invocation of this sweep — each model, each resume —
   must be given the same one. A new sweep gets a new id.

## Isolation: an isolated worktree

Run the sweep from a **dedicated git worktree**, not from a working tree any
other agent or session is touching.

The reason is on the record. During the Track-A sweep (#24) a concurrent
agent's `git stash -u` + `pop` rewrote the run log from an older snapshot and
destroyed two rows that had already been paid for. A live sweep writes its
artifact as an **untracked file in the working tree**, which is exactly what
tree-snapshotting commands (`git stash`, `git clean`, `git reset`,
`git checkout -- .`) discard or restore over.

This is why the tree-snapshot ban on agents working in this repo stays in
force, and the isolation is the belt to that braces: no agent runs a command
that snapshots, restores or deletes files beyond the specific paths it is
editing.

**Guard backups.** While the sweep runs, keep a copy of the log outside the
working tree and refresh it as rows land. It is what limited the #24 incident
to two rows. Verify the committed blob byte-for-byte against the runner's own
bytes before trusting it.

## One agent version per sweep

Pin the `claude` CLI version for the whole sweep and **do not let it change
between invocations**. If it has drifted when the next invocation is about to
start, stop: either restore the pinned version or start a new sweep under a
new id. Do not carry on and log the mixed cells.

What this protects is the only comparison the report can make. Round 1's cells
spanned three CLI versions — 44 baseline cells on 2.1.221, 45 on 2.1.222, 9 on
2.1.223 — so **every** knob-versus-baseline contrast in it crosses at least one
version boundary, and the within-round contrasts (K1's levels against each
other, K9's matched pairs) are the only ones that survive the caveat. A knob
verdict is not worth much if the version moved underneath it.

Why this is protocol and not a runner check: the runner reads the CLI version
once per invocation and stamps every row of that invocation with it, so drift
is by construction something that happens *between* invocations. The runner
would have to know which earlier logs belong to this sweep to catch it, and it
does not — a sweep spans as many log files as the operator gives it. The
operator holds that knowledge, so the operator holds this rule.

## Dry checks write to normally-named logs

A dry check — one cheap cell run to prove the pipeline works before committing
the budget — is a **real, paid, graded run**. Write it to a log named like any
other log of the sweep. Do not mark it in the filename.

Round 1 left two paid cells in `2026-08-05-dry.jsonl` and
`2026-08-05-trackb-dry.jsonl`. Reconciliation read them correctly, because it
reads every `*.jsonl` under the run-log directory and never looks at a name.
The first pass of the round-1 analysis, which filtered by filename, silently
dropped both. **No analysis may select run logs by filename.** The log's
contents say which sweep it belongs to; its name says nothing.

## During and after

- Invocations may be split by model and resumed after a crash. Give each the
  same `--sweep` id and a fresh `--log` path — the runner refuses to append to
  an existing log, so a resume is a new file, and the sweep id is what keeps
  the round whole.
- A run the environment blocked (non-empty `permission_denials`) is a broken
  run, not a failed one: it fails loudly rather than logging a verdict.
- Read the sweep before launching the next one. Rounds are sequential by
  design; reconciliation attributes a task swept in two overlapping sweeps to
  the one that started later.
- Commit the logs, then reconcile: `uv run ai-bench reconcile-v1`. Every number
  in the report is recomputable from checked-in artifacts by that one command,
  which is only true once the logs are in.
