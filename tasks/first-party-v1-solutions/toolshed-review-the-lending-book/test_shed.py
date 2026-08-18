from shed import Tool, by_rack, on_rack


def tools():
    return [
        Tool("hand saw", "wall"),
        Tool("lump hammer", "bench"),
        Tool("tin snips", "wall"),
    ]


def test_a_rack_has_its_own_tools_in_the_order_the_rack_list_has_them():
    assert [tool.label for tool in on_rack(tools(), "wall")] == [
        "hand saw",
        "tin snips",
    ]


def test_a_rack_with_two_tools_on_it_collects_both_of_them():
    racked = by_rack(tools())

    assert sorted(racked) == ["bench", "wall"]
    assert [tool.label for tool in racked["wall"]] == ["hand saw", "tin snips"]
