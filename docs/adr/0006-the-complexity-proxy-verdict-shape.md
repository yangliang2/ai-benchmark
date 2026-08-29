# ADR-0006: The complexity-proxy verdict shape

Status: accepted
Date: 2026-08-29

## Context

`performance-optimisation` was the coverage table's last authorable `- - 0`
row — heap 4's one action, empty in every language, and parked round after
round for a reason none of the earlier zeros had. ADR-0004 closed heap 1 by
grading the tests an agent wrote against hand-planted mutants; ADR-0005 ruled
a shape for heap 3's prose. Heap 4 resisted both because the truth of an
"optimisation" is the hardest question this corpus had left: held-out tests
can say whether code is *correct*, and nothing in the grader could say whether
it is *faster* without measuring something. No verdict shape was registered
for the action anywhere — not in the loader, not in an ADR, not in the design
note. Round 13 (design note §117) rules one, and §117.2 rules that it is owed
an ADR beside the two above rather than being left to the grading code alone.

## Decision

The verdict is the **complexity proxy**: two held-out suites per task, and
`resolved` is both of them passing.

- **The behaviour suite.** Correctness unchanged. Named per task in the
  `grading` block's `behaviour_tests`, exactly as a `refactor` task names its
  own — this is the behaviour/structural split reaching a second category, and
  the first time it has moved since round 3.
- **The complexity suite.** Everything else in `grading/`: operation counts
  across held-out input sizes, ratio-bounded or ceiling-bounded, instrumented
  through **seams the task repository already owns** — a comparator that
  counts its calls, a stub ledger that counts its reads.
- **The verdict.** `resolved` is both suites passing: binary,
  execution-verified, computed rather than spoken, and replayable offline from
  the archived diff.
- **The prohibition.** **Wall-clock never enters the verdict path.** No
  elapsed-time reading is taken in a held-out suite, in a grading helper, or
  even as a disclosed non-gating reading printed beside the verdict.

## The two-sided proof, as standing invariants

The proxy is only worth anything if it is honest about the thing it stands in
for, and what says so is a proof that runs in both directions. It needs no new
machinery, because both directions are invariants the **task-set lint** already
runs — reached, for this action, by the extended split and by nothing else:

- **The reference solution passes both suites.** The author's optimised tree is
  graded like any other reference solution, and a proxy no correct optimisation
  can satisfy is refused before an agent ever meets it.
- **The pristine repository passes behaviour and fails complexity.** The
  behaviour side is `refactor`'s own behaviour-tests-pass-on-pristine rule
  reaching a second category: a task must start from behaviour that already
  works, or "preserved" has nothing to be measured against. The complexity side
  is the standing grading-must-not-pass-on-pristine rule doing for a slow start
  exactly what it has always done for a buggy one: a proxy the unoptimised code
  already satisfies is a task with nothing left for an agent to do, and the lint
  says so in the words it already had.

Those two invariants are this shape's whole gate, and neither is weakened,
special-cased or exempted to admit the new category — the extension is the
split, and the invariants are what the split then rides.

## The honest-proxy discipline

The counter counts a **fact of the algorithm**, reached through a seam the
repository owns — never a wall-clock, and never an implementation constant an
agent could satisfy without changing the algorithm's shape. A proxy that
counted, say, the number of times one named helper is called would grade
whether the agent wrote the author's solution rather than whether the work got
cheaper.

This is an **authoring discipline, not a machine check**, and it is recorded as
one: it is policed by spec review, where the three hot paths and their counters
are read before a ticket is cut, and by the two invariants above, which catch
the proxy that the pristine tree already satisfies and the proxy the reference
solution cannot. **No machine lint is claimed for it**, because none exists —
saying otherwise would be the kind of claim the invariants above are here to
make unnecessary.

## Rationale

