from deliveries import Delivery, House, Round
from grades import Grade
from statement import Statement, Terms

NUTS = Grade("nuts", 96)
SLACK = Grade("slack", 40)

MILL = House("Mill Cottage", 1)
FARM = House("Bostock Farm", 6)

ROUND = Round([
    Delivery(MILL, "jun", NUTS, 6),
    Delivery(FARM, "jun", NUTS, 6),
    Delivery(MILL, "jan", NUTS, 4, empties=3),
    Delivery(MILL, "jan", SLACK, 2),
    Delivery(MILL, "may", SLACK, 1),
])

DEMANDS = Statement(ROUND)


def test_a_plain_month_is_the_sacks_at_what_the_kind_fetches():
    assert DEMANDS.made_up(MILL, "jun") == 576


def test_a_cold_month_carries_the_cold_price():
    assert DEMANDS.made_up(MILL, "jan") == 4 * 110 + 2 * 54 - 3 * 2


def test_a_house_out_along_the_lane_carries_the_extra():
    assert DEMANDS.made_up(FARM, "jun") == 576 + 30


def test_a_house_that_had_next_to_nothing_is_asked_the_least():
    assert DEMANDS.made_up(MILL, "may") == 250


def test_a_month_with_nothing_in_it_asks_for_nothing():
    assert DEMANDS.made_up(FARM, "jan") == 0


def test_the_season_is_every_month_the_house_had_anything():
    assert DEMANDS.season(MILL) == 576 + (4 * 110 + 2 * 54 - 3 * 2) + 250


def test_another_set_of_terms_is_obeyed():
    keener = Statement(ROUND, Terms(carriage=0, allowed_back=5, least=0, near_miles=3))

    assert keener.made_up(FARM, "jun") == 576
    assert keener.made_up(MILL, "may") == 40
