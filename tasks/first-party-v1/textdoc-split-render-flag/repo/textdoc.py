"""Render a document — a title plus items — as HTML or plain text."""

from html import escape


def render(doc, as_html):
    """The document as one string: HTML when as_html, plain text otherwise."""
    if as_html:
        items = "".join(f"<li>{escape(item)}</li>" for item in doc["items"])
        return f"<h1>{escape(doc['title'])}</h1><ul>{items}</ul>"
    lines = [doc["title"], "=" * len(doc["title"])]
    lines.extend(f"- {item}" for item in doc["items"])
    return "\n".join(lines)
