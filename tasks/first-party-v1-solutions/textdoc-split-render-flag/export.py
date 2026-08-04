"""Full-page HTML export."""

from textdoc import render_html


def export_page(doc):
    """The document as a complete HTML page."""
    return f"<html><body>{render_html(doc)}</body></html>"
