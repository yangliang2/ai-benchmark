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
   the first rule holds by construction rather than by discipline. The table
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
