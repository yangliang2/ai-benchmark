from points import PLACES, champion


def test_a_first_is_worth_four_and_a_third_two():
    assert PLACES["first"] == 4
    assert PLACES["second"] == 3
    assert PLACES["third"] == 2


def test_the_cup_goes_to_the_exhibitor_with_the_most():
    assert champion({"ada": 12, "bob": 15, "cid": 4}) == "bob"


def test_the_cup_stays_on_the_shelf_where_nobody_has_a_point():
    assert champion({}) is None
    assert champion({"ada": 0}) is None
