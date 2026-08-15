from handins import Handin, days_in, in_order, ticket_for

TODAY = 200

UMBRELLA = Handin("umbrella", 199)
COAT = Handin("coat", 40)
KEYS = Handin("keys", 190, claimed=True)
CAKE = Handin("cake", 200, keeps=False)


def test_a_handin_is_what_it_is_and_the_day_it_came_in():
    assert repr(UMBRELLA) == "Handin('umbrella', 199, keeps=True, claimed=False)"
    assert UMBRELLA == Handin("umbrella", 199)
    assert UMBRELLA != Handin("umbrella", 198)


def test_two_handins_alike_in_every_way_are_one_thing_to_a_set():
    assert len({CAKE, Handin("cake", 200, keeps=False)}) == 1


def test_the_desk_deals_with_what_came_in_earliest_first():
    assert in_order([UMBRELLA, COAT, KEYS]) == [COAT, KEYS, UMBRELLA]


def test_two_handed_in_on_one_day_keep_the_order_they_were_written_in():
    tin = Handin("tin", 200)
    assert in_order([CAKE, tin]) == [CAKE, tin]
    assert in_order([tin, CAKE]) == [tin, CAKE]


def test_how_long_the_office_has_had_a_thing_is_a_subtraction():
    assert days_in(COAT, TODAY) == 160
    assert days_in(UMBRELLA, TODAY) == 1


def test_the_ticket_on_something_asked_for_says_so():
    assert ticket_for(KEYS, TODAY) == "keys - asked for"


def test_the_ticket_on_something_in_today_says_so():
    assert ticket_for(Handin("scarf", TODAY), TODAY) == "scarf - in today"


def test_the_ticket_on_anything_else_counts_the_days():
    assert ticket_for(COAT, TODAY) == "coat - 160 days in"
