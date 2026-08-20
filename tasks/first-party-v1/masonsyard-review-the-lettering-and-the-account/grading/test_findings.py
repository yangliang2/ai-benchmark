"""Held out: whether the agent's answer file reports every planted finding.

Canonical — this project's own file, shipped byte for byte into every
code-review task's grading directory and read back that way by the task-set
lint, so that nothing in a task's grading directory can stop consulting
`_findings.py` while still shipping an unedited copy of it. A task may ship
additional grading tests beside this one: resolution requires every grading
test to pass, so an extra test can only make the task harder to resolve, never
let a wrong answer through.
"""

from _findings import findings_problem


def test_the_answer_reports_every_planted_finding():
    assert (problem := findings_problem()) is None, problem
