from slugger import slugify, unique_slugs


def test_distinct_titles_are_simply_slugified():
    assert unique_slugs(["Hello World", "Weekly Report"]) == [
        "hello-world",
        "weekly-report",
    ]


def test_repeated_titles_get_numbered_suffixes():
    assert unique_slugs(["Note", "Note", "Note"]) == ["note", "note-2", "note-3"]


def test_a_literal_collision_with_a_numbered_variant_is_skipped():
    assert unique_slugs(["Report", "Report 2", "Report"]) == [
        "report",
        "report-2",
        "report-3",
    ]


def test_a_numbered_variant_taken_earlier_keeps_its_own_base():
    assert unique_slugs(["Report", "Report", "Report 2"]) == [
        "report",
        "report-2",
        "report-2-2",
    ]


def test_titles_without_alphanumerics_fall_back_to_untitled():
    assert unique_slugs(["???", "!!!"]) == ["untitled", "untitled-2"]


def test_an_empty_list_gives_an_empty_list():
    assert unique_slugs([]) == []


def test_existing_behaviour_is_preserved():
    assert slugify("Hello, World!") == "hello-world"
