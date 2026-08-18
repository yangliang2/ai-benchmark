from grades import Grade, price_of

NUTS = Grade("nuts", 96)


def test_a_warm_month_is_the_price_written_on_the_kind():
    assert price_of(NUTS, "jun") == 96


def test_a_cold_month_is_dearer_by_the_same_amount_for_every_kind():
    assert price_of(NUTS, "jan") == 110
    assert price_of(Grade("slack", 40), "jan") == 54


def test_the_kind_prints_as_it_was_made():
    assert repr(NUTS) == "Grade('nuts', 96)"
