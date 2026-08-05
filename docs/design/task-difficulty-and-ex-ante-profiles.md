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
- Solution side: K9 crux depth (exactly one inventive decision, rest
  mechanical; zero-crux controls), K10 coordination width (N consistent
  edit sites).
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
