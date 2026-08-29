# Runbook: The round 13 sweep (§118)

This is the operational record for running the nine cells of round 13's sweep of `performance-optimisation` tasks. Every rule stated here cost something; read `docs/agents/sweep-protocol.md` entire before launching the sweep.

Round 13 has **no payment path and no grader pre-flight**, because no cell is point-graded. The round is the first since round 9 whose verdict path spends no grader dollar.

## 1. The gate that stands in front of the sweep: the task-set lint's two pristine invariants

**Every member of one contrast shares one limit**, and the two invariants over the three tasks are both hard gates.

The round's **single hard gate** is the **task-set lint's two pristine invariants** over all three `performance-optimisation` tasks, stated as a universal quantifier:

- For every one of the three tasks, the **whole grading suite must not pass** on the pristine repository.
- For every one of the three tasks, the **named behaviour half must pass** on it.

Both invariants are already held by `lint_task_set`'s per-task tail in `src/ai_benchmark/firstparty_v1.py`. The first is the standing grading-must-not-pass-on-pristine rule, holding for every task category. The second is the behaviour-tests-pass-on-pristine rule, extended from `refactor` to `performance-optimisation` by ticket 02's loader move.

**The kill discipline:** Run `uv run ai-bench lint-v1` clean over the task set and the full test suite green, before the first paid cell. A failed gate stops the round with a record, `performance-optimisation` stays absent, and the sweep does not run.

## 2. The payment path this round does not have

No cell is point-graded, no grader dollar is in the verdict path, and DEEPSEEK_API_KEY is needed by no column. The Codex column needed it in round 12 for grading and this round does not, because grading a perf task is running two held-out suites. The round therefore makes **no** session-memory disclosure of its own and prints no key probe. The standing disclosure of DEEPSEEK_API_KEY storage lives in the round-10/11/12 runbooks and records where the key was used.

## 3. The pre-flight, in order

Before the first paid cell:

1. **§118's registered figures unchanged and the three ids in its register match the corpus.** Ticket 05 fills the three task ids. §118 registers the requirement that the three tasks put three different performance questions.

2. **Sweep id `round-13` on every invocation.** `--sweep` has no default and a resume reuses the same id.

3. **`LIVE_RUN_LIMITS_S` confirmed at `performance-optimisation: 600` and not touched.** Ticket 02 registered it. All nine cells run at **600 s**. No cell's limit is adjusted during the sweep, and no cross-round caveat arises.

4. **`codex login status` checked here, at the gate**, and not before.

5. **No new sweep rows under `data/first-party-v1-runs/` since §118's registration** other than this sweep's own. Run:
   ```bash
   find data/first-party-v1-runs -type f -newermt 2026-08-29
   ```
   The date is the registration's date from §118. Only files modified after that date should be this sweep's own logs.

6. **The CLI versions of both harnesses captured fresh before the first cell** and held constant across every invocation. Round 12 ran at claude-code 2.1.246 and codex-cli 0.147.0. The runbook says **re-pin, do not assume**. Capture the versions:
   ```bash
   claude --version   # the claude-code harness's CLI binary is `claude`
   codex --version
   ```
   Record these in the round's record when the sweep completes.

## 4. The invocation

An **isolated git worktree**, with the merge and the cleanup run **from the main tree**, fast-forward when the sweep is complete.

A **dry cell first, in its own invocation, graded alone** — one of the nine, a real paid cell, never a rehearsal, never re-run — so a mis-shaped grade is found on one cell rather than nine. Its log is named like any other log of the sweep; **the protocol bans `-dry` in a log's name**. Round 1 left two paid cells in `-dry`-named logs and the first pass of that analysis silently dropped both.

The remaining eight follow in further invocations under the same `--sweep round-13`, cells chosen with **`--task`**, a **fresh `--log` per invocation** under `data/first-party-v1-runs/` (round 8's naming: `2026-08-20-r8-a.jsonl` and kin; this round's are `2026-XX-XX-r13-*.jsonl`), and **Guard backups per invocation** kept outside the worktree and verified byte-for-byte against the committed logs afterwards.

## 5. The three columns, unchanged from rounds 7, 8, 10, 11 and 12

- `claude-code` × `claude-haiku-4-5`
- `claude-code` × `claude-sonnet-5`
- `codex` × `gpt-5.6-terra` at reasoning `medium`

Nine cells, nothing re-run: a task × agent × model cell is only ever swept once.

## 6. What a perf cell's grading does, so the operator can recognise a mis-shaped one

`resolved` is **both held-out suites passing**, computed from execution in the run's own workdir — no grader call, no network in the verdict path, and **no wall-clock reading anywhere**, not even as a disclosed non-gating one. The two suites are:

- **Behaviour suite** — correctness unchanged, must pass on the pristine repository and on the reference solution.
- **Complexity suite** — operation counts across held-out input sizes, ratio-bounded or ceiling-bounded, instrumented through seams the task repository already owns; must fail on the pristine repository and pass on the reference.

A cell that comes back unresolved is a behaviour failure (behaviour suite did not pass both times) or an unmet complexity bound (complexity suite did not pass on the reference solution). Read the grading suite output to tell them apart.

## 7. When a run breaks mid-sweep

A broken run (non-empty `permission_denials`) writes no row and is not a failed one. The sweep resumes under the same id in a fresh log, and the empty log of a failed invocation is left as the record of it.

**On a connection failure, probe the local proxy before concluding a vendor is down.** This machine's system proxy has produced a local `Connection refused` that reads like an outage. Probe with:
```bash
curl --noproxy '*' https://api.anthropic.com/
```
If this succeeds, the machine's proxy was blocking; if it fails, the vendor is down or unreachable.

## 8. After the sweep

1. Commit the logs.
2. Run `uv run ai-bench reconcile-v1`.
3. Run `uv run ai-bench calibrate-v1` — the round that reconciles but is never calibrated leaves the selection-facing artifact a round behind the corpus.

**Nothing of this round's grading is a rulings archive.** There is **no `prove-points-v1` step and no rulings directory to commit**. This round authors no point key, so all proof machinery stays absent.

