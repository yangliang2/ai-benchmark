# Runbook: The round 12 proofs (§106)

This is the operational record for running the point gate's two-sided existence proofs on round 12's three `codebase-comprehension` tasks. Run by hand in the session; never queued. One paid run per planted point and per disqualifier against each of the two answers (reference and foil), 8–16 calls a task. **The writer has no resume — it re-asks whatever it is pointed at — so every run here names its tasks with `--task`, and the round's registered call arithmetic includes metered calls with `--task` selection mandatory (§96 amendment and §107 registration).**

## 1. Payment-path pre-flight: `DEEPSEEK_API_KEY` stored in session memory by owner ruling

The `DEEPSEEK_API_KEY` is **stored in the operator's session memory** by the owner's ruling of **2026-08-23**, a **disclosed exception** to the standing stored-nowhere rule. The key is **supplied inline in the invoking command's environment**:

```bash
export DEEPSEEK_API_KEY=...
# then all steps below
```

The operational rules that survive the exception, all three stated: the key is **supplied inline in the invoking command's environment** and is **committed to no file** in this repository and **written to no config** here; it is **never printed**, not into a log, a transcript quote, a record or an error message; and the proofs run is **never queued to the ticket harness** — it is run by hand in the session.

## 2. Liveness probe and local-proxy rule

Before the run starts, verify the payment path is live:

```bash
curl --noproxy '*' https://api.deepseek.com/
```

This command confirms the vendor is reachable, bypassing any local system proxy that may have produced a `Connection refused` that reads like a vendor outage. **On any connection failure during the proof run, probe with this command before concluding the vendor is down, then resume.** If this pre-flight probe fails, the vendor is down or the network is unreachable; if it succeeds, the machine's system proxy is suspect.

## 3. Instrument tuple: read from code, never retyped

The grader is a versioned instrument (model id + checkpoint; version tuple read once and archived). Read the grader version from the code:

```bash
uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)'
```

It must print:
```
deepseek-v4-pro:DeepSeek-V4-Pro-0813:8bf4fedb86be
```

A moved checkpoint is a version change and **stops the round for re-registration** — if the tuple differs, do not proceed. The tuple is recorded here and restated below in section 8.

## 4. The one-clause-tight authoring rule — the discipline this round tests first

§106.1 ruled: **from this round on, a planted point is written one-clause-tight — one point is one fact of the code that a single evidence span can hit, and a consequence is its own point, never a trailing clause.** 

No machine lint holds it: it is an authoring discipline, written into the authoring ticket's own text and policed where authoring is already policed — the spec review and the two-sided proofs. 

An author who finds a point uncoverable by a reference answer that plainly states it should suspect the *point*'s shape first. This is the round's first test of the discipline: a planted multi-clause point met by no single evidence span is a wrong point. Rewrite the point one-clause-tight and re-prove rather than weakening the check. A recurrence of this shape in a later round is evidence the record must report.

## 5. Proof answers avoid typographic quotes

