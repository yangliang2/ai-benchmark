# ADR-0005: The point-gate verdict shape

Status: accepted
Date: 2026-08-23

## Context

`investigation` — together with `requirement-decomposition` and explain-style
`codebase-comprehension` — was heap 3, empty in every language: the one group
of actions whose deliverable is prose with no ground truth held-out tests can
check. ADR-0004 closed heap 1's zero by grading the tests an agent wrote
against hand-planted mutants; heap 3's deliverable is not tests, so that shape
does not reach it. Round 9 (design note §76) rules a verdict shape for prose
itself, gated on a calibration experiment before any task is authored.

## Decision

The verdict is the **point gate**: a hand-planted key of required points
judged against one prose answer file.

- **Collection.** One file — the prompt-named answer file — taken from the
  **workdir diff** under the mutation gate's subtree-alone rule narrowed to a
  single path; everything else the run wrote is archived, not scored.
- **The question.** One narrow grader call per hand-planted point, and one per
  optional **disqualifier** — never "is this resolved?". A covered ruling must
  cite a **verbatim evidence span** from the deliverable; a span the mechanical
  check cannot locate in the deliverable is demoted, and the demotion is
  archived alongside the ruling it came from.
- **The verdict.** `resolved` is computed, not spoken: every planted point
  covered and no disqualifier present, binary and universally quantified over
  points — not a coverage rate. The per-point rulings are archived, and the
  verdict downstream is a pure function of them, so replay re-reads rulings
  rather than re-asking a model; the non-hermetic surface this grading admits
  is confined to those archived rulings and nothing past them.
- **The instrument.** The grader is a versioned instrument — model id plus
  prompt hash, an announced checkpoint joining the tuple where the vendor pins
  only a moving alias — gated on a calibration bar registered as counts
  before its first call: an under-capable grader has to fail visibly, at
  numbers a reader can check by hand, before an authoring dollar moves.

## Rationale

- **Binary and universally quantified, never a rate** (§76.5, §76.6). This is
  ADR-0004's quantifier pointed at prose instead of mutants: a proposal
  resolves when every planted point is covered, the same institution — plant
  the ground truth, then ask a binary question of it — applied a fourth time
  after held-out tests, findings keys and mutants. A coverage percentage under
  the name `resolved` would be the second quality metric the **quality
  metric** glossary entry already refuses, and it would let a doubtful point
  hide inside the slack instead of being provably coverable.
- **Evidence spans make each ruling a checkable claim** (§76.6). The grader is
  never asked for the verdict directly; it answers one point at a time, and a
  covered ruling has to quote the deliverable back verbatim. That is what
  turns a subjective per-point call into something the calibration
  experiment, and later an auditor, can visibly agree or disagree with — and
  what keeps the verdict a pure function of the archive rather than a fresh
  judgment on every replay.
- **The grader is gated by a calibration bar, and the bar is registered before
  it is paid for** (§76.1, §76.4, §78.1, §78.2). The experiment runs first and
  gates: if the bar fails, no `investigation` task is authored, no cell is
  swept, and heap 3 stays empty and disclosed rather than filled by an
  unproven instrument. The bar's counts, its stratum split and its two
  clauses (overall agreement, and a separate floor on the unresolved class,
  where an always-covered grader hides) are all fixed before the first grader
  call, so the record states a bar a reader can check by hand rather than one
  fitted to whatever the run produced.

## Alternatives considered

- **Holistic judgment ("is this resolved?").** Rejected as unauditable: when a
  holistic verdict misfires, nothing in the record says why (§76.5).
- **A reference-answer comparison ("equivalent or better").** Rejected: scoring
  a proposal against one reference answer imports every known LLM-judge
  pathology — a preference for the reference's phrasing, its length, its
  ordering — into the verdict (§76.5, §76.6).
- **A rubric score, or any kill-rate-style fraction over points.** Rejected
  for the same reason ADR-0004 refused a mutation score: partial recall is not
  a score anywhere else in this corpus's grading, and a coverage fraction
  wearing `resolved`'s name is that same second-quality-metric move undisguised
  (§76.5's own citation of §67.3).
- **Asking an LLM for the verdict directly.** Rejected: the grader is never
  asked whether the task as a whole succeeded, only one narrow per-point
  question with a quote required, because the subjectivity has to be confined
  to the smallest judgment available — does this prose cover this point?
  (§76.5, §76.6).
- **A structured YAML/JSON deliverable.** Rejected (§76.9): an
  `investigation` deliverable *is* argued prose, and fields would grade
  schema-compliance as much as thinking; a missing section is not a format
  crime but planted points going uncovered, and the evidence span needs
  running text to quote from in the first place.
- **k-vote majority grading.** Not built. Recorded as the fallback if
  calibration shows per-point instability under a single temperature-0 call;
  it did not arise, because the calibration failures traced to the instrument's
  prompt and to a stratum construction defect, never to per-point instability
  (§76.6, §79.2, §81.2).

## Consequences

- **Covered-but-mediocre stays a known narrowing.** An agent can cover every
  planted point with a proposal that argues them badly — the same trade
  ADR-0004 made when it let a suite kill every mutant inelegantly. The
  subjectivity this buys down is confined to one question per point; it does
  not certify the prose is good, only that it touches what was planted.
- **Replay stays exact but cannot regenerate a ruling.** Everything downstream
  of the archived rulings — the verdict, the record, the calibration counts —
  recomputes exactly on replay. The rulings themselves are the one
  non-hermetic surface this grading admits, and nothing past them is.
- **Grader and gradees share a vendor, and the verdict's trust rests on the
  calibration number rather than on vendor separation.** The instrument was
  first pinned to a model strictly above the ladder and column in no sweep
  (§76.7); that premise failed when no credentials for it were available, and
  the grader was re-pinned to a vendor whose credentials the operator holds —
  DeepSeek, which shares a vendor with no swept column but also earns no
  cross-vendor argument. What carries the claim's weight either way is the
  same sentence, restated rather than replaced at the re-pin: the verdict's
  trust rests on the calibration number (§78.1).
- **The instrument failed its registered bar, twice, and heap 3 stays empty.**
  Round 9's calibration experiment ran under two instrument versions —
  `deepseek-v4-pro:DeepSeek-V4-Pro-0813:5ec690f5eb62` and, after a prompt
  revision, `…:8bf4fedb86be` — and neither cleared the registered bar of
  ≥ 57 of 63 overall and ≥ 7 of 8 on the unresolved class: the first scored
  15 of 63, the second 46 of 63 (design note §79, §81). Both clauses gate, so
  both rounds closed as records of the failure rather than as authored tasks:
  no `investigation` task exists, no cell was swept, the coverage table's
  `investigation` zero stands disclosed, and **no cell has ever been graded
  by this gate**. The shape this ADR records was decided and built regardless
  of that outcome — the calibration gate is what the shape itself specifies,
  and its failure is a finding about one vendor's instrument, not a reversal
  of the decision above (§79, §81, §82.4).
