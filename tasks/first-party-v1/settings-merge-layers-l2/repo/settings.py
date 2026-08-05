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
