from cards import Card
from ledger import Quarter, Reading, most_used

RUN = [Card(3, "1180"), Card(7, "820"), Card(12, "3400")]

LAST_TIME = {3: 1000, 12: 3400}


def run():
    return Quarter(RUN, LAST_TIME)


def test_a_run_knows_which_plots_a_card_came_back_for():
    assert run().carded() == [3, 7, 12]


def test_the_card_that_came_back_for_a_plot_is_the_one_handed_in_for_it():
    assert run().card_for(7) == Card(7, "820")


def test_what_a_plot_got_through_is_the_figure_on_its_card():
    assert run().used_on(3) == 1180
    assert run().used_on(12) == 3400


def test_what_a_plot_stood_at_last_time_comes_out_of_the_books():
    assert run().read_before(3) == 1000


def test_a_plot_the_books_have_nothing_for_stood_at_nothing_they_know_of():
    assert run().read_before(7) is None


def test_a_reading_on_its_own_is_the_whole_of_what_went_through():
    assert Reading(3, 1180).since() == 1180


def test_a_reading_against_the_run_before_is_the_difference():
    assert Reading(3, 1180).since(1000) == 180


def test_a_dial_that_has_been_changed_reads_as_nothing_and_not_as_less():
    assert Reading(12, 40).since(3400) == 0


def test_the_most_used_plot_is_the_one_that_got_through_the_most():
    readings = [Reading(3, 1180), Reading(7, 820), Reading(12, 3400)]

    assert most_used(readings) == Reading(12, 3400)


def test_a_run_that_brought_nothing_back_has_no_most_used_plot():
    assert most_used([]) is None
