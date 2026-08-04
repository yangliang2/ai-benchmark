"""Structural half of the grading suite: asserts parse_task now returns a
real ParsedTask. Fails on the pristine repo, where the class is missing."""

import pytest

from tasktrack import ParsedTask, parse_task


def test_parse_task_returns_a_parsed_task():
    task = parse_task("x pay rent !1 #home #money")

    assert isinstance(task, ParsedTask)
    assert task.title == "pay rent"
    assert task.priority == 1
    assert task.tags == ["home", "money"]
    assert task.done is True


def test_the_defaults_survive_the_reshape():
    task = parse_task("water plants")

    assert task.title == "water plants"
    assert task.priority == 3
    assert task.tags == []
    assert task.done is False


def test_the_tuple_shape_is_retired():
    # A NamedTuple would keep every positional call site working unchanged;
    # the reshape is only real if unpacking no longer is.
    task = parse_task("water plants")

    assert not isinstance(task, tuple)
    with pytest.raises(TypeError):
        title, priority, tags, done = task
