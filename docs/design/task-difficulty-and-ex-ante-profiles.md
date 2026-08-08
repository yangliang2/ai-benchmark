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
  K3 contradiction traps (correct behaviour = flag, not implement),
  K12 decision conveyance (criterion / repo-primitive / unmentioned /
  **prose** — how the one withheld decision reaches the solver; the ladder's
  order *is* the registered claim, prose hardest and sitting below
  unmentioned).
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

**K12, derived from round 1's failing diffs (section 14) and registered here
before any code or task names it.** The K1 sweep's non-monotonicity was
mechanistic, not noise: `settings-l1` stated copy-on-write as an acceptance
criterion and both models wrote an explicit deep copy; `settings-l3` said
nothing about the merge and sonnet composed the answer out of the module's
own copying primitives; `settings-l2` described the merge clause-for-clause
and both models transcribed that shape, whose canonical Python spelling
aliases by construction. So what orders the outcomes is not how much prose a
prompt carries but how the withheld decision *reaches* the solver, and the
order is criterion → repo-primitive → unmentioned → **prose**: prose
displaces the module as the source of truth and steers the implementation
shape, which is worse than saying nothing and leaving the module to be read.
That order is the whole claim, pre-registered and falsifiable exactly as
written — prose variants coming back easier than unmentioned ones kills it in
public, which is the point of registering it here first. (Section 14's inline
list transposes its last two terms; the sentence immediately after it, which
puts "implied by prose" *below* "unmentioned", is the reading registered.)

**How K1 is read across a K12 family.** K12 scopes one decision out of K1:
where both are declared, K1 is the level the spec's *other* decisions are
written at and K12 is the conveyance of the crux alone. A K12 family
therefore writes every non-crux decision identically in every variant — the
members share one acceptance-criteria block verbatim — and varies only the
passage the crux travels in, so K1 is honestly constant while K12 moves.
Where K12 is not declared, K1 goes on covering the whole spec, which is what
the round-1 K1 families measured. Unlike K8's and K11's, a K12 family is
authorable under the shipped lint today: its lever is the prompt, and the
prompt is the one thing the lint asks a family to *vary*.

**What K12 does not claim.** Difficulty and price come apart here, and round
1 says which way round: `settings-l2`, the prose variant, cost haiku 5 turns
against `l1`'s 7 and `l3`'s 9 — and failed both models, where `l3` was
solved. Prose was the cheap answer and the wrong one; saying nothing cost
more and got solved. A K12 task therefore registers the
ladder claim on its rung, and registers an **effort claim only where the
level's mechanism is reading burden**, which peaks at unmentioned rather than
at prose. A turns ladder running monotonically along K12 would be a bet the
round-1 run log already argues against. [Round 2 registered exactly this and
it is the part that was falsified: all 8 K12 effort readings missed, and they
missed in the *ladder's* direction — prose is the costlier variant in 6 of 8
readings and flat in the other 2, none leaning the reading-burden way. The
paragraph is left as registered because it is the record of the bet; the
result is §18, and round 3 registers K12's effort claims along the ladder
instead (§23.6).] Such a claim is read against the pair
partner rather than a category baseline, which is what the two pairs a K12
family declares are for — criterion against repo-primitive, and prose against
unmentioned, the second being the contrast the whole ladder turns on. Neither
pair plants anything: reconciliation's section 4 prints them under its
existing `crux`/`control` columns, which for a pair varying an enumerated
ladder name the higher rung and the lower rather than a planted decision and
its absence, so `unmentioned` printing as `prose`'s "control" is that column
read as the ladder, not a claim that the crux was built into one side.

Guards: difficulty must come from a named knob traceable to a real
architect experience (no puzzle difficulty, no obfuscation); one knob at a
time (baseline + single-knob deviations + a few realistic composites, no
full factorial); honest-variant probes as in #12/#13; knobs face the same
kill discipline as profile dims — no separation after two sweeps → demoted.
[Amended for round 3 by #37, immediately below. The sentence stays as it was
registered, because what changed is *what a separation is* and not the two
sweeps it takes; the amendment is written out rather than edited in, so the
rule the first two rounds were scored under stays legible.]
Ladder coverage is a design goal: anchors at every rung incl. headroom
(expected all-fail) tasks; the existing 22 tasks serve as baseline controls.

**Kill discipline, amended — round 3, #37.** Two rounds say the rule above
counts the wrong thing. It counts any comparison the report can draw, in
either direction, and round 2 fired its separation flag three times with only
one of the three informative (§19): K9's was read level against level inside a
registered contrast and is real; K1's fired off a level K12's families hold
*constant* by design, so it flagged a knob round 2 never varied (§22.1); and
K11's fired because its level came out uniformly *easier* than the baseline it
was read against, crediting an anti-saturation knob for pushing a task down
(§22.2). K7 meanwhile cannot be assessed at all, because its only comparison
is against a baseline it can never match on sample size (§18) — and the axis
that *has* separated in every round, effort, advances no counter whatever it
says, so a knob that reliably makes work expensive faces demotion for staying
quiet on an axis nobody registered it against (§§20, 22.3, 23.8). The amended
rule, which `reconcile-v1` mirrors verbatim:

1. **Contrast-only counting.** A round advances a knob's counter only where
   that round put the knob to a **registered contrast** — a comparison the
   *task set* declares, not one the report constructs. Two things are
   registered contrasts and nothing else is: a **family or pair** swept in
   that round whose **varied knob** this is, and an **effort claim**
   registered on a task activating it *and scored to it by clause 3*, read
   against the comparator that claim named. The qualification is not a detail:
   clause 3 scores a pair claim to the pair's varied knob alone, so a task
   activating K1 and K12 inside a K12 pair registers nothing about K1, and a
   reader mirroring this clause without it would give K1 a counted round off a
   bet nobody placed on it. A knob's level read against the frozen zero-knob
   baseline's rung set is *not* one: the baseline was swept once, in an
   earlier round, against tasks nobody built to be read against this level,
   and the set difference that falls out of that is a property of the two
   samples as much as of the knob. Such comparisons stay **printed**, clearly labelled as informational
   and advancing no counter, because they are still the widest view of where a
   level landed and losing them would cost the report its only reading of a
   knob that has no contrast yet.

   A registered *effort claim* counts where a frozen-baseline *rung* set does
   not, and the difference is registration rather than the comparator: an
   author who writes `baseline, cost, 1.25x` into a task's construction block
   before the run has named a comparator, a metric and a number in advance and
   can lose. Nobody registered anything by activating a knob.

