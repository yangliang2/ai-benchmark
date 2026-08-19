"""The language runner seam: the per-language half of execution-verified grading.

A **language runner** is the named answer to "how is a task in this language
graded". It is selected by the task's own declared `language` and by nothing an
operator can pass: a task carries its own grading mechanism, and no flag may
grade a task with the wrong one.

Everything that used to be a pytest fact scattered through the grader lives
here, so that admitting a second language is registering a second entry rather
than editing the grader. `python` is the first instance and, until round 7's
TypeScript ticket, the only one.

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
import subprocess
import sys
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
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


# --- the registry --------------------------------------------------------------

PYTHON = PythonRunner()

# The registry, keyed on a task's declared `language` and on nothing an operator
# can pass. One entry today; a second language is a second entry here and no
# edit to the grader. See the module docstring for what an entry owes.
RUNNERS: dict[str, LanguageRunner] = {PYTHON.language: PYTHON}

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
