"""Behaviour half of the grading suite: must pass before and after the
pull-up, so it exercises the two exporters' public behaviour only."""

import pytest

from exporters import DelimitedExporter, TableExporter


def test_table_export_aligns_columns_and_trims_line_ends():
    exporter = TableExporter(["name", "qty"])
    exporter.add(["apples", 12])
    exporter.add(["plums", 7])

    assert exporter.export() == "name    qty\napples  12\nplums   7"


def test_table_export_with_no_rows_is_just_the_header():
    assert TableExporter(["name", "qty"]).export() == "name  qty"


def test_delimited_export_joins_cells():
    exporter = DelimitedExporter(["name", "qty"], delimiter="|")
    exporter.add(["apples", 12])

    assert exporter.export() == "name|qty\napples|12"


def test_the_default_delimiter_is_a_semicolon():
    exporter = DelimitedExporter(["a", "b"])
    exporter.add([1, 2])

    assert exporter.export() == "a;b\n1;2"


def test_cells_are_coerced_to_text_and_counted():
    for exporter in (TableExporter(["a", "b"]), DelimitedExporter(["a", "b"])):
        exporter.add([1, None])
        assert exporter.count() == 1
        assert "None" in exporter.export()


def test_rows_must_match_the_columns():
    for exporter in (TableExporter(["a", "b"]), DelimitedExporter(["a", "b"])):
        with pytest.raises(ValueError, match="expected 2 cells, got 3"):
            exporter.add([1, 2, 3])


def test_at_least_one_column_is_required():
    with pytest.raises(ValueError, match="at least one column is required"):
        TableExporter([])
    with pytest.raises(ValueError, match="at least one column is required"):
        DelimitedExporter([])
