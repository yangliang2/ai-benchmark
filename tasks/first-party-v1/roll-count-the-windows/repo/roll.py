"""A roll of photographs, and what was taken when."""

from collections import namedtuple

# One photograph: the second of the shoot it was taken at, what it shows, and
# the mark the photographer put on it — "" for none, "blurred" for one that
# came out soft, "keep" for one that is to survive whatever else goes.
Photo = namedtuple("Photo", "at shows mark")


def in_order(photos):
    """Whether the roll runs in time order, each photo taken at or after the
    one before it."""
    return all(later.at >= earlier.at for earlier, later in zip(photos, photos[1:]))


def gaps(photos):
    """The seconds between one photo and the next, in order."""
    return [later.at - earlier.at for earlier, later in zip(photos, photos[1:])]


def marked(photos, mark):
    """The photos carrying a given mark, in the order they were taken."""
    return [photo for photo in photos if photo.mark == mark]


def shown(photos):
    """What the photos show, in the order they were taken."""
    return [photo.shows for photo in photos]


def describe(photos):
    """One line per photo: when it was taken and what it shows."""
    return [
        f"{photo.at}s {photo.shows}" + (f" ({photo.mark})" if photo.mark else "")
        for photo in photos
    ]
