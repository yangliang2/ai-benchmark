import pytest
from tabular import parse, render

TEXT = """\
name,age
ada,36
grace,45
"""


def test_parse_returns_headers_and_row_dicts():
    headers, rows = parse(TEXT)
    assert headers == ["name", "age"]
    assert rows == [{"name": "ada", "age": "36"}, {"name": "grace", "age": "45"}]


def test_parse_of_empty_text_is_empty():
    assert parse("") == ([], [])


def test_a_ragged_row_raises():
    with pytest.raises(ValueError):
        parse("a,b\n1\n")


def test_render_round_trips():
    headers, rows = parse(TEXT)
    assert render(headers, rows) == "name,age\nada,36\ngrace,45"
