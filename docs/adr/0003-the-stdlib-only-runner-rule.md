# ADR-0003: The stdlib-only runner rule

Status: accepted
Date: 2026-08-19

## Context

Round 7 admits the project's second **language runner**, TypeScript, and
records the rule the next one after that is admitted against too (design
note §45.8). Every task graded so far has been stdlib Python: no
`pip install`, no network, no vendored dependency tree. That property was
never written down as a rule of the corpus — it was simply true of the only
language there was.

**Execution-verified** grading (`CONTEXT.md`) already accepts that it runs
agent-written code in a local subprocess with a timeout, not a sandbox
(`ai_benchmark.firstparty_v1`). That acceptance rests on the corpus having
nothing to fetch or install: grading needs no network and no installs
because starting repositories are stdlib Python. Widening the corpus to a
second language could keep that property or spend it, and nothing had ruled
which.

## Decision

A **language runner** is admitted only if a task in that language can be
graded with the language's own toolchain and **nothing installed** — no
package manager step, no network fetch, no vendored dependency tree, on
either the starting repository or its held-out grading tests.

TypeScript is admitted under this rule: Node 22.18 ships `node:test`, a JUnit
reporter and default type-stripping, so a TypeScript task is authored and
graded with no `package.json` and no `node_modules` at all — the same
hermetic footing the Python corpus has had since round 1. Go is named as a
language the rule would also admit, on the same reasoning (a single static
binary, no package manager step to grade). Neither ruling opens a language
whose only toolchain requires installing something to run its tests.

## Rationale

- **Hermeticity has been a property of Python, not of the corpus.** Nothing
  enforced it; it was true because the only language available was stdlib
  Python. Naming it as a rule is what makes it survive the corpus growing a
  second language, rather than quietly depending on no author reaching for
  a package.
- **A dependency tree would make process isolation a precondition.** Grading
  a task whose toolchain needs installed packages means fetching and running
  code this project does not control, inside the same process tree the
  oracle's verdict is read from (`CONTEXT.md`'s execution-verified
  limitation). That is a materially different exposure than running a small
  hand-authored repository's own tests, and closing it needs process-level
  isolation (#15, open and unscheduled) as a precondition for admitting the
  language at all.
- **The rule is what keeps #15 unscheduled through the widening.** By ruling
  out any language whose grading needs installs, round 7 admits TypeScript
  without needing #15 first. #15 stays open for the reason it always was,
  not because widening the corpus made it newly urgent.

## Alternatives considered

- **Process isolation as a precondition** (#15). Rejected for round 7: it
  would block every language the widening might otherwise admit on a piece
  of infrastructure nobody has scheduled, when a rule about which languages
  are eligible achieves the same safety more cheaply for the languages that
  qualify under it.
- **A vendored dependency tree as substrate.** Rejected: grading would need
  to fetch or ship third-party code, which reopens the network/install
  surface the stdlib-only corpus never had, for a hermeticity cost that
  buys nothing the toolchain itself doesn't already provide when the
  toolchain is stdlib-only.
- **A per-language container.** Rejected: it substitutes one kind of
  installed surface (image build, container runtime) for another, and this
  project's grading has run as a local subprocess since round 1 — a
  container changes what has to be trusted and operated, it does not remove
  the trust question the stdlib-only rule answers directly.

## Consequences

- **What the rule forbids an author.** A TypeScript starting repository may
  not ship a `package.json` or a `node_modules` directory; its imports are
  limited to `node:` builtins and relative `.ts` imports within the task's
  own `repo/` (`CONTEXT.md`'s starting repository entry).
- **What it costs an agent.** A dependency the agent installs during a run
  is neither captured in the **workdir diff** nor available at grade time —
  the workdir diff is a `git diff` against the pristine commit, and an
  installed package is not part of it. A solution that rests on such a
  package is ungraded exactly the way the rule says it must be: the grading
  tests run against a workdir the install never reached.
- **`frontend` stays closed.** Node has no DOM; a DOM-capable runner needs
  either a vendored `jsdom` (a dependency, forbidden by this rule as it
  stands) or a browser runtime (a different runner altogether). The
  `frontend` surface stays closed to TypeScript tasks until a DOM-free or
  browser runner is ruled on separately (design note §45.11) — this ADR
  does not open it.
- The one machine-readable definition of what a runner is is
  `ai_benchmark.language_runners`; `CONTEXT.md`'s **language runner** and
  **starting repository** glossary entries carry the human-readable rule
  this ADR records.
