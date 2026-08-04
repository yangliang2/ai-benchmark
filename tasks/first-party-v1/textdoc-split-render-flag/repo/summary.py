"""One-line summaries for listings."""

from textdoc import render


def listing_line(doc):
    """The plain-text title line followed by an item count."""
    title = render(doc, False).splitlines()[0]
    return f"{title} ({len(doc['items'])} items)"
