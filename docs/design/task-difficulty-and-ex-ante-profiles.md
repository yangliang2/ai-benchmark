# Task difficulty and ex-ante profiles — working notes

**Status: DRAFT — direction converged 2026-08-05, not yet an ADR, no tickets.**
The earlier "still not good enough" gap was identified as open question 5:
the user wanted one coherent object, framed as *how a top human architect
judges requirement complexity*. The 2026-08-05 session produced the architect
decomposition, a knob-based task-construction framework derived from it, and
a substrate strategy (see "Converged direction" below). The user's closing
stance: don't over-plan substrate selection — pick several base repos and
let experiments decide ("我们也不可能一次想明白的,多找一些基地仓库,多做
一点实验"). Formalization was explicitly deferred; next step is experiments,
not schema work.

## The question this must serve

The selection tool's core query: *for a ticket no agent has run yet, which
agent × model combination should be recommended, at what confidence and cost?*
Recommendations must be **ex-ante** — they can never wait for the task to be
executed. Everything below is instrumental to that decision.

## How the thinking evolved (kept so we don't re-litigate)

1. **Five a-priori difficulty axes** grounded in software-essence theory
   (Brooks essential/accidental, Parnas information hiding, change impact,
   testability): D1 decision content (graded assertions × stated/derivable/
   invented ladder), D2 locus (read-set vs write-set), D3 coordination
   (consistent edit sites), D4 preservation load (invariants near the edit),
   D5 verification distance (visible-test coverage of graded behaviour).
   Post-hoc they explain the first sweep: refactor = low-D1/high-D3 → LLM
   comfort zone → saturation (100%/100%); calc-infix = highest D1 → only
   both-model failure; jobrunner poor D5 → haiku's 21 turns.

2. **Measurement-theory objection (accepted):** "intrinsic task difficulty"
   has no empirical ordering — difficulty is a *relation* between task and
   solver, so the five axes are covariates/features, not measurements.
   Operational definition instead: **difficulty = lowest rung on a model
   ladder that reliably solves the task** (Mohs-hardness / chess-Elo / IRT
   logic). Today's 2-rung instrument already yields a real reading:
   19 haiku-solvable / 2 sonnet-only (docstore, jobrunner) / 1 unsolved
   (calc-infix). Ladder refines as models are added; IRT once the matrix
   is big enough; difficulty drifts with model generations (as-of date).

3. **Ex-ante constraint (user):** post-hoc ladder readings don't support
   recommendations for *new* tickets. Correction it forced: half the D-axes
   were computed from reference solutions, which user tasks don't have.
   Ex-ante features may only use (ticket text S, repo R).

4. **Resulting mechanism — actuarial loop:**
   - **Profile (ex-ante, 30 seconds, no run):** category (taxonomy v0,
     classifier exists) · scope estimate (single/cross-file) · spec
     completeness (acceptance-level / description-level / intent-level) ·
     test presence over the touched area (covered / partial / bare).
     Candidate 5th dim: seam quality (fan-in/out of touched modules) — not
     in v1, no predictive evidence yet.
   - **Calibration table:** every benchmark task carries the same profile
     (same measurement procedure) plus measured outcomes. Recommendation =
     cheapest combination in the matching cell above a reliability
     threshold (a business parameter); no qualifying cell → "don't
     delegate".
   - **Hierarchical backoff** for sparse cells: primary key category ×
     scope (14 cells, fillable today), spec/tests as refinement keys;
     backoff must be declared in the recommendation as reduced confidence.
   - **Feedback:** user runs flow back through the first-party pipeline and
     sharpen the table; recommendations never block on them.

5. **Strengthening calibration by back-derivation from actually-written
   code** (user's request). The run logs already store every agent diff,
   including failures. Three uses:
   - **Realized-vs-declared profile:** compute the realized profile from
     reference solutions + successful diffs; the estimator error measured
     on benchmark tasks *is* the confidence interval for user-task
     profiles.
   - **Failure forensics:** persist per-assertion junitxml results
     (currently discarded after the verdict); re-grade failed diffs →
     *near-miss score* (0.73 resolved with near-misses is a different
     business risk than 0.73 with garbage — changes the recommendation to
     "delegable with human review") and *failure concentration* (which
     decision types models jointly fail → difficulty localisation, informs
     task authoring).
   - **Struggle signal:** agent-diff churn relative to the reference
     solution + turns = how lost the agent was despite passing; predicts
     collapse on harder same-profile tasks → gives the table extrapolation
     warning power.

6. **Engineering-method pass** (how a top engineer would sequence this):
   - Reduce to the served decision (above); every component must name the
     recommendation it changes.
   - **Kill the most expensive assumption cheapest, first.** The whole
     design rests on "profile dims predict outcomes". Testable in ~a day
     with zero infrastructure: hand-annotate the 22 tasks' profiles,
     re-grade the 4 failing diffs for per-assertion results, produce a
     one-page analysis. **Kill criterion pre-registered:** dims with no
     signal are dropped; no signal at all → the profile approach is
     demoted and rethought. Only survivors get schema status (ADR +
     task.yaml + query grouping). Forensics persistence is built only if
     near-miss analysis provably changes a recommendation.
   - Seams: profile vocabulary + query semantics are the stable interface
     (CONTEXT.md/ADR); estimators and annotation methods are volatile and
     stay out of the record schema (labels fill gaps, never overwrite —
     existing principle). `analyze` reads only run logs + task artifacts
     (provenance boundary unchanged).
   - Explicit non-goals for v1: backoff engine (an `if`, not a system),
     seam-quality dim, LLM annotation pipeline (22 tasks: hand-label).
   - Exit criteria (code): every acceptance criterion traced to a test at
     the stable seam, both directions (behaviour + loud failure); every
     number recomputable from checked-in artifacts by one command;
     docs claim nothing the code doesn't deliver (the #10 lesson,
     institutionalised); prediction protocols pre-registered before
     sweeps; two-axis review where the Spec reviewer's brief is to break
     it (adversarial verification, the project's actual quality source).

## Business mapping (agreed direction, phrasing not final)

The five lead-questions a tech lead implicitly asks when assigning a ticket
map 1:1 onto the profile dims (spec written? how much context? blast radius?
regression risk? self-verifiable?). Outward projection: **delegation levels**
L1 execute-as-written / L2 independent-within-module / L3 cross-module /
L4 design-judgment — with explicit projection rules; the vector stays ground
truth, levels are a documented lossy view. Model ladder = delegation ladder
directly (haiku-solvable ⇒ delegable to the cheapest tier). Human-time
buckets (SWE-bench-Verified style) as an independent ROI anchor. Current v1
set concentrates in L1–L2, which both explains refactor saturation and
defines the roadmap statement ("we measure L1–L2 well; L3–L4 is the gap").

## First sweep facts the design must stay consistent with

44 runs, $5.25 (+$0.84 resume), pass@1, n=1 per cell, duplicate runs
schema-forbidden. sonnet feature-dev 91% / haiku 73%; refactor 100%/100%
(saturated — separation only in cost ~2.6–2.9× and turns 6.5–9.8). Misses:
calc-infix (both), docstore + jobrunner (haiku only). Replay reproduces all
records byte-for-byte. Repeat-sampling would need a run-index schema decision
(pass@k vs mean) — parked.

## Converged direction (2026-08-05 session)

### 7. The gap was open question 5 — architect-mediated judgment

The user confirmed the missing piece: model the process by which a top
human architect judges requirement complexity. Key insight: the architect's
judgment is *mediated by a cheap mental solution sketch* — complexity is a
property of the imagined solution path, not of the requirement text. The
earlier 4-dim profile skipped this mediating object, which is why the design
read as a bag of mechanisms. A sketch-centred chain (π = Sketch(S,R) →
features φ(π) → P(resolve | φ, combo) → recommend → feedback comparing
sketch to realized diff) was proposed and resonated, but **formalization is
deferred by explicit user instruction** — decompose and experiment first.

### 8. Architect decomposition (the source of truth for difficulty factors)

Steps, iterative not linear: (0) frame the problem — real intent vs stated
ask, reversibility/stakes decide recon depth, self-check familiarity;
(1) interrogate the spec — decisions closed vs left open, implicit
requirements, boundary cases, decidable acceptance, spec stability,
contradiction detection; (2) reconnoiter the terrain — touch-set (read-set
vs write-set), with/against the architectural grain, haunted areas,
invariant density, safety-net quality, code archaeology; (3) sketch the
solution and locate the crux — classify its uncertainty (known-hard /
known-unknown → spike / unknown-unknown → outside view), classify each step
mechanical/derivable/inventive, identify external dependencies (often the
dominant schedule-variance source, orthogonal to technical difficulty);
(4) outside view — nearest-neighbour past cases, base-rate correction,
asking the person who knows; (5) pre-mortem — four failure modes (can't
build / breaks something else / builds the wrong thing / can't verify),
detection distance per mode, stop-loss checkpoints; (6) match the executor —
difficulty is relational (crux type × executor profile); **active
difficulty reduction**: architects rewrite the task (pre-decide the crux,
add scaffolding) to downgrade it to a delegable level; (7) output — a
distribution not a point, explicit assumption list, staged commitment
(spike before full estimate), calibration record. Scenario table: bug-fix
crux = localization; refactor crux = behaviour-preservation verification;
perf crux = measurement; migration crux = data/rollback; vague ask crux =
negotiation into a decidable spec; dependency-heavy crux = coordination.

### 9. Knob framework: task construction = experimental design

Each architect factor becomes an independently settable knob; a task's
metadata records which knob at which level it activates, plus the author's
**pre-registered difficulty prediction** (expected ladder rung + which knob
justifies it). Sweep results then confirm/kill knobs — task authoring and
difficulty-theory validation become the same activity. Knobs:

- Spec side: K1 decision openness (acceptance/description/intent spec
  ladder), K2 implicit requirements (constraints live in repo conventions,
  not the ticket — the recorded "convention-driven difficulty" lever),
  K3 contradiction traps (correct behaviour = flag, not implement).
- Terrain side: K4 read-set/write-set ratio, K5 with/against grain,
  K6 haunted areas (load-bearing weird code, Chesterton's fence),
  K7 invariant density, K8 safety-net quality (covered / partial / bare /
  **misleading** — green tests that don't cover the graded behaviour).
- Solution side: K9 crux depth (none / **single** — exactly one inventive
  decision, rest mechanical, against the zero-crux control it is paired
  with), K10 coordination width (N consistent edit sites).
- Verification side: K11 detection distance (how late failure manifests).

Post-hoc mapping: calc-infix = natural high-K9; jobrunner's 21 haiku turns
= K11; refactor saturation = K7/K8 set too kind (natural refactor crux is
behaviour-preservation verification; current tasks give too good a net).

**Task families** — the highest-value construction trick: one underlying
change + one reference solution, N spec variants (L1 crux-pre-decided /
L2 hints / L3 intent-only). Clean K1 isolation, amortized authoring cost,
and directly tests the product hypothesis that rewriting a ticket downgrades
the required tier ("how to make this ticket delegable" as a product
feature). Same family pattern applies to K8 (net good/broken/misleading)
and K11 — in principle only, as of #19: the shipped family lint holds `repo/`
byte-identical across members and a K8 or K11 lever lives inside `repo/`, so
those families are not authorable today. Round-1 K8 is therefore standalone
tasks, and defining the lint per knob rather than per family is a recorded
round-2 decision (see the #16 close comment).

**K1/K2 overlap, recorded before any sweep so the caveat cannot be invented
afterwards:** the ladder's L3 (intent-only) does not delete the withheld
decisions, it relocates them — an intent-level prompt makes the agent recover
from repo conventions what L1 stated outright, which is exactly K2's lever.
So an L1→L3 rung difference is attributable to "spec completeness including
its K2 shadow", not to K1 alone, and a K1 family is not a clean K1 instrument
however carefully everything else is held constant. The clean K2 instrument is
a pure-K2 task: constraints living in conventions while the spec stays at
acceptance level, where K1 is pinned at L1 and only K2 moves.

Guards: difficulty must come from a named knob traceable to a real
architect experience (no puzzle difficulty, no obfuscation); one knob at a
time (baseline + single-knob deviations + a few realistic composites, no
full factorial); honest-variant probes as in #12/#13; knobs face the same
kill discipline as profile dims — no separation after two sweeps → demoted.
Ladder coverage is a design goal: anchors at every rung incl. headroom
(expected all-fail) tasks; the existing 22 tasks serve as baseline controls.

### 10. Substrate spectrum — construction method is one, substrate varies

```
fully authored  ←—  modified OSS (mainline)  —→  as-is OSS (optional)
(substrate=artifact)  (substrate=raw material)     (substrate=found site)
```

Route B is NOT history replay (that lane already exists via meta-aggregation
and is contaminated); the repo is somebody else's, the requirement is ours,
and — the user's sharpening — **the substrate is editable**: surgically set
terrain knobs on a real repo (delete/degrade tests for K8, inject a
convention for K2, plant a load-bearing oddity along real grain for K6).
Control and organic mass at the same time; prospecting risk (finding
perfect natural sites) largely dissolves. Residual concerns, recorded not
blocking: familiarity imbalance across models (pick cold repos, record
provenance), heavy-handed edits killing the organic quality (edits sparse,
along the grain, each traceable to a knob), one-time engineering cost for
env pinning (vendor at pinned SHA into the existing task format — repo/
tree + held-out grading/ — dependencies pinned, network stripped).

Sequencing agreed loose (user: don't over-plan): first knob-family batch
(K1 families, K8-misleading, K9) can start on existing authored repos with
zero new engineering; in parallel, vendor several cold small OSS substrates
(few kloc, Python, thin deps) and set K7/K8 knobs there — plural substrates
by design, selection mistakes are cheap. As-is OSS prospecting deferred
until modified-substrate results show whether planted knobs differ
systematically from natural sites. Bonus: agreement between authored and
OSS substrates on knob → difficulty ordering is itself the external-validity
check open question 3 asked for.

## Round 1 verdicts — 2026-08-06

Round 1 (#16) is built and swept: 27 constructed tasks, two sweeps
(Track A #24, Track B #25), 54 new cells, $7.46 total. Everything below is
recomputable by `uv run ai-bench reconcile-v1` over checked-in artifacts,
except the effort contrasts, which are computed from the same run logs'
`turns`/`cost_usd`/`tokens_in` fields and are quoted here because the
report does not yet group by them. Nothing above is superseded; section 9's
knob list stands, with the verdicts below attached to it.

### 11. What the round measured

Hit-rate 10/27 (37.0%). Of the 17 misses, **14 are over-predictions** (the
task was easier than registered) and 3 under. Rungs: 22 of the 27
constructed cells landed at haiku-solvable, 2 at sonnet-only, 3 unsolved.
The rung ladder, in other words, saturated again — the same failure the
first sweep had, now reproduced on deliberately-knobbed tasks.

The one axis that did not saturate is effort. Per-knob-level contrasts
against the zero-knob baseline of the same category, all cells n=1:

```
category     level           model    turns(mean/med)   cost(mean)   tokens_in(mean)
feature-dev  K1 acceptance   haiku      6.5 / 7          $0.0657        177k
             K1 description  haiku      6.0 / 6          $0.0602        161k
             K1 intent       haiku      8.0 / 7.5        $0.0672        215k
             K1 acceptance   sonnet     4.25/ 4          $0.1682        149k
             K1 description  sonnet     5.0 / 4          $0.1767        176k
             K1 intent       sonnet     5.5 / 4.5        $0.1884        193k
             K7 dense        haiku     36.0 /36          $0.3620       2026k
             K7 dense        sonnet    13.0 /13          $0.4024        557k
             K9 none         haiku      3.33/ 3          $0.0359         84k
             K9 single       haiku      6.0 / 4          $0.0545        159k
             K9 none         sonnet     4.67/ 5          $0.1301        157k
             K9 single       sonnet     6.33/ 6          $0.1844        219k
             (baseline)      haiku      9.82/10          $0.0711        235k
             (baseline)      sonnet     6.45/ 5          $0.1846        209k
refactor     K8 misleading   haiku      6.57/ 4          $0.0637        198k
             K8 misleading   sonnet     7.29/ 7          $0.1949        263k
             (baseline)      haiku      9.09/ 9          $0.0572        214k
             (baseline)      sonnet     7.55/ 7          $0.1643        234k
```

### 12. Per-knob verdicts

**K1 (decision openness) — SURVIVES, the round's only validated rung
lever.** It is the sole knob that separated on the graded outcome:
acceptance {haiku-solvable ×4} vs description and intent each spanning all
three rungs. It is corroborated on the effort axis independently — sonnet's
turns (4.25 → 5.00 → 5.50), cost ($0.168 → $0.177 → $0.188) and input
tokens (149k → 176k → 193k) are all **monotone across the three levels**,
a version-matched within-round contrast that owes nothing to the frozen
baseline. K1 also carries the round's best prediction record (7/12 hits vs
3/15 outside it). Promote to candidate ex-ante profile dimension.

**K7 (invariant density) — SURVIVES on effort, INERT on rung; the report's
"separated" flag is not the reason.** Both dense cells resolved on both
models, so the knob moved no rung. What it did move is effort, by more than
anything else in the round: haiku spent 36 turns and $0.362 mean against a
feature-dev baseline of 9.8 turns / $0.0711 — **3.7× the turns, 5.1× the
cost, 8.6× the input tokens**, and both individual cells exceeded the worst
baseline haiku cell ($0.126, jobrunner) by 1.9× and 3.8×. Sonnet: 2.0×
turns, 2.2× cost. Caveat recorded rather than resolved: the K7 cells are
the only ones on large vendored substrates, so the effort signal conflates
invariant density with plain repo size (a K2/scale confound), and n=2. Keep
K7, re-run it with a size-matched control.

**K8 (safety-net quality, misleading) — DEMOTED.** Two sweeps, silent in
both, and the effort data says it is worse than inert. 7/7 misleading-net
refactor tasks landed haiku-solvable against an 11/11 haiku-solvable
refactor baseline — no rung movement available in either direction, since
refactor was already saturated. On effort the Track-A K8 tasks, which share
their substrate kind with the baseline, came out **easier**: haiku 5.75
turns mean / 3.5 median and $0.0447 against a baseline 9.09 / 9.0 and
$0.0572 — 37% fewer turns and 22% cheaper. Sonnet the same direction (6.25
turns / $0.157 vs 7.55 / $0.164). The mechanism is legible: a misleading net
is constructed by *deleting* tests, and deleting tests shrinks the visible
suite the agent reads, so the lever that was meant to withhold a warning
also withholds a read-set. All 7 predictions missed, all in the
over-direction. K8-misleading, as instrumented, is a difficulty *reducer*.

**K9 (crux depth) — SILENT ROUND 1 of 2, NOT demoted; real on effort.** No
rung separation: all three crux tasks and all three zero-crux controls
resolved on both models. But the paired design does show something the
grouped rung comparison cannot: **5 of the 6 matched crux-vs-control cells
cost more with the crux planted**. haiku 3.33 → 6.0 turns mean (1.80×) and
$0.0359 → $0.0545 (1.52×); sonnet 4.67 → 6.33 turns (1.36×) and $0.130 →
$0.184 (1.42×). Per pair: playlist +7 haiku turns / 2.34× cost, settleup +3
sonnet turns / 1.79× cost, cartons flat on turns and within ±3% on cost for
both models — the one pair whose planted crux left no trace. K9 has been swept
once. It gets one more round, with effort registered as an outcome.

### 13. Kill-discipline ruling

The registered rule (section 9) reads "**no separation after two sweeps →
demoted**". `reconcile-v1` operationalises a sweep as one distinct `as_of`
date, and both round-1 sweeps carry `2026-08-05`, so the report shows K8 and
K9 at silent-1 and warns in its own criterion text to read the dates before
reading a demotion off them. [Resolved by #28: rounds now key on sweep ids,
with the as-of date only as the fallback for logs written before the field
existed — including these round-1 logs, which is why the ruling below still
stands as the record of how it was decided.] The ruling here goes to the registered text,
not to its current implementation, and it does **not** land the same way on
both knobs, because the two knobs did not get the same number of sweeps:

- **K8 was swept twice.** 4 tasks in Track A (hand-authored repos, CLI
  2.1.222) and 3 in Track B (vendored pysm and RBQL, CLI 2.1.223) —
  separate runner invocations, separate log files, separate substrate
  kinds, the second run after the first was read. That is two sweeps by
  every reading of the rule except the date column. **K8 is demoted now.**
  The date collapse is a dating artifact, and waiting for a third sweep to
  fix a filename would be letting the instrument's calendar overrule its
  evidence — particularly when the effort data has K8 moving difficulty the
  wrong way, so a further sweep is not being asked to break a tie.
- **K9 was swept once.** Every K9 task is Track A; Track B has none. K9 has
  one silent sweep, not two, and is not eligible for demotion under the
  rule as written. **K9 stays, flagged, with one sweep remaining.**

Consequence, stated so it cannot be re-litigated later: K8-misleading is out
of the candidate profile dimensions and round 2 must not spend its
anti-saturation budget there. If K9 is silent again on rungs in round 2 it
is demoted as a rung lever regardless of its effort signal — the effort
result is grounds for changing *what is measured*, not for extending the
knob's life under the old measure. Implementation follow-up (recorded, not
a ticket): `reconcile-v1`'s round counter should key on the sweep, not on
`as_of`, or the same collapse recurs whenever two sweeps share a day.
[Resolved by #28: the live runner stamps a caller-named sweep id on every row
and the round counter keys on it, falling back to the as-of date only for
legacy logs that carry none.]

### 14. What each miss teaches

Sorting the 17 misses by what actually went wrong, rather than by knob:

- **Model stronger than the bet — 9 misses** (alerts-rule-table,
  leaderboard, sessions-extract-expiry, stockroom, pysm-extract,
  pysm-revert, rbql-quote; plus billing-l3 and inventory-l2). The planted
  trap was correctly described and simply did not fire. All seven K8 tasks
  are here: the boundary negation, the `dict()` shallow copy, the merged
  quoter, the rank-key tie-break — each was the obvious wrong move, each was
  not taken, and in no case did the green-but-misleading suite persuade a
  model that a wrong answer was done. Three rationales pre-emptively raised
  recognition (pysm and RBQL are public MIT code); rbql-quote's rationale
  argued specifically that the graded contract could *not* be recognised,
  and it resolved anyway, so recognition does not explain the K8 result.
- **Right lever, wrong axis — 4 misses** (playlist-space-out,
  settleup-settle, pysm-remember, rbql-like). The knob did make the task
  harder; "harder" showed up as turns and dollars and not as a rung. These
  four are the strongest argument for the round-2 change in section 16.
- **Mechanism absent — 1 miss** (cartons-pack). The planted "inventive
  decision" was not one: it is the only K9 pair with zero effort delta on
  both models, so the task and its zero-crux control are, empirically, the
  same task.
- **Bet inverted — 3 misses**, all K1, and all three under-predictions.
  These are the round's most informative cells, because in each the
  registered rationale named a trap and a *different* trap fired.
  - `settings-merge-layers-l2` (predicted haiku-solvable, observed
    unsolved) registered "the one decision left out — copy-on-write — is
    the convention the module docstring and `set_value` already announce".
    Both models paraphrased that invariant into their own docstrings and
    then violated it: `dict(base)` plus direct assignment aliases the
    input's subtrees, and the held-out mutate-then-recheck assertions catch
    it. **Announcing an invariant in a docstring buys a correct-sounding
    docstring, not a correct implementation.**
  - `duration-parse-written-l3` (sonnet-only → unsolved) predicted the whole
    refusal surface would collapse. Both models refused four of six
    malformed inputs and lost exactly one clause — order-and-uniqueness,
    the clause the *l2* prompt states in a single sentence and l3 does not.
    A rationale that estimates the breadth of a collapse mis-estimates the
    rung, because a rung is decided by the union of held-out assertions and
    one narrow hole sinks the cell.
  - `inventory-consume-lots-l3` (sonnet-only → unsolved) predicted
    under-refusal from having to read the rules off the module. Both models
    **over**-refused, transplanting the neighbouring `receive` function's
    `if quantity <= 0: raise` near-verbatim (error message included) onto a
    `consume` whose contract requires `consume(lots, 0)` to be a no-op.
    Sonnet's cell fails on that one character. "Read the invariant off the
    repo" is not a safe fallback — it generates confident wrong answers as
    readily as right ones, and that mechanism has no knob in section 9.

**The K1 non-monotonicity is mechanistic, not noise.** `settings-l2` (more
complete prompt) failed both models while `settings-l3` (less complete) was
solved by sonnet, and the reason is visible in the diffs: l3 says nothing
about the merge, so sonnet composed the answer out of the repo's own
`flatten`/`set_value`, which already copy every section along the path; l2
describes a two-dict recursive merge clause-for-clause, the model
transcribed that shape, and the canonical Python idiom for that shape is
aliasing-unsafe by construction. l1 states copy-on-write as an acceptance
criterion and both models wrote an explicit deep copy and passed. So the
ordering that predicts the outcome is not "how much prose" but **stated as
a criterion > reuse a primitive that already enforces it > implied by prose
> unmentioned** — and "implied by prose" sits *below* "unmentioned",
because prose displaces the module as the source of truth and steers the
implementation shape. Every one of the six K1 failures is invisible to a
happy-path value-equality check, which is exactly what the agents' own
self-verification ran (sonnet's settings-l2 message: "All checks pass",
from a repo suite that never imports `merged`).

### 15. Anomalies, read

1. **Rounds collapsed into one as-of date.** Both sweeps carry
   `2026-08-05`, so `reconcile-v1` reports "2 rounds" only because the
   2026-08-04 baseline sweep supplies the second date, and the kill counter
   reads round-1 as a single round. The evidence is unaffected — two
   sequential runner invocations, two log sets, the second launched after
   the first was read — and section 13 rules on the sweeps, not the dates.
2. **Agent-version drift, wider than reported.** #25 flagged one Track-B
   haiku cell (`rbql-like-escape-wildcards`, also the round's most extreme
   row at 46 turns and $0.48) running on CLI 2.1.222 while its nine
   siblings ran 2.1.223. The full stratification is larger and matters
   more: **all 44 baseline cells ran 2.1.221, 45 cells ran 2.1.222, 9 ran
   2.1.223**. Every knob-vs-baseline comparison in this round therefore
   crosses at least one CLI version boundary, and the frozen baseline is
   the weakest comparator available. The contrasts that survive this are the
   version-matched within-round ones: K1's three levels against each other,
   and K9's three matched pairs. Round 2 should pin the CLI version for a
   sweep and prefer paired designs over baseline deltas.
3. **K7 flagged "separated", in the easier direction.** The report's
   criterion compares *sets* of observed rungs, and K7's 2 cells
   ({haiku-solvable}) cannot reproduce the 11-cell baseline's 3-element set
   whatever they do. The flag is an artifact of set comparison at n=2, not
   evidence of a difficulty effect; K7's real result is the effort contrast
   in section 12. The criterion needs a minimum-n guard, or set comparison
   needs replacing by something that degrades gracefully at n=1 per cell.
   [Resolved by #29: the guard is the comparison's own arithmetic rather than
   a constant — a side of n graded cells lands on at most n distinct rungs, so
   a side with fewer cells than the other has rungs is reported not assessable
   with the counts named. K7's flag now reads "not assessable"; nothing else in
   the report moved, because sides landing on the same set always pass the
   guard, so it can only ever withdraw a claim of separation.]
4. **Two graded cells live in files named `-dry`.**
   `2026-08-05-dry.jsonl` and `2026-08-05-trackb-dry.jsonl` each hold one
   real, graded, paid row (`settings-merge-layers-l1` haiku,
   `rbql-like-escape-wildcards` haiku). Reconciliation reads them correctly;
   any hand-rolled analysis that filters on the filename will silently drop
   two cells, as a first pass of this analysis did.
5. **A rare flake on the RBQL substrate, cause not pinned.** Found while
   running this ticket's gates:
   `test_the_reference_solution_keeps_the_repository_green` on
   `rbql-like-escape-wildcards` failed once in a full-suite run (483 passed,
   1 failed), and the full suite came back 484 green on an immediate rerun.
   Chased rather than waved through, with the evidence recorded because it
   is short of a diagnosis: it reproduced once more in 194 iterations of the
   test node — and in that same iteration the *pristine* counterpart,
   `test_the_repository_starts_out_green`, passed — but 250 direct
   executions of the pristine visible suite and 250 of the solved one, run
   outside pytest in the same temp-dir way the helper does it, produced zero
   failures. So the rate is on the order of 0.5% or lower and the mechanism
   is not established. The leading candidate is upstream nondeterminism: the
   vendored `repo/test_csv_utils.py` builds its tables, delimiters,
   encodings and line separators with **unseeded `random`**, which would
   make "the repository's own tests pass" a probabilistic assertion on this
   substrate — for our lint gates and for the agent alike. That candidate is
   not confirmed, since the 500 direct runs failed to reproduce it. Two
   things follow either way, and both are round-2 work: a K8 verdict resting
   on "the visible suite stays green" is only as firm as that suite's
   determinism, and seeding the vendored generators would cost nothing and
   remove the question. Worth checking against the observation that this
   same cell is the round's most extreme at 46 turns and $0.48 — suggestive,
   not evidence. [Addressed by #29: the harness now seeds `random` in the
   throwaway copy it runs a visible suite in — a conftest injected after the
   edit, never in a checked-in tree, since replay of a logged run applies its
   diff to those exact bytes. The node reran 1000 times without a failure; at
   the 0.5% rate observed above a clean thousand happens 0.7% of the time, so
   the rate is not merely unobserved but bounded. The upstream mechanism is
   still not *proven*, because the seeding removes the question rather than
   answering it; what is proven is that the gate no longer depends on the
   answer.]

### 16. What round 2 should change (candidates, not tickets)

1. **Make effort a registered, reconciled outcome alongside the rung.** The
   rung ladder saturated in both sweeps — 22 of 27 constructed cells at the
   lowest rung — while turns and cost separated cleanly wherever a knob was
   real (K7 3.7×, K9 1.5× on matched pairs, K1 monotone on sonnet). This
   generalises the first sweep's refactor lesson, which is now the second
   independent time cost/turns saw a difference that `resolved` could not.
   Predictions should register an expected effort band, `reconcile-v1`
   should group by turns and cost, and the kill criterion should read
   separation on either axis. This is the highest-value single change and
   the one that would have made round 1 read as four results instead of one.
2. **Replace K8-misleading as the anti-saturation lever, with K11
   (detection distance).** K8 is demoted and its budget is free. The round's
   own failure analysis names the replacement: every K1 defect that fired —
   aliasing, an inverted tie-break, a refusal boundary, a dropped return
   value — is invisible to the happy-path check the agent runs on itself,
   and "how late does failure manifest" is K11's lever, not K8's. Secondary
   candidates: K7 at scale, since it is the only knob that moved effort by
   multiples; K10 coordination width, untouched so far.
3. **Split K1 by *how* a decision is conveyed, not by how much prose.** The
   K1 ladder is validated but its levels are the wrong variable. Round 2's
   K1 should vary along the ordering section 14 recovered — criterion stated
   / repo primitive available / implied by prose / unmentioned — with
   "implied by prose" registered as *harder* than "unmentioned", which is
   the round's most interesting and most falsifiable single claim.

Also recorded, unranked: **a new knob candidate, "misleading neighbour"** —
the guard-transplant mechanism from `inventory-l3`, where a model copies an
adjacent function's precondition verbatim onto a contract that needs the
opposite; it is adjacent to K2 but is not conventions-as-implicit-
requirements, it is conventions-as-trap. Harder K1-intent tasks and
cross-file scale are worth trying but rank below the three above, since
the round's evidence is that the models are not rung-limited on this
material at all. On the prediction instrument itself: hand-registered rungs
hit 37% with a strong directional bias, and outside K1 the record is 3/15
where **all three hits are the zero-crux controls the authors expected to be
easy** — i.e. every prediction of the form "this knob makes this task
harder" missed, 0/12. Read as an instrument, the rationales are good
mechanism descriptions (the diffs confirm the traps were real and correctly
located) attached to bad difficulty estimates, and the systematic direction
says the gap is calibration, not understanding: 2026 authors reasoning about
what an agent will find hard consistently over-estimate, because they price
the trap and not the model's willingness to read past it. Formalization
(the sketch → φ → P(resolve) chain) stays deferred; the round did not
produce a stable enough outcome variable to fit against, and item 1 above is
the prerequisite.

## Open questions (superseded list resolved 2026-08-05)

Of the five candidate gaps: #5 confirmed as the real gap (architect
framing, above); #1 and #2 dissolve inside the sketch-centred chain
(feature granularity follows the sketch; P(resolve|φ,combo) is the
backbone) — *when* formalization resumes; #3 partially addressed by
cross-substrate agreement; #4 moot (falsification-first survives, now
testing the knob framework). Remaining genuinely open:

1. Sketcher instrument (which model/prompt, versioned like the classifier)
   — deferred with formalization.
2. Multi-turn negotiation tasks (vague-ask scenario, oracle answering
   questions) — has a place in the knob framework, far future.
3. Prospecting efficiency on as-is OSS — only matters if modified
   substrates prove insufficient.
4. Repeat-sampling / run-index schema (pass@k vs mean) — still parked.

## Related repo state (for whoever picks this up)

#9 train (#10–#14) complete; #9 parent still open, stale `ready-for-human`
label. #15 (grading process isolation) open, unscheduled. Post-merge cleanup
candidates recorded in auto-memory. The 22 tasks, reference solutions,
run logs, and per-task grading machinery are all in place — the raw material
for step 0 exists in the repo today.