Round 11's re-prove lesson: a curly quote in a reference answer cost a full re-prove on a mechanical span miss. Write proof answers in plain ASCII quotes. Every quote the grader sees must be ASCII `"` or `'`, never `"`, `"`, `'`, `'` or any Unicode variant.

## 6. Pre-flight checks

Before the run starts, verify:

1. **Full test suite green.** Run the suite and confirm all pass:
   ```bash
   uv run pytest -q
   ```

2. **Lint clean.** Run the v1 linter with no errors:
   ```bash
   uv run ai-bench lint-v1
   ```

3. **Instrument tuple matches registration.** The check from section 3:
   ```bash
   uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)'
   ```
   It must print `deepseek-v4-pro:DeepSeek-V4-Pro-0813:8bf4fedb86be`. A moved checkpoint is a version change and **stops the round for re-registration**.

## 7. The gate: what it bars, and the proof form

The bar is stated as a universal quantifier: **every planted point of every task's reference answer resolves, every foil answer fails**. Read offline by the lint from the archived rulings (`_the_reference_resolves_and_the_foil_fails`, `src/ai_benchmark/firstparty_v1.py:5681`). 

For this round's category (`codebase-comprehension`, explain-style on a points key): the gate is the point gate's production form — every planted point of the reference answer resolves under the grader, and every disqualifier either fails to appear in the reference or is articulated as an exception; every planted point of the foil answer fails to resolve under the grader. The gate is a hard dependency edge — no sweep dollar moves until every proof of all three tasks is green under the lint.

## 8. The run: prove every planted point and disqualifier

Run the point gate over each task's reference answer and foil answer. For each of the three tasks, call:

```bash
uv run ai-bench prove-points-v1 --task <the task id this run is proving>
```

One call per planted point and per disqualifier against each answer, 8–16 calls a task. This is the one affordance in this project that calls the grader outside a run; `ai-bench lint-v1` never calls the LLM.

**`--task` is mandatory here, and the reason is a bill.** The writer has **no resume**: it re-asks every question of every task it is pointed at, both sides, on every invocation, and rewrites the archive with what comes back. Left unselected it re-asks — and re-pays for — every point-keyed task in the corpus. So **each of the round's proof runs names exactly the task ids it means to pay for**, repeating the flag once per id. An id naming no task, or naming a task that ships no points key, is refused before any client is constructed.

The registered call arithmetic for round 12 (§107) is **metered calls with `--task` selection mandatory**, counting the calls for the three tasks' two-sided proofs at **4–6 planted points and 0–2 disqualifiers per task**, meaning **8–16 calls per task for the two proofs**.

## 9. Connection-failure procedure

If the run fails mid-stream with a connection error:

1. **Probe the local proxy first.** The machine's system proxy is the first suspect (a `Connection refused` at the vendor's host, not the vendor's fault):
   ```bash
   curl --noproxy '*' https://api.deepseek.com/
   ```
   If this succeeds, the machine's proxy was blocking; if it fails, the vendor is down or unreachable.

2. **Re-run the same selected command.** Once connectivity is restored, re-run it with the same `--task` ids:
   ```bash
   uv run ai-bench prove-points-v1 --task <the same task id>
   ```
   **This re-asks that task from the start and is paid for again — there is no resume and there never was one** (§96). What `--task` bounds is the damage: a run that dies mid-task costs that task's 8–16 calls twice and nothing else, where an unselected re-run would re-ask every archive in the corpus. Count the second attempt into the round's metered calls and note it in the record.

## 10. What is committed

For each task, commit:

- `proofs/reference-answer.md` — the author's reference answer
- `proofs/foil-answer.md` — the author's foil answer  
- `proofs/rulings/reference.json` — the rulings archive for the reference answer
- `proofs/rulings/foil.json` — the rulings archive for the foil answer

The archive is stamped with the grader version (`GRADER_VERSION`), the points key's hash and each answer's hash, so editing the key or either answer, or bumping the instrument, refuses at lint until the proof is re-run. **Re-proof triggers on edit, not on every lint run.**

Nothing from the proofs reaches `data/unified.jsonl`.

## 11. The deliverable and what gets proved

The deliverable is `ANSWER.md` with three sections: **What happens** (the behaviour traced through the code step by step in the repository's own terms), **Why it comes out that way** (the specific decisions in the code that produce the behaviour, load-bearing facts named one by one), and **Boundaries and edge behavior** (what the mechanism does at the edges and on the paths the question did not name). A planted point is a fact of the code and what that fact requires the explanation to account for — a line that writes what the walk must trace, an interaction an honest explanation cannot omit. The foil is the **fluent explanation that reads well and misses the planted facts** — plausible, articulate, and wrong.

## 12. The failure branches

Two kinds of failure can occur:

1. **A point the reference answer cannot cover is a wrong point** — the unmeetable-point analog of an equivalent mutant. Rewrite the point one-clause-tight and re-prove, never weaken the check.

2. **A foil the grader resolves is a key that does not discriminate** — the foil fails to demonstrate the grader can tell a wrong answer from a right one. Rewrite the key or the foil and re-prove.

**A failed proof stops the round with a record** — explain-style `codebase-comprehension` stays absent, and the round has cost authoring effort plus the proofs' cents and nothing more.

## 13. The gate is a hard dependency edge

No sweep dollar moves until every proof of all three tasks is green under the lint.

## Acceptance

When everything is committed, this command must pass (exit code 0):

```bash
test -f docs/agents/runbook-round-12-proofs.md && \
  grep -q DEEPSEEK_API_KEY docs/agents/runbook-round-12-proofs.md && \
  grep -q 'session memory' docs/agents/runbook-round-12-proofs.md && \
  grep -q -- '--noproxy' docs/agents/runbook-round-12-proofs.md && \
  grep -q -- '--task' docs/agents/runbook-round-12-proofs.md && \
  grep -q 'prove-points-v1' docs/agents/runbook-round-12-proofs.md && \
  grep -q 'lint-v1' docs/agents/runbook-round-12-proofs.md && \
  grep -q '§107' docs/agents/runbook-round-12-proofs.md && \
  grep -q 'one-clause-tight' docs/agents/runbook-round-12-proofs.md && \
  uv run python -c 'from ai_benchmark import point_grader as p; print(p.GRADER_VERSION)' | xargs -I{} grep -qF {} docs/agents/runbook-round-12-proofs.md
```

All checks must pass. The runbook names the payment-path constraint at the top with the key stored in session memory by the owner's ruling, the `--noproxy` proxy probe rule, the `prove-points-v1` invocation, the `lint-v1` offline check, the §107 reference, the one-clause-tight discipline and its testing, and the instrument tuple from the code.
