"""A tiny placeholder template language with loop blocks.

render(template, context) substitutes {{ name }} placeholders with values
from context, optionally piped through a filter ({{ name|upper }}), and
renders {% for item in items %}...{% endfor %} blocks once per element.
"""

import re

from filters import FILTERS

_PLACEHOLDER = re.compile(
    r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*)?\}\}"
)
_TAG = re.compile(r"\{%\s*(.*?)\s*%\}")
_FOR = re.compile(r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+([A-Za-z_][A-Za-z0-9_]*)")


def render(template, context):
    """Render template against context.

    A name missing from scope raises KeyError; an unknown filter or an
    unbalanced loop tag raises ValueError.
    """
    # Split into alternating literal text (even indices) and tag contents
    # (odd indices), then walk that flat list as a block structure.
    segments = _TAG.split(template)
    return _render_block(segments, 0, len(segments), dict(context))


def apply_filter(name, value):
    """Run the named filter over an already-rendered value."""
    try:
        filter_function = FILTERS[name]
    except KeyError:
        raise ValueError(f"unknown filter {name!r}") from None
    return filter_function(value)


def _render_block(segments, start, stop, scope):
    """Render segments[start:stop], a region with balanced loop tags."""
    parts = []
    position = start
    while position < stop:
        if position % 2 == 0:
            parts.append(_substitute(segments[position], scope))
            position += 1
            continue
        tag = segments[position]
        if tag == "endfor":
            raise ValueError("endfor with no loop open")
        matched = _FOR.fullmatch(tag)
        if matched is None:
            raise ValueError(f"unknown tag {tag!r}")
        variable, iterable = matched.group(1), matched.group(2)
        end = _matching_endfor(segments, position)
        for item in scope[iterable]:
            parts.append(
                _render_block(segments, position + 1, end, scope | {variable: item})
            )
        position = end + 1
    return "".join(parts)


def _matching_endfor(segments, position):
    """The index of the endfor tag closing the for tag at position."""
    depth = 1
    index = position + 2
    while index < len(segments):
        tag = segments[index]
        if tag == "endfor":
            depth -= 1
            if depth == 0:
                return index
        elif _FOR.fullmatch(tag):
            depth += 1
        index += 2
    raise ValueError("for without endfor")


def _substitute(text, scope):
    def substitute(match):
        name, filter_name = match.group(1), match.group(2)
        value = str(scope[name])
        if filter_name is not None:
            value = apply_filter(filter_name, value)
        return value

    return _PLACEHOLDER.sub(substitute, text)
