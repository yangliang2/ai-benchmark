"""Dataset-seam tests: unclassified records + cache in -> classified records + cache out."""

import json
from pathlib import Path

import pytest

from ai_benchmark.classify import Label, classify_records, load_cache, write_cache
from ai_benchmark.dataset import read_records
from ai_benchmark.instances import InstanceContext
from ai_benchmark.schema import TaskCategory


def label(category: TaskCategory) -> Label:
    return Label(category=category, scale="single-file", language="python")


def never_called(
    benchmark: str, instance_id: str, context: InstanceContext | None
) -> Label:
    raise AssertionError("LLM must not be called when the cache is warm")


def test_warm_cache_classifies_without_llm_calls(dataset_fixture: Path) -> None:
    records = read_records(dataset_fixture)
    cache = {
        "polyglot-bench/rust__fix-1": label("feature-dev"),
        "swe-bench-verified/django__django-11099": label("bug-fix"),
        "swe-bench-verified/sympy__sympy-20590": label("bug-fix"),
    }

    classified, cache_after, llm_calls = classify_records(records, cache, never_called)

    by_instance = {r.instance_id: r for r in classified if r.instance_id}
    assert by_instance["django__django-11099"].category == "bug-fix"
    assert by_instance["django__django-11099"].scale == "single-file"
    assert by_instance["rust__fix-1"].category == "feature-dev"
    # Labels fill gaps but never overwrite source-derived facts.
    assert by_instance["rust__fix-1"].language == "rust"
    assert llm_calls == 0
    assert cache_after == cache


def test_cache_miss_asks_llm_once_and_caches_the_answer(dataset_fixture: Path) -> None:
    records = read_records(dataset_fixture)
    asked: list[str] = []

    def stub_llm(
        benchmark: str, instance_id: str, context: InstanceContext | None
    ) -> Label:
        asked.append(f"{benchmark}/{instance_id}")
        return label("bug-fix")

    classified, cache_after, llm_calls = classify_records(records, {}, stub_llm)

    assert llm_calls == len(set(asked)) == 3  # 3 distinct per-instance instances
    assert cache_after["swe-bench-verified/django__django-11099"]["category"] == "bug-fix"

    # Second run with the produced cache is deterministic and free.
    again, _, second_calls = classify_records(classified, cache_after, never_called)
    assert second_calls == 0
    assert again == classified


def test_unclassifiable_verdict_is_cached_not_force_fitted(
    dataset_fixture: Path,
) -> None:
    records = read_records(dataset_fixture)

    def unsure_llm(
        benchmark: str, instance_id: str, context: InstanceContext | None
    ) -> Label:
        return Label(category="unclassified", scale="unknown", language=None)

    classified, cache_after, _ = classify_records(records, {}, unsure_llm)

    assert all(
        r.category == "unclassified" for r in classified if r.source_type == "per-instance"
    )
    # The verdict is cached so the next run does not re-ask.
    _, _, second_calls = classify_records(classified, cache_after, never_called)
    assert second_calls == 0


def test_already_classified_records_are_left_alone(dataset_fixture: Path) -> None:
    records = read_records(dataset_fixture)

    first, cache_after, _ = classify_records(
        records, {}, lambda b, i, c: label("bug-fix")
    )
    second, _, calls = classify_records(first, cache_after, never_called)

    assert calls == 0
    assert second == first


def test_malformed_cache_label_fails_loudly(dataset_fixture: Path) -> None:
    """The hand-editable committed cache is an input to the unified dataset;
    it must pass through the validation seam like any other source."""
    from ai_benchmark.schema import RecordValidationError

    records = read_records(dataset_fixture)
    bad_cache = {
        "polyglot-bench/rust__fix-1": label("feature-dev"),
        "swe-bench-verified/sympy__sympy-20590": label("bug-fix"),
        "swe-bench-verified/django__django-11099": {
            "category": "vibe-coding",  # not in the taxonomy
            "scale": "single-file",
            "language": "python",
        },
    }

    with pytest.raises(RecordValidationError, match="category"):
        classify_records(records, bad_cache, never_called)  # type: ignore[arg-type]


