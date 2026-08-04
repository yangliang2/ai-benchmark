"""Terminal preview, clipped to a width."""

from textdoc import render


def clipped(doc, width):
    """Every plain-text line of the document, clipped to width characters."""
    return "\n".join(line[:width] for line in render(doc, False).splitlines())
