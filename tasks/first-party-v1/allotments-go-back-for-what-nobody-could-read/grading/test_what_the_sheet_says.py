"""Held out: what the sheet says when a card comes back nobody can make out.

Graded through what the society answers rather than through how it answers it:
the prompt reports a sheet carrying a plot at nothing and a list to go back to
that came back empty, so those are what is asserted. Where the figure stops
being made up is the author's business and not the fix's.
"""

from cards import Card, Unreadable, figure, handed_in, written_up
from ledger import NOTHING_USED, Quarter, Reading, most_used
from plots import NotAPlot, Plot, held_by, number_of, watered
from society import Society

SITE = [
    Plot(12, "aggie", standpipe=True),
    Plot(3, "wilf", standpipe=True),
    Plot(9, "wilf"),
    Plot(7, "morag", standpipe=True),
]

NOTES = {9: "no standpipe, uses the trough"}

# Plot 7's card came back out of the rain with nothing left on it.
RUN = [Card(3, "1180"), Card(7, "   "), Card(12, "3400")]

# The same run with plot 7 read and found not to have moved, which is a
# reading and belongs on the sheet.
STOOD_STILL = [Card(3, "1180"), Card(7, "0"), Card(12, "3400")]


def society():
    return Society(SITE, NOTES)


def test_a_card_nobody_could_make_out_is_left_off_the_sheet():
    assert society().sheet(Quarter(RUN)) == {3: 1180, 12: 3400}


def test_a_card_nobody_could_make_out_puts_its_plot_on_the_list_to_go_back_to():
    assert society().to_go_back_to(Quarter(RUN)) == [7]


def test_a_run_that_came_back_whole_leaves_nobody_to_go_back_to():
    assert society().to_go_back_to(Quarter(STOOD_STILL)) == []


def test_a_plot_read_and_found_not_to_have_moved_is_on_the_sheet_at_nothing():
    """The other half of the same claim, and what makes it worth asserting: a
    figure of nothing is a reading like any other. What must not be on the
    sheet is the plot nobody read."""
    assert society().sheet(Quarter(STOOD_STILL)) == {3: 1180, 7: 0, 12: 3400}
    assert society().to_go_back_to(Quarter(RUN)) == [7]


def test_the_whole_site_leaves_out_what_nobody_could_make_out():
    assert society().altogether(Quarter(RUN)) == 4580
    assert society().altogether(Quarter(STOOD_STILL)) == 4580


def test_a_run_where_nothing_could_be_made_out_puts_every_plot_on_the_list():
    nothing_read = [Card(3, "see over"), Card(7, "   ")]

    figures, going_back = society().read(Quarter(nothing_read))

    assert figures == {}
    assert going_back == [3, 7]
    assert society().altogether(Quarter(nothing_read)) == 0


def test_the_figures_and_the_list_are_the_two_halves_of_one_reading():
    figures, going_back = society().read(Quarter(RUN))

    assert figures == {3: 1180, 12: 3400}
    assert going_back == [7]


def test_the_book_still_writes_up_every_card_that_came_back():
    """What the fix must leave alone: the book says what came back off each
    plot, unread cards and all. It is the sheet that leaves them off."""
    assert society().book(Quarter(RUN)) == [
        "plot 3: 1180",
        "plot 7: not read",
        "plot 12: 3400",
    ]


def test_the_neighbouring_reckonings_are_unchanged():
    """What the fix must leave alone: the order the reader goes round in, the
    plots one person holds, how a plot number is read off what was written
    against it, what the books have for last time, and the notes."""
    quarter = Quarter(RUN, {3: 1000, 12: 3400})

    assert [plot.number for plot in society().standpipes()] == [3, 7, 12]
    assert [plot.number for plot in held_by(SITE, "wilf")] == [3, 9]
    assert [plot.number for plot in watered(SITE)] == [3, 7, 12]
    assert number_of("#12") == 12
    assert quarter.carded() == [3, 7, 12]
    assert quarter.card_for(7) == Card(7, "   ")
    assert quarter.read_before(3) == 1000
    assert quarter.read_before(7) is None
    assert society().note_on(9) == "no standpipe, uses the trough"
    assert society().note_on(3) == ""
    assert figure(" 3400 ") == 3400
    assert written_up(Card(7, "   ")) == "plot 7: not read"
    assert handed_in(["12: 3400"]) == [Card(12, " 3400")]
    assert Reading(3, 1180).since(1000) == 180
    assert Reading(12, 40).since(3400) == NOTHING_USED
    assert most_used([Reading(3, 1180), Reading(12, 3400)]) == Reading(12, 3400)
    assert most_used([]) is None

    try:
        number_of("marrows")
    except NotAPlot:
        pass
    else:
        raise AssertionError("a plot number was made up out of nothing")

    try:
        figure("see over")
    except Unreadable:
        pass
    else:
        raise AssertionError("a figure was made up out of a card nobody read")
