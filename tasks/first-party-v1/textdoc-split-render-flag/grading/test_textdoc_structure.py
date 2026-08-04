"""Structural half of the grading suite: asserts the flag function is gone
and each format has a function of its own. Fails on the pristine repo, where
render_html and render_text do not exist."""

import textdoc
from textdoc import render_html, render_text


def test_the_flag_function_is_gone():
    # Keeping render(doc, as_html) around — even delegating to the new
    # functions — is not a split.
    assert not hasattr(textdoc, "render")


def test_render_html_owns_the_html_format():
    doc = {"title": "Q3 <plan>", "items": ["ship & iterate"]}

    assert render_html(doc) == (
        "<h1>Q3 &lt;plan&gt;</h1><ul><li>ship &amp; iterate</li></ul>"
    )


def test_render_text_owns_the_plain_format():
    doc = {"title": "Q3 <plan>", "items": ["ship & iterate"]}

    assert render_text(doc) == "Q3 <plan>\n=========\n- ship & iterate"
