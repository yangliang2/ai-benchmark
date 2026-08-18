from deliveries import Delivery, House, Round
from grades import Grade

NUTS = Grade("nuts", 96)
SLACK = Grade("slack", 40)

MILL = House("Mill Cottage", 1)
FARM = House("Bostock Farm", 6)

ROUND = Round([
    Delivery(MILL, "jun", NUTS, 2),
    Delivery(FARM, "jun", SLACK, 5),
    Delivery(MILL, "jan", NUTS, 4, empties=2),
    Delivery(MILL, "jan", SLACK, 1),
])


def test_only_that_house_in_that_month_comes_back():
    assert [delivery.sacks for delivery in ROUND.at(MILL, "jan")] == [4, 1]


def test_a_month_a_house_had_nothing_comes_back_bare():
    assert ROUND.at(FARM, "jan") == []


def test_the_months_come_back_in_the_order_they_were_written_down():
    assert ROUND.months(MILL) == ["jun", "jan"]


def test_a_house_is_the_house_of_that_name_and_not_another():
    assert ROUND.months(House("Mill Cottage", 1)) == ["jun", "jan"]
