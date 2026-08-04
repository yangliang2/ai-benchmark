"""Instance-context seam tests: raw source content in -> context store + mechanical scale.

The context store is a committed side-input keyed like the classification
cache ("benchmark/instance_id"); parsing is pure so it stays offline-testable.
"""

import json
from pathlib import Path

from ai_benchmark.instances import (
    InstanceContext,
    load_instances,
    patch_files_from_diff,
    scale_from_patch_files,
    swebench_context_from_rows,
    write_instances,
)

TWO_FILE_PATCH = """\
diff --git a/django/core/validators.py b/django/core/validators.py
index 1111111..2222222 100644
--- a/django/core/validators.py
+++ b/django/core/validators.py
@@ -1 +1 @@
-old
+new
diff --git a/tests/validators/tests.py b/tests/validators/tests.py
index 3333333..4444444 100644
--- a/tests/validators/tests.py
+++ b/tests/validators/tests.py
@@ -1 +1 @@
-old
+new
"""


def test_patch_files_from_diff_lists_each_file_once() -> None:
    files = patch_files_from_diff(TWO_FILE_PATCH)
    assert files == [
        "django/core/validators.py",
        "tests/validators/tests.py",
    ]


def test_patch_files_from_diff_uses_post_image_path_for_renames() -> None:
    patch = (
        "diff --git a/old_name.py b/new_name.py\n"
        "similarity index 90%\n"
        "rename from old_name.py\n"
        "rename to new_name.py\n"
    )
    assert patch_files_from_diff(patch) == ["new_name.py"]


def test_patch_files_from_diff_dedupes_repeated_headers() -> None:
    patch = (
        "diff --git a/x.py b/x.py\n@@ -1 +1 @@\n-a\n+b\n"
        "diff --git a/x.py b/x.py\n@@ -9 +9 @@\n-c\n+d\n"
    )
    assert patch_files_from_diff(patch) == ["x.py"]


def test_scale_is_mechanical_from_patch_file_count() -> None:
    assert scale_from_patch_files(["a.py"]) == "single-file"
    assert scale_from_patch_files(["a.py", "b.py"]) == "cross-file"
    assert scale_from_patch_files([]) == "unknown"
    assert scale_from_patch_files(None) == "unknown"


def test_swebench_rows_become_context_keyed_like_the_cache() -> None:
    rows = [
        {
            "instance_id": "django__django-11099",
            "problem_statement": "UsernameValidator allows trailing newline",
            "patch": TWO_FILE_PATCH,
        },
    ]

    instances = swebench_context_from_rows(rows)

    context = instances["swe-bench-verified/django__django-11099"]
    assert context["problem_statement"] == "UsernameValidator allows trailing newline"
    assert context["patch_files"] == [
        "django/core/validators.py",
        "tests/validators/tests.py",
    ]


def test_context_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "instance-context.json"
    instances = {
        "swe-bench-verified/x__x-1": InstanceContext(
            problem_statement="a bug", patch_files=["x.py"]
        )
    }

    write_instances(instances, path)

    assert load_instances(path) == instances
    assert json.loads(path.read_text())  # plain JSON, reviewable in the repo
