from album import (
    add_keyword,
    canonical,
    describe,
    has_keyword,
    keyword_set,
    keywords,
    new_album,
)


def test_a_new_album_carries_nothing():
    assert keywords(new_album("Holiday")) == []


def test_a_keyword_is_filed_as_it_was_written():
    album = new_album("Holiday")

    add_keyword(album, "Black & White")

    assert keywords(album) == ["Black & White"]


def test_keywords_come_back_in_filing_order():
    album = new_album("Holiday")

    add_keyword(album, "sunset")
    add_keyword(album, "beach")

    assert keywords(album) == ["sunset", "beach"]


def test_keywords_hands_back_a_list_of_its_own():
    album = new_album("Holiday")
    add_keyword(album, "sunset")

    keywords(album).append("beach")

    assert keywords(album) == ["sunset"]


def test_canonical_folds_case_trims_and_closes_up_blanks():
    assert canonical("  BLACK   & white ") == "black & white"


def test_keyword_set_answers_canonically():
    album = new_album("Holiday")
    add_keyword(album, "Sunset Over Water")

    assert keyword_set(album) == {"sunset over water"}


def test_two_spellings_of_one_keyword_are_one_keyword():
    album = new_album("Holiday")

    add_keyword(album, "Sunset")
    add_keyword(album, "  sunset ")

    assert keywords(album) == ["Sunset", "  sunset "]
    assert keyword_set(album) == {"sunset"}


def test_has_keyword_ignores_how_either_was_written():
    album = new_album("Holiday")
    add_keyword(album, "Black & White")

    assert has_keyword(album, "  black & WHITE ")
    assert not has_keyword(album, "colour")


def test_describe_lists_what_is_carried_canonically_and_in_order():
    album = new_album("Holiday")
    add_keyword(album, "Sunset")
    add_keyword(album, "beach")

    assert describe(album) == "Holiday: beach, sunset"


def test_describe_says_so_when_nothing_is_carried():
    assert describe(new_album("Holiday")) == "Holiday: nothing"
