"""Locate-style `codebase-comprehension` rides the fault-location answer key,
`_answer.py`, the task-set lint and the hash gate verbatim (#68, design note
§45.2): a comprehension task asks "where is X handled" with no defect behind
it, and is graded through exactly the same mechanism a fault-location task
is — the accepted set names where correct behaviour lives instead of where a
defect lives, and the rejected set names the plausible wrong place a related
but different behaviour lives instead of the plausible wrong file the symptom
points at.

Everything here is proved on a **fixture** task built into tmp_path, the way
`tests/test_firstparty_v1_fault_location.py` proves the mechanism itself: no
comprehension task is authored here (that is tickets 18 and 19), only that
every gate which used to read `category == "fault-location"` now reads the
two-member set.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from firstparty_v1_tasks import run_for, workdir_diff

from ai_benchmark.dataset import IngestError
from ai_benchmark.firstparty_v1 import (
    ANSWER_KEY_FILE,
    ANSWER_MODULE,
    ANSWER_TEST_FILE,
    HASH_GATE_FILE,
    Task,
    answer_key,
    answer_module_source,
    answer_test_source,
    evaluate,
    hash_gate_source,
    is_keyed,
    lint_task_set,
    load_task_set,
)

FIXTURE_ID = "messaging-locate-where-email-is-sent"

ANSWER_PATH = "ANSWER.json"

# Two modules, each responsible for one channel: the accepted answer lives in
# one, and the rejected near-miss is the *other* channel's module — a
# plausible wrong place because it is a related but different behaviour,
# never a defect. `Notifier` sits beside `EmailChannel` so a class-level
# accepted answer is not the only class in its file (terrain rule 3), and
# each module's docstring says what it is for in words the prompt does not
# use, so the prompt's own vocabulary is not one grep from the answer.
EMAIL = '''\
"""Where outbound email is sent from."""


class Notifier:
    """Something that tells a user about an order."""

    def notify(self, user, message):
        raise NotImplementedError


class EmailChannel(Notifier):
    """Sends a message over email."""

    def __init__(self, smtp):
        self.smtp = smtp

    def notify(self, user, message):
        return self.smtp.send(user.email, message)
'''

SMS = '''\
"""Where outbound text messages are sent from."""

from messaging import Notifier


class SmsChannel(Notifier):
    """Sends a message over SMS."""

    def __init__(self, gateway):
        self.gateway = gateway

    def notify(self, user, message):
        return self.gateway.send(user.phone, message)
'''

PROMPT = f"""\
This service notifies a user by more than one channel. Say where the email
channel is handled. Do not change any code.

