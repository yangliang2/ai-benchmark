"""URL slug helpers."""

import re

_INVALID = re.compile(r"[^a-z0-9]+")


def slugify(title):
    """Lowercase title, squeezing runs of other characters into single
    hyphens and trimming hyphens from both ends."""
    return _INVALID.sub("-", title.lower()).strip("-")
