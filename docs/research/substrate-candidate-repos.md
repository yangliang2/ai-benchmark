# Substrate candidate repos — vendoring shortlist

**Status: research output, 2026-08-05. Candidate 4 (`pgularski/pysm`) and
candidate 2 (`mechatroner/RBQL`) have since been vendored — see "What was
actually vendored" at the end. The other three are still untouched shortlist
entries.**

Context: `docs/design/task-difficulty-and-ex-ante-profiles.md` §10 ("Substrate
spectrum") calls for vendoring several **cold, small, thin-dependency Python
repos** at pinned SHAs, so that terrain knobs K4–K8 can be set surgically on
real code rather than on authored scaffolds. The design note is explicit that
plural substrates are the point and that selection mistakes are cheap
("多找一些基地仓库"), so this list is sized for breadth, not for a single winner.

Every factual claim below was verified against the repo itself — a cloned
working tree, a file inside it, or a GitHub / PyPI API field — and is cited
inline. No claim comes from a blog post or a listicle.

## Verification method

- Clone (full history) → `git rev-list --count`, `git log --format=%ae | sort -u`
  for commit depth and distinct author emails.
- `gh api repos/{owner}/{repo}` for stars, forks, SPDX license id, `pushed_at`,
  `archived`; `gh api repos/{owner}/{repo}/contributors?anon=1` for contributor
  count.
- LOC via `wc -l` on the actual `.py` files (blank/comment lines included —
  these are file lengths, not SLOC).
- Dependencies read out of `pyproject.toml` / `setup.py` / `setup.cfg` **and**
  cross-checked against the actual `import` lines in the package source.
- **Every test command listed below was executed** in a clean venv on
  Python 3.14.4 with `pytest 9.1.1`, and the pass counts recorded are the
  counts that run produced.
- Coldness is judged on **PyPI download volume**, not stars — see the warning
  under "Rejected". Source: `https://pypistats.org/api/packages/{pkg}/recent`,
  queried 2026-08-05.

---

## Candidate 1 — `rbarrois/xworkflows` (workflow / state machine)

| Field | Value | Source |
|---|---|---|
| URL | https://github.com/rbarrois/xworkflows | — |
| License | BSD-2-Clause | `gh api repos/rbarrois/xworkflows .license.spdx_id`; `LICENSE` |
| Stars / forks | 190 / 26 | `gh api` `.stargazers_count`, `.forks_count` |
| Contributors | 4 (API) / 5 distinct author emails (git) | `contributors?anon=1`; `git log --format=%ae` |
| History | 206 commits, 2011-06-21 → 2021-04-29 | `git rev-list --count`, `git log` |
| Pin SHA | `c6adfb200c61dd0df768c92856355d301c2caf87` (2021-04-29) | `git rev-parse HEAD` |
| Python files | 11 | `find -name '*.py'` |
| Size | 1 143 lines source / 1 981 lines tests | `wc -l src/xworkflows/*.py tests/*.py` |
| Runtime deps | **none** — `install_requires` is empty in `setup.cfg`; source imports only `logging`, `re`, `sys`, `warnings` | `setup.cfg`; `grep '^import\|^from' src/xworkflows/*.py` |
| PyPI volume | 25 760 downloads / month | pypistats |

**Test command (verified):**
```bash
pip install -e .        # required: tests resolve the package version via importlib.metadata
pytest                  # → 98 passed
```

**Shape.** Practically the whole library is one 1 086-line module,
`src/xworkflows/base.py`, holding `State` / `StateList` / `Transition` /
`TransitionList`, a `Hook` system with ordering (`__lt__`/`__gt__` are
defined on hooks), and a descriptor stack (`ImplementationWrapper` →
`ImplementationProperty` → `TransitionWrapper`) that installs transition
methods onto user classes via a metaclass.

**Knob terrain.**
- **K7 (invariant density) — the strongest of the five.** Every transition
  must have a declared source state, hooks fire in a defined order around
  `_pre_transition_checks` / `_pre_transition` / `_during_transition` /
  `_log_transition` / `_post_transition`, and `is_available()` must agree with
  what actually happens on call. These are exactly the "invariants near the
  edit" the design note wants dense.
- **K6 (haunted areas).** `compat.py` (21 lines, `is_python3`/`is_string`/`u`)
  is live Python-2 residue in a package that no longer supports Python 2 — a
  genuine Chesterton's fence a task can be built around, not a planted one.
- **K5 (grain).** The descriptor/metaclass machinery has a very definite grain;
  against-the-grain variants are easy to specify and hard to execute.
- **K8** is naturally *good* here (98 tests over ~1.1 kloc), which makes it the
  right substrate for the K8 **family** treatment — degrade or make the net
  misleading and measure the delta against a strong baseline.

**Caveat.** Unmaintained since 2021 and the tests need an editable install to
import; both are fine for a pinned vendored snapshot, and the install step must
be recorded in the task environment setup.

---

## Candidate 2 — `mechatroner/RBQL` (SQL-like query engine over CSV)

| Field | Value | Source |
|---|---|---|
| URL | https://github.com/mechatroner/RBQL | — |
| License | MIT | `gh api` `.license.spdx_id`; `LICENSE` |
| Stars / forks | 337 / 15 | `gh api` |
| Contributors | 6 (API) / 4 distinct author emails (git) | `contributors?anon=1`; `git log` |
| History | 1 141 commits, 2017-07-15 → 2026-04-14 (**actively maintained**) | `git rev-list --count`, `git log` |
| Pin SHA | `4137027611f551591a1775d1d4c8f7fb8d163caa` (2026-04-14) | `git rev-parse HEAD` |
| Size (Python half) | 3 500 lines across `rbql-py/rbql/*.py`; core is `rbql_engine.py` (1 772) + `rbql_csv.py` (585) + `rbql_main.py` (558) | `wc -l rbql-py/rbql/*.py` |
| Runtime deps | **none** — imports are `ast`, `re`, `sys`, `os`, `io`, `json`, `math`, `datetime`, `random`, `time`, `collections`, `errno` only | `grep '^import\|^from' rbql-py/rbql/*.py` |
| PyPI volume | **603 downloads / month** — the coldest package in this list | pypistats (`rbql`) |

**Test command (verified):**
```bash
PYTHONPATH=./rbql-py pytest test/test_rbql.py test/test_csv_utils.py test/test_json_io.py
# → 45 passed
```
Deliberately excluded: `test/test_rbql_pandas.py` and `test/test_rbql_sqlite.py`
(pandas is an optional integration; sqlite tests read fixture DBs) and
`test_mad_max.py`. Vendoring should drop `rbql_pandas.py` / `rbql_sqlite.py`
along with their tests, or keep them and pin pandas.

**Shape.** A real query engine: parses an RBQL query, compiles it, and executes
it against CSV/JSON streams with join support, aggregation, `ORDER BY`, and a
warning channel. Test fixtures live in `test/csv_files/`, `test/json_files/`,
plus JSON-driven table-test manifests (`test/rbql_unit_tests.json`).

**Knob terrain.**
- **K4 (read-set ≫ write-set) — the best of the five.** Making a change to the
  engine requires reading the query AST handling in `rbql_engine.py`, the CSV
  dialect/encoding layer in `rbql_csv.py`, and the CLI surface in
  `rbql_main.py`. A one-line write-set with a three-module read-set is the
  natural state here, not something you have to construct.
- **K7.** Encoding, dialect, and newline handling in `csv_utils.py` (121 lines)
  carry sharp round-trip invariants — split/join must be inverse.
- **K11 (detection distance).** Malformed-record and warning propagation means
  a wrong edit surfaces several layers away from where it was made.
- **K6.** `rbql_engine.py` executes user query code via `ast` — genuinely
  load-bearing weird code with real reasons behind it.

**Caveat.** The repository is bilingual (there is a parallel `rbql-js/` JS
implementation and `test_rbql.js`). Vendor `rbql-py/` + the Python tests only,
and record in the task provenance that the JS twin was dropped — otherwise a
cross-language consistency invariant silently disappears.

---

## Candidate 3 — `purcell/airspeed` (Velocity-compatible template engine)

| Field | Value | Source |
|---|---|---|
| URL | https://github.com/purcell/airspeed | — |
| License | BSD 2-clause (text in `LICENCE`, "Copyright (c) 2004-2015 Steve Purcell & Chris Tarttelin"). GitHub reports `NOASSERTION` only because the file is spelled `LICENCE`; `pyproject.toml` classifies it `License :: OSI Approved :: BSD License` | `cat LICENCE`; `pyproject.toml`; `gh api .license` |
| Stars / forks | 91 / 39 | `gh api` |
| Contributors | **23** — the widest contributor base here | `contributors?anon=1` |
| History | 268 commits, **2004-08-11 → 2026-06-19** (22 years, still maintained) | `git log --reverse`, `git log -1` |
| Pin SHA | `c0c0bdeb29c191a40bb98c9ef3eb05ccddb11d8b` (2026-06-19) | `git rev-parse HEAD` |
| Size | 1 288 lines source (`airspeed/__init__.py` 1 245 + `api.py` 43) / 1 398 lines tests | `wc -l` |
| Runtime deps | `cachetools` (small, pure-Python) — and it is used **only** in `api.py:9` (`from cachetools import LRUCache`) for the optional caching file loader. The engine itself (`airspeed/__init__.py`) imports only `re`, `operator`, `os`, `string`, `sys`, `abc`, `io` | `pyproject.toml:14`; `grep -rn cachetools`; import lines |
| PyPI volume | 40 516 downloads / month | pypistats |

**Test command (verified):**
```bash
pip install -e .
python -m unittest              # → Ran 193 tests, OK   (this is what CI runs)
pytest tests/__init__.py        # → 193 passed          (under pytest)
```
Note the unusual layout: the entire suite lives in `tests/__init__.py`, so bare
`pytest` collects **nothing**. The path must be named explicitly. CI
(`.github/workflows/ci.yml`) runs `uv run python -m unittest` on Python
3.10–3.13.

**Shape.** A hand-written recursive-descent parser plus evaluator for the
Velocity template language, in one large module: `$references`, `#if`/`#foreach`
/`#macro`/`#parse`, method calls on Python objects, escaping rules.

**Knob terrain.**
- **K5 (with/against the grain) — the standout.** A 22-year-old single-module
  parser has an unmistakable house grain (every construct is a class with the
  same parse/evaluate protocol). Tasks that go with it and tasks that cut
  across it are trivially specifiable and measurably different.
- **K2 (implicit requirements).** The controlling spec is *Velocity
  compatibility*, which lives in the Java reference implementation and in
  22 years of accumulated test cases — never in a ticket. This is the
  "convention-driven difficulty" lever in a naturally occurring form.
- **K9 (crux depth).** Template-language semantics (scoping in `#foreach`,
  quiet-reference behaviour) contain single genuinely inventive decisions
  surrounded by mechanical work.
- **K8** is good-to-excellent (193 tests over 1.3 kloc), so like xworkflows it
  suits the K8 degradation family.

**Caveat.** 1 245 lines in one file makes K4/K10 (read-set spread, coordination
width) hard to set — this substrate is a K5/K2/K9 instrument, not a K4 one.

---

## Candidate 4 — `pgularski/pysm` (hierarchical state machine)

| Field | Value | Source |
|---|---|---|
| URL | https://github.com/pgularski/pysm | — |
| License | MIT | `gh api`; `LICENSE` |
| Stars / forks | 77 / 13 | `gh api` |
| Contributors | 6 (API) / 7 distinct author emails (git) | `contributors?anon=1`; `git log` |
| History | 213 commits, 2016-05-01 → 2026-06-18 (**actively maintained**) | `git rev-list --count`, `git log` |
| Pin SHA | `0c47a5067974951c75a498ee4ed025cf881f48fd` (2026-06-18) | `git rev-parse HEAD` |
| Size | ~1 750 lines source (`pysm.py` 954, `aio.py` 265, `serialization.py` 216, `builder.py` 105, …) / 5 121 lines tests | `wc -l pysm/*.py test/*.py` |
| Runtime deps | **none** — imports are `collections.deque`, `asyncio`, `sys` | `grep '^import\|^from' pysm/*.py` |
| PyPI volume | **3 309 downloads / month** | pypistats |

**Test command (verified):**
```bash
pytest test --ignore=test/test_release_scripts.py    # → 145 passed
```
The ignore is required and is not a code problem: `test_release_scripts.py`
shells out to a bare `python` binary and fails with `FileNotFoundError` in a
venv where only `python3` exists. Bare `pytest test` gives `1 failed, 149
passed`. Vendoring should drop that file (it tests the project's own release
tooling, not the library).

**Knob terrain.**
- **K7 (invariant density) — very high, and formally specified.** This is a
  UML/statechart-style HSM: entry/exit actions must fire in the correct order
  along the state hierarchy (`_exit_states`, `_enter_states`,
  `_initial_entry_path`), `leaf_state` must stay consistent with the stack,
  and `revert_to_previous_leaf_state` must restore it exactly. Breaking one of
  these produces behaviour that is wrong but not obviously wrong.
- **K8 — best safety net in the list (5 121 test lines over ~1 750 source
  lines, ~2.9:1).** That ratio is what makes it the ideal K8 **family**
  substrate: you can dial the net from excellent down through partial, bare,
  and *misleading* on the same underlying change and get a clean K8 isolation.
- **K11.** State-machine bugs manifest several dispatches after the faulty
  transition — naturally long detection distance.
- **K10.** `pysm.py` / `aio.py` / `serialization.py` / `builder.py` are four
  parallel surfaces over the same state model, so "change the model
  consistently in N places" tasks are real rather than contrived.

---

## Candidate 5 — `funkybob/stencil` (minimal Django-style template engine)

| Field | Value | Source |
|---|---|---|
| URL | https://github.com/funkybob/stencil | — |
| License | MIT | `gh api`; `LICENSE` |
| Stars / forks | 58 / 8 | `gh api` |
| Contributors | 8 (API and git agree) | `contributors?anon=1`; `git log` |
| History | 175 commits, 2016-08-11 → 2024-10-25 | `git rev-list --count`, `git log` |
| Pin SHA | `1dd661b8b17ec42fb94c8279cde5c8812f46432a` (2024-10-25) | `git rev-parse HEAD` |
| Size | **555 lines** source (single file `stencil.py`) / **154 lines** tests | `wc -l` |
| Runtime deps | **none** — `html`, `importlib`, `re`, `token`, `tokenize`, `collections`, `io`, `pathlib`, `typing` | `head stencil.py` |
| PyPI volume | **4 761 downloads / month** (package `stencil-template`) | pypistats |

**Test command (verified):**
```bash
pytest        # → 15 passed, 1 warning
```

**Knob terrain — this one is on the list for exactly one reason: K8.**
The repo ships a *naturally bare* safety net. 555 source lines, 32 classes, and
15 tests; the tests reference only `Template`, `Context`, `TemplateLoader`,
`tokenise`, `Token`, and `BlockNode`
(`grep -oh 'stencil\.[A-Za-z_]*' tests/`). That leaves `ExtendsTag`,
`BlockTag`, `IncludeTag`, `WithTag`, `CaseTag`/`WhenTag`, the whole
`AstLookup`/`AstAttr`/`AstCall` expression tree, and template inheritance
**entirely uncovered** — a real, unplanted K8-bare / K11-long region on live
code. Template inheritance (`ExtendsTag` at `stencil.py:426`, `BlockTag` at
`:449`) is the natural task site: high semantic weight, zero test coverage.

**Caveat.** At 555 lines it sits *below* the 1–10 kloc target, so it cannot
carry K4 (read-set) tasks at all. Treat it as a narrow instrument for the
K8-bare and K11 arms, paired with a high-coverage substrate (pysm, xworkflows)
for contrast — not as a general-purpose base.

---

## Rejected and near-misses

The single most useful finding: **star count is a bad coldness proxy.** Two
candidates that pass every star-based filter are among the most-downloaded
packages on PyPI, and are near-certainly memorized by any frontier model.

| Repo | Stars | Why rejected |
|---|---|---|
| `gweis/isodate` | 175 | **228 331 718 downloads/month** (pypistats). A top-tier transitive dependency (rdflib, Azure SDKs). Otherwise a perfect fit — BSD-3, stdlib-only, 280 passing tests, 24 contributors, 2009→2024 — which is precisely why it is the cautionary example. Fails criterion 1 decisively. |
| `adriank/ObjectPath` | 380 | 272 210 downloads/month; also `pytz` dep, dead since 2022, and only 38 tests over 2.9 kloc. |
| `fnl/syntok` | 211 | Depends on `regex`, a **compiled C extension** — violates the pure-Python/thin-deps criterion. 62 222 downloads/month. (75 tests do pass.) |
| `ericpruitt/cronex` | 69 | Great domain and genuinely cold, but the suite **fails on modern Python**: `8 failed, 16 passed` on 3.14 with `AttributeError`s (last commit 2018). Fails criterion 4 unless pinned to an old interpreter. |
| `aclements/biblib` | 125 | Cold, MIT, stdlib-only, nice BibTeX-parser domain — but **1 author, 29 commits, all within Nov–Dec 2013**. Fails criterion 6 (organic evolution). Worth reconsidering if that criterion is relaxed. |
| `santalvarez/python-rule-engine` | 61 | Depends on `pydantic` (+`pydantic-core`, compiled) and `jsonpath-ng`. Fails criterion 3. |
| `saurabh0719/py-rules-engine` | 36 | 1 author, 48 commits over 2 months (2023-12 → 2024-02). Fails criterion 6. |
| `eliben/luz-cpu` | 176 | Attractive domain (assembler + linker + CPU simulator), but the unit suite **does not collect** under pytest (7 collection errors), only 4 authors, 8.4 kloc, and an Unlicense/`COPYING` situation needing more care. |

---

## Ranked recommendation

**Vendor these two first:**

1. **`pgularski/pysm`** — pin `0c47a506`. It is cold by download volume (3.3k/mo),
   stdlib-only, actively maintained, and its ~2.9:1 test-to-source ratio makes
   it the single best instrument for the **K8 family** (good / partial / bare /
   misleading net over one underlying change), which the design note calls out
   as a highest-value construction trick. High K7 and long K11 come free with
   the statechart semantics.

2. **`mechatroner/RBQL`** — pin `41370276`. The coldest package found (603
   downloads/month), zero runtime deps, 1 141 commits of real evolution, and
   the only candidate whose module structure gives **K4 (read-set ≫ write-set)**
   for free. Budget a little vendoring work to strip `rbql-js/`, the pandas and
   sqlite integrations, and their tests.

**Then, if a third is wanted:**

3. **`rbarrois/xworkflows`** — pin `c6adfb20`. Cleanest **K7** terrain of the
   five, plus a real un-planted **K6** site in the vestigial `compat.py`.
   Cheapest to vendor (11 files, no deps); the only cost is recording the
   `pip install -e .` step.

`purcell/airspeed` is the right choice specifically when a **K5/K2** experiment
is on the table — its 22-year Velocity-compatibility grain is not reproducible
in an authored repo — and `funkybob/stencil` should be picked up only as the
paired **K8-bare** arm, given it is under half the target size.

A useful property of this set for the external-validity check in open question
3: it contains **two state machines** (pysm, xworkflows) and **two template
engines** (airspeed, stencil) with sharply different safety-net quality. Running
the same knob at the same level across a matched pair tests whether the knob →
difficulty ordering survives a substrate swap, holding domain roughly constant.

---

## What was actually vendored

Two sections, one per substrate. Both record the same thing and for the same
reason: the *recipe* is not recoverable from the snapshot, because
`construction.substrate.modifications` records the knob-setting edits — which
is what it is for — and says nothing about what was left out of the snapshot
in the first place.

### `pgularski/pysm` (ticket #22, 2026-08-05)

`pgularski/pysm` at the pinned `0c47a506…`, into three task directories under
`tasks/first-party-v1/pysm-*`.

**Layout.** The visible test suite sits at the root of `repo/` beside the
`pysm/` package, not in a `test/` subdirectory as upstream. Two reasons: plain
`pytest` in the workdir then finds the package without a `conftest.py` putting
the root on `sys.path`, and a top-level `test/` would sit next to a
standard-library package name in a tree that grading keeps *behind* the
standard library. Upstream's `conftest.py` was dropped for that first reason:
the flattened layout is what makes it unnecessary, not packaging hygiene.

**Kept:** `pysm/*.py` (all six modules — stdlib-only, verified import by
import), `LICENSE`, `README.rst`, and 12 of the 14 upstream `test_*.py` files.

**Dropped, and why — none of it knob-motivated:**

- `.git`, `.github/`, `docs/`, `examples/`, `setup.py`, `setup.cfg`,
  `.pylintrc`, `.readthedocs.yaml`, `CHANGELOG.md` — VCS metadata, CI, and
  packaging. (`conftest.py` went too, for the layout reason above.)
- `pysm/*.pyi` and `pysm/py.typed` — typing metadata, not needed to run, and
  keeping them would make every reference solution a cross-file diff for
  stub-only reasons.
- `test/test_release_scripts.py` — tests the project's own release tooling and
  shells out to a bare `python` (the research note above already flags it).
- `test/test_micropython_optional_modules.py` — rewrites module files on disk
  to simulate a MicroPython interpreter.
- `test/upysm_smoke.py` — not a pytest file.
- Two tests inside `test_pysm.py`
  (`test_core_imports_without_logging_module`,
  `test_core_imports_without_collections_defaultdict`) — they reach for
  `pysm/pysm.py` through `dirname(dirname(__file__))`, which is the upstream
  `test/` layout and not the vendored one.

**Test counts.** Upstream `pytest test --ignore=test/test_release_scripts.py`
gives 145 passed. The snapshot above, before any knob edit, gives **138**. The
two K8-misleading tasks then delete the tests covering the contract they grade
and ship **136** passing tests each; the K7 task ships the 138 unchanged.

**Confirmed under the grading isolation**, which was the risk worth probing
first: the package imports and runs with `--noconftest`, the pinned config, and
the workdir behind the standard library on `sys.path`. No module in it is named
after a standard-library one, so the loader's shadowing rejection does not fire.

### `mechatroner/RBQL` (ticket #23, 2026-08-05)

`mechatroner/RBQL` at the pinned `41370276…`, into two task directories under
`tasks/first-party-v1/rbql-*`. The second substrate, and the point of doing it
was to find out which parts of the pysm recipe were the recipe and which were
pysm. The answer: the flattened layout and the licence-in-`repo/` rule carried
over unchanged, and the only new work was deciding what "the Python half"
means in a bilingual repository.

**Layout.** Same shape as pysm's, for the same reason: the visible test files
sit at the root of `repo/` beside the `rbql/` package rather than in the
upstream `test/` directory, so that plain `pytest` in the workdir finds the
package without a `conftest.py` putting the root on `sys.path`. The fixture
directories the tests read (`csv_files/`, `json_files/`, `other_test_files/`)
and the three JSON test manifests move to the root with them, because the
tests resolve every fixture against `os.path.dirname(os.path.abspath(__file__))`.

That flattening leaves one dead line in each vendored test file: they also do
`sys.path.insert(0, os.path.join(os.path.dirname(script_dir), 'rbql-py'))`,
which in this layout names a directory that does not exist. It was left
byte-identical rather than "fixed" — a non-existent `sys.path` entry is
skipped, `import rbql` falls through to the root pytest already put there, and
editing upstream code that works is how a snapshot stops being a snapshot.

**The bilingual half.** The shortlist entry above flags it, and it is the one
genuinely new decision here. Dropped whole: `rbql-js/`, and the three
JavaScript test files beside the Python ones (`test/test_rbql.js`,
`test/test_csv_utils.js`, `test/test_common.js`). Recorded here rather than in
any task's metadata, because dropping the twin also drops a real
cross-language consistency invariant — upstream keeps the two implementations
agreeing test-for-test, and the vendored snapshot cannot.

**Kept:** `rbql/*.py` (nine of the eleven modules), the repository's `LICENSE`
(MIT, Dmitry Ignatovich), `rbql-py/LIBRARY_README.md` as `README.md`, three of
the upstream test files (`test_rbql.py`, `test_csv_utils.py`,
`test_json_io.py`) and the fixtures and manifests they read.

`rbql_sqlite.py` is **kept**, which departs from the shortlist entry's advice
to drop it alongside `rbql_pandas.py`. The reason that advice existed is the
sqlite *tests*, which read binary fixture databases, and those are dropped. The
module itself imports `re`, `os`, `sys` and the engine; `sqlite3` is the
standard library and is imported by its callers in `rbql_main.py`, so keeping
it costs nothing and dropping it would have meant surgery on ~39 lines of
`rbql_main.py` — the CLI surface that is half of why this substrate was picked
for K4 in the first place. Cutting un-knobbed holes in the module a task's
read-set runs through is a worse trade than carrying a module no test touches.

**Dropped, and why — none of it knob-motivated:**

- `.git`, `.github/`, `DEV_README.md`, `rbql_logo.png`, `test_all.sh`,
  `rbql-py/setup.py`, `rbql-py/MANIFEST.in`, `rbql-py/DEV_README.md`,
  `rbql-py/README.md`, `rbql-py/LICENSE` (a duplicate of the root one) — VCS
  metadata, CI, packaging and developer docs.
- `rbql/rbql_pandas.py` — pandas is a third-party dependency, and a
  starting repository has to be stdlib-only. (It imports pandas lazily, so
  keeping it would not have broken `import rbql`; it would have left a module
  that cannot run in a repository whose whole claim is that everything in it
  can.)
- `rbql/rbql_ipython.py` — the IPython magic, which exists to query pandas
  dataframes and imports `rbql_pandas` at module level, so it goes with it.
- The two lines in `rbql/__init__.py` that re-export those two modules. This
  is the only edit to vendored *source* in either snapshot, and it is a
  consequence of the two deletions rather than a decision of its own: without
  it `import rbql` raises ImportError.
- `test/test_rbql_pandas.py`, `test/test_rbql_sqlite.py`, `test/sqlite_files/`
  — the tests of the two integrations, one needing pandas and the other
  reading binary `.sqlite` fixtures.
- `test/test_mad_max.py` — excluded by upstream's own verified test command
  (see the shortlist entry above).
- `test/__init__.py`, `test/library_demos/` — the package marker the flattened
  layout does not need, and hand-run demo scripts (Python, JavaScript and
  HTML) rather than tests.
- One test inside `test_rbql.py`, `test_column_name_parsing_from_file` — it
  writes `python_column_infos.txt` into the directory it lives in, which in
  the flattened layout is the root of `repo/`, so every run's workdir diff
  would carry the artifact. What it exists for is md5-comparison against the
  JS twin's output, and the twin is not vendored.

**Test counts.** Upstream
`PYTHONPATH=./rbql-py pytest test/test_rbql.py test/test_csv_utils.py test/test_json_io.py`
gives 45 passed. The snapshot above, before any knob edit, gives **44** — the
one JS-comparison test. The K7 task ships those 44 unchanged; the
K8-misleading task then deletes the three tests covering the contract it
grades and ships **41**.

**Confirmed under the grading isolation** before anything was authored on it,
because RBQL compiles and `exec`s the user's query through `ast` and that was
the risk worth probing first: a throwaway task graded 1.0 on a probe suite
that imported the package, ran a query with `where`/`order by` over an
in-memory table, round-tripped a quoted CSV file through `query_csv`, and
reached `csv_utils` and `rbql_engine` directly — all with `--noconftest`, the
pinned config, and the workdir behind the standard library on `sys.path`. No
module in the tree is named after a standard-library one (`rbql`, `csv_files`,
`json_files`, `other_test_files`, `test_*.py`), so the loader's shadowing
rejection does not fire.

One thing that probe did *not* have to catch, and is worth writing down because
the next substrate might: keeping the upstream `test/` directory would have put
a top-level package sharing a name with CPython's own `test` package into the
tree, and the loader would have allowed it — `sys.stdlib_module_names`, which
is what the shadowing check reads, does not list `test`. Nothing here imports
it, so it would have been latent rather than broken, which is exactly the shape
of problem the flattening avoids for free.