2. **Direction-aware separation.** A contrast separates only *upward*. Order
   its levels on the knob's ladder; a contrast separates when some harder
   level's **highest observed rung stands strictly above** some easier
   level's highest observed rung. Set difference on its own is not
   separation — under the old criterion any level that resolved uniformly
   differed from a spread comparison and read as the knob working, which is
   how K11, commissioned to push tasks *up*, was credited for coming out
   easier. Where the knob's ladder is not enumerated in this section, no level
   is the harder one and the contrast is **not assessable**: the same reason
   reconciliation's crux/control section names no crux in a pair whose knob
   has no enumerated ladder.

   Every side of a contrast declares the knob, and the task set is where that
   is enforced rather than here: the lint refuses a pair or a family whose
   members set *different* knobs, because a knob only one side was built for
   leaves the other side with no level to print and no rung to be ordered
   against. Reconciliation meets the shape anyway — an artifact replayed from
   before the lint, a set assembled by hand — and where it does, the contrast
   is **not assessable** in either direction and the row names the member that
   does not declare the knob. What it must not say is either of the two things
   it has said: "the ladder is not enumerated", which is false wherever the
   ladder is written down right here, or a separation read off the undeclared
   side as though it sat below the lowest rung. The second is the worse of the
   two, because on every ladder whose bottom rung already means the knob is
   *off* — K9's `none`, K8's `covered` — it would call two semantically
   identical states separated and hand a demotion argument to whichever way
   the noise fell.

   A contrast is read only where its sides were balanced enough to speak. The
   minimum-sample guard the informational rows carry applies to the counting
   side too, turned in the direction this reading runs: there it asks whether
   two rung *sets* could have matched, here whether the harder side had the
   draws to top the easier one's spread. A side of n graded tasks lands on at
   most n distinct rungs, so a harder side holding fewer graded tasks than the
   easier side has rungs is being read against the maximum of more draws than
   it took itself — three easy tasks against one hard one. That does not make
   its silence impossible, since one task landing unsolved would still stand
   above anything; it makes the silence an unbalanced sample as much as a
   quiet knob, which is not evidence a demotion may be argued from. Where
   every comparison a contrast could draw is unbalanced that way, the contrast
   is **not assessable**. The guard only ever withdraws a verdict: an observed
   upward separation stands whatever the sampling, and so does silence read
   off sides that were balanced.

   The two guards read the same data and answer different questions, so they
   can disagree on it without either being wrong. The informational row's asks
   whether two rung *sets* could have matched, and withdraws where one side
   could not have reproduced the other's spread however its runs came out; the
   counting row's asks whether an upward separation was *observed*, and an
   observed separation stands whatever the sampling. So one task at the easier
   level read against three at the harder one prints a counted row that
   separated beside an informational row on the same two levels that is not
   assessable. That is the mirror of the shape the paragraph above withdraws,
   and the report prints both readings because the reader is owed the question
   each of them answered.

3. **Effort-bearing non-silence.** A counted round is **non-silent** for a
   knob when a registered contrast of that knob separated upward **or** when
   any effort claim scored to that knob **hit** on any model. Otherwise the
   round is silent. Effort claims are scored to a knob the way the contrast
   they are read in attributes them: a **pair** claim to the pair's varied
   knob — the one knob that moved between the two measurements — and a
   **baseline** claim to the knob its task activates where that is **exactly
   one** knob, and to no knob at all where the task activates several. A
   single-knob task is the one shape where the baseline comparator names what
   moved; a composite varies several things at once from the baseline, and one
   cost reading over three knobs names none of them, for the same reason a
   contrast moving two knobs attributes its outcome to neither. Composites and
   anchors declare their activations for the calibration table's profile key
   and form no contrast on purpose, and a counter that advanced a silent round
   for K1, K9 and K7 together off one baseline claim would be the artifact
   verdict this whole amendment removes.

4. **Only a reading that could have spoken counts as silence.** A round that
   put the knob to registered contrasts or claims and got a readable answer
   out of none of them prints **not assessable** and advances nothing. An
   unreadable comparison has never been allowed to count as silence: a
   contrast on an unenumerated ladder, a contrast the sample guard withdrew,
   and a claim read against an unswept or zero comparator each say nothing
   about the knob, and a counter reading them as misses would demote off
   measurements nobody made. Silence needs at least one contrast that could
   have separated or one claim that could have hit — and the report's tally
   says how many of each there were, so a row never renders an unreadable
   claim as an assessed miss.

5. **Two silent rounds still demote.** Unchanged, and the demotion still names
   the rounds it counted, with their dates.

6. **Stalled is not silent.** A knob with no counted round at all has not been
   shown to move nothing; it has never been asked. Its counter does not
   advance and it prints as **stalled**, naming what it lacks. This is a
   standing invitation to author a contrast or register a claim, and the price
   of it is that a knob can sit there forever — which is a fair price, because
   the alternative is demoting a knob on evidence nobody collected.

**What this does to the record, recomputed from the checked-in artifacts.**
The counters are derived and never stored, so amending the rule re-reads all
of history by itself. Where the recomputation and the recorded rulings of
§§13 and 19 disagree:

| knob | printed under the old rule | recomputed under the amended rule |
| --- | --- | --- |
| K1 | separated in both rounds; 0 silent | round 2 no longer counted at all — K12's families hold K1 constant, so K1 is nobody's varied knob there; round 1's four K1 families still separate upward. 0 silent, 1 counted round |
| K7 | not assessable, round 1; 0 silent | **stalled** — no family, no pair, no registered claim, in any round. 0 counted rounds, exactly as §18 ruled and #35 recorded |
| K8 | no separation, round 1; 1 silent | **stalled** — the seven K8 tasks are standalone and register no claim. 0 silent. **§13's demotion stands** as a recorded human verdict over two sweeps and an effort reading that ran the wrong way; it was never a counter reading and the amended counter does not reproduce it |
| K9 | no separation round 1, separated round 2; 1 silent | unchanged at 1 silent. Round 1's three pairs are flat; round 2's digest and dossier reach a rung above their controls, and outage's claim hit on haiku, so the round is non-silent twice over |
| K11 | separated, round 2; 0 silent | **silent 1 of 2** — no rung contrast exists, but four registered baseline claims do, and all eight readings missed. This is exactly the reading §19 wrote into the record by hand, and the counter now agrees without being told to |
| K12 | no separation, round 2; 1 silent | unchanged at 1 silent — both families flat across all four levels and all eight claim readings missed |

