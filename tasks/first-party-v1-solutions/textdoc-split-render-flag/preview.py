"""Terminal preview, clipped to a width."""

from textdoc import render_text


def clipped(doc, width):
    """Every plain-text line of the document, clipped to width characters."""
    return "\n".join(line[:width] for line in render_text(doc).splitlines())
