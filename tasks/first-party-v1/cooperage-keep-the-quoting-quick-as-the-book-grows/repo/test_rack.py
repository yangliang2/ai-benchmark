from gauging import Gauge
from rack import Cask, Rack

RACK = [
    Cask("pin", 15, 20),
    Cask("firkin", 20, 23),
    Cask("kilderkin", 25, 29),
    Cask("barrel", 30, 40),
]


def test_each_order_gets_the_snuggest_cask():
    rack = Rack(RACK, Gauge())

    assert rack.quote([10, 4]) == [(10, "kilderkin"), (4, "pin")]


def test_an_order_too_big_for_the_rack_is_refused():
    assert Rack(RACK, Gauge()).cask_for(99) is None


def test_the_gauge_tallies_its_gaugings():
    gauge = Gauge()

    assert gauge.gaugings == 0
    assert gauge.measure(Cask("firkin", 20, 23)) == 9
    assert gauge.gaugings == 1
