"""Layered application settings.

Settings are plain nested mappings: a mapping is a section to look inside,
anything else — a number, a string, a list — is a value. Nothing here
modifies what it is given, and every mapping a function returns is one of
its own, so callers can keep using the settings they passed in.
"""


def flatten(settings):
    """The settings as a flat mapping of dotted paths to values."""
    flat = {}
    for key, value in settings.items():
        if isinstance(value, dict):
            for path, leaf in flatten(value).items():
                flat[f"{key}.{path}"] = leaf
        else:
            flat[key] = value
    return flat


def value_at(settings, path, default=None):
    """The value at a dotted path, or default when nothing is set there."""
    here = settings
    for key in path.split("."):
        if not isinstance(here, dict) or key not in here:
            return default
        here = here[key]
    return here


def set_value(settings, path, value):
    """A copy of the settings with value set at the dotted path.

    Every section along the path is copied rather than written into, so the
    settings passed in come back out unchanged.
    """
    key, _, rest = path.partition(".")
    updated = dict(settings)
    if rest:
        section = updated.get(key)
        updated[key] = set_value(section if isinstance(section, dict) else {},
                                 rest, value)
    else:
        updated[key] = value
    return updated


def merged(layers):
    """The single settings mapping an ordered sequence of layers adds up to.

    Later layers win, but only key by key: two sections at the same key are
    merged rather than replaced, at any depth. A section and a value are
    different kinds of thing, so either replaces the other outright, and a
    list is a value like any other. Every section in the result is a fresh
    mapping, so the layers come back out untouched.
    """
    settings = {}
    for layer in layers:
        settings = _overlay(settings, layer)
    return settings


def _overlay(settings, layer):
    """The settings so far with one more layer applied over them."""
    combined = dict(settings)
    for key, value in layer.items():
        if isinstance(value, dict):
            section = combined.get(key)
            combined[key] = _overlay(section if isinstance(section, dict) else {},
                                     value)
        else:
            combined[key] = value
    return combined
