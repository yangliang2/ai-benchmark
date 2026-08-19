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
   whether a source file loads under the toolchain (`loads`), plus the glob
   that finds a repository's source files at all (`source_glob`).

**What stays the grader's,** in `ai_benchmark.firstparty_v1`: the throwaway
root with the workdir beneath it, copying `repo/` in, `git init` + `git apply`
of the logged diff, overlaying `grading/` last so an agent's edit at a grading
path is overwritten, the single timeout, `evaluate()` and every record field it
writes. A runner is handed a root and a workdir that are already built; it
never builds one.

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
import os
import re
import shutil
import signal
import subprocess
import sys
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import ClassVar
from xml.etree import ElementTree

from ai_benchmark.dataset import IngestError


class SourceUnreadable(Exception):
    """A source file the runner's toolchain cannot load.

    The language-agnostic spelling of "this file does not parse": the Python
    runner raises it in place of `SyntaxError`, so a caller in the grader
    catches one exception rather than one per language. Its message is the
    toolchain's own, because that is what the lint quotes back to an author.
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
        """Responsibility 6. Whether this source file loads under the
        toolchain that grades it."""

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
        is about dependencies rather than names, and is ticket 03's (#100).
        """
        return None

    def loads(self, source: str) -> bool:
        raise NotImplementedError(_SOURCE_PRIMITIVES_TICKET)

    def defined_symbols(self, source: str) -> set[str]:
        raise NotImplementedError(_SOURCE_PRIMITIVES_TICKET)

    def defined_classes(self, source: str) -> set[str]:
        raise NotImplementedError(_SOURCE_PRIMITIVES_TICKET)


# Responsibility 6 is the lint's half of the seam, not grading's: it is read by
# the terrain rules, the accepted-answer key and the constructed near-miss, none
# of which a verdict passes through. Registering the runner without it lets a
# TypeScript task be *graded* now and *linted* when its ticket lands; raising
# here rather than returning something empty is what keeps that visible, since an
# empty symbol set would read as a key naming a symbol the file does not define.
_SOURCE_PRIMITIVES_TICKET = (
    "the typescript runner's source primitives — loads, defined_symbols and "
    "defined_classes — are ticket 04's (#101), where the lint's instruments "
    "start dispatching on the declared runner"
)


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


# --- the registry --------------------------------------------------------------

PYTHON = PythonRunner()
TYPESCRIPT = TypeScriptRunner()

# The registry, keyed on a task's declared `language` and on nothing an operator
# can pass. A third language is a third entry here and no edit to the grader.
# See the module docstring for what an entry owes.
RUNNERS: dict[str, LanguageRunner] = {
    runner.language: runner for runner in (PYTHON, TYPESCRIPT)
}

# What a task declaring no language is graded by. Provisional: `language` is
# still optional on `Task`, and every checked-in v1 task declares `python`, so
# this is the reading that changes no verdict. Making the declaration required —
# and refusing an unregistered one at load, with a message naming the registered
# runners — is round 7's loader ticket, not this seam's.
_UNDECLARED_LANGUAGE_RUNNER = PYTHON


def runner_for(language: str | None) -> LanguageRunner:
    """The runner that grades a task declaring this language.

    The only way into `RUNNERS`. Callers pass the task's own declaration and
    never an operator's choice, so a task cannot be graded by the wrong
    mechanism.
    """
    if language is None:
        return _UNDECLARED_LANGUAGE_RUNNER
    runner = RUNNERS.get(language)
    if runner is None:
        raise IngestError(
            f"no language runner is registered for {language!r} — v1 grading "
            f"runs a task's tests with its language's own toolchain, and the "
            f"registered language(s) are {sorted(RUNNERS)}"
        )
    return runner
