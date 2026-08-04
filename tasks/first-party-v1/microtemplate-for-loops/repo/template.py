"""A tiny placeholder template language.

render(template, context) substitutes {{ name }} placeholders with values
from context, optionally piped through a filter: {{ name|upper }}.
"""

import re

from filters import FILTERS

_PLACEHOLDER = re.compile(
    r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*)?\}\}"
)


def render(template, context):
    """Substitute every placeholder in template from context.

    A name missing from context raises KeyError; an unknown filter raises
    ValueError.
    """

    def substitute(match):
        name, filter_name = match.group(1), match.group(2)
        value = str(context[name])
        if filter_name is not None:
            value = apply_filter(filter_name, value)
        return value

    return _PLACEHOLDER.sub(substitute, template)


def apply_filter(name, value):
    """Run the named filter over an already-rendered value."""
    try:
        filter_function = FILTERS[name]
    except KeyError:
        raise ValueError(f"unknown filter {name!r}") from None
    return filter_function(value)