Two of those are the test that the amendment reads the evidence rather than
leaning on it: §19 predicted in advance that a direction-aware criterion would
print `no separation` for K11 and that "the counter would agree retroactively
when recomputed", and #35 ruled K7 stalled-not-silent for the reason the rule
now states in general. Neither was written into the code as a special case;
both fall out of clauses 1–3 and 6.

One weakness of K11's counted round is recorded rather than fixed: all four of
its claims use the category-baseline comparator, which §22.4 calls the weak
form — the baseline cells ran a different CLI version and are content-matched
to nothing, where a pair comparator is matched on both. So K11's silent round
rests on the weaker of the two comparators the schema offers. It is still a
number its author registered in advance and lost, which is the standard this
whole discipline is built on, and the identifiability argument of §23.5 is the
reason K11's retirement does not wait on a stronger one. Recorded beside it:
all eleven claims the task set registers — K11's four and the seven pair
claims of round 2 — are written on `metric: turns`, the metric this same
amendment stops defaulting to. The readings survive the deprecation because
every one of them is read against a comparator that is a measurement or a mean
of measurements rather than a threshold, so quantization moves a ratio and
never the rule; what it cost is the stringency, which is why the metric
changes for round 3 rather than the readings being rerun.

**Cost is the default effort metric** (#37). `turns` stays available and
nothing is forbidden, but a claim should be registered on `cost` unless its
author has a reason. §20 is why: turn counts here are small integers, so a
turns claim's stringency depends on how cheap its comparator happened to be —
from a 4-turn control the smallest possible step is exactly 1.25×, so a 1.25×
turns claim is met by one extra turn there and needs two against an 8-turn
control. Nobody registered that. Cost is continuous, and it accumulates the
reading, thinking and retrying that happen *inside* a turn: `dossier` on
sonnet spent its control's 5 turns and 54% more money. The claim schema is
unchanged — `metric` has always been there and stays required, because a
default that silently picks the metric would make old claims read as bets
their authors did not place.

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
K7, re-run it with a size-matched control. [Not done in round 2 and still
required. Round 2 gave K7 no tasks and K7 carries no effort claims, so it
produced nothing and its rung flag reads `not assessable` under #29's guard —
which advances no counter, leaving the knob unfalsifiable rather than silent.
Ruled stalled at §18; round-3 conditions at §23.7.]

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
[Resolved by #33/#34/#35: it got that round, with three non-textbook cruxes
and registered effort claims, and it separated on rungs for the first time —
§18. The knob survives on a narrowed claim, with a write-volume confound
recorded against it.]

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
  [Under §9's round-3 amendment (#37) the recomputed counter reads K8
  **stalled**, not silent: its seven tasks are standalone and register no
  effort claim, so no round ever put it to a registered contrast. The
  demotion above stands unchanged as what it always was — a human verdict on
  two sweeps and an effort reading, argued here rather than read off a
  counter.]
- **K9 was swept once.** Every K9 task is Track A; Track B has none. K9 has
  one silent sweep, not two, and is not eligible for demotion under the
  rule as written. **K9 stays, flagged, with one sweep remaining.**

Consequence, stated so it cannot be re-litigated later: K8-misleading is out
of the candidate profile dimensions and round 2 must not spend its
anti-saturation budget there. If K9 is silent again on rungs in round 2 it
is demoted as a rung lever regardless of its effort signal — the effort
result is grounds for changing *what is measured*, not for extending the
knob's life under the old measure. [Discharged by #35: K9 was **not** silent
in round 2 — digest and dossier each moved a full rung — so the clause never
fired and K9 survives as a rung lever. Final ruling at §19.]
Implementation follow-up (recorded, not a ticket): `reconcile-v1`'s round
counter should key on the sweep, not on `as_of`, or the same collapse recurs
whenever two sweeps share a day.
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
> unmentioned** [the `>` chain here transposes its last two terms; the
registered order is section 9's — prose below unmentioned, as the rest of
this sentence says] — and "implied by prose" sits *below* "unmentioned",
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
   sweep and prefer paired designs over baseline deltas. [Addressed by #29:
   `docs/agents/sweep-protocol.md` pins the version for a whole sweep and
   aborts on drift between invocations. It is protocol rather than a runner
   check because the runner reads the version once per invocation and stamps
   every row of that invocation with it, so drift is by construction something
   that happens between invocations — and the runner does not know which
   earlier logs belong to the sweep.]
3. **K7 flagged "separated", in the easier direction.** The report's
   criterion compares *sets* of observed rungs, and K7's 2 cells
   ({haiku-solvable}) cannot reproduce the 11-cell baseline's 3-element set
   whatever they do. The flag is an artifact of set comparison at n=2, not
   evidence of a difficulty effect; K7's real result is the effort contrast
   in section 12. The criterion needs a minimum-n guard, or set comparison
   needs replacing by something that degrades gracefully at n=1 per cell.
   [Resolved by #29: the guard is the comparison's own arithmetic rather than
   a constant — a side of n graded tasks lands on at most n distinct rungs, so
   a side with fewer tasks than the other has rungs is reported not assessable
   with the counts named. K7's flag now reads "not assessable"; nothing else in
   the report moved, because sides landing on the same set always pass the
   guard, so it can only ever withdraw a claim of separation.] [Round 2: the
   guard closed the arithmetic half of this wound and left the other half
   open. The criterion is still direction-blind, so K11's level was flagged
   "separated" in round 2 for coming back uniformly *easier* than the
   baseline — the same shape as K7's round-1 flag, now surviving the guard
   because K11 has four graded tasks instead of two. Ruled at §19; the fix is
   §23.1.]
4. **Two graded cells live in files named `-dry`.**
   `2026-08-05-dry.jsonl` and `2026-08-05-trackb-dry.jsonl` each hold one
   real, graded, paid row (`settings-merge-layers-l1` haiku,
   `rbql-like-escape-wildcards` haiku). Reconciliation reads them correctly;
   any hand-rolled analysis that filters on the filename will silently drop
   two cells, as a first pass of this analysis did. [Addressed by #29: dry
   checks now write to normally-named logs and no analysis may select logs by
   filename — `docs/agents/sweep-protocol.md`. These two files keep their
   names: they are checked-in artifacts of a swept round, and renaming them
   would be rewriting the record rather than the rule.]
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
   [Resolved by #30, in part: predictions may register an effort claim and
   `reconcile-v1` grades it per model. The kill criterion still counts rung
   silence only — deferred there, and still outstanding at §23.8. First
   reading of the instrument at §20: it worked, and its metric is the thing
   worth changing.]
