"""The language runner seam: the per-language half of execution-verified grading.

A **language runner** is the named answer to "how is a task in this language
graded". It is selected by the task's own declared `language` and by nothing an
operator can pass: a task carries its own grading mechanism, and no flag may
grade a task with the wrong one.

Everything that used to be a pytest fact scattered through the grader lives
here, so that admitting a second language is registering a second entry rather
than editing the grader. `python` is the first instance — pytest with junitxml —
and `typescript` the second, `node --test` with the JUnit reporter and nothing
installed. The second one is what the seam was built for, and it arrived as an
entry: the grader below it did not change to admit it.

**What a runner owns** — this list and no more:

1. *how the language-native grading tests are invoked* — argv, pinned config,
   environment, and a report path outside the workdir (`run_tests`, and for
   Python the pinned `_GRADING_CONFIG` and `_PATH_PLUGIN` written beside the
   workdir rather than in it);
2. *how the machine-readable verdict is read back* — folded into `run_tests`,
   whose bool is the verdict; for Python that is `_report_shows_every_test_passed`
   over the junitxml report;
3. *the glob that finds held-out grading tests* (`grading_test_glob`) *and the
   glob for a repository's visible tests* (`visible_test_glob`);
4. *the toolchain check* — what must be present, and the loud refusal when it
   is not (`require_toolchain`);
5. *the starting-repository naming invariant* (`starting_repository_problem`);
6. *the source primitives the lint needs* — the symbols a file defines
   (`defined_symbols`), the classes a file defines (`defined_classes`), and
   whether a source file can be read at all by whatever answers those two
   (`loads`), plus the glob that finds a repository's source files at all
   (`source_glob`).

**What stays the grader's,** in `ai_benchmark.firstparty_v1`: the throwaway
root with the workdir beneath it, copying `repo/` in, `git init` + `git apply`
of the logged diff, overlaying `grading/` last so an agent's edit at a grading
path is overwritten, the single timeout, `evaluate()` and every record field it
writes. A runner is handed a root and a workdir that are already built; it
never builds one.

One thing here answers to none of that list and says so where it sits:
`typescript_load_problems`, the probe the *task-set lint* imports a checked-in
`.ts` file with. It is not a seventh responsibility — nothing in it runs a test
or reads a verdict — and it lives beside the TypeScript runner only because
everything it knows is Node's.

**What stays harness-side and language-agnostic:** the answer-key module and
test (`ai_benchmark._answer`, `grading/test_answer.py`), the findings-key module
and test (`ai_benchmark._findings`, `grading/test_findings.py`), and the
generated hash gate. They read JSON and file digests out of the workdir and
never the repository's language; they ship byte-for-byte into any task's grading
directory and are run by pytest, which is the harness's own dependency and not
the task's. A TypeScript task's grading directory therefore holds canonical
Python beside its own held-out tests, and that is not a contradiction: the
harness-side half is not the task's language runner's business at all.
"""

import ast
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import ClassVar
from xml.etree import ElementTree

from ai_benchmark.dataset import IngestError


class SourceUnreadable(Exception):
    """A source file the runner cannot read the declarations of.

    The language-agnostic spelling of "this file does not parse": the Python
    runner raises it in place of `SyntaxError`, so a caller in the grader
    catches one exception rather than one per language. Its message is the
    reading instrument's own, because that is what the lint quotes back to an
    author — `ast`'s for Python, and for TypeScript the declaration scan's
    account of what it could not get through.
    """


class LanguageRunner(ABC):
    """One language's answer to the six responsibilities in the module
    docstring. Registered in `RUNNERS` under `language`, and reached only
    through `runner_for`."""

    #: The task-declared `language` this runner is registered under.
    language: ClassVar[str]

    #: Responsibility 3. Relative to a task's `grading/` directory, read
    #: recursively: what `Task.grading_test_paths` collects and hands to
    #: `run_tests`.
    grading_test_glob: ClassVar[str]

    #: Responsibility 3. Relative to a task's `repo/`: the repository's own
    #: tests, the net the agent sees, which grading never reads.
    visible_test_glob: ClassVar[str]

    #: Responsibility 6. Relative to a task's `repo/`: every source file of the
    #: starting repository, tests included, which is what the terrain rules
    #: read the repository through.
    source_glob: ClassVar[str]

    @abstractmethod
    def require_toolchain(self) -> None:
        """Responsibility 4. Raise `IngestError` unless what grades this
        language is present, before any test runs: a verdict must never be a
        toolchain artefact."""

    @abstractmethod
    def run_tests(
        self, root: Path, workdir: Path, targets: Sequence[str], *, timeout_s: int
    ) -> bool:
        """Responsibilities 1 and 2. Run the named tests in `workdir`, and
        return True only if they all actually passed.

        `root` is the throwaway directory the grader built, with `workdir`
        beneath it: everything the verdict rests on — pinned config, plugins,
        the report — is written under `root` and outside `workdir`, because a
        logged diff can only write inside the workdir. `targets` are paths
        relative to the workdir.
        """

    @abstractmethod
    def starting_repository_problem(self, repo_dir: Path) -> str | None:
        """Responsibility 5. What makes this starting repository ungradable
        under this language's import rules, as a sentence the loader appends to
        the task id — or None where it is fine."""

    @abstractmethod
    def loads(self, source: str) -> bool:
        """Responsibility 6. Whether this source file can be read at all by the
        instrument that answers the two primitives below — `ast` for Python, a
        declaration scan for TypeScript.

        What a caller asks before it asks what a file defines, and what those
        two raise `SourceUnreadable` for where it is False.
        """

    @abstractmethod
    def defined_symbols(self, source: str) -> set[str]:
        """Responsibility 6. Every symbol this file defines, in every spelling
        an accepted answer may legitimately name it by.

        Raises `SourceUnreadable` where `loads` is False.
        """

    @abstractmethod
    def defined_classes(self, source: str) -> set[str]:
        """Responsibility 6. The classes this file defines at its own top
        level — the level an accepted answer naming a class is answering at.

        Raises `SourceUnreadable` where `loads` is False.
        """


