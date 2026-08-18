from reeve import COURT_DAYS, Reeve, shared_out, still_to_keep


def test_the_days_kept_come_back_in_the_order_they_were_written_down():
    reeve = Reeve("ada")
    reeve.keep("Michaelmas")
    reeve.keep("Martinmas")

    assert reeve.days_kept() == ["Michaelmas", "Martinmas"]


def test_what_the_reeve_hands_out_is_a_copy_of_what_was_written_down():
    reeve = Reeve("ada")
    reeve.keep("Michaelmas")

    reeve.days_kept().append("Martinmas")

    assert reeve.days_kept() == ["Michaelmas"]


def test_the_year_still_to_keep_is_the_year_less_what_has_been_kept():
    reeve = Reeve("ada")
    reeve.keep("Midsummer")

    assert still_to_keep(reeve) == [day for day in COURT_DAYS if day != "Midsummer"]


def test_what_will_not_divide_evenly_still_comes_to_what_was_shared_out():
    shares = shared_out(100, 3)

    assert shares == [34, 33, 33]
    assert sum(shares) == 100
