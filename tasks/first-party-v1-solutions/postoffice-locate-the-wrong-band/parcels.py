"""What a parcel is, and the two readings taken off one.

A parcel is what somebody brought in: what is written on the label, what it
weighed on the scale, and how far it goes round the middle on the gauge. The
two readings are taken separately and neither stands in for the other — a
heavy little thing and a light awkward one are both ordinary parcels, and the
office has seen plenty of each over the years.

Both readings come back as a band, A to D, because that is how the counter has
always written them down. That the two runs of bands are lettered alike is a
convenience of the book and nothing more: a parcel in band C on the scale has
nothing to do with a parcel in band C on the gauge.
"""

from typing import NamedTuple

BY_THE_SCALE = ((250, "A"), (1000, "B"), (5000, "C"), (20000, "D"))

BY_THE_GAUGE = ((18, "A"), (30, "B"), (48, "C"), (72, "D"))


class TooBig(ValueError):
    """What was brought in runs off the end of what it was measured on."""


class Parcel(NamedTuple):
    """One parcel as it was taken in: the label it came in under, what the
    scale said in grams, and what the gauge said in inches round the middle."""

    label: str
    grams: int
    inches: int


def weight_band(grams):
    """The band the scale puts a parcel in.

    Raises `TooBig` where the scale runs out, which is the office's way of
    saying the thing goes by carrier and not through here.
    """
    for most, band in BY_THE_SCALE:
        if grams <= most:
            return band
    raise TooBig(grams)


def size_band(inches):
    """The band the gauge puts a parcel in.

    Raises `TooBig` where the gauge runs out, for the same reason.
    """
    for most, band in BY_THE_GAUGE:
        if inches <= most:
            return band
    raise TooBig(inches)


def to_the_scale(parcels, band):
    """The parcels the scale puts in one band, in the order they came in."""
    return [parcel for parcel in parcels if weight_band(parcel.grams) == band]


def to_the_gauge(parcels, band):
    """The parcels the gauge puts in one band, in the order they came in."""
    return [parcel for parcel in parcels if size_band(parcel.inches) == band]


def taken_in(lines):
    """The parcels taken in off one day's sheet — `biscuits, 1200, 34` — in
    the order they were written down on it."""
    parcels = []
    for line in lines:
        label, grams, inches = line.split(",")
        parcels.append(Parcel(label.strip(), int(grams), int(inches)))
    return parcels