2. **Replace K8-misleading as the anti-saturation lever, with K11
   (detection distance).** K8 is demoted and its budget is free. The round's
   own failure analysis names the replacement: every K1 defect that fired —
   aliasing, an inverted tie-break, a refusal boundary, a dropped return
   value — is invisible to the happy-path check the agent runs on itself,
   and "how late does failure manifest" is K11's lever, not K8's. Secondary
   candidates: K7 at scale, since it is the only knob that moved effort by
   multiples; K10 coordination width, untouched so far.
   [Resolved by #31/#34/#35, negatively: K11 was authored and swept and read
   inert — cheaper than baseline on both metrics, 0/8 on effort, no rung
   movement. As instrumented it measured spec self-checking, which the models
   have. §18; the pair-it-or-drop-it decision is §23.5. K10 is still
   untouched.]
3. **Split K1 by *how* a decision is conveyed, not by how much prose.** The
   K1 ladder is validated but its levels are the wrong variable. Round 2's
   K1 should vary along the ordering section 14 recovered — criterion stated
   / repo primitive available / implied by prose / unmentioned — with
   "implied by prose" registered as *harder* than "unmentioned", which is
   the round's most interesting and most falsifiable single claim.
   [Resolved by #32/#34/#35 as knob K12, inconclusively: both families came
   back flat at the bottom rung, so the ladder was not tested rather than
   falsified — a floor effect, compounded by the docstring channel #32
   recorded. Silent 1 of 2. The ordering does show up in *effort*, in the
   ladder's direction, against the reading-burden order registered instead.
   §18, conditions for the second round at §23.6.]

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
harder" missed, 0/12. [Round 2 made two more such bets, the K12 prose
variants, and missed both: **0/14 lifetime outside K1**. Round 2's own
hit-rate rose to 77.8% by betting conservatively, but the bias inverted
rather than vanished — the two cells where a rung actually moved were both
under-predicted. §21.] Read as an instrument, the rationales are good
mechanism descriptions (the diffs confirm the traps were real and correctly
located) attached to bad difficulty estimates, and the systematic direction
says the gap is calibration, not understanding: 2026 authors reasoning about
what an agent will find hard consistently over-estimate, because they price
the trap and not the model's willingness to read past it. Formalization
(the sketch → φ → P(resolve) chain) stays deferred; the round did not
produce a stable enough outcome variable to fit against, and item 1 above is
the prerequisite.

## Round 2 verdicts — 2026-08-06

Round 2 (#27) is built and swept: instrument repairs (#28–#30), 18 new tasks
(#31–#33), one sweep (#34, sweep id `round-2`, 36 cells, one agent version
2.1.223, $4.05). Everything below is recomputable by
`uv run ai-bench reconcile-v1` over checked-in artifacts, except the per-cell
turns/cost contrasts and the added-line ratios, which are computed from the
same run logs' `turns`/`cost_usd` fields and from the reference solutions,
and are quoted here because the report does not group by them. Nothing above
is superseded; section 9's knob list stands, with the verdicts below attached
to it.

### 17. What the round measured

Hit-rate 24/45 (53.3%) over the whole corpus; round 2's own 18 tasks went
**14/4 (77.8%)** against round 1's 10/27 (37.0%). The calibration lesson
worked: rungs bet conservatively more than doubled the hit rate.

The rung ladder saturated harder than in round 1. Sonnet resolved all 18
tasks and haiku resolved 16, the two exceptions being the digest and dossier
cruxes — so **16 of 18 round-2 tasks landed on the bottom rung** and the
other two on the middle one. Nothing reached unsolved.

Per-cell effort. Frozen feature-dev zero-knob baseline for reference: haiku
9.82 turns / $0.0711 mean, sonnet 6.45 / $0.1846, n=11.

```
                       haiku turns  haiku cost  sonnet turns  sonnet cost
K9  crux    digest          15        $0.1662         9         $0.5584
    control digest           7        $0.0628         8         $0.3809
K9  crux    dossier          6        $0.0706         5         $0.2457
    control dossier          4        $0.0434         5         $0.1595
K9  crux    outage           6        $0.0554         5         $0.1529
    control outage           4        $0.0474         5         $0.1417
K11 far, mean of 4         6.50        $0.0626      5.00         $0.1379

K12, per variant along the ladder (criterion / repo-primitive /
unmentioned / prose):
    album     haiku    3 / 3 / 3 / 5 turns    $.0325 / .0322 / .0317 / .0411
              sonnet   4 / 4 / 4 / 4          $.1133 / .1088 / .1124 / .1139
    pricelist haiku    7 / 4 / 3 / 4          $.0559 / .0395 / .0330 / .0395
              sonnet   3 / 3 / 3 / 4          $.0985 / .0983 / .0986 / .1188
```

### 18. Per-knob verdicts

**K9 (crux depth) — SURVIVES as a rung lever, on a narrower claim than the
knob's name.** Round 2 is the first rung separation any knob other than K1
has produced: `digest-fit-to-budget` and `dossier-merge-two-records` land
sonnet-only against haiku-solvable controls, +1 rung each; `outage` is flat.
What survived is *the redesign*, not the knob as originally registered. Round
1's three cruxes were textbook (bin packing, rearrange-k-apart, debt
simplification) and separated nothing; round 2's three were built so that no
named method resolves them, and two of three moved a rung. The registered
claim that survives is therefore **"a planted open decision that no named
method resolves"**, and K9's round-1 formulation is not what was validated.

Three caveats travel with it, and they are load-bearing:

1. **K9 measures resolving a labelled crux, never noticing one exists**
   (recorded in #33). All six round-2 cruxes are announced by the same
   closing formula as round 1 — *"Which of the entries that could be left out
   you keep is yours to choose … any of them is a correct answer."* The
   validated lever is a *labelled*-crux lever. Noticing is untested.
2. **The separation is confounded with write volume, and the confound lines
   up with the result.** Added lines in the reference solution, crux against
   its control: digest **1.61×**, dossier **1.41×**, outage **0.84×**. The
   two pairs that moved a rung are the two whose crux also writes ~40–60%
   more code; the one pair whose crux writes *less* is the one that stayed
   flat. "The crux is harder" and "the crux is bigger" are not separated by
   this design. (#33 recorded the ratios as control/crux — 0.62/0.71/1.19 —
   and as better balanced than round 1's 0.58/0.54/0.83; better balanced they
   are, but 1.61× and 1.41× are not matched, and the ordering is exactly the
   ordering of the result.)
3. **n=3 pairs, n=1 per cell.** Two of three is a direction, not a rate.

Verdict: K9 stays, promoted to *candidate* ex-ante profile dimension
alongside K1, but **not usable for selection until the volume confound is
broken** — round 3 must match added lines within a pair (or vary volume
orthogonally) before any recommendation inherits this.

**K11 (detection distance) — NEGATIVE first reading, and the design is why.**
All four tasks resolved on both models (8/8), every rung bet hit, and the
effort claims went **0/8** — K11 came in *cheaper* than the baseline on both
metrics and both models: haiku 6.50 turns (0.66×) and $0.0626 (0.88×);
sonnet 5.00 turns (0.77×) and $0.1379 (0.75×). Seven of the eight readings
came in under 1.0×, two of them far under — `standrig` 0.31× and `roster`
0.41× on haiku — and every sonnet reading landed on 0.77×.

The registered prompt-length confound **ran the other way and the reading
survives it.** #31 pre-registered that K11 prompts run ~1.5–1.9× the
controls' word count, so an effort *hit* would have read as "distance plus a
longer brief". The prompts were longer and the work came in below baseline
anyway, on turns and on cost. The confound could only have inflated the
result; it did not, so the negative is if anything understated.

#31's spec-review observation is the diagnosis, and the run logs confirm it:
a clause-by-clause self-check written straight off each prompt's own bullets
catches all four planted bends, so **K11@far as instrumented measures whether
the model self-checks against the spec it was handed, and current models do.**
Sonnet spent exactly 5 turns on all four tasks — a fixed read/edit/verify
loop, not an encounter with distance. The defect distance was never reached.

The deeper fault is structural: **K11 was authored without a contrast.** Four
standalone tasks at one free-text level, whose only comparator is a frozen
cross-version category baseline. K9 was readable because it was paired; K11
was not. Round 3's decision is pair-it-or-drop-it (§23), and note the
identifiability problem before pairing: removing the prompt clause that lets
a self-check catch the defect moves K1, not K11, so K11 may not be
identifiable against spec completeness at all.

**K12 (decision conveyance) — SILENT round 1 of 2 on rungs; the ladder is
untested, not falsified; the *effort* deviation is falsified.** Both families
came back flat at {haiku-solvable}×4 — eight cells, all at the bottom rung,
on both models. A ladder cannot show an ordering when every rung is the
floor. Read #32's recorded compression first, as instructed: the crux is
stated in module docstrings at every level (discoverability requires it), so
c1→c3 was compressed by construction for any docstring-reading agent. Both
readings agree the instrument did not test the claim.

The prose variants are the round's two over-predictions — the only two
"harder" bets round 2 made, both missed (§21).

What round 2 *did* falsify is the separately registered reading-burden effort
order (§9's "What K12 does not claim", deviation accepted on review in #32),
which predicted effort peaking at **unmentioned** rather than at prose. All
eight registered K12 readings (4 claims × 2 models) missed, and they missed
*in the ladder's direction*. Taking the withheld pair (unmentioned vs prose)
on both metrics and both models — eight measurements — prose is the costlier
variant in six and level in the other two, **none leaning the registered
way** —

```
prose ÷ unmentioned    album-haiku  album-sonnet  price-haiku  price-sonnet
  turns                   1.67x         1.00x        1.33x        1.33x
  cost                    1.30x         1.01x        1.20x        1.20x
```

So the ladder's *order* survives in effort exactly where the rung could not
show it, while the reading-burden order that displaced it does not. On the
stated pair (criterion vs repo-primitive) repo-primitive is never costlier:
0.99×, 0.96×, 0.71×, 1.00× on cost. This is post-hoc and n=2 families —
it is a hypothesis for round 3, registered as such below, not a result.

**K7 (invariant density) — STALLED, and it is the instrument's fault as much
as the knob's.** K7 registered no effort claims (it predates #30) and got no
new tasks in round 2, so it produced nothing this round: its rung flag is
`not assessable` under #29's min-n guard (2 graded tasks against a 3-rung
baseline), and a not-assessable verdict advances no counter. **K7 is
currently unfalsifiable — it can sit at "not assessable" forever without ever
being demoted.** That is the ruling: not silent, stalled.

Recorded, flagged post-hoc so it cannot later be mistaken for evidence: K7's
two round-1 cells are the largest effort effect in the entire corpus —
`pysm-remember-substate-history` 26 haiku turns and `rbql-like-escape-wildcards`
46, against a 9.82 baseline mean (2.65× and 4.68×; sonnet 1.55× and 2.48×).
A baseline turns claim at ≥1.5× would have gone 4/4. **Round 3 must not
register that claim at that factor**, because it would be fitted to the data
it is then scored against — which is precisely the post-hoc mining #30 was
built to end. For K7 to survive round 3 it must (a) register effort claims on
*new* K7 tasks before they run, and (b) carry at least 3 graded tasks at the
dense level so the min-n guard admits it. §12's round-1 follow-up — re-run
with a size-matched control — is still outstanding and still required, since
the K7 cells remain the only ones on large vendored substrates.

**K1 — validated in round 1, not tested in round 2.** The report's
`K1 sweep round-2 separated` flag must not be read as evidence: the
acceptance side of that comparison is exactly the eight K12 variants, and
every K12 family holds K1 constant at acceptance *by design* (§9, "How K1 is
read across a K12 family"). The flag is set arithmetic over a constant. See
§22.1.

**K8 — stays demoted** (ruled in #26 / §13). It sits at silent 1 under as-of
keying and round 2 spent nothing on it, as §13 required.

### 19. Kill-discipline ruling

Registered rule (section 9): no separation after two sweeps → demoted. Round
2 is the first round keyed on a real sweep id (#28), so the counters below
are honest for the first time.

- **K9: not silent. Not demoted. Ruled finally as a rung lever — it
  survives.** §13's consequence clause read "if K9 is silent again on rungs
  in round 2 it is demoted as a rung lever regardless of its effort signal".
  It was not silent: digest and dossier each moved a full rung. The clause is
  discharged and the counter resets to 0 silent rounds. K9 remains subject to
  the discipline in future rounds; what it carries forward is the narrowed
  claim and the volume caveat of §18.
- **K12: silent 1 of 2. Kept, but a repeat of round 2 would be a wasted
  sweep.** The mechanical counter is correct and stays. Demoting early would
  be wrong — the round produced a floor effect, not a falsification, and a
  knob has to be *given* a chance to separate before silence means anything.
  But K12's second round must not be round 2 again. It is conditioned in §23:
  raise the floor, handle the docstring channel, register the effort claims
  in the ladder's direction. Flat again under those conditions and K12 is
  demoted with a real negative behind it.
- **K11: the counter says 0 silent rounds. The research record counts this as
  silent 1 of 2.** This is an interpretation ruling and it is written here
  rather than into `reconcile-v1`, whose code is unchanged.

  The report flags `K11 sweep round-2 separated — far {haiku-solvable} vs
  baseline {haiku-solvable, sonnet-only, unsolved}`. That separation is a
  strict-subset relation **in the easier direction**: K11's level is narrower
  and lower than the baseline it is read against. K11 was commissioned as the
  *anti-saturation* lever — its entire purpose is to push tasks up — so a
  flag that fires because the level came out uniformly easier is the
  instrument recording evidence *against* the knob as evidence that the knob
  did something.

  Three things make this a criterion defect rather than a judgement call.
  (a) The criterion compares *sets* and is direction-blind by construction:
  any level that resolves uniformly differs from a spread baseline, so the
  flag is near-automatic. (b) #29's min-n guard does not reach it — the guard
  is one-directional by design, it can only ever withdraw a separation claim,
  and K11 clears it by a single task (4 graded against the baseline's 3
  distinct rungs; at 3 tasks it would still clear, at 2 it would have read
  not assessable). The guard fixed the *arithmetic* blind spot #29 was aimed
  at and leaves the *direction* blind spot untouched. (c) Round 2 fired this
  flag three times and only one is informative: K9's (level against level,
  inside a designed contrast) is real; K11's is direction-inverted; K1's is
  an artifact of K12 holding K1 constant.

  So: K11 counts as **silent 1 of 2** in this record, and the divergence
  between that reading and the printed counter is to be closed by fixing the
  criterion in round 3 (§23.1), not by hand-maintaining a second set of
  counters. Under a direction-aware criterion the report would print
  `no separation` for K11 in round 2 and the counter would agree
  retroactively when recomputed — which is the test that this ruling is a
  reading of the evidence and not a thumb on the scale.

  [Closed by #37. §9's amended kill discipline is contrast-only, direction-
  aware and effort-bearing, and the recomputation over the same artifacts
  prints K11 **silent 1 of 2**: the direction-inverted baseline flag is now an
  informational row advancing nothing, and what counts the round is K11's four
  registered baseline claims, whose eight readings all missed. The hand-kept
  reading and the printed counter agree, and the test above is passed.]

### 20. The effort instrument's first reading

#30 shipped and it worked: 22 readings of 11 claims, **0 not assessable** —
every comparator was present, which is the thing that was supposed to be hard
and turned out not to be. Hit-rate 3/22 (13.6%): the three hits are all haiku
readings of K9 crux pair claims (2.14×, 1.50×, 1.50× against 1.25×), and all
three miss on sonnet (≤1.12×).

The instructive part is what that pattern is *not*. Read as registered — on
turns — effort fires on haiku for **all three** K9 pairs and misses on sonnet
for all three, including outage, whose rung did not move, and excluding
digest on sonnet, whose rung did. **Turns did not distinguish the two knobs
that moved a rung from the one that did not.** The claim verdicts are
identical across all three pairs; the rung outcomes are not.

Cost does distinguish them, perfectly, at n=3:

```
crux ÷ control      turns haiku  turns sonnet   cost haiku  cost sonnet   rung
digest                 2.14x        1.12x         2.65x       1.47x       +1
dossier                1.50x        1.00x         1.63x       1.54x       +1
outage                 1.50x        1.00x         1.17x       1.08x       flat
```

Against the same registered 1.25× threshold, cost scores 4/4 on the two pairs
that moved a rung and 0/2 on the one that did not: 3/3 correspondence with
the rung outcome, on both models. Turns produced the identical verdict
pattern for all three pairs and so discriminated none of them.

The mechanism is legible. Turn counts here are small integers (3–9), and they
quantize: from a 4-turn control the smallest possible non-zero step is +1
turn = exactly 1.25×, so a 1.25× turns claim against a cheap control is met
by any single extra turn, while the same claim against digest's 8-turn sonnet
control needs two. **A turns claim's stringency depends on how cheap its
comparator happened to be**, which is not a property anyone intended to
register. Cost is continuous and accumulates the reading, thinking and
retrying that happen *inside* a turn: `dossier` on sonnet spent the same 5
turns as its control and 54% more money. Turns were blind to work that cost
real tokens.

Two honest limits on this. First, it is a post-hoc metric swap on three
pairs — a round-3 pre-registration (§23.2), not a verdict. Second, the cost
ordering (2.65 / 1.63 / 1.17) is collinear with the added-line ordering
(1.61 / 1.41 / 0.84) at n=3, so cost may be tracking write volume rather than
crux difficulty; §18's volume caveat and this finding have to be broken apart
by the same round-3 experiment.

Verdict on the instrument itself: **#30 is validated and stays.** It produced
a falsifiable reading on every claim registered, guessed at nothing, and its
one design choice worth revisiting is the metric, not the mechanism.

### 21. The prediction instrument

24/45 lifetime (53.3%), round 2's own 18 going 14/4. The calibration shift
is the whole story, and it cut both ways:

- **Rung bets got much better by getting more conservative.** 37.0% → 77.8%.
  Sixteen of round 2's eighteen rung bets were "haiku-solvable", and fourteen
  of those sixteen hit.
- **The "harder" bet is still 0.** Round 2 made exactly two upward rung bets
  — the K12 prose variants, the ladder's own registered claim — and both
  missed. Outside K1, predictions of the form "this knob makes this task
  harder" now stand at **0/14** (0/12 in round 1, 0/2 here). No author has
  ever correctly predicted an upward rung movement outside K1.
- **The first under-predictions outside K1 arrived, and they are the two
  cells where a rung actually moved.** `digest-fit-to-budget` and
  `dossier-merge-two-records` were bet haiku-solvable — conservatively,
  explicitly citing the 0/12 lesson, explicitly betting the difficulty would
  "show in turns rather than in the rung" — and came back sonnet-only.

Put together: **rung movement happened twice in round 2 and the author had
bet against it both times.** The instrument's directional bias did not
disappear under the calibration lesson; it inverted. Round 1's authors
over-predicted because they priced the trap and not the model's willingness
to read past it; round 2's authors, told that, under-predicted the two hardest
things they built. The rationales remain good mechanism descriptions attached
to unreliable difficulty estimates — what changed is the sign of the error,
which is what a calibration correction does when it is applied as a rule
rather than as a prior.

The consolation is that the mechanism descriptions were right where it
counted: both under-predicted rationales named the *effort* consequence
correctly ("shows in turns rather than the rung"), and both carried effort
claims that hit on haiku. Authors know what they built; they cannot price it
against a model. That argues for keeping the rung prediction mandatory (it is
cheap and it is the falsification record) while treating the effort claim as
the load-bearing one.

### 22. Anomalies, read

1. **K1's round-2 "separated" flag is set arithmetic over a constant.** The
   comparison's K1=acceptance side is exactly the eight K12 variants, and
   every K12 family holds K1 at acceptance *by design* — §9's own "How K1 is
   read across a K12 family" says so. K1 was not varied
   in round 2 and cannot have been tested by it. The general fault: a knob is
   currently scored in any round where tasks *declaring* it happen to have
   run, rather than in rounds where it was the *varied* knob. See §23.1.
2. **The separation criterion is direction-blind.** Ruled at §19 for K11;
   noting here that it also means a knob can be credited with a "separation"
   for making tasks easier, which no reading of the kill discipline intends.
   §15.3's round-1 anomaly is the same wound: #29 closed the arithmetic half
   (min-n) and left the direction half open.
3. **The rung ladder has run out of headroom on this material.** Sixteen of
   eighteen round-2 tasks landed at the bottom rung, and the two exceptions
   needed a deliberately non-textbook invented constraint to get one rung up.
   Across two rounds, 7 of 45 constructed tasks have ever landed above
   haiku-solvable, and only 2 of those 7 were predicted correctly
   (`billing-l2`, `settings-l3` — both K1). The rung is a three-valued
   outcome on a saturated ladder; effort is continuous and has separated in
   every round it has been measured. Round 3 should stop asking the rung to
   carry verdicts (§23).
4. **Effort claims registered against a frozen baseline are the weak form.**
   All eight K11 claims used the category-baseline comparator; all eight
   missed. All six K9 claims used the pair comparator; three hit, and the
   pair contrast is version-matched and content-matched where the baseline is
   neither (§15.2's version stratification still applies to every baseline
   comparison — the baseline cells ran 2.1.221, round 2 ran 2.1.223). Pair
   comparators are the ones that produced signal in both rounds.
5. **Process, recorded from #34:** the 18-task scratch root does not lint in
   isolation because K11's baseline comparators live outside it (subsetting
   artifact; whole-set lint clean at 67). One scratch-dataset path collision
   with another agent's leftover file during the dry check, non-destructive,
   resolved by switching to a unique path. #33's cross-suite coverage guard
   now fails loudly if a K9 pair goes unprobed — the INFO probe-coverage gap
   is closed.

### 23. What round 3 should change (candidates, not tickets)

1. **Score a knob only where it was the varied knob of a designed contrast.**
   The single highest-value instrument change, and it fixes three faults at
   once: K1's artifact flag (§22.1), K11's direction-inverted flag (§19), and
   K7's permanent not-assessable stall (§18). Level-against-level comparisons
   inside a family or pair become the scoring comparison; level-against-frozen-
   baseline becomes informational output that advances no counter. Add
   direction-awareness while there: a level separates *upward* only when its
   rung distribution reaches above its comparator's. [Shipped by #37: the
   amended rule is registered in §9 and mirrored by `reconcile-v1`, and it
   carries candidate 8 with it.]
2. **Pre-register the K9 effort claims on cost, not turns, on new pairs.**
   §20's 3/3 correspondence is post-hoc and collinear with write volume;
   registering the same threshold on cost in advance is what turns it into a
   result. Registering it at a factor fitted to round 2's numbers is not — the
   factor should stay at 1.25×. [Shipped by #39, on the pairs candidate 3
   asks for; each crux's rationale also registers the prompt-length gap it
   carries, 1.20–1.25× the control's word count, following #31's precedent.]
3. **Break K9's volume confound.** Match added lines within a pair (±10%), or
   author a crux/control pair where the crux writes *fewer* lines. Until this
   lands, K9 is not usable as an ex-ante profile dimension however good the
   rung result looks. [Shipped by #39: three pairs at 1.00×, 1.05× and 1.08×
   added lines, each crux registering cost ≥1.25× against its pair partner.]

   **The any-resolution property and the non-textbook justification pull
   against each other, recorded before any sweep so the caveat cannot be
   invented afterwards.** A K9 crux grades every answer satisfying the stated
   rules at 1.0, and a named method fails such a suite *only* where its output
   violates one of those rules. So "no named method resolves this" can never
   mean "no named method passes"; it means one of two much weaker things, and
   #39's three pairs are split across them. `bookcase-shelve-the-run` is the
   strong form: a divider stands between two stretches sharing a shelf, so the
   sizes bin packing takes to add up do not, and next fit, first fit and the
   fewest-shelves optimum all overfill a shelf and fail the stated width rule
   — the round-3 suite runs next fit as a checked-in probe, under the name
   `pack-the-shelves-without-the-dividers`, and it fails 2 of the crux's 46
   grading tests. `remit-pay-what-fits` is the weak form, and its task.yaml says
   so outright: a subset-sum optimum is maximal by construction and maximality
   is all the rules ask, so 0/1 knapsack passes the grading suite 63/63.
   `roll-pick-from-bursts` is weak in the same way and always conceded it —
   the prompt hands the clustering over, and a dedupe keeping the first
   admissible frame of each burst passes 48/48. Read a round-3 K9 result,
   therefore, as evidence about **a labelled open decision** and not about a
   decision recall cannot reach: only one of the three pairs supports the
   second reading, and two of the three sit beside a textbook method that
   resolves them.
4. **K9 deepening: the notice-the-crux variant.** Every K9 crux so far is
   announced by the same closing formula. A variant that plants the same
   decision and *does not label it* tests whether K9 measures resolution or
   detection — the question §18.1 leaves open, and the more valuable half.
5. **K11: pair it or drop it.** As authored it has no contrast and no
   identifiable lever (§18). If it is kept, it needs a matched near/far pair
   over one underlying change, and an answer to the identifiability problem —
   the prompt clause that lets a self-check catch the defect is K1's variable,
   not K11's. Retirement is a defensible outcome and cheaper than a second
   negative round.
6. **K12's second round must raise the floor.** Four levels at the bottom rung
   test nothing. Cross K12 with an underlying change that is not haiku-trivial
   (the K9 substrate is the obvious host), handle or measure the docstring
   channel that compresses c1→c3, and register the effort claims **in the
   ladder's direction on cost** — which §18 shows is where the ordering
   actually lives.
   [Shipped by #40 as the `nightbus-print-the-sheet` family: one underlying
   change — a printed running sheet whose reference solution adds 32 lines
   against the album family's 5 and the pricelist family's 9 — conveyed at all
   four levels, with the withheld decision (a day's working runs 04:00 to
   04:00) absent from every docstring, from the README and from the acceptance
   block all four prompts share, discoverable instead through
   `operating_day`'s body and through three of the repository's own visible
   tests.]

   **The readings this round is taken under, recorded before the sweep so they
   cannot be invented after it, the way §23.3 records K9's:**

   **The floor is 3.6× round 2's, not 6.4×.** The family's suite binds the
   ratio against the *larger* of round 2's two changes — pricelist's 9, at a
   threshold of 3× — so 32 lines is 3.6 times the change this comparison is
   actually made against. The 6.4× that 32-against-album's-5 suggests is the
   friendlier of the two numbers and is not the one under test. #40's own
   commit prose and its `-c1` authoring comment said "32 against album's 5"
   without naming which comparison binds; corrected here.

   **One family, not round 2's two.** K12 buys 8 cells this round rather
   than 16. Sixteen would be over a third of a 34–44 cell round spent on a
   knob already at silent 1 of 2, ahead of K10 and K4, which have never been
   built at all. So a flat result is a result about one change conveyed four
   ways under the three conditions, and the sample is no larger than round
   2's.

   **What #40 raises is the change's floor, not the ladder's.** The docstring
   channel is closed and the underlying change is no longer a five-line set
   intersection, and both were real faults. But three of the four rungs #40
   registers are `haiku-solvable` and only `prose` is bet a rung up, so by the
   author's own pre-registration three of the four variants sit on the bottom
   rung before a model is run. §18's objection — "a ladder cannot show an
   ordering when every rung is the floor" — therefore remains available for
   the rung axis: a family that comes back flat at haiku-solvable×4 has
   returned exactly what was predicted for three of its four members, and the
   rung cannot falsify the ladder off that. The cost claims are what carry
   this round.

   **The prior is asymmetric, and here it is before the fact.** Under §9's
   amended discipline the round is non-silent only if a registered contrast
   separates upward or an effort claim scored to K12 hits. With three rungs
   registered at the floor, and with `-c2`'s claim discounted in advance two
   paragraphs below, the outcome that plainly keeps K12 non-silent is `-c4`'s
   claim hitting — or, failing that, `prose` landing above `unmentioned` on
   the rung. Against round 2's own prose-over-unmentioned cost multiples
   (1.30×, 1.01×, 1.20×, 1.20×) a 1.25× claim goes 1 of 4. That is the number
   this lane is entered on and it is written down here rather than
   reconstructed from a flat report afterwards.

   **Its `repo-primitive` pointer is the strong kind.** `operating_day` is the
   whole of the withheld decision, so following the pointer lands on 1.0 —
   album's asymmetry, not pricelist's (#32). A miss at that level is the level
   failing and may be read as one; there is no weaker pointer to blame.

   **The stated pair's cost claim is registered against the only evidence
   there is.** Round 2 measured repo-primitive ÷ criterion at 0.99×, 0.96×,
   0.71× and 1.00×, so the 1.25× registered on `-c2` bets against all four
   readings, on the ground that with the boundary out of the module's prose
   the pointer now costs a read the criterion variant does not make. If that
   claim misses it is not news, and a miss there should not be read as
   evidence against the ladder; the withheld pair's claim on `-c4` is the one
   carrying the contrast, and 1.25× would have gone 1 of 4 against round 2's
   own prose-over-unmentioned cost multiples.

   **And the symmetric half of that discount.** A `-c2` hit would contradict
   all four readings anyone has, which makes it the weaker kind of surprise
   until its mechanism is shown. What the claim asserts is not a number but a
   read: that following the pointer costs an inspection of `operating_day`
   the criterion variant never makes. So a hit is confirmed from the run's
   diff and turn record showing that read, not from the multiple alone — a
   1.25× produced by a model that wandered is the same 1.25×. A discount
   applied only to the losing direction is a thumb on the scale.

   **What a third `prose` miss means, read now.** This is the third time
   `prose` is bet `sonnet-only` — album's and pricelist's were the other two,
   and both missed. Upward rung bets outside K1 stand at 0/14 lifetime (§21),
   every one of the 14 lost. A third `prose` miss would leave that ledger
   still at zero after a round built specifically to give an upward bet room,
   and at that point it stops being a fact about K12: it is the instrument
   reporting that authors of this material cannot pick in advance which of
   their own tasks a model will fail. The reading to take then, fixed now, is
   §21's — keep the rung prediction as the falsification record it is and stop
   asking it to carry selection — taken as a conclusion this paragraph
   pre-committed to, not as a fresh inference invented to explain a
   disappointing round.

   **What the calibration table will not show.** All four variants declare
   `K1=acceptance` with a K12 level, which is exactly the profile key round
   2's two families already occupy, so `calibrate-v1` pools a 32-line change
   with album's 5 and pricelist's 9 into one row and the row key has no way to
   say so. Declaring K9 to hold them apart was considered and rejected as
   untrue rather than inconvenient: §18's surviving formulation is a
   *labelled* open decision, and this boundary is labelled but not open in
   `-c1`, whose criterion states it and where an answer satisfying the stated
   rules grades 1.0, and open but not labelled in `-c3` and `-c4`, where
   nothing announces that a decision is being left. In those two the stated
   rules leave the boundary undetermined and the transcription still grades
   0.0, which is the sense in which §23.3's any-resolution property does not
   describe this family — it is a caveat on how a K9 result should be read,
   not a test a task is put to. So the pooling is recorded instead, here and
   in all four authoring comments: a K12 cost multiplier read off that table
   is a mean over changes of 5, 9 and 32 added lines, and the table cannot be
   asked which.
7. **K7: register claims or retire it.** New tasks, effort claims registered
   before the run, at least 3 graded tasks at the dense level, and the
   size-matched control §12 asked for in round 1. It is the largest effort
   effect ever measured here and the only activated knob carrying no claim.
8. **Make effort the primary registered outcome.** §22.3: the rung has
   saturated on this material and effort has separated in every round. The
   kill discipline should read separation on either axis, as §16.1 proposed
   and #30 half-delivered — #30 grades effort claims but the demotion counter
   still counts rung silence only (recorded as deferred in #30's close).
   [Shipped by #37 as clause 3 of §9's amended discipline: a registered effort
   claim that hits makes the round non-silent, and one that is registered and
   misses is what makes the round count at all — which is the whole difference
   between K11, silent, and K7, stalled.]
9. **Still unticketed from round 1:** the "misleading neighbour" knob
   candidate (the guard-transplant mechanism from `inventory-l3`) and K10
   coordination width, both untouched by round 2.

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