def test_mechanical_scale_upgrades_unknown_cache_entries_without_llm(
    dataset_fixture: Path,
) -> None:
    """A patch file list makes scale mechanical (#8): cached "unknown" scales
    are re-derived in place with zero LLM calls; other cached fields survive."""
    records = read_records(dataset_fixture)
    cache = {
        "polyglot-bench/rust__fix-1": label("feature-dev"),
        "swe-bench-verified/django__django-11099": Label(
            category="bug-fix", scale="unknown", language="python"
        ),
        "swe-bench-verified/sympy__sympy-20590": Label(
            category="bug-fix", scale="unknown", language="python"
        ),
    }
    instances = {
        "swe-bench-verified/django__django-11099": InstanceContext(
            problem_statement="validator bug", patch_files=["django/core/validators.py"]
        ),
        "swe-bench-verified/sympy__sympy-20590": InstanceContext(
            problem_statement="printing bug",
            patch_files=["sympy/printing/latex.py", "sympy/printing/str.py"],
        ),
    }

    classified, cache_after, llm_calls = classify_records(
        records, cache, never_called, instances
    )

    by_instance = {r.instance_id: r for r in classified if r.instance_id}
    assert by_instance["django__django-11099"].scale == "single-file"
    assert by_instance["sympy__sympy-20590"].scale == "cross-file"
    assert llm_calls == 0
    assert cache_after["swe-bench-verified/django__django-11099"] == Label(
        category="bug-fix", scale="single-file", language="python"
    )
    assert cache_after["swe-bench-verified/sympy__sympy-20590"] == Label(
        category="bug-fix", scale="cross-file", language="python"
    )


def test_mechanical_scale_never_overwrites_a_known_cache_entry(
    dataset_fixture: Path,
) -> None:
    """Existing cache entries are preserved — only "unknown" is re-derived."""
    records = read_records(dataset_fixture)
    cache = {
        "polyglot-bench/rust__fix-1": label("feature-dev"),
        "swe-bench-verified/django__django-11099": label("bug-fix"),  # single-file
        "swe-bench-verified/sympy__sympy-20590": label("bug-fix"),
    }
    instances = {
        "swe-bench-verified/django__django-11099": InstanceContext(
            problem_statement=None, patch_files=["a.py", "b.py"]  # says cross-file
        ),
    }

    _, cache_after, _ = classify_records(records, cache, never_called, instances)

    assert cache_after == cache


def test_cache_miss_passes_context_to_llm_and_mechanical_scale_wins(
    dataset_fixture: Path,
) -> None:
    records = read_records(dataset_fixture)
    seen: dict[str, InstanceContext | None] = {}

    def stub_llm(
        benchmark: str, instance_id: str, context: InstanceContext | None
    ) -> Label:
        seen[f"{benchmark}/{instance_id}"] = context
        return Label(category="bug-fix", scale="unknown", language="python")

    instances = {
        "swe-bench-verified/django__django-11099": InstanceContext(
            problem_statement="validator bug", patch_files=["django/core/validators.py"]
        ),
    }

    classified, cache_after, llm_calls = classify_records(
        records, {}, stub_llm, instances
    )

    assert llm_calls == 3
    assert seen["swe-bench-verified/django__django-11099"] == instances[
        "swe-bench-verified/django__django-11099"
    ]
    assert seen["polyglot-bench/rust__fix-1"] is None
    # The LLM said "unknown"; the patch file list is ground truth.
    assert cache_after["swe-bench-verified/django__django-11099"]["scale"] == "single-file"
    by_instance = {r.instance_id: r for r in classified if r.instance_id}
    assert by_instance["django__django-11099"].scale == "single-file"


def test_mechanical_scale_applies_even_when_category_stays_unclassified(
    dataset_fixture: Path,
) -> None:
    records = read_records(dataset_fixture)
    cache = {
        "polyglot-bench/rust__fix-1": label("feature-dev"),
        "swe-bench-verified/django__django-11099": Label(
            category="unclassified", scale="unknown", language=None
        ),
        "swe-bench-verified/sympy__sympy-20590": label("bug-fix"),
    }
    instances = {
        "swe-bench-verified/django__django-11099": InstanceContext(
            problem_statement=None, patch_files=["django/core/validators.py"]
        ),
    }

    classified, cache_after, llm_calls = classify_records(
        records, cache, never_called, instances
    )

    by_instance = {r.instance_id: r for r in classified if r.instance_id}
    assert by_instance["django__django-11099"].category == "unclassified"
    assert by_instance["django__django-11099"].scale == "single-file"
    assert llm_calls == 0
    assert cache_after["swe-bench-verified/django__django-11099"]["scale"] == "single-file"


def test_cache_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    cache = {"swe-bench-verified/x__x-1": label("refactor")}

    write_cache(cache, path)

    assert load_cache(path) == cache
    assert json.loads(path.read_text())  # plain JSON, reviewable in the repo
