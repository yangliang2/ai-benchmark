"""Behaviour half of the grading suite: must pass before and after the split,
so it renders only through the callers — never through render itself."""

from export import export_page
from preview import clipped
from summary import listing_line


def test_listing_line_takes_the_title_line_and_counts_items():
    doc = {"title": "Groceries", "items": ["milk", "eggs"]}

    assert listing_line(doc) == "Groceries (2 items)"


def test_listing_line_with_no_items():
    assert listing_line({"title": "Empty", "items": []}) == "Empty (0 items)"


def test_export_page_is_the_escaped_document_in_a_page():
    doc = {"title": "Q3 <plan>", "items": ["ship & iterate"]}

    assert export_page(doc) == (
        "<html><body><h1>Q3 &lt;plan&gt;</h1>"
        "<ul><li>ship &amp; iterate</li></ul></body></html>"
    )


def test_clipped_narrows_title_underline_and_items_alike():
    doc = {"title": "Notes", "items": ["a very long item"]}

    assert clipped(doc, 4) == "Note\n====\n- a "
