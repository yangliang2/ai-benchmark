from cards import Card
from ledger import Quarter
from plots import Plot
from society import Society

SITE = [
    Plot(12, "aggie", standpipe=True),
    Plot(3, "wilf", standpipe=True),
    Plot(9, "wilf"),
    Plot(7, "morag", standpipe=True),
]

NOTES = {9: "no standpipe, uses the trough"}

RUN = [Card(3, "1180"), Card(7, "820"), Card(12, "3400")]


def society():
    return Society(SITE, NOTES)


def test_the_reader_goes_round_the_plots_with_a_standpipe():
    assert [plot.number for plot in society().standpipes()] == [3, 7, 12]


def test_a_note_written_against_a_plot_comes_back_as_it_was_written():
    assert society().note_on(9) == "no standpipe, uses the trough"


def test_a_plot_with_nothing_written_against_it_has_nothing_written():
    assert society().note_on(3) == ""


def test_the_sheet_has_every_plot_a_card_came_back_for():
    assert society().sheet(Quarter(RUN)) == {3: 1180, 7: 820, 12: 3400}


def test_a_run_the_reader_got_all_the_way_round_leaves_nobody_to_go_back_to():
    assert society().to_go_back_to(Quarter(RUN)) == []


def test_the_site_altogether_is_what_the_sheet_comes_to():
    assert society().altogether(Quarter(RUN)) == 5400


def test_a_run_that_brought_no_cards_back_comes_to_nothing():
    assert society().altogether(Quarter([])) == 0


def test_the_book_writes_up_every_card_that_came_back():
    assert society().book(Quarter(RUN)) == [
        "plot 3: 1180",
        "plot 7: 820",
        "plot 12: 3400",
    ]


def test_a_plot_read_and_found_not_to_have_moved_is_on_the_sheet_at_nothing():
    stood_still = [Card(3, "1180"), Card(7, "0")]

    assert society().sheet(Quarter(stood_still)) == {3: 1180, 7: 0}
