from caretaker import USUAL_LOCK_UP, hand_back, lock_up_at


def test_a_day_with_an_hour_of_its_own_is_locked_at_that_hour():
    assert lock_up_at({"friday": 23}, "friday") == 23


def test_a_day_with_no_hour_of_its_own_is_locked_at_the_usual_one():
    assert lock_up_at({"friday": 23}, "monday") == USUAL_LOCK_UP


def test_an_hour_of_nothing_is_midnight_and_not_the_usual_hour():
    assert lock_up_at({"sunday": 0}, "sunday") == 0


def test_every_key_one_person_holds_comes_back_together():
    held = ["ada", "ada", "bob"]

    assert hand_back(held, "ada") == 2
    assert held == ["bob"]
