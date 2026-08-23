# Runbook: The v2 gate re-run (§81)

This is the operational record for running the v2 grader's calibration gate, scheduled to follow the v2 prompt revision's landing at §80. Run by hand in the session; never queued. One run, resumed on infrastructure failure only, never repeated for a nicer number. The session's own frontier assertion moves to §81 with the record.

## 1. Payment-path pre-flight: `DEEPSEEK_API_KEY` is not stored anywhere on this machine

The owner supplies `DEEPSEEK_API_KEY` in the invoking shell before calling the run:

```bash
export DEEPSEEK_API_KEY=...
# then all steps below
```

No API key is committed or checked into any file — the gate is run in a shell where the key is available by environment variable alone, and the runbook names that constraint first.

## 2. Pre-flight checks

Before the run starts, verify:

1. **Full test suite green.** Run the suite and confirm all pass:
   ```bash
   uv run pytest -q
   ```

2. **Lint clean.** Run the v1 linter with no errors:
   ```bash
   uv run ai-bench lint-v1
   ```

3. **Split re-derived and identical to §77.2.** Re-derive the split offline, without the grader, and confirm the counts are unchanged:
   ```bash
   uv run ai-bench calibrate-grader-v1 --split-only
   ```
   It must print:
   - stratum A: **63 answers / 115 points, 55 resolved / 8 unresolved**
   - stratum B: **243 answers**
   - **358 archive calls in all**

   If any count differs, stop here. A moved split stops the run by design — report it and do not re-register after the fact.

4. **No new sweep rows between §80.4's registration and this run.** Confirm that no new files have been added to `data/first-party-v1-runs/` since §80's registration on 2026-08-23:
   ```bash
   find data/first-party-v1-runs -type f -newermt "2026-08-23" | sort
   ```
   The output must be empty. A moved split or a new row stops the run by design.

## 3. The run: 358 calibration calls over both strata, one paid run

Run the v2 grader over the full calibration set. This is the single paid invocation — it is never retried for a nicer number and is resumed only on infrastructure failure:

```bash
DEEPSEEK_API_KEY=... uv run ai-bench calibrate-grader-v1
```

