"""Render a document — a title plus items — as HTML or plain text."""

from html import escape


def render_html(doc):
    """The document as an HTML fragment."""
    items = "".join(f"<li>{escape(item)}</li>" for item in doc["items"])
    return f"<h1>{escape(doc['title'])}</h1><ul>{items}</ul>"


def render_text(doc):
    """The document as plain text: underlined title, dashed items."""
    lines = [doc["title"], "=" * len(doc["title"])]
    lines.extend(f"- {item}" for item in doc["items"])
    return "\n".join(lines)
