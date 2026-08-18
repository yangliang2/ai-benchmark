"""Held out: whether the agent's answer file names an accepted location.

Canonical — this project's own file, shipped byte for byte into every
fault-location task's grading directory and read back that way by the
task-set lint (`_answer_test_problems` in firstparty_v1.py), so that nothing
in a task's grading directory can stop consulting `_answer.py` while still
shipping an unedited copy of it. A task may ship additional grading tests
beside this one: resolution requires every grading test to pass, so an extra
test can only make the task harder to resolve, never let a wrong answer
through.
"""

from _answer import answer_problem


def test_the_answer_names_an_accepted_location():
    assert (problem := answer_problem()) is None, problem
