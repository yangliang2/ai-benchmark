from digest import Entry, Gap, entries_only, must_keep, render, stands_for

RUN = [
    Entry(1, "started", False),
    Entry(2, "loaded config", False),
    Entry(3, "disk full", True),
    Entry(4, "retrying", False),
    Entry(5, "done", False),
]

DIGESTED = [RUN[0], Gap(1), RUN[2], Gap(1), RUN[4]]


def test_the_entries_of_a_digest_are_the_items_that_are_not_gaps():
    assert entries_only(DIGESTED) == [RUN[0], RUN[2], RUN[4]]


def test_a_digest_stands_for_what_it_keeps_and_what_its_gaps_count():
    assert stands_for(DIGESTED) == 5


def test_a_run_with_nothing_left_out_stands_for_itself():
    assert stands_for(RUN) == 5


def test_nothing_stands_for_nothing():
    assert stands_for([]) == 0
    assert entries_only([]) == []


def test_what_has_to_be_kept_is_the_important_ones_and_the_two_ends():
    assert must_keep(RUN) == [RUN[0], RUN[2], RUN[4]]


def test_an_important_entry_at_an_end_is_not_counted_twice():
    assert must_keep([Entry(1, "started", True), Entry(2, "done", False)]) == [
        Entry(1, "started", True),
        Entry(2, "done", False),
    ]


def test_a_run_of_one_has_one_entry_that_has_to_be_kept():
    assert must_keep([RUN[0]]) == [RUN[0]]


def test_an_empty_run_has_nothing_that_has_to_be_kept():
    assert must_keep([]) == []


def test_the_rendering_says_how_many_entries_a_gap_stands_in_for():
    assert render(DIGESTED) == [
        "1 started",
        "... 1 more",
        "3 disk full",
        "... 1 more",
        "5 done",
    ]
