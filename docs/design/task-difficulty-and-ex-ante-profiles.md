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
| K7 | not assessable, round 1; 0 silent | **stalled** — no family, no pair, no registered claim, in any round. 0 counted rounds, exactly as §18 ruled and #35 recorded. [Round 3 gives it two pairs and two registered cost claims (#41, §23.7), so the next recomputation reads a counted round rather than a stall — the rung side stays not assessable while K7's ladder is empty] [And that is what round 3 printed: one counted round, non-silent on 2 of 4 effort readings, both pairs not assessable on the rung. 0 silent. §25, §26] |
| K8 | no separation, round 1; 1 silent | **stalled** — the seven K8 tasks are standalone and register no claim. 0 silent. **§13's demotion stands** as a recorded human verdict over two sweeps and an effort reading that ran the wrong way; it was never a counter reading and the amended counter does not reproduce it |
| K9 | no separation round 1, separated round 2; 1 silent | unchanged at 1 silent. Round 1's three pairs are flat; round 2's digest and dossier reach a rung above their controls, and outage's claim hit on haiku, so the round is non-silent twice over [Round 3 adds a third counted round, non-silent on 2 of 6 effort readings with 0 of 3 contrasts separating, so the counter stays at 1 silent of 3. What the flat rungs mean now that the volume confound is broken is ruled at §30] |
| K11 | separated, round 2; 0 silent | **silent 1 of 2** — no rung contrast exists, but four registered baseline claims do, and all eight readings missed. This is exactly the reading §19 wrote into the record by hand, and the counter now agrees without being told to. [**Retired** by #41 at this count, on the identifiability argument of §23.5, not on the counter: no round after round 2 asks it, so 1 of 2 is where it stays. Its four tasks and their construction blocks stay in the set, because every counter here is derived from the artifacts and a knob deleted from the registry would leave the report unable to read its own past] |
| K12 | no separation, round 2; 1 silent | unchanged at 1 silent — both families flat across all four levels and all eight claim readings missed. [Round 3's nightbus family is flat too, on all three contrasts and all four claim readings, so the counter reaches **silent 2 of 2 and demotes** — the first demotion clause 5 has ever computed. §25 records what kind of evidence produced it and §26 the ruling] |

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
Ruled stalled at §18; round-3 conditions at §23.7. **Done in round 3 by #41**,
and matched harder than this sentence asked: each of the two new pairs holds
its dense task and its calm control on the *same* pysm snapshot byte for byte,
so repository size is identical rather than similar, and the reference
solutions are matched on added lines within 10% as well.]

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
   untouched.] [Both secondary candidates are taken up in round 3: K7 by #41
   (§23.7) and K10 by #42, alongside K4, as the intensity batch (§23.9).]
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
[Round 3 matched them, and the condition discharges into a negative. Three new
pairs at 1.00×, 1.05× and 1.08× added lines, with the effort claims registered
on cost in advance, came back flat on all three contrasts — so "the crux is
harder" and "the crux is bigger" have been separated once and the rung signal
went with size. §30 rules accordingly: the promotion above stands as a
description of round 2's two pairs, and no recommendation inherits it.]

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
[Dropped, by #41. The identifiability problem this paragraph raises turned out
to be decisive rather than a caveat — the pair §23.5 asks for would move K1
and K11 together, which the task-set lint refuses outright — and the
retirement is argued in full there. The four tasks stay in the set as data;
the counter stays at silent 1 of 2, where §19 put it.]

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

[All three conditions met by #41, and the registered readings are at §23.7.
Four new tasks as two dense/calm pairs on one pysm snapshot; the two dense
members register `pair, cost, 1.25×` before the run, which is neither the 1.5×
this paragraph forbids nor any other number K7 has produced; and the control
is size-matched by byte-identity of `repo/` rather than by approximation, with
added lines matched to 10% on top. One condition of this paragraph is
superseded rather than met: (b) asked for 3 graded tasks at the dense level so
the **rung** min-n guard would admit K7, and #37's amendment has since made
that unreachable — an unenumerated ladder reads not assessable on the rung
whatever the sample. The round-3 tasks clear the count anyway (4 graded, 2 of
them dense) and the evidence runs entirely through the claims.]

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

  [**Flat again, and demoted — the condition fired.** #40 built round 3's K12
  tasks to the conditions §23.6 set, and the round came back flat anyway, so
  the counter reads silent 2 of 2 and `reconcile-v1` computes the demotion
  itself rather than a human ruling it. §26 records it, together with the
  qualification #40 carried on the floor and the fact that the negative lands
  on the cost claims and not on the rung ladder: sweep round-3, 2026-08-08.]
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

  [And there it stops. #41 **retires K11** on the identifiability argument
  §23.5 records, so no round after round 2 asks it and this counter is the
  last one it will carry: silent 1 of 2, not a demotion. The four tasks stay
  in the task set as data.]

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

[**Ruled at §32**, on the condition §23.6 attached to a third `prose` miss and
after round 3 took the upward-bet ledger outside K1 from 0/14 to **0 for 18**.
The paragraph above is no longer an argument: the rung prediction stays
mandatory as the falsification record and is retired from selection, and
nothing may cite an author's rung bet as evidence that a task is hard.]

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

   [**Retired by #41, on identifiability and not on the counter.** K11 is
   dropped: no new K11 task is authored, no future round asks it, and the four
   tasks it already has stay in the set as the data they are — swept once,
   graded, read at §18 and counted at §19. The argument this candidate asked
   for is the one that retires it, and it is written out here because it is
   the whole of the case.

   **Why the pair cannot be built.** K11's lever is meant to be *when* a
   defect makes itself known: near, and the run that introduced it shows it;
   far, and it shows several calls or several runs downstream. What the four
   tasks actually varied is whether a clause-by-clause self-check written off
   the prompt's own bullets catches the planted bend, and §18's reading of the
   run logs is that it does — on all four tasks, on both models, with sonnet
   spending exactly five turns each time. To make the self-check *miss*, the
   author has to take the clause out of the prompt. A prompt with a
   requirement removed is a prompt at a different level of decision openness,
   which is K1's ladder — the one knob this experiment has actually validated
   (§12) — so the near/far pair candidate 5 asks for moves K1 and K11
   together by construction, and a contrast moving two knobs attributes its
   outcome to neither (§9, clause 3). Declared honestly, that pair does not even
   load: the **task-set lint holds a pair to exactly one varied knob**, and a
   near/far pair whose two members declare different K1 levels varies two.
   The lint cannot force the honesty — an author who wrote the same K1 level
   on both members would pass it — which is why this is recorded here as a
   verdict rather than left to the gate. What it comes to is that pairing K11
   is not merely expensive, it is unauthorable under the rule that makes a
   pair readable, and that is a stronger result than a second negative round
   would have bought, available without spending one.

   **What is not being claimed.** Not that detection distance is unreal. It is
   something architects experience and §9's list is right to name it. What is
   claimed is narrower and, being narrower, is the part that can be wrong:
   *this instrument* cannot separate detection distance from spec
   completeness, because its lever is the prompt and the prompt is K1's. A
   future round that wants the knob back needs a lever that moves when the
   failure surfaces while leaving the brief identical — a repository-side
   lever rather than a spec-side one — and that is a different knob from the
   one K11 was authored as. It would be registered as one, with its own
   ladder and its own contrast, rather than inheriting K11's counter.

   **The counter it retires on, stated so the record is not read as harsher
   than it is.** K11 stands at **silent 1 of 2** (§19, and §9's recomputation
   table), not at a demotion, and this retirement does not advance it.
   Retirement here is not a verdict the evidence forced; it is the author
   declining to spend a second round on a knob whose one counted round ran the
   wrong way and whose contrast cannot be built. Two weaknesses in that
   counted round are the reason the case is argued from identifiability rather
   than from the reading: all four claims used the frozen-baseline comparator,
   which §22.4 calls the weak form, and all four were registered on `turns`,
   the metric §9 stops defaulting to. Neither weakness is repaired by
   retirement and neither is needed by it.

   **What stays, and why nothing in code changes.** `KNOB_LEVELS` keeps `K11`
   with its empty ladder, and the four tasks keep their construction blocks
   and their registered claims. Removing either would rewrite history rather
   than record it: every counter in this experiment is *derived* — nothing is
   stored, `reconcile-v1` re-reads the artifacts on each run, and replay grades
   a logged diff against the task's own declarations — so a retired knob
   deleted from the registry would leave the report unable to read its own
   past. What makes the retirement effective is the authoring side: nothing
   new declares K11, so no round can put it to a registered contrast, so its
   counter cannot advance. What it prints is **silent 1 of 2** for good — not
   §9's clause 6 **stalled**, which is reserved for a knob with no counted
   round at all, and K11 has one. The mechanism is clause 6's, the state is
   not: a counter is frozen here by the same absence of contrasts that leaves
   an unasked knob stalled, but it is frozen one round into a count rather
   than at zero. Which is why the retirement has to live here in prose. A
   frozen counter cannot tell the difference between a knob nobody has got
   back to and a knob that was argued out, and this one was argued out.

   **Precedent, and how this differs from it.** K8's demotion (§13) is the
   other verdict in this document that the counter does not reproduce: under
   the amended rule K8 also prints stalled, and §13 carries its demotion as a
   recorded human verdict over two sweeps and an effort reading that ran the
   wrong way. K11's entry is written the same way and means something
   different. K8 was demoted for what it *did* — a lever measured moving
   difficulty downward. K11 is retired for what it cannot be *shown* to do
   separately from K1, which is a claim about the instrument rather than about
   the world, and would be answered by a better lever rather than by more
   sweeps of this one.]
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

   [**Swept, and every reading registered above came due.** The family came
   back flat at haiku-solvable×4 with 0 of 3 contrasts separating and 0 of 4
   claim readings hitting, which is K12's second silent round and its
   demotion (§25, §26). Both cost claims came back *below* parity in the
   ladder's direction — `-c4` at 0.96×/0.90× and `-c2` at 0.61×/1.04× — so
   the outcome this entry called the one that plainly keeps K12 non-silent
   did not occur, and the pre-discount registered on `-c2` applies as
   written. `prose` missed a third time; the reading fixed here for that is
   in force at §28.]
7. **K7: register claims or retire it.** New tasks, effort claims registered
   before the run, at least 3 graded tasks at the dense level, and the
   size-matched control §12 asked for in round 1. It is the largest effort
   effect ever measured here and the only activated knob carrying no claim.

   [**Shipped by #41 as two pairs on one substrate, and the rung is not the
   channel.** Four new tasks for this round's sweep, each pair one
   dense-terrain task and the calm-terrain control built beside it. §12's
   outstanding condition is met in its strongest available form, and §18's
   three are met but for one that has since been superseded — the note there
   says which and why.

   **The contrast, and why it is the control §12 asked for.** Round 1's two
   K7 cells are the only ones in the corpus on a large vendored repository, so
   their multiples against the frozen feature-dev baseline conflate invariant
   density with plain repository size — §12 recorded the confound and asked
   for a size-matched control, round 2 built none, and §18 ruled the knob
   stalled partly for that reason. A control on a *different* repository of
   similar size would have answered it approximately. These controls answer it
   exactly: each pair's two members start from the same pgularski/pysm
   snapshot at the same pinned commit, and the **pair lint holds `repo/`
   byte-identical across them**, so repository size is not matched to within a
   tolerance, it is the same bytes. What is left between the two members is
   where in the library the change lands.

   Dense is `pysm/pysm.py`'s transition machinery: the exit walk that pushes
   the leaf it left onto the leaf-state stack and every state it climbs past
   onto its parent's state stack, the entry walk that rebuilds its path by
   descending a `.state` the exit walk has just reset to `initial_state`, the
   root-only `_leaf_state` every handler's view of the machine goes through,
   and the three stacks a `StateMachine` carries of which only two are
   history. Calm is `pysm/builder.py`, a 105-line opt-in fluent helper that
   nothing else in the package imports, whose entire state is one dictionary
   from path tuple to state and whose every invariant is written in the file
   being edited. Neither snapshot carries a knob-setting edit — the density is
   the library's own, as round 1's was — which is also forced, since an edit
   would break the byte-identity the pair rests on.

   Calm is **local, not easy**: the chain control has to refuse a colliding
   name before it has added anything, and the rename control has to move every
   path running *through* the state it renames. Both are real slips and both
   are registered as careless-answer probes that must grade 0.0. A control
   that were merely trivial would make the pair a reading of task difficulty
   wearing a terrain label.

   **Size-matched, on §23.3's axis and by its test.** Reference added lines
   within 10% inside each pair, asserted by the suite: 31 against 29 (1.07×)
   for `pysm-reset`, 28 against 26 (1.08×) for `pysm-pushdown`. Same
   tolerance and same measurement as the K9 pairs, deliberately — two knobs
   read against one definition of "the same amount to write". Without it,
   "dense terrain costs more" and "the dense task was bigger" would be one
   measurement, which is the fault round 2's K9 result was rejected for
   (§18).

   **Prompt length is the axis one of the two pairs does not hold, and both
   ratios are on the record.** #39 made the brief's own length something a
   pair registers rather than something a reader has to measure, and the two
   readings here differ. `pysm-reset` is level at 310 words against 313, a
   ratio of 0.99, with the dense member the shorter of the two.
   `pysm-pushdown` is not: 328 against 255, a ratio of **1.29**, the widest of
   the nine pairs round 3 registers and carried by the member holding the
   claim, which is the direction that matters — a longer brief is a direct
   alternative explanation for a cost hit. [Seven when #41 wrote this;
   #42's two intensity-batch pairs bring it to nine, and neither of them
   disturbs the ranking below, because in both of them the member holding the
   claim is the *shorter* one — 0.98 for `pysm-trace` and 0.97 for
   `pysm-snapshot`. The count is corrected here rather than the sentence being
   rewritten, so that what #41 registered stays legible.] On that quantity — a
   registered effort claim carried by the longer-prompted member of its
   pair — 1.29× is the corpus maximum, and the whole ranking is short enough
   to print:
   `pysm-pushdown` 1.29, `bookcase` 1.25, `roll` 1.24, `digest` 1.22, `remit`
   1.20, `outage` 1.18, `dossier` 1.17, `nightbus`-withheld 1.11. Wider *raw*
   gaps do exist — `pricelist`-withheld at 1.49, round 1's `settleup` at 1.39,
   `album`-withheld at 1.30 — and not one of the three is precedent for a
   claim carried across a wide gap: `settleup` registers no effort claim at
   all, and the other two put their claim on the *shorter* member, where the
   gap cuts against the claim rather than for it. So this is the widest gap of
   its kind on record, and what retires it is not precedent but the
   arithmetic, registered in that task's own rationale and not close: 73 more
   words is 504 more characters, on the order of 130 input tokens added to
   what every turn re-sends, against the 42,900 input tokens per turn round
   1's pysm K7 cell measured on haiku and 48,000 on sonnet. That is three
   tenths of one percent of a turn's input against a claim needing
   twenty-five percent — roughly an eightieth of the gap. The confound is
   registered because it is real, and dismissed because it is two orders of
   magnitude too small to manufacture the effect.

   **The claims, and the argument that 1.25× is unfitted.** Each dense member
   registers `pair, cost, 1.25×` against the calm member beside it; the calm
   members register nothing, as §23.3's controls do. The numbers a fitted
   claim would have reached for are all on the record and none of them is this
   one: round 1 measured K7 at 3.7× turns, 5.1× cost and 8.6× input tokens on
   haiku and 2.0× / 2.2× on sonnet against the frozen baseline, with per-task
   turns of 2.65× (`pysm-remember-substate-history`) and 4.68×
   (`rbql-like-escape-wildcards`), and §18 names **≥1.5× on turns** as the
   claim that would have gone 4/4 and forbids registering it. Round 2 gave K7
   no tasks, so there is nothing since. 1.25× is the house factor — round 2
   registered it on turns, #39 and #40 carry it into round 3 on cost — fixed
   before K7 had a pair to be read against, and it sits **below every multiple
   K7 has ever produced**, which is the opposite of the direction fitting
   pulls.

   The factor is the weaker half of the argument and the comparator is the
   stronger. Every one of those multiples is read against the frozen zero-knob
   baseline: hand-authored repositories of a few hundred lines, run on an
   earlier CLI, content-matched to nothing. Not one of them measures dense
   terrain against calm terrain *inside one library* — which is precisely the
   quantity §12 said round 1 could not separate from repository size, and
   precisely what these four tasks bet on. There is no prior reading of that
   quantity at any factor, so no factor registered against it can be fitted to
   one. What would have been fitted is carrying 2.6–4.7× across from a
   comparison whose confound this pair exists to remove.

   **The rung will say nothing, and it is registered here rather than
   discovered at reconcile time.** K7 has no enumerated ladder in §9 and none
   in `KNOB_LEVELS`, so under the amended clause 2 neither `dense` nor `calm`
   is the harder level and both pairs read **not assessable** on the rung
   axis. #36's own spec review raised this and left the enumeration to a
   human; nothing here enumerates one, and the suite asserts the ladder is
   still empty so that the day somebody fills it, this reading is flagged
   rather than silently outdated. The whole of K7's round-3 evidence is
   therefore the four claim readings — two claims, two models — and the round
   is non-silent only if one of them hits. All four rungs are registered
   `haiku-solvable`, which is where round 1 actually put both dense K7 tasks
   after betting them a rung up, and where round 2's sixteen bottom-rung bets
   went fourteen of sixteen; four more upward bets would have been the
   fifteenth through eighteenth placings of a bet that stands at nought for
   fourteen outside K1 (§21). So: a flat rung result returns what was predicted and
   falsifies nothing, and all four claim readings missing makes K7 **silent 1
   of 2** — the first time in three rounds the knob has been able to lose
   anything at all, which is the whole purpose of the ticket.

   **The base rate this lane is entered on.** 1.25× on cost has a record here
   and the record is not neutral, so it is written down before the sweep
   rather than reconstructed off whatever comes back. Round 2's three K9 pair
   claims were registered on turns and went 3 of 3 on haiku (2.14×, 1.50×,
   1.50×) and 0 of 3 on sonnet (1.12×, 1.00×, 1.00×). Read on cost at the same
   1.25×, the same three pairs go 4 of 6 — digest 2.65× and 1.47×, dossier
   1.63× and 1.54×, outage 1.17× and 1.08× (§20) — so the metric these two
   pairs register on is the *easier* of the two at the identical factor, and
   the clearest case is dossier on sonnet, which spent the same five turns as
   its control and 54% more money. Three things then compound in the claim's
   favour and are stated as such: clause 3 makes the round non-silent on one
   hit on either model, so four readings are four chances at one thing rather
   than one test; the factor is the house 1.25× rather than anything reached
   for; and the four readings are not four independent shots, because both
   dense sites are the same machinery, so the correlation that stops two hits
   from being two results also makes one hit likelier than four coin flips
   would suggest. Non-silence is therefore cheap here, and the honest reading
   is pre-committed: **a bare hit at around 1.3× is a small result, not a
   replication of round 1.** On the metric these claims register, round 1's
   K7 cost multiple was 5.1× on haiku and 2.2× on sonnet, and §12's whole
   objection is that most of that was repository size — which these pairs hold
   byte-identical. A 1.3× that clears the bar says the terrain is worth
   something once the confound is removed; it does not say round 1's number
   survived, and nothing in a later round may cite it as though it did. What
   would be a real result is a multiple that stays large with size held: 2× or
   better on both models, or 2× on haiku with sonnet at **1.5× or better**.
   The second branch carries a number now, before the sweep, so that "within
   reach" cannot be settled afterwards against whatever sonnet happens to
   return; 1.5× is set where round 2's K9 pairs already landed on sonnet at
   this metric — 1.47×, 1.54×, 1.08× (§20) — so it is a bar the corpus has
   been at rather than one invented to be clearable.

   **Two caveats recorded before the sweep, so they cannot be invented after
   it.** *One substrate, not two.* Both pairs sit on pysm, so this round
   replicates the dense/calm contrast twice inside one library rather than
   once in each of two. That buys the cleaner reading — the two pairs differ
   only in the change asked for, where a pysm pair and an RBQL pair would
   differ in the library as well — and gives up the cross-substrate agreement
   §10 wants from K7, which round 1 had and round 3 does not. The trade was
   taken on authoring risk: RBQL's visible suite builds its fixtures with the
   unseeded global `random` (§15.5, and the seeding the harness injects into
   its throwaway copies), where pysm's 138 tests are deterministic and the
   library is small enough to be read whole. *And the two dense sites are the
   same machinery.* Both are the transition walks of `pysm/pysm.py`, so the
   four claim readings are not four independent draws: a model that reads that
   machinery well is likely to read it well twice, and two claims both hitting
   is closer to one result than to two. Read a hit as evidence about one
   terrain measured twice.]

   [**Swept: 2 of 4, and both hits are the one pair.** K7's stall ends and the
   round is non-silent. `pysm-reset` hit on both models at 1.75×/1.67× — the
   "small result, not a replication of round 1" this entry pre-committed to,
   since it clears 1.25× and neither branch of the real-result bar.
   `pysm-pushdown` missed both at 0.47×/1.07× and its calm control landed a
   rung *above* its dense member, which is weaker than the correlated-draws
   caveat above anticipated and is read at §25 under the discount that
   control's own rationale registered.]

   [**Ruled at §30**, on the reading above: the stall ends, K7 survives the
   first round in which it could lose anything, and round 1's 5.1× is not
   replicated.]
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

   [**K10 and K4 shipped by #42 as the intensity batch: one pair each, both on
   pysm, and the scale axis turned for the first time.** The "misleading
   neighbour" candidate stays parked, as the round-3 spec puts it out of
   scope. Four new tasks for this round's sweep. Neither knob has ever been
   swept at any level before, in any round, so everything below is a first
   reading and nothing in it can have been fitted to a measurement — which is
   a stronger version of the unfitted argument §23.7 has to make at length for
   K7, and it is the one advantage of a knob nobody has built.

   **The contrasts.** `pysm-trace` is K10: `pysm-trace-what-the-machine-did`
   at `wide` against `pysm-list-the-waiting-events` at `narrow`. The wide
   member adds a `trace` to `StateMachine` recording what was entered, exited,
   handled, deferred and thrown away, and the reference solution carries that
   one stated decision to **14 places in 3 modules**, 12 of them the same
   recording written again — ten a single appended line, the two that record
   thrown-away events four apiece — and the other two declaring the attribute
   and documenting it. What makes the repetition irreducible is the library's
   own shape: `pysm/aio.py` does not override the core's entry walk, exit walk
   and dispatching step, it carries its own copies of all three, and
   `pysm/queued.py` carries its own copy of the queue draining, so no amount
   of inheritance collects them across the three. (Within one module they do
   collect, and by rather more than the sentence above admits — see the
   ten-site floor below.) The narrow member is the same *kind* of
   change — two small methods mirrored across the package's two queued
   layers — at **2 places in 2 modules**. `pysm-snapshot` is K4:
   `pysm-refuse-a-snapshot-in-flight` at `wide` against
   `pysm-keep-snapshot-metadata-plain` at `narrow`. Both write into
   `pysm/serialization.py`, at 3 hunks and 2, and what moves is how far the
   author must read: the wide member's guard turns on `_is_processing`, which
   is defined in `pysm/queued.py`, defined again in `pysm/aio.py` by a class
   that extends `StateMachine` rather than the queued one, and defined nowhere
   in `pysm/pysm.py`, so the guard must tolerate its absence. The narrow
   member's every fact — the promise of plain data in `snapshot`'s own
   docstring, the function guarded, the exception raised — is in the file
   being edited.

   **The site count is asserted, not described.** K10 is "N consistent edit
   sites", and §23.7 records that K7's `dense` is free text nothing checks.
   This suite counts the hunks of each reference diff and holds the wide
   member to the ticket's 8–15 band and the narrow one to a handful; it also
   requires the wide member's `task.yaml` to argue, where a reader of the task
   alone would look, why the library forces the repetition — because fourteen
   sites a competent author could have written as one would be a badly
   factored solution rather than a wide task. The K4 wide member's `task.yaml`
   carries the ≥3-module walk in the same way, and the suite pins the three
   substrate facts the walk depends on, so the claim fails loudly rather than
   going quietly stale if the library is ever re-snapshotted.

   **Ten is the floor, and fourteen only the reference's count.** Registered
   here because the first version of this entry got it wrong in the direction
   that flatters the knob. The reference appends inline at every walk, but
   both large modules funnel their entry and exit walks through an `_on` —
   `State._on` in `pysm/pysm.py`, `AsyncQueuedStateMachine._on` in
   `pysm/aio.py` — so a solution recording at those two choke points collects
   three sites into one in each of them and comes to **10 hunks**. That
   solution was written out and graded during #42's fix pass: it passes every
   held-out test and leaves the repository's own 138 green, as it should. Ten
   is inside the ticket's 8–15 band and inside the band the suite asserts, so
   the level does not move; what moves is the *reason*. The irreducibility
   holds **across** modules and fails **within** them — three recordings
   inside one module collect, and the three-module spread does not, because
   `pysm/aio.py` and `pysm/queued.py` hold their own copies of machinery
   `pysm/pysm.py` also has. So what this pair carries is "one decision, ten to
   fourteen places, three modules, and no spelling reaching two", not
   "fourteen places, none of them collectible". The site-count assertion
   measures the *reference* diff and so passes unchanged either way; the prose
   around it, in the suite and in the wide member's `task.yaml`, is corrected
   to the ten-site floor.

   **What the K4 walk is not, and it is registered rather than discovered.**
   Two things shorten it, and both are written down here because a limit
   admitted before the sweep is evidence and one admitted after it is an
   excuse. This is K4's version of the caveat §23.3 records for K9's
   any-resolution property and §18.1 for its labelled cruxes — with a second
   shortcut beside the first, found in #42's review.

   *The prompt supplies two of the three steps.* Step 3 is in the brief
   verbatim — "the classic core never has it" — so `pysm/pysm.py` need not be
   opened to learn that the guard must tolerate the flag's absence. Step 2's
   operative conclusion is in the brief too: "every layer that runs events
   counts, and a graph that mixes plain core machines with ones that queue is
   judged by the ones that queue" is precisely the sentence that refuses an
   `isinstance` against `QueuedStateMachine`, so what `pysm/aio.py` supplies
   is the *evidence* for a conclusion already stated rather than the
   conclusion. The graph walk and the climb to the root are stated as well and
   are visible inside `pysm/serialization.py`, which already does both. What
   is left needing a read outside the edited module is **one identifier**: the
   name `_is_processing`, withheld deliberately and available only from
   `pysm/queued.py` or `pysm/aio.py`. So the ticket's "genuinely spanning ≥3
   modules" is met in the documented walk and in where the facts live, and
   *not* in what a solver is compelled to do; and the ticket's own framing of
   K4 as "a genuine hunt through three modules with a wrong turn in it" —
   which this note carried into its first registration of the batch, and which
   now survives below only inside the discount that retracts it — overstates
   the task. Nothing downstream may lean on that phrasing.

   The repair is registration and not prompt surgery, which was considered and
   rejected. The brief has to say those things to stay honest: withholding
   "the classic core never has it" would make the core's absence a planted
   crux, which is K9's mechanism rather than K4's, and would move a rung bet
   registered at the floor. A task whose honesty depends on saying what it
   says is a task whose limits belong on the record, not in the prompt.

   *And the defensive answer skips the third module entirely.* The walk is
   what a *confident* answer costs, not what a correct one strictly requires.
   An author who read `pysm/queued.py` alone and then wrote
   `getattr(machine, '_is_processing', False)` out of habit would pass every
   grading test without opening `pysm/aio.py`, because duck typing happens to
   cover the class they never saw. So the claim is narrower than "three
   modules are unreachable otherwise": it is that skipping the third costs you
   the ability to know you are right, and that the idiomatic non-defensive
   answer — an `isinstance` against the one class the short read turns up — is
   wrong, which is what the careless probe grades 0.0.

   Both shortcuts point where the claim was already pointed. A resolved run
   says little, since several roads reach it; **the cost claim carries the
   whole of the reading**, and it carries it a little less far than the
   ticket's framing of K4 implies. What is still true and still worth
   measuring is that the facts do live in three modules and the brief stands
   in for two of them, so a solver who trusts the prose writes the same lines
   off a much shorter read than one who checks it — and the price of checking
   is what this pair is pitched on.

   **The two pairs hold each other's knob still, as far as two pairs can.**
   K10 and K4 are adjacent and the batch is built so the readings do not
   collapse into one: the K10 pair moves the site count (14 against 2 as the
   references are written, 10 against 2 at the floor above) while
   both prompts name the modules to edit, and the K4 pair holds the site count
   nearly still (3 against 2, in one and the same module) while moving the
   reading. Neither is a clean instrument for the other knob, and neither
   claims to be. And the K10 pair does not hold K4's quantity still either:
   its wide member has to survey the walk machinery of three modules to place
   its recordings and its narrow member reads two methods, so read volume
   moves there as well as site count. What the K10 pair holds still is the
   *finding* — every module is named in both prompts, so nothing has to be
   hunted for — and not the reading. A K10 hit is therefore a reading on
   "carry one decision to many named places", which includes the cost of
   visiting them.

   **Matched the way #39 and #41 match.** Each pair's two members start from
   the same pysm snapshot byte for byte, so repository size is identical
   rather than similar; reference added lines are within 10% inside each pair,
   asserted by the suite — 24 against 26 (1.08×) for `pysm-trace`, 17 against
   16 (1.06×) for `pysm-snapshot`. Neither snapshot carries a knob-setting
   edit, so `modifications` is empty in all four: the width and the scatter
   are the library's own, and an edit would break the byte-identity the pairs
   rest on.

   **Prompt length runs the favourable way in both, which is the one axis
   these pairs did not have to argue.** In each pair the member holding the
   claim is the *shorter* of the two — 324 words against 331 for `pysm-trace`,
   299 against 307 for `pysm-snapshot` — so the gap cuts against the claim
   rather than for it, no defusing arithmetic is needed, and neither pair
   joins the ranking §23.7 keeps of claims carried across a wide gap. A suite
   assertion holds it that way, because a later edit to either prompt could
   turn it around silently.

   **One substrate, and the choice is recorded either way.** Both pairs sit on
   pysm, as #41's two K7 pairs do, so round 3 now puts eight of its tasks on
   one library. RBQL was weighed and declined for the same reason #41 declined
   it and for one more: §15.5 records that RBQL's visible suite builds its
   fixtures with the unseeded global `random`, and while the *harness* seeds
   the throwaway copies it runs a visible suite in, the agent's own copy is
   not seeded — so an agent checking its work against that suite can be told
   something different on two consecutive runs. Under a task whose entire
   evidence is a cost reading, that is noise in the measured quantity and not
   merely an authoring nuisance. What the choice gives up is the
   cross-substrate agreement §10 wants, and it gives it up for a second round
   running.

   **And it gives up more than that, which §23.7 names within K7 and this
   entry has to name across knobs.** §23.7 records that K7's two dense sites
   are the same machinery — both the transition walks of `pysm/pysm.py` — so
   its four claim readings are not four independent draws and two hits are
   closer to one result than to two. The same argument runs one level up and
   nobody has run it there. Round 3's four registered pysm cost claims — K7's
   two from #41, K10's and K4's from #42 — are all readings on the *same
   byte-identical snapshot*, so the independence assumption fails across knobs
   and not only within one. A single pysm-specific effect, a model that is
   expensive on this library's idiom or cheap on it, would push all four the
   same way and would be attributable at reconcile time to three different
   knobs separately. That is a live way to over-read the round: three knobs
   speaking together on one substrate is one substrate speaking, until a
   second substrate says the same thing. Reconciliation has no machinery for
   this — the flag is per knob per round — so it is registered here, and the
   reading it licenses is that agreement among round 3's pysm claims is weak
   evidence about the knobs and strong evidence only about pysm.

   **What the round can say, registered rather than discovered at reconcile
   time.** Neither K10 nor K4 has an enumerated ladder in §9 or in
   `KNOB_LEVELS`, so under the amended clause 2 neither `wide` nor `narrow` is
   the harder level and **both pairs read not assessable on the rung axis**,
   exactly as K7's do; the suite asserts both ladders are still empty so that
   the day somebody fills one, this reading is flagged rather than silently
   outdated. All four rungs are registered `haiku-solvable`, which is where
   round 1 actually put both of its dense K7 cells after betting them a rung up,
   and where round 2's sixteen bottom-rung bets went fourteen of sixteen. So
   the whole of the evidence is four claim readings — two claims, two
   models — and the round is non-silent for each knob only if one of that
   knob's two readings hits.

   **The base rate these two lanes are entered on, and the honest reading
   pre-committed.** 1.25× on cost went 4 of 6 on round 2's three K9 pairs when
   read post-hoc (§20), so the factor is not a stretch on this corpus, and
   clause 3 makes a round non-silent on a single hit on either model — two
   readings per knob are two chances at one thing rather than one test. Set
   against that: unlike K7, neither knob here has a prior effort effect of any
   size to replicate, so there is no number a hit can be said to have
   confirmed and none it can be said to have missed. **A bare hit at around
   1.3× is therefore a first reading and a small one**, and nothing in a later
   round may cite it as more.

   The ticket asks for predictions "expected to be beaten", and the reading
   taken of that phrase is on the record rather than assumed: it is read as
   the discipline of registering a bet you can lose and naming what would
   defeat it, which every rationale here does. It is not read as a
   requirement that some bet be aimed above where the corpus lands, because
   the only axis with room above the floor is the rung, upward rung bets
   outside K1 stand at nought for fourteen lifetime (§21), and buying a
   literal reading with a fifteenth would spend the round's falsification
   record on a bet that has never come in. The four rungs sit at the floor and
   are expected to be met; the two cost claims are the ones that can be
   beaten, and each rationale says what beating it would look like.

   What would be a real result is the same shape §23.7 fixes for K7: 2× or
   better on both models, or 2× on haiku with sonnet at 1.5× or better.

   **And the discount on each knob hitting alone, registered symmetrically.**
   Both are written against the corrected mechanisms above, which move the
   premise in both directions at once: K10 is easier than "fourteen
   irreducible sites" suggested, because a ten-site answer grades, and
   K4 is shallower than "a genuine hunt through three modules with a wrong
   turn in it" suggested, because the prompt supplies two of the three steps
   and the outside read reduces to one identifier. So neither wide member is
   the thing its first registration described, and neither hit is worth what
   an undiscounted reading would make it.

   *If K4 hits alone*, that is the less surprising of the two outcomes and is
   not the batch working. Its wide member still asks for a read the narrow one
   does not have at all, and — per §23.3's caveat, restated for K4 above —
   the cost claim is the only thing carrying it, so a lone K4 hit is one
   knob's first reading and nothing about K10.

   *If K10 hits alone*, that is likewise not the batch working, and the reason
   is the one the paragraph above on the two pairs records: the K10 pair moves
   read volume alongside site count, so a lone hit is consistent with
   "visiting three modules costs something" as much as with "carrying a
   decision to many sites costs something", and those are K4's mechanism and
   K10's respectively. A K10 hit read as coordination width specifically needs
   the K4 pair's reading beside it, which is exactly what a lone hit does not
   have.

   Neither discount is a reason not to run the batch; both are reasons no
   single hit may be cited later as more than a first reading of one knob.

   **And the failure this batch is most likely to record instead.** Every
   careless probe checked in for the two wide members omits the async layer —
   the K10 one leaves out a single one of the reference's fourteen sites, the
   K4 one asks `isinstance` against the class `pysm/queued.py` defines — and
   both grade 0.0 while leaving the repository's own 138 tests green. That is
   the mechanism each knob is named after, and it is also the reason a model
   could fail these tasks on the *rung* despite four floor bets: nothing the
   agent can run inside its workdir distinguishes a half-carried change from a
   finished one. If either wide member comes back unsolved, that is the
   registered explanation and not a fresh one.

   **One grading gap, found in review and closed at every site — and the
   first attempt at closing it shut one site of twelve.** The K10 prompt gives
   the trace to the root machine — "a nested machine's own trace stays empty
   however often its states are entered and left" — and a machine driven from
   its root writes `self.trace` and `self.root_machine.trace` into the same
   list. Every held-out case drove from the root, so a solution writing
   `self.trace` throughout recorded into the right list everywhere the suite
   looked and graded 1.0 with a stated rule broken. #42's fix pass added a
   case that initializes a nested machine, which closed the initial-path walk
   of `pysm/pysm.py`; measuring the other eleven recording places afterwards
   showed the substitution still grading 1.0 at every one of them, because
   `initialize` is not the only call that can be made below the root.
   `dispatch` is another, and each of the three modules holds its own copy of
   both — the same duplication the whole task is pitched on, arriving as a
   grading hole rather than as a cost. The final pass added five more held-out
   cases that dispatch to and initialize a nested machine in each layer, and
   the suite-side probe became a probe per place: all twelve now grade 0.0,
   while the reference and the ten-hunk collapse both pass the widened
   twenty-three. Legal to do on the grading side because the pair's
   byte-identity requirement is on `repo/` — the lint compares that and
   nothing else, and each member's `grading/` is its own file — so the control
   was not touched and the pair still holds. Recorded because a task whose
   grading was widened after authoring and before the sweep is a fact about
   the artifact, and because the general lesson is stronger than the first
   registration of it made out: wherever a prompt says "the root's" and every
   test drives from the root, the gap is not one site but every site, and
   closing the one review happened to find leaves the class open.]

   [**Swept: both knobs hit 2 of 2, and only K10 cleared the bar this entry
   set.** K10's `pysm-trace` returned 2.04× on haiku and 5.47× on sonnet, the
   corpus's widest effort separation and the first reading to reach "2× or
   better on both models". K4's `pysm-snapshot` returned 1.31× and 1.49×,
   which is the "bare hit at around 1.3×" this entry pre-committed to reading
   as a first reading and a small one that no later round may cite as more.
   Neither lone-hit discount applies, since both hit. The cross-knob qualifier
   this entry registered does apply, to K10's number above all, and it is
   carried beside the multiples at §25 and §27.]
10. **Not a round-2 candidate: the ceiling, commissioned by the round-3 spec.**
    Everything above this entry was recovered from round 2's evidence. This one
    was not — it is #36's US-13 and US-14, which ask for the top of the ladder
    to be built on purpose because §22.3 says the corpus has never had one, and
    it is numbered here so it sits with the rest of the round rather than
    because round 2 proposed it.

    [**Shipped by #43 as two composites and two headroom anchors, none of
    which advances any counter.** Four new tasks for this round's sweep, all
    four registered `unsolved`, none of them in a family or a pair, none of
    them carrying an effort claim.

    **The recipe, corrected against the record before anything is built on
    it.** The spec calls "intent-level spec × planted open decision ×
    substrate terrain" the only recipe that ever produced unsolved cells. It
    is not, and the correction matters because everything downstream would
    otherwise inherit a claim the artifacts do not support. The census is
    **four** cells and not three, and it is derivable from checked-in
    artifacts alone — `reconcile-v1` replays every logged diff, and the four
    tasks no model resolved are `settings-merge-layers-l2`,
    `duration-parse-written-l3`, `inventory-consume-lots-l3` and
    `calc-infix-evaluator`. [#43's first commits registered three, citing §14.
    That was wrong twice over: §14 sorts round 1's *prediction misses*, and a
    frozen zero-knob control registers no prediction, so calc-infix could
    never have appeared in it however carefully that section were read. The
    census belongs to `reconcile-v1`'s baseline rows, which report one
    unsolved cell among the eleven feature-dev controls, and that cell is
    calc-infix.]

    Three of the four are constructed, and those three are the ones with a
    shape in common: all hand-authored, all declaring K1 and nothing else, two
    at `intent` and one at `description`. The fourth was planted by nobody —
    `calc-infix-evaluator` is a control authored before the knob experiment
    existed, and it is the archetype the anchors are named after. **The
    corrected reading is stronger than the one it replaces, in the direction
    of this batch's own bets**, because the fourth cell sits on the axis the
    anchors bet: "How the thinking evolved" opens by reading the first sweep
    off the D-axes and records "calc-infix = highest D1 → only both-model
    failure". D1 is decision content — graded assertions on a stated /
    derivable / invented ladder — which is the width of what an answer has to
    get right, and width is exactly what an anchor is for. So the gap
    paragraph below, which records that §9's list has no knob naming width,
    now records something more useful with it: the width class already holds
    an unsolved cell, arrived at without any knob, and the anchors' unsolved
    bet inherits that record rather than standing on nothing. The
    narrower claim survives untouched and is what the composites lean on:
    neither K9 nor a vendored substrate has ever produced an unsolved cell at
    any level.

    So the constructed ingredient with a record is **K1 at intent**, and what
    a composite does is stack on it the two levers with the largest measured
    *effort* effects — K7's **5.1× cost** on haiku in round 1 (§12) and K9's
    **1.17–2.65× cost** on haiku in round 2 (§20). Both figures are cost on
    the weaker model, which is the comparison §20 settled on after finding
    that turns discriminated none of the three K9 pairs; #43's first commits
    put K7's cost multiple beside K9's *turns* multiple (1.5–2.1×) as though
    they were one series, and they are two metrics. That is a mechanism-based
    bet and not a replication, it is registered as such in both composites'
    `task.yaml` comments, and a later round may not cite the composites as
    "the recipe rebuilt" without this paragraph beside it.

    **The composites.** `pysm-work-out-a-way-there` gives `StateMachine` a
    `route(target)` that hands back the events which would put the machine on
    a state, or `None` where nothing does.
    `pysm-rebuild-a-graph-from-a-snapshot` gives `pysm/serialization.py` a
    `rebuild(data)` that builds a fresh graph out of a snapshot, so that
    snapshotting what comes back gives the snapshot back.
    Both declare `K1=intent, K7=dense, K9=single`. The
    briefs state what is wanted and no acceptance criteria beyond the
    interface, one refusal convention and the K9 label; the terrain is
    `pysm/pysm.py`'s transition walks in the first and the plain-data round
    trip's invariants in the second, neither restated in the brief; and the
    labelled open decision is which run of events comes back, and which of a
    machine's states becomes its initial one.

    **Both K9 cruxes are the weak form of §23.3's caveat and say so.** A
    named method resolves the first — breadth-first search over the graph's
    configurations — and the second's open decision is a *choice* the snapshot
    format leaves rather than an algorithm to invent, which is weaker again.
    So a resolved run on either says nothing about a decision recall cannot
    reach, exactly as `remit-pay-what-fits` and `roll-pick-from-bursts`
    concede. What the label buys is that the grading honours it: the held-out
    tests dispatch whatever route came back rather than comparing it with
    ours, and never ask which initial state was picked, only that the choice
    is legal.

    **The anchors, and why they declare a knob at all.** The ticket's framing
    was that an anchor follows `calc-infix-evaluator`, which carries no
    construction block. That is unavailable and the reason is the design's
    own: absence of the block *is* the zero-knob baseline's declaration,
    `BASELINE_TASK_IDS` freezes that set at the 22 tasks authored before the
    experiment, and the lint refuses a task outside it that declares nothing.
    So an anchor declares, and what it honestly declares is the level its spec
    is written at — `K1=acceptance`, every rule stated as a criterion.
    `sieve-select-what-matches` is a filter language over records with
    three-valued logic; `gauge-evaluate-in-units` is literally the calc-infix
    class with one axis added, an infix evaluator whose quantities carry
    dimensions the arithmetic has to carry through. Neither withholds
    anything. The difficulty bet on is the *width* of a closed contract, and
    §9's list has no knob that names width, which is recorded here as the gap
    it is rather than papered over by declaring a knob that sounds close. What
    the corrected census adds to that gap is the reason it is worth a lane:
    the width class is not an untested idea, because the one unsolved cell no
    knob accounts for is `calc-infix-evaluator`, which "How the thinking
    evolved" puts down to the highest D1 in round 1's set. The unnamed axis is
    the axis carrying the corpus's only knob-free ceiling reading, and these
    two anchors are a second and third attempt at that reading rather than the
    first. [Registered here because this is the paragraph the anchors' bets
    hang off: `sieve-select-what-matches`'s grading was tightened after its
    prediction was registered and before any sweep — a preserved-behaviour
    test over the four existing functions, and two field-name clauses the
    brief states and nothing graded — which enforces criteria the brief
    already sets rather than changing the contract, is legal only while the
    task is unswept, and raises what its `unsolved` is a bet about, which is
    the direction favouring the prediction and so is recorded here rather than
    left in a commit message.]

    **What that costs the calibration table, registered rather than
    discovered.** `calibrate-v1` keys a row on category × sorted profile, so
    both anchors land in `feature-dev K1=acceptance` beside round 1's four
    `-l1` variants, whose changes are a fraction of the size — 26 to 36 added
    lines, against 165 and 248 for the two anchors — and which all came back
    haiku-solvable. All six are single-file and hand-authored, so #38's mix
    disclosure prints `K1=acceptance: 6 single-file; 6 hand-authored`, under
    the heading for rows whose mix differs from the baseline's, since the
    controls this row is divided by are not all single-file. What the
    disclosure cannot do is the thing wanted here: six tasks alike on both
    disclosed axes come out as one line, so it separates the row from its
    denominator and does nothing at all to separate an anchor from an `-l1`
    variant. If the rung bets land, the row's floor moves to `unsolved` with
    no way for the key or the disclosure to say which tasks put it there.
    This is #40's pooling problem in a second place and it gets #40's answer:
    recorded here and in both anchors' comments, and asserted by
    the suite so it cannot drift into being a surprise. The composites have
    the opposite property and it is asserted the same way:
    `K1=intent,K7=dense,K9=single` is a key nothing else in the corpus has, so
    they are a cell of two rather than a contribution to somebody else's.

    **Counter-neutrality, and why it is structural rather than promised.**
    §9's amended clause 1 counts a knob's rounds off two things: a family or
    pair whose varied knob it is, and an effort claim registered on a task
    activating it and scored to it. None of these four declares a family or a
    pair, so `registered_contrasts` cannot see them; none registers an effort
    claim, so `claim_knobs` returns nothing for them. #43's suite asserts both
    against those two functions rather than against a restatement of the rule,
    over the whole task set rather than a subset, and separately asserts that
    nothing new declares the retired K11 and that the frozen baseline is still
    its 22.

    **No effort claim was registered, and clause 3 is the whole reason.** A
    baseline claim on a task activating several knobs is scored to *no* knob —
    one cost reading over K1, K7 and K9 names none of them — so a claim on a
    composite would have been a bet nothing could ever be attributed to. The
    anchors are the case that needed care rather than the composites: each
    activates exactly *one* knob, so a baseline claim on one **would** have
    scored to K1 and made it a registered contrast, giving K1 a counted round
    off a task built to measure the ceiling. That is the artifact verdict this
    round's whole amendment removes, arriving by the back door, and not
    registering the claim is what keeps it out.

    **Two of each, not three, and the arithmetic is the reason.** #36 budgets
    ~34–44 new cells for round 3. #39, #40, #41 and #42 have put 18 tasks in,
    which is 36 cells on two models; four more makes 22 tasks and 44 cells,
    exactly the top of the range. Six would be 48 and would spend a fifth of
    the round's budget past its own estimate on the lane with the poorest
    prior. Both acceptance criteria say "2–3" and this takes the bottom of
    the band deliberately.

    **One substrate again, and the part of §23.9's warning that transfers.**
    Both composites sit on the same pysm snapshot #41's and #42's pairs use,
    so round 3 now puts ten of its twenty-two tasks on one library. §23.9
    registers that a single pysm-specific effect would push the round's
    readings the same way and be attributed to three knobs separately — but it
    argues that about *cost claims*, and these composites register none, so
    the part that transfers is narrower and is stated rather than assumed:
    **two unsolved rungs on one library are one library's ceiling**, and no
    later round may read them as the corpus's until a second substrate says
    the same. RBQL was weighed and declined, and on a weaker ground than
    #41's and #42's: §15.5's unseeded visible suite is noise in a measured
    cost and there is no measured cost here, so what actually decided it was
    authoring risk on a 1,772-line engine nobody in this round had read.
    Declining for the weaker reason is recorded as what it is.

    **Four more upward rung bets, on a ledger that says they lose.** Upward
    rung bets outside K1 stand at nought for fourteen lifetime (§21) and these
    are the fifteenth through eighteenth. §23.9 declined to buy a literal
    reading of "expected to be beaten" with a fifteenth, and this entry buys
    four — the difference being that there the rung was structurally
    unreadable and the cost claims carried the lane, whereas here the rung is
    the *only* registered outcome and an unsolved bet is the only bet that
    measures a ceiling. The pre-registered reading, fixed before the sweep:
    **a beaten anchor is ceiling data and not a failure.** An anchor either
    marks where the ceiling is or discovers the ceiling is above it, and the
    second is the more useful of the two on a corpus where sixteen of
    eighteen tasks landed on the floor. The suite requires the phrase in every
    one of the four rationales, and requires each to name what would defeat
    it.

    **What a flat result would mean, taken now rather than after the fact.**
    If all four come back resolved, the reading is §21's, applied to the
    ceiling rather than to the instrument: this material has no headroom left
    at single-file scale, on a hand-authored module or on a vendored one, and
    the next anchor needs an axis other than width and a substrate other than
    a small library — which is a conclusion about where to build next and not
    a fact about these four tasks. If any comes back unsolved, what it
    measures is one cell of the ceiling and the composite's three knobs are
    not separable within it, by construction: that is the price of a composite
    and the reason it advances nothing.

    **Each careless probe stays invisible to the agent.** All four are checked
    in: the route search reading the destination off the configuration before
    the exit walk rather than after it, `rebuild` inferring which paths are
    machines from the shape instead of from the snapshot's own list, `NOT`
    spelled as Python's `not` so the unknown flips to true, and the unit
    arithmetic carried in written units rather than base ones. Every one grades
    0.0 and every one leaves the repository's visible tests green — asserted
    by the suite, because that is why these rungs are bet where they are:
    nothing the agent can run inside its workdir distinguishes a half-right
    answer from a finished one.]

    [**Swept: the ceiling was not reached, and all three scored bets lost.**
    `gauge` came back haiku-solvable, `sieve` and `pysm-rebuild` sonnet-only;
    `pysm-work-out-a-way-there` has no sonnet cell and scores nothing. The
    framing fixed here — a beaten anchor is ceiling data and not a
    failure — is the one the record takes, and the flat-result reading this
    entry registered is earned on the three cells that exist and left open on
    the fourth. §28 records it.]

## Round 3 verdicts — 2026-08-08

Round 3 (#36) is built and swept: instrument amendments (#37, #38), 22 new
tasks (#39–#43), one sweep (#44, sweep id `round-3`, 43 of 44 cells, one agent
version 2.1.226, $12.1969). Everything below is recomputable by
`uv run ai-bench reconcile-v1` over the checked-in artifacts, except the
per-cell turns and cost multiples, which are computed from the same run logs'
`turns` and `cost_usd` fields and are quoted here because the report groups by
neither. Nothing above is superseded; §9's knob list and its amended kill
discipline stand, with the readings below attached to them.

**What these sections are.** #44's sweep commit recorded the numbers and left
interpretation to whoever read the round. This is the other half of that, and
it is deliberately the narrow half: the round's outcomes, and beside each one
the reading §23 pre-committed to for the outcome that occurred, cited rather
than re-derived. Where §23 fixed a reading in advance and the case it named
came up, that reading is in force as something pre-committed to, not as a
fresh inference invented to explain the round. Where §23 fixed nothing, the
outcome is recorded and no verdict is written. Candidates for round 4 are not
in scope here, and nothing below changes a rule in §9.

### 24. What the round measured

Hit-rate 40/66 scored (60.6%) over the corpus; round 3's own 21 scored tasks
went **16/5 (76.2%)**, against round 2's 14/4 (77.8%) and round 1's 10/27
(37.0%). The twenty-second task, `pysm-work-out-a-way-there`, reads
`incomplete` rather than scored — haiku ran it, sonnet did not — and is
counted in neither figure.

The ladder stayed saturated. Eighteen of the twenty-one scored tasks landed
haiku-solvable, three landed sonnet-only (`pysm-rename-and-list-states`,
`sieve-select-what-matches`, `pysm-rebuild-a-graph-from-a-snapshot`), and
**none landed unsolved** — so after a round that bet four tasks at the top of
the ladder, the corpus's unsolved census is still the four round-1 cells §23.10
counted.

Per-cell effort. All nine of round 3's registered claims are pair claims on
cost at the house 1.25×, so the frozen feature-dev zero-knob baseline (haiku
9.82 turns / $0.0711, sonnet 6.45 / $0.1846, n=11) is comparator to none of
them and is repeated only for continuity with §17.

```
claim holder ÷ pair partner       knob  turns h  turns s  cost h  cost s  rung
pysm-trace-what-the-machine-did   K10     2.19x    3.00x   2.04x   5.47x  flat
pysm-reset-to-initial-states      K7      1.76x    0.88x   1.75x   1.67x  flat
pysm-refuse-a-snapshot-in-flight  K4      1.38x    1.33x   1.31x   1.49x  flat
pysm-push-and-pop-states          K7      0.28x    0.67x   0.47x   1.07x  control +1
bookcase-shelve-the-run           K9      2.80x    1.00x   2.66x   1.06x  flat
remit-pay-what-fits               K9      0.46x    1.60x   0.75x   2.04x  flat
roll-pick-from-bursts             K9      0.57x    1.00x   0.69x   1.05x  flat
nightbus-print-the-sheet-c4       K12     1.00x    0.83x   0.96x   0.90x  flat
nightbus-print-the-sheet-c2       K12     0.67x    1.00x   0.61x   1.04x  flat
```

"control +1" on the `pysm-pushdown` row is not a rung delta the report claims:
K7's ladder is unenumerated, so the report names neither member the crux and
reads no direction. The label is this section's, and what it records is that
the calm control landed a rung *above* the dense member it was built to sit
beneath. §25 reads that row.

### 25. Per-knob outcomes, beside the reading registered for each

**K10 (coordination width) — non-silent on its first counted round, 2 of 2
effort readings hit, and the only round-3 claim that cleared the bar §23.9 set
for a real result.** `pysm-trace-what-the-machine-did` against
`pysm-list-the-waiting-events`: **2.04× cost on haiku and 5.47× on sonnet**,
the widest effort separation the experiment has recorded. §23.9 fixed the bar
before the sweep — "2× or better on both models, or 2× on haiku with sonnet at
1.5× or better" — and this is the first reading in three rounds to reach the
first branch. Both rungs came back haiku-solvable, as both were bet.

Three things registered in advance travel with the number and none of them is
retracted by it. §23.9's ten-site correction stands: a solution recording at
the two `_on` choke points collects to 10 hunks rather than the reference's 14,
so what the pair carries is "one decision, ten to fourteen places, three
modules, and no spelling reaching two". §23.9's own account of what the pair
does *not* hold still stands too — the wide member surveys the walk machinery
of three modules while the narrow one reads two methods, so read volume moves
alongside site count and the hit is a reading on "carry one decision to many
named places, including the cost of visiting them" rather than on site count
alone. And §23.9's cross-knob qualifier applies to this number first of all,
because it is the number a later round will want to cite: all four of round 3's
registered cost claims read one byte-identical pysm snapshot, so agreement
among them is weak evidence about the knobs and strong evidence only about
pysm. 5.47× is one library measured once.

The pair of discounts §23.9 registered for a *lone* hit — K4 alone, K10
alone — is not the case that occurred: both knobs hit, so neither discount is
the one to apply, and the reason both were written is that the batch was built
so the readings would not collapse into one.

**K4 (read-set/write-set ratio) — non-silent on its first counted round, 2 of
2 effort readings hit, and the reading pre-committed for this size of hit is
that it is small.** `pysm-refuse-a-snapshot-in-flight` against
`pysm-keep-snapshot-metadata-plain`: **1.31× cost on haiku and 1.49× on
sonnet**. That clears the registered 1.25× on both models and clears neither
branch of §23.9's real-result bar. The reading §23.9 fixed for exactly this
outcome is quoted rather than re-argued: "a bare hit at around 1.3× is
therefore a first reading and a small one, and nothing in a later round may
cite it as more." Both rungs came back haiku-solvable, as both were bet, and
§23.9's two registered shortcuts — the brief supplies two of the walk's three
steps, and a defensive `getattr` answer skips the third module entirely — are
untouched by the result, so the cost claim carries the whole of the reading and
carries it less far than the ticket's framing of K4 implied.

**K7 (invariant density) — non-silent on its first counted round in three,
2 of 4 effort readings hit, and the two hits are one pair.** This is the entry
§23.7's caveat anticipated in shape and under-anticipated in degree, so both go
on the record together.

`pysm-reset-to-initial-states` against `pysm-chain-and-outline-states` hit on
both models: **1.75× cost on haiku, 1.67× on sonnet**. Like K4's, it clears
1.25× and clears neither branch of the real-result bar, so §23.7's
pre-committed reading is the one in force: "a bare hit at around 1.3× is a
small result, not a replication of round 1", against round 1's 5.1× on haiku
and 2.2× on sonnet, most of which §12 attributes to repository size that these
pairs hold byte-identical.

`pysm-push-and-pop-states` against `pysm-rename-and-list-states` missed on both
models, and missed in a way the caveat did not reach. The dense member came in
at **0.47× cost on haiku** — it ran less than half as expensive as the calm
control built to sit beneath it — and at 1.07× on sonnet. Its rungs went the
same way: the *control* landed sonnet-only while the dense member landed
haiku-solvable, so on this pair the calm terrain outranked the dense terrain on
both axes the round reads.

What §23.7 registered was that two hits would be closer to one result than to
two, both dense sites being the transition walks of `pysm/pysm.py`. The actual
is weaker than that: one pair hit and one pair failed in the opposite
direction, so the round's K7 evidence is a single pair reading 1.7×, with its
sibling reading below parity on the same machinery. The control's own
registered rationale pre-committed the discount for precisely this, and it is
quoted here because it was written before the sweep — "if this one lands
anywhere but the bottom rung, the pair is measuring how hard the task was
rather than how dense the terrain is, and the round's cost reading should be
discounted accordingly." It landed above the bottom rung. The discount is owed.

One confound is retired by the result rather than argued away. `pysm-pushdown`
carried the corpus's widest prompt-length gap on a claim held by the *longer*
member — 1.29, the ranking §23.7 prints — and it is the pair that missed, so
the confound cannot have manufactured anything here. §23.7's arithmetic for
dismissing it is untested by round 3 and remains as registered.

**K9 (crux depth) — non-silent, 2 of 6 effort readings hit, no registered
contrast separated, and the counter stays at silent 1.** The three round-3
pairs — `bookcase`, `remit`, `roll` — all came back flat on the rung, so round
2's digest and dossier separation did not replicate on new pairs. On cost at
1.25×: `bookcase-shelve-the-run` hit on haiku at **2.66×** and missed on sonnet
at 1.06×; `remit-pay-what-fits` missed on haiku at 0.75× and hit on sonnet at
**2.04×**; `roll-pick-from-bursts` missed both at 0.69× and 1.05×. No pair hit
on both models, and the two hits are on different models of different pairs.

What round 3 bought here is the condition §18 attached to K9 and §23.2/§23.3
shipped: the volume confound is broken (added lines matched within a pair at
1.00×, 1.05× and 1.08×) and the cost claims were registered in advance rather
than swapped in post hoc. With volume matched and the metric pre-registered, no
rung moved and two of six readings hit. §18's caveat said no recommendation may
inherit K9's round-2 result until this was done; it is done, and what it
returned is recorded here for whoever rules on the knob. [Ruled at §30: the
condition discharges into a negative, and K9's rung lever is not usable for
selection.]

**K12 (decision conveyance) — silent 2 of 2, demoted.** §26 carries the ruling.
The outcome: all four `nightbus` rungs landed haiku-solvable, 0 of 3 registered
contrasts separated, and 0 of 4 registered effort readings hit.

§23.6's caveats travel with the demotion, because they say what kind of
evidence produced it and the note pre-committed to recording them.

*The rung axis could never have falsified here, and §23.6 said so before the
sweep.* Three of the family's four rungs were registered at the floor, so a
flat return at haiku-solvable×4 "has returned exactly what was predicted for
three of its four members, and the rung cannot falsify the ladder off that".
§18's objection — a ladder cannot show an ordering when every rung is the
floor — was live going in and is live coming out.

*The cost claims carried the round and lost, and in the ladder's own direction
they came back inverted.* §23.6 named `-c4`'s claim as "the one carrying the
contrast": prose against unmentioned returned **0.96× on haiku and 0.90× on
sonnet** against a claim needing 1.25×, which is prose costing *less* than
unmentioned on both models. `-c2`'s stated-pair claim, pre-discounted two
paragraphs earlier in §23.6 as a bet against all four of round 2's readings,
returned 0.61× and 1.04× — and §23.6 fixed the reading that "if that claim
misses it is not news", so the record takes it as no news. Three of the four
readings landed below parity.

The demotion is what §9 clause 5 computes off a second silent round and it
stands as computed. What this entry adds is only the shape of the evidence
behind it: a family whose ladder the rung axis could not test, and whose
carrying claims came back on the wrong side of 1.0.

**K1 (decision openness) — no counted round, informational only, and that is
clause 1 working.** Round 3 varied no K1 family, so the report prints round 3's
K1 row as informational and not assessable — acceptance {haiku-solvable,
sonnet-only} against intent {sonnet-only}, with intent holding 1 graded task
against acceptance's 2 distinct rungs. The counter stays where §9's
recomputation left it, at 0 silent over 1 counted round. This is the artifact
§22.1 named and §23.1 amended away: tasks declaring K1 ran in round 3 and K1
was not tested by them. §23.10's counter-neutrality construction is the other
half — the two anchors each activate exactly one knob, and registering a
baseline claim on either would have handed K1 a counted round off a task built
to measure the ceiling. None was registered, and no such round appears.

**K8 and K11 — untouched.** Round 3 asked neither. K8 stays stalled under the
amended counter with §13's human demotion standing beside it; K11 stays retired
by #41 at silent 1 of 2.

### 26. Kill-discipline ruling

Registered rule (§9, amended by #37): a knob silent for two counted rounds is
demoted, and the demotion names the rounds it counted with their dates.

- **K12: silent 2 of 2 — demoted.** The report prints it as
  `demote K12: silent in sweep round-2 (2026-08-06), sweep round-3
  (2026-08-08) — 2 round(s) against the 2 the kill discipline allows`. It is
  the first demotion this report has ever computed; §13's K8 demotion was a
  human verdict the amended counter does not reproduce. §19 conditioned the
  second round in advance — "flat again under those conditions and K12 is
  demoted with a real negative behind it" — and §23.6 set the conditions:
  raise the change's floor, close the docstring channel, register the effort
  claims in the ladder's direction on cost. #40 met all three, with the
  qualification §23.6 attached to the first of them — what was raised is the
  *change's* floor and not the ladder's — and the round came back flat anyway.
  The negative behind the demotion is the one §23.6 described in advance, and
  it is a negative on the cost claims rather than on the rung ladder, which
  three floor registrations left untestable.
- **K4, K7 and K10: first counted round each, all three non-silent, all three
  on effort.** K4 2 of 2, K10 2 of 2, K7 2 of 4; no registered contrast in any
  of the three was readable, because none of the three ladders is enumerated in
  §9 or in `KNOB_LEVELS`. Counters at 0 silent. K7's stall — recorded in §18,
  in §9's recomputation table and in #35 — ends here, and the note's own
  forecast in that table ("the next recomputation reads a counted round rather
  than a stall — the rung side stays not assessable while K7's ladder is
  empty") is what the report now prints.
- **K9: non-silent, counter stays at silent 1.** Two of six effort readings
  hit; no contrast separated.
- **K1: no counted round in round 3.** Counter unchanged.
- **K8: stalled, 0 silent. K11: retired at silent 1 of 2.**

One property of the ruling is worth stating plainly because it is new: three
knobs took their first counted round this round and every one of them was
counted on the *effort* axis, with the rung axis unreadable in all three. Under
the unamended rule none of the three could have been counted at all. §23.8's
candidate — make effort the primary registered outcome — is what clause 3
already does for the counter, and round 3 is the first round where it was the
only thing keeping three knobs out of a stall.

### 27. The effort instrument's second reading

Forty readings of twenty registered claims across the corpus, **0 not
assessable**; lifetime hit-rate 11/40 (27.5%). Round 3's own nine claims went
**8 of 18 (44.4%)**, against round 2's 3 of 22 (13.6%).

Every round-3 claim is a pair claim on cost, and every round-3 hit is
therefore a pair reading. The corpus's baseline-comparator claims still stand
at 0 for 8, all of them K11's from round 2. Round 3 registered no baseline
claim at all, so §22.4's observation — pair comparators are the ones that
produce signal — is neither tested nor contradicted by this round.

**What the pre-registered metric swap actually bought.** §23.2 registered the
claims on cost rather than turns because §20 found turns quantized against
cheap comparators. Re-reading round 3's eighteen readings on turns at the same
1.25× changes **exactly one of them**: `pysm-reset-to-initial-states` on sonnet
reads 0.88× on turns and 1.67× on cost. Every other reading returns the same
verdict on either metric. That one reading is the difference between K7's
surviving pair hitting on one model and hitting on both, so the swap was not
decorative — but the honest size of the effect on this round is one reading in
eighteen, and §20's mechanism (cost accumulates work that happens inside a
turn) is confirmed once rather than replicated broadly.

**The cross-knob qualifier, carried beside the numbers.** §23.9 registered it
and it is repeated here because this is where a later reader will find the
multiples: round 3's four registered cost claims — K7's two, K10's one, K4's
one — all read the same byte-identical pysm snapshot, six of their eight
readings hit, and a single pysm-specific effect would push all of them the same
way while being attributed at reconcile time to three knobs separately. The
licensed reading is §23.9's: agreement among round 3's pysm claims is weak
evidence about the knobs and strong evidence only about pysm. Nothing here is a
cross-substrate replication, and §10 still wants one.

### 28. The prediction instrument

40/66 lifetime (60.6%), round 3's own 21 scored going 16/5. The five misses,
with their direction:

- `gauge-evaluate-in-units`: bet unsolved, landed **haiku-solvable** — two
  rungs down, the largest over-prediction in the round.
- `sieve-select-what-matches`: bet unsolved, landed **sonnet-only**.
- `pysm-rebuild-a-graph-from-a-snapshot`: bet unsolved, landed **sonnet-only**.
- `nightbus-print-the-sheet-c4`: bet sonnet-only, landed **haiku-solvable**.
- `pysm-rename-and-list-states`: bet haiku-solvable, landed **sonnet-only** —
  the round's only under-prediction, and it is a control nobody was measuring
  (§25 reads what it does to K7).

**The third `prose` miss, and the reading §23.6 fixed for it.** `nightbus-c4`
is the third time a K12 `prose` variant has been bet `sonnet-only` and come
back `haiku-solvable`; album's and pricelist's were the first two. §23.6 wrote
the reading down before the sweep and it is now the one in force, quoted so it
cannot be mistaken for hindsight: a third prose miss "would leave that ledger
still at zero after a round built specifically to give an upward bet room, and
at that point it stops being a fact about K12: it is the instrument reporting
that authors of this material cannot pick in advance which of their own tasks a
model will fail. The reading to take then, fixed now, is §21's — keep the rung
prediction as the falsification record it is and stop asking it to carry
selection." §21's conclusion is therefore carried forward as a pre-committed
one: the rung prediction stays mandatory because it is cheap and it is the
falsification record, and the effort claim is the load-bearing outcome.

**The upward-bet ledger outside K1: 0/18.** Round 3 made five upward rung bets
outside K1 — `nightbus-c4` at sonnet-only, and the four `unsolved` bets §23.10
counted as the fifteenth through eighteenth. Four were scored and all four
lost; the fifth, `pysm-work-out-a-way-there`, is `incomplete` and scores
nothing. So the ledger §21 recorded at 0 for 14 now stands at **0 for 18**,
with one bet unmeasured. No author has yet correctly predicted an upward rung
movement outside K1 in three rounds.

**The ceiling did not hold, and §23.10 said in advance what that means.** All
three scored ceiling bets lost. The pre-committed framing is §23.10's — "a
beaten anchor is ceiling data and not a failure" — and it is taken as written:
an anchor either marks where the ceiling is or discovers the ceiling is above
it, and round 3 discovered the second, three times.

The flat-result reading §23.10 fixed is the one that now largely applies, with
one honest gap. It was registered for "if all four come back resolved": that
this material "has no headroom left at single-file scale, on a hand-authored
module or on a vendored one, and the next anchor needs an axis other than width
and a substrate other than a small library". Three of the four came back
resolved, and the fourth is unmeasured on sonnet rather than unsolved — so the
condition is met on the three cells that exist and cannot be completed until
`pysm-work-out-a-way-there` has a sonnet cell. What the three do establish is
that neither of the two constructed routes to a ceiling reached one: the width
anchors on hand-authored modules (`gauge` at haiku-solvable, `sieve` at
sonnet-only) and the composite on the vendored library (`pysm-rebuild` at
sonnet-only) all resolved, and the round added no unsolved cell to a census
that still holds only round 1's four. §22.3 counted 7 of 45 constructed tasks
ever landing above haiku-solvable across two rounds; three rounds in, it is
**10 of 66 scored**, and the three round 3 added are `sieve`, `pysm-rebuild`
and `pysm-rename` — two of them ceiling bets that fell a rung short of their
own prediction, and the third a control nobody aimed there.

§23.10's narrower transfer of the substrate warning applies to what the
composites did produce. Two unsolved rungs on one library would have been one
library's ceiling, and the same holds for the one rung they actually
moved: `pysm-rebuild` at sonnet-only is a reading about pysm until a second
substrate says the same, and the composite's three knobs are not separable
within it by construction, which is the price §23.10 named for building one.

### 29. Anomalies and process, read

1. **The cross-round version boundary.** Round 3 ran entirely on
   `claude` CLI 2.1.226, verified before and after each of the four
   invocations, so no contrast *within* round 3 crosses a version. Round 2 ran
   2.1.223 and round 1 spanned 2.1.221–2.1.223, so every reading that compares
   round 3 against an earlier round crosses a boundary — including the two the
   sections above make: K9's round-2 rung separation against round 3's three
   flat pairs, and round 1's K7 multiples against `pysm-reset`'s. #44's commit
   body records the caveat; it is repeated here because this is where those
   comparisons are written down.
2. **One substrate under three knobs, one snapshot under four claims.** §23.9's
   qualifier, in force — see §27. Ten of round 3's twenty-two tasks sit on the
   same pysm snapshot, and every one of the round's registered cost claims is
   read on it.
   [Read that last clause as this entry's own heading scopes it and as §27
   writes it out, not as it stands alone: the four claims on the snapshot are
   the round's *terrain-knob* cost claims — K7's two, K10's and K4's. The
   round registered nine claims in all, and the other five, K9's three and
   K12's two, are hand-authored and read no pysm file. Corrected in the same
   form at §30 and §33 by #45.]
3. **K9's informational round-3 row is set arithmetic over the composites.**
   The report prints an informational `separated — none {haiku-solvable},
   single {haiku-solvable, sonnet-only}` for K9 in round 3 while the counted
   row reads 0 of 3 contrasts separated. The sonnet-only in that set is
   `pysm-rebuild-a-graph-from-a-snapshot`, a composite that declares
   `K9=single` alongside K1 and K7 and registers no contrast at all. This is
   §22.1's fault class in an informational row, which is exactly where §23.1's
   amendment put it: it advances no counter, and no reading may be taken off
   it.
4. **The per-run timeout was never calibrated, and round 3 is the first round
   to reach it.** `RUN_TIMEOUT_S = 600` entered the runner in #7 as one line of
   a generic "subprocess calls get timeouts" review fix, not as a measurement
   decision, and nothing has re-set it since. It is about six times round 3's
   own mean run (104.1 s), ten times the corpus's mean (56.7 s over 177 runs),
   and roughly twice the longest run ever logged — 311.2 s, which is the haiku
   cell of `pysm-work-out-a-way-there`, whose sonnet cell then became the first
   in the corpus's history to hit the ceiling and cost the round its only
   missing cell.

   The lesson for the next sweep is recorded in
   `docs/agents/sweep-protocol.md`, and it is not "pick a bigger number". The
   limits are set deliberately before the first paid run and **may be tiered by
   task class** — a ceiling task and a four-turn control are not the same
   measurement problem, and per-task limits are ordinary practice elsewhere —
   under two hard rules: every member of one contrast shares one limit, and the
   limits are registered per class up front rather than adjusted per cell
   mid-sweep. A limit that changes between rounds is a cross-round caveat,
   recorded the way a CLI version change is.

   Round 3's missing cell is accepted as it stands. The round is 43 of 44,
   `pysm-work-out-a-way-there` stays unswept on sonnet and reads `incomplete`
   throughout this record, and it may be swept in a later round under a tier
   limit set deliberately in advance. Such a cell would be measured under
   conditions its forty-three round-3 neighbours did not have, so it would
   arrive carrying the cross-round caveat rather than repairing this round's
   record.

   [Shipped by #50, and what shipped is a table rather than a number. The live
   runner takes each task's limit from one per-class table registered in code
   (`firstparty_v1.LIVE_RUN_LIMITS_S`), and `eval-v1` no longer has a
   `--timeout`: a limit an invocation can pass is a limit adjusted per cell,
   which is the second rule above. The key is the task's category, because the
   task-set lint already holds a family's and a pair's category constant, so
   for those two constructs the first rule holds by construction rather than
   by discipline — and only for them: a contrast whose members differ in
   category, such as round 4's locate/fix comparison over one planted defect
   (its members declared neither a family nor a pair for exactly that
   reason), is not held to one limit by this key, and tiering fault-location
   and bug-fix differently would confound exactly that comparison. The table
   registers nothing yet — every category falls back to the flat 600, so no
   cell of the corpus moves, and the first tier set deliberately is a commit
   made before the sweep that reads it. When one is set, the change travels
   exactly as this entry rules: a cross-round caveat recorded beside its round
   the way §29.1 records the CLI version boundary.]
5. **Process, recorded from #44.** The sweep itself held the round-2 protocol —
   detached worktree, guard backups, byte-for-byte blob comparison, normally
   named logs including the dry check, `--data` scratched throughout. Two
   pieces of residue from the session are recorded because near-misses belong
   on the record as much as incidents do. A `git stash -u` ran in the *shared*
   working tree during the review lane after both commits — the tree-snapshot
   class the protocol bans outright, and one whose reflog signature is
   `reset: moving to HEAD`. It was popped immediately and both untracked paths
   were restored; the committed run-log blobs were re-verified byte-for-byte
   against the guard backups afterwards and are intact, and no artifact was
   lost. And `data/unified.jsonl` was rewritten by a replay invoked without
   `--data`; the file is untracked, holds only round-1 records, and carries no
   round-3 leakage, but scratching `--data` is exactly what the sweep itself
   did for all four of its invocations and the replay should have done the
   same. Neither cost anything this time, which is the only reason they are
   anomalies rather than incidents.

## Round 3 rulings — 2026-08-09

§§24–29 recorded round 3's outcomes beside the readings §23 pre-committed to,
and stopped there on purpose: §25 says of K9 that what the round returned is
"recorded here for whoever rules on the knob". This is that ruling, for K9 and
for every other knob the round activated, together with the first published
reading of `calibrate-v1`'s table and the instrument-level conclusion the
prediction ledger has now earned.

**Where the numbers come from.** Counters, contrasts, claim readings and rung
predictions are printed by `uv run ai-bench reconcile-v1`; the calibration
table and its mix disclosures by `uv run ai-bench calibrate-v1`; both read the
checked-in task set and run logs and nothing else. Per-task and per-pair
multiples are the same run logs' `cost_usd` and `turns` fields, quoted the way
§24 quotes them because neither report groups by them. Nothing below is
re-derived from the artifacts that §§24–29 already read: where a fact was
recorded there it is cited, and where §23 fixed a reading in advance for the
outcome that occurred, the verdict takes that reading as pre-committed rather
than arguing it again. Nothing here amends §9.

### 30. Per-knob verdicts

A verdict here says what the knob is now good for, what may cite it, and what
it would take to move it — over and above the counter, which `reconcile-v1`
computes and no verdict may contradict. Two of this round's rulings were made
before this section: K12's demotion is computed by clause 5 and K11's
retirement was argued at §23.5. Both are read here, neither is re-litigated.

**K10 (coordination width) — the round's one positive result, and the only
reading in three rounds to clear a bar set in advance. Promoted to candidate
*effort* lever; not promoted to a profile dimension, and one library wide.**
`pysm-trace-what-the-machine-did` returned 2.04× cost on haiku and 5.47× on
sonnet against its narrow partner (§24), which is the first branch of §23.9's
real-result bar — "2× or better on both models" — met on the first try by a
knob nobody had ever built. That is worth stating without hedging, because
three rounds of this experiment have produced nothing else like it.

The hedges are the ones §23.9 registered, and they bound what the result may
be cited for rather than shading it. The pair does not hold read volume
still — the wide member surveys the walk machinery of three modules where the
narrow one reads two methods — so the licensed reading is §23.9's "carry one
decision to many named places, including the cost of visiting them", not site
count alone. The width it carries is the corrected one, ten to fourteen
places in three modules with no spelling reaching two, not the fourteen
irreducible sites of the batch's first registration. And it is n=1 pair, one
sweep, one byte-identical pysm snapshot shared with the round's three other
terrain-knob cost claims — K7's two and K4's — so §23.9's cross-knob qualifier
lands on this number first: 5.47× is one library measured once.

So the verdict is a promotion of status and not of authority. K10 may be cited
as the largest effort effect the corpus has measured under a matched pair, and
as the reason the width axis is worth a second round. It may not be cited as a
priced dimension of an ex-ante profile, because a single pair on a single
substrate prices nothing. What would change that is one thing and it is §33's
third and seventh candidates: the same contrast built again somewhere that is
not pysm. Counter: 0 silent, 1 counted round.

**K4 (read-set/write-set ratio) — survives its first counted round on a hit
its own pre-registration calls small, and the pre-registration governs.**
1.31× on haiku and 1.49× on sonnet clears the registered 1.25× on both models
and clears neither branch of the real-result bar, which is exactly the case
§23.9 wrote a reading for: "a bare hit at around 1.3× is therefore a first
reading and a small one, and nothing in a later round may cite it as more."
That sentence is the verdict. K4 is kept, non-silent, and is not a profile
dimension.

Two registered discounts stay attached wherever the number is quoted, because
both narrow what was measured. The brief supplies two of the three steps of
the walk the task is pitched on, and a defensive `getattr` answer skips the
third module entirely, so what the 1.31×/1.49× prices is the cost of
*checking* a conclusion the prose already states — not the hunt through three
modules the round-3 spec's framing described, which §23.9 retracted before the
sweep. Counter: 0 silent, 1 counted round.

**K7 (invariant density) — the stall ends, the knob survives the first round
in which it could lose anything, and the result is half of one pair.** Two
facts carry this and they point in opposite directions. K7 has been
unfalsifiable since round 1 — §18 ruled it stalled rather than silent, #35
recorded it, and §9's recomputation table forecast that round 3 would turn it
into a counted round. It did: one counted round, non-silent, 0 silent. That is
an instrument outcome and it is the ticket's, not the knob's.

The knob's own outcome is smaller than the count makes it look. Of four claim
readings two hit, and both are `pysm-reset` (1.75× haiku, 1.67× sonnet), which
clears 1.25× and neither branch of the bar — so §23.7's pre-committed reading
is in force verbatim: "a bare hit at around 1.3× is a small result, not a
replication of round 1." Its sibling `pysm-pushdown` missed on both models at
0.47× and 1.07×, and its calm control landed a rung *above* the dense member
it was built to sit beneath. That control's own rationale pre-committed the
consequence — "if this one lands anywhere but the bottom rung, the pair is
measuring how hard the task was rather than how dense the terrain is, and the
round's cost reading should be discounted accordingly" — it landed above the
bottom rung, and the discount is applied here rather than merely noted: round
3's K7 evidence is **one pair reading 1.7× on one site of one library**, with
its sibling below parity on the same machinery, and §23.7's own warning that
two hits would be "closer to one result than to two" turns out to have been
generous to a round that produced one.

What that settles and what it does not. §12's confound — round 1's 5.1× cost
on haiku conflating invariant density with plain repository size — is
answered, and answered against the knob: with `repo/` held byte-identical the
multiple falls from 5.1× to 1.75×. §31 says where a plausible share of the
rest sits, without decomposing round 1's number, which nothing can: the task
the 1.75× was read on costs $0.2873 on haiku against the feature-dev
baseline's $0.0711 mean, so `pysm-reset` prices at **4.04× a hand-authored
control** in absolute terms — most of that being the vendored library it sits
in rather than the density inside it, and 4.04× is within sight of 5.1× across
different tasks and a different CLI version. (Composing the pooled figures
instead — the calm side's 2.18× times the pair's 1.75× — returns 3.8, which
lands on the `K7=dense` row's printed 3.80×. That is the division §31 forbids
run backwards, and the agreement is a coincidence of pooling rather than a
confirmation: the dense row holds round 1's two cells as well as round 3's, so
it cannot corroborate a pair it only half contains.) Dense terrain is worth
something once size is held; round 1's number did not survive, and nothing may
cite it as though it had. K7 is kept, at 0 silent and 1 counted, with its rung
axis still unreadable and no enumerated ladder — the second of §33's
candidates.

**K9 (crux depth) — the condition §18 attached to round 2's result is
discharged, and it discharges into a negative. K9's rung lever is not usable
for selection, and no recommendation may inherit round 2's separation.** This
is the ruling §25 deferred, and the reason it can be made now is that the
round bought exactly what §18 demanded: added lines matched within each pair
at 1.00×, 1.05× and 1.08×, and the effort claims registered on cost in advance
rather than swapped in afterwards. §18's clause was "not usable for selection
until the volume confound is broken — round 3 must match added lines within a
pair (or vary volume orthogonally) before any recommendation inherits this."
Under those conditions three new pairs built to §18's surviving formulation
came back **flat on every rung**, 0 of 3 registered contrasts separating.

Round 2's +1 rungs came with cruxes writing 1.61× and 1.41× their controls'
added lines, and the pair that wrote *fewer* lines than its control was the
pair that stayed flat. That is the ordering §18.2 recorded and could not
break. Round 3 broke it, and with volume matched no rung moved. The
conservative reading — the one this verdict takes — is that "the crux is
harder" and "the crux is bigger" have now been separated once, and the rung
signal went with size. §18's "SURVIVES as a rung lever" is therefore narrowed
to a description of two pairs in round 2 that no later round may generalize:
the selection tool gets nothing from K9's rung.

The effort side is non-silent and is not more than that. Two of six readings
hit — `bookcase` at 2.66× on haiku (1.06× on sonnet) and `remit` at 2.04× on
sonnet (0.75× on haiku) — on different models of different pairs, with no pair
hitting both and `roll` missing both. Under clause 3 one hit on either model
makes the round non-silent and two do so twice over; under any reading aimed
at pricing a task, a scatter across opposite models is not a signal. The
counter stays at silent 1 of 3 counted rounds and K9 remains subject to the
discipline.

One reading runs the other way and is recorded as a hypothesis rather than
folded into the verdict, because it is n=1 and because §23.3 registered the
distinction before the sweep. Of round 3's three pairs only `bookcase` is the
strong form of the any-resolution caveat — next fit, first fit and the
fewest-shelves optimum all fail its stated width rule — while `remit` and
`roll` concede outright that a textbook method passes their grading suites
63/63 and 48/48. On §18's own surviving formulation, "a planted open decision
that no named method resolves", round 3 built one instance and two
near-misses. The one instance is also the pair with the round's largest K9
haiku multiple. That is one pair on one model and it is written here so that
round 4 can aim at it, not so that anything can be read off it.

**K12 (decision conveyance) — demoted, and the demotion is narrower than the
knob's obituary would be. What died is the effort claim; the ladder was never
tested.** The counter is computed, not ruled: `reconcile-v1` prints `demote
K12: silent in sweep round-2 (2026-08-06), sweep round-3 (2026-08-08)`, the
first demotion clause 5 has ever produced, and §26 carries it. This verdict
only says what a later round may do with it.

What the two rounds falsified is a registered bet about cost, twice, in both
available directions. Round 2 registered effort peaking at `unmentioned` — the
reading-burden order — and §18 records two facts about how that went which
this verdict must quote separately rather than compress into one. First, all
eight of the registered readings missed: four claims across two models, and
nothing hit. Second, on different measurements entirely, §18 took the withheld
pair itself — `unmentioned` against `prose`, both metrics and both models,
eight measurements — and found prose the costlier variant in six of them and
level in the other two, none leaning the registered way. The first fact is the
claim losing; the second is the direction it lost in, and of the registered
readings only the four on `-c3`, the `unmentioned` level the claim peaked at,
bear on that direction at all. Round 3 took the lesson and registered the
claims along the ladder on cost, and all four readings missed with three of
them below parity, `-c4`'s carrying claim at 0.96× and 0.90× against a claim
needing 1.25×. A knob whose effort signal has been bet on in both directions
and lost both times has been measured, and demoting it is what the discipline
is for.

What neither round tested is the rung ladder, and the record must say so
plainly or a later round will revive K12 by pointing at the gap. Round 2 came
back flat at haiku-solvable×4 with the crux stated in module docstrings at
every level; round 3 closed the docstring channel and raised the change's
floor, and three of its four rungs were still *registered* at the floor, so
§18's objection — a ladder cannot show an ordering when every rung is the
floor — was live going in and is live coming out. So the demotion rests on the
cost axis and on nothing else, and the ruling that goes with it is: **K12
returns only behind an underlying change whose rungs have room** — a change
that already resists haiku before K12 touches it at all, which on this corpus
is rare enough to be the harder half of the work: ten of sixty-six scored
tasks have ever landed above the floor and three have ever landed unsolved,
none of them constructed for this purpose. (The corpus's unsolved census holds
a fourth cell, `calc-infix-evaluator`, which sits outside that population as a
zero-knob control authored before the experiment — the distinction §23.10
draws.) What the ruling does not license is the inference in the other
direction: the ladder's being untested is a reason to demand such a change
before rebuilding the ladder, not a reason to call the demotion premature,
because what was demoted is a claim about cost and that claim was bet twice
and measured twice. Until then the prose-over-unmentioned claim of §9 stands
as registered, unfalsified on rungs, and demoted on the only axis anyone has
been able to read.

**K1 (decision openness) — no counted round, and the silence is clause 1
working as designed.** Round 3 varied no K1 family; the report prints an
informational, not-assessable row and advances nothing, and §23.10's
counter-neutrality construction kept the two anchors from handing K1 a counted
round off tasks built to measure the ceiling. The counter stays at 0 silent
over 1 counted round — round 1's four families, which remain the only
*validated* rung lever the record holds. They are not the only rung
separations it holds, and the counter prints the others: K9's `digest` and
`dossier` separated in round 2, which is part of why `reconcile-v1` reads that
round non-silent for K9, and the K9 paragraph above rules the two of them a
description of two pairs that no later round may generalize. Recorded as a
fact about the record rather than a verdict: the one knob whose rung lever
anything may be built on has not been asked a question in two rounds.

**K8 — stalled at 0 silent, with §13's human demotion standing beside it.
K11 — retired at silent 1 of 2 by #41, on identifiability.** Round 3 asked
neither and this section changes neither.

**And the property of the round that outranks any single knob.** Three knobs
took their first counted round — K4, K7, K10 — and all three were counted on
the *effort* axis, with the rung axis unreadable in all three because none of
their ladders is enumerated. Under the unamended rule none of the three could
have been counted at all, so #37's amendment is what kept them out of a stall;
under the amended rule they now sit in a state nobody chose, half-instrumented
by default. That is either the amendment working or three knobs permanently
unable to speak on the axis the framework was built around, and which of the
two it is depends on a decision no round can make for itself. It is the second
of §33's candidates and it is already an open question on #36.

### 31. The first calibration table, read

`uv run ai-bench calibrate-v1` publishes for the first time over the full
corpus: 89 tasks, 177 runs, **20 cells over two categories**, keyed
category × sorted knob-activation profile, and — for the first time — no empty
cell. Eighteen of the cells are feature-dev, one of which is the eleven-task
zero-knob denominator the other seventeen divide by; the two refactor cells
run on the same pattern over another eleven controls.

**The headline is that the biggest numbers in the table are not knobs.** The
four largest feature-dev multipliers on haiku are `K1=intent,K7=dense,K9=single`
at 6.84× (n=2), `K10=wide` at 6.40× (n=1), `K7=dense` at 3.80× (n=4) and
`K10=narrow` at 3.14× (n=1) — and every one of those rows is vendored, priced
against eleven hand-authored controls, because the corpus has no vendored
control anywhere. #38's disclosure prints the substrate mix under every such
row and its preamble says why there can be no better denominator: substrate
provenance is declared inside a construction block, and a zero-knob control
declares no construction block at all. The check that turns that caveat into a
measurement is already in the table: the *deliberately easy* sides of the
vendored pairs read 2.18× (`K7=calm`), 2.37× (`K4=narrow`) and 3.14×
(`K10=narrow`) on haiku, and 1.95×, 1.54× and 1.45× on sonnet. A calm 105-line
fluent builder in a vendored library, authored as the control that must not be
hard, prices at 2.18× the hand-authored baseline on haiku. **On this corpus
the substrate step is worth roughly 2–3× on haiku before any knob moves**, and
roughly 1.5–2× on sonnet. The knob effects measured inside those rows sit on
top of that step and are within-pair ratios: 1.31×/1.48× for K4 and
1.75×/1.67× for `pysm-reset`, with `pysm-pushdown` at or below parity on
0.47×/1.07× and K10 the outlier at 2.04×/5.47×. That is §12's confound with a
number on it, and it is the quantitative reason §30's K7 verdict reads the way
it does.

**The vendored rows are readable as pairs, which is how they should be read.**
Two members of one pair share a denominator, so dividing their cells returns
the pair multiple exactly: K10 is 6.40 ÷ 3.14 = 2.04× on haiku and
7.93 ÷ 1.45 = 5.47× on sonnet, K4 is 3.10 ÷ 2.37 = 1.31× and
2.28 ÷ 1.54 = 1.48× — §24's four numbers back, the last of them 1.49× before
the printed cells were rounded. Neither pair's reading is what its absolute
multipliers say. The one place this does not work is K7: its `dense`
row pools round 1's two cells with round 3's two, across two libraries and a
CLI version boundary, so 3.80 ÷ 2.18 is not `pysm-reset`'s 1.75× and must not
be quoted as it.

**Four pooling facts a reader of this table has to carry, three of them
registered before it existed.**

- *`K1=acceptance` at 2.06× describes none of its six tasks.* The row holds
  round 1's four `-l1` variants and #43's two anchors, and the split is not
  subtle: on haiku the four variants cost $0.0446–$0.0772 against a $0.0711
  baseline mean, pooling to 0.92×, while `gauge` and `sieve` cost $0.2622 and
  $0.3541, pooling to 4.33×. The printed 2.06× is a mean over two populations
  and sits near neither. §23.10 registered this in advance and #38's
  disclosure cannot fix it, because all six tasks are single-file and
  hand-authored and so come out as one mix line.
- *The same row's rung floor hides its hardest member.* It prints
  `haiku-solvable (n=6)` although `sieve` came back sonnet-only, because a
  floor is the *weakest* rung any graded member landed on — the claim that
  this profile has been solved that cheaply at least once, which is what a
  selection query can act on. §23.10 expected a landed bet to move the floor
  to `unsolved`; the more exact statement, now that the table exists, is that
  a floor only moves when *every* graded member moves, so a pooled row can
  keep a harder task invisible. That is the row-key question already on #36's
  thread arriving from a second direction.
- *K12's four rows each pool changes of 5, 9 and 32 added lines*, exactly as
  #40 registered. What survives the pooling is worth one line: all four sit
  *below* the baseline on sonnet (0.67×, 0.68×, 0.70×, 0.71×), and on haiku
  the spread runs 0.81×–1.19× with `criterion`, the easiest level, the most
  expensive of the four. Neither ordering is the registered one — the
  demotion in a third view.
- *K9's rows pool three rounds and both sides of the volume confound.*
  `K9=none` reads 0.74×/0.91× and `K9=single` 1.10×/1.29×, which divides to a
  tidy 1.49×/1.42× that means nothing: nine pairs across three rounds and more
  than one CLI version, round 2's cruxes writing 1.4–1.6× their controls'
  lines and round 3's matched to 10%. §30's K9 verdict turns on that
  distinction and the table cannot make it.

**The one rung the table has.** Nineteen of twenty cells floor at
`haiku-solvable`. The single exception is the composite row
`K1=intent,K7=dense,K9=single`, at `sonnet-only (n=1)` — one graded task,
`pysm-rebuild-a-graph-from-a-snapshot`, its sibling being the round's
incomplete cell, and its 6.84×/3.73× computed over n=2 on haiku and n=1 on
sonnet for the same reason. So the rung column of the corpus's first
calibration table is one value wide with a single n=1 exception, while the
cost columns run from 0.67× to 7.93×. **This corpus prices difficulty in
dollars and cannot price it in rungs**, which is §22.3's saturation finding
arriving as a property of the published product rather than as a complaint
about a sweep.

**The refactor category is one row.** `K8=misleading` at 1.11×/1.19× (n=7),
the only row in the table whose own mix is split on both disclosed axes
(4 single-file + 3 cross-file, 4 hand-authored + 3 vendored). Consistent with
§13's demotion and adding nothing to it.

**What the table refuses, and the two questions that are above it.** v1 prints
no number it did not measure: no interpolation between levels, no backoff to a
coarser key, no pooling across categories, and `-` plus a named reason
wherever a cell is empty — there are none today. The two known weaknesses are
disclosed by the tool and are decisions for a human, both already recorded on
#36 from #38's spec review: the row key is category × profile where the
actuarial-loop design of §4 fixes category × scope, and the feature-dev
denominator is 6 single-file + 5 cross-file while nearly every constructed
cell is 100% single-file, which biases those multipliers downward; and no
vendored control exists, so every vendored row prices somebody else's
repository along with the knobs. Nothing in this section leans on a multiplier
in a way those two would overturn — every reading above is either a
within-pair ratio, a cell-against-cell comparison sharing one denominator, or
an explicit statement that a pooled number describes nothing.

### 32. The prediction instrument, ruled

The facts are §28's: 40/66 lifetime (60.6%), round 3's own 21 scored going
16/5, five misses, and the upward-bet ledger outside K1 moving from 0/14 to
**0 for 18** with one bet unmeasured. §21 pre-committed the conclusion to draw
if a third `prose` bet missed, and §23.6 quoted it forward before the sweep.
It missed. The conclusion is therefore in force as something pre-committed:
**the rung prediction stays mandatory because it is cheap and because it is
the falsification record, and it is retired from selection.** No ticket, spec,
recommendation or profile may cite an author's rung bet as evidence that a
task is hard.

What makes this an instrument-level ruling rather than another calibration
note is that round 3's authors knew the ledger's state and could not beat it.
§23.9 declined to place a fifteenth upward bet precisely because the ledger
said it would lose; §23.10 placed four anyway, deliberately, with the
pre-registered framing that a beaten anchor is ceiling data and not a failure,
and three were scored and all three lost. Round 1's authors over-predicted,
round 2's were told so and under-predicted the two hardest things they built,
and round 3's — writing with both lessons in front of them — went 0 for 4 on
the only axis with room above the floor. An instrument whose users know its
bias and still cannot correct it is not miscalibrated; it is answering a
different question from the one being asked of it. The rationales stay good
mechanism descriptions, which is what §21 said and what round 3's five misses
confirm one by one: `gauge` bet unsolved on contract width and landed
haiku-solvable two rungs down, `sieve` and `pysm-rebuild` fell one rung short
of the same bet, `nightbus-c4` is the third `prose` miss, and the round's only
under-prediction is `pysm-rename-and-list-states`, a control nobody was
measuring, which is also the task whose surprise did the most damage (§30's
K7 verdict).

**The effort instrument, by contrast, is where the round's information is.**
Forty readings of twenty claims, **0 not assessable** across the two rounds
that have ever registered one — the instrument shipped in #30 for round 2 and
round 1 registered no effort claim at all — so it has never once failed to
return a readable verdict, which is the half of §20's validation that keeps
being confirmed. Lifetime 11/40 (27.5%); round 3's own nine claims went 8 of
18 (44.4%) against round 2's 3 of 22. Read against the registered rationales,
the misses sort cleanly and none of them is a surprise the record has to
absorb after the fact:

- The four K12 readings lost as §23.6 said they might, with `-c2`'s
  pre-discounted as "not news" before the sweep and `-c4`'s the real loss.
- The four K9 misses run from 0.69× to 1.06×, so on every one the crux came in
  *cheaper* than its control or within a few percent of it, and for two of the
  three pairs §23.3 registered the reason in advance — a textbook method
  resolves `remit` and `roll`, and a task a named method solves is a task
  whose cost the crux does not raise.
- `pysm-pushdown`'s two are covered by its control's own registered discount,
  applied in §30.
- The eight baseline-comparator readings, all K11's, remain 0 for 8. Every
  claim that has ever hit in this corpus is a **pair** claim: 11 of 32 pair
  readings against 0 of 8 baseline readings. §22.4 observed it after round 2
  and round 3, which registered no baseline claim at all, neither tested nor
  contradicted it. Whether that record should harden into a rule about which
  baseline claims are admissible, or whether clause 3's existing scoring is
  already enough, is a question about §9 and nothing here answers it — it is
  §33's ninth candidate.

One honest measurement of what the pre-registered metric swap bought, carried
from §27 because it belongs in an instrument ruling: re-reading round 3's
eighteen readings on turns changes exactly one verdict. The swap was not
decorative — that one reading is the difference between K7's surviving pair
hitting on one model and on both — and it is one in eighteen, so §20's
mechanism is confirmed once and not replicated broadly.

### 33. What round 4 should change (candidates, not tickets)

Listed, not started. Each of these needs `/grill-with-docs` or `/to-spec`
before it is work, and nothing below authors a task, a spec or a ticket.

1. **Set the per-tier run-time limits deliberately.** The project owner's
   direction, recorded on #36 on 2026-08-09 and anticipated by §29.4:
   `RUN_TIMEOUT_S = 600` is an uncalibrated convention from #7 and round 3 is
   the first round to reach it. Task tiers should carry different,
   deliberately-set limits, the way per-task timeouts are ordinary practice
   elsewhere. The two hard constraints this round's methodology imposes on any
   such design: every member of one contrast shares one limit, and limits are
   registered per task class before the first paid run rather than adjusted
   per cell mid-sweep. A limit that changes between rounds is a cross-round
   caveat recorded the way a CLI version change is.
2. **Enumerate the ladders for K4, K7 and K10 — or record that effort is their
   only channel.** The question #37's spec review put on #36 and nothing has
   answered. Under clause 2 an unenumerated ladder makes every contrast on
   these three knobs not assessable on the rung, which is why round 3 counted
   all three on effort alone (§30). Both answers are defensible and the cost
   of not choosing is that three knobs stay half-instrumented by accident
   rather than by decision.
3. **A second substrate, and a replication rather than a new lane.** Ten of
   round 3's twenty-two tasks read one byte-identical pysm snapshot, and so do
   all four of the round's terrain-knob cost claims — K7's two, K10's and
   K4's. §10 has wanted cross-substrate agreement since before round 1 and
   three rounds have not bought it. The candidate is specifically to rebuild
   an existing pair's shape on a second vendored library rather than to open a
   new knob there — the point is whether the reading transfers, and RBQL
   having been weighed and declined by all three of round 3's substrate
   tickets (§15.5's unseeded visible suite, and #43's weaker authoring-risk
   ground) means the substrate choice is part of the work.
4. **Name the width axis or rule it out of scope.** §23.10 records that §9's
   knob list has nothing naming the width of a closed contract, that the
   corpus's only knob-free unsolved cell (`calc-infix-evaluator`) sits on it
   as round 1's highest D1, and that both round-3 anchors bet on it and were
   beaten. Either it becomes a knob with an enumerated ladder or the note
   records that the ceiling is not being pursued along it.
5. **Calibration table v2: the row key and the missing control.** Both
   questions are on #36 from #38's spec review, and §31 is the reason they are
   now live rather than hypothetical — the table is published and its
   multipliers are being read. The cheaper half is a vendored zero-knob
   control, which would give every pysm row a same-substrate denominator and
   collapse most of §31's headline caveat; the larger half is whether v2 keys
   on category × scope as §4's actuarial loop specifies.
6. **K9's third round, or none.** Three counted rounds have produced one rung
   separation that did not replicate under matched volume and a 2-of-6 effort
   scatter across opposite models. §23.4's notice-the-crux variant — a planted
   decision that is *not* labelled — is the only K9 design that asks a
   question this corpus has not already answered, and §18.1 has wanted it
   since round 2. A fourth round of labelled-crux pairs is a candidate for
   deliberately *not* running.
7. **Replicate K10.** The one result that cleared a bar set in advance, at
   n=1 pair on one library, with read volume moving alongside site count by
   construction. A second K10 pair — ideally under candidate 3, and ideally
   one that holds read volume closer to still — is what would turn the
   corpus's widest effort separation into a reading about coordination width.
8. **Sweep the incomplete cell.** `pysm-work-out-a-way-there` × sonnet is the
   corpus's only unswept cell and the only run ever to hit the timeout. Under
   candidate 1's tier limit it can be swept legitimately, and §29.4 already
   fixes how it must be read: measured under conditions its forty-three
   round-3 neighbours did not have, so it arrives carrying the cross-round
   caveat rather than repairing round 3's record.
9. **Rule on baseline-claim admissibility, or record that clause 3 already
   settles it.** §32's standing fact is that every effort claim which has ever
   hit is a pair claim: 11 of 32 pair readings against 0 of 8 baseline
   readings, all eight of the latter K11's. One available answer is a rule
   that a baseline claim is admissible only where its task activates exactly
   one knob and no pair is authorable; the other is that clause 3 already
   scopes baseline claims narrowly enough and the 0-for-8 record is advice to
   an author rather than a rule on the instrument. Nothing in the corpus
   forces the choice, because the only baseline claims ever registered are
   K11's and §23.5 rules that knob's pair unauthorable — which is why this
   belongs on the candidate list under the same `/grill-with-docs` or
   `/to-spec` gate as the rest of it, and not in a verdict.

## Round 4 shape — decided 2026-08-12

§33 listed nine candidates and authored nothing. This section is the owner's
ruling on them, taken in a `/grill-with-docs` session on 2026-08-12. It settles
what round 4 *is* and turns most of §33's list into either adopted work,
superseded work, or work explicitly deferred. It authors no task, spec or
ticket: `/to-spec` and `/to-tickets` are still owed before any of this is work.

### 34. What round 4 is

**The round's subject changed, and that is the ruling §33 did not anticipate.**
§33's nine candidates all assume round 4 continues the knob experiment. It does
not. Round 4's subject is **which engineering actions the first-party corpus
covers, and how the ones it cannot currently grade get graded** — the knob line
continues only as instrument hygiene (34.6).

**34.1 The rung axis is conceded to the meta-aggregation layer.** §31's finding
that nineteen of twenty cells floor at `haiku-solvable`, and §32's 0-for-18
upward prediction record, are not treated as a corpus defect to be engineered
away. The three-layer split in `AGENTS.md` already assigns per-instance
quality separation to ingested public benchmarks — `swebench.py` reads
SWE-bench Verified's per-instance resolved/unresolved — and assigns to the
first-party corpus what second-hand data cannot give: cost, latency,
harness-versus-model attribution, and scenarios no public benchmark contains.
So the first-party corpus stops trying to separate models on solvability. Two
consequences, both recorded as rulings rather than deferrals: **§33 candidate 4
(name the width axis) and candidate 6 (K9's third round) are dropped** — both
exist only to push tasks up a ladder this corpus no longer needs to climb.

**34.2 The category vocabulary is wrong and is rebuilt first.** Round 4's first
work is not authoring tasks. Three defects, all in `CONTEXT.md`'s taxonomy v0
and `schema.py`'s `TaskCategory`:

- **Categories will name engineering *actions*, not ticket types.** A real
  ticket chains several actions — investigate, then edit, then test — and the
  present rule ("exactly one category, decided by the primary deliverable")
  discards every action but the last. Ruling: one benchmark task measures
  **exactly one action** (it needs one gradeable deliverable); a real ticket is
  a sequence of actions, and that relation is documented rather than keyed on.
  The per-task rule is therefore unchanged in force and changed in meaning.
- **`frontend-ui` and `infra-config` are not actions and leave the list.** They
  name *where* work happens, not what is done — one can fix a bug, add a
  feature or refactor in each. Keeping them beside actions forces a
  frontend bug fix to pick one of two boxes and pollutes the calibration row it
  lands in. They become an orthogonal annotation beside `scale` and `language`.
- **The action list is ten**: fix a defect, add a feature, refactor, author
  tests, comprehend code, locate a fault, review a diff, investigate and
  propose, decompose a requirement, optimise performance. The last five are all
  additions; four of them (`locate a fault`, `review a diff`, `investigate and
  propose`, `decompose a requirement`) have never existed here, and
  `codebase-comprehension` has existed since taxonomy v0 without ever holding a
  task — for the reason 34.3 gives.

**The sunk cost of this change is near zero today and grows monotonically.**
`data/classification-cache.json` holds four classified public instances (all
`bug-fix`); the 89 first-party tasks use two categories (71 `feature-dev`, 18
`refactor`). Nothing in the corpus needs reclassifying. That is an argument for
doing it now rather than an argument that it is free: `TaskCategory` is a hard
`Literal` in the record schema (ADR-0001), read by the classifier and by
`llm.py`'s prompt, so this is a code change, not a documentation edit.

**34.3 Actions divide into four grading heaps, and round 4 eats the first two.**
The division is by *deliverable*, and it explains the corpus's shape better
than any difficulty argument does:

| Heap | Actions | Grading |
|---|---|---|
| 1 | fix a defect, add a feature, refactor, author tests | **Exists** — held-out tests over the workdir diff |
| 2 | locate a fault, review a diff, locate-style comprehension | **New mechanism, same principle** — plant the ground truth, then check against it |
| 3 | investigate and propose, decompose a requirement, explain-style comprehension | **None** — no ground truth; needs a subjective grader, itself uncalibrated |
| 4 | optimise performance | **None** — needs a stable performance baseline, a third mechanism |

Heap 1's only gap is `bug-fix`, and round 4 fills it. Heap 2 is the round's new
capability. **Heaps 3 and 4 are deferred, not dropped**, and the reason is
recorded so a later round does not rediscover it: their deliverable has no
ground truth, so grading them means building a subjective grader *and* a
calibration experiment proving that grader is worth trusting — two new
instruments, where round 4 already carries one.

**34.4 A text deliverable becomes evidence by landing in the workdir.** Heap 2's
deliverable is prose, and the v1 stance is that a run's final message is
metadata and the workdir diff is the evidence. Grading the final message would
reinstate exactly the pattern-verified weakness v1 was built to replace.
Ruling: the task asks the agent to write a **structured answer file** in the
workdir (a located fault as file and symbol; a review as findings with
locations), and the held-out tests read that file and compare it to the planted
truth. Nothing in the provenance boundary moves — the diff is still the
evidence, replay is still exact, the verdict is still execution-verified.
**The free-text answer is archived alongside and excluded from the verdict**:
the run log already stores the final message, so this costs nothing but a
change of name — from metadata to an archived artifact the verdict does not
read — and it is the corpus a heap-3 grader would later be calibrated against.

**34.5 Scale: one action proves the mechanism.** Round 4's most expensive
assumption is not whether the tasks are good but whether plant-and-check grades
a text deliverable correctly at all — an agent can locate a fault correctly and
describe it at a different level of the tree than the planted answer, and be
marked wrong. §6's method is to kill the most expensive assumption cheapest and
first. So the new mechanism ships against **one** action, `locate a fault`
(the hardest ground truth in heap 2), alongside the `bug-fix` fill: roughly
twelve tasks, in the $6–10 band against round 3's $12.20. `review a diff` and
locate-style comprehension follow once real runs have exercised the mechanism.

**34.6 The knob line does hygiene only.** No new knob contrast is authored in
round 4. Three items from §33 are adopted, and they are adopted because the
round's own work makes them load-bearing rather than because the list contained
them:

- **§33 candidate 5's cheaper half — a same-substrate control.** The table is
  published and being read, and round 4 adds rows built on real libraries;
  without a vendored zero-knob control every such row keeps dividing by
  hand-authored controls and carrying §31's 2–3× substrate step inside the
  number.
- **§33 candidate 1 — per-tier run-time limits.** Now a requirement rather than
  a candidate: fault-location tasks on real repositories read widely before
  answering, and `RUN_TIMEOUT_S = 600` has already been reached once (§29.4).
  Its two constraints stand: one limit per contrast, registered per class
  before the first paid run.
- **§33 candidates 2 and 9 — the two rulings that cost nothing.** Whether
  K4/K7/K10's ladders are enumerated or effort is recorded as their only
  channel, and whether a baseline effort claim is admissible.

§33 candidates 3, 7 and 8 (a second substrate, replicating K10, sweeping
`pysm-work-out-a-way-there` × sonnet) are **not dropped and not scheduled**:
they remain the knob line's next work whenever it resumes, and candidate 8
still depends on candidate 1's tier limit.

### 35. What round 4's spec must settle

Decided above is the shape, not the design. Four questions were surfaced in the
same session and deliberately left to `/to-spec`, so that nothing below is read
as already answered:

1. **What the timeout tiers are keyed on** — the action, the substrate's size,
   or something else.
2. **Whether the `category` field is renamed.** Its meaning changes from ticket
   type to action; the field name is a separate call, and it is a schema field.
3. **Whether the `surface` annotation lands now or when a frontend or infra
   task first exists.** It is where `frontend-ui` and `infra-config` go, which
   argues for now; nothing would populate it beyond one value, which argues for
   later.
4. **The resolution of a planted fault's ground truth** — file, symbol, or
   line. This is 34.5's expensive assumption in one question: too fine a
   resolution marks correct answers wrong, too coarse grades nothing.

## Round 4 grading surface — ruled 2026-08-13

#47 through #50 shipped and are closed. The adversarial review of #49 found
the mechanism's plumbing sound and its *authoring surface* not, and #50's
found the limit key's guarantee written wider than it holds. Both findings
outran what #46 specified, so they came back here. This section is the
owner's ruling on them, taken in a `/grill-with-docs` session on 2026-08-13.
It authors no task: one ticket is owed, and it blocks #51–#56.

### 36. What a fault-location verdict has to earn

**36.1 The gate that protects a code task does not protect this one.** #46
said the must-fail-on-pristine invariant "needs no special case", and that is
true in the way that matters least: a pristine repository never carries an
answer file, so the check is unconditionally satisfied and therefore proves
nothing. Two fixtures demonstrated the cost, both linting clean and passing
every gate the corpus has. A grading test that never reads the key — `assert
ANSWER.json.is_file()` — graded a *wrong* answer resolved, and an *empty*
answer file too. And a task whose repository **contained no defect at all**,
keyed to a perfectly correct method, passed both must-fail-on-pristine and the
reference-solution gate. For a code task those two together prove the task is
real and solvable; for `fault-location` neither does.

Ruling: both holes close, by different means, because they are different
holes. *Does the grading test discriminate* is answered by **negatives the
lint runs through the real pipeline**. *Is there a fault here at all* is
answered by the **paired `bug-fix` member**, whose held-out tests must already
fail on the shared pristine repository under #51's own acceptance criteria —
a proof this round gets for nothing.

Rejected: deriving the key's ground truth from the fix's diff. It would tie
the claimed location to the demonstrated fault mechanically, which is
attractive, but it makes a fault-location task unlintable on its own, and the
two members are deliberately not a family or a pair.

**36.2 The pairing is a convention, and says so.** Nothing in the model
records that the two members belong together — #51 declares them neither a
family nor a pair, so the lint cannot see the relationship. Round 4 is safe
by ticket construction: each of #51–#56 authors both members from one
repository, so the `bug-fix` pristine gate always runs over the shared
terrain. Ruling: leave it conventional and **write the limit down** — a
fault-location task authored *alone* has no proof a defect exists in it. The
first such task is the trigger to revisit, and heap 2's remaining actions
(`code-review`, locate-style comprehension) are where it will arrive, since
neither has a paired member to borrow a proof from.

**36.3 The lint invents the negatives it can.** Given the accepted set and
the file it names, the lint can construct a near-miss with no help from the
author: take an accepted file, pick any symbol defined there that is *not*
accepted, write it as the answer, require unresolved. That single check kills
the blind grading test and the sloppier one that reads the file but not the
symbol. Ruling: the lint synthesises and requires unresolved for a **missing**
answer file, an **empty** one, a **malformed** one, and an **accepted file
with a non-accepted symbol**. The author supplies a `rejected:` set, required
non-empty, for the near-miss the lint cannot invent — the plausible wrong
*file*: the caller of the defective function, the module that looks
responsible. Judgement is spent only where judgement is required.

A consequence worth naming: the synthesised near-miss also forces the accepted
set to be honest about the file it names. If the synthesised answer is in fact
a legitimate description of the fault, the lint fails and the author adds it to
`accepted` — which is the expensive assumption of 34.5 being paid down by a
mechanism rather than by hope.

**36.4 The comparison is owned, and copied.** #49 shipped the key, the loader
hook and the lint, and left the comparison — the half that discriminates — as
a string constant in a test file that six authors would each hand-copy. Ruling:
ship `grading/_answer.py`, identical in every fault-location task, and have the
lint read the copies **byte for byte**. Read against bytes this project itself
owns (`ai_benchmark._answer`, via `answer_module_source()`) rather than against
each other — a *stronger* check than the family lint's, which compares each
member's tree against the alphabetically-first member's because that is the
only source a family lint has: a lone fault-location task has no sibling to
compare against. The two mechanisms differ for that reason; what they share is
only the motivation, self-containedness beating deduplication because copies
drift silently. The held-out test becomes a one-line assertion over it — and
#58 closed the gap this left unstated: the held-out test itself is shipped and
read back the same way (`grading/test_answer.py`, `answer_test_source()`,
`_answer_test_problems`), because shipping `_answer.py` byte-identical proves
nothing about whether a task's grading test actually calls it.

Rejected: generating the grading test from the key. It is the stronger
guarantee and it is new authoring machinery, which is precisely what 34.4 was
pleased to have avoided.

**36.5 What counts as the same answer.** Measured on #49's fixture, every one
of `total_with_tax` (the bare method name), `./pricing.py`, `"Basket "` and
`"Basket.total_with_tax()"` graded unresolved. Over six tasks that is a
false-negative floor, and it would read as models being bad at locating faults.
Ruling, now that 36.4 gives it one home: the answer is **exactly one (file,
symbol) pair and never a list** — breadth must not be rewarded. Surrounding
whitespace, a leading `./` and a trailing `()` are stripped, and a **bare
symbol matches the last dotted component** of an accepted one, so
`total_with_tax` answers `Basket.total_with_tax`. File and symbol stay
**case-exact**: Python is case-sensitive, and a case-insensitive match on the
grading side would make a verdict depend on the grader's filesystem — the same
defect that made a wrong-case *answer path* resolve on macOS and replay
unresolved on Linux.

A known consequence, inherent in the last-dotted-component rule this section
adopts and not caught by #58's lint either: in a file where two classes define
a same-named method, a bare answer meant for the wrong class still resolves,
because the rule reads only the last component and `_near_miss` has no way to
flag a symbol that already matches something accepted.

**36.6 What can be named.** `_defined_symbols` saw only `def` and `class`, so
a fault in a module-level constant, a dispatch table or a compiled pattern was
unkeyable — which would have quietly steered #56, whose defect is a wrong key
in a lookup. Ruling: **module-level assignment targets count as symbols.**

And the other direction stays shut: #46's prose allows an author to write down
"the enclosing class **or module**", but an accepted answer naming a file with
no symbol is refused. On repositories as small as this round's, a bare filename
is barely a location — it would resolve for an agent that located nothing,
which is 35's "too coarse grades nothing" arriving by the back door.

What is not bound at module level, and so cannot be keyed at all: a walrus
target, a `for` target, a `with … as` or `except … as` name, and an imported
name — a wrong import is a plausible planted defect, and none of these five
can name it. And a non-Python accepted file cannot be keyed at any level,
since `_defined_symbols` reports no definitions for a file it cannot parse as
Python — fine for round 4's stdlib-Python repositories, and worth knowing
before heap 2's substrates stop being that.

**36.7 Held out of the workdir is not held out of the machine.** The key is
verified absent from the agent's workdir — the run-time copy takes `repo/`
only and the overlay lands at grade time. It is also a plaintext file on the
same filesystem, and this project runs its agents under
`--permission-mode bypassPermissions`; §29 already records a sweep aborted
because a model read outside its workdir. The exposure is not new — every v1
task's held-out tests are equally readable — but the payoff is: for a code task
reading the tests still leaves the work, and here the key *is* the entire
deliverable, obtainable for nothing and leaving no trace, since the log stores
only the final message and the diff.

Ruling: **accept and disclose.** Hashing the accepted pairs was considered and
rejected as theatre — the (file, symbol) space of a small hand-authored
repository is enumerable, and the salt would ship with the key, so an agent
that reads the file can hash its way back to the answer. The only real fix is
running the agent where the checkout is unreachable, which belongs to the
runner and to every v1 task rather than to this round. So the glossary and this
section record what the word "held out" covers, and a fault-location verdict
carries the stated assumption that the agent did not read the key off disk.

**36.8 Round 4 registers no run-time limit tier.** §34.6 promoted per-tier
limits to a requirement on the grounds that "fault-location tasks *on real
repositories* read widely before answering". #46 then built this round on
hand-authored stdlib-only repositories — and deferred the same-substrate
control for exactly that premise failure, without noticing it applies here too.
It does. The stated case for tiering `fault-location` is about terrain this
round does not use.

The second reason is stronger. #50's key is the task's category, justified by
the lint holding category constant across a family and a pair — which it does,
and which does not cover the contrast this round exists to read: #51 declares
the locate and fix members neither a family nor a pair, precisely because they
vary no knob and *differ in category*. Tiering `fault-location` apart from
`bug-fix` would run the two sides of the round's headline comparison under
different ceilings. The obvious "free" move — register `fault-location` now,
since no such task exists yet, so no cell moves — is the one move that
confounds the reading the round is being swept to produce.

Ruling: `LIVE_RUN_LIMITS_S` stays **empty for round 4, by decision and not by
omission**, and the sweep protocol's step reads met rather than unmet. Round
4's own runs are the evidence for whether a tier is ever needed.

**36.9 The limit is narrated, not stamped, and that is enough for now.** A CLI
version change is recorded twice — stamped on every run row and narrated here.
The limit in force is narrated only: `Run` carries no limit field, so the log
cannot say which ceiling a row ran under. Every row in every round so far ran
at the flat 600 and round 4 will too, so this section determines it for any row
in the log. Ruling: **defer, with the trigger written down** — when the first
tier is registered, one sweep's rows will run under different ceilings and the
narration stops determining anything. Stamp the limit on the row at that point,
the way the sweep id was added.

## Round 4 run-time limits — ruled 2026-08-16

**37. §36.8 superseded: `bug-fix` and `fault-location` both register at 600.**
§36.8 left `LIVE_RUN_LIMITS_S` empty for round 4 because the case for tiering
`fault-location` was made for real-repository terrain this round does not use,
and because tiering it apart from `bug-fix` would run the round's headline
locate/fix comparison under different ceilings — #50's key guarantee (module
comment, glossary, sweep protocol, design note) holds "every member of one
contrast shares one limit" only for a family or a pair, and the locate/fix
contrast is neither.

That second reason rules out *different* values for the two categories; it
says nothing against equal ones. Registering both at the same number keeps the
guarantee true by equality rather than by omission, so it clears #50's
constraint without reopening it. This is the adjudicated move: `bug-fix` and
`fault-location` both register at **600** — the flat default's own value, so
no cell of the round moves and every row still runs, as §36.9 already says,
"at the flat 600". The nearest terrain with history, feature-dev over
comparable multi-module stdlib repos (141 runs), shows p90 133–143 s and a
historical maximum of 311 s (§23's reading of round 3, above); 600 s is
roughly twice that maximum and four times the p90, wide enough that the
unrecoverable direction — a clipped cell, unrepeatable because a task × agent
× model cell is swept once, and a clipped `bug-fix` member corrupting the
locate/fix reading itself — is the one this leaves no room for. The
recoverable direction, a runaway run burning bounded minutes, cost at most
$1.46 in the corpus's history.

Because the registered value equals the value every category already fell
back to, no cell runs under a different ceiling than it would have under
§36.8's ruling, and §36.9's stamping trigger — "one sweep's rows will run
under different ceilings" — is still unmet: this remains a narrated limit,
not a stamped one. And because the number in force does not change, this is
not a cross-round caveat under #50's rule: round 3 and round 4 both ran, and
run, at 600.

## Round 4 verdicts — 2026-08-16

Round 4 (#46) is built and swept: the taxonomy rebuild (#47–#50), the
fault-location grading surface (#58), twelve tasks over six planted defects
(#51–#56, #59, #60), the tier registration §37 ruled (#61), and one sweep
(#57, sweep id `round-4`, 24 of 24 cells, one agent version 2.1.233,
$3.2748). Everything below is recomputable from the checked-in artifacts:
the table in §39 by `uv run ai-bench calibrate-v1`, the verdicts in §38 and
§41 by re-grading each logged diff the way `eval-v1 --replay` does, and the
per-pair multiples in §40 from the three run logs' own `cost_usd` and `turns`
fields — quoted here because no report groups by a locate/fix pair, the two
members being deliberately neither a **task family** nor a **pair** (§37).
`tests/test_firstparty_v1_round4_record.py` pins every figure these sections
publish, and §42 is how the logs were shown to replay exactly.

**What these sections are not.** Round 4 registered no knob contrast — §34.6
ruled the knob line to hygiene only — so there are no per-knob verdicts to
write, no effort claim to grade, and no kill-discipline reading to take.
`reconcile-v1` counts the round in its round list (`5 round(s): … sweep
round-4`) and nowhere else: no knob's counter moves, and none is demoted or
advanced by this round. All twelve tasks are **declared controls**, which is
what a task authored to fill a **category** rather than to move a knob
declares. What the round bought is two categories the corpus could not
measure at all, one new grading mechanism exercised for the first time
against paid runs, and one comparison — locating against fixing — that no
earlier round could draw.

### 38. What the round measured

**The sweep.** Twelve tasks × the two ladder models = 24 cells, all swept,
none twice. One sweep id `round-4` and one agent version
`2.1.233 (Claude Code)` across all three invocations, the version re-checked
between them: `r4-a` is the dry check (`noticeboard-locate-the-lost-notice`
on haiku), written to a normally-named log as the protocol requires; `r4-b`
is haiku's other eleven; `r4-c` is sonnet's twelve. The sweep ran from a
dedicated worktree with guard backups kept outside it
(`~/sweep-backups/round-4/`, verified byte-for-byte against the committed
blobs) — the rule the #24 incident bought. All 24 cells logged a row, so none
was blocked by the environment: a run with non-empty `permission_denials` is
a broken run and fails loudly rather than logging a verdict.

**Cost, against the expectation stated before the first paid run.** Expected
**$5–8**, 24 cells priced at the nearest terrain's p90. Actual **$3.27** —
$0.9066 on haiku and $2.3681 on sonnet, $3.2748 in total — against round 3's
**$12.1969**. Per cell that is $0.1364 against round 3's $0.2837 over 43,
and the reason is terrain rather than thrift: round 3's cells were mostly a
vendored library, round 4's are twelve small hand-authored repositories, and
§31 put the substrate step alone at roughly 2–3× on haiku. The round came in
under a range stated in advance, which is worth exactly what it is worth —
an estimate honoured, on the cheap side, once.

**The limits in force.** #61 registered `bug-fix` and `fault-location` in
`LIVE_RUN_LIMITS_S`, both at **600 seconds** — the flat default's own value,
for the reason §37 gives: the round's headline contrast spans exactly those
two categories and tiering them apart would confound it, so equal
registration clears #50's constraint instead of reopening it. **No
cross-round caveat arises**: the number in force did not change, round 3 and
round 4 both ran at 600, and the limit stays narrated rather than stamped on
a row. Nothing came near it — the round's longest run was **101.4 s**
(`allotments-go-back-for-what-nobody-could-read` on haiku) and its mean
**51.4 s**, against a corpus mean of 56.1 s over 201 runs and a longest-ever
311.2 s. No cell was clipped, so no verdict in this record is a timeout in
disguise.

**Resolution: 21 of 24 cells.** haiku resolved **10/12**, sonnet **11/12**.
Per category and model:

```
                  bug-fix      fault-location
claude-haiku-4-5  4/6          6/6
claude-sonnet-5   6/6          5/6
```

The three cells that did not resolve are
`allotments-go-back-for-what-nobody-could-read` × haiku,
`lostproperty-write-up-what-happened` × haiku, and
`paperround-locate-the-carried-over-count` × sonnet. §41 reads each one.

**Rungs.** Ten of the twelve tasks came back `haiku-solvable`; two came back
`sonnet-only`, and both are `bug-fix` — the two haiku cells above. None
landed `unsolved`, so the corpus's unsolved census is still the four round-1
cells §23.10 counted, and its rung census now reads 85 `haiku-solvable`, 11
`sonnet-only`, 4 `unsolved` and the one `incomplete` cell round 3 left. The
two new `sonnet-only` tasks were authored to fill a category and declare
nothing about difficulty, which is the shape §34.1 predicted the corpus would
keep producing after it stopped trying to separate models: the separation
that arrives arrives incidentally.

**The corpus after the round.** 101 tasks, 201 runs, **22 cells over four
categories**, and still no empty cell — against §31's 89 tasks, 177 runs and
20 cells over two.

### 39. The two new categories' rows, as printed

`uv run ai-bench calibrate-v1` publishes them like this, quoted as printed:

```
category bug-fix
   baseline mean cost   claude-haiku-4-5 $0.0805 (n=6), claude-sonnet-5 $0.2128 (n=6)
   baseline mix         6 single-file; 6 hand-authored

   profile      tasks  claude-haiku-4-5  claude-sonnet-5  rung floor
   (zero-knob)  6      1.00x (n=6)       1.00x (n=6)      haiku-solvable (n=6)

category fault-location
   baseline mean cost   claude-haiku-4-5 $0.0706 (n=6), claude-sonnet-5 $0.1819 (n=6)
   baseline mix         6 single-file; 6 hand-authored

   profile      tasks  claude-haiku-4-5  claude-sonnet-5  rung floor
   (zero-knob)  6      1.00x (n=6)       1.00x (n=6)      haiku-solvable (n=6)
```

**Both multipliers are 1.00× by construction and neither is a reading.**
Every task in both categories is a declared control, so each row *is* its own
category's denominator, over n=6 tasks that ran each model. What these two
rows actually publish is the denominators — haiku $0.0805 and sonnet $0.2128
for `bug-fix`, haiku $0.0706 and sonnet $0.1819 for `fault-location` — which
is what a later constructed task in either category will be divided by, and
what a selection query reads as the price of the shape of work. The table
does what its own `refuses` preamble says and pools no category's controls
into another category's denominator: it will not divide `fault-location`'s
mean by `bug-fix`'s, which is why the locate-versus-fix reading is per defect
in §40 and not read off these two lines. (Dividing them anyway gives 0.88×
on haiku and 0.85× on sonnet; that is a ratio of means over two categories,
not a number this table publishes, and §40's per-pair medians are the reading
that survives the unresolved cells.)

**The `bug-fix` floor hides its two hardest members.** It prints
`haiku-solvable (n=6)` although two of the six came back `sonnet-only`,
because a floor is the *weakest* rung any graded member landed on — the claim
that this profile has been solved that cheaply at least once. §31 recorded
that shape for a pooled knob row; it arrives here in a row of six controls
that nothing pooled, which is the more exact statement of the same caveat:
the floor moves only when *every* graded member moves, whatever the row is
made of.

**The mixes are the one thing these rows do not have to apologise for.** Both
baselines read `6 single-file; 6 hand-authored`, and every task in both
categories is single-file and hand-authored, so no row in either table
discloses a mix of its own — the first two categories in this corpus whose
multipliers, when they arrive, will not be reading across a scope or
substrate difference on top of the knobs.

### 40. Locating against fixing, per model over six matched defects

Six planted defects, each authored twice against one byte-identical starting
repository: a `bug-fix` member whose deliverable is the correction and a
`fault-location` member whose deliverable is one (file, symbol) pair in an
**answer file**. Both members do the same detective work, so the pair prices
the second action against the first. Read locate-relative-to-fix, within one
model:

```
defect         haiku cost  haiku turns  sonnet cost  sonnet turns
allotments          0.59x*       0.69x*       0.57x         0.54x
ferry               0.92x        0.78x        0.87x         0.89x
lostproperty        3.01x*      10.00x*       0.71x         0.67x
noticeboard         0.93x        0.89x        0.90x         0.89x
paperround          0.87x        0.75x        1.53x*        1.22x*
postoffice          0.70x        0.67x        0.72x         0.64x
```

`*` marks a pair one of whose two cells did not resolve.

**How the unresolved cells are handled: quoted, never dropped.** An
unresolved run still spent its dollars — the calibration view counts it for
exactly that reason — but what it spent them on is a failed attempt, not the
action the pair is trying to price, so a ratio built on one measures the
failure. All twelve ratios are printed above; the reading below is taken over
the pairs whose *both* members resolved, and the three marked pairs are read
one at a time in §41 instead. Dropping them silently would have been dropping
the counterexamples, because **both of the round's only above-parity readings
are marked pairs**: haiku's `lostproperty` (the fix cell wrote nothing and
cost $0.0258 over one turn) and sonnet's `paperround` (the locate cell
answered wrongly after eleven turns).

**The reading: locating cost less than fixing, in nine of nine pairs where
both members resolved.** On haiku, four such pairs: **0.70×–0.93× on cost,
median 0.89×**, and 0.67×–0.89× on turns, median 0.76×. On sonnet, five:
**0.57×–0.90× on cost, median 0.72×**, and 0.54×–0.89× on turns, median
0.67×. No both-resolved pair on either model reached parity, and turns move
in the same direction as cost in every one of them — the two channels agree
here, which they have not always done (§20, §27).

**What the number is, and four things it is not.** It is what locating cost
against fixing, on six hand-authored single-file repositories, in one round,
on one agent version, with both members of each pair written by the same
author. It is *not* a general price of the action: the corpus has six
defects, and §25's own qualifier about four claims on one snapshot applies
here in the mirror image — six repositories, one authoring hand. It is not a
statement that locating is *easy*: the fault-location cells run 6–11 turns on
haiku and 7–11 on sonnet, which is real reading, and the terrain was built to
defeat a grep (`paperround`'s repository holds seven mutable defaults and one
of them is the defect). It is not a claim the calibration table makes, for
the reason §39 gives. And it is not a turns result independent of the cost
one: turn counts here are small integers, so a single turn moves a ratio by
more than a tenth, which is the quantisation the **effort claim** vocabulary
already refuses to bet on.

**What it does support.** The cheaper action is the one whose deliverable is
smaller, on both models, at a discount that is larger on the stronger model —
median 0.72× over sonnet's five pairs against 0.89× over haiku's four, which
are different pair sets, because the two models failed on different cells and
each model's reading drops its own. A selection query that has both rows can
now ask what it costs to have a fault *named* rather than *fixed*, which is a
question the corpus could not answer before this round at any price.

### 41. The three cells that did not resolve, read

**`lostproperty-write-up-what-happened` × haiku — an empty workdir diff.**
One turn, $0.0258, 24.7 s, and no file written. The agent worked the puzzle
out correctly in prose ("both should be written as thrown away … perishable
takes priority") and then asked which format to work in — "code that
implements this logic, or something else?" — and stopped. There is nothing to
grade: the diff is empty, so grading applies nothing and the held-out tests
fail on the pristine repository exactly as the lint requires them to. This is
the cell that makes its pair read 3.01× on cost and 10.00× on turns, and the
denominator is a run that did no work. Worth recording beside #60, which took
the filenames out of both `lostproperty` prompts hours before the sweep so
they would not be grep bait: the prompt this cell answered names no file, and
haiku answered the prompt as a question rather than as a task. Sonnet, on the
same prompt, resolved it in twelve turns.

**`allotments-go-back-for-what-nobody-could-read` × haiku — the right edit
and one too many.** Eight of the nine held-out tests passed. The agent
removed the swallowed exception in `Quarter.used_on` correctly — that *is*
the planted defect — and then also filtered unreadable plots out of
`Society.book`, which the held-out
`test_the_book_still_writes_up_every_card_that_came_back` forbids in as many
words: the book says what came back off each plot, unread cards and all; it
is the sheet that leaves them off. The run even wrote its own test asserting
the opposite of that one. Sonnet's cell made the same change in `used_on` and
touched `Society.book` not at all. This is a task's own contract catching an overreach, which is
the discrimination held-out tests exist for, and it is why the pair reads
0.59× on cost with a star beside it rather than as a reading.

**`paperround-locate-the-carried-over-count` × sonnet — onto a registered
near-miss.** The answer file read
`{"file": "newsagent.py", "symbol": "Newsagent.bundle_list"}`, which is
verbatim the first of the three **rejected answers** the task's
**accepted-answer key** registered: the place the wrong list is returned
from, where the prompt's symptom points before the trail reaches
`Slate.bundles` in `tallying.py`. §36 built the rejected half of the key for
exactly this shape — the plausible wrong *file* no lint can invent — and the
round's one failed locate cell landed on an answer the author had written
down in advance as wrong. That is the strongest evidence this round produces
that the new mechanism grades something: the key discriminated a near-miss,
on a paid run, in the direction it was built to.

**And the mechanism's first paid outing, taken as a whole.** Twelve
fault-location cells, eleven resolved, one failed onto a registered
near-miss, no broken run, no clipped cell, and no case of the failure mode
§34.5 called the round's most expensive assumption — an agent locating the
fault correctly and describing it at a level the key did not anticipate.
Zero of twelve is not proof that the assumption is safe; it is one round's
worth of it not having bitten, on six defects whose accepted sets were
written to two description levels each.

### 42. Replay, and how it was shown

The provenance claim v1 rests on is that a record is recomputable from the
run log: the log carries the workdir diff, and the verdict is obtained by
re-grading that diff against the held-out tests rather than by trusting
anything the agent said. Round 4's three logs were replayed one command per
log, each into a scratch `--data` path (never the checked-in dataset, which
is untracked and holds only round-1 records — the discipline §29.5 recorded
after a replay rewrote it):

```
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-16-r4-a.jsonl --data /tmp/r4replay/a.jsonl
  evaluated 1 runs over 101 tasks (1 resolved)
  merged 1 records into /tmp/r4replay/a.jsonl (1 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-16-r4-b.jsonl --data /tmp/r4replay/b.jsonl
  evaluated 11 runs over 101 tasks (9 resolved)
  merged 11 records into /tmp/r4replay/b.jsonl (11 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-16-r4-c.jsonl --data /tmp/r4replay/c.jsonl
  evaluated 12 runs over 101 tasks (11 resolved)
  merged 12 records into /tmp/r4replay/c.jsonl (12 total)
```

24 runs, 21 resolved, matching §38's per-category counts. The same three
commands with one shared `--data` path merge to 24 records (`1 total`,
`12 total`, `24 total`), and the three per-log datasets concatenated are
identical to
that merged corpus record for record — no row missing, no row duplicated, no
field differing — with every record carrying its log row's own measurements
(cost, turns, tokens, latency, agent version, as-of date) unchanged, because
replay reads the log and never re-runs the agent.
`tests/test_firstparty_v1_round4_record.py` runs that comparison as a test,
so the claim is re-checked rather than remembered.

What this shows is that every verdict in this record is recomputable from
checked-in bytes by one command per log. What it does not show is that a
re-run would produce the same diff: a task × agent × model cell is swept
once, and replay reproduces the grading, not the agent.

## Round 5 candidates — listed 2026-08-16

Round 4 is closed: #47–#61 are shut, §§38–42 are the record and
`tests/test_firstparty_v1_round4_record.py` re-checks it. What follows is the
candidate list for the next round in §33's sense — **candidates, not
tickets**, each gated on `/grill-with-docs` or `/to-spec` before it is work.
Nothing below authors a task, a spec or a ticket. The ordering follows §6:
kill the most expensive assumption cheapest and first, and carry one new
instrument per round.

### 43. What round 5 should take up (candidates, not tickets)

**Residue from round 4, none of it blocking, all of it cheaper to clear
before a round than during one.**

- #46 is open by the parent-ticket convention; a `/frontier #46` pass confirms
  nothing on that spec remains and the owner closes it.
- `.qap/regen_hashes.py`, which generates the held-out "repository is as it
  was handed over" digests for every locate task, is uncommitted; the next
  locate-style task cannot be authored against a generator that only one
  machine holds.
- `surface` is undeclared on all twelve round-4 tasks (#46 said "decide once,
  not at #56"; it was not decided).
- The taxonomy ADR that #46 judged warranted (3/3 on the criteria) is
  unwritten.
- §34.5's most expensive assumption — an agent locates the fault correctly
  and describes it at a level the key did not anticipate — went 0/12 in
  round 4. That is one round of not being bitten, not a proof; it stays on
  the watch list.

**Candidate A — finish heap 2: `review a diff` and locate-style
comprehension.** §34.5 named this the step after real runs had exercised
plant-and-check, and §41 supplies the exercise: eleven of twelve locate
cells resolved, the twelfth failed onto a registered near-miss, so the
mechanism has been paid for once and discriminated in the direction it was
built to. The grading principle is unchanged (plant the ground truth, read a
structured answer file from the workdir diff, compare through a
project-owned comparison module), which is why this is the cheapest new
coverage available. It also forces a ruling round 4 deferred: §36 keeps the
bug-fix/fault-location pairing as an **unchecked convention** whose stated
revisit trigger is "the first fault-location-style task with no partner".
`review a diff` is that task — its planted findings have no fix-side member
whose mandatory pristine failure proves a defect exists — so round 5 either
turns the convention into a checked rule (a second proof of existence per
planted finding) or records why review-a-diff needs none. About twelve
tasks, in round 4's cost band.

**Candidate B — the knob line's parked work, as a rider not a subject.**
§34.6 left §33 candidates 3, 7 and 8 "not dropped and not scheduled":
rebuild an existing pair's shape on a second vendored library, replicate
K10 there, and sweep `pysm-work-out-a-way-there` × sonnet, the corpus's one
`incomplete` cell. Candidate 8 is now unblocked (its dependency was §33
candidate 1's tier limit, which #50/#61 delivered) and costs one cell under
the recorded cross-round caveat of §29.4. Candidates 3 and 7 buy the
cross-substrate agreement §10 has wanted since before round 1. None of the
three opens a new capability, which is why they ride alongside A rather
than displace it.

**Candidate C — heap 3 now (investigate and propose, decompose a
requirement, explain-style comprehension).** §34.3 deferred these because
grading them needs two new instruments — a subjective grader and a
calibration experiment proving it is worth trusting — and round 4 already
carried one. The argument for **not** doing this in round 5 is that §34.4
already archives every run's free-text answer as an artifact the verdict
does not read, precisely so a heap-3 grader has something to be calibrated
against: round 4 contributed 24 such answers, round 5 under A would
contribute more, all on tasks whose ground truth is known. A grader
calibrated on one round of archive is thinner than one calibrated on two.

**Candidate D — heap 4 (optimise performance).** Needs a stable performance
baseline, a third grading mechanism, on a single-machine harness with no
process isolation (#15 open, unscheduled). Highest variance of the four
heaps under present conditions; ordered after C.

**Cross-cutting, any round can carry one:** repeat sampling per cell and a
run-index schema (pass@k against mean, the open question parked since
2026-08-05); a third ladder model; #15 process isolation.

**The recommendation put to the grill:** round 5 = A as the subject, with
B's candidate 8 as a one-cell rider; round 6 = C, calibrated against the
free-text archive of rounds 4 and 5. One new instrument per round, the
pairing convention forced to a ruling by the first task that breaks it.

### 44. Three rounds at once — the arc from round 5 to round 7 (candidates, not tickets)

The owner asked, on 2026-08-16, to think rounds 5, 6 and 7 together, with
round 7's subject fixed in advance: **widen the corpus** — more benchmark
samples, specifically more programming languages and more differentiated
tasks. This section records the arc as candidates for `/grill-with-docs`;
it authors nothing. §43's per-round detail for round 5 stands; what changes
is the reason for round 5's and round 6's shape, which is now partly
"round 7 needs it".

**44.1 The arc.** Finish the graders (round 5 heap 2, round 6 heap 3), then
widen (round 7). Widening before the graders exist would author tasks that
land in no gradeable box; widening before the graders are trusted would
scale noise. One new instrument per round, as §6 requires:

| Round | Subject | The instrument | Riders |
|---|---|---|---|
| 5 | finish heap 2 (`review a diff`, locate-style comprehension) | none new — plant-and-check reused; §36's pairing convention forced to a ruling | §33 cand. 8; round-4 residue (§43) |
| 6 | heap 3 (investigate/propose, decompose, explain-style comprehension) | a subjective grader plus its calibration experiment against the free-text archive of rounds 4–5 | a third ladder model; #15 or a hermetic-grading ruling |
| 7 | widen: languages and differentiated scenarios | a per-language grading runner (44.2) and a coverage grid with a lint (44.3) | repeat sampling / pass@k schema, if the budget allows |

**44.2 More languages is a third grading mechanism, not more tasks.** All
101 tasks carry `language: python`, and although `schema.py` has held a
`language` field since v0, the grader in `src/ai_benchmark/firstparty_v1.py`
is pytest-shaped end to end: `--noconftest`, stdlib-first `sys.path`,
a junitxml verdict, the loader invariant that no top-level `repo/` entry
shares a stdlib name. Every one of those is a Python fact. Adding a language
therefore means a **runner registered per language** — its test invocation,
its machine-readable verdict, and its own answers to the two questions the
Python runner already answers (how held-out tests override visible ones;
which verdict-forgery classes are closed). Two costs to name at the grill:

- *Hermeticity.* The corpus is stdlib-only and grades offline. TypeScript or
  Rust bring a toolchain and a dependency tree; #15 (process isolation),
  open and unscheduled since 2026-08-04, becomes a precondition rather than
  a residual, or round 7 records an explicit hermetic-grading ruling in its
  place.
- *A new confounder.* The same action in two languages costs differently for
  reasons that are toolchain, not model. The clean reading is §10's
  cross-substrate method transposed: **port an existing task's shape to the
  second language** — same action, scale and surface — and read whether the
  round-3/4 readings transfer, before authoring new scenarios in it.

§34.5's discipline applies verbatim: one language proves the runner. The
leading candidate is TypeScript (opens the `frontend` surface, mature
tooling, a public multi-language benchmark to read against); Go is the cheap
alternative (single-binary toolchain, easiest hermeticity).

**44.3 "More differentiated" has to be a coordinate, or it is a mood.** The
repo already has the axes: `category` (ten actions), `surface` (introduced by
#46, declared on no task), `scale`, `language`, and substrate (hand-authored;
vendored pysm and RBQL; three untouched entries in
`docs/research/substrate-candidate-repos.md`). Differentiation is **filling
empty cells of that grid**, and the lint says so: a new task must land in an
under-populated cell or declare why not. Round 7's acceptance is then a
coverage figure — cells populated before and after — not a task count.

One guard-rail, from §34.1: the rung axis was conceded to the ingested public
benchmarks, so "differentiated" must not drift back into "harder". The
axis being widened is scenario — surface, language, terrain — not
difficulty.

**44.4 What rounds 5 and 6 must lay down for round 7.**

- Round 5 decides `surface` once and declares it on every task (a round-4
  residue), and spreads its own ~12 new tasks across surfaces on purpose —
  otherwise round 7 has no coverage baseline to move.
- Round 5 generalises #51's terrain assertions into lint rules (a prompt may
  not name an accepted file or symbol; an accepted class level requires more
  than one class in the file). Round 5 is the last low-volume authoring pass
  before volume, and the hand-run adversarial review that #51 needed twice
  does not scale to round 7.
- Round 6's subjective grader is designed language-agnostic — it reads the
  structured answer file and the archived free text, never the test runner —
  or every language round 7 adds re-opens heap 3.
- Round 6 carries #15 or the hermetic-grading ruling, and trials a third
  ladder model: model differences by language are where a two-model ladder
  reads least.

**44.5 Cost, stated before anyone spends.** Round 4 came in at $0.14 per cell
on hand-authored Python. Rounds 5 and 6 should sit in that band. Round 7 is
the first round that could not: a second language on vendored substrates
carries §31's 2–3× terrain step, a third model adds a column, and repeat
sampling multiplies by n. Fifty tasks × three models × n=3 is ~450 cells and
roughly $60–130 by round-3/4 unit costs. That is why repeat sampling is a
rider "if the budget allows" and why the language runner is proven on a
ported handful before anything is authored fresh.

**44.6 The questions the grill has to answer.**

1. Round 7's first language — TypeScript (surface + ecosystem) or Go
   (hermeticity)?
2. Is round 7's acceptance a coverage-grid figure with a lint, rather than a
   task count?
3. Does round 7 port existing shapes first (transfer reading, cheap, clean)
   or author new scenarios in the new language (wider, more confounded) —
   or a small port followed by new authoring?
4. Round 6's calibration bar for the subjective grader (agreement with the
   held-out verdict on archived free text) — the number decides whether heap
   3 takes part in round 7's widening at all.

## Rounds 5–7 rulings — 2026-08-17

§§43–44 were put through `/grill-with-docs` on 2026-08-17. Fifteen decisions,
taken one at a time in dependency order; where a ruling reverses a §43/§44
recommendation the reversal is stated. This section still authors nothing:
it is the input to `/to-spec`, which files one spec per round.

### 45. What rounds 5, 6 and 7 are

**45.1 The arc is re-ordered: widen before the subjective grader.** §44.1's
linear R5 → R6 (heap 3) → R7 (widen) assumed widening waits on every grader.
It does not — widening covers heaps 1–2 only, and heap 3 stays on Python
until its grader is trusted. Ruling: **round 5 = heap 2; round 6 = the agent
round (45.13); round 7 = the widening round; round 8 is not ruled** (45.15).
Two consequences: the heap-3 grader gains two more rounds of free-text
archive to be calibrated against, and the hermeticity question loses the
buffer round it had — 45.8 answers it instead of #15.

**45.2 Round 5's scope is `review a diff` plus locate-style comprehension,
and its one instrument is the set-shaped answer key.** Locate-style
comprehension ("where is X handled") is a (file, symbol) answer with no
defect behind it: it reuses the fault-location key, `_answer.py`, lint and
hash gate verbatim and rides at zero mechanism cost (~4 tasks). Review-a-diff
is the new shape — a **findings key** whose accepted and rejected halves are
*sets* — and is the round's instrument (~8 tasks). About twelve tasks, in
round 4's cost band.

**45.3 A review-a-diff verdict is recall over the planted findings, guarded
by rejected findings.** `resolved` iff every **planted finding** in the key
is matched by some answer *and* no answer matches a rejected finding.
Unregistered extra findings are archived and not scored — a real problem the
author did not plant must not fail the run, and every-line-is-a-finding
fails on the rejected half. The lint requires at least one rejected finding
per task, as it does for fault-location; the verdict stays binary — partial
recall is not a score, because a partial score would be a new quality
metric.

**45.4 §36's pairing convention becomes a rule with three registered forms.**
Every planted truth in a plant-and-check task needs a mechanical **existence
proof**, and the form is registered per action: fault-location's is the
partner bug-fix member's mandatory pristine failure (unchanged);
review-a-diff's is a held-out test shipped per planted finding that **fails
on the repository with the reviewed diff applied and passes on the author's
corrected version**, run by the lint and never by grading; locate-style
comprehension's is that the accepted (file, symbol) resolves in the starting
repository. §44's alternative — a bug-fix partner per finding — was rejected
as N partners nobody runs; "author attests" was rejected as the convention it
already is.

**45.5 `surface` is declared once, mechanically, and round 5 does not
spread it.** All 101 existing tasks are stdlib Python libraries and CLIs and
are declared `application` in one commit; from then on the lint requires a
first-party task to declare `surface` explicitly (`unknown` stays legal only
for ingested records). §44.4's "round 5 spreads its tasks across surfaces"
is **withdrawn**: under a pytest grader `frontend` is unauthorable and
`infrastructure` is contrived, and a task written to occupy a coordinate is a
bad task. Surface diversity is the widening round's, and only once 45.11's
condition is met.

**45.6 The terrain assertions become task-set lint, with a declared waiver.**
Three rules, over every task that carries an answer key: the prompt names no
accepted or rejected file or symbol; no prompt content word narrows to the
accepted module alone; an accepted class-level answer requires the file to
define more than one class. Per-task tests stop copying them. False positives
are handled by a per-task `terrain_waiver:` carrying a reason, never by
loosening the rule. The hash-gate digests move from the uncommitted
`.qap/regen_hashes.py` into the CLI, discovering locate-style tasks from
their keys rather than a hand-kept tuple; the script retires.

**45.7 Round 5 carries §33 candidate 8 and nothing else from the knob line.**
`pysm-work-out-a-way-there` × sonnet is swept, one cell, under the 600 s now
registered, and read with §29.4's cross-round caveat. Candidates 3 and 7 stay
parked: their question — does a reading survive a change of substrate — will
be asked in a stronger form when the corpus changes language, and is
re-weighed after that. The taxonomy ADR #46 owed is written in round 5.

**45.8 The widening round's first language is TypeScript on `node:test`, and
"stdlib-only runner" is the entry condition for every language.** Node 22
ships `node:test`, a JUnit reporter and default type-stripping, so a
TypeScript task can be authored and graded with no `node_modules` at all —
the same hermetic footing the Python corpus has had since round 1, the same
verdict shape (JUnit XML), and the same held-out-overrides-visible mechanics.
That removes the hermeticity cost that made Go attractive; Go remains the
alternative if a second language is wanted. The **stdlib-only rule** — a
**language runner** is admitted only if a task in that language can be graded
with the language's own toolchain and nothing installed — is what keeps #15
unscheduled. This is the second ADR the arc owes (45.16).

**45.9 TypeScript tasks are authored fresh; nothing is ported.** §44.2's
"port a handful first" was put and declined: a ported batch by itself buys a
transfer reading the owner does not want and no coverage. The cost is
recorded as a known forfeit — the runner's first paid outing confounds new
language with new scenario, and no cross-language transfer reading exists —
and the runner's credibility rests on the free instruments round 4 used:
lint-constructed negatives through the real pipeline, the reference-solution
gate, replay.

**45.10 The coverage grid is `category × surface × language`; acceptance is a
spec target; the lint prints, it does not steer.** `scale` is derived and
`substrate` is nearly all hand-authored, so both are disclosed, not gridded.
The widening spec names its target cells (as many tasks per action ×
`typescript` as it commits to); `ai-bench lint-v1` gains a **coverage
table** so the figure is read, not remembered. §44.3's per-task rule — a new
task must land in an under-populated cell — is **withdrawn**: coverage is a
round's goal, not a task's property, and the rule would tax every later
round that wants depth.

**45.11 TypeScript tasks are all `application`; `frontend` is deferred behind
its own ruling.** Node has no DOM; jsdom is a dependency; a browser is a
different runner. So `frontend` cannot be opened under 45.8 this round, and
declaring DOM-free UI logic as `frontend` was rejected as misnaming the
glossary's "where the work happens". Differentiation in the widening round
comes from **language and scenario type** — `node:http` services,
async/event flow, streams, CLI and filesystem tools, none of which the Python
corpus has — with `surface` unmoved. Opening `frontend` (a vendored jsdom as
substrate? a browser runner?) is a separate ruling.

**45.12 The widening round covers the actions that already have graders, and
`test-authoring` is a registered empty cell.** TypeScript gets bug-fix +
fault-location pairs, feature-dev, refactor and code-review, two to three
each, ~12–14 tasks. `test-authoring` — the only heap-1 action with zero
tasks in *any* language — needs a mutation gate (the agent's suite must pass
on the starting repository and fail on each planted mutant), a new verdict
shape, and does not ride on the language runner. It appears in the coverage
table as 0 and queues for round 8 (45.15).

**45.13 Round 6 is the agent round: a Codex adapter, no new tasks.** The
owner's "read Codex too" is, in this glossary, a second **agent**, not a
third model — `combination = agent × model`, and harness-versus-model
attribution is what §34.1 kept for the first-party layer. `codex-cli` is
installed and `codex exec --json` yields a headless event stream. The
adapter is a real instrument (invocation, event parsing to turns/tokens,
version capture, the permission-denial equivalent, the run-time limit) and
gets its own round so it is not confounded with the language runner. Scope:
round 4's twelve tasks plus a per-category sample, ~30 cells, one OpenAI
model (named at spec time; default the CLI's default), **$5–10 stated in
advance**; the whole-corpus sweep is decided on that reading. From round 7
on, Codex is a second column.

**45.14 Codex cost is table-derived and says so.** Codex reports tokens, not
dollars. `cost_usd` is computed from a checked-in, as-of-dated **price
table**, whose version rides in the run log beside `agent_version`; the run
carries a **cost source** field, `vendor-reported` (claude-code's
`total_cost_usd`) or `table-derived`, so cross-agent cost readings disclose
that the two numbers were obtained differently. Replay never recomputes cost.

**45.15 The arc is ruled to round 7; round 8 is chosen after the widening
record.** Two candidates queue: the heap-3 subjective grader (§34.3, now
with three rounds of archive) and the `test-authoring` mutation gate
(45.12). Their order, and the grader's calibration bar, are set on the
widening round's record rather than today.

**45.16 Models, sampling, budget.** The two-model ladder stands through the
arc; repeat sampling stays parked (a whole-corpus sampling round, once the
corpus's shape settles, is cleaner than adding n per round). Rounds 5 and 6
sit in round 4's ~$0.14/cell band; the widening round's range is stated in
its spec from round 6's per-cell figure. ADRs owed: the taxonomy change (#46,
round 5) and the stdlib-only runner rule (round 7's spec).

## Round 5 run-time limits and cost — registered 2026-08-18

**46. `code-review` and `codebase-comprehension` register at 600, beside round
4's two, and the round's cost range is stated before the first paid run.**
Ticket 20 (#82) does §37's move again, one round later: `LIVE_RUN_LIMITS_S`
gains `code-review: 600` and `codebase-comprehension: 600`, so the table now
carries four entries — `bug-fix`, `fault-location`, `code-review`,
`codebase-comprehension` — all at the flat default's own value. Registration
is the point, not a cell moved: round 5 has no locate/fix-shaped contrast to
protect the way round 4 did, but registering both new categories at the
default's own value is still a considered commitment rather than an inherited
convention, and equal values are what keep the round's readings free of a
ceiling difference between its two new actions. Because the number in force
does not change for any task, **no cross-round caveat arises** against round
4 — the rule is CONTEXT.md's live-run-limit glossary entry, not restated
here.

The rider `pysm-work-out-a-way-there` × sonnet (§45.7, §33 candidate 8) is a
`feature-dev` task, which this ticket leaves unregistered: it runs under the
flat default of 600 seconds, numerically equal to the round's four registered
limits but not itself a registration. Stating that here is what lets the
round's record later say the rider ran "at the flat default", not "under the
registered 600 s" — a claim only the four registered categories can make.

**Cost, stated before anyone spends.** Round 5's sweep is twelve tasks (eight
`code-review`, four locate-style `codebase-comprehension`, §45.2) × the
two-model ladder = 24 cells. Round 4's actual per-cell figure, $0.1364 over
24 cells of comparable hand-authored terrain (§38), puts a flat extrapolation
at roughly $3.27; the range stated here is **$3–6**, wider than a flat
extrapolation to leave headroom for `code-review`'s larger read — a
multi-file diff plus a findings key is more context per turn than a single
planted defect. Whether the round landed inside it is for the round's
verdicts section to say, against this line, once the sweep — run by hand
under `docs/agents/sweep-protocol.md`, never queued — has happened.

## Round 5 verdicts — 2026-08-18

Round 5 (#62) is built and swept: `surface` declared on every task and required
from then on (#63), the coverage table (#64), the terrain rules moved into the
lint (#65, #66), hash-gate generation moved into the CLI (#67), locate-style
`codebase-comprehension` riding round 4's answer key at zero mechanism cost
(#68), the round's one instrument — the set-shaped **findings key** (#69, #70,
and #85 which made a planted finding a set of alternative locations), the
**existence proof** registered per action (#71), twelve tasks (#72–#81), the
tier registration §46 ruled (#82), ADR-0002 (#83), and one sweep (sweep id
`round-5`, 24 of 24 cells, $3.9631) plus one rider invocation that logged
nothing. Everything below is recomputable from the checked-in artifacts: the
table in §48 by `uv run ai-bench calibrate-v1`, the verdicts in §47 and §50 by
re-grading each logged diff the way `eval-v1 --replay` does, and the per-cell
figures from the run logs' own fields.
`tests/test_firstparty_v1_round5_record.py` pins every figure these sections
publish, and §51 is how the logs were shown to replay exactly.

**What these sections are not.** Round 5 registered no knob contrast — its
twelve tasks are all **declared controls**, as round 4's were — so there are no
per-knob verdicts to write, no effort claim to grade, and no kill-discipline
reading to take. `reconcile-v1` counts the round in its round list and nowhere
else: no knob's counter moves, and none is demoted or advanced by this round.
Nor is there a headline contrast between actions. Round 4 had one because six
repositories each carried two actions; round 5's twelve repositories carry one
action each, and §49 says what follows from that rather than quoting a
comparison the round was not authored to produce. What the round bought is two
more categories the corpus could not measure at all, one new grading mechanism
— a verdict over a *set* — exercised for the first time against paid runs, and
the first reading anyone has taken of that mechanism's failure modes.

### 47. What the round measured

**The sweep.** Twelve tasks × the two ladder models = 24 cells, all swept, none
twice: eight `code-review` and four locate-style `codebase-comprehension`
(§45.2), every one of them a declared control, `scale: single-file`,
`surface: application`, `language: python`, hand-authored. One sweep id
`round-5` and one agent version `2.1.234 (Claude Code)` across every row of
every log: `r5-a` is the dry check (`bandstand-where-the-poster-is-worded` on
haiku), written to a normally-named log as the protocol requires; `r5-b` is
haiku's other eleven; `r5-c` is sonnet's twelve. The sweep ran from a dedicated
worktree with guard backups kept outside it and verified byte-for-byte against
the committed blobs. All 24 cells logged a row, so none was blocked by the
environment: a run with non-empty `permission_denials` is a broken run and
fails loudly rather than logging a verdict.

**The rider, recorded apart.** `pysm-work-out-a-way-there` × sonnet (§45.7,
§33 candidate 8) was run in its own invocation, `r5-d`, and **timed out again**
exactly as it did in round 3 — so that log is empty, the cell is still
`incomplete`, and the round is 24 cells rather than 25. Three things follow and
none of them is a reading. It ran at the **flat default of 600 seconds**: its
category `feature-dev` is not in `LIVE_RUN_LIMITS_S` and §46 registered nothing
for it, so the number it ran under is numerically equal to all four entries
the limits table now carries and is not itself a registration — a distinction
only the four registered categories can claim the other way. It carries §29.4's
cross-round caveat, and **it is not merged into round 3's readings**: had it
produced a row it would have been measured under an invocation its
forty-three round-3 neighbours did not have, so it would have repaired nothing;
having produced none, it leaves `feature-dev`'s
`K1=intent,K7=dense,K9=single` row reading `3.73x (n=1)` and
`sonnet-only (n=1)` on sonnet, unchanged from §31. And the version claim above
is a claim about rows: the three logs that carry rows all carry `2.1.234`, and
what the rider ran under is recorded by the sweep commit's own body rather than
by a row, because a timed-out invocation logs nothing to check.

**Cost, against the expectation stated before the first paid run.** Expected
**$3–6**, stated in §46 from round 4's per-cell figure with headroom for
`code-review`'s larger read. Actual **$3.96** — $0.9794 on haiku and $2.9836 on
sonnet, $3.9631 in total — against round 4's **$3.2748**. Per cell that is
$0.1651 against round 4's $0.1364 over the same 24, and the headroom is where
it was expected to be: the sixteen review cells took $3.2095 of it against the
eight comprehension cells' $0.7535, and a review cell cost $0.2006 on average
against a comprehension cell's $0.0942. **The estimate was honoured**, in the
middle of a range stated in advance rather than at its cheap edge, which is
the second round in a row a range set before the spending held.

**The limits in force.** #82 registered `code-review` and
`codebase-comprehension` in `LIVE_RUN_LIMITS_S`, both at **600 seconds** — the
flat default's own value, so the table now carries four entries and all four
read the same number. **No cross-round caveat arises for this round's own
cells**: the number in force did not change for any task, round 4 and round 5
both ran at 600, and the limit stays narrated rather than stamped on a row.
(The rider is the exception and is recorded above, not here.) Nothing came near
it — the round's longest run was **265.2 s**
(`belfry-review-the-peals-and-the-board` on haiku, and the closest any cell has
come to the ceiling since round 3) and its mean **77.6 s**, against a corpus
mean of 58.4 s over 225 runs and a longest-ever 311.2 s. No cell was clipped,
so no verdict in this record is a timeout in disguise.

**Resolution: 20 of 24 cells.** haiku resolved **9/12**, sonnet **11/12**. Per
category and model:

```
                  code-review  codebase-comprehension
claude-haiku-4-5  5/8          4/4
claude-sonnet-5   7/8          4/4
```

Every unresolved cell is a `code-review` cell:
`belfry-review-the-peals-and-the-board`,
`parishhall-review-the-hire-and-the-diary` and
`produceshow-review-the-points-and-the-sheet` on haiku, and
`apiary-review-the-book-and-the-crop` on sonnet. §50 reads each one. The
comprehension half went 8 for 8, which is what a locate-style task riding a
mechanism that has already had a paid outing (§41) was expected to do and is
not evidence about anything else.

**Rungs.** Nine of the twelve tasks came back `haiku-solvable`; three came back
`sonnet-only`, and all three are `code-review` — the three haiku cells above.
None landed `unsolved`, so the corpus's unsolved census is still the four
round-1 cells §23.10 counted, and its rung census now reads 94
`haiku-solvable`, 14 `sonnet-only`, 4 `unsolved` and the one `incomplete` cell
round 3 left and this round's rider did not repair.

**The corpus after the round.** 113 tasks, 225 runs, **24 cells over six
categories**, and still no empty cell — against §38's 101 tasks, 201 runs and
22 cells over four.

### 48. The two new categories' rows, as printed

`uv run ai-bench calibrate-v1` publishes them like this, quoted as printed:

```
category code-review
   baseline mean cost   claude-haiku-4-5 $0.0923 (n=8), claude-sonnet-5 $0.3089 (n=8)
   baseline mix         8 single-file; 8 hand-authored

   profile      tasks  claude-haiku-4-5  claude-sonnet-5  rung floor
   (zero-knob)  8      1.00x (n=8)       1.00x (n=8)      haiku-solvable (n=8)

category codebase-comprehension
   baseline mean cost   claude-haiku-4-5 $0.0603 (n=4), claude-sonnet-5 $0.1281 (n=4)
   baseline mix         4 single-file; 4 hand-authored

   profile      tasks  claude-haiku-4-5  claude-sonnet-5  rung floor
   (zero-knob)  4      1.00x (n=4)       1.00x (n=4)      haiku-solvable (n=4)
```

**Both multipliers are 1.00× by construction and neither is a reading**, for
the reason §39 gives of round 4's pair: every task in both categories is a
declared control, so each row *is* its own category's denominator, over the n
its own category swept — n=8 for `code-review` and n=4 for
`codebase-comprehension`, each taken over the tasks that ran that model. What
these two rows publish is the denominators — haiku $0.0923 and sonnet $0.3089
for `code-review`, haiku $0.0603 and sonnet $0.1281 for
`codebase-comprehension` — which is what a later constructed task in either
category will be divided by, and what a selection query reads as the price of
the shape of work. Every one of these numbers counts unresolved runs, which is
the table's rule and not an oversight: a failed run still spent its dollars.

**`code-review` is the widest model gap the corpus has published.** Sonnet
costs 3.35× haiku on this category's controls, against 2.87× on `refactor`,
2.64× on `bug-fix`, 2.60× on `feature-dev`, 2.58× on `fault-location` and 2.12×
on `codebase-comprehension`. That is a ratio of two denominators inside one
category, so it is a legitimate reading of these rows in a way that dividing
two categories' means is not — but it is one round on eight repositories, and
what it prices is a whole action's read rather than any knob.

**The `code-review` floor hides its three hardest members.** It prints
`haiku-solvable (n=8)` although three of the eight came back `sonnet-only`,
because a floor is the *weakest* rung any graded member landed on — the claim
that this profile has been solved that cheaply at least once. §39 recorded that
shape for `bug-fix`'s six controls; it repeats here in a row of eight, and the
repetition is the point: the floor moves only when *every* graded member moves,
whatever the row is made of.

**The mixes disclose nothing again.** Both baselines read
`N single-file; N hand-authored`, and every task in both categories is
single-file and hand-authored, so no row in either table discloses a mix of its
own — as with round 4's two, the multipliers these rows will one day carry will
not be reading across a scope or substrate difference on top of the knobs.

### 49. Review against locating against fixing: what this round cannot quote

Round 4's headline was locate-relative-to-fix per defect (§40), and it was
available only because six repositories each carried two actions against one
byte-identical starting tree. **Round 5's twelve repositories carry one action
each**, and no repository anywhere in the corpus carries a `code-review` task
beside a `fault-location` or `bug-fix` one: the twelve are twelve fresh
scenarios, and the six that carry two actions are round 4's locate/fix pairs,
none of which has a review member. So the per-repository comparison is **not
quoted here, because there is nothing to quote it over** — the round was not
authored to produce it and this is not a headline.

What is deliberately *not* done instead is dividing the categories' printed
means. `code-review`'s haiku denominator over `fault-location`'s would be a
ratio of means over two categories on two disjoint sets of repositories, and
§39's table refuses that pooling in as many words; §40's own reading was per
pair for exactly this reason, and it survived only because the pairs held the
repository constant while the action varied. Nothing in this round holds a
repository constant across two actions, so any three-way review/locate/fix
number quoted from it would be a difference between scenarios wearing an
action's name. If that comparison is wanted, it costs a review task authored on
a repository that already carries a locate/fix pair — which is a task somebody
would have to write, not a number this record can extract.

### 50. The four cells that did not resolve, read

All four are `code-review` cells, and between them they exercise both halves of
the new key: two failed on recall, one on the rejected half, and one on both.

**`parishhall-review-the-hire-and-the-diary` × haiku — two of three.** Six
turns, $0.0626. The answer named `diary.py Diary.cancel` and
`charges.py hire_for`, both planted, and never named `charges.py price_of`, the
third. Nothing it wrote matches a rejected finding. This is the plain shape of
a review verdict failing: recall short by one, with no partial credit, because
§45.3 rules that a partial score would be a new quality metric.

**`produceshow-review-the-points-and-the-sheet` × haiku — two of three,
again.** Six turns, $0.0533. `entries.py Book.of_class` and
`points.py points_for` matched; `points.py tally` was never named. Two
cheap six-turn cells missing exactly one finding each is the round's most
ordinary failure and the one worth least commentary: on eight repositories,
haiku found 21 of the 24 planted findings.

**`belfry-review-the-peals-and-the-board` × haiku — one missed and one
rejected, in the round's longest and most expensive haiku run.** Ten turns,
265.2 s, $0.2226. It matched `peals.py Book.longest` and `board.py peal_board`,
never named `ringers.py Band.ringer` (the normalisation made on one side of a
comparison only), and reported `tower.py minutes` — which the key registers as
a **rejected finding** because the tower clock subtracts the two strokes in the
order it names them and it is `Book.longest` that hands them over the wrong way
round. The note it filed argues `minutes` should add 1440 across midnight,
which no house rule asks for. So this cell failed twice over, and the second
failure is the rejected half discriminating exactly as it was built to — the
mirror of §41's `paperround` near-miss, one action later.

**`apiary-review-the-book-and-the-crop` × sonnet — full recall, failed on the
rejected half.** Ten turns, $0.4236. It named all three planted findings, and
then two more: `harvest.py Book.off_hive` and `keepers.py Roll.keeping`. The
second is a registered rejected finding, so the verdict is unresolved however
completely the change was reviewed — which is §45.3 working as ruled, since
every-line-is-a-finding has to fail somewhere.

**And what the fifth answer says about the key rather than the model.** The
reason sonnet gave for `Roll.keeping` is not the reason the key rejects it. The
key rejects that location as the place a reviewer chasing the joint-hive rule
points at first, and on the joint-hive rule the method is right. Sonnet did not
argue the joint-hive rule at all: it argued that `Roll.keeping` matches a hive
mark with `mark in keeper.hives` while the README's pre-existing house rule
says a mark is matched however it was written down, and that `apiary.standing`
in the same repository normalises both sides of that comparison. It filed the
same argument against `Book.off_hive`, which is unlisted and was therefore
archived and unscored. The author's ruling is visible in `corrected/`, which
leaves both comparisons exact — the rule is about asking the yard for a hive,
not about every place a mark is compared — and the author's ruling stands. The
finding for this record is not who is right. It is that **the verdict cannot
express the difference**: a rejected finding is a *location*, and the note
beside an answer is never read, so "right place, wrong reason" and "right
place, for a reason the author had ruled on" arrive at the grader as the same
bytes. §34.5 named the round's most expensive assumption as an agent locating a
fault correctly and describing it at a level the key did not anticipate. On the
**accepted** half that assumption did not bite, and not narrowly: all 45
accepted answers of the round named their finding's **primary** — the most
specific location its key registers — and not one of them needed the
class-level alternative #85 added. Those alternatives cost nothing and bought
nothing on this round's evidence, which is a fact about eight repositories and
not an argument for dropping them: the level nobody needed is the level a
differently-worded answer would have needed. The nearest miss is `belfry`'s
`peals.py Book.rung_by`, reported by both models — the very rule the first
planted finding turns on, argued against a neighbouring method the author's
`corrected/` leaves alone. That is a different location rather than a coarser
description of the listed one, and being unlisted it cost neither cell
anything. What bit is the **rejected** half's twin of the same assumption, on
the first paid outing of the mechanism: an answer the author had ruled on, at a
location registered against a different ruling, indistinguishable at the
grader from the false positive the registration was written to catch. That is a
reading about the key's description levels and not about the model, and the
cheapest thing it argues for is that a rejected finding's registered ground be
written down where something can read it — which is a change to the key and a
candidate for a later round, not a repair to this one.

**The mechanism's first paid outing, taken as a whole.** Sixteen review cells,
twelve resolved; 51 findings reported, of which 45 matched a planted finding,
two matched a rejected one and four were unlisted and archived; no broken run,
no clipped cell, and no edited repository — the guard suite that fails a run
which touched the code never fired. Both models independently reported
`peals.py Book.rung_by` on `belfry`, an unlisted location whose argument is the
same one sonnet made on `apiary`; under §45.3 that cost neither cell anything,
which is the archived-and-unscored rule doing precisely the job it was ruled
for.

### 51. Replay, the archive, and how each was shown

The provenance claim v1 rests on is that a record is recomputable from the run
log: the log carries the workdir diff, and the verdict is obtained by re-grading
that diff against the held-out tests rather than by trusting anything the agent
said. Round 5's four logs were replayed one command per log, each into a
scratch `--data` path (never the checked-in dataset — the discipline §29.5
recorded after a replay rewrote it):

```
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r5-a.jsonl --data /tmp/r5replay/a.jsonl
  evaluated 1 runs over 113 tasks (1 resolved)
  merged 1 records into /tmp/r5replay/a.jsonl (1 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r5-b.jsonl --data /tmp/r5replay/b.jsonl
  evaluated 11 runs over 113 tasks (8 resolved)
  merged 11 records into /tmp/r5replay/b.jsonl (11 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r5-c.jsonl --data /tmp/r5replay/c.jsonl
  evaluated 12 runs over 113 tasks (11 resolved)
  merged 12 records into /tmp/r5replay/c.jsonl (12 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r5-d.jsonl --data /tmp/r5replay/d.jsonl
  evaluated 0 runs over 113 tasks (0 resolved)
  merged 0 records into /tmp/r5replay/d.jsonl (0 total)
```

24 runs, 20 resolved, matching §47's per-category counts. The fourth is the
rider's empty log, and it replays to nothing rather than to an error, which is
the right handling of an invocation that logged no row: an empty log is a
record of an attempt and not a missing file. The same four commands with one
shared `--data` path merge to 24 records (`1 total`, `12 total`, `24 total`,
`24 total`), and the four per-log datasets concatenated are identical to that
merged corpus record for record — no row missing, no row duplicated, no field
differing — with every record carrying its log row's own measurements (cost,
turns, tokens, latency, agent version, as-of date) unchanged, because replay
reads the log and never re-runs the agent.
`tests/test_firstparty_v1_round5_record.py` runs that comparison as a test, so
the claim is re-checked rather than remembered.

What this shows is that every verdict in this record is recomputable from
checked-in bytes by one command per log. What it does not show is that a re-run
would produce the same diff: a task × agent × model cell is swept once, and
replay reproduces the grading, not the agent.

**The archive, and what it is for.** Every review and comprehension run's free
text is in the logs and **the verdict does not read a word of it**. The 24 rows
carry 2,373 words of agent `output` between them, and the sixteen review cells'
answer files carry a `note` on every one of their 51 findings — some 11,500
characters of argued English about why a line disagrees with a house rule —
which `_findings.py` tolerates beside a location and never inspects. The
verdicts in §47 turn on locations alone, and the notes are archived evidence:
they ride in the checked-in run logs, and unlike a verdict they cannot be
recomputed — replay re-grades a diff and cannot regenerate a sentence, so the
only copy of what an agent argued is the one the sweep wrote down. That text is
the calibration corpus the heap-3 subjective grader (§34.3, §45.15) is being
grown against. §45.1 re-ordered the
arc partly to buy that grader two more rounds of this material; this is the
round that first produced it in quantity, and the reason the free text is kept
in the logs rather than summarised into them.

## Round 6 cells and cost — registered 2026-08-18

**52. The round's thirty cells, its one Codex combination and its cost range,
written down before the first paid run.** This is round 6's pre-registration
and nothing else: §46 did it for round 5, and the same discipline applies a
round later to a round whose novelty is an *agent* rather than a task. The
round's record — what the sweep measured, what it cost, and what the two
harnesses looked like read against each other — follows at the next free
section numbers, §53 onward; nothing below is a result.

**52.1 The cells: thirty tasks, one combination.** Round 6 runs no new tasks.
It re-runs a sample of the corpus under a second harness, so every cell it
sweeps is a cell `claude-code` has already answered and the round's whole
reading is a cross-agent one. The thirty are:

Round 4's twelve — the six planted-defect repositories, each under both of the
actions built on it, which is the one contrast in the corpus that spans two
categories over one repository:

```
allotments-go-back-for-what-nobody-could-read   (bug-fix)
allotments-locate-the-swallowed-reading         (fault-location)
ferry-cast-off-when-it-should                   (bug-fix)
ferry-locate-the-idle-boat                      (fault-location)
lostproperty-write-up-what-happened             (bug-fix)
lostproperty-locate-the-wrong-write-up          (fault-location)
noticeboard-show-every-notice                   (bug-fix)
noticeboard-locate-the-lost-notice              (fault-location)
paperround-count-each-walk-on-its-own           (bug-fix)
paperround-locate-the-carried-over-count        (fault-location)
postoffice-charge-what-the-scale-said           (bug-fix)
postoffice-locate-the-wrong-band                (fault-location)
```

Four `code-review`, from round 5's eight:

```
apiary-review-the-book-and-the-crop
belfry-review-the-peals-and-the-board
commonland-review-the-beasts-and-the-dues
launderette-review-the-rate-and-the-card
```

Two locate-style `codebase-comprehension`, from round 5's four:

```
bandstand-where-the-poster-is-worded
boatyard-where-a-lift-out-is-refused
```

Six `feature-dev`:

```
calc-infix-evaluator
checkout-discount-codes
docstore-json-pointer
jobrunner-dependency-order
matcher-brace-expansion
microtemplate-for-loops
```

Six `refactor`:

```
cart-extract-coupon-policy
exporters-pull-up-base-class
gradebook-split-compute-from-format
ledger-split-formatting
logparse-extract-timestamp-parsing
measures-merge-duplicate-converters
```

**This list is the register.** Thirty ids, and the counts are 6 `bug-fix`, 6
`fault-location`, 4 `code-review`, 2 `codebase-comprehension`, 6 `feature-dev`
and 6 `refactor`.

**52.2 Where the sample came from, and why only from there.** Every one of the
thirty is a **declared control** or a member of the frozen **zero-knob
baseline**: round 4's twelve and round 5's six are declared controls, and all
twelve `feature-dev` and `refactor` ids are frozen-22 baseline tasks. Two
things follow, and both are why the sample was drawn this way rather than for
variety. First, every sampled task already has a category baseline behind it —
a control is what the **calibration view**'s denominator is made of, so a
Codex row on one of these lands in a cell that has a claude-code denominator
to be read against rather than in a cell that has none. Second, none of them
declares a **knob activation**, so nothing in this round can be misread as a
knob result: round 6 registers no contrast, moves no knob's counter, and the
kill discipline does not count it.

The second filter is mechanical: **both ladder rows must already exist** in
`data/first-party-v1-runs/` — `claude-code` × `claude-sonnet-5` and
`claude-code` × `claude-haiku-4-5`. Nothing is re-run on Claude this round;
the comparison side is the checked-in logs. Within each category the eligible
set was ordered by task id and the first N taken, a rule written down before
the sweep so that nobody chose which `feature-dev` tasks Codex is measured on
after seeing anything. `feature-dev` and `refactor` each have exactly eleven
eligible tasks and six were taken; `code-review` has eight and four were
taken; `codebase-comprehension` has four and two were taken.

**52.3 The combination**: `codex` × `gpt-5.6-terra` at reasoning `medium`
(`ai_benchmark.agents.CODEX_REASONING_LEVELS`). One model, **no ladder** — the
two-model ladder is claude-code's, and round 6's question is what a second
harness does, not what a second harness's cheaper model does. So the round is
thirty tasks × one combination = **thirty cells**.

**52.4 Cost, stated before anyone spends: $5–10, at list price.** The thirty
cells' claude-code × sonnet rows, already in the logs, total **$6.2572** —
$0.2086 a cell over exactly this task selection, which is a better anchor than
any round's flat per-cell figure because it is the same thirty repositories
and prompts. `gpt-5.6-terra`'s published per-token prices ($2/M uncached
input, $12/M output; `data/price-table.json`) sit near sonnet's, so a flat
substitution lands around $6. The registered range is **$5–10**: the low end
allows for Codex reading less per turn, the high end for it reading more or
taking more turns, and neither end is a prediction. Whether the round landed
inside it is for the round's record to say against this line.

**Why that is list price and not a bill.** The operator's Codex is
authenticated by **ChatGPT login**, not by an API key, so these runs are not
billed per token at all. Every Codex row's `cost_usd` is therefore list price
*by construction* — tokens × `data/price-table.json`, stamped
`cost_source: table-derived` with the price table's version beside it — and
the dollars in this section and in the round's record are what the same work
would have cost on the metered API, not an invoice anyone received. A
claude-code row's `vendor-reported` figure and a Codex row's `table-derived`
one are made differently, which is exactly what the `cost_source` field exists
to disclose, and a cross-agent cost reading has to carry that difference rather
than quietly average across it. If the account is switched to API billing
before the sweep, **nothing in the pipeline changes** — the adapter still
prices from tokens, because `codex exec` reports no dollars either way — and
the record says which billing the runs were made under.

**The Codex spending that preceded this registration, disclosed.** Ticket 04
(#90) captured the checked-in event-stream anchor
(`tests/fixtures/codex/exec-events.jsonl`) with a real `codex exec --json`
call, and it was not the only one: finding an invocation shape that streams
every item kind the adapter parses, and seeing the real shapes `codex` emits
for a CLI-level failure, took **several throwaway calls**, each on a throwaway
prompt in a throwaway git-initialized directory. That batch is recorded in
`tests/fixtures/codex/metadata.json`, which names this section as the place it
is disclosed. **None of it ran a task, none of it wrote a run-log row, and
none of it is one of the thirty cells or inside the $5–10 range** — the range
is the sweep's. It was on the same ChatGPT-login account, so it was not billed
per token either.

**52.5 The limits in force: 600 seconds, every cell, and nothing new is
registered.** `bug-fix`, `fault-location`, `code-review` and
`codebase-comprehension` are registered at 600 in `LIVE_RUN_LIMITS_S`
(`src/ai_benchmark/firstparty_v1.py:4523`) — round 4's two by §37 and round 5's
two by §46. `feature-dev` and `refactor` are **not** in that table, and this
ticket adds nothing to it: those twelve cells run under the **flat default**,
which is numerically the same 600 seconds and is not a registration. Saying so
here is what lets the round's record write "at the flat default" for those
twelve and "under the registered 600 s" for the other eighteen, a distinction
only the four registered categories can claim. Because the number in force is
600 for every cell of the round and 600 is what every earlier round ran at,
**no cross-round caveat arises** and none is implied — the limit is still a
narrated ceiling rather than a field stamped on a row (CONTEXT.md's live
run-time limit entry).

**52.6 How the sweep is invoked.** Sweep id **`round-6`**, on every invocation
of it. Run by hand under `docs/agents/sweep-protocol.md`, never queued.

A **dry cell first**, in its own invocation: one of the thirty, run alone, so
that a mis-shaped event stream — the one failure mode a second harness adds
that the first cannot have — is discovered on a single paid cell rather than on
thirty. It is a real, paid, graded run and one of the round's thirty; it is
**not** a rehearsal to be re-run, because a task × agent × model cell is only
ever swept once. Its log is named like any other log of the sweep: the sweep
protocol bans `-dry` in a log's name, because round 1 left two paid cells in
`-dry`-named logs and the first pass of that analysis silently dropped both.
The remaining twenty-nine follow in one or more further invocations carrying
the same `--sweep round-6` and their own fresh `--log` paths.

The cells are chosen on the command line with **`--task`** (ticket 06, #92),
repeated once per id, and never by staging a cut-down worktree: the filter
refuses an id naming no task in the set before anything runs, and runs the
filtered set in corpus order, so two invocations naming the same ids sweep the
same sequence. `--agent codex` is what selects the harness and
`--model gpt-5.6-terra` the one model; the reasoning level is not a flag,
because the adapter reads it from the registered combination rather than from
the operator. So the dry cell is

```
uv run ai-bench eval-v1 --live --sweep round-6 --agent codex \
  --model gpt-5.6-terra --task <one of the thirty> --log <a normally-named log>
```

and each further invocation is the same line with the remaining ids and a
fresh `--log` path, the runner refusing to append to a log that already
exists.

## Round 6 verdicts — 2026-08-18

Round 6 (#86) is built and swept: the `codex` adapter (#91), the checked-in
price table and its corrected prices (#88, #96), the captured event-stream
anchor and the fake `codex` the live seam is tested against (#90), `--task`
(#92), one agent's rows selected before either reader reads them (#93), the
round's pre-registration (#94, §52), and one sweep — sweep id `round-6`, 30 of
30 registered cells, $2.1511 at list price. The round authored no task and
moved no knob: its whole novelty is a **second harness**, so every cell it
swept is a cell `claude-code` had already answered and every reading below is
a cross-agent one.

**Section numbering.** #86 named §52 for this record. §52 was taken by ticket
08's pre-registration, written before the first paid run as it had to be, so
the record is §53–§58 — the next free numbers, which is what §52 itself says
to expect.

**What these sections are not.** Round 6 registers no knob contrast, no
**knob activation** and no rung: its thirty tasks are declared controls or
frozen-22 baseline members (§52.2), and one model is not a ladder, so no
counter moves, nothing is killed or advanced, and `reconcile-v1` does not
count the round at all — its rows are another agent's and `select_agent`
drops them before the round list is built (§58). Nor is this a reading about
Codex-the-harness apart from `gpt-5.6-terra`: one Codex model is one
combination, and §57 says what follows from that rather than quoting a
comparison the round was not authored to produce.

Everything below is recomputable from the checked-in artifacts: the tables in
§55 and §56 from the run logs' own fields plus the verdicts re-grading their
diffs produces, the spend in §54 from those same fields, and §58's claims by
`eval-v1 --replay`, `calibrate-v1` and `reconcile-v1`.
`tests/test_firstparty_v1_round6_record.py` pins every figure these sections
publish, selecting the round's runs by sweep id and never by log filename.

### 53. What the round measured

**The sweep.** Thirty tasks × one combination = 30 cells, all swept, none
twice, and **the thirty are exactly the thirty §52.1 registered** — no cell
was dropped, none was added, and nothing had to be re-run. Six `bug-fix`, six
`fault-location`, four `code-review`, two `codebase-comprehension`, six
`feature-dev` and six `refactor`; twelve of them round 4's locate/fix pairs,
six from round 5, twelve frozen-22 baseline members. The combination is
`codex` × `gpt-5.6-terra` at reasoning `medium`, the one entry in
`CODEX_REASONING_LEVELS`, and the level rides with the model rather than with
the operator: it is not a flag, so no invocation of this sweep could have
asked for a different one.

**One sweep id, two invocations, one harness version.** Every row carries
sweep `round-6`, `agent: codex`, `model: gpt-5.6-terra`, as-of `2026-08-18`,
`cost_source: table-derived` and `price_table: openai-pricing-2026-08-18.1`.
The dry cell ran first and alone, in its own invocation — the round's
`noticeboard-locate-the-lost-notice` cell, a real paid graded run and one of
the thirty rather than a rehearsal — and the remaining twenty-nine followed in
one further invocation. The version is `codex-cli 0.147.0`, captured by
`codex --version` at the head of each invocation, and **it held across both**:
one string on all thirty rows, so no contrast in this record crosses a harness
version. All thirty logged a row, so none was blocked: a Codex run the harness
ended — an approval request nothing can answer, a failed turn, an error event
— raises and logs nothing, the exact counterpart of claude-code's
`permission_denials` rule.

**The limits in force: 600 seconds, every cell.** `bug-fix`,
`fault-location`, `code-review` and `codebase-comprehension` are registered at
600 in `LIVE_RUN_LIMITS_S`; `feature-dev` and `refactor` are not in that table
and their twelve cells ran under the **flat default**, which is numerically
the same 600 seconds and is not a registration. So the number in force was 600
for every cell of the round, as it has been for every earlier round, and **no
cross-round caveat arises** and none is implied. Nothing came near it: the
round's longest run was **92.8 s** (`matcher-brace-expansion`) and its mean
**63.0 s**, against round 5's longest of 265.2 s. No cell was clipped, so no
verdict in this record is a timeout in disguise. The limit is handed to the
adapter and never asked of it, which is what makes that one sentence cover a
harness the table was written before.

**Resolution: 29 of 30.** The one unresolved cell is
`apiary-review-the-book-and-the-crop`, read in §55. Against the same thirty
cells the ladder had already answered — 24 of 30 on `claude-haiku-4-5` and 27
of 30 on `claude-sonnet-5` — but see §54 before reading the dollars beside
those counts and §57 before reading anything into the harness.

**The corpus after the round.** 113 tasks and **255 runs**: the 225
`claude-code` runs the corpus had, plus 30 `codex` runs. The matrix has a
second agent in six of six categories and in exactly one combination, and no
cell of it was overwritten — a task × agent × model cell is swept once, and a
Codex cell is a different cell from the claude-code one on the same task.

### 54. Spend, by cost source, against the range registered before it

**What the account was billed: nothing per token.** The operator's Codex is
authenticated by ChatGPT login, not by an API key, so these thirty runs were
not metered. Every dollar figure in this record for a Codex row is therefore a
**list-price estimate by construction** — the row's usage breakdown priced at
write time from `data/price-table.json`, version
`openai-pricing-2026-08-18.1`, stamped `cost_source: table-derived` with that
version beside it — and it is what the same work *would* have cost on the
metered API. It is not an invoice, and "$2.1511 on Codex" must not be read as
one.

**The round, by cost source:**

```
codex x gpt-5.6-terra     $2.1511  table-derived  (list price, openai-pricing-2026-08-18.1)
claude-code x haiku       $2.3481  vendor-reported (the same thirty cells, already logged)
claude-code x sonnet      $6.2572  vendor-reported (the same thirty cells, already logged)
```

Per cell that is $0.0717 for Codex against $0.0783 on haiku and $0.2086 on
sonnet. **The two figures are made differently and the difference is not a
rounding one**: a `vendor-reported` dollar is what the vendor charged, and a
`table-derived` dollar is this repository's arithmetic over a published price
page. Reading them side by side is the whole point of the `cost_source` field
and is also its whole warning — a reader who joins them without it is joining
an estimate to a bill.

Two disclosures ride with that. The claude-code rows quoted here were written
before the field existed, so they carry **no `cost_source` at all**; they are
`vendor-reported` by construction, because claude-code prints its own
`total_cost_usd` and no price table is ever consulted for it, and the adapter
now stamps the field on rows written from here on. And the field lives on the
run-log row and not on the unified **record**: replay copies a row's
`cost_usd` through untouched but carries neither `cost_source` nor
`price_table` with it, which is exactly why §55's table prints the cost source
on the column — downstream of the log, nothing else does.

**The registered range was $5–10. The round came to $2.1511. It was not
honoured**, and it missed low by a factor of 2.3 rather than narrowly. Two
rounds in a row had held a range set before the spending (§47); this one
breaks that, and the reason is identifiable rather than mysterious. §52.4
built the range by substituting `gpt-5.6-terra`'s published prices into
sonnet's spend on these same thirty cells, and it priced input as though none
of it were cached. Round 6's thirty cells read **3,892,528 input tokens** and
wrote **49,636 output tokens**. The output alone prices at $0.5956; the
remaining $1.5555 over those input tokens is an effective **$0.3996 per
million**, against the table's $2 uncached and $0.20 cached. A registration
that had allowed for prompt caching would have landed near the answer; the one
that was made allowed only for turn counts, and turn counts were not what
moved.

**What a hand recomputation from a row can and cannot reproduce.** A row
carries `tokens_in`, `tokens_out`, `cost_usd` and the price table's version —
and `tokens_in` is the input *total*. The cached, cache-write and plain split
the figure was priced from is not on the row: it was read off the usage events
and consumed at write time. So from a row and the named table version a reader
can recompute the two bounds and check the figure sits between them — over the
round, **$1.3741 all-cached and $8.3807 all-uncached, with the logged $2.1511
between** — and cannot reproduce $2.1511 itself. That the all-uncached bound
($8.3807) falls inside the registered $5–10 is the same observation as the
paragraph above, arrived at from the rows instead of from the reasoning: the
registration priced the round at its upper bound.

### 55. The thirty cells under three combinations

Verdict and cost for every cell, with the cost source printed on the column,
because two of these three columns are bills and one is an estimate:

```
                                               claude-code x       claude-code x       codex x
                                               claude-haiku-4-5    claude-sonnet-5     gpt-5.6-terra
                                               vendor-reported     vendor-reported     table-derived
allotments-go-back-for-what-nobody-could-read  unresolved $0.1349  resolved   $0.2559  resolved   $0.0911
allotments-locate-the-swallowed-reading        resolved   $0.0792  resolved   $0.1448  resolved   $0.0540
apiary-review-the-book-and-the-crop            resolved   $0.0805  unresolved $0.4236  unresolved $0.0711
bandstand-where-the-poster-is-worded           resolved   $0.0662  resolved   $0.1428  resolved   $0.0494
belfry-review-the-peals-and-the-board          unresolved $0.2226  resolved   $0.5119  resolved   $0.0879
boatyard-where-a-lift-out-is-refused           resolved   $0.0664  resolved   $0.1184  resolved   $0.0420
calc-infix-evaluator                           unresolved $0.0843  unresolved $0.1435  resolved   $0.0750
cart-extract-coupon-policy                     resolved   $0.0526  resolved   $0.1652  resolved   $0.0748
checkout-discount-codes                        resolved   $0.0605  resolved   $0.2159  resolved   $0.0604
commonland-review-the-beasts-and-the-dues      resolved   $0.1063  resolved   $0.2992  resolved   $0.0790
docstore-json-pointer                          unresolved $0.0648  resolved   $0.1976  resolved   $0.0594
exporters-pull-up-base-class                   resolved   $0.0517  resolved   $0.1567  resolved   $0.0461
ferry-cast-off-when-it-should                  resolved   $0.0689  resolved   $0.1950  resolved   $0.0939
ferry-locate-the-idle-boat                     resolved   $0.0632  resolved   $0.1705  resolved   $0.0653
gradebook-split-compute-from-format            resolved   $0.0461  resolved   $0.1307  resolved   $0.0566
jobrunner-dependency-order                     unresolved $0.1264  resolved   $0.2247  resolved   $0.0836
launderette-review-the-rate-and-the-card       resolved   $0.0665  resolved   $0.2262  resolved   $0.0999
ledger-split-formatting                        resolved   $0.0551  resolved   $0.1296  resolved   $0.0450
logparse-extract-timestamp-parsing             resolved   $0.0338  resolved   $0.1107  resolved   $0.0475
lostproperty-locate-the-wrong-write-up         resolved   $0.0778  resolved   $0.1842  resolved   $0.0614
lostproperty-write-up-what-happened            unresolved $0.0258  resolved   $0.2601  resolved   $0.0863
matcher-brace-expansion                        resolved   $0.0937  resolved   $0.2487  resolved   $0.1301
measures-merge-duplicate-converters            resolved   $0.0564  resolved   $0.1692  resolved   $0.0609
microtemplate-for-loops                        resolved   $0.1075  resolved   $0.2745  resolved   $0.0647
noticeboard-locate-the-lost-notice             resolved   $0.0646  resolved   $0.1642  resolved   $0.0567
noticeboard-show-every-notice                  resolved   $0.0693  resolved   $0.1834  resolved   $0.0790
paperround-count-each-walk-on-its-own          resolved   $0.0635  resolved   $0.1881  resolved   $0.1079
paperround-locate-the-carried-over-count       resolved   $0.0550  unresolved $0.2875  resolved   $0.0635
postoffice-charge-what-the-scale-said          resolved   $0.1205  resolved   $0.1944  resolved   $0.0892
postoffice-locate-the-wrong-band               resolved   $0.0839  resolved   $0.1402  resolved   $0.0695
```

**Read the columns down, not across, until §57 has been read.** What this
table is for is the per-cell record: every cell of the round, its verdict and
what it cost, with nothing averaged and nothing dropped. Unresolved runs are
priced in exactly like resolved ones — a failed run still spent its dollars,
which is the calibration view's rule and this table's too.

The per-category sample, beside it rather than above it, because two of the
six categories are sampled at four cells and two, and a rate over two cells is
not a rate:

```
category                 n  claude-haiku-4-5   claude-sonnet-5    gpt-5.6-terra
bug-fix                  6  4/6  $0.4830       6/6  $1.2768       6/6  $0.5473
code-review              4  3/4  $0.4760       3/4  $1.4609       3/4  $0.3380
codebase-comprehension   2  2/2  $0.1326       2/2  $0.2612       2/2  $0.0914
fault-location           6  6/6  $0.4236       5/6  $1.0914       6/6  $0.3704
feature-dev              6  3/6  $0.5372       5/6  $1.3049       6/6  $0.4732
refactor                 6  6/6  $0.2957       6/6  $0.8621       6/6  $0.3309
all six                 30  24/30  $2.3481     27/30  $6.2572     29/30  $2.1511
```

Costs are as the columns above declare them: the two claude-code columns are
vendor-reported bills and the `gpt-5.6-terra` column is a list-price estimate.
The counts are verdicts and carry no such caveat — grading is one pipeline and
does not know which harness produced a diff.

**The one cell that did not resolve, and what it replicates.**
`apiary-review-the-book-and-the-crop`, the cell round 5's sonnet also failed
(§50) — and it failed it the same way, at the same location, on the same
argument. Codex named all three planted findings at their **primary**
locations, and then two more: `harvest.py Book.off_hive`, which is unlisted
and was archived unscored, and `keepers.py Roll.keeping`, which the key
registers as a **rejected finding**. Its note argues that `Roll.keeping`
matches a hive mark with plain equality where the house rule says a mark is
matched however it was written down — which is, to the sentence, the argument
§50 recorded sonnet making, filed against the same two locations. §50 read
that as a fact about the key's description levels rather than about the model,
and hedged it as a reading from one round. **A second harness and a different
vendor's model, given the same repository, filed the identical pair of extra
findings** — which is the strongest evidence the corpus has that what the
rejected half caught there is a property of the task rather than of one
model, and it costs nothing to obtain because the cell was swept anyway.

Across the four review cells Codex reported 16 findings: 13 matched a planted
one, all 13 at its primary; one matched a rejected one; two were unlisted and
archived. The twelve planted findings of the four keys were **all covered** —
the 13th accepted answer is `washes.py Book.owed` written twice in
`launderette`'s answer file, a duplicate that costs nothing because the
verdict asks whether a set covers another and not how many times. On `belfry`
Codex filed `peals.py Book.rung_by`, the unlisted near-miss §50 recorded
*both* claude models filing on that repository; three combinations across two
harnesses have now argued that location, which is the second thing this round
says about a key rather than about a model.

### 56. Locating against fixing, with a second harness beside the ladder

Round 4's headline (§40) was locate-relative-to-fix per defect, over six
planted defects each authored twice against one byte-identical starting
repository. All twelve of those cells are in this round, so the reading now
has a harness dimension. Read locate-relative-to-fix, within one combination,
both actions each:

```
defect           haiku cost  haiku turns  sonnet cost sonnet turns   codex cost  codex turns
allotments           0.59x*       0.69x*        0.57x        0.54x        0.59x        0.50x
ferry                 0.92x        0.78x        0.87x        0.89x        0.70x        0.54x
lostproperty         3.01x*      10.00x*        0.71x        0.67x        0.71x        0.82x
noticeboard           0.93x        0.89x        0.90x        0.89x        0.72x        0.64x
paperround            0.87x        0.75x       1.53x*       1.22x*        0.59x        0.47x
postoffice            0.70x        0.67x        0.72x        0.64x        0.78x        0.73x
```

`*` marks a pair one of whose two cells did not resolve. The haiku and sonnet
columns are §40's, unchanged and recomputed here from the same rows.

**The reading: locating cost less than fixing, in all six pairs, on the third
combination as on the first two.** Codex resolved all twelve cells, so all six
pairs are both-resolved — the first combination for which that is true —
giving **0.59×–0.78× on cost, median 0.70×**, and 0.47×–0.82× on turns, median
0.59×. Against haiku's four both-resolved pairs (0.70×–0.93×, median 0.89×)
and sonnet's five (0.57×–0.90×, median 0.72×). No pair on any of the three
reached parity where both its cells resolved, and the direction is the same
everywhere.

**What that adds, and what it does not.** §40's finding was one agent's; it
now survives a change of harness *and* of vendor, on the same six
repositories, which is the one thing this round could add to it cheaply. It
adds no generality about the action: it is still six hand-authored
single-file repositories with one authoring hand behind them, and a third
combination agreeing about the same six defects is not a seventh defect.

Two cautions, and the second is the one that matters. The cost ratios are
each taken inside one column, so no list-price dollar is ever divided by a
vendor-reported one — a ratio of two Codex cells is a ratio of two estimates
made the same way, which is sound in a way that Codex-over-sonnet would not
be. The **turn** ratios are weaker still: a turn is harness-defined (§57), so
a Codex turn ratio and a claude-code turn ratio are two different quantities
that agree in direction, and the agreement is worth no more than that. Turn
counts here are small integers, so one turn moves a ratio by more than a
tenth — the quantisation §40 already refused to bet on.

### 57. What this round cannot say

**No rung.** A rung is a claim about the cheapest model that solved something,
and rungs come from a ladder. Round 6 ran **one** Codex model, so it registers
no rung for any of its thirty tasks, moves nothing in the corpus's rung census
and leaves `reconcile-v1`'s ladder reading exactly where round 5 left it. What
`gpt-5.6-terra` would have cost at another reasoning level, or what a cheaper
Codex model would have done, is not in these logs at any price.

**No multiplier, and no Codex baseline.** The calibration view's multiplier is
a constructed task's cost over its category's control mean *for that agent*,
and there is no Codex denominator: thirty cells over six categories is between
two and six cells a category, all of them controls or frozen-22 members, and
none of them a constructed task. Nothing here is a Codex baseline and nothing
here should be divided by anything to make one. The published tables stay
claude-code's, which §58 shows they did.

**No cross-harness turn comparison.** A turn is defined by the harness that
counted it. A claude-code turn is the `num_turns` its result JSON reports; a
Codex turn is one **completed item of the event stream that is not a reasoning
item** (`agents._NOT_A_TURN`), so a tool call, a shell command and a message
each count as one. Round 6's Codex cells ran 6–15 of those, 248 in all. Those
are not the same unit, and this record quotes no comparison between them: the
turn ratios in §56 are each taken inside one harness for exactly that reason.

**No claim about the harness apart from the model.** `codex` × `gpt-5.6-terra`
@ `medium` is one combination, and a combination is what this project
measures. Nothing here separates what the scaffold did from what the model
did, so "Codex resolved 29 of 30" is shorthand for that combination and not a
statement about `codex exec` driving anything else.

**The round's expensive assumption, and how it held.** Everything above rests
on the two harnesses having been asked the *same thing*, so that what differs
between the columns is the thing under test — their own system prompts and
tool sets — and not something the runner introduced. An unequal condition on
the runner's side would invalidate the reading rather than weaken it: a
sandbox prompt eating part of a limit, a permission stance that stops one
harness and not the other, the operator's own config leaking into one side.
Five things are held equal, and each is held in the runner rather than in the
adapter:

- **the same prompt bytes** — `run_live` hands `task.prompt` to whichever
  adapter it resolved, and the Codex seam asserts that the last argv element
  *is* that task's prompt;
- **the same starting repository** — the workdir copy, the pristine commit and
  the diff capture are the runner's, and the adapter is handed a prepared
  directory it did not make;
- **the same limit** — `live_run_limit_s(task)`, keyed on the task's class,
  handed to the adapter and never asked of it, with a test that no caller can
  pass one;
- **the same grant** — `--dangerously-bypass-approvals-and-sandbox` against
  claude-code's `--permission-mode bypassPermissions`, plus
  `--ignore-user-config` against `--setting-sources ""`, so neither run reads
  the operator's configuration;
- **the same grading** — one pipeline over the diff, with a test that the same
  bytes from either harness grade to the same verdict.

**What stands against the failure mode is the live seam's argv assertions**
(`tests/test_firstparty_v1_codex_adapter.py`), which pin the exact command a
Codex run is made with — the registered model and reasoning level, the grant,
the two config-isolation flags, the prompt last and positional, and the
absence of `-s`, `--sandbox` and `--approve-for-me`. A drift in any of them is
a test failure before it is a reading. What none of that can check is the one
difference that is the variable itself: the two harnesses' own system prompts
and tool sets are not this project's to hold equal, and holding them equal
would leave nothing to measure.

### 58. Replay, and the published tables left where they were

Both round-6 logs were replayed, one command per log, each into a scratch
`--data` path rather than the checked-in dataset:

```
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r6-a.jsonl --data /tmp/r6replay/a.jsonl
  evaluated 1 runs over 113 tasks (1 resolved)
  merged 1 records into /tmp/r6replay/a.jsonl (1 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-18-r6-b.jsonl --data /tmp/r6replay/b.jsonl
  evaluated 29 runs over 113 tasks (28 resolved)
  merged 29 records into /tmp/r6replay/b.jsonl (29 total)
```

30 runs, 29 resolved, matching §55's column cell for cell. The two logs into
one shared `--data` path merge to 30 records, and the two per-log datasets
concatenated are identical to that merged corpus record for record — no row
missing, none duplicated, no field differing — with every record carrying its
log row's own measurements unchanged, because replay reads the log and never
re-runs the agent. That a Codex diff re-grades through the same pipeline is
not a new claim of this round; that every Codex row of it does, is.

**`calibrate-v1` and `reconcile-v1` print for `claude-code` exactly what they
printed before the round.** Both readers select one agent's rows before
anything else runs, defaulting to `claude-code` (#93), so the thirty Codex
rows are read out of the log directory and then dropped, and every published
number is computed over the same 225 rows as before. `reconcile-v1` says so in
its own header:

```
  runs       225 over 113 task(s)
  rounds     6 round(s): as-of 2026-08-04, as-of 2026-08-05, sweep round-2, sweep round-3, sweep round-4, sweep round-5
```

Six rounds, not seven: round 6 is not in that list, because a round list built
from `claude-code`'s rows cannot contain a round that swept none. And
`calibrate-v1` prints §39's and §48's rows unchanged — round 3's multipliers,
round 4's `bug-fix` and `fault-location` baselines and round 5's
`code-review` and `codebase-comprehension` ones, every figure where §§39, 48
and 31 left it — over a log directory whose provenance list now names
`2026-08-18-r6-a.jsonl` and `2026-08-18-r6-b.jsonl`. The Codex rows are
visibly *read* and provably *not counted*, which is a stronger statement than
their being absent would have been, and the one the suite pins.

## Round 7 cells and cost — registered 2026-08-20

**59. The round's fourteen tasks, its three combinations and its cost range,
written down before the first paid run.** This is round 7's pre-registration
and nothing else: §46 did it for round 5 and §52 for round 6, and the same
discipline applies to a round whose novelty is a *language* rather than a task
knob or an agent. The round's record — what the sweep measured, what it cost,
and what a second toolchain looked like read beside the first — follows at the
next free section numbers, §60 onward; nothing below is a result.

**59.1 The cells: fourteen tasks × three combinations = forty-two cells.**
Round 7 runs no Python. Every one of the fourteen is a task this round
authored, written in TypeScript against a repository that did not exist before
it, so nothing here re-runs a cell any combination has already answered. The
fourteen are, grouped by the action they are declared under.

Three `bug-fix`, the "put it right" half of the round's three planted defects:

```
leftluggage-put-the-unweighed-bag-back-on-the-scales   (a node:http service)
lockhouse-work-the-rest-of-the-night-through           (an async / event flow)
telegraph-write-up-the-last-message-of-the-day         (a stream pipeline)
```

Three `fault-location`, the "say where it is" half of the same three
repositories:

```
leftluggage-locate-the-charge-nobody-arrived-at
lockhouse-locate-the-boats-that-never-reached-the-book
telegraph-locate-the-message-left-on-the-tape
```

Three `feature-dev`:

```
seedbank-book-out-what-the-store-hands-over           (a CLI over the filesystem)
weighbridge-put-the-second-weighing-on-the-tape       (node:buffer, fixed-width frames)
parishchest-seal-the-register-against-a-later-hand    (node:crypto, a digest chain)
```

Three `refactor`:

```
gasworks-take-the-press-out-of-the-roll-room          (node:zlib)
tollhouse-take-the-writing-of-a-pass-off-the-ticket   (node:url)
courtleet-put-the-verdicts-on-one-table               (node:vm)
```

Two `code-review`:

```
masonsyard-review-the-lettering-and-the-account
limekiln-review-the-drawing-and-the-carting
```

**This list is the register.** Fourteen ids, and the counts are 3 `bug-fix`, 3
`fault-location`, 3 `feature-dev`, 3 `refactor` and 2 `code-review`.

**59.2 What every one of the fourteen is.** Each declares `language:
typescript` and `surface: application`, and each is a **declared control** —
`control: true`, no construction block, no knob activation, no prediction. Two
things follow, and both are why the round was authored this way rather than
with a knob in it. First, a control is what a category's **calibration view**
denominator is made of, so a TypeScript row lands in a cell that can be read
against its own category's baseline rather than against nothing. Second,
because no task here declares a contrast, **round 7 moves no knob's counter
and the kill discipline does not count it**: whatever the round measures, it
cannot be read as a difficulty result. Nothing is re-run in Python, and
nothing was ported from it — the three defect repositories, the three feature
scenarios, the three restructurings and the two reviews are all new scenarios
chosen for what the Node standard library can do and the Python corpus has
nothing like (`node:http`, `node:events`, `node:stream`, the filesystem behind
a real CLI, `node:buffer`, `node:crypto`, `node:zlib`, `node:url`, `node:vm`),
under ADR-0003's stdlib-only rule.

**59.3 The combinations**: `claude-code` × `claude-haiku-4-5`, `claude-code` ×
`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`
(`ai_benchmark.agents.CODEX_REASONING_LEVELS`) — the two-model ladder plus the
combination round 6 registered, **unchanged**. §45.13 said that from round 7
on Codex is a second column, and **this is the first task round to carry the
Codex column**: round 6's thirty cells were a re-run of tasks the ladder had
already answered, and these forty-two are the first cells where a Codex row
and its two claude-code rows are all written by the same sweep. So the round
is fourteen tasks × three combinations = **forty-two cells**.

**59.4 Cost, stated before anyone spends: $6–15, at list price.** The anchor
is round 6's per-cell spend on the same three combinations, which is the only
place in the corpus where all three have been priced over one selection:
**$0.0783** a cell on `claude-haiku-4-5`, **$0.2086** on `claude-sonnet-5` and
**$0.0717** on `codex` × `gpt-5.6-terra` (§54; the last of the three is
table-derived). That is **$0.3586 — about $0.36 — a task across the three
combinations**, so fourteen tasks come to **about $5** if TypeScript cost what
Python did. The registered range is **$6–15**, which is that $5 multiplied by
roughly 1.2 at the low end and 3 at the high end, and the headroom is for two
identifiable things rather than for comfort: **fresh scenario types** — a
service, an event flow, a stream, a CLI over real files, a binary frame format
— none of which the corpus has exercised at any price, and **a toolchain the
corpus has not exercised at all**, where an agent may spend turns on
`node --test`, on module resolution and on TypeScript's own errors before it
spends any on the task.

**The bound is caching-aware, and both ends of it are registered.** Round 6
missed its range 2.3× low for one identifiable reason: §52.4 priced every
input token as uncached, so the registration landed on the round's *upper*
bound (§54, and `docs/agents/sweep-protocol.md`, "Before the sweep" item 2).
The fix is in the estimate, not in the stance, so this section registers the
Codex column at both ends. Round 6's thirty Codex cells read **3,892,528**
input tokens and wrote **49,636** — 129,751 in and 1,655 out a cell — so
fourteen cells at the same rate are about **1,816,513 input** and **23,163
output** tokens. At `data/price-table.json`'s `gpt-5.6-terra` prices the output
is **$0.2780** whatever happens, and the input is **$3.6330 all-uncached**
($2/M) against **$0.3633 all-cached** ($0.20/M). So the Codex column is
registered at **$0.64 all-cached to $3.91 all-uncached**, with round 6's
observed effective input rate of $0.3996/M putting the expected figure near
**$1.00**. The two Claude columns are **vendor-reported** and carry no such
split: 14 × $0.0783 = **$1.0962** on haiku and 14 × $0.2086 = **$2.9204** on
sonnet, **$4.0166** together. Added up at Python-equal token counts the whole
round is **$4.66 all-cached to $7.93 all-uncached** — an envelope whose upper
end sits inside the registered $6–15 rather than at its floor, which is
exactly the mistake round 6 made. **The one way this round misses low is
registered here too**: if TypeScript costs no more than Python *and* the Codex
column caches as well as round 6's did, the round lands near $5 and under the
range. That outcome is a finding about the toolchain, not an accounting
surprise, and the record is to say so against this line.

**Why those are list prices and not a bill.** The operator's Codex is
authenticated by **ChatGPT login**, not by an API key, so a Codex run is **not
billed per token** at all. Every Codex figure above and in the round's record
is therefore a **list-price equivalent** — tokens × `data/price-table.json`,
stamped `cost_source: table-derived` with the table's version beside it — and
not an invoice anyone received. A claude-code row's `vendor-reported` figure
is made differently, which is what the `cost_source` field exists to disclose,
and the round's record has to carry that difference rather than average across
it. Round 7 is the first round where the two kinds of dollar are produced by
the *same* sweep over the *same* task, so the disclosure matters more here
than it did in round 6, not less.

**59.5 The limits in force: 600 seconds, every cell, and nothing new is
registered.** `bug-fix`, `fault-location`, `code-review` and
`codebase-comprehension` are registered at 600 in `LIVE_RUN_LIMITS_S`
(`src/ai_benchmark/firstparty_v1.py`) — round 4's two by §37 and round 5's two
by §46. `feature-dev` and `refactor` are **not** in that table, and this
ticket adds nothing to it: those six cells per combination run under the
**flat default**, `RUN_TIMEOUT_S` in `src/ai_benchmark/firstparty.py`, which is
numerically the same 600 seconds and is not a registration. The spec does not
ask for a new limit and none is taken. What is worth saying once, because
round 7 is the first round with two languages in it, is that **the limit comes
out of the same table for every language**: `live_run_limit_s` is keyed on a
task's *category* alone and never on its language or its runner, so **no cell
gets a longer run because of its toolchain**. If `node --test` is slower than
`pytest`, that shows up as a run that spent more of its 600 seconds, never as
a cell that was given more of them. And because 600 is the number in force for
every cell of this round and of every earlier one, **no cross-round caveat
arises** and none is implied — the limit is still a narrated ceiling rather
than a field stamped on a row (CONTEXT.md's live run-time limit entry).

**59.6 How the sweep is invoked.** Sweep id **`round-7`**, on every invocation
of it. Run by hand under `docs/agents/sweep-protocol.md`, never queued.

A **dry cell first**, in its own invocation: one of the forty-two, run alone,
so that a mis-shaped grade on the new runner — the failure mode a new language
adds, where `node --test` runs but its per-testcase verdicts are read wrongly
— is discovered on **one paid run rather than forty**. It is a real, paid,
graded run and one of the round's forty-two; it is **not** a rehearsal to be
re-run, because a task × agent × model cell is only ever swept once. Its log
is named like any other log of the sweep: the sweep protocol **bans `-dry` in
a log's name**, because round 1 left two paid cells in `-dry`-named logs and
the first pass of that analysis silently dropped both. The rest follow in
further invocations carrying the same `--sweep round-7` and their own fresh
`--log` paths.

The cells are chosen on the command line with **`--task`**, repeated once per
id, and never by staging a cut-down worktree: the filter refuses an id naming
no task in the set before anything runs, and runs the filtered set in corpus
order. So the dry cell is

```
uv run ai-bench eval-v1 --live --sweep round-7 --agent codex \
  --model gpt-5.6-terra --task <one of the fourteen> --log <a normally-named log>
```

and each further invocation is the same line with the remaining ids, the other
agent and its two models, and a fresh `--log` path, the runner refusing to
append to a log that already exists.

**59.7 What the round cannot say, registered in advance.** Four readings are
ruled out now rather than argued about against the numbers later.

- **No cross-language transfer reading.** Nothing was ported. Not one of the
  fourteen is a TypeScript rewrite of a Python task, so there is no matched
  pair anywhere in the corpus and no "the same task in two languages" figure
  can be computed from this round however the columns are lined up.
- **No Python-versus-TypeScript difficulty claim.** The grid widens
  **scenario**, not difficulty: these tasks were authored for what the Node
  standard library can do, and they differ from the Python corpus in what they
  are about as much as in what they are written in. A resolution rate that
  differs between the two languages is confounded with the scenarios by
  construction, and this round registers no contrast that would separate them.
- **No Codex rung.** `gpt-5.6-terra` is one model, and **one model is not a
  ladder**. The two-model ladder is claude-code's; the Codex column can say
  what a second harness did, never what a cheaper second-harness model would
  have done.
- **No multiplier.** A multiplier is computed from a constructed task against
  its category's control baseline, and **there is no constructed TypeScript
  task** in the corpus — all fourteen are controls. `calibrate-v1` therefore
  gains no TypeScript multiplier row from this round, and the absence is the
  design rather than a gap in it.

**59.8 The coverage target, as the lint actually prints it.** Acceptance is a
figure read off `uv run ai-bench lint-v1`'s coverage table rather than a task
count somebody remembers. The table has one row per (category, surface,
language) that has tasks, plus a `(category, "-", "-", 0)` row for a category
with no task in **any** language, so what it can show is this: exactly **five
`typescript` × `application` rows** —

```
  bug-fix                    application  typescript  3
  fault-location             application  typescript  3
  feature-dev                application  typescript  3
  refactor                   application  typescript  3
  code-review                application  typescript  2
```

— and **no `typescript` row** for `test-authoring` or for
`codebase-comprehension`. Those two are registered here as **zero by
absence**, which is all the table can express, and the reasons are on the
record: `test-authoring` has no task in any language because it needs a
mutation gate and a new verdict shape (§45.12) and is out of round 7's scope,
so it still prints as `test-authoring - - 0`; `codebase-comprehension` prints
only its Python row (`application python 4`) because no locate-style
comprehension task was authored in TypeScript this round. **The lint is not
changed** to print registered-zero cells per language: the round buys no
coverage-table generalisation, and adding one would move the printed table
inside every earlier round's record suite for no reading this round needs.

The `python` column is **unchanged at 113** — 6 `bug-fix`, 6
`fault-location`, 71 `feature-dev`, 18 `refactor`, 4
`codebase-comprehension`, 8 `code-review` — because round 7 authored no Python
task and re-ran none. What does move is the readers' corpus-count header:
`reconcile-v1` and `calibrate-v1` count the task set they were pointed at, so
the line that read **113 task(s)** now reads **127 task(s)**, and any figure
those readers print over `claude-code`'s Python rows is unchanged beneath a
header that counts fourteen more tasks than it did.

## Round 7 verdicts — 2026-08-20

**§60 is the next free number.** §59 is round 7's pre-registration and the last
section written before the sweep, so this record opens at **60** and runs to
**66**. Nothing above it is renumbered.

### 60. What the round measured

**Forty-two cells, and they are exactly the forty-two §59.1 registered.**
Fourteen TypeScript tasks × three combinations, every one of them swept and
logged: **42 of 42**, with nothing dropped and nothing added. The fourteen ids
the rows carry are the fourteen the register lists — 3 `bug-fix`, 3
`fault-location`, 3 `feature-dev`, 3 `refactor`, 2 `code-review` — and each is
swept once per combination and never twice.

**One sweep id, and the harness versions it ran under.** Every row carries
`sweep: round-7` and `as_of: 2026-08-20`. The version is single within each
harness's rows: `claude-code` at **2.1.235**, a step from round 6's 2.1.234 and
disclosed here because the protocol requires a version boundary to be visible
rather than because it is known to matter; `codex` at **codex-cli 0.147.0**,
which is round 6's exactly, so the Codex column crosses no version boundary
between the two rounds. The reasoning level rides with the model
(`ai_benchmark.agents.CODEX_REASONING_LEVELS` is `{"gpt-5.6-terra": "medium"}`)
and no invocation could have asked for another.

**Eight invocations, eight logs, one of them empty.** `r7-a` is the **dry
cell** §59.6 required: one of the forty-two, run alone and paid for, so that a
mis-shaped grade on a brand-new runner would be found on one cell rather than
forty. It is `leftluggage-locate-the-charge-nobody-arrived-at` on `claude-code`
× `claude-haiku-4-5`, and it **resolved** — the TypeScript runner's first paid
verdict. §59.6 wrote its example command with `--agent codex`; the cell
actually run alone was a claude-code one, which is a departure from the
example and from nothing else: the registration's requirement was *a* dry cell
from among the forty-two, and one was run. `r7-b` carries haiku's other
thirteen and `r7-c` sonnet's fourteen. The Codex column took **four**
invocations — `r7-d`, `r7-e`, `r7-g`, `r7-h` — because the codex stream twice
died mid-run on a TLS handshake EOF; the adapter's broken-run rule ended each
loudly and wrote **no row**, and the empty `r7-f` is the record of an
invocation that logged nothing before the same failure. No cell is missing on
account of any of it: the interrupted cells were re-run in the following
invocation, and the fourteen ids appear once per combination.

**Resolution: 40 of 42.** **12 of 14** on `claude-haiku-4-5`, **14 of 14** on
`claude-sonnet-5`, **14 of 14** on `codex` × `gpt-5.6-terra`. Both misses are
haiku's and both are `code-review`; §63 reads them beside the scenario they
belong to rather than as a language result.

**The limits in force: 600 seconds, every cell, and nothing new registered.**
`bug-fix`, `fault-location`, `code-review` and `codebase-comprehension` are the
four categories registered at 600 in `LIVE_RUN_LIMITS_S`; `feature-dev` and
`refactor` are not in that table and ran under the flat default,
`firstparty.RUN_TIMEOUT_S`, which is numerically the same 600. The limit is
keyed on a task's category alone and never on its language or its runner, so
**no cell got a longer run because of its toolchain**, and because 600 is the
number in force for every cell of this round and of every earlier one, **no
cross-round caveat arises** and none is implied. Nothing came near it: the
round's longest run was **189.6 s** (`seedbank-book-out-what-the-store-hands-over`
on Codex) and the mean was **87.0 s**, so no verdict here is a timeout in
disguise.

**The toolchain the sweep graded under: Node v22.22.2, and Python 3.14.4
beside it.** Both are recorded because a TypeScript verdict is `node --test`'s
and a Python verdict is `pytest`'s, and a reader re-grading these diffs on a
different Node may get a different answer for reasons that have nothing to do
with the agent. They are **provenance and not row fields**: round 7 added **no
`runner` field and no `toolchain` field** to a run-log row or to a record, and
this record proposes none. A record's `language` is not new either — it has
been in `record.schema.json` since the schema seam was first reviewed — and
what round 7 did was fill it with a second value, `typescript`, on 42 records.

### 61. Spend, by cost source, against the range registered before it

**The three columns, kept apart by how their dollars were made:**

```
claude-code x haiku     $1.4532  vendor-reported (what the account was billed)
claude-code x sonnet    $4.2344  vendor-reported (what the account was billed)
codex x gpt-5.6-terra   $1.6046  table-derived   (list price, openai-pricing-2026-08-18.1)
```

**What the account was actually billed: $5.6877, and nothing per token for
Codex.** The operator's Codex is authenticated by **ChatGPT login**, not by an
API key, so no Codex run in this round was billed per token at all. The
$1.6046 is this repository's own arithmetic — the round's Codex tokens priced
through `data/price-table.json` at version **`openai-pricing-2026-08-18.1`**,
stamped `cost_source: table-derived` on all fourteen rows — and it is a
**list-price equivalent, not an invoice**. The two claude-code columns are the
vendor's own figures, `cost_source: vendor-reported`, and their sum is what was
billed.

**The registered range was $6–15. The round came to $7.2923, and it was
honoured.** That total is the form §59.4 registered the bound in — the three
columns added — and it is therefore a quantity with an estimate inside it,
which is why the block above prints the three separately and why this section
states the billed figure on its own line. **Every total here is summed before
rounding**, so a reader who adds the printed columns instead will find a last
digit that differs: $7.2922 rather than $7.2923 for the round, $5.6876 rather
than $5.6877 for the bill. The difference is rounding and nothing else. Round 6
missed its range 2.3× low by pricing every input token as uncached and so registering at its own upper bound; §59.4 fixed the
*estimate* rather than the stance and registered an envelope of **$4.66
all-cached to $7.93 all-uncached**. The round landed at **$7.2923**, inside
that envelope and near its upper end, and inside the registered $6–15.

**Each column against what was registered for it.** §59.4 registered 14 ×
round 6's per-cell figures for the two Claude columns and a two-ended band for
Codex:

```
                        registered            actual     per cell   round 6
claude-code x haiku     $1.0962               $1.4532    $0.1038    $0.0783
claude-code x sonnet    $2.9204               $4.2344    $0.3025    $0.2086
codex x gpt-5.6-terra   $0.64-$3.91 (~$1.00)  $1.6046    $0.1146    $0.0717
```

Every column came in **above** its Python-equal registration and the Codex one
landed inside its band, above the ~$1.00 expectation: **1.33×** on haiku,
**1.45×** on sonnet, **1.60×** on Codex, per cell. §59.4's registered
downside — "if TypeScript costs no more than Python *and* the Codex column
caches as well as round 6's did, the round lands near $5 and under the range" —
**did not happen**, and both halves of it failed: the cells cost more, and the
caching was worse.

**What a Codex row can and cannot reproduce.** The round's Codex cells read
**2,169,811** input tokens and wrote **30,396** — against the 1,816,513 and
23,163 §59.4 projected from round 6's rate. Priced at
`openai-pricing-2026-08-18.1` those tokens bound the column at **$0.7987
all-cached** and **$4.7044 all-uncached**, and the logged **$1.6046** sits
between them, as it must. The split it was actually priced from is not on the
row: the effective input rate the round paid works out at **$0.5714/M**,
against round 6's **$0.3996/M** on the same model and the same table. A round
of fresh repositories caches less well than a round of already-answered ones,
which is a fact about the sweep and not about TypeScript.

### 62. The forty-two cells under three combinations

Every cell, its verdict and its cost, with each column's **cost source** in the
header where a reader cannot join the three without seeing it:

```
                                                        claude-code x       claude-code x       codex x
                                                        claude-haiku-4-5    claude-sonnet-5     gpt-5.6-terra
                                                        vendor-reported     vendor-reported     table-derived
courtleet-put-the-verdicts-on-one-table                 resolved   $0.0746  resolved   $0.2910  resolved   $0.0964
gasworks-take-the-press-out-of-the-roll-room            resolved   $0.0994  resolved   $0.2488  resolved   $0.0975
leftluggage-locate-the-charge-nobody-arrived-at         resolved   $0.0793  resolved   $0.1919  resolved   $0.0616
leftluggage-put-the-unweighed-bag-back-on-the-scales    resolved   $0.1595  resolved   $0.2349  resolved   $0.1707
limekiln-review-the-drawing-and-the-carting             unresolved $0.1227  resolved   $0.3725  resolved   $0.1432
lockhouse-locate-the-boats-that-never-reached-the-book  resolved   $0.1160  resolved   $0.1546  resolved   $0.0598
lockhouse-work-the-rest-of-the-night-through            resolved   $0.0958  resolved   $0.2495  resolved   $0.1435
masonsyard-review-the-lettering-and-the-account         unresolved $0.0590  resolved   $0.5026  resolved   $0.0955
parishchest-seal-the-register-against-a-later-hand      resolved   $0.0770  resolved   $0.2827  resolved   $0.1228
seedbank-book-out-what-the-store-hands-over             resolved   $0.1654  resolved   $0.5956  resolved   $0.1962
telegraph-locate-the-message-left-on-the-tape           resolved   $0.0700  resolved   $0.1659  resolved   $0.0935
telegraph-write-up-the-last-message-of-the-day          resolved   $0.1161  resolved   $0.2195  resolved   $0.1310
tollhouse-take-the-writing-of-a-pass-off-the-ticket     resolved   $0.0995  resolved   $0.2976  resolved   $0.0934
weighbridge-put-the-second-weighing-on-the-tape         resolved   $0.1190  resolved   $0.4274  resolved   $0.0994
```

And the same forty-two by the **action** each task is declared under, with `n`
printed beside every count because a rate over two cells is not a rate:

```
category         n   haiku              sonnet             codex
bug-fix          3   3/3  $0.3714       3/3  $0.7039       3/3  $0.4452
code-review      2   0/2  $0.1817       2/2  $0.8751       2/2  $0.2387
fault-location   3   3/3  $0.2653       3/3  $0.5125       3/3  $0.2150
feature-dev      3   3/3  $0.3614       3/3  $1.3056       3/3  $0.4184
refactor         3   3/3  $0.2734       3/3  $0.8374       3/3  $0.2872
all five        14   12/14  $1.4532     14/14  $4.2344     14/14  $1.6046
```

`n` is 3 in four rows and 2 in the fifth. Nothing in this block is a rate worth
quoting on its own, and the reading the round is entitled to is in §63.

**Turns, for what they are worth on each side.** Haiku took **183** turns over
the fourteen (4–23), sonnet **168** (7–23), Codex **130** (6–13). A Codex turn
is a completed non-reasoning item and a claude-code turn is `num_turns`, so the
three numbers are **not** comparable across the harness boundary — §65 refuses
that comparison as round 6's §57 did, and these are quoted only so that the
refusal is anchored to something.

### 63. Per scenario, not per syntax

The reading this round is entitled to is about the **work**, not the
punctuation. Each of the fourteen was authored for something the Node standard
library does and the Python corpus has nothing like, so the row that means
anything is the scenario:

```
scenario                   module        n   haiku              sonnet             codex
a node:http service        node:http     2   2/2  $0.2388       2/2  $0.4268       2/2  $0.2324
an async / event flow      node:events   2   2/2  $0.2118       2/2  $0.4042       2/2  $0.2033
a stream pipeline          node:stream   2   2/2  $0.1861       2/2  $0.3854       2/2  $0.2245
a CLI over the filesystem  node:fs       1   1/1  $0.1654       1/1  $0.5956       1/1  $0.1962
fixed-width frames         node:buffer   1   1/1  $0.1190       1/1  $0.4274       1/1  $0.0994
a digest chain             node:crypto   1   1/1  $0.0770       1/1  $0.2827       1/1  $0.1228
a compression seam         node:zlib     1   1/1  $0.0994       1/1  $0.2488       1/1  $0.0975
a pass written as a link   URL           1   1/1  $0.0995       1/1  $0.2976       1/1  $0.0934
a table of verdicts        node:vm       1   1/1  $0.0746       1/1  $0.2910       1/1  $0.0964
two reviews to file        -             2   0/2  $0.1817       2/2  $0.8751       2/2  $0.2387
```

The `module` column is what the scenario is built on — a `node:` builtin in
eight rows, and the WHATWG `URL` in the ninth, which Node exposes as a global
as well as out of `node:url`. Every task in a row uses what its row names. The first three rows are the round's three planted
defects, each counted twice because each repository carries a `bug-fix` cell
and a `fault-location` cell.

**Nine of the ten scenarios resolved under all three combinations.** A service
that answers over `node:http`, an event flow that has to finish the night, a
stream that has to flush what it is holding, a CLI that has to write to a real
directory, a fixed-width frame format, a digest chain, a compression seam, a
URL round-trip and a `node:vm` dispatch table were each put right, located, or
built by every one of the three. The one row that is not 3-for-3 is the last.

**The reviews, read.** `masonsyard` and `limekiln` each plant three findings
and each list two rejected ones. Across the six review cells the answers split
**16 accepted, 0 rejected, 0 unlisted**, and all sixteen named the finding's
**primary** location. Sonnet and Codex each filed all three findings on each
repository. Haiku filed **two of three** on each and stopped: it named
`carting.ts / Sheet.carts` and `spells.ts / spellsIn` on `limekiln`, missing
`dockets.ts / Docket.asFigure`; and `inscription.ts / asCut` and `orders.ts /
Book.strikeOff` on `masonsyard`, missing `account.ts / Account.comesTo`. **It
tripped no rejected finding and filed nothing unlisted.** So both misses are
**under-reporting and not false accusation** — the failure mode of a reviewer
who stopped early, not one who cried wolf — and the verdict is unresolved
because a review resolves only when the answer covers every planted finding.

**What that cell is and is not.** `code-review` under a TypeScript repository
resolved less often on `claude-haiku-4-5` than the other nine scenarios did:
0 of 2 against 12 of 12. That is a fact about **that scenario under that
combination**, on a denominator of two. It is not a ratio worth quoting, not a
language result, and not comparable to haiku's Python `code-review` rate — the
tasks are different tasks. §65 says why in full.

**ADR-0003, and what an agent installed: nothing that reaches a verdict.** The
stdlib-only rule says a package an agent installs is neither captured in the
diff nor present at grade time, so a solution resting on one fails. The
disclosure this record owes is therefore per cell, and the answer is that
**no cell of round 7 was touched by an agent-installed dependency**. Three
things are true of all forty-two diffs: none adds a `package.json`, a lockfile
or any path under `node_modules`; **no added line imports a bare specifier** —
every `import` in every diff resolves either relatively or to a `node:`
builtin; and the fourteen starting repositories import nothing but `node:`
builtins themselves. The forty resolved cells therefore resolved on the
standard library, and the two unresolved ones are the review misses above,
which install nothing because a review answer is a JSON file.

### 64. The coverage table, as the lint prints it

`uv run ai-bench lint-v1` reports **`lint clean: 127 task(s)`** and prints:

```
coverage: category x surface x language
  category                   surface      language    count
  bug-fix                    application  python      6
  bug-fix                    application  typescript  3
  feature-dev                application  python      71
  feature-dev                application  typescript  3
  refactor                   application  python      18
  refactor                   application  typescript  3
  test-authoring             -            -           0
  codebase-comprehension     application  python      4
  fault-location             application  python      6
  fault-location             application  typescript  3
  code-review                application  python      8
  code-review                application  typescript  2
  investigation              -            -           0
  requirement-decomposition  -            -           0
  performance-optimisation   -            -           0
  unclassified               -            -           0
```

**The five `typescript` rows are at the registered counts** — `bug-fix` 3,
`fault-location` 3, `feature-dev` 3, `refactor` 3, `code-review` 2, every one
of them `application` — which is §59.8's target met exactly. The **`python`
column is unchanged at 113**: 6 `bug-fix`, 6 `fault-location`, 71
`feature-dev`, 18 `refactor`, 4 `codebase-comprehension`, 8 `code-review`,
because round 7 authored no Python task and re-ran none.

**Why the two absent cells read zero, in §59.8's wording: they are zero by
absence, which is all the table can express.** The table has one row per
(category, surface, language) that has tasks, plus a `(category, "-", "-", 0)`
row for a category with no task in **any** language. So `test-authoring` prints
as `test-authoring - - 0` — it has no task in any language at all, because it
needs a mutation gate and a new verdict shape (§45.12) and was out of round 7's
scope. And `codebase-comprehension` prints **only** its Python row,
`application python 4`, because no locate-style comprehension task was
authored in TypeScript this round; there is no `codebase-comprehension … typescript 0`
line and there was never going to be one. **The lint was not changed** to print
registered-zero cells per language, exactly as §59.8 said it would not be: the
generalisation buys no reading this round needs and would move the printed
table inside every earlier round's record suite.

### 65. What this round cannot say

Four readings were ruled out in §59.7 before the numbers existed. Restated
against the numbers, they all still hold.

- **No cross-language transfer reading.** Nothing was ported. Not one of the
  fourteen is a TypeScript rewrite of a Python task, so no matched pair exists
  anywhere in the corpus and no "the same task in two languages" figure can be
  computed from these forty-two rows however the columns are lined up.
- **No Python-versus-TypeScript difficulty claim.** The grid widens
  **scenario**, not difficulty. The fourteen differ from the Python corpus in
  what they are about — a service, an event flow, a stream, a CLI over real
  files, a binary frame format — as much as in what they are written in, so any
  rate that differs between the two languages is confounded with the scenarios
  by construction. This applies to the **cost** figures too: §61's 1.33×, 1.45×
  and 1.60× are TypeScript-and-fresh-scenarios against Python-and-answered-ones,
  and the round registered no contrast that could separate the two.
- **No Codex rung.** `gpt-5.6-terra` is one model and **one model is not a
  ladder**. `reconcile_v1.LADDER_MODELS` is the two claude-code models and the
  Codex column is not in it; the column can say what a second harness did on
  these fourteen, never what a cheaper second-harness model would have done.
- **No multiplier.** All fourteen are declared controls with no construction
  block, so `calibrate-v1` gains no TypeScript multiplier row from this round.
  The absence is the design, not a gap in it. Round 7 moves no knob's counter
  and the kill discipline does not count it.

Two more refusals this round's numbers make it tempting to break:

- **No cross-harness turn comparison.** §62's 183, 168 and 130 are counted
  differently on each side of the harness boundary — a Codex turn is a
  completed item that is not a reasoning item, a claude-code turn is
  `num_turns` — so the Codex column being lowest is a fact about two counting
  rules meeting, not about two harnesses working.
- **No ratio out of the review cell.** `code-review` on haiku is 0 of 2 and the
  other nine scenarios are 12 of 12. The record states both counts and their
  denominators and quotes **no ratio**, because a rate over two cells is not a
  rate and because §63's reading — two under-reports, no false accusation — is
  what those two cells actually contain.

### 66. Replay, and the published tables left where they were

**Every round-7 log replays to the verdicts this record quotes.** Each of the
eight was replayed into a scratch dataset of its own, and all eight into one
merged dataset; the eight together are the merged one record for record:

```
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-a.jsonl --data /tmp/r7replay/a.jsonl
  evaluated 1 runs over 127 tasks (1 resolved)
  merged 1 records into /tmp/r7replay/a.jsonl (1 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-b.jsonl --data /tmp/r7replay/b.jsonl
  evaluated 13 runs over 127 tasks (11 resolved)
  merged 13 records into /tmp/r7replay/b.jsonl (13 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-c.jsonl --data /tmp/r7replay/c.jsonl
  evaluated 14 runs over 127 tasks (14 resolved)
  merged 14 records into /tmp/r7replay/c.jsonl (14 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-d.jsonl --data /tmp/r7replay/d.jsonl
  evaluated 9 runs over 127 tasks (9 resolved)
  merged 9 records into /tmp/r7replay/d.jsonl (9 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-e.jsonl --data /tmp/r7replay/e.jsonl
  evaluated 2 runs over 127 tasks (2 resolved)
  merged 2 records into /tmp/r7replay/e.jsonl (2 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-f.jsonl --data /tmp/r7replay/f.jsonl
  evaluated 0 runs over 127 tasks (0 resolved)
  merged 0 records into /tmp/r7replay/f.jsonl (0 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-g.jsonl --data /tmp/r7replay/g.jsonl
  evaluated 2 runs over 127 tasks (2 resolved)
  merged 2 records into /tmp/r7replay/g.jsonl (2 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r7-h.jsonl --data /tmp/r7replay/h.jsonl
  evaluated 1 runs over 127 tasks (1 resolved)
  merged 1 records into /tmp/r7replay/h.jsonl (1 total)
```

42 rows and 40 resolved, which is §60's resolution line reached a second way.
The empty `r7-f` replays to **nothing rather than to an error**, which is all
an invocation that logged no row can be shown to do. Every merged record also
carries its log row's own measurements — cost, turns, tokens, latency, version
— because replay re-grades the diff and never re-runs the agent, and for a
Codex row that is the whole of the claim that a table-derived cost is not
recomputed on the way through.

**`evaluated … over 127 tasks` is one of the three counts ticket 06 worked
through, and it is the only one that moved.** `eval-v1 --replay` has no
language selection: it counts the task set it was pointed at, so the line that
read 113 now reads **127**. The pins that see it derive the number from the
loaded task set rather than from a literal, which ticket 08 arranged when the
corpus first grew, and they read 127 today without being moved by this ticket.

**§59.8 predicted the readers' corpus header would move 113 → 127. It did not,
and the code changed under the prediction.** The commit that made
`reconcile-v1` and `calibrate-v1` select a language narrowed **the task set
with the rows** rather than the rows alone, so a default reading counts the
tasks of the language it selected. What the two readers print is therefore:

```
  task set   tasks/first-party-v1 — 113 task(s): 46 control(s), 67 constructed
  runs       225 over 113 task(s)
  rounds     6 round(s): as-of 2026-08-04, as-of 2026-08-05, sweep round-2, sweep round-3, sweep round-4, sweep round-5
```

**Six rounds, not seven**, and 225 runs — the corpus's `claude-code` Python
rows, exactly what they were before the round. The forty-two round-7 rows are
in the same directory both readers are pointed at, so "unmoved" here means
**read and dropped**, not absent: the eight round-7 logs are named in the
provenance list above those counts, and no `sweep round-7` and no
`gpt-5.6-terra` and no `typescript` appears anywhere in either report. Every
fenced calibration block rounds 4 and 5's records published still prints byte
for byte what it printed then, counted fields aside.

**And the TypeScript side is reachable by asking for it.** With `--language
typescript`, `reconcile-v1` reads `14 task(s): 14 control(s), 0 constructed`,
`runs 28 over 14 task(s)` and `1 round(s): sweep round-7` — 28 rather than 42
because the agent selection is a separate one and drops the Codex column
unless it too is asked for.

## Round 8 rulings — 2026-08-20

§45.15 left round 8 unruled with two candidates queued — the heap-3
subjective grader (§34.3) and the `test-authoring` mutation gate (§45.12) —
their order to be set on the widening round's record. That record exists
(§§60–66), #97 is closed, and this section records the grill of 2026-08-20.
**§67 is the next free number.** Like §45, this section authors nothing: it
is the input to `/to-spec`, which files one spec for the round.

### 67. What round 8 is

**67.1 Round 8 is the test-authoring round: the mutation gate. The heap-3
subjective grader is round 9's, and its calibration experiment does not run
in parallel.** Three reasons, in the order they carried the ruling. A round
carries **one new instrument** — the discipline that gave the Codex adapter
its own round (§45.13) so it would not be confounded with the language
runner; the grader is *two* instruments (the grader and the experiment that
proves it worth trusting, §34.3), the gate is one. The gate closes the **only
registered zero** in the coverage table — `test-authoring`, the one heap-1
action with no tasks in any language — and with it heap 1 entire. And
waiting costs the grader nothing while paying it: the free-text archive
§34.4 built for its calibration stands at **297 answers across eight
sweeps** today and grows by every round that runs first. A third option was
put and declined: the calibration experiment reads the archive and sweeps
nothing, so it *could* run beside round 8 without sharing a row with it —
but one instrument per round is the ruling, not one confound per round.

**67.2 Python only; the TypeScript cell stays a disclosed zero.** The round's
one new instrument is a new **verdict shape**, and it pairs with the mature
harness so that a failure attributes cleanly — the same reasoning as 67.1's
discipline, applied within the round. `test-authoring × typescript` remains
`0` in the coverage table, disclosed rather than omitted as that table
already does, and filling it is a mechanical follow-on for any later round
once one round's record has proven the gate.

**67.3 The verdict is binary and its quantifier universal: the suite passes
on the pristine starting repository — no exceptions — and every planted
mutant is killed by at least one test.** Both halves of the industry's usual
alternative were rejected. A kill-rate threshold ("≥80% killed resolves")
makes `resolved` quietly mean something else on one action — a hidden second
quality metric on a corpus whose glossary rules that values under different
quality metrics never compare. A continuous kill-rate score is the same
move without the disguise. The findings key already owns the stance — "the
verdict is binary — partial recall is not a score" — and this is that
quantifier pointed at mutants: a review resolves when every planted finding
is covered, a suite resolves when every planted mutant is killed. The
universal quantifier also keeps precision where it belongs: every mutant
the author plants must really be killable (67.5), where a threshold would
let a doubtful one hide in the slack. Gate 1 admits no exception for the
symmetric reason: one failing test on correct code is the false accusation
the findings key's rejected half refuses.

**67.4 Grading collects only the prompt-named test subtree from the workdir
diff; everything outside it is archived, not scored; mutants touch only
source files, and the lint checks the disjointness.** Without this ruling
the gate has two holes: applied whole, an agent's source edits could
overwrite a mutation (gate 2 dies) or bend the code toward a wrong suite
(gate 1 dies). The shape is the **answer file**'s precedent — the
deliverable lands "at a path the prompt names" and grading reads it there —
widened from one file to one subtree; the disposition of everything else is
the findings key's — "archived, not scored". An agent that edits source is
not committing a foul; its edits simply do not exist in the world the gates
run in, and if its suite needed them, gate 1 goes red honestly. The
alternative — declaring source edits a violation — was rejected as a second
adjudication surface (is a comment edit a violation? an added
`__init__.py`?) that the collection rule dissolves entirely.

**67.5 Mutants are hand-planted, and the existence proof registered for
this action is the reference suite: it passes on the pristine repository
and fails at least one test on every mutant, checked per mutant by the
lint.** Hand-planting is "plant the ground truth" continued — and the
stronger the quantifier, the more the key must be hand-made: operator-style
generation (mutmut and kin) is cheap per mutant but carries the *equivalent
mutant* — a change no behaviour distinguishes — which under 67.3 makes a
task permanently unresolvable for every agent. The registered proof form is
what refuses one mechanically: a mutant no reference test kills is rejected
at the lint, before any agent meets it. The form is code-review's proof
aggregated — there, one held-out test per planted finding; here, one suite
whose per-mutant kills the lint checks individually, with equal proof
force and one fewer concept — and it lands on an existing institution,
since a task's reference solution is already the author being their task's
first perfect agent. Proof materials live in the task's own subtree outside
`grading/`, the address existence proofs already keep: never overlaid,
never collected, never read by a verdict.

**67.6 Three fresh-authored small repositories; the prompt is a complete
behavioural specification naming the test path; the mutant set is
undisclosed; the module under test has zero existing tests; and the terrain
rule is exempted at the action level.** Fresh-authored is §45's stance
("fresh-authored not ported"), and this action's repositories carry
requirements porting would fight: a specification precise enough to test
against, and nothing already testing it — an existing suite is a crib, so
the lint checks the starting repository's test path is empty of the module
under test. The prompt discloses the spec fully (the corpus's standing
style: prompts are complete specs) and the mechanism not at all — the
mutant set has exactly the held-out status grading tests have always had.
The terrain exemption is recorded with its reason: the rule stops a key
being grepped out of the workdir, and this key is never in the workdir; the
prompt must name the module under test because that is the task's
definition, not a leak. It is an **action-level exemption, not three
`terrain_waiver` declarations**: the waiver mechanism is per-task and
reason-per-task, and three tasks carrying one identical action-shaped
reason is the smell that mechanism was not built for.

**67.7 Four to six mutants per task; the lint enforces a minimum of three
and no maximum; distribution across behaviours is authoring judgement, not
a lint rule.** Below three, the universal quantifier barely binds and one
lucky assertion clears the gate; above six, hand-planting plus per-mutant
proof (67.5) buys noise — six variants of one line are repetition, not
strength. The spec carries the guidance that mutants spread across distinct
specified behaviours, and it stays guidance: one test killing two mutants
is legal, since 67.3's quantifier binds mutants and not tests, and a
formal distinctness rule was declined — the findings key's "distinct
through the comparison" closes a one-answer-satisfies-two-findings hole
that this quantifier's direction does not have.

**67.8 The sweep: nine cells — three tasks under the three standing
columns — with **$1.5–5** registered before the first paid run and a dry
cell first.** The columns are §45.13's own ruling ("from round 7 on, Codex
is a second column"): claude-code × haiku, claude-code × sonnet, codex ×
gpt-5.6-terra. A flat extrapolation from round 7's per-cell figures puts
nine cells at ≈$1.57; the headroom is for the two lessons round 7 actually
realized — fresh repositories cache worse, and this deliverable (a whole
test suite) is a larger write than a locate answer. The dry-cell rule
(§59.6) is kept because it exists for exactly this round's situation, a
brand-new verdict shape meeting its first paid diff: one cell — claude-code
× haiku, the cheapest — runs and grades alone before the other eight.
`test-authoring` joins no `LIVE_RUN_LIMITS_S` row: it runs at the flat
default of 600 s, and the round's record will say "at the flat default" in
§46's registered sense of the distinction.

**67.9 The three queued side-rulings are deferred again, each with the
trigger that would ripen it.** **`frontend`** (§45.11): its own grill when
someone actually wants a frontend reading — the substrate-or-browser-runner
question deserves a session, not a paragraph here. **A second Codex-side
model**: when a specific reading needs a Codex rung — §65's refusal ("one
model is not a ladder") stands until a reading is worth its cells, and
column symmetry is not a reason. **Repeat sampling** (§45.16): after heap 3
lands and the action coverage closes — a whole-corpus sampling round on a
settled corpus beats adding n per round, which is §45.16's own sentence,
and the corpus is not settled while rounds 8 and 9 are still adding actions.

**ADR owed: ADR-0004, the mutation-gate verdict shape, lands with round
8's spec** — the §45.16 pattern, as ADR-0003 landed with round 7's. All
three of the ADR conditions hold: the verdict shape is expensive to
reverse once records carry it, binary-all-killed will surprise a reader
raised on kill rates, and 67.3 records the real alternatives it was chosen
over. The glossary gains **mutation gate** and **planted mutant** with this
section, marked as landing with round 8.

## Round 8 cells and cost — registered 2026-08-20

**68. The round's three tasks, its three combinations and its cost range,
written down before the first paid run.** This is round 8's pre-registration
and nothing else: §46 did it for round 5, §52 for round 6 and §59 for round 7,
and the discipline does not relax for a round whose novelty is a **verdict
shape** rather than a task knob, an agent or a language. If anything a new gate
is the thing a sweep is most likely to be surprised by, which is why the
invocation plan below keeps the dry cell §59.6 registered. The round's record —
what the sweep measured, which gate each unresolved cell failed, what it cost —
follows at **the next free section number**, §69 onward; nothing below is a
result, and nothing above is renumbered.

**68.1 The cells: three tasks × three combinations = nine cells.** The three
are the tasks this round authored, read off `tasks/first-party-v1/` as the
corpus actually holds them:

```
lido-put-the-admissions-desk-under-test          (an admissions desk; six mutants)
playbill-put-the-setting-of-the-bill-under-test  (the setting of a bill; five mutants)
signalbox-put-the-train-register-under-test      (a train register; six mutants)
```

**This list is the register.** Three ids, all `test-authoring`, and they are
**every `test-authoring` task the corpus holds** — the round sweeps the action
entire and re-runs nothing any combination has already answered.

**68.2 What every one of the three is.** Each declares `category:
test-authoring`, `language: python` and `surface: application`, and each is a
**declared control** — `control: true`, no construction block, no knob
activation, no prediction. The same two things follow as in §59.2, and for the
same reasons. A control is what a category's **calibration view** denominator
is made of, so the corpus's first `test-authoring` rows land in a cell that can
be read against their own category's baseline rather than against nothing.
And because no task here declares a contrast, **round 8 moves no knob's counter
and the kill discipline does not count it**; `calibrate-v1` gains no
`test-authoring` multiplier row from this round, and that absence is the design
rather than a gap in it. Python only, by §67.2: `test-authoring × typescript`
stays a **disclosed zero** in the coverage table and is a mechanical fill for a
later round, once one round's record has proven the gate.

**68.3 The combinations**: `claude-code` × `claude-haiku-4-5`, `claude-code` ×
`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`
(`ai_benchmark.agents.CODEX_REASONING_LEVELS`) — **the three standing columns,
unchanged from round 7**. This is §45.13's own ruling ("from round 7 on, Codex
is a second column") in its second task round, and it is taken here without
re-argument: a new verdict shape is the round's one instrument, and changing
the columns beside it would confound the two. So the round is three tasks ×
three combinations = **nine cells**.

**68.4 Cost, stated before anyone spends: $1.5–5, at list price.** The anchor
is **round 7's** per-cell spend on these same three combinations, which is the
most recent selection in the corpus where all three were priced over one sweep,
and the arithmetic is re-derivable from the checked-in round-7 rows rather than
quoted from §61: the round's forty-two rows come to **$1.4532** on
`claude-haiku-4-5`, **$4.2344** on `claude-sonnet-5` and **$1.6046** on `codex`
× `gpt-5.6-terra`, over fourteen cells each, which is **$0.1038**, **$0.3025**
and **$0.1146** a cell. That is **$0.5209 — about $0.52 — a task across the
three combinations**, so three tasks come to **$1.5627, about $1.56**, if a
suite cost what a TypeScript patch did. Registered in §59.4's summed-columns
form, that flat extrapolation is

```
claude-code x claude-haiku-4-5   3 x $0.1038 = $0.3114
claude-code x claude-sonnet-5    3 x $0.3025 = $0.9075
codex x gpt-5.6-terra            3 x $0.1146 = $0.3438
                                 total        $1.5627
```

and the registered range is **$1.5–5** — the flat extrapolation itself at the
low end, rounded down to a round number, and roughly **3.2×** it at the high
end. **The headroom is for the two lessons round 7 actually realized**, in
§67.8's own terms and not for comfort. **Fresh repositories cache worse**:
round 7's Codex column paid an effective input rate of **$0.5714/M** against
round 6's **$0.3996/M** on the same model and the same price table, and §61
attributed the difference to a round of fresh repositories rather than to
TypeScript — round 8's three repositories are fresh again, authored for this
round. And **a whole test suite is a larger write than a locate answer**: the
deliverable here is a `tests/` subtree, on an action the corpus has never
priced at any model, where the output half of the bill is the part nobody has
an anchor for.

**The bound is caching-aware, and both ends of it are registered**, the way
§59.4 registered round 7's after round 6 missed its range 2.3× low by pricing
every input token as uncached. Round 7's fourteen Codex cells read
**2,169,811** input tokens and wrote **30,396** — 154,986.5 in and 2,171 out a
cell — so three cells at the same rate are about **464,960 input** and **6,513
output** tokens. At `data/price-table.json`'s `gpt-5.6-terra` prices the output
is **$0.0782** whatever happens, and the input is **$0.9299 all-uncached**
($2/M) against **$0.0930 all-cached** ($0.20/M). So the Codex column is
registered at **$0.17 all-cached to $1.01 all-uncached**, with round 7's own
observed effective input rate putting the expected figure near **$0.34**. The
two Claude columns are **vendor-reported** and carry no such split: **$0.3114**
on haiku and **$0.9075** on sonnet, **$1.2189** together. Added up at
round-7-equal token counts the whole round is **$1.39 all-cached to $2.23
all-uncached** — an envelope whose all-uncached end sits **inside** the
registered $1.5–5 and below its middle, which is the shape §59.4 asked for and
the opposite of registering at one's own upper bound. Its all-cached end,
$1.39, falls **under** the floor, and that is not a slip in the arithmetic: it
is the one-way miss the next sentence registers, stated as a number. **The one
way this round misses is registered here too**, and it is the low side: the
range's floor *is* the flat extrapolation,
so the round falls under $1.5 only if nine `test-authoring` cells cost less per
cell than round 7's forty-two did. That would be a finding about the action —
a specification read once and a suite written straight out — and not an
accounting surprise, and the record is to say so against this line.

**Why those are list prices and not a bill.** The operator's Codex is
authenticated by **ChatGPT login**, not by an API key, so a Codex run is **not
billed per token** at all. Every Codex figure above and in the round's record
is therefore a **list-price equivalent** — tokens × `data/price-table.json`,
stamped `cost_source: table-derived` with the table's version beside it — and
not an invoice anyone received. The two claude-code columns are
`cost_source: vendor-reported`, the vendor's own figures, and their sum is what
the account is actually billed. The round's record has to carry that difference
rather than average across it, exactly as §61 did.

**68.5 The limits in force: the flat default of 600 seconds, every cell, and
nothing is registered.** `LIVE_RUN_LIMITS_S`
(`src/ai_benchmark/firstparty_v1.py`) carries four entries — `bug-fix`,
`fault-location`, `code-review` and `codebase-comprehension`, round 4's two by
§37 and round 5's two by §46 — and **`test-authoring` joins none of them**.
This ticket adds no row, because §67.8 asks for exactly that and no more.
`live_run_limit_s()` falls back to `RUN_TIMEOUT_S`
(`src/ai_benchmark/firstparty.py`) for any category with no row of its own, and
that value is **600**, so all nine cells run at the **flat default** — the same
number the four registered categories carry, reached the other way. Saying it
here is what lets the round's record write "at the flat default" rather than
"under the registered 600 s", which is §46's registered sense of the
distinction and a claim only a registered category can make. Because 600 is the
number in force for every cell of this round and of every earlier one, **no
cross-round caveat arises** and none is implied. Two riders, both about what
the limit is keyed on. It is keyed on a task's **category** alone — never on
its language, its runner or its deliverable — so a suite gets no more seconds
than a patch does. And it bounds **the agent's run**, which is where it is
handed to the adapter; the mutation gate runs afterwards, over the captured
diff, and is no part of the 600.

**68.6 How the sweep is invoked.** Sweep id **`round-8`**, on every invocation
of it. Run by hand under `docs/agents/sweep-protocol.md`, never queued.

A **dry cell first**, in its own invocation and **graded alone before the other
eight**: one `claude-code` × `claude-haiku-4-5` cell, **the cheapest of the
nine**, so that a mis-shaped verdict on a brand-new gate — the failure mode
this round adds, where the two gates run but their verdict comes out the wrong
shape on a real agent's diff — is discovered on **one paid cell rather than
nine**. §59.6's dry-cell rule is kept rather than re-argued: it exists for
exactly this situation, a new instrument meeting its first paid diff, and round
8 is the situation. It is a real, paid, graded run and one of the round's nine;
it is **not** a rehearsal to be re-run, because a task × agent × model cell is
only ever swept once. Its log is named like any other log of the sweep: the
sweep protocol **bans `-dry` in a log's name**, because round 1 left two paid
cells in `-dry`-named logs and the first pass of that analysis silently dropped
both.

The cells are chosen on the command line with **`--task`**, repeated once per
id, and never by staging a cut-down worktree: the filter refuses an id naming
no task in the set before anything runs, and runs the filtered set in corpus
order. So the dry cell is

```
uv run ai-bench eval-v1 --live --sweep round-8 --agent claude-code \
  --model claude-haiku-4-5 --task <one of the three> --log <a normally-named log>
```

and each further invocation is the same line with the remaining ids, the other
model and the other agent, and a fresh `--log` path, the runner refusing to
append to a log that already exists.

**68.7 What the round cannot say, registered in advance.** Four readings are
ruled out now rather than argued about against the numbers later.

- **Nothing about `test-authoring` × `typescript`.** It stays a **disclosed
  zero** (§67.2): the round's one new instrument pairs with the mature harness
  and the mature runner so that a failure attributes cleanly, so the language
  cell is empty by design and is a mechanical follow-on for a later round. No
  row of this round licenses a claim about what a suite in TypeScript would
  cost, take or resolve at.
- **No kill-rate reading of any kind.** The verdict is **binary by ruling**
  (§67.3): the suite passes on the pristine repository and every planted mutant
  is killed by at least one test. The record says, per unresolved cell, **which
  gate failed**; it does not quote a per-cell kill count as a score, and no
  fraction over mutants is computed anywhere. "Five of six killed" is not a
  four-fifths result, it is a red cell with a locatable reason.
- **No cross-action difficulty comparison.** A suite and a patch are
  **different deliverables**, so a `test-authoring` resolution rate read
  against `bug-fix`'s or `feature-dev`'s compares two gates as much as two
  actions — one asks whether a defect was repaired, the other whether a
  universal quantifier over hand-planted mutants was cleared. The round
  registers no contrast that could separate them, and none is computed from its
  nine rows.
- **No Codex rung.** `gpt-5.6-terra` is one model and **one model is not a
  ladder** (§65). `reconcile_v1.LADDER_MODELS` is the two claude-code models
  and the Codex column is not in it; the column can say what a second harness
  did on these three tasks, never what a cheaper second-harness model would
  have done.

## Round 8 verdicts — 2026-08-20

**§69 is the next free number.** §68 is round 8's pre-registration and the last
section written before the sweep, so this record opens at **69** and runs to
**75**. Nothing above it is renumbered.

### 69. What the round measured

**Nine cells, and they are exactly the nine §68.1 registered.** Three
`test-authoring` tasks × three combinations, every one of them swept and
logged: **9 of 9**, with nothing dropped and nothing added. The three ids the
rows carry are the three the register lists — `lido`, `playbill` and
`signalbox`, the whole of the action the corpus holds — and each is swept once
per combination and never twice.

**One sweep id, and the harness versions it ran under.** Every row carries
`sweep: round-8` and `as_of: 2026-08-20`. The version is single within each
harness's rows and **neither harness crosses a version boundary from round 7**:
`claude-code` at **2.1.235**, which is round 7's exactly, and `codex` at
**codex-cli 0.147.0**, which is round 7's and round 6's. So nothing in this
record has to be read against a harness that changed under it. The reasoning
level rides with the model (`ai_benchmark.agents.CODEX_REASONING_LEVELS` is
`{"gpt-5.6-terra": "medium"}`) and no invocation could have asked for another.

**Four invocations, four logs, none of them empty.** `r8-a` is the **dry cell**
§68.6 required: one of the nine, run alone and paid for and **graded alone
before the other eight**, so that a mis-shaped verdict on a brand-new gate
would be found on one cell rather than nine. It is
`playbill-put-the-setting-of-the-bill-under-test` on `claude-code` ×
`claude-haiku-4-5`, and it **resolved** — the mutation gate's first paid
verdict. `r8-b` carries haiku's other two, `r8-c` sonnet's three and `r8-d`
Codex's three. No stream died, no invocation logged nothing, and no cell was
re-run: four logs, nine rows, and the round's provenance is as plain as it has
ever been. **The dry cell was registered as the cheapest of the nine and was
not**: §68.6 picked the `claude-code` × `claude-haiku-4-5` column off round 7's
per-cell anchor, where haiku's $0.1038 sat just under Codex's $0.1146. In the
event **Codex was the cheapest column**, at $0.0899 a cell against haiku's
$0.2412 (§70), and the cheapest of the nine cells was `playbill` on Codex at
$0.0585 against the dry cell's $0.1138. The registration's requirement was a
cell from the claude-code × haiku column run alone, and one was; the word
"cheapest" was an ex-ante reading of an anchor that did not hold.

**Resolution: 8 of 9.** **3 of 3** on `claude-haiku-4-5`, **3 of 3** on
`claude-sonnet-5`, **2 of 3** on `codex` × `gpt-5.6-terra`. The one miss is
`playbill-put-the-setting-of-the-bill-under-test` on Codex; §72 reads it as
**which gate it failed**, which is this round's one new reading.

**The limits in force: the flat default of 600 seconds, every cell.**
`test-authoring` carries no `LIVE_RUN_LIMITS_S` row — §68.5 registered none and
this round added none — so `live_run_limit_s()` falls back to
`firstparty.RUN_TIMEOUT_S`, and all nine cells ran **at the flat default**
rather than under a registered 600 s. That distinction is §46's, registered
there and used here for the first time on a whole round: it is a claim only a
registered category can make, and this action is not one. Because 600 is the
number in force for every cell of this round and of every earlier one, **no
cross-round caveat arises** and none is implied. Nothing came near it: the
round's longest run was **289.7 s** (`lido-put-the-admissions-desk-under-test`
on haiku) and the mean was **131.8 s**, so no verdict here is a timeout in
disguise. And the limit bounds the agent's run only — the two gates run
afterwards, over the captured diff, and are no part of the 600.

**The toolchain the sweep graded under: Python 3.14.4, and no Node.** Every
cell of this round is a Python task, so `node --test` graded nothing here and
the round's verdicts are `pytest`'s alone. It is recorded for the reason round
7 recorded both: a reader re-grading these diffs on a different interpreter may
get a different answer for reasons that have nothing to do with the agent. It
is **provenance and not a row field** — round 8 added no `runner` field, no
`toolchain` field and no `gate` field to a run-log row or to a record, and this
record proposes none.

### 70. Spend, by cost source, against the range registered before it

**The three columns, kept apart by how their dollars were made:**

```
claude-code x haiku     $0.7237  vendor-reported (what the account was billed)
claude-code x sonnet    $1.7679  vendor-reported (what the account was billed)
codex x gpt-5.6-terra   $0.2698  table-derived   (list price, openai-pricing-2026-08-18.1)
```

**What the account was actually billed: $2.4916, and nothing per token for
Codex.** The operator's Codex is authenticated by **ChatGPT login**, not by an
API key, so no Codex run in this round was billed per token at all. The $0.2698
is this repository's own arithmetic — the round's Codex tokens priced through
`data/price-table.json` at version **`openai-pricing-2026-08-18.1`**, stamped
`cost_source: table-derived` on all three rows — and it is a **list-price
equivalent, not an invoice**. The two claude-code columns are the vendor's own
figures, `cost_source: vendor-reported`, and their sum is what was billed.

**The registered range was $1.5–5. The round came to $2.7614, and it was
honoured.** That total is the form §68.4 registered the bound in — the three
columns added — and it is therefore a quantity with an estimate inside it,
which is why the block above prints the three separately and why this section
states the billed figure on its own line. Every total here is **summed before
rounding**; this round the printed columns happen to add to the same last
digit, which round 7's did not, and the sentence is kept so that a reader who
checks finds the check made.

**Each column against what was registered for it.** §68.4 registered 3 × round
7's per-cell figures for the two Claude columns and a two-ended band for Codex:

```
                        registered            actual     per cell   round 7
claude-code x haiku     $0.3114               $0.7237    $0.2412    $0.1038
claude-code x sonnet    $0.9075               $1.7679    $0.5893    $0.3025
codex x gpt-5.6-terra   $0.17-$1.01 (~$0.34)  $0.2698    $0.0899    $0.1146
```

The two Claude columns came in **above** their round-7-equal registration —
**2.32×** on haiku and **1.95×** on sonnet, per cell — and the Codex column came
in **below** the ~$0.34 the band expected, at **0.78×** round 7's per-cell
figure, while still landing inside the registered $0.17–$1.01. **The one way
§68.4 registered this round missing was the low side, and it did not happen**:
$2.7614 is comfortably above the $1.5 floor, so the finding-about-the-action
that a cheap round would have been is not the finding this round has.

**The envelope was overshot at the top, and the overshoot is entirely the
Claude columns.** §68.4's caching-aware envelope — **$1.39 all-cached to $2.23
all-uncached** — held the two Claude columns fixed at round-7-equal token
counts and varied only the Codex caching split. The Claude columns did not hold
still: $1.2189 registered against **$2.4916** actual, **2.04×**, and that
difference alone carries the round past $2.23. The lesson §68.4 named — *a
whole test suite is a larger write than a locate answer* — is exactly what
happened, and it was priced into the Codex band and not into the Claude
columns. The output halves say it plainly: **15,907** output tokens a cell on
haiku and **12,754** on sonnet, against round 7's **5,388** and **5,049**, with
the input halves up about 2.3× beside them. Registering a lesson qualitatively
and arithmetically only in the column that has a token model is the shape of
this miss, and it is a miss inside the range rather than outside it.

**What a Codex row can and cannot reproduce.** The round's Codex cells read
**361,275** input tokens and wrote **8,122** — against the 464,960 and 6,513
§68.4 projected from round 7's rate, so fewer read and more written, which is
the same deliverable fact seen from the other side. Priced at
`openai-pricing-2026-08-18.1` those tokens bound the column at **$0.1697
all-cached** and **$0.8200 all-uncached**, and the logged **$0.2698** sits
between them, as it must. The split it was actually priced from is not on the
row: the effective input rate the round paid works out at **$0.4771/M**,
against round 7's **$0.5714/M** and round 6's **$0.3996/M** on the same model
and the same table. So round 8's repositories were fresh and its Codex column
still cached **better** than round 7's — which is worth writing down beside
§61's attribution of that gap to freshness, as a second observation and not as
a correction: three points on one rate, from three sweeps that differ in more
than one way, do not separate a cause.

### 71. The nine cells under three combinations

Every cell, its verdict and its cost, with each column's **cost source** in the
header where a reader cannot join the three without seeing it:

```
                                                 claude-code x       claude-code x       codex x
                                                 claude-haiku-4-5    claude-sonnet-5     gpt-5.6-terra
                                                 vendor-reported     vendor-reported     table-derived
lido-put-the-admissions-desk-under-test          resolved   $0.4138  resolved   $0.5121  resolved   $0.0820
playbill-put-the-setting-of-the-bill-under-test  resolved   $0.1138  resolved   $0.5358  unresolved $0.0585
signalbox-put-the-train-register-under-test      resolved   $0.1961  resolved   $0.7201  resolved   $0.1293
```

There is no per-category block beside it and there is nothing to group: all
three tasks are one action, which is the round. Nine cells is the whole
denominator this record has, and no rate is quoted off it.

**Turns, for what they are worth on each side.** Haiku took **57** turns over
the three (12–31), sonnet **55** (15–22), Codex **24** (5–10). A Codex turn is
a completed non-reasoning item and a claude-code turn is `num_turns`, so the
three numbers are **not** comparable across the harness boundary — §74 refuses
that comparison as §65 and round 6's §57 did, and these are quoted only so that
the refusal is anchored to something.

### 72. Which gate, and what the collection rule archived

The round's one new reading, and the only thing a mutation-gate record can say
that an earlier record could not: **per unresolved cell, which of the two gates
failed**. A suite that fails on the pristine starting repository (gate 1) is a
different failure from a suite that passes pristine and lets a planted mutant
live (gate 2) — the first is the false accusation the findings key's rejected
half refuses elsewhere, the second is a hole in coverage — and telling them
apart is derivable from replay, because both gates run over trees the grader
builds for itself out of the checked-in mutants and the collected subtree.

```
cell                                                                gate 1  gate 2
lido-put-the-admissions-desk-under-test x claude-haiku-4-5          passed  every planted mutant killed
lido-put-the-admissions-desk-under-test x claude-sonnet-5           passed  every planted mutant killed
lido-put-the-admissions-desk-under-test x gpt-5.6-terra             passed  every planted mutant killed
playbill-put-the-setting-of-the-bill-under-test x claude-haiku-4-5  passed  every planted mutant killed
playbill-put-the-setting-of-the-bill-under-test x claude-sonnet-5   passed  every planted mutant killed
playbill-put-the-setting-of-the-bill-under-test x gpt-5.6-terra     passed  a planted mutant survived
signalbox-put-the-train-register-under-test x claude-haiku-4-5      passed  every planted mutant killed
signalbox-put-the-train-register-under-test x claude-sonnet-5       passed  every planted mutant killed
signalbox-put-the-train-register-under-test x gpt-5.6-terra         passed  every planted mutant killed
```

**Gate 1 was passed by all nine.** Not one of the nine suites accused correct
code of a fault, which is the half of the verdict a corpus of hand-written
tests could most easily have failed on: nine suites written blind against a
prose specification, run against the very repository they were written for, and
none of them red.

**The one unresolved cell failed gate 2, at a named mutant.**
`playbill-put-the-setting-of-the-bill-under-test` × `codex` × `gpt-5.6-terra`
passed pristine and then let
`02-set-a-line-without-counting-the-space-between-words` through: the mutant
that drops the `+ 1` from the fit test, so a word is set on the line it would
only fit without the space before it. The suite it wrote does test the exact-fit
boundary — a line exactly as wide as the measure, one more character too wide —
but never a width at which the **space between two words** is the character
that decides, which is the only width the mutant is visible at. **That is the
whole of the reading.** No fraction is computed here — a per-cell kill count is
not a score and would be a second quality metric wearing `resolved`'s name
(§67.3) — and the failure is reported the way §68.7 registered it: a red cell
with a locatable reason, not four-fifths of a result.

**What the collection rule archived, on a real diff.** §67.4 rules that grading
collects the prompt-named test subtree out of the workdir diff and archives
everything else. Eight of the nine diffs touch nothing outside `tests/` at all.
The ninth — `playbill` × `claude-sonnet-5` — added a **`pytest.ini`** at the
workdir root carrying `pythonpath = .`, and it was **archived, not scored**:
the collected subtree is `tests/` alone, so the file never reached either gate,
and the cell resolved regardless. That is the rule working in the direction it
was written for, and it is worth the paragraph because the file is precisely
the kind that could otherwise bend a verdict — `pytest.ini` is one of the four
config files execution-verified grading already refuses to read `addopts` from.
**No cell of the round edited the module under test**: not one of the nine
diffs touches `lido.py`, `playbill.py` or `register.py`, so the hole §67.4
closes — a source edit rescuing a failing suite or overwriting a mutation —
was never even approached, and the rule is unexercised in that direction rather
than proved in it.

### 73. The coverage table, as the lint prints it

`uv run ai-bench lint-v1` reports **`lint clean: 130 task(s)`** and prints:

```
coverage: category x surface x language
  category                   surface      language    count
  bug-fix                    application  python      6
  bug-fix                    application  typescript  3
  feature-dev                application  python      71
  feature-dev                application  typescript  3
  refactor                   application  python      18
  refactor                   application  typescript  3
  test-authoring             application  python      3
  codebase-comprehension     application  python      4
  fault-location             application  python      6
  fault-location             application  typescript  3
  code-review                application  python      8
  code-review                application  typescript  2
  investigation              -            -           0
  requirement-decomposition  -            -           0
  performance-optimisation   -            -           0
  unclassified               -            -           0
```

**`test-authoring application python 3` is the round's acceptance figure**, and
it is the line that was `test-authoring - - 0` in every record up to §64's. The
rest of the table is unchanged: round 8 authored no task in any other category
and re-ran none, so the `python` column stands at **116** and the five
`typescript` rows are round 7's exactly.

**Why `test-authoring × typescript` reads zero, in §64's own wording: it is
zero by absence, which is all the table can express.** The table has one row per
(category, surface, language) that has tasks, plus a `(category, "-", "-", 0)`
row for a category with no task in **any** language. `test-authoring` now has
tasks, so it prints its Python row and nothing else; there is no
`test-authoring … typescript 0` line and there was never going to be one, for
the same reason `codebase-comprehension` prints only its Python row. **The lint
was not changed** to print registered-zero cells per language, exactly as §64
said it would not be: the generalisation buys no reading this round needs and
would move the printed table inside every earlier round's record suite.

**This prose is where round 8's TypeScript zero is disclosed.** §67.2 ruled the
round Python-only so that a new verdict shape would meet the mature harness and
the mature runner and a failure would attribute cleanly, and §68.7 registered
the cell as saying nothing. So the cell is **zero by absence**, the disclosure
lives here in the record's prose rather than in the printed table, and filling
it is a **mechanical follow-on for a later round** now that the gate has a
record: the gate itself is language-free, and a TypeScript `test-authoring`
task needs mutants, a reference suite and a `test_path` and nothing new from
the grader.

### 74. What this round cannot say

Four readings were ruled out in §68.7 before the numbers existed. Restated
against the numbers, they all still hold.

- **Nothing about `test-authoring` × `typescript`.** No row of this round is a
  TypeScript row; the cell is a disclosed zero (§73) and no figure here says
  what a suite in TypeScript would cost, take or resolve at.
- **No kill-rate reading of any kind.** §72 names the gate and, for the one
  unresolved cell, the mutant that survived. No fraction over mutants is
  computed anywhere in this record, in figures or in words: a suite that killed
  every planted mutant but one is a red cell with a locatable reason, and it is
  not four-fifths of a result.
- **No cross-action difficulty comparison.** 8 of 9 here is not to be read
  against round 7's 40 of 42 or against any earlier action's rate. A suite and
  a patch are different deliverables graded by different gates, the round
  registered no contrast that could separate them, and the denominators are
  nine and forty-two.
- **No Codex rung.** `gpt-5.6-terra` is one model and **one model is not a
  ladder**. `reconcile_v1.LADDER_MODELS` is the two claude-code models, so the
  rung floor §75 quotes is claude-code's alone and the Codex miss does not
  enter it — which is the refusal doing visible work rather than merely being
  restated.

Two more refusals this round's numbers make it tempting to break:

- **No cross-harness turn comparison.** §71's 57, 55 and 24 are counted
  differently on each side of the harness boundary, so the Codex column being
  lowest is a fact about two counting rules meeting, not about two harnesses
  working.
- **No multiplier.** All three tasks are declared controls with no construction
  block, so `calibrate-v1` gains a `test-authoring` table whose only row is the
  controls divided by themselves at **1.00×**. The absence is the design, not a
  gap in it. Round 8 moves no knob's counter and the kill discipline does not
  count it.

### 75. Replay, the readers, and heap 1 closed

**Every round-8 log replays to the verdicts this record quotes.** Each of the
four was replayed into a scratch dataset of its own, and all four into one
merged dataset; the four together are the merged one record for record:

```
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r8-a.jsonl --data /tmp/r8replay/a.jsonl
  evaluated 1 runs over 130 tasks (1 resolved)
  merged 1 records into /tmp/r8replay/a.jsonl (1 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r8-b.jsonl --data /tmp/r8replay/b.jsonl
  evaluated 2 runs over 130 tasks (2 resolved)
  merged 2 records into /tmp/r8replay/b.jsonl (2 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r8-c.jsonl --data /tmp/r8replay/c.jsonl
  evaluated 3 runs over 130 tasks (3 resolved)
  merged 3 records into /tmp/r8replay/c.jsonl (3 total)
uv run ai-bench eval-v1 --replay data/first-party-v1-runs/2026-08-20-r8-d.jsonl --data /tmp/r8replay/d.jsonl
  evaluated 3 runs over 130 tasks (2 resolved)
  merged 3 records into /tmp/r8replay/d.jsonl (3 total)
```

9 rows and 8 resolved, which is §69's resolution line reached a second way.
Every merged record also carries its log row's own measurements — cost, turns,
tokens, latency, version — because replay re-grades the diff and never re-runs
the agent, and for a Codex row that is the whole of the claim that a
table-derived cost is not recomputed on the way through.

**And this time the readers count the round.** Round 7's rows were dropped by
the default reading because they were TypeScript; round 8's claude-code rows are
Python, so `reconcile-v1` and `calibrate-v1` pick them up with no flag at all —
the first time since round 5 that a round lands inside the default view:

```
  task set   tasks/first-party-v1 — 116 task(s): 49 control(s), 67 constructed
  runs       231 over 116 task(s)
  rounds     7 round(s): as-of 2026-08-04, as-of 2026-08-05, sweep round-2, sweep round-3, sweep round-4, sweep round-5, sweep round-8
             5 keyed on a sweep id, 2 on an as-of date
```

**Six claude-code rows, not nine**: the three Codex rows are dropped by the
agent selection, which is separate from the language one and defaults to
`claude-code`. `sweep round-8` appears in `reconcile-v1`'s report exactly once,
in that rounds line, and `test-authoring` appears in it not at all — the report
is about constructed tasks and the knobs they declare, and this round declared
none. **The prediction reconciliation is unmoved**: 67 constructed tasks, 67
swept, and every knob's counter where round 7 left it.

What `calibrate-v1` gains is a table:

```
category test-authoring
   baseline mean cost   claude-haiku-4-5 $0.2412 (n=3), claude-sonnet-5 $0.5893 (n=3)
   baseline mix         3 single-file; 3 hand-authored

   profile      tasks  claude-haiku-4-5  claude-sonnet-5  rung floor
   (zero-knob)  3      1.00x (n=3)       1.00x (n=3)      haiku-solvable (n=3)
```

One row, and it is the controls divided by themselves. What the corpus now has
for this action is a **denominator** — the price of a `test-authoring` control
at each ladder model, on n=3 — which is what a later round's constructed task
would be read against. The rung floor is `haiku-solvable` on all three, because
haiku resolved all three; the Codex miss is not in it, since the ladder is
claude-code's (§74).

**Heap 1 closes.** `test-authoring` was the capability matrix's only registered
zero and the last heap-1 action with no tasks in any language (§34.3's table:
fix a defect, add a feature, refactor, author tests). With this record it has
three tasks, nine graded cells and a verdict whose ground truth is **planted
and machine-checked** — hand-planted mutants, each proved killable by the
author's reference suite before any agent met it (§67.5). Every action of heaps
1 and 2 — the two whose ground truth can be planted and machine-checked, by
held-out tests or by a key or, now, by a mutant — is in the corpus with a
record behind it. What remains empty is heap 3 (`investigation`,
`requirement-decomposition`, explain-style comprehension) and heap 4
(`performance-optimisation`), and those are the two heaps whose deliverable has
no ground truth at all.

**What round 9 meets.** §67.1 deferred the heap-3 subjective grader to round 9
on the argument that waiting costs it nothing while paying it, and both halves
of that are now cashable. The corpus it will be built beside is **settled in
the sense that matters to it**: 130 tasks, every heap-1 and heap-2 action
populated, and no round between this record and it. §67.9's stricter sense —
the one repeat sampling waits on, where the action coverage has closed — is
not reached until round 9 itself lands, because round 9 is the round that adds
heap 3's actions. And the **free-text archive** §34.4 built for its
calibration has grown from the **297 answers across eight sweeps** §67.1
counted to **306 across nine** — round 8's nine final messages, archived and
read by no verdict, exactly as every answer in it is.

## Round 9 rulings — 2026-08-21

§67.1 deferred the heap-3 subjective grader to round 9, and §75 declared
both halves of "waiting pays it" cashable: 130 tasks, every heap-1 and
heap-2 action populated, and a free-text archive of 306 answers across nine
sweeps. This section records the grill of 2026-08-21 — thirteen decisions,
taken one at a time in dependency order. **§76 is the next free number.**
Like §45 and §67, this section authors nothing: it is the input to
`/to-spec`, which files one spec for the round. One naming ruling runs
through everything below and is stated once: what the record has called the
"subjective grader" since §34.3 is renamed the **point gate**, because the
design this grill settled on is not a subjective judgment — the phrase
survives below only where a historical section is being quoted.

### 76. What round 9 is

**76.1 Round 9 is the point gate and its calibration experiment, with
authoring gated in-round on the calibration number.** Two readings of
§67.1's "two instruments" were put. A calibration-only round — the grader
proved, tasks deferred to round 10 — was declined: the grader and the
experiment that proves it worth trusting were always priced as one round's
load (§44.1's row 6), and a round whose entire output is an experiment that
sweeps nothing is thinner than this corpus's rounds run. Ruled instead:
the calibration experiment runs **first** and gates; if the bar (76.4) is
met, the round authors three tasks for **one** heap-3 action (76.8) and
sweeps them; if the bar fails, the round closes as a record of the failure
and heap 3 stays empty, disclosed — the §34.5 discipline, one action proves
the mechanism, with the proof moved ahead of the spend. Not a paid
authoring dollar moves before the experiment is judged.

**76.2 The calibration experiment is §44.6.4's, and its transfer gap is
named rather than assumed away.** The form §44.6.4 fixed stands: the grader
reads an archived free-text answer blind to the verdict, rules, and the
held-out machine verdict scores it. What the grill added is the honest
sentence about what that proves: the archive's 306 answers are heap-1 and
heap-2 runs — prose *narrating* work whose real deliverable was a diff or
an answer file — where a heap-3 deliverable is the prose itself. Passing
calibration proves the grader judges argued prose against a known truth; it
does not directly prove it judges a proposal with no truth behind it.
Ruled: the experiment gates as registered, the gap is disclosed in the
round's record in as many words, and a non-gating check rides on it — the
owner labels agree/disagree on each of the round's own swept heap-3 cells
(nine labels, work half-done by reading the record anyway), recorded as a
disclosed check on the transfer gap, not as a second gate. A third option —
replacing the archive experiment with human labels alone — was declined as
discarding five rounds of deliberately grown corpus.

**76.3 The gate runs on stratum A; stratum B is reported with its confound
named.** The archive is not one corpus but two. **Stratum A — 63 answers**
(27 `fault-location`, 26 `code-review`, 10 locate-style comprehension):
prose arguing locations and findings *for which a planted key exists*, so
the grader runs in exactly its production mode — per-point coverage with
evidence spans — and the machine verdict on the answer file scores it.
**Stratum B — 243 heap-1 answers**: the deliverable was a diff and the
prose merely narrates it; the only available point is the synthetic "the
asked-for work was done", and disagreement there measures agent narrative
truthfulness as much as grader skill — an agent that sincerely believed it
succeeded writes a resolved-sounding message on an unresolved run, an
irreducible ceiling that is not the grader's fault. Gating on all 306
undifferentiated would blend a clean measurement into a confounded one —
the hidden-second-metric move the glossary refuses elsewhere. Ruled: the
gate reads stratum A only; stratum B runs anyway (306 calls are cheap),
both numbers are stated, and stratum B gates nothing.

**76.4 The bar: stratum-A overall agreement ≥ 90% and unresolved-class
agreement ≥ 80%, registered as exact counts before the first grader call.**
The second clause is the load-bearing one: a grader that always says
"covered" collects the resolved class free, so the unresolved class is
where discrimination lives and it gets its own floor. 90% overall is the
human inter-rater band for judging argued prose, on a stratum with a known
honest disagreement source that is not grader failure — §34.5's original
worry, the right fault described at a different level of the tree than the
key names, restated in prose; 95% would fail the grader for the corpus's
own ambiguity, 85% would trust a grader wrong one time in seven. The
unresolved floor sits at 80% because that class is small and one or two
honest key-mismatches should not sink the instrument — while an
always-covered grader is refused outright. The split inside stratum A is
replay-computable before the grader runs, so the pre-registration states
the bar as counts a reader can check by hand ("≥57 of 63, and ≥N of M"),
and replay computing the split peeks at nothing. Rejected alternatives: a
single overall figure (gameable by base rate), Cohen's κ (a statistic where
the corpus's style is counts).

**76.5 The verdict judges against planted points, and its quantifier is
universal.** The task author hand-plants a **key of required points** —
and, where relevant, **disqualifiers**, claims that sink an answer — and
the verdict is: resolved iff **every** planted point is covered by the
deliverable and no disqualifier is present. This is "plant the ground
truth" continued into prose, the corpus's one institution applied a fourth
time — held-out tests, findings keys, mutants, points — and ADR-0004's
quantifier pointed at prose: a review resolves when every finding is
covered, a suite when every mutant is killed, a proposal when every planted
point is covered. Two alternatives were rejected: holistic judgment
("is this resolved?") as unauditable — when it misfires nothing says why —
and reference-answer comparison ("equivalent or better") as importing every
known LLM-judge pathology into the verdict. The narrowing this buys is
disclosed in the same breath: an agent can cover every planted point with a
mediocre proposal, the same trade ADR-0004 made when it let a suite kill
every mutant inelegantly. The subjectivity is confined to the smallest
possible judgment — does this prose cover this point? — which is what makes
the renaming honest.

**76.6 Per-point calls with mandatory evidence spans; the verdict is
computed, not spoken; the non-hermetic surface is confined to the archived
rulings.** The grader is never asked "is this resolved?". It is asked one
narrow question per planted point, and a covered-ruling must return a
**verbatim quote from the deliverable** that covers the point — no quotable
span, no coverage. The binary verdict is then a pure function of the
archived per-point rulings (all covered ∧ no disqualifier), so replay
re-reads the rulings and recomputes the verdict exactly — the free-text
archive's status ("replay cannot regenerate a sentence") extended one step:
replay cannot regenerate a ruling, and everything downstream of the rulings
is exact. This is the hermetic-grading ruling §44.4 queued: heap-3 grading
is not hermetic and cannot be, and the record confines the non-hermetic
surface to the archived rulings rather than pretending otherwise.
Temperature 0, a single call per point; k-vote majority is the recorded
fallback, adopted only if calibration shows per-point instability. The
evidence span is what makes each subjective ruling a checkable claim — the
span either covers the point or visibly does not, and 76.2's owner check
has something concrete to disagree with.

**76.7 The grader is claude-opus-5, pinned and versioned like the
classifier.** Strictly above both ladder rungs and a column in no sweep, so
no cell is graded by the model that produced it — the self-grading shape a
ladder-model grader would have, with two of three swept combinations on
sonnet or its sibling, is the trap this avoids. Model id and prompt hash
are pinned; the grader is a versioned instrument, and a grader version
change is an edit that triggers re-proof (76.10). Grader and gradees share
a vendor, and the record says so in one sentence: the verdict's trust rests
on the calibration number, not on vendor separation. A cross-vendor grader
(the Codex side's credentials) was declined — it recruits the corpus's
second vendor into its first verdict instrument, and the Codex adapter is a
swept combination, not infrastructure. Cross-vendor agreement — re-running
the archived rulings under a second vendor — queues as a natural rider for
a later round.

**76.8 The action is `investigation` — the heap's hardest case, by §34.5's
own precedent.** Round 4 shipped plant-and-check against `locate a fault`
because it was the hardest ground truth in heap 2, on §6's method: kill the
most expensive assumption cheapest and first. The point gate's most
expensive assumption is that a planted-point key can grade a deliverable
with **no** ground truth behind it — a genuinely open question, options
with trade-offs, a recommendation a good answer might argue differently
than the author did. Explain-style comprehension has quasi-ground-truth
(the code itself) and was declined for exactly that reason: passing there
leaves the heap's real question untested, and `investigation` still stands
between the corpus and heap 3 one round later. If planted points survive
contact with an open-ended proposal, `requirement-decomposition` and
explain-style comprehension follow as mechanical fills, as `review a diff`
and locate-style comprehension followed round 4's locate. The cost is
named: `investigation` is where the covered-but-mediocre gap of 76.5 is
widest, and the prompt bears that load — it names the deliverable's
required parts so the points have something to grip.

**76.9 The deliverable is one prose answer file at a prompt-named path,
with the structure in the prompt rather than the format.** §34.4's
institution continued: the prompt names the path and requires the
deliverable's parts by name — the options considered, the trade-offs, the
recommendation — and grading collects that one file from the workdir diff
under §67.4's rule, everything else archived, not scored. Structured
YAML/JSON was rejected: an investigation's deliverable *is* argued prose,
fields would grade schema-compliance as much as thinking, and the evidence
span needs running text to quote from anyway. A missing section is not a
format crime — it is planted points going uncovered, and the verdict says
so through the one mechanism the round is proving; no marker-string check
enters the verdict path.

**76.10 Three fresh-authored small Python repositories, each holding one
closed-world-decidable open question; four to six points per task with the
lint enforcing a minimum of three; and the existence proof runs in both
directions.** Fresh-authored is §45's stance carried again, doubly needed
here: the author must know the terrain well enough to plant points about
its trade-offs, and a ported repo's real history is a crib. Python only is
§45.1's own sentence — heap 3 stays on Python until its grader is trusted,
and this is the round that decides the trusting. The question must be
answerable from the repo and the prompt alone — no web research, no
missing-production-data escape — or the points cannot be fair. The proof is
§67.5's mapped over, plus the symmetric half the mapping exposes. Positive:
the **reference answer** resolves under the point gate, per point, before
any agent meets the task — refusing the equivalent-mutant analog, the
unmeetable point. Negative: the author also writes one **foil answer** —
plausible-but-wrong, the wrong recommendation argued fluently or the right
one missing the load-bearing consideration — and the gate must rule it
unresolved. Without the foil an always-covered grader passes every positive
proof; calibration proves the instrument discriminates in general, the foil
proves each task's key does — R8's two gates, mapped: reference resolves as
the suite passed pristine, foil fails as the mutants died. Proofs run at
authoring time; their per-point rulings are archived under the task's
`proofs/` subtree (the standing address: never overlaid, never collected,
never read by a verdict); the **lint stays offline and deterministic** — it
checks the archived rulings exist, cover every point, and that the foil
failed, and never calls the LLM; re-proof triggers on edit (points,
reference, foil, or grader version), not on every lint run.

**76.11 Nine cells, the calibration rulings stay out of the unified
dataset, and both halves are priced before the first paid call.** The
sweep: three tasks × the three standing combinations = nine cells, §68's
shape verbatim — the action swept entire, nothing re-run, the dry cell
first (§59.6's discipline). The two-model claude ladder stands; a third
ladder model stays behind §67.9's trigger. The calibration experiment's
306 + proof rulings are instrument calibration, not combination results:
they are archived under `data/` with the grader's version, read by the
record's registered counts, and never enter `unified.jsonl` — admitting
them under a new quality metric is the second-quality-metric move the
glossary refuses. The pre-registration section (`/to-spec`'s job, as §68
was) prices both halves: the sweep in round 8's band, and the experiment —
~306 archive calls plus per-task proofs on opus, short outputs — under its
own stated range rather than riding unpriced. The order is 76.1's:
experiment judged, then authoring.

**76.12 ADR owed: ADR-0005, the point-gate verdict shape, lands with round
9's spec** — the §45.16 pattern, as ADR-0004 landed with round 8's. All
three conditions hold: the shape is expensive to reverse once records carry
it, binary-universal-with-evidence-spans will surprise a reader expecting
an LLM-judge score, and 76.5, 76.6 and 76.10 record the real alternatives
it was chosen over. The glossary gains **point gate**, **planted point**,
**foil answer** and **evidence span** with this section, marked as landing
with round 9; "subjective grader" retires outside historical sections.

## Round 9 cells and cost — registered 2026-08-21

**77. Both halves of round 9, written down before the first paid call: the
split, the bar, the experiment's price, the sweep's, the nine cells and the
grader's version.** This is round 9's pre-registration and nothing else: §46
did it for round 5, §52 for round 6, §59 for round 7 and §68 for round 8, and
the shape below is §68's. One difference this round forces. The
**pre-registration comes before the calibration experiment**, which is the
round's first paid call, so it registers *both* halves — the experiment that
gates, and the sweep that only happens if the gate opens. The round's record —
what the experiment measured, whether the bar was met, and what the sweep then
did — follows at **the next free section number**, §78 onward; nothing below is
a result, and nothing above is renumbered.

**77.1 The order, stated: the experiment is judged first, and not a paid
authoring dollar moves before it.** §76.1's ruling, restated here because it is
what the two ranges below hang off. The calibration experiment runs first and
gates. If the bar of 77.3 is met, the round authors three `investigation` tasks
(77.6) and sweeps them; **if the bar fails, the round closes as a record of the
failure and heap 3 stays empty, disclosed**. So the first range below is
unconditional and the second is contingent, and no authoring call is made until
the first is spent and read.

**77.2 The stratum split, as counts, re-derived mechanically.** Not copied from
§76.3 and not from the round's spec. `uv run ai-bench calibrate-grader-v1
--split-only` — offline, no grader built, no call made, no key shown to
anything — was run on **2026-08-21** and printed

```
strata (derived from each row's task and the key shape it ships)
  stratum  answers  points  what the grader is asked
  A        63       115     the task's planted key, run in production mode
  B        243      243     the synthetic point "the asked-for work was done"

stratum A, by action, with the replay-computed split the bar reads
  category                answers  points  resolved  unresolved
  code-review             26       78      19        7
  codebase-comprehension  10       10      10        0
  fault-location          27       27      26        1
  (all)                   63       115     55        8
```

over **306** archived answers read out of the **37** run logs the directory
holds. So **stratum A = 63** — 27 `fault-location`, 26 `code-review` and 10
locate-style `codebase-comprehension` — and **stratum B = 243**, with the
stratum-A verdicts **55 resolved / 8 unresolved**. **Every count the command
printed matches §76.3's to the answer**, and there is no difference to report
as a finding against this item.

What that split is for is §76.3's ruling and is registered with it: **the gate
reads stratum A alone**, stratum B runs anyway because 243 more calls are cheap
and is reported **with its confound named and gating nothing**, and §76.2's
**transfer gap** — the archive is heap-1 and heap-2 prose *narrating* work whose
real deliverable was a diff or an answer file, where a heap-3 deliverable is the
prose itself — is disclosed in the round's record in as many words, with the
owner's nine agree/disagree labels on the round's own swept cells riding as a
disclosed check and never as a second gate.

**77.3 The bar, as counts a reader can check by hand: ≥ 57 of 63, and ≥ 7 of
8.** §76.4 registered two percentages over stratum A; this is the arithmetic
that turns them into answers, done once here so that nobody does it against the
result later.

```
overall           0.90 x 63 = 56.7   -> the least whole answer count above it is 57   -> >= 57 of 63
unresolved class  0.80 x  8 =  6.4   -> the least whole answer count above it is  7   -> >=  7 of  8
```

Rounding **up** in both lines, and never to the nearest: 56 of 63 is 88.9% and
6 of 8 is 75%, so a bar met by rounding down would be a bar below the one §76.4
registered.

**What each clause is for.** The overall clause is the headline number and the
weaker of the two: 90% of a stratum whose resolved class is 55 of 63 is nearly
collectable by base rate alone. **The unresolved clause is the load-bearing
one** — a grader that always says "covered" collects the resolved class free and
scores 55 of 63, which is 87.3% and misses the overall bar by two answers, but a
single point of drift the other way would carry it; read against the unresolved
class the same grader scores **0 of 8** and is refused outright. And the floor
sits at 80% rather than higher **because that class is small**: on 8 answers one
honest key-mismatch — the right fault described at a level of the tree the key
does not name, §34.5's original worry restated in prose — is absorbed at 7 of 8,
while two sink the instrument at 6 of 8. That is the whole reason the second
clause is registered as a count and not as a percentage: on a class this size a
percentage hides how few answers separate met from failed.

**77.4 The experiment's price: $1.5–8, at list price, counted in calls and not
in answers.** The unit is the **call**, because production mode is one call per
planted point and an answer graded against a three-finding key costs three of
them.

```
stratum A   27 fault-location   x 1 point  =  27
            26 code-review      x 3 points =  78
            10 comprehension    x 1 point  =  10
                                              115 calls
stratum B  243 answers          x 1 point  = 243 calls
                                              358 archive calls in all
```

The 26 `code-review` answers grade against a three-finding key apiece, which is
where the gap between 63 answers and 115 calls comes from, and it is the whole
reason this item is registered over calls: 306 answers priced as 306 calls would
underprice the experiment by a sixth before anything else went wrong.

**The proofs are priced separately and are contingent on the bar.** Only if the
experiment passes does ticket 03's authoring writer run, once per planted point
*and* once per disqualifier, against **both** answers — the reference answer and
the **foil** — so a task's proof costs

```
3 tasks x (4-6 points + 0-2 disqualifiers) x (reference + foil)
      = 8-16 calls a task = 24-48 calls for the round
```

**The assumed disqualifier count is 0–2 a task**, stated here so that the range
cannot be silently exceeded: the 16-call top of the per-task range is 6 points
plus 2 disqualifiers, and a task that declares a third disqualifier puts the
round outside this registration and forces a re-registration rather than being
absorbed by it.

**The prices were read, not remembered.** Fetched on **2026-08-21** with

```
curl -sL https://platform.claude.com/docs/en/about-claude/pricing
```

- `source_url`: `https://platform.claude.com/docs/en/about-claude/pricing`
  (`https://docs.claude.com/en/docs/about-claude/pricing` redirects there)
- `as_of`: **2026-08-21**

That command's own output carries the row **Claude Opus 5** — the model
`point_grader.GRADER_MODEL` names — at **$5 / MTok** base input, **$0.50 /
MTok** cache hits and refreshes, and **$25 / MTok** output. The two prices this
round is billed at are therefore **$5/MTok in and $25/MTok out**.

**The cached/uncached split the sweep protocol's item 2 asks for is settled
here, and it is all uncached.** The grader sets no `cache_control` breakpoint
(`point_grader.anthropic_point_grader`), every call carries a different
deliverable, and the only shared prefix is the prompt template's **714**
characters — an order below the smallest cacheable prefix in any case. So
**every input token in this half is priced at the base rate** and the $0.50/MTok
cache-hit price prices nothing this round. This is the one estimate in the
project where that split is a fact about the instrument rather than a guess
about a run.

**The arithmetic, at four characters a token.** The deliverables are short:
stratum-A answers run **45–1379 characters, median 352**. Filling the grader's
prompt template with each point and its deliverable over all 358 calls comes to
**491,246 characters**, and the deliverables those calls carry come to
**212,658 characters**.

```
input   491,246 chars / 4                    = 122,811 tok  x $5/M  = $0.6141
output  low   358 calls x 100 tok thinking   =  35,800 tok  x $25/M = $0.8950
        high  358 x 300 tok + 53,164 quoted  = 160,564 tok  x $25/M = $4.0141
                                               archive half  $1.5091 - $4.6282

proofs  low   24 calls x 4,914 chars / 4     =  29,484 tok  x $5/M  = $0.1474
              24 x 100 tok thinking          =   2,400 tok  x $25/M = $0.0600
        high  48 calls x 8,914 chars / 4     = 106,968 tok  x $5/M  = $0.5348
              48 x (2,000 quoted + 300)      = 110,400 tok  x $25/M = $2.7600
                                               proofs half   $0.2074 - $3.2948

                                               round total   $1.7165 - $7.9230
```

and the registered range is **$1.5–8**: the arithmetic's own low end rounded
down to a round number and its own high end rounded up to one.

**Which half of that is an assumption, named.** The input half is arithmetic
over text that already exists, and only the four-characters-a-token convention
stands between it and a certainty. **The output half is the half with no
anchor**, exactly as §68.4's was, and it is registered with both ends stated
rather than with a point estimate: the low end assumes every ruling comes back
uncovered and quotes nothing, over **100** output tokens of `effort: low`
thinking a call; the high end assumes every ruling quotes **its whole
deliverable** over **300**. The high end is a bound and not an expectation — no
ruling should quote a whole answer, since the prompt asks for the span that
covers one point — so the expected figure sits nearer the low end of the range
than the high. A proof answer is assumed at **4,000 characters** at the low end
and **8,000** at the high, against an archive whose longest answer is 1,379,
because a heap-3 reference answer is the deliverable rather than a note about
one.

**The one way this half misses is the grader thinking longer than it is
registered to.** At more than 300 output tokens a call the top of the range
goes, and that is a fact about the instrument at `effort: low` rather than an
accounting surprise; the record is to say so against this line, with the
archived rulings' own token counts beside it. The rulings themselves are
**instrument calibration and not combination results**: they are archived under
`data/` with the grader's version and **never enter `unified.jsonl`** (§76.11).

**77.5 The sweep's price: $2.5–5, at list price, in round 8's band.** Contingent
on 77.1, and re-derived from the **checked-in round-8 rows** — selected by sweep
id `round-8` over every log in the directory and never by a log's filename —
because round 8 is the nearest anchor this corpus has: the same three
combinations, the same nine-cell shape, three freshly authored repositories and
a brand-new verdict shape, one round ago. Its nine cells came to **$0.7237** on
`claude-haiku-4-5`, **$1.7679** on `claude-sonnet-5` and **$0.2698** on `codex`
× `gpt-5.6-terra`, over three cells each, which is **$0.2412**, **$0.5893** and
**$0.0899** a cell. That is **$0.9204 a task across the three combinations**, so
three tasks come to **$2.7612**, if an investigation costs what a test suite
did. In §68.4's summed-columns form,

```
claude-code x claude-haiku-4-5   3 x $0.2412 = $0.7236
claude-code x claude-sonnet-5    3 x $0.5893 = $1.7679
codex x gpt-5.6-terra            3 x $0.0899 = $0.2697
                                 total        $2.7612
```

— which is round 8's own **$2.7614** re-derived through rounded per-cell
figures, the two differing by the two hundredths of a cent the rounding costs,
and the figure a reader with the printed cents can redo.

**The bound is caching-aware and both ends of it are registered**, §59.4's rule
kept. Round 8's three Codex cells read **361,275** input tokens and wrote
**8,122**, and round 9 sweeps three cells on the same column, so the projection
is that round's own totals rather than a rate scaled up. At
`data/price-table.json`'s `gpt-5.6-terra` prices the output is **$0.0975**
whatever happens, and the input is **$0.7225 all-uncached** against **$0.0723
all-cached**; the Codex column is registered at **$0.17 all-cached to $0.82
all-uncached**, with round 8's own observed effective input rate of
**$0.4771/M** putting the expected figure near **$0.27**. The two Claude columns
are **vendor-reported** and carry no such split: **$0.7236** on haiku and
**$1.7679** on sonnet, **$2.4915** together. Added up at round-8-equal token
counts the whole sweep is **$2.66 all-cached to $3.31 all-uncached** — an
envelope whose all-uncached end sits **inside** the registered $2.5–5 and below
its middle, which is the shape §59.4 asked for.

**Why the headroom is thinner than §68.4's, and the two ways this misses.** §68
registered its ceiling at roughly 3.2× its flat extrapolation because its anchor
was a round of another action in another language; this one is **1.8×**, because
the anchor is the same three columns over the same nine-cell shape one round
ago. The **low** miss is §68.4's own and is the likelier: the range's floor *is*
the flat extrapolation rounded down, so the sweep falls under $2.5 only if nine
`investigation` cells cost less a cell than round 8's nine `test-authoring` ones
— a repository read once and a proposal written straight out, against a suite
written file by file — which would be a finding about the action and not an
accounting surprise. The **high** miss is this round's own and is what the
thinner headroom buys watching: an investigation that reads the whole repository
on every turn is an input bill no anchor here has priced, and $5 is where the
record is to stop and say so.

**Why those are list prices and not a bill.** Unchanged from §68.4 and stated
again because both halves of this round carry it. The operator's Codex is
authenticated by **ChatGPT login**, not by an API key, so a Codex run is **not
billed per token** at all and every Codex figure above is a **list-price
equivalent** — tokens × `data/price-table.json`, stamped `cost_source:
table-derived` — and not an invoice anyone received. The two claude-code columns
are `cost_source: vendor-reported`. The experiment's own calls in 77.4 are
neither: they are metered API calls on the operator's Anthropic key, and there
the list-price equivalent and the invoice are the same number.

**77.6 The cells: three `investigation` tasks × the three standing columns =
nine cells, and the id register is left to be filled in before the sweep.** The
combinations are `claude-code` × `claude-haiku-4-5`, `claude-code` ×
`claude-sonnet-5`, and `codex` × `gpt-5.6-terra` at reasoning `medium`
(`ai_benchmark.agents.CODEX_REASONING_LEVELS`) — **the three standing columns,
unchanged from rounds 7 and 8**, taken here without re-argument for §68.3's
reason: the point gate is the round's one instrument and changing a column
beside it would confound the two. So the round is three tasks × three
combinations = **nine cells**.

Each of the three is **Python** (§76.10: heap 3 stays on Python until its
grader is trusted, and this is the round that decides the trusting), and each is
a **declared control** — `control: true`, no construction block, no knob
activation, no prediction. The same two things follow as in §68.2 and for the
same reasons: the corpus's first `investigation` rows land in a cell that can be
read against their own category's baseline, and because no task here declares a
contrast, **round 9 moves no knob's counter and the kill discipline does not
count it**; `calibrate-v1` gains no `investigation` multiplier row from this
round, and that absence is the design rather than a gap in it.

**The three task ids do not exist yet, and that is 77.1's order rather than an
omission.** Authoring is gated on the experiment, so there is nothing to list
here: **the id register for round 9 is left explicitly to be filled in, in this
section, before the sweep, by the round's task-authoring ticket** — the corpus
holds no `investigation` task as this is written, and `investigation` is a
**disclosed zero** in the coverage table until it does.

**How the sweep is invoked.** Sweep id **`round-9`**, on every invocation of it.
Run by hand under `docs/agents/sweep-protocol.md`, never queued. A **dry cell
first**, in its own invocation and **graded alone before the other eight**: one
`claude-code` × `claude-haiku-4-5` cell, the cheapest of the nine, so that a
mis-shaped verdict on a brand-new gate is discovered on **one paid cell rather
than nine**. §59.6's dry-cell rule is kept rather than re-argued, and round 9 is
exactly its situation — a new instrument meeting its first paid diff. It is a
real, paid, graded run and one of the round's nine; it is **not** a rehearsal to
be re-run, because a task × agent × model cell is only ever swept once. Its log
is named like any other log of the sweep: the sweep protocol **bans `-dry` in a
log's name**. The cells are chosen on the command line with **`--task`**,
repeated once per id, and never by staging a cut-down worktree, so the dry cell
is

```
uv run ai-bench eval-v1 --live --sweep round-9 --agent claude-code \
  --model claude-haiku-4-5 --task <one of the three> --log <a normally-named log>
```

and each further invocation is the same line with the remaining ids, the other
model and the other agent, and a fresh `--log` path, the runner refusing to
append to a log that already exists. **Nothing is re-run**: the round sweeps the
three tasks it authors and no cell any combination has already answered.

**77.7 The limits in force: the flat default of 600 seconds, every cell, and
nothing is registered.** `LIVE_RUN_LIMITS_S`
(`src/ai_benchmark/firstparty_v1.py`) carries four entries — `bug-fix`,
`fault-location`, `code-review` and `codebase-comprehension`, round 4's two by
§37 and round 5's two by §46 — and **`investigation` joins none of them**. This
ticket adds no row: §76 rules nothing about run-time limits, and §68.5's
precedent for a new action is explicit — `test-authoring` joined no register
one round ago, because registering is a deliberate act and the flat default
already covers every cell. `live_run_limit_s()` falls back to `RUN_TIMEOUT_S`
(`src/ai_benchmark/firstparty.py:247`) for any category with no row of its own,
and that value is **600**, so all nine cells run at the **flat default** — the
same number the four registered categories carry, reached the other way. Saying
it here is what lets the round's record write "at the flat default" rather than
"under the registered 600 s", which is §46's registered sense of the distinction
and a claim only a registered category can make. Because 600 is the number in
force for every cell of this round and of every earlier one, **no cross-round
caveat arises** and none is implied. And the limit bounds **the agent's run**:
the point gate runs afterwards, over the collected answer file, and its grader
calls are no part of the 600.

**77.8 The grader's pinned version, quoted verbatim.**

```
claude-opus-5:c8c8f5e6dd67
```

That is `point_grader.GRADER_VERSION` — the model id §76.7 pinned, and the
first twelve hex digits of the SHA-256 of the prompt beside it. It is written
down here so that **a later grader change is visibly a different instrument**
rather than a quiet drift under a number this section already registered: the
rulings archive holds one file per version, a version change re-triggers every
task's proofs (§76.10), and a bar met at this string says nothing about a bar
met at another.

## Round 9 amendment — 2026-08-22

**78. The grader instrument is re-pinned: `deepseek-v4-pro`.** Round 9
parked at its calibration gate on 2026-08-22 (#123): stage 1 landed entire —
the grader, the point gate, the lint, `calibrate-grader-v1`, §77 — and the
experiment's 358 calls could not be paid for, because the machine holds no
Anthropic SDK credentials and no path to them was found. Grading through the
`claude` CLI was put and stays refused: an unpinned harness inside a
versioned instrument. This section records the third option, ruled in the
owner's session of 2026-08-22: reopen §76.7 — whose choice of vendor rested
on a premise that has failed — and re-pin the grader to a vendor whose
credentials the owner holds. Nothing here is a result; the round's record
still follows at the next free number.

**78.1 The reopen is a premise failure, not a reversal.** §76.7 chose
claude-opus-5 over a cross-vendor grader for two reasons: no cell graded by
the model that produced it, and not recruiting the corpus's second vendor
into its first verdict instrument. Both reasons assumed the choice existed.
It does not — the alternatives actually on the table are a DeepSeek-graded
round 9, an indefinite park that quietly becomes abandonment, or the CLI
grading §76.7's session already refused. Against those three, the amendment
carries §76.7's own logic further than the original did: **the self-grading
shape vanishes entirely** — DeepSeek is a column in no sweep and shares a
vendor with neither swept vendor, where opus shared one with two thirds of
the columns — and the sentence the original trusted still holds verbatim:
the verdict's trust rests on the calibration number, not on vendor
separation. The 90/80 bar (§77.3) is unchanged, and this amendment is the
first time it does precisely the job §76.2 built it for: deciding whether a
grader nobody has vouched for is worth trusting. If `deepseek-v4-pro` cannot
clear ≥ 57 of 63 and ≥ 7 of 8, the round closes as a record of that, §76.1's
own sentence, and the corpus has spent an experiment's price to learn it.

**78.2 What is no longer claimed: "strictly above both ladder rungs".**
§76.7's tier argument does not carry a claim that `deepseek-v4-pro` clears
sonnet, and none is made. The claim's load — a grader capable enough that
its rulings mean something — moves onto the bar, where it always really
sat: an under-capable grader fails calibration visibly, at registered
counts, before an authoring dollar moves. The instrument's settings are part
of the pin: **low reasoning effort, temperature 0, JSON output** — the
per-point question is narrow (coverage plus a verbatim quote), a reasoning
chain buys latency and paraphrase risk, and a paraphrased span is refused
mechanically either way. k-vote majority stays the recorded fallback,
adopted only if calibration shows per-point instability (§76.6).

**78.3 The weak pin, disclosed, and what compensates it.** Anthropic model
ids are snapshots; the DeepSeek API accepts only **moving aliases**
(`deepseek-v4-pro`, `deepseek-v4-flash`) and no dated checkpoint id, so the
pin §76.7 promised is not available from this vendor. Disclosed, and
compensated rather than accepted silently: the vendor announces checkpoints
publicly (at this writing `V4-Pro-0813`, GA 2026-08-13), and the announced
checkpoint **joins the instrument's version tuple** — alias, announced
checkpoint, prompt hash. A checkpoint announcement under the alias is
thereby a version change, and a version change already re-triggers every
task's proofs (§76.10) and opens a new rulings file (§77.8's sentence: a
bar met at one string says nothing about a bar met at another). What the
tuple cannot catch is an unannounced swap under the alias — named here as
the residual exposure, bounded by the same fact that bounds everything
else: replay never re-calls, so archived rulings and archived proofs are
immune; only new gradings and new proofs ride the alias. The non-hermetic
surface (§76.6) changes vendor, not size.

**78.4 What §77 keeps, and the one thing re-registered before the first
paid call.** The split (77.2), the bar (77.3), the call count (358, 77.4's
table), the sweep's price (77.5), the cells (77.6) and the limits (77.7)
all stand — none of them mentions a vendor. Two entries are superseded:
**77.8's version string**, replaced by the new tuple quoted verbatim once
the implementation pins it, and **77.4's dollar range**, re-derived at
DeepSeek list pricing (registered at peak-hour list price, the conservative
end of the vendor's peak/off-peak schedule) — both re-registered by the
implementing ticket **before the first grader call**, which is honest for
the same reason §77's original registration was: not one paid call has
happened. The implementation changes are three and small: the live client
moves to the vendor's OpenAI-compatible endpoint, the version constant
becomes the tuple, and §77's amendment lands with its pins. Delivery is the
standing pipeline's: tickets cut on #123, the park comment superseded, and
#130's runbook then runs with the DeepSeek key in the invoking shell.

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
