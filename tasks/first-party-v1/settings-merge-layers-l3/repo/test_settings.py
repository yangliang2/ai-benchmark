from settings import flatten, set_value, value_at


def test_flatten_gives_nested_sections_dotted_paths():
    assert flatten({"db": {"host": "localhost", "port": 5432}}) == {
        "db.host": "localhost",
        "db.port": 5432,
    }


def test_flatten_treats_a_list_as_a_value():
    assert flatten({"db": {"hosts": ["a", "b"]}}) == {"db.hosts": ["a", "b"]}


def test_value_at_walks_a_dotted_path():
    assert value_at({"db": {"pool": {"size": 5}}}, "db.pool.size") == 5


def test_value_at_falls_back_when_nothing_is_set_there():
    assert value_at({"db": {}}, "db.port", 5432) == 5432


def test_set_value_leaves_the_settings_it_was_given_alone():
    settings = {"db": {"host": "localhost"}}

    updated = set_value(settings, "db.port", 5432)

    assert updated == {"db": {"host": "localhost", "port": 5432}}
    assert settings == {"db": {"host": "localhost"}}


def test_set_value_returns_sections_of_its_own():
    settings = {"db": {"host": "localhost"}}

    set_value(settings, "db.port", 5432)["db"]["host"] = "elsewhere"

    assert settings == {"db": {"host": "localhost"}}
