from ringers import Band, Ringer


def test_the_band_holds_its_ringers_in_the_order_they_were_taken_on():
    band = Band()
    band.take_on(Ringer("ann", "treble"))
    band.take_on(Ringer("bea", "tenor"))

    assert [each.who for each in band.ringers] == ["ann", "bea"]


def test_the_band_takes_a_second_of_one_name_as_it_is_given():
    band = Band()
    band.take_on(Ringer("ann", "treble"))
    band.take_on(Ringer("ann", "third"))

    assert [each.bell for each in band.ringers] == ["treble", "third"]


def test_everyone_standing_at_one_bell_comes_back_in_the_order_they_were_taken_on():
    band = Band()
    band.take_on(Ringer("ann", "treble"))
    band.take_on(Ringer("bea", "tenor"))
    band.take_on(Ringer("cal", "treble"))

    assert [each.who for each in band.standing_at("treble")] == ["ann", "cal"]
