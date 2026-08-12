---
name: frontier
description: Drive the open ticket frontier to completion — one fresh subagent per ticket, evidence-gated closes, hard stop at thinking-layer boundaries. Use when the user types /frontier, says 推进/continue the frontier, or wants agent-ready tickets executed until done or blocked. Pairs with the native /goal command for unattended continuation.
---

# Frontier — ticket executor

Execute agent-ready tickets continuously while preserving the workflow's core
separation: **thinking** (grill → to-spec → to-tickets, always human-triggered)
versus **doing** (this skill). /frontier never invents work. When the frontier is
empty and the goal is not met, it names the missing upstream step and stops —
it does not improvise tickets, specs, or scope.

## Arguments

- *(none)* — work the whole open frontier.
- `#N` — work only tickets whose Parent is #N (and their unblocked successors).
- free text — match tickets whose parent spec covers that goal; nothing
  matches → stop and say which upstream step (/grill-with-docs, /to-spec,
  /to-tickets) would create them.

## Invariants (the workflow essence — never break these)

1. **One fresh context per ticket.** Implementation happens in a spawned
   subagent that receives only the ticket (body + comments) and pointers to
   the repo's agent docs — never this session's conversation history. The
   orchestrator session stays thin: one line of state per ticket.
2. **Frontier discipline.** Eligible = open, labelled `ready-for-agent`, zero
   open blockers (`issue_dependencies_summary.blocked_by == 0`), no assignee,
   and not labelled `needs-info` / `ready-for-human`. Work them in dependency
   order. Blocking edges are read-only: never add, remove, or bypass one.
3. **Evidence before close.** Gates green (`uv run pytest`, `uv run mypy`,
   `uv run ruff check`), then a two-axis review by *separate* reviewer
   subagents — Standards axis, and Spec axis briefed to break it — with
   confirmed findings fixed and declined findings recorded. Close with an
   evidence comment. No self-approval inside the implementer's context.
4. **Thinking stays human-triggered.** Never author specs or tickets, never
   widen a ticket's scope, never close a parent/spec issue. A scope question
   discovered mid-ticket → comment it on the ticket, label `ready-for-human`,
   move on.
5. **The tracker is the memory.** All durable state lives in issues, commits,
   and checked-in artifacts, so stopping at any moment is safe and re-running
   /frontier resumes for free. If this session's context grows heavy
   mid-frontier, stop cleanly after the current ticket and say "re-run
   /frontier".

## Loop

1. **Frontier query** per `docs/agents/issue-tracker.md` (gh CLI). Empty?
   - Every relevant ticket closed → report goal met, stop.
   - Open tickets remain but all are blocked / assigned / human-labelled →
     report exactly what gates each one, stop. Never grind.
2. **Claim**: `gh issue edit <n> --add-assignee @me` — the first write.
3. **Implement** (fresh subagent, `model: opus`): give it the full ticket, tell
   it to read `AGENTS.md`, `CONTEXT.md`, and relevant `docs/adr/` first, then
   follow the repo's per-ticket protocol — TDD at the seam the spec agreed,
   gates green, commit in the project's style. Brief it to deliver the
   ticket's scope and nothing more, and to do the work itself rather than
   spawning subagents of its own. Do not tell it to verify or double-check its
   work — it already does, and asking buys over-verification, not safety. It
   reports a diff summary + test evidence. It does not push, does not close,
   does not review itself.
4. **Review** (two fresh reviewer subagents on the diff — different models by
   design, so their errors decorrelate): Standards axis (`model: sonnet`);
   Spec axis adversarial (`model: opus`, "your brief is to break it against
   the ticket and parent spec"). Brief both for coverage, not filtering:
   report every finding with confidence and severity, and let this loop rank
   them. A "only report what matters" brief is followed literally and
   depresses recall. Confirmed findings → fresh fix subagent (`model: sonnet`)
   with findings + ticket; re-run gates. Iterate at most twice.
5. **Close**: push, then `gh issue close <n>` with the evidence comment
   (test counts, review verdicts, declined findings + why).
6. **Re-query** the frontier — closes unblock successors — and continue.

## Model allocation

`model` on a spawned subagent takes `opus` | `sonnet` | `haiku` | `fable`
(Claude Opus 5 / Sonnet 5 / Haiku 4.5 / Fable 5). Omitting it inherits the
orchestrator session's model — which is an accident, not a decision. Set it
per role:

| Role | Model | Why |
|---|---|---|
| implement | `opus` | Multi-file, long-horizon agentic coding — where Opus 5's lead is largest. A cheaper model that needs a second pass costs more than the difference. |
| review, Standards axis | `sonnet` | Conformance against `AGENTS.md` + `docs/agents/` is comparison against a written reference, and it re-reads the whole diff — the token-heavy half of the gate. |
| review, Spec axis | `opus` | The load-bearing half: closing a ticket rests on this agent failing to break it. Wants high precision *and* recall on real defects. |
| fix | `sonnet` | Findings arrive already specified; convergent work. |
| orchestrator (this session) | `opus` | Thin in tokens, but it owns the money rails, the two-failure rule, and every stop decision. |

Deliberately unused here:

- **`fable`** (Claude Fable 5, 2× Opus 5) belongs to the thinking layer —
  /grill-with-docs and /to-spec on open questions — not to doing. An
  agent-ready ticket is already specified; the difficulty isn't in executing
  it. One exception: before labelling a twice-failed ticket `ready-for-human`,
  a single `fable` attempt is worth trying.
- **`haiku`** has no role on an evidence-gated path. Every step here is
  load-bearing, and the saving is smaller than one round of rework.

The model driving this workflow is unrelated to the agent × model cells a
sweep measures (`docs/agents/sweep-protocol.md`). Changing it does not touch
recorded results.

## Money and safety rails

- **Paid tickets** (live sweeps, API-spending runs): before the first one in
  a /frontier run, state the expected cost. Within the same order of magnitude as
  the last checked-in sweep → proceed; materially larger → pause and ask.
- A ticket that fails its gates or review twice → comment the findings, label
  `ready-for-human`, unassign, continue with the rest of the frontier.
- Permission denial, dirty working tree this loop didn't create, or any repo
  state that contradicts the ticket → stop and report. Never force, never
  reset, never delete to make progress.

## Reporting

- After each close: one line — ticket, what shipped, evidence link.
- At stop: a short table — closed / still blocked (by what) / needs human
  (and which upstream skill to invoke next). The last line always names the
  single next action the human should take.

## Continuous mode — pair with the native /goal command

The native /goal command (Claude Code v2.1.139+) is the continuation engine:
it holds a completion condition and keeps starting turns until a checker
model judges it met. This skill is the working method those turns follow.
Combine them:

```
/frontier #16
/goal every ticket under #16 is closed or labelled ready-for-human
```

The native goal keeps the session driving; this skill's invariants decide
what each turn does and where it must stop regardless of the goal (thinking
boundaries, money rails, two-failure rule — a stop-and-report satisfies the
goal loop honestly rather than grinding). Phrase the goal condition so that
"blocked, human needed" counts as done — never as something to push through.
Alternative for cross-session cadence: `/loop /frontier`. This skill never
schedules its own wake-ups.
