"""Structural half of the grading suite: asserts RetryPolicy genuinely moved.
Fails on the pristine repo, where retry.py does not exist."""

import inspect
from pathlib import Path

import pipeline
import retry


def test_retry_module_owns_the_policy():
    # A re-export shim (`from pipeline import RetryPolicy`) leaves the class's
    # __module__ pointing at pipeline; a genuine move does not.
    assert retry.RetryPolicy.__module__ == "retry"
    assert retry.RetryPolicy(attempts=2, backoff_s=1.5).delays() == [0.0, 1.5]


def test_pipeline_module_no_longer_defines_it():
    source = Path(inspect.getsourcefile(pipeline)).read_text()

    assert "class RetryPolicy" not in source


def test_pipeline_defaults_to_the_moved_policy():
    assert isinstance(pipeline.Pipeline().policy, retry.RetryPolicy)
