"""One-line summaries for listings."""

from textdoc import render_text


def listing_line(doc):
    """The plain-text title line followed by an item count."""
    title = render_text(doc).splitlines()[0]
    return f"{title} ({len(doc['items'])} items)"