Write your answer to {ANSWER_PATH} in the repository root, as a JSON object
with "file" (the path, relative to the repository root) and "symbol" (the
class or method the behaviour lives in).
"""

ACCEPTED: list[dict[str, object]] = [
    {"file": "messaging.py", "symbol": "EmailChannel.notify"},
    {"file": "messaging.py", "symbol": "EmailChannel"},
]

# The plausible wrong place: the other channel, which is a related but
# different behaviour rather than a defect's symptom.
REJECTED: list[dict[str, object]] = [{"file": "sms.py", "symbol": "SmsChannel"}]

DOMAIN_NOUNS = ["user", "message", "channel", "notify", "notifies", "notifier", "email"]

GRADING_TEST = answer_test_source().decode("utf-8")


def write_fixture(
    root: Path,
    *,
    accepted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
    prompt: str = PROMPT,
    grading_test: str = GRADING_TEST,
    task_id: str = FIXTURE_ID,
    **spec: object,
) -> Path:
    """The fixture codebase-comprehension task, written into root ready to
    load — built the same way `test_firstparty_v1_fault_location.py`'s
    `write_fixture` builds a fault-location one, since #68's whole point is
    that nothing about the mechanism differs."""
    task_dir = root / task_id
    (task_dir / "repo").mkdir(parents=True)
    (task_dir / "grading").mkdir()
    fields: dict[str, object] = {
        "id": task_id,
        "category": "codebase-comprehension",
        "scale": "single-file",
        "surface": "application",
        "language": "python",
        "control": True,
        "domain_nouns": DOMAIN_NOUNS,
        "prompt": prompt,
    }
    fields.update(spec)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(fields, sort_keys=False))
    (task_dir / "repo" / "messaging.py").write_text(EMAIL)
    (task_dir / "repo" / "sms.py").write_text(SMS)
    (task_dir / "grading" / ANSWER_TEST_FILE).write_text(grading_test)
    (task_dir / "grading" / ANSWER_MODULE).write_bytes(answer_module_source())
    (task_dir / "grading" / ANSWER_KEY_FILE).write_text(
        json.dumps(
            {
                "answer_path": ANSWER_PATH,
                "accepted": ACCEPTED if accepted is None else accepted,
                "rejected": REJECTED if rejected is None else rejected,
            },
            indent=2,
        )
        + "\n"
    )
    (task_dir / "grading" / HASH_GATE_FILE).write_bytes(
        hash_gate_source(task_dir / "repo")
    )
    return task_dir


def fixture_task(root: Path, **overrides: Any) -> Task:
    write_fixture(root, **overrides)
    [task] = load_task_set(root)
    return task


def naming(file: str, symbol: str) -> str:
    return json.dumps({"file": file, "symbol": symbol}, indent=2) + "\n"


def answers(payload: str) -> Callable[[Path], None]:
    def write(workdir: Path) -> None:
        (workdir / ANSWER_PATH).write_text(payload)

    return write


def verdict(task: Task, payload: str) -> float:
    diff = workdir_diff(task, answers(payload))
    [record] = evaluate([task], [run_for(task, diff)], source="run-log")
    return record.quality_value


def test_a_comprehension_task_loads_carrying_its_accepted_answer_key(
    tmp_path: Path,
) -> None:
    task = fixture_task(tmp_path)
    key = answer_key(task)

    assert task.category == "codebase-comprehension"
    assert is_keyed(task)
    assert key.answer_path == ANSWER_PATH
    assert {(a.file, a.symbol) for a in key.accepted} == {
        ("messaging.py", "EmailChannel.notify"),
        ("messaging.py", "EmailChannel"),
    }
    assert lint_task_set([task]) == []


def test_a_comprehension_task_with_an_empty_accepted_set_fails_to_load(
    tmp_path: Path,
) -> None:
    """The same load-time refusal a fault-location task gets: `ai-bench
    run-live` loads a task set but never lints it, so an unsolvable key would
    otherwise reach a paid run."""
    with pytest.raises(IngestError, match="accepts no"):
        fixture_task(tmp_path, accepted=[])


def test_lint_rejects_a_comprehension_key_naming_a_file_not_in_the_repo(
    tmp_path: Path,
) -> None:
    """The key-shape rules run identically on a comprehension task — proved
    with the same class of defect `test_firstparty_v1_fault_location.py`
    proves on a fault-location one."""
    task = fixture_task(
        tmp_path, accepted=[{"file": "push.py", "symbol": "PushChannel"}]
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "push.py" in problem
    assert "starting repository" in problem


def test_lint_requires_a_rejected_answer_naming_a_file_not_already_accepted(
    tmp_path: Path,
) -> None:
    """The rejected-half rules apply exactly as written for comprehension too
    — not softened for the new action: a rejected set confined to files the
    accepted set already names never supplies the plausible wrong place."""
    task = fixture_task(
        tmp_path,
        rejected=[{"file": "messaging.py", "symbol": "Notifier"}],
    )

    [problem] = lint_task_set([task])

    assert FIXTURE_ID in problem and "messaging.py" in problem


def test_the_discrimination_gate_runs_on_a_comprehension_fixture(
    tmp_path: Path,
) -> None:
    """`_discrimination_problems` used to be gated on `category ==
    "fault-location"` alone; a comprehension task with a grading test that
    resolves everything now fails the lint the same way."""
    always_resolves = '''\
"""A grading test that reads nothing and asserts nothing."""


def test_the_answer_names_an_accepted_location():
    assert True
'''
    task = fixture_task(tmp_path, grading_test=always_resolves)

    problems = lint_task_set([task])

    assert all(FIXTURE_ID in problem for problem in problems)
    for negative in (
        "no answer file",
        "an empty answer file",
        "a malformed answer file",
        "does not accept",
        "rejected answer",
    ):
        assert any(negative in problem for problem in problems), negative


def test_a_correct_answer_resolves_and_a_rejected_one_does_not(
    tmp_path: Path,
) -> None:
    task = fixture_task(tmp_path)

    assert verdict(task, naming("messaging.py", "EmailChannel.notify")) == 1.0
    assert verdict(task, naming("sms.py", "SmsChannel")) == 0.0
