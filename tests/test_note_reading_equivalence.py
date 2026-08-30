"""The migration harness for `tests/note_reading.py`.

Proves, byte for byte, that every round suite's local note-reading helpers
read the design note identically to the kit — before ticket 03 onward deletes
a single local copy. Stays after the migration as the standing guard: once no
round suite declares a local copy, this file asserts exactly that.

Headings are harvested mechanically (an `ast` walk), never hand-listed, so a
suite this file has never seen narrows the run by itself as new rounds land
and widens it by itself as migration tickets delete local copies.
"""

import ast
import importlib.util
import inspect
import types
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import note_reading
import pytest

_T = TypeVar("_T")

# How to reproduce a harvested heading's local reading: `("zero", None)` for
# the `_HEADING`-closure style, `("note_section", bare)` /
# `("note_part", bare)` for the argument style.
_Fetch = tuple[str, str | None]

_TESTS_DIR = Path(__file__).parent

_HELPER_NAMES = {
    "note_section",
    "note_part",
    "prose",
    "blocks",
    "fenced_block",
    "fenced_blocks",
    "block_holding",
}

_CANDIDATES = sorted(_TESTS_DIR.glob("test_firstparty_v1_round*.py")) + [
    _TESTS_DIR / "test_firstparty_v1_k10_k4_round3_pairs.py",
    _TESTS_DIR / "test_firstparty_v1_k12_round3_families.py",
]

# Disclosed divergences: a suite whose local helper does not agree with the
# kit for a reason that is not "still a local copy". Empty until a real one
# turns up — see the module docstring on how a suite lands here.
DISCLOSED_DIVERGENCES: dict[str, str] = {}


def _local_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in _HELPER_NAMES
    }


def _string_arg(call: ast.Call) -> str | None:
    if len(call.args) != 1:
        return None
    (arg,) = call.args
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def _harvest_headings(path: Path, local_names: set[str]) -> list[tuple[str, _Fetch]]:
    """Every heading the suite's source actually asks the note for."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    headings: list[tuple[str, _Fetch]] = []
    seen: set[str] = set()

    heading_const = None
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id == "_HEADING"
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            heading_const = stmt.value.value

    if heading_const is not None and "note_section" in local_names:
        headings.append((heading_const, ("zero", None)))
        seen.add(heading_const)

    for call_node in ast.walk(tree):
        if not isinstance(call_node, ast.Call) or not isinstance(call_node.func, ast.Name):
            continue
        if call_node.func.id == "note_section" and "note_section" in local_names:
            bare = _string_arg(call_node)
            if bare is None:
                continue
            full = f"### {bare}"
            if full not in seen:
                headings.append((full, ("note_section", bare)))
                seen.add(full)
        elif call_node.func.id == "note_part" and "note_part" in local_names:
            bare = _string_arg(call_node)
            if bare is None:
                continue
            full = f"## {bare}"
            if full not in seen:
                headings.append((full, ("note_part", bare)))
                seen.add(full)

    return headings


def _import(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(f"_note_reading_check_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call_with_optional_text(fn: Callable[..., _T], text: str) -> _T:
    """Call a local helper that closes over its own section (no parameters)
    or takes the text explicitly, whichever this suite declares."""
    if len(inspect.signature(fn).parameters) == 0:
        return fn()
    return fn(text)


_PARAMS = [
    pytest.param(path, id=path.name)
    for path in _CANDIDATES
    if _local_function_names(path)
]


@pytest.mark.parametrize("path", _PARAMS)
def test_local_note_reading_matches_the_kit(path: Path) -> None:
    if path.name in DISCLOSED_DIVERGENCES:
        pytest.skip(DISCLOSED_DIVERGENCES[path.name])

    local_names = _local_function_names(path)
    module = _import(path)
    headings = _harvest_headings(path, local_names)

    for full_heading, fetch in headings:
        kit_text = note_reading.section(full_heading)

        if fetch[0] == "zero":
            local_text = module.note_section()
        elif fetch[0] == "note_section":
            local_text = module.note_section(fetch[1])
        else:
            local_text = module.note_part(fetch[1])

        assert local_text == kit_text, full_heading

        if "prose" in local_names:
            local_prose = _call_with_optional_text(module.prose, local_text)
            assert local_prose == note_reading.prose(kit_text), full_heading

        kit_fenced = note_reading.fenced_blocks(kit_text)

        if "fenced_blocks" in local_names:
            local_fb = _call_with_optional_text(module.fenced_blocks, local_text)
            assert local_fb == kit_fenced, full_heading

        if "fenced_block" in local_names and kit_fenced:
            # Only meaningful where the section actually holds a block: the
            # singular local reader indexes `[1]` directly and raises on a
            # section that carries none, which just means that heading was
            # never read for a block by the suite that harvested it.
            local_single = module.fenced_block(local_text)
            assert local_single == kit_fenced[0], full_heading

        if "blocks" in local_names:
            local_blocks = _call_with_optional_text(module.blocks, local_text)
            # The documented exception: a local `blocks()` split on ``` alone
            # returns each block with a leading newline the kit's `\n`-anchored
            # split does not carry.
            assert local_blocks == ["\n" + b for b in kit_fenced], full_heading


def test_disclosed_divergences_are_still_divergent() -> None:
    """A stale allowlist entry is itself a lint problem: if the terrain it
    apologised for was fixed, the entry should have been deleted with it."""
    for name in DISCLOSED_DIVERGENCES:
        assert any(path.name == name for path in _CANDIDATES), name


def test_no_new_local_copy_hides_outside_the_scanned_glob() -> None:
    """The standing guard once the migration lands: every
    `test_firstparty_v1_round*.py` file is already in `_CANDIDATES`, so a
    round suite that grows a local copy is caught by this file without an
    edit to it."""
    scanned = {path.name for path in _CANDIDATES}
    for path in sorted(_TESTS_DIR.glob("test_firstparty_v1_round*.py")):
        assert path.name in scanned