# --- the python runner ---------------------------------------------------------

# The config grading runs under, pinned so nothing in the workdir is consulted.
_GRADING_CONFIG = "[pytest]\naddopts =\n"

# Loaded with -p from outside the workdir. Python is started with -P and pytest
# with --import-mode=importlib so that nothing puts the workdir on sys.path;
# this puts it back at the end, behind the standard library.
_PATH_PLUGIN_NAME = "gradingpath"
_PATH_PLUGIN = """\
import sys

WORKDIR = {workdir!r}


def pytest_configure(config):
    sys.path.append(WORKDIR)
"""


class PythonRunner(LanguageRunner):
    """Python's instance: pytest with junitxml, and the standard library ahead
    of the workdir on `sys.path`."""

    language = "python"
    grading_test_glob = "test_*.py"
    visible_test_glob = "test_*.py"
    source_glob = "*.py"

    def require_toolchain(self) -> None:
        """Grading shells out to pytest; without it every task would score 0.0
        and look like a very bad model rather than a broken environment."""
        if importlib.util.find_spec("pytest") is None:
            raise IngestError(
                f"pytest is not installed in {sys.executable} — v1 grading runs the "
                "task's tests in a subprocess and cannot grade without it"
            )

    def run_tests(
        self, root: Path, workdir: Path, targets: Sequence[str], *, timeout_s: int
    ) -> bool:
        """Run the named tests in workdir. True only if they all actually passed.

        The verdict must depend on the held-out tests alone, so pytest is given no
        chance to read anything else the agent wrote:

        - `-c` pins the config file, so pytest.ini / tox.ini / setup.cfg /
          pyproject.toml in the workdir cannot contribute `addopts` (and with it
          arbitrary plugins), and `--noconftest` stops conftest.py at any depth
          from running hooks. Both directions matter: without them a conftest can
          forge exit status 0, and a stray broken one can sink a correct solution.
        - `-P` and `--import-mode=importlib` keep the workdir off sys.path, and
          the pinned plugin appends it again *behind* the standard library. A file
          the agent added cannot then shadow a stdlib module the grading tests
          measure against, while the task's own modules stay importable.
        - the report is checked rather than the exit status alone, because agent
          code runs during collection and one os._exit(0) there is otherwise
          indistinguishable from a clean pass. This catches an accidental early
          exit and a corrupted run, not an adversary: the report is written by
          the same process tree, so code that means to can rewrite it.
        """
        config = root / "grading-pytest.ini"
        config.write_text(_GRADING_CONFIG, encoding="utf-8")
        harness = root / "harness"
        harness.mkdir()
        (harness / f"{_PATH_PLUGIN_NAME}.py").write_text(
            _PATH_PLUGIN.format(workdir=str(workdir)), encoding="utf-8"
        )
        report = root / "report.xml"
        inherited = os.environ.get("PYTHONPATH")
        try:
            process = subprocess.run(
                [sys.executable, "-P", "-m", "pytest", "-q",
                 "-c", str(config), "--noconftest", "--rootdir", str(workdir),
                 "--import-mode=importlib", f"--junitxml={report}",
                 "-p", _PATH_PLUGIN_NAME, "-p", "no:cacheprovider", *targets],
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=timeout_s,
                check=False,
                env=os.environ
                | {
                    "PYTHONPATH": os.pathsep.join(
                        [str(harness), *([inherited] if inherited else [])]
                    )
                },
            )
        except subprocess.TimeoutExpired:
            return False
        except OSError as error:
            raise IngestError(f"cannot run pytest: {error}") from error
        return process.returncode == 0 and _report_shows_every_test_passed(report)

    def starting_repository_problem(self, repo_dir: Path) -> str | None:
        collisions = _stdlib_collisions(repo_dir)
        if not collisions:
            return None
        return (
            f"{repo_dir.name}/ names {collisions} after standard-library "
            "module(s) — grading keeps the standard library ahead of the workdir "
            "on sys.path, so these are invisible at grade time and the task can "
            "lint clean while being impossible to solve"
        )

    def loads(self, source: str) -> bool:
        try:
            ast.parse(source)
        except SyntaxError:
            return False
        return True

    def defined_symbols(self, source: str) -> set[str]:
        """Every symbol a module defines: its functions and classes, both
        qualified by nesting and bare, and its module-level assignment targets.

        A method is accepted either way: `Class.method`, which is how an author
        writes down the two levels a defect in one is legitimately described at —
        the method, and the class enclosing it — and the bare `method`, which is
        how a locating agent actually phrases an answer about something nested.
        Only nested definitions get the bare form; a module-level definition has
        no qualified form to be an alternative to.

        An assignment counts only at module level, and that is the ruling's own
        boundary: a fault can live in a constant, a dispatch table or a compiled
        pattern, and a key that saw only `def` and `class` could not name one. An
        assignment inside a class body or a function is not keyable, because it is
        a state change inside something already keyable, and accepting it would
        key a location at a level no author wrote down.
        """
        symbols: set[str] = set()
        definitions = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

        def bind(target: ast.expr) -> None:
            if isinstance(target, ast.Name):
                symbols.add(target.id)
            elif isinstance(target, ast.Starred):
                bind(target.value)
            elif isinstance(target, ast.Tuple | ast.List):
                for element in target.elts:
                    bind(element)

        def walk(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, definitions):
                    symbols.add(prefix + child.name)
                    if prefix:
                        symbols.add(child.name)
                    walk(child, f"{prefix}{child.name}.")
                else:
                    if not prefix:
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                bind(target)
                        elif isinstance(child, ast.AnnAssign):
                            bind(child.target)
                    # Anything else keeps the prefix: a definition guarded by an
                    # `if` or a `try` at module level is still defined there, and
                    # so is an assignment.
                    walk(child, prefix)

        walk(_parse(source), "")
        return symbols

    def defined_classes(self, source: str) -> set[str]:
        """The classes a module defines at its own top level — the level an
        accepted answer naming a class is answering at.

        A companion reading to `defined_symbols` rather than a rival to it:
        that method deliberately flattens `def`, `class` and module-level
        assignment into one namespace, because a key may legitimately name any of
        them, and that flattening is exactly what this rule cannot use — "more
        than one class" is a question about classes and not about symbols. It
        descends through an `if` or a `try` for the same reason `defined_symbols`
        does, and into neither a class body nor a function body: a class nested
        inside either is not a level a filename names.
        """
        classes: set[str] = set()

        def walk(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    classes.add(child.name)
                elif not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    walk(child)

        walk(_parse(source))
        return classes


def _parse(source: str) -> ast.Module:
    """The module tree, or `SourceUnreadable` carrying the toolchain's own
    message — the one place the Python runner turns "does not load" into the
    seam's language-agnostic signal."""
    try:
        return ast.parse(source)
    except SyntaxError as error:
        raise SourceUnreadable(str(error)) from error


def _report_shows_every_test_passed(report: Path) -> bool:
    """Evidence from outside the workdir that the tests really ran.

    pytest writes the report when the session ends, so a run that killed the
    process part-way leaves none — and a run that finished but skipped
    everything leaves one that says so. Evidence, not proof: the report is
    written by the graded process itself, so it is only as trustworthy as
    that process (see PythonRunner.run_tests).
    """
    try:
        suites = list(ElementTree.parse(report).getroot().iter("testsuite"))
    except (OSError, ElementTree.ParseError):
        return False
    counts = {
        field: sum(int(suite.get(field, "0")) for suite in suites)
        for field in ("tests", "failures", "errors", "skipped")
    }
    return counts["tests"] > 0 and not any(
        counts[field] for field in ("failures", "errors", "skipped")
    )


def _stdlib_collisions(repo_dir: Path) -> list[str]:
    """Top-level names in the starting repository the standard library owns.

    Only the top level matters: that is what grading puts on sys.path, and a
    module deeper in a package is reached through its package name.
    """
    collisions = []
    for entry in sorted(repo_dir.iterdir()):
        if entry.is_dir():
            importable = entry.name
        elif entry.suffix == ".py":
            importable = entry.stem
        else:
            continue
        if importable in sys.stdlib_module_names:
            collisions.append(entry.name)
    return collisions


# --- the typescript runner -----------------------------------------------------

# The first Node that strips TypeScript types with no flag (22.18). Below it a
# `.ts` grading test does not even parse, so every task would score 0.0 and read
# as a very bad model rather than a toolchain that cannot grade.
NODE_TYPE_STRIPPING_FLOOR = (22, 18)

# Written beside the workdir and loaded with `--import`, so a logged diff — which
# can only write inside the workdir — cannot reach it.
#
# What it closes, probed on Node v22.22.2 on 2026-08-19: a `process.exit(0)` in
# the module under test, at import or inside a function a test calls mid-run,
# ends `node --test` with **exit status 0** and a report holding exactly one
# *passing* `testcase` named after the test file, every real test gone. Without
# this that is indistinguishable from a clean pass.
#
# Both properties, because each closes a path the other leaves open: replacing
# only `process.exit` leaves the mid-run exit refused and the import-time one
# still forging a pass, and replacing only `reallyExit` the other way about
# (probed by removing each in turn).
_PRELOAD_NAME = "grading-preload.mjs"
_PRELOAD = """\
const refuse = (name) => () => {
  throw new Error(
    `grading: ${name}() is disabled while the held-out tests run`
  );
};

process.exit = refuse("process.exit");
process.reallyExit = refuse("process.reallyExit");
"""

# Written *into* the workdir, last, for the same reason the grading overlay is:
# Node reads the module system off the nearest package.json, so an agent-written
# `{"type": "commonjs"}` makes every held-out `.test.ts` a syntax error and sinks
# a correct solution (probed, same date). A stdlib-only TypeScript task installs
# nothing, so a package.json carries nothing but that declaration — which is the
# runner's to pin, not the agent's.
_PACKAGE_JSON = "package.json"
_CANONICAL_PACKAGE_JSON = '{"type": "module"}\n'

# Node reads its own options out of the environment, so a `NODE_OPTIONS` on the
# operator's machine would join the invocation the runner pinned. Scrubbed by
# prefix rather than by list: `NODE_OPTIONS` and `NODE_PATH` are the two that
# matter today, and a verdict must not start varying with the machine the day
# Node adds a third.
_NODE_ENVIRONMENT_PREFIX = "NODE_"

_NODE = "node"

# `node --version` prints and exits; a machine where it does not is broken in a
# way the toolchain check should say out loud rather than hang on.
_VERSION_TIMEOUT_S = 30


class TypeScriptRunner(LanguageRunner):
    """TypeScript's instance: `node --test` with the JUnit reporter, nothing
    installed, and a preload that makes an exit throw."""

    language = "typescript"
    grading_test_glob = "*.test.ts"
    visible_test_glob = "*.test.ts"
    source_glob = "*.ts"

    def require_toolchain(self) -> None:
        """Grading shells out to `node --test`; a Node that is missing, or too
        old to strip types, would score every task 0.0 and look like a very bad
        model rather than a broken environment."""
        node = shutil.which(_NODE)
        if node is None:
            raise IngestError(
                f"{_NODE} is not on PATH — v1 grading runs a typescript task's "
                "held-out tests with `node --test` and cannot grade without it"
            )
        try:
            reported = subprocess.run(
                [node, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=_VERSION_TIMEOUT_S,
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as error:
            raise IngestError(f"cannot run `{_NODE} --version`: {error}") from error
        version = _node_version(reported)
        floor = ".".join(str(part) for part in NODE_TYPE_STRIPPING_FLOOR)
        if version is None:
            raise IngestError(
                f"`{_NODE} --version` printed {reported!r}, which is not a version "
                f"this grader can read — v1 grading needs Node {floor} or newer, "
                "which is the first that strips TypeScript types with no flag"
            )
        if version < NODE_TYPE_STRIPPING_FLOOR:
            raise IngestError(
                f"{_NODE} {reported} is below v{floor} — v1 grading runs a "
                "typescript task's held-out `.ts` tests with `node --test` and "
                f"nothing installed, and Node {floor} is the first that strips "
                "TypeScript types with no flag, so an older one cannot grade at all"
            )

    def run_tests(
        self, root: Path, workdir: Path, targets: Sequence[str], *, timeout_s: int
    ) -> bool:
        """Run the named tests in workdir. True only if they all actually passed.

        The same rule the Python runner is built on — the verdict depends on the
        held-out tests and on nothing the agent wrote around them — spelled in
        Node's terms:

        - the held-out files are **named explicitly**, so `node --test` runs no
          discovery and a test the agent wrote is never collected;
        - the JUnit report is written **outside the workdir**, and the verdict is
          read from it rather than from the exit status alone, because agent code
          runs at import and one `process.exit(0)` there is otherwise a clean
          pass;
        - the preload that makes that exit throw is `--import`ed from **outside
          the workdir** too, so a logged diff cannot reach it;
        - the environment's `NODE_*` variables are dropped, so a `NODE_OPTIONS`
          on the operator's machine cannot join the invocation;
        - a canonical `package.json` is written into the workdir last, pinning
          the module system an agent-written one would otherwise decide.

        The same accepted limitation as Python's: the report is written by the
        process tree being graded, so this catches an accidental early exit and a
        corrupted run, not an adversary.
        """
        preload = root / _PRELOAD_NAME
        preload.write_text(_PRELOAD, encoding="utf-8")
        report = root / "node-report.xml"
        (workdir / _PACKAGE_JSON).write_text(_CANONICAL_PACKAGE_JSON, encoding="utf-8")
        argv = [
            _NODE,
            "--import",
            preload.as_uri(),
            "--test",
            "--test-reporter=junit",
            f"--test-reporter-destination={report}",
            *targets,
        ]
        environment = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith(_NODE_ENVIRONMENT_PREFIX)
        }
        try:
            # `node --test` runs each test file in a child process of its own, so
            # a synchronous loop in agent code survives killing the parent alone.
            # Its own session, killed as a group, is what makes the timeout a
            # verdict rather than a runaway.
            process = subprocess.Popen(
                argv,
                cwd=workdir,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except OSError as error:
            raise IngestError(f"cannot run `{_NODE} --test`: {error}") from error
        with process:
            try:
                process.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                _kill_session(process)
                process.communicate()
                return False
        return process.returncode == 0 and _every_named_testcase_passed(report, targets)

    def starting_repository_problem(self, repo_dir: Path) -> str | None:
        """None, always, and that is a finding rather than a stub.

        Python's rule exists because grading puts the workdir on `sys.path`, so a
        `queue.py` in the starting repository silently becomes the module a
        grading test imports. Node has no such collision to have: a builtin is
        reached through a bare specifier (`node:assert`, `assert`), a repository
        module through a relative one (`./assert.ts`), and the two namespaces
        never meet — a file cannot shadow a builtin however it is named. The
        stdlib-only rule TypeScript *does* owe — that grading installs nothing —
        is about dependencies rather than names, so it is not this invariant's
        to state: it is refused on the author by the task-set lint, which is
        where a rule about what a task *ships* belongs (ADR-0003, and
        `_typescript_problems` in `ai_benchmark.firstparty_v1`).
        """
        return None

    def loads(self, source: str) -> bool:
        """Whether the declaration scan can read this file at all.

        A narrower question than the one `typescript_load_problems` asks, and
        deliberately: that probe *imports* a checked-in file under the Node that
        grades it, which is the lint's rule about what a task ships, and it is
        run over every `.ts` file of every tree already. This is the reading
        instrument's own "can I see the declarations", so what it answers False
        to is a file the scan cannot get through — an unterminated string,
        comment or template, or braces that do not balance — and nothing else. A
        file that scans clean and then throws on import is caught where import
        errors are caught, and is not this method's to report twice.
        """
        try:
            _typescript_declarations(source)
        except SourceUnreadable:
            return False
        return True

    def defined_symbols(self, source: str) -> set[str]:
        """Every symbol this module defines: its classes, its functions, its
        class and object-literal members that are behaviour, and its top-level
        bindings — each qualified by the scopes enclosing it and, where there
        are any, bare as well.

        `PythonRunner.defined_symbols`' ruling in Node's terms, clause by
        clause, because what an accepted answer may legitimately name is a
        question about description levels rather than about a language. A method
        is accepted both as `Class.method`, the two levels an author writes a
        defect in one down at, and as the bare `method` a locating agent
        actually phrases an answer with; only a nested definition gets the bare
        form, a top-level one having no qualified form to be an alternative to.

        A binding counts at the module's own top level and nowhere else, which
        is the same boundary and drawn for the same reason: a fault can live in
        a `const` holding a rate, a dispatch table or a compiled pattern, and a
        key that saw only `class` and `function` could not name one — while a
        binding inside a function body is a state change inside something
        already keyable.

        Where the two languages differ is what "a member" is, because Node's
        class bodies hold two spellings of one thing: `total() {}` and
        `total = () => {}` are both behaviour attached to the class, and the
        second is idiomatic TypeScript rather than an exception. Both are
        accepted; a field holding a *value* — `readonly limit = 10` — is not, by
        exactly the rule that keeps a Python class-body assignment out.

        What is deliberately *not* a symbol is a type: an `interface`, a `type`
        alias or the type half of a declaration is erased before anything runs
        (type stripping is how a `.ts` file is executed at all here), so no
        defect can live in one and no answer can be graded against it.

        Raises `SourceUnreadable` where `loads` is False.
        """
        return _typescript_declarations(source)[0]

    def defined_classes(self, source: str) -> set[str]:
        """The classes this module declares at its own top level.

        `PythonRunner.defined_classes`' companion reading, at the level an
        accepted answer naming a class is answering at: through an `if` or a
        `try`, which do not change what level a declaration is at, and into
        neither a class body nor a function body nor an object literal, none of
        which is a level a filename names.

        Raises `SourceUnreadable` where `loads` is False.
        """
        return _typescript_declarations(source)[1]


# --- the typescript declaration scan -------------------------------------------
#
# How the TypeScript runner answers responsibility 6. Python's instrument is
# `ast`, which is a parser for the toolchain that grades it; TypeScript's
# toolchain is Node, whose parser is not reachable from this process without
# running a subprocess — and the lint would then pay for one per accepted answer,
# per synthesised near-miss and per file of terrain. So the answer here is a
# **declaration scan**: comments and literals blanked, then the declaration
# keywords read off what is left, with a stack of the scopes their braces open.
#
# What that costs, said once and in one place: a scan reads what an author wrote
# down and not what a module exports once it has run, so a binding a loop
# assembles is not seen. That is outside what a keyed task can be — a key names a
# location in a file the agent was handed, and an author writes that location
# down — while a *missed ordinary declaration* would be a key the lint refuses
# for a reason that says nothing about the key, which is what the suite around
# this holds it to.
#
# Two conventions the scan reads by, rather than a parser's precision:
#
# - a class member and a top-level binding are read at the **start of a line**,
#   which is where authored code puts a declaration and where a call or a nested
#   expression that happens to look like one is not;
# - what a `{` opens is read from the character before it — an `=` or an `=>`
#   opens an initializer, a `(` or a `,` an object literal, anything else a
#   block — which is how the same brace is told apart from itself.

_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"

# What may stand between the start of a line and a class member's own name. `get`
# and `set` are in the list and are still readable as a member named `get`,
# because a modifier is only consumed where whitespace follows it: `get(key) {`
# has none and is a method by that name.
_MEMBER_MODIFIER = (
    r"(?:static|public|private|protected|readonly|abstract|override|declare"
    r"|async|get|set)"
)

# A member's initializer, where the member is behaviour rather than state: a
# `function` expression, or an arrow whose parameter list may carry types and
# whose return type may follow it. A member bound to anything else is a field
# holding a value, and is no more keyable than a Python class-body assignment.
_FUNCTION_VALUED = (
    rf"(?:async[ \t]+)?(?:function\b|\([^()]*\)[ \t]*(?::[^=;\n]*)?=>"
    rf"|{_IDENTIFIER}[ \t]*=>)"
)

_TOKEN = re.compile(
    rf"""
      (?P<member>^[ \t]*(?:{_MEMBER_MODIFIER}[ \t]+)*\*?[ \t]*
        (?P<member_name>\#?{_IDENTIFIER})[ \t]*[?!]?[ \t]*
        (?:<[^<>()]*>[ \t]*)?  # the type parameters a generic method carries
        (?:\(|(?::[^=;\n]*)?=[ \t]*{_FUNCTION_VALUED}|:[ \t]*{_FUNCTION_VALUED}))
    | \b(?P<class>class)\b(?:[ \t]+(?P<class_name>{_IDENTIFIER}))?
    | \b(?P<function>function)\b[ \t]*\*?[ \t]*(?P<function_name>{_IDENTIFIER})?
    | (?P<binding>(?:export[ \t]+)?(?:declare[ \t]+)?\b(?:const|let|var)[ \t]+
        (?P<binding_name>{_IDENTIFIER}))
    | (?P<open>\{{)
    | (?P<close>\}})
    | (?P<end>;)
    """,
    re.VERBOSE | re.MULTILINE,
)

# The scope kinds the stack holds. `class` and `object` are the two a member
# declaration is read inside — a class body and an object literal are the two
# places Node lets one be written — and `function` and `block` are the two it is
# not. `block` is the only one that does not change what level a declaration is
# at, which is what `_module_level` reads.
_CLASS, _OBJECT, _FUNCTION, _BLOCK = "class", "object", "function", "block"

# What a `{` follows when it opens an object literal rather than a block.
_OBJECT_FOLLOWS = set("=(,:[?")

# What a `/` follows when it opens a regular expression rather than dividing.
# Read from the character before it, which is the whole of what a blanking pass
# has — and enough, because the alternative to a regex here is division, whose
# left-hand side is always a value.
_REGEX_FOLLOWS = set("(,=:[!&|?{};+-*%^~<>")
_REGEX_FOLLOWS_WORD = frozenset(
    "return typeof case in of new delete void throw yield await do else".split()
)


def _typescript_declarations(source: str) -> tuple[set[str], set[str]]:
    """Every symbol this file defines, and the classes it defines at its own top
    level — the two readings `defined_symbols` and `defined_classes` return.

    One pass for both, because they are one walk over one scope stack read at
    two levels of forgiveness, and two passes would be two places for the
    scoping to drift.
    """
    text = _blanked(source)
    symbols: set[str] = set()
    classes: set[str] = set()
    stack: list[tuple[str, str | None]] = []
    pending: tuple[str, str | None] | None = None
    binding: str | None = None

    def record(name: str) -> None:
        """This declaration, qualified by the scopes enclosing it — and bare as
        well where there are any, which is the `Class.method` / `method` pair
        `PythonRunner.defined_symbols` accepts both of."""
        prefix = ".".join(name for _, name in stack if name)
        symbols.add(f"{prefix}.{name}" if prefix else name)
        if prefix:
            symbols.add(name)

    for match in _TOKEN.finditer(text):
        if match.group("member") is not None:
            if stack and stack[-1][0] in (_CLASS, _OBJECT):
                member = match.group("member_name")
                record(member)
                pending = (_FUNCTION, member)
            continue
        if match.group("class") is not None:
            name = match.group("class_name")
            if name is not None:
                record(name)
                if _module_level(stack):
                    classes.add(name)
            pending = (_CLASS, name if name is not None else binding)
            continue
        if match.group("function") is not None:
            name = match.group("function_name")
            if name is not None:
                record(name)
            pending = (_FUNCTION, name if name is not None else binding)
            continue
        if match.group("binding") is not None:
            binding = match.group("binding_name")
            if _module_level(stack) and _starts_a_statement(text, match.start()):
                symbols.add(binding)
            continue
        if match.group("open") is not None:
            stack.append(_opened_by(text, match.start(), pending, binding))
            pending = None
            continue
        if match.group("close") is not None:
            if not stack:
                raise SourceUnreadable(
                    "a '}' closes a scope that was never opened"
                )
            stack.pop()
        pending, binding = None, None  # a '}' or a ';' ends the declaration
    if stack:
        raise SourceUnreadable(f"{len(stack)} '{{' is never closed")
    return symbols, classes


def _module_level(stack: list[tuple[str, str | None]]) -> bool:
    """Whether a declaration under these scopes is at the module's own top
    level. An `if` or a `try` does not change the level a declaration is at, for
    the reason `PythonRunner.defined_classes` descends through both; a class
    body, a function body and an object literal all do."""
    return all(kind == _BLOCK for kind, _ in stack)


def _starts_a_statement(text: str, index: int) -> bool:
    """Whether this declaration begins a statement rather than sitting inside
    something — a `const` in `for (const shift of rota)` binds a loop variable
    and not a module-level name, and a key naming one would be naming a symbol
    that exists only while the loop runs.

    A statement is one the previous one has ended: at a `;` or a brace, or at a
    line break, which is how a file written without semicolons ends one.
    """
    before = text[:index]
    settled = before.rstrip()
    if "\n" in before[len(settled) :]:
        return True
    return not settled or settled[-1] in ";{}"


def _opened_by(
    text: str, index: int, pending: tuple[str, str | None] | None, binding: str | None
) -> tuple[str, str | None]:
    """What this `{` opens, read from the declaration in front of it and the
    character behind it.

    The name a scope carries is what qualifies the declarations inside it, so an
    arrow assigned to a binding carries that binding's name: `const rota = {`
    and `const shifts = () => {` are how Node spells "a thing with things
    inside it", and a defect inside either is legitimately described as
    `rota.add` as much as `add`.
    """
    if pending is not None:
        # The declaration this brace belongs to, however much stands between
        # them: a return type, a parameter list, an `implements` clause. Nothing
        # else can be pending, because a `;` and a `}` both clear it.
        return pending
    before = text[:index].rstrip()
    if before.endswith("=>"):
        return _FUNCTION, binding
    if before.endswith("="):
        return _OBJECT, binding
    if before and before[-1] in _OBJECT_FOLLOWS or re.search(r"\breturn$", before):
        return _OBJECT, None
    return _BLOCK, None


def _blanked(source: str) -> str:
    """`source` with every comment and every literal replaced by blanks of the
    same length, newlines kept.

    What the scan reads is the file's declarations, and a brace inside a string,
    a `class` inside a comment and a `}` inside a template's interpolation are
    none of them declarations. Blanking rather than deleting keeps every offset,
    so the line a member is read at is still the line the author wrote it on.

    Raises `SourceUnreadable` where a comment or a literal is never closed:
    together with a brace that never closes, that is the whole of what this
    instrument means by "does not parse" (see `TypeScriptRunner.loads`).
    """
    out = list(source)
    length = len(source)
    index = 0
    previous = ""  # the last significant character read
    word = ""  # the identifier being read, and the one before it
    before = ""

    def blank(start: int, stop: int) -> None:
        for position in range(start, stop):
            if out[position] != "\n":
                out[position] = " "

    while index < length:
        char = source[index]
        pair = source[index : index + 2]
        if pair == "//":
            stop = source.find("\n", index)
            blank(index, length if stop < 0 else stop)
            index = length if stop < 0 else stop
            continue
        if pair == "/*":
            stop = source.find("*/", index + 2)
            if stop < 0:
                raise SourceUnreadable("a '/*' comment is never closed")
            blank(index, stop + 2)
            index = stop + 2
            continue
        if char in "\"'":
            stop = _end_of_quoted(source, index)
            blank(index + 1, stop)
            index, previous, before, word = stop + 1, char, word or before, ""
            continue
        if char == "`":
            stop = _end_of_template(source, index)
            blank(index + 1, stop)
            index, previous, before, word = stop + 1, char, word or before, ""
            continue
        if char == "/" and _opens_a_regex(previous, word or before):
            closing = _end_of_regex(source, index)
            if closing is not None:
                blank(index + 1, closing)
                index, previous, before, word = closing + 1, "/", word or before, ""
                continue
        if char.isalnum() or char in "_$":
            word += char
        else:
            before, word = word or before, ""
        if not char.isspace():
            previous = char
        index += 1
    return "".join(out)


def _opens_a_regex(previous: str, word: str) -> bool:
    """Whether the `/` after this much source opens a regular expression.

    Division's left-hand side is a value — an identifier, a number, a closing
    bracket — so a `/` following anything else, or following one of the keywords
    a value may come after, is opening a pattern instead. The two have to be told
    apart because a pattern is a literal and may hold braces and quotes that are
    not code.
    """
    if not previous:
        return True
    if previous.isalnum() or previous in "_$":
        return word in _REGEX_FOLLOWS_WORD
    return previous in _REGEX_FOLLOWS


def _end_of_quoted(source: str, start: int) -> int:
    """The index of the quote that closes the one at `start`."""
    quote = source[start]
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == quote:
            return index
        if char == "\n":
            break
        index += 1
    raise SourceUnreadable(f"a {quote} string is never closed")


def _end_of_template(source: str, start: int) -> int:
    """The index of the backtick that closes the template starting at `start`,
    interpolations and the literals nested inside them included."""
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == "`":
            return index
        if source[index : index + 2] == "${":
            index = _end_of_interpolation(source, index + 2) + 1
            continue
        index += 1
    raise SourceUnreadable("a template literal is never closed")


def _end_of_interpolation(source: str, start: int) -> int:
    """The index of the `}` that closes a `${` interpolation, which may hold
    braces, strings and templates of its own."""
    index = start
    depth = 0
    while index < len(source):
        char = source[index]
        if char in "\"'":
            index = _end_of_quoted(source, index) + 1
            continue
        if char == "`":
            index = _end_of_template(source, index) + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                return index
            depth -= 1
        index += 1
    raise SourceUnreadable("a '${' interpolation is never closed")


def _end_of_regex(source: str, start: int) -> int | None:
    """The index of the `/` that closes the pattern starting at `start`, or None
    where the line ends first — which means this `/` was dividing after all."""
    index = start + 1
    inside_class = False
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == "\n":
            return None
        if char == "[":
            inside_class = True
        elif char == "]":
            inside_class = False
        elif char == "/" and not inside_class:
            return index
        index += 1
    return None


def _node_version(reported: str) -> tuple[int, int] | None:
    """(major, minor) out of what `node --version` prints, or None where that is
    not something this grader can compare against the floor."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)(?:\..*)?", reported)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _kill_session(process: "subprocess.Popen[str]") -> None:
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):  # already gone
        process.kill()


def _every_named_testcase_passed(report: Path, targets: Sequence[str]) -> bool:
    """The TypeScript verdict, read per `testcase`.

    Not `_report_shows_every_test_passed`'s reading, and deliberately: probed on
    Node v22.22.2 on 2026-08-19, `node --test`'s JUnit reporter emits a top-level
    test as a bare `<testcase>` child of `<testsuites>` and only a `describe`
    block as a `<testsuite>` element with count attributes — so summing those
    attributes reads a file of top-level tests as zero tests. Every `testcase` is
    read wherever it sits, and must carry no failure, error or skipped mark,
    written by Node either as an attribute or as a child element.

    The third clause is Node's own forgery class: a held-out file that registered
    no tests, or exited before they ran, is reported as a single *passing*
    `testcase` named after the file. A verdict cannot be a placeholder, so one
    named after a file this run was asked to grade is refused.
    """
    try:
        cases = list(ElementTree.parse(report).getroot().iter("testcase"))
    except (OSError, ElementTree.ParseError):
        return False
    if not cases:
        return False
    placeholders = {target for target in targets} | {
        PurePosixPath(target).name for target in targets
    }  # named as given on the command line, or by its bare file name
    for case in cases:
        if case.get("name") in placeholders:
            return False
        for mark in ("failure", "error", "skipped"):
            if case.get(mark) is not None or case.find(mark) is not None:
                return False
    return True


# --- the lint's node-side probe ------------------------------------------------
#
# Deliberately not a seventh runner responsibility: nothing here runs a test or
# reads a verdict, and what it answers — "does this file the author checked in
# load at all" — is the task-set lint's question rather than grading's. It lives
# beside the TypeScript runner because everything it knows is Node's: the
# binary, the environment scrub, the module system a workdir is pinned to. A
# second copy of that in the lint would be a second place for it to drift.

# Run as the entry point from *outside* the throwaway copy, so that a module
# comparing `process.argv[1]` against its own URL — the Node 22 idiom for "am I
# the CLI entry point", there being no `import.meta.main` — sees this file and
# not itself, and its main() does not run. It writes one verdict line to stdout
# and exits, rather than letting its exit status say it: importing a held-out
# test registers that file's tests, and their outcome is not what is being
# asked here.
_PROBE_NAME = "grading-probe.mjs"
_PROBE = """\
import fs from "node:fs";

// Captured before the import, because the module being loaded may replace it.
const exit = process.exit.bind(process);

const say = (verdict, detail) => {
  fs.writeSync(1, `${verdict} ${JSON.stringify(String(detail))}\\n`);
  exit(0);
};

try {
  await import(process.argv[2]);
} catch (error) {
  const message = (error && error.message) || String(error);
  const dependency =
    (error && error.code === "ERR_MODULE_NOT_FOUND") ||
    /does not provide an export named/.test(message);
  say(dependency ? "unresolved" : "failed", message);
}
say("loaded", "");
"""

# The probe's three verdicts: it loaded; it did not, over something outside the
# file (see `typescript_load_problems`); it did not, over the file itself.
_LOADED = "loaded"
_UNRESOLVED = "unresolved"
_FAILED = "failed"

# One import of one small module. Generous enough that a slow machine is never
# the reason a task fails to lint, short enough that a module looping at import
# is reported rather than hanging the lint.
_LOAD_TIMEOUT_S = 60


def typescript_load_problems(directory: Path) -> dict[str, str]:
    """Every `.ts` file under `directory` that does not load under the Node
    that grades a TypeScript task, by path relative to it, with the reason.

    A **real import**, in a throwaway subprocess whose cwd is a throwaway copy,
    and not `node --check`, because the two are not the same question: probed
    on v22.22.2 on 2026-08-19, `node --check` exits 0 on a file holding
    `export enum E { A }` and the refusal — "TypeScript enum is not supported
    in strip-only mode" — appears only on a real load. The copy is thrown away
    because a real import runs the file's top-level code, which may write; the
    environment is scrubbed of `NODE_*` for the reason `run_tests` scrubs it,
    so what this reports cannot vary with the operator's machine.

    What is *not* reported is a specifier that does not resolve, or a name the
    module it names does not export. A held-out test is written against the
    solved repository, so against the pristine one it legitimately imports a
    function nobody has written yet — that is the task, not a defect in the
    file. Both are read off Node's own error (`ERR_MODULE_NOT_FOUND`, and the
    link-time "does not provide an export named") and passed over. Everything
    else — syntax that type stripping refuses, a throw at import, a module that
    ends the process while it is being loaded — is this file's own problem and
    is reported in Node's words.
    """
    files = sorted(directory.rglob(TYPESCRIPT.source_glob))
    if not files:
        return {}
    # Loudly, once, before any file is judged: a missing or too-old Node would
    # otherwise report every checked-in `.ts` file as unloadable, which is a
    # fact about the machine and not about the corpus.
    TYPESCRIPT.require_toolchain()
    problems: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        probe = root / _PROBE_NAME
        probe.write_text(_PROBE, encoding="utf-8")
        copy = root / directory.name
        shutil.copytree(directory, copy)
        # The same declaration `run_tests` pins into the workdir, and pinned
        # here for the same reason: Node reads the module system off the
        # nearest package.json, and a `.ts` file's imports are only ESM under
        # this one. The lint refuses a task-shipped package.json separately.
        (copy / _PACKAGE_JSON).write_text(_CANONICAL_PACKAGE_JSON, encoding="utf-8")
        for path in files:
            relative = path.relative_to(directory)
            if problem := _load_problem(probe, copy, relative):
                problems[str(relative)] = problem
    return problems


def _load_problem(probe: Path, copy: Path, relative: Path) -> str | None:
    """Why this one file does not load, or None where it does."""
    argv = [_NODE, str(probe), (copy / relative).as_uri()]
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(_NODE_ENVIRONMENT_PREFIX)
    }
    try:
        process = subprocess.Popen(
            argv,
            cwd=copy,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as error:
        raise IngestError(f"cannot run `{_NODE}`: {error}") from error
    with process:
        try:
            stdout, stderr = process.communicate(timeout=_LOAD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            _kill_session(process)
            process.communicate()
            return (
                f"it was still being imported {_LOAD_TIMEOUT_S}s later — a module "
                "does its work when it is called and not when it is loaded"
            )
    verdict, _, payload = stdout.partition("\n")[0].partition(" ")
    try:
        detail = str(json.loads(payload))
    except json.JSONDecodeError:  # not the probe's line: it said nothing at all
        verdict, detail = "", ""
    if verdict in (_LOADED, _UNRESOLVED):
        return None
    if verdict == _FAILED:
        return detail
    return (
        f"the import ended the process (exit status {process.returncode}) before "
        f"it could say whether the file loaded: {stderr.strip() or '(no output)'}"
    )


# --- the registry --------------------------------------------------------------

PYTHON = PythonRunner()
TYPESCRIPT = TypeScriptRunner()

# The registry, keyed on a task's declared `language` and on nothing an operator
# can pass. A third language is a third entry here and no edit to the grader.
# See the module docstring for what an entry owes.
RUNNERS: dict[str, LanguageRunner] = {
    runner.language: runner for runner in (PYTHON, TYPESCRIPT)
}

def runner_for(language: str) -> LanguageRunner:
    """The runner that grades a task declaring this language.

    The only way into `RUNNERS`. Callers pass the task's own declaration and
    never an operator's choice, so a task cannot be graded by the wrong
    mechanism — and there is no reading for a task that declares nothing,
    because a first-party v1 task must declare a language (`Task.language`):
    what runs a task's tests is never implicit.
    """
    runner = RUNNERS.get(language)
    if runner is None:
        raise IngestError(
            f"no language runner is registered for {language!r} — v1 grading "
            f"runs a task's tests with its language's own toolchain, and the "
            f"registered language(s) are {sorted(RUNNERS)}"
        )
    return runner
