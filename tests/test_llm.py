"""build_prompt is pure: the instance evidence must actually land in the prompt."""

from ai_benchmark.instances import InstanceContext
from ai_benchmark.llm import _PROBLEM_STATEMENT_LIMIT, build_prompt


def test_prompt_includes_problem_statement_and_patch_files() -> None:
    context = InstanceContext(
        problem_statement="UsernameValidator allows trailing newline",
        patch_files=["django/core/validators.py", "tests/validators/tests.py"],
    )

    prompt = build_prompt("swe-bench-verified", "django__django-11099", context)

    assert "UsernameValidator allows trailing newline" in prompt
    assert "- django/core/validators.py" in prompt
    assert "- tests/validators/tests.py" in prompt
    assert "Benchmark: swe-bench-verified" in prompt
    assert "Instance id: django__django-11099" in prompt


def test_prompt_without_context_is_the_bare_prompt() -> None:
    prompt = build_prompt("polyglot-bench", "rust__fix-1", None)

    assert "Problem statement" not in prompt
    assert "Files changed" not in prompt
    assert "{context}" not in prompt  # the placeholder collapses cleanly
    assert "Instance id: rust__fix-1" in prompt


def test_prompt_with_patch_files_only_omits_statement_section() -> None:
    context = InstanceContext(problem_statement=None, patch_files=["x.py"])

    prompt = build_prompt("swe-bench-verified", "x__x-1", context)

    assert "Problem statement" not in prompt
    assert "- x.py" in prompt


def test_overlong_problem_statement_is_truncated_with_a_marker() -> None:
    context = InstanceContext(
        problem_statement="a" * (_PROBLEM_STATEMENT_LIMIT + 100), patch_files=None
    )

    prompt = build_prompt("swe-bench-verified", "x__x-1", context)

    assert "a" * _PROBLEM_STATEMENT_LIMIT + "\n[truncated]" in prompt
    assert "a" * (_PROBLEM_STATEMENT_LIMIT + 1) not in prompt
