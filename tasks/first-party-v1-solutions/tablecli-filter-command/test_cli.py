import pytest
from cli import main

TEXT = """\
name,age
ada,36
grace,45
"""


def test_columns_lists_the_header_names():
    assert main(["columns"], TEXT) == "name\nage"


def test_count_counts_the_rows():
    assert main(["count"], TEXT) == "2"


def test_an_unknown_command_raises():
    with pytest.raises(ValueError):
        main(["explode"], TEXT)


def test_no_command_raises():
    with pytest.raises(ValueError):
        main([], TEXT)
