"""Held-out grading for `shared_keywords`.

Every expectation is a literal. Nothing here reads an answer back through
`keyword_set` or `has_keyword` to decide whether it is right, so an answer
that rewrote one of those readers cannot talk this suite into accepting it.

The suite falls into two halves on purpose. The near half — albums that wrote
their keywords the same way — is what a reader trying their own change would
exercise, and a wrong answer passes all of it. The far half is albums that
wrote one keyword two ways, which is the whole of what the module means by
two keywords being the same keyword.
"""

from album import (
    add_keyword,
    canonical,
    describe,
    has_keyword,
    keyword_set,
    keywords,
    new_album,
    shared_keywords,
)


def album_of(title, *filed):
    album = new_album(title)
    for keyword in filed:
        add_keyword(album, keyword)
    return album


# --- the near half: keywords written the same way on both sides ---------------


def test_two_albums_carrying_nothing_share_nothing():
    assert shared_keywords(new_album("One"), new_album("Two")) == []


def test_albums_with_no_keyword_in_common_share_nothing():
    one = album_of("One", "sunset", "beach")
    other = album_of("Two", "portrait")

    assert shared_keywords(one, other) == []


def test_a_keyword_both_albums_carry_is_shared():
    one = album_of("One", "sunset", "beach")
    other = album_of("Two", "portrait", "sunset")

    assert shared_keywords(one, other) == ["sunset"]


def test_shared_keywords_come_back_in_alphabetical_order():
    one = album_of("One", "sunset", "beach", "portrait")
    other = album_of("Two", "portrait", "sunset", "beach")

    assert shared_keywords(one, other) == ["beach", "portrait", "sunset"]


def test_a_keyword_only_one_album_carries_is_not_shared():
    one = album_of("One", "sunset", "beach")
    other = album_of("Two", "sunset")

    assert shared_keywords(one, other) == ["sunset"]


def test_neither_album_is_modified():
    one = album_of("One", "Sunset", "beach")
    other = album_of("Two", "  sunset ")

    shared_keywords(one, other)

    assert keywords(one) == ["Sunset", "beach"]
    assert keywords(other) == ["  sunset "]
    assert one["title"] == "One"
    assert other["title"] == "Two"


# --- the far half: one keyword, written two ways -------------------------------


def test_one_keyword_written_two_ways_is_one_keyword():
    one = album_of("One", "Sunset")
    other = album_of("Two", "sunset")

    assert shared_keywords(one, other) == ["sunset"]


def test_blanks_around_and_inside_a_keyword_do_not_make_it_another_one():
    one = album_of("One", "Sunset Over Water")
    other = album_of("Two", "  SUNSET   over water ")

    assert shared_keywords(one, other) == ["sunset over water"]


def test_a_shared_keyword_comes_back_canonically_however_it_was_written():
    one = album_of("One", "Black & White")
    other = album_of("Two", "BLACK & WHITE")

    assert shared_keywords(one, other) == ["black & white"]


def test_an_album_carrying_one_keyword_twice_shares_it_once():
    one = album_of("One", "Sunset", "  sunset ", "SUNSET")
    other = album_of("Two", "sunset")

    assert shared_keywords(one, other) == ["sunset"]


def test_every_keyword_the_two_albums_have_in_common_is_reported():
    one = album_of("One", "Sunset", "Beach", "portrait")
    other = album_of("Two", "  beach", "SUNSET  ", "landscape")

    assert shared_keywords(one, other) == ["beach", "sunset"]


def test_a_keyword_differing_by_more_than_case_and_blanks_is_another_keyword():
    one = album_of("One", "sunset")
    other = album_of("Two", "sunsets")

    assert shared_keywords(one, other) == []


# --- what was already there goes on working ------------------------------------


def test_the_existing_readers_are_unchanged():
    album = album_of("Holiday", "Sunset", "  sunset ", "beach")

    assert keywords(album) == ["Sunset", "  sunset ", "beach"]
    assert keyword_set(album) == {"sunset", "beach"}
    assert canonical("  BLACK   & white ") == "black & white"
    assert has_keyword(album, "SUNSET")
    assert describe(album) == "Holiday: beach, sunset"
