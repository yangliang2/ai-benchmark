import pytest
from plots import NotAPlot, Plot, held_by, number_of, watered

SITE = [
    Plot(12, "aggie", standpipe=True),
    Plot(3, "wilf", standpipe=True),
    Plot(9, "wilf"),
    Plot(7, "morag", standpipe=True),
]


def test_a_plot_is_its_number_its_holder_and_whether_it_has_a_standpipe():
    assert Plot(3, "wilf", standpipe=True) == Plot(3, "wilf", standpipe=True)
    assert Plot(3, "wilf") != Plot(3, "wilf", standpipe=True)


def test_a_plot_with_nobody_on_it_is_written_down_all_the_same():
    assert repr(Plot(5)) == "Plot(5, holder=None, standpipe=False)"


def test_the_reader_goes_round_the_plots_with_a_standpipe_lowest_first():
    assert [plot.number for plot in watered(SITE)] == [3, 7, 12]


def test_a_plot_with_no_standpipe_is_never_gone_round():
    assert Plot(9, "wilf") not in watered(SITE)


def test_the_plots_one_person_holds_come_back_in_the_order_the_site_has_them():
    assert [plot.number for plot in held_by(SITE, "wilf")] == [3, 9]


def test_a_plot_number_is_read_off_what_was_written_against_it():
    assert number_of("12") == 12
    assert number_of("  12 ") == 12


def test_half_the_site_puts_a_hash_in_front_and_that_is_let_through():
    assert number_of("#12") == 12


def test_what_nobody_can_make_out_is_not_a_plot_number():
    with pytest.raises(NotAPlot):
        number_of("marrows")
