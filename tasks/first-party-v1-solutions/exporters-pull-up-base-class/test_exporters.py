import pytest
from exporters import DelimitedExporter, TableExporter


def test_table_export_aligns_columns():
    exporter = TableExporter(["name", "qty"])
    exporter.add(["apples", 12])
    exporter.add(["plums", 7])

    assert exporter.export() == "name    qty\napples  12\nplums   7"


def test_delimited_export_joins_cells():
    exporter = DelimitedExporter(["name", "qty"], delimiter="|")
    exporter.add(["apples", 12])

    assert exporter.export() == "name|qty\napples|12"


def test_rows_must_match_the_columns():
    exporter = TableExporter(["name", "qty"])

    with pytest.raises(ValueError, match="expected 2 cells, got 3"):
        exporter.add(["apples", 12, "extra"])
