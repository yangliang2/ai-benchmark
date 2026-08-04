from matchers import filter_names, match


def test_star_matches_any_run_of_characters():
    assert match("*.txt", "notes.txt")
    assert not match("*.txt", "notes.md")


def test_question_mark_matches_exactly_one_character():
    assert match("?.txt", "a.txt")
    assert not match("?.txt", "ab.txt")


def test_literals_must_match_exactly():
    assert match("notes.txt", "notes.txt")
    assert not match("notes.txt", "notes.txt.bak")


def test_filter_names_keeps_order():
    names = ["b.txt", "a.md", "a.txt"]
    assert filter_names("*.txt", names) == ["b.txt", "a.txt"]
