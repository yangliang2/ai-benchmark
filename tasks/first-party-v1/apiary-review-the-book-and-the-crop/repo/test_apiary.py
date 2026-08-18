from apiary import STANDS, Hive, Yard, jars, on_the_stand, standing, stands_in_use


def test_a_hive_is_found_however_the_mark_was_written_down():
    hives = [Hive("WB2", "the orchard", 11)]

    assert standing(hives, " wb2 ").frames == 11
    assert standing(hives, "WB3") is None


def test_the_hives_of_one_stand_come_back_in_the_order_they_were_made_up():
    hives = [
        Hive("WB2", "the orchard", 11),
        Hive("WB5", "the paddock", 10),
        Hive("WB7", "the orchard", 11),
    ]

    assert [hive.mark for hive in on_the_stand(hives, "the orchard")] == ["WB2", "WB7"]
    assert stands_in_use(hives) == 2


def test_the_yard_says_what_it_was_laid_out_with():
    yard = Yard("the glebe", 6)

    assert (yard.whose, yard.stands) == ("the glebe", 6)
    assert STANDS[0] == "the orchard"


def test_a_crop_is_put_up_in_whole_jars():
    assert jars(7) == 3
    assert jars(1) == 0
