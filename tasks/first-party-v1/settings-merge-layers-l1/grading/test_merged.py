from settings import flatten, merged, set_value


def test_no_layers_at_all_are_empty_settings():
    assert merged([]) == {}


def test_the_last_layer_that_sets_a_key_wins():
    assert merged([{"port": 5432}, {"port": 6543}]) == {"port": 6543}


def test_a_key_only_one_layer_sets_is_kept():
    assert merged([{"host": "localhost"}, {"port": 6543}]) == {
        "host": "localhost",
        "port": 6543,
    }


def test_a_section_is_merged_key_by_key_not_replaced():
    assert merged([
        {"db": {"host": "localhost", "port": 5432}},
        {"db": {"port": 6543}},
    ]) == {"db": {"host": "localhost", "port": 6543}}


def test_sections_are_merged_at_every_depth():
    assert merged([
        {"db": {"pool": {"size": 5, "timeout": 30}}},
        {"db": {"pool": {"size": 20}}},
    ]) == {"db": {"pool": {"size": 20, "timeout": 30}}}


def test_a_value_takes_the_place_of_a_section():
    assert merged([{"db": {"host": "localhost"}}, {"db": "off"}]) == {"db": "off"}


def test_a_section_takes_the_place_of_a_value():
    assert merged([{"db": "off"}, {"db": {"host": "localhost"}}]) == {
        "db": {"host": "localhost"}
    }


def test_lists_are_values_and_replace_rather_than_combine():
    assert merged([{"hosts": ["a", "b"]}, {"hosts": ["c"]}]) == {"hosts": ["c"]}


def test_layers_apply_in_the_order_they_are_given():
    assert merged([
        {"db": {"host": "localhost", "port": 5432}},
        {"db": {"port": 6543}},
        {"db": {"host": "prod"}},
    ]) == {"db": {"host": "prod", "port": 6543}}


def test_no_layer_is_modified_and_the_result_holds_sections_of_its_own():
    base = {"db": {"host": "localhost", "pool": {"size": 5}}}
    override = {"db": {"port": 6543}}

    settings = merged([base, override])
    settings["db"]["host"] = "elsewhere"
    settings["db"]["pool"]["size"] = 99

    assert base == {"db": {"host": "localhost", "pool": {"size": 5}}}
    assert override == {"db": {"port": 6543}}


def test_a_lone_layer_is_copied_rather_than_handed_straight_back():
    layer = {"db": {"host": "localhost"}}

    settings = merged([layer])

    assert settings == {"db": {"host": "localhost"}}
    settings["db"]["host"] = "elsewhere"
    assert layer == {"db": {"host": "localhost"}}


def test_existing_behaviour_is_preserved():
    settings = merged([{"db": {"host": "localhost"}}, {"db": {"port": 6543}}])

    assert flatten(settings) == {"db.host": "localhost", "db.port": 6543}
    assert set_value({"db": {}}, "db.port", 5432) == {"db": {"port": 5432}}
