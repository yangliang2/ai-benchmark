from show import Class, Section, named, under


def test_the_schedule_answers_to_the_name_of_a_class():
    peas = Class("six pods of peas", "vegetables")

    assert named([peas], "six pods of peas") is peas
    assert named([peas], "six pods of beans") is None


def test_a_section_holds_its_classes_in_the_order_the_schedule_lists_them():
    classes = [
        Class("six pods of peas", "vegetables"),
        Class("a vase of sweet peas", "flowers"),
        Class("three onions", "vegetables"),
    ]

    assert [cls.name for cls in under(classes, "vegetables")] == [
        "six pods of peas",
        "three onions",
    ]


def test_a_section_is_judged_in_a_tent():
    assert Section("flowers", "the big tent").tent == "the big tent"
