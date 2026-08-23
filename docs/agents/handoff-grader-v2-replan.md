# Handoff: grader v2 replan (§80) — for the session that picks this up

Written 2026-08-23, at the close of the session that ran round 9's calibration
gate. The owner has ruled the next step in that session's words: **replan in a
new context — grader v2 by prompt revision, not a model switch, delivered as a
§80 amendment on #123.** This file is the map; delete it once §80 has landed
and its tickets are cut.

## Where things stand (all pushed, HEAD `e4d532e` at this writing)

- **Round 9 closed at its gate, FAILED.** §79 of
  `docs/design/task-difficulty-and-ex-ante-profiles.md` is the record:
  overall agreement **15 of 63** against the registered ≥ 57 of 63; the
  unresolved clause met at 7 of 8. One paid run, 358 calls, ~$0.25–1.5,
  nothing re-asked (a mid-run local-proxy failure was resumed by deliverable
  hash: 105 + 253).
- **The rulings archive** is committed whole at
  `data/point-gate-calibration/deepseek-v4-pro:DeepSeek-V4-Pro-0813:5ec690f5eb62.json`
  (`c19d4f0`). Nothing from calibration is in `data/unified.jsonl`.
- **The pin suite** `tests/test_firstparty_v1_round9_calibration.py` (9 tests)
  re-derives every §79 figure from the archive offline and audits every
  covered ruling's span. Full suite 2525 green, mypy green, lint green.
- **Issues**: #130 closed done (its closing comment is the run log). #131–#134
  closed **unstarted**, each naming §79 — their ticket texts stand almost
  verbatim for revival if a future bar is met. **#127 (ADR-0005) is OPEN** —
  it runs on either branch and writes its gating sentences from §79's actual
  verdict; it can go to `qap run` any time.
- The frontier assertion in `tests/test_firstparty_v1_round9_cells.py` is at
  `numbered[-1] == 79` / `range(69, 80)`; whoever writes §80/§81 bumps it as
  the named exception, touching nothing else in that suite.

## Why prompt revision, not a model switch (the evidence, §79.1–79.2)

47 of 48 disagreements are the grader refusing machine-resolved answers, and
both mechanisms are instrument-spec defects, not capability limits:

1. **The literal-form refusal** (carries `fault-location` 24/26 and
   comprehension 8/10): the point text renders the key as
   `file.py:Class.method`; answers name the same location in prose ("the
   `Yard.book_in` method in `yard.py`"); the machine's matcher accepts these
   forms, the grader was never told to, and it faithfully ruled not-covered.
2. **The paraphrased quote** (15 covered rulings): spans quoted the
   deliverable with its markdown stripped (`dues.py: owed_by — …` for
   `**dues.py: owed_by** — …`); `span_in_deliverable`'s whitespace-only
   normalisation refused them, as specified.

The model executed flawlessly: 358/358 well-formed JSON rulings, zero
refusals/truncations/empty spans, non-degenerate verdict split (A: 54/61
covered, B: 162/81), span lengths 5–330 median 62. See #130's closing comment.

## What §80 must contain (the §78 pattern, reused)

§78 is the precedent for everything procedural here: amendment section in the
design note, a scoped copy appended to **#123's body** (qap plan reads only
the body, never comments), then `qap plan --issue 123` cuts the tickets,
numbered from **15** onward (12–14 were §78's).

1. **The reopen ruling**: §79's failure was the instrument's question, not the
   model — so the PROMPT moves, the model and settings stay
   (`deepseek-v4-pro`, low reasoning effort, temperature 0, JSON output).
2. **Two prompt revisions** in `src/ai_benchmark/point_grader.py`'s `PROMPT`:
   - location-equivalence: prose, backticked, and `file.py:Class.method`
     forms of the same location all count as naming it (align with what the
     machine matcher accepts);
   - span discipline: the quote is copied verbatim from the deliverable
     **including markdown markers**.
3. **One open judgment point — flag it for the plan review**: whether to also
   loosen `span_in_deliverable`'s normalisation (strip markdown on both sides
   before comparing). That changes the gate's mechanics, not the prompt, and
   deserves its own ruling rather than riding silently.
4. **The re-registration, before the first paid call**: the new version tuple
   (same alias, same checkpoint `DeepSeek-V4-Pro-0813` — re-verify against the
   pinned fetch — **new prompt hash**) quoted verbatim into §80; the split
   re-derived and required identical to §77.2 (63/115 + 243 = 358, 55/8); the
   bar unchanged at ≥ 57 of 63 and ≥ 7 of 8; the $0.25–1.5 range reaffirmed
   or re-fetched.
5. **A re-run runbook ticket** mirroring #130: record lands at **§81**, the
   frontier assertion moves to 81 with it, new rulings file (one per version),
   archive committed whole, nothing to unified.
6. **The conditional revival**: if the new bar is met, re-file the authoring
   and sweep work from #131–#134's texts (pointing at the new sections); if it
   fails again, §81 closes the question of this vendor's grader and the next
   move is a design discussion, not a third prompt.

## Guardrails in force

- **No new sweep rows** under `data/first-party-v1-runs/` between §80's
  registration and the §81 run — a moved split stops the run by design.
- **The paid run is one run**, resumed on infrastructure failure only, never
  repeated for a nicer number. Run it by hand in the session, not via
  `qap run` (cascade retries can double-spend a paid gate).
- **`DEEPSEEK_API_KEY` is not stored anywhere on this machine** — the owner
  supplies it at the gate. Name this at the top of the runbook, per the
  qap.md payment-path rule.
- The machine's system proxy can refuse connections (`httpx2`+truststore
  reads macOS proxy settings); a `Connection refused` at api.deepseek.com is
  local — probe with `curl --noproxy '*'` before blaming the vendor, and just
  resume.

## The short path, in commands

```
# 1. write §80 into docs/design/task-difficulty-and-ex-ante-profiles.md
#    (after §79, before "## Open questions"; bump the frontier test to 80)
# 2. append the scoped §80 spec to #123's body:
gh issue view 123 --json body -q .body > /tmp/b.md   # edit, then:
gh issue edit 123 --body-file /tmp/b.md
# 3. cut and review the tickets:
qap plan --issue 123        # expect files from 15-*.md; review .qap/plan-review.md
# 4. file as issues (Parent #123), add front-matter `issue: N`, queue, run:
qap queue add tickets/15-*.md ... && qap run --close-issues
# 5. the paid gate, by hand, key in the invoking shell:
DEEPSEEK_API_KEY=... uv run ai-bench calibrate-grader-v1 --split-only   # must match §77.2
DEEPSEEK_API_KEY=... uv run ai-bench calibrate-grader-v1
```
