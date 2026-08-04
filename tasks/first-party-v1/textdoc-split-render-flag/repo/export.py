"""Full-page HTML export."""

from textdoc import render


def export_page(doc):
    """The document as a complete HTML page."""
    return f"<html><body>{render(doc, True)}</body></html>"