- **The truth of an optimisation is ruled to be asserted growth behaviour, not
  measured time** (§117.1). That is the whole decision, and everything else
  follows from it: an assertion about operation counts is a fact about the code
  the agent wrote, it is the same kind of thing every earlier held-out suite
  asserted, and it replays to the same answer on any machine on any day.
- **Binary and execution-verified, like every verdict beside it.** `resolved`
  is both suites passing — no rate, no threshold, no score. This is ADR-0004's
  and ADR-0005's quantifier a third time: plant the ground truth, then ask a
  binary question of it.
- **The prohibition is registered as a prohibition rather than as a
  preference** (§118.3). A wall-clock reading nobody gates on is still a
  reading a later round would be tempted to gate on, and the replay-exactness
  every round since round 5 has kept is what the prohibition protects.
- **The prompt names the observable requirement and never the instrument's
  numbers** (§117.3). It names the hot operation and the scale the repository
  must handle in behavioural terms — which listing must stay fast as which
  ledger grows — and never the counter's input sizes, ratios or ceilings. A
  prompt silent on performance grades telepathy; a prompt naming the bound
  outright grades whether the agent can implement a named algorithm rather than
  whether it can find the optimisation.

## Alternatives considered

- **Measured wall-clock — thresholds over elapsed time.** Rejected, and it is
  the honest-to-the-action's-name candidate, so its price is worth stating
  plainly: measurement noise on shared hardware is a confounder no earlier
  round has priced, a threshold over a noisy quantity is a tuning knob, and a
  verdict that re-times on replay can flip — against the replay-exactness every
  round since round 5 has kept (§117.1).
- **Point-keyed explain-the-optimisation.** Rejected: reusing ADR-0005's
  instrument would grade the *explanation* and not the speedup, so heap 4's
  real question — can the gate catch a fake optimisation? — goes untested, and
  a fake optimisation with a good essay resolves. §115's addendum has a live
  false-red mechanism open on that instrument besides (§117.1).
- **The hybrid rider — this shape's verdict plus a non-gating point-keyed
  reading.** Rejected under the one-new-instrument-per-round discipline (§6):
  the rider buys paid existence proofs and grader calls for a reading that
  gates nothing. Recorded as declined rather than as impossible — it may queue
  for a later round.

## Consequences

- **What a `performance-optimisation` task now has to ship.** A prompt naming
  the hot operation and the scale in behavioural terms; a starting repository
  whose behaviour is already correct and whose hot path is not yet cheap; a
  `grading` block naming the behaviour half; a complexity half beside it
  counting through a seam the repository owns; and a reference solution that
  passes both.
- **The category carries no key, and no registry moves.** There is no accepted
  answer, no findings key, no mutant set and no points key, so `EXISTENCE_PROOFS`
  gains no entry and owes none — the lint's unregistered-proof check subtracts
  registered proofs from the *keyed* actions, and this action is in none of
  them. `_POINT_CATEGORIES` is untouched, no points key is admitted for the
  category, and no terrain exemption is granted (§117.6, §118.8).
- **The machinery is one move.** The behaviour/structural split, held to
  `refactor` by the loader's own two validators, admits a second category, and
  the run-time limit is registered at 600 — the flat default's own value, so
  registration and not tuning (§118.9). The runner, the readers, the point gate
  and the proofs writer do not move.
- **This round's verdict path spends no grader dollar** — the first since round
  9 of which that is true. Every verdict is two suites run against a collected
  diff: offline, replayable and free.
- **A cross-reference, and nothing more:** §117.4's disqualifier rule — a
  point-key disqualifier must name the wrong route in words surface-disjoint
  from the true mechanism's own — was ruled in the same round and lives at
  §117.4. It binds future point-keyed authoring; nothing in this ADR and
  nothing in this round authors a point key, so it does not reach this shape.
- **Records carrying this verdict make the shape expensive to reverse**, which
  is why it is written down here beside the mutation gate's and the point
  gate's rather than left to the loader alone.