This makes:
- **115 calls on stratum A** (the task's planted key, run in production mode)
- **243 calls on stratum B** (the synthetic point "the asked-for work was done")
- **358 calls in all** over the same archive used by v1

The grader version used is the v2 tuple from `point_grader.GRADER_VERSION`. The current v2 tuple is:

```
deepseek-v4-pro:DeepSeek-V4-Pro-0813:8bf4fedb86be
```

This is the same alias and checkpoint as v1, with a new prompt hash (§80.2's two revisions). Read it from the code if it has changed:

```bash
uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)'
```

## 4. Connection-failure procedure

If the run fails mid-stream with a connection error:

1. **Probe the local proxy first.** The machine's system proxy is the first suspect (a `Connection refused` at the vendor's host, not the vendor's fault):
   ```bash
   curl --noproxy '*' https://api.deepseek.com/
   ```
   If this succeeds, the machine's proxy was blocking; if it fails, the vendor is down or unreachable.

2. **Resume the run.** Once connectivity is restored, re-run the same command:
   ```bash
   DEEPSEEK_API_KEY=... uv run ai-bench calibrate-grader-v1
   ```
   Resume-by-deliverable-hash re-uses all rulings already archived by that delivery and paid for, and re-asks nothing. The run will complete exactly 358 calls in total across both invocations, with no duplicate calls and no overage.

See #130's closing comment for how the v1 run's mid-run failure was resumed and how the calls split across the two halves.

## 5. What is committed

The rulings archive is committed whole and unedited at a single path, named by the grader version:

```bash
data/point-gate-calibration/<grader-v2-tuple>.json
```

Replace `<grader-v2-tuple>` with the v2 tuple printed by `point_grader.GRADER_VERSION`. Do not retype it — quote it verbatim from the code.

The archive is committed as a **new file** — one rulings file per instrument version — and nothing from this calibration is added to `data/unified.jsonl`. That file stays unchanged by the gate.

## 6. What is written: the record at §81

The record lands at the next free section of `docs/design/task-difficulty-and-ex-ante-profiles.md`, which is **§81** (not §80; §80 is the amendment that re-pinned the prompt).

Write the section with these elements, mirroring #130's structure:

1. **The stratum A verdict, in one sentence.** State both counts against the registered bar:
   - overall agreement: `<count> of 63` vs. `≥ 57 of 63`
   - unresolved-class agreement: `<count> of 8` vs. `≥ 7 of 8`
   - verdict: **met** or **NOT MET** — if both clauses gate, the gate passes only if both are met

2. **Stratum B's figure and confound.** Report the count `<agreed> of 243` and name the confound (the deliverable was a diff and the archived prose merely narrates it, so disagreement measures narrative truthfulness as much as the grader's skill). State that **it gates nothing**.

3. **The transfer gap.** In as many words: the gap between what the gate certifies (the grader judges argued prose against a known truth) and what it does not (whether the grader judges a proposal with no truth behind it). This would have been watched by owner labels on swept cells had the bar been met; it states anyway so the record's reader knows what a met bar would and would not have certified.

4. **Where disagreements fell.** Read them rather than score them. Quote the disagreements by category if the bar fails; if it passes, note that agreement held.

5. **Whether the two mechanisms §79.2 named are gone.** §79.2(a) was the literal-form refusal on single-point categories; §79.2(b) was the paraphrased quote. The v2 revision (§80.2) aimed at both. State whether either still appears in the archive — that is what this instrument was revised to fix.

6. **The spend, against the registered range.** Exactly 358 calls at the v2 tuple. The registered range is **$0.25–1.5**, reaffirmed at §80.4's arithmetic. Report the actual spend (the vendor's console is the invoice's word) and the date.

7. **The grader version tuple, the archive path, and the fact that nothing reached `data/unified.jsonl`.**

## 7. Frontier assertion

The frontier assertion in `tests/test_firstparty_v1_round9_cells.py` must be updated to reflect §81 as the new frontier:

- Change `numbered[-1] == 80` to `numbered[-1] == 81`
- Change `range(69, 81)` to `range(69, 82)`
- Keep the named exception comment with its explanation

Touch nothing else in that suite.

## 8. §81's pin suite

Write a new pin suite at `tests/test_firstparty_v1_round9_v2_calibration.py` in the shape of §79's suite (`tests/test_firstparty_v1_round9_calibration.py`), which re-derives both agreement figures from the committed archive offline and audits every covered ruling's span mechanically.

The suite must:

1. **Re-derive both stratum A figures from the archive** — overall agreement and unresolved-class agreement — and assert they match §81's quoted counts.

2. **Audit every covered ruling's span mechanically.** A covered ruling's archived `verified` flag must equal what `point_grader`'s own normalisation says about its span against the deliverable, using the v2 span rule (whitespace-only normalisation plus the markdown-stripped fallback defined at §80.3).

3. **Check the one-ruling-per-point shape.** The archive holds exactly 115 rulings on stratum A and 243 on stratum B, one per point, and nothing more.

4. **Check the archive is stamped and named by the version.** The archive carries the v2 grader version and is named by it — one rulings file per instrument version (§77.8's sentence).

5. **Check nothing reached `data/unified.jsonl`.** No calibration data appears in the unified dataset.

6. **Carry §80.5's freezing rule forward in one line.** A pin suite that reaches the live `GRADER_VERSION` or `span_in_deliverable` freezes those to the instrument its record was computed under, the next time the instrument moves.

7. **Slice its section deliberately.** §79's suite sliced its section from its own heading to `## Round 9 second amendment` (not to `## Open questions`, which would have swallowed §80 silently). §81's suite must slice from §81's own heading to the next top-level heading at the same level (or end-of-note if none follows) — deliberately, to avoid the same accident.

## 9. Both branches out of §81

Both outcomes are decided now, so the record only reports which one happened. Write both:

### If the bar is met

The authoring and sweep work returns as fresh issues. Re-file the work from #131–#134's own ticket texts, re-pointed at §81:

- #131: author the first `investigation` task
- #132: author the second `investigation` task
- #133: author the third `investigation` task
- #134: sweep the three new tasks across the operational ladder

Tickets 15 and 16 (the v2 prompt revision and re-registration) are green; these four are cut by the plan and resume as queued work.

### If the bar fails

§81 closes the question of this vendor's grader. The next move is **a design discussion, not a third prompt**. There is no third re-run under this vendor.

### Either branch

**#127 (ADR-0005) runs on either branch and is not among the blocked.** It writes its gating sentences from §79 and §81's actual verdicts. It can go to `qap run` immediately after the record lands.

## Acceptance

When everything is committed, this command must pass (exit code 0):

```bash
test -f docs/agents/runbook-grader-v2-gate.md && \
  ! test -f docs/agents/handoff-grader-v2-replan.md && \
  grep -q DEEPSEEK_API_KEY docs/agents/runbook-grader-v2-gate.md && \
  grep -q -- '--split-only' docs/agents/runbook-grader-v2-gate.md && \
  grep -q -- '--noproxy' docs/agents/runbook-grader-v2-gate.md && \
  grep -q '§81' docs/agents/runbook-grader-v2-gate.md && \
  uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)' | xargs -I{} grep -qF {} docs/agents/runbook-grader-v2-gate.md
```

All checks must pass. The runbook names the payment-path constraint at the top, the split-derivation step, the proxy probe, the record section number, and the v2 version tuple from the code.
