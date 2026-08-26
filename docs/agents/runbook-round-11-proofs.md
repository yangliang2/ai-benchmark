# Runbook: The round 11 proofs (§95)

This is the operational record for running the point gate's two-sided existence proofs on round 11's three `requirement-decomposition` tasks. Run by hand in the session; never queued. One paid run per planted point and per disqualifier against each of the two answers (reference and foil), 8–16 calls a task, 24–48 for the round. The session's own frontier assertion moves to §95 with the record.

## 1. Payment-path pre-flight: `DEEPSEEK_API_KEY` stored in session memory by owner ruling

The `DEEPSEEK_API_KEY` is **stored in the operator's session memory** by the owner's ruling of **2026-08-23**, a **disclosed exception** to the standing stored-nowhere rule. The key is **supplied inline in the invoking command's environment**:

```bash
export DEEPSEEK_API_KEY=...
# then all steps below
```

The operational rules that survive the exception, all three stated: the key is **supplied inline in the invoking command's environment** and is **committed to no file** in this repository and **written to no config** here; it is **never printed**, not into a log, a transcript quote, a record or an error message; and the proofs run is **never queued to the ticket harness** — it is run by hand in the session.

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

3. **Instrument tuple matches registration.** Read the grader version from the code:
   ```bash
   uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)'
   ```
   It must print:
   ```
   deepseek-v4-pro:DeepSeek-V4-Pro-0813:8bf4fedb86be
   ```
   A moved checkpoint is a version change and **stops the round for re-registration** — if the tuple differs, do not proceed.

## 3. The run: prove every planted point and disqualifier

Run the point gate over each task's reference answer and foil answer. For each of the three tasks, call:

```bash
uv run ai-bench prove-points-v1
```

One call per planted point and per disqualifier against each answer, 8–16 calls a task, 24–48 for the round in total. This is the one affordance in this project that calls the grader outside a run; `ai-bench lint-v1` never calls the LLM.

The registered call range is **8–48**, against §95's registered range. Re-running the command re-uses everything already archived and paid for and re-asks nothing.

## 4. Connection-failure procedure

If the run fails mid-stream with a connection error:

1. **Probe the local proxy first.** The machine's system proxy is the first suspect (a `Connection refused` at the vendor's host, not the vendor's fault):
   ```bash
   curl --noproxy '*' https://api.deepseek.com/
   ```
   If this succeeds, the machine's proxy was blocking; if it fails, the vendor is down or unreachable.

2. **Resume the run.** Once connectivity is restored, re-run the same command:
   ```bash
   uv run ai-bench prove-points-v1
   ```
   Resume-by-deliverable-hash re-uses all rulings already archived and paid for, and re-asks nothing. The run will complete with no duplicate calls and no overage.

## 5. The gate: what it bars

The bar is stated as a universal quantifier: **every planted point of every task's reference answer resolves, every foil answer fails**. Read offline by the lint from the archived rulings (`_the_reference_resolves_and_the_foil_fails`, `src/ai_benchmark/firstparty_v1.py:5681`). The gate is a hard dependency edge — no sweep dollar moves until every proof of all three tasks is green under the lint.

## 6. What is committed

For each task, commit:

- `proofs/reference-answer.md` — the author's reference answer
- `proofs/foil-answer.md` — the author's foil answer  
- `proofs/rulings/reference.json` — the rulings archive for the reference answer
- `proofs/rulings/foil.json` — the rulings archive for the foil answer

The archive is stamped with the grader version (`GRADER_VERSION`), the points key's hash and each answer's hash, so editing the key or either answer, or bumping the instrument, refuses at lint until the proof is re-run. **Re-proof triggers on edit, not on every lint run.**

Nothing from the proofs reaches `data/unified.jsonl`.

## 7. The deliverable and what gets proved

The deliverable is `ANSWER.md` with three sections: **Pieces**, **Order and dependencies** and **Open questions and risks**. A planted point is a fact of the code and its consequence for the decomposition — a piece an honest decomposition cannot omit, a dependency the code forces, a consequence a fluent-but-ungrounded split misses. The foil is the **fluent-but-ungrounded split** — plausible pieces, the disqualified claim made, the planted facts unsaid.

## 8. The failure branches

Two kinds of failure can occur:

1. **A point the reference answer cannot cover is a wrong point** — the unmeetable-point analog of an equivalent mutant. Rewrite the point and re-prove, never weaken the check.

2. **A foil the grader resolves is a key that does not discriminate** — the foil fails to demonstrate the grader can tell a wrong answer from a right one. Rewrite the key or the foil and re-prove.

**A failed proof stops the round with a record** — the record ticket runs on that branch too, heap 3 stays empty, disclosed, and the round has cost authoring effort plus the proofs' cents and nothing more.

## 9. The gate is a hard dependency edge

No sweep dollar moves until every proof of all three tasks is green under the lint.

## Acceptance

When everything is committed, this command must pass (exit code 0):

```bash
test -f docs/agents/runbook-round-11-proofs.md && \
  grep -q DEEPSEEK_API_KEY docs/agents/runbook-round-11-proofs.md && \
  grep -q 'session memory' docs/agents/runbook-round-11-proofs.md && \
  grep -q -- '--noproxy' docs/agents/runbook-round-11-proofs.md && \
  grep -q 'prove-points-v1' docs/agents/runbook-round-11-proofs.md && \
  grep -q 'lint-v1' docs/agents/runbook-round-11-proofs.md && \
  grep -q '§95' docs/agents/runbook-round-11-proofs.md && \
  uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)' | xargs -I{} grep -qF {} docs/agents/runbook-round-11-proofs.md
```

All checks must pass. The runbook names the payment-path constraint at the top with the key stored in session memory by the owner's ruling, the `--noproxy` proxy probe rule, the `prove-points-v1` invocation, the `lint-v1` offline check, the §95 reference, and the instrument tuple from the code.
