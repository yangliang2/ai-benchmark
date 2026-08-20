# ADR-0004: The mutation-gate verdict shape

Status: accepted
Date: 2026-08-20

## Context

`test-authoring` was the capability matrix's only registered zero — the one
heap-1 action with no tasks in any language. It resisted round 6 and round 7
for the same reason: the deliverable *is* tests, and held-out tests cannot
grade tests. An all-green suite may be thorough or may be `assert True`, and
passing is not effectiveness. Round 8 closes it by ruling a verdict shape for
that deliverable (design note §67).

## Decision

The verdict is the **mutation gate**: two gates over the test suite the agent
wrote at the test path the prompt names.

- **Gate 1**: the suite passes on the pristine starting repository, no
  exceptions.
- **Gate 2**: every hand-planted mutant is killed by at least one test.

`resolved` is both gates, binary and universally quantified over mutants —
not a kill rate.

Collection takes the prompt-named test subtree from the **workdir diff** and
nothing else; everything outside it is archived, not scored.

## Rationale

- **Binary, all-killed, rather than a kill-rate threshold** (§67.3). A
  threshold ("≥80% killed resolves") makes `resolved` quietly mean something
  else on one action — a hidden second quality metric on a corpus whose
  glossary already rules that values under different quality metrics never
  compare — and a continuous kill-rate score is the same move undisguised.
  The **findings key** already owns the stance that the verdict is binary and
  partial recall is not a score; this is that same quantifier pointed at
  mutants instead of findings. The universal quantifier also forces every
  planted mutant to be provably killable, where a threshold would let a
  doubtful one hide in the slack. Gate 1 admits no exception for the
  symmetric reason: one failing test on correct code is the false accusation
  the findings key's rejected half refuses.
- **Subtree-only collection** (§67.4). Applied whole, an agent's source edits
  could overwrite a mutation (killing gate 2's signal) or bend the code
  toward a wrong suite (killing gate 1's). The shape is the **answer file**'s
  precedent — the deliverable lands at a path the prompt names, and grading
  reads it there — widened from one file to one subtree; the disposition of
  everything else is the findings key's own "archived, not scored." The
  alternative, declaring source edits a violation, was rejected as a second
  adjudication surface (is a comment edit a violation? an added
  `__init__.py`?) that the collection rule dissolves entirely.

## Alternatives considered

- **A kill-rate threshold.** Rejected: turns `resolved` into a second,
  undisclosed quality metric and lets a doubtful mutant hide inside the
  slack instead of being provably killable (§67.3).
- **A continuous mutation score.** Rejected for the same reason as the
  threshold, undisguised: partial recall is not a score anywhere else in
  this corpus's grading, and this action does not get an exception (§67.3).
- **Operator-generated mutants** (mutmut and kin). Rejected: cheap per
  mutant, but the *equivalent mutant* — a change no behaviour distinguishes
  — makes a task permanently unresolvable for every agent under a universal
  quantifier. Mutants are hand-planted instead, and each is proved killable
  at lint time by the author's reference suite, checked per mutant (§67.5).
- **Source-edits-as-violation.** Rejected: a second adjudication surface the
  subtree-collection rule dissolves entirely — collection already decides
  what is scored without needing to police what an agent touched (§67.4).

## Consequences

- **What a `test-authoring` task now has to ship.** A prompt naming the test
  path as a complete behavioural specification, a starting repository whose
  module under test carries no existing tests, and a held-out mutant set —
  hand-planted, four to six per task, lint minimum three — each proved
  killable by the author's reference suite (§67.5, §67.7).
- **What the lint refuses.** A mutant patch touching the prompt-named test
  path (mutants touch source only, and the lint checks the disjointness); a
  mutant the reference suite does not kill; fewer than three mutants.
- **The gate is language-free.** The suite runs under whichever **language
  runner** the task declares; round 8 fills only the Python cell, and the
  TypeScript cell stays a disclosed zero — a mechanical fill for a later
  round once one round's record has proven the gate (§67.2).
- **Records carrying this verdict make the shape expensive to reverse**,
  which is why it is written down here rather than left to the grading
  code alone.
