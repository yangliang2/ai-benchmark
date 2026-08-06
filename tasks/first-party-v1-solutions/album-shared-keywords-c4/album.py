"""Photo albums and the keywords filed against them.

A keyword is remembered exactly as it was written, because that is what a
caption shows. Two keywords that canonicalise the same way are the same
keyword all the same: `canonical` folds case, trims the ends and closes up
runs of blanks, so `Black & White`, `black & white` and `  BLACK   & white `
are one keyword filed three ways.

Anything this module answers about *which* keywords an album carries, rather
than about how somebody typed them, it answers in canonical form.
`keyword_set` is that answer, and `has_keyword` and `describe` are built on
it. `keywords` is the other kind of question, and answers as written.

Nothing here modifies the album it is given except `add_keyword`, which is
the one function that files anything.
"""


def new_album(title):
    """An album with a title and nothing filed against it yet."""
    return {"title": title, "keywords": []}


def add_keyword(album, keyword):
    """File `keyword` against `album`, as written."""
    album["keywords"].append(keyword)


def keywords(album):
    """Every keyword filed against the album, as written, in filing order."""
    return list(album["keywords"])


def canonical(keyword):
    """The form two keywords share when they are the same keyword."""
    return " ".join(keyword.split()).casefold()


def keyword_set(album):
    """Which keywords the album carries, canonically."""
    return {canonical(keyword) for keyword in album["keywords"]}


def has_keyword(album, keyword):
    """Whether the album carries `keyword`, however either was written."""
    return canonical(keyword) in keyword_set(album)


def describe(album):
    """A one-line summary of an album and what it carries."""
    carried = ", ".join(sorted(keyword_set(album))) or "nothing"
    return f"{album['title']}: {carried}"


def shared_keywords(one, other):
    """The keywords both albums carry, canonically, in alphabetical order."""
    return sorted(keyword_set(one) & keyword_set(other))
