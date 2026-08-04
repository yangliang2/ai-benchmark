from export import export_page
from preview import clipped
from summary import listing_line
from textdoc import render

DOC = {"title": "Groceries", "items": ["milk", "eggs & flour"]}


def test_render_plain_text():
    assert render(DOC, False) == "Groceries\n=========\n- milk\n- eggs & flour"


def test_render_html_escapes_items():
    assert render(DOC, True) == (
        "<h1>Groceries</h1><ul><li>milk</li><li>eggs &amp; flour</li></ul>"
    )


def test_listing_line_counts_items():
    assert listing_line(DOC) == "Groceries (2 items)"


def test_export_page_wraps_the_html():
    assert export_page(DOC).startswith("<html><body><h1>Groceries</h1>")


def test_clipped_narrows_every_line():
    assert clipped(DOC, 3) == "Gro\n===\n- m\n- e"
