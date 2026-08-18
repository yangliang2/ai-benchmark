from common import Pasture, gates_for, open_in


def test_a_cow_takes_up_four_gates_and_a_sheep_one():
    assert gates_for("cow") == 4
    assert gates_for("sheep") == 1


def test_a_kind_the_common_never_priced_is_refused_where_it_is_asked_for():
    try:
        gates_for("goat")
    except KeyError:
        return
    raise AssertionError("a goat has never been priced on this common")


def test_a_pasture_shut_for_the_quarter_is_not_open_for_grazing():
    pastures = [Pasture("the moor", "Midsummer"), Pasture("the ings", "Lammas")]

    assert [pasture.name for pasture in open_in(pastures, "Lammas")] == ["the ings"]
