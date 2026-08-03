from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def swebench_fixture() -> Path:
    return FIXTURES / "swebench"


@pytest.fixture
def dataset_fixture() -> Path:
    return FIXTURES / "unified.jsonl"
