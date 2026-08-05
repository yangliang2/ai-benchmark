from cartons import Item, fits, manifest, total_weight


def test_an_empty_carton_weighs_nothing():
    assert total_weight([]) == 0


def test_a_cartons_weight_is_its_items_added_up():
    assert total_weight([Item("a", 300), Item("b", 250)]) == 550


def test_an_item_fits_while_the_capacity_is_not_used_up():
    assert fits([Item("a", 300)], Item("b", 700), 1000)


def test_an_item_that_would_go_over_the_capacity_does_not_fit():
    assert not fits([Item("a", 300)], Item("b", 701), 1000)


def test_the_manifest_numbers_cartons_from_one():
    assert manifest([[Item("a", 300)], [Item("b", 250), Item("c", 100)]]) == [
        "carton 1: 1 item(s), 300g",
        "carton 2: 2 item(s), 350g",
    ]
