from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def swebench_fixture() -> Path:
    return FIXTURES / "swebench"


@pytest.fixture
def dataset_fixture() -> Path:
    return FIXTURES / "unified.jsonl"


@pytest.fixture
def classified_fixture() -> Path:
    return FIXTURES / "classified.jsonl"


@pytest.fixture
def aggregates_fixture() -> Path:
    return FIXTURES / "aggregates.jsonl"


@pytest.fixture
def aider_fixture() -> Path:
    return FIXTURES / "aider"


@pytest.fixture
def pareto_fixture() -> Path:
    return FIXTURES / "pareto.jsonl"


@pytest.fixture
def firstparty_fixture() -> Path:
    return FIXTURES / "firstparty" / "runs.jsonl"


@pytest.fixture
def firstparty_v1_fixture() -> Path:
    return FIXTURES / "firstparty-v1" / "runs.jsonl"
