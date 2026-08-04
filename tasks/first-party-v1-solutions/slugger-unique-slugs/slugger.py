"""URL slug helpers."""

import re

_INVALID = re.compile(r"[^a-z0-9]+")


def slugify(title):
    """Lowercase title, squeezing runs of other characters into single
    hyphens and trimming hyphens from both ends."""
    return _INVALID.sub("-", title.lower()).strip("-")


def unique_slugs(titles):
    """One unique slug per title, in order; collisions get -2, -3, ..."""
    taken = set()
    slugs = []
    for title in titles:
        base = slugify(title) or "untitled"
        slug = base
        number = 2
        while slug in taken:
            slug = f"{base}-{number}"
            number += 1
        taken.add(slug)
        slugs.append(slug)
    return slugs
