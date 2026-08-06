"""How `merge_runs` is graded: against the runs the prompt spells out.

Every decision is stated — which run goes first at a shared moment, what makes
two entries one entry, what the shared list holds and in whose order, which
mistake is refused — so the expected runs are written out here in full. This
is the zero-crux control the budget task is read against.
"""

import pytest
from digest import Entry, merge_runs

WORKER = [
    Entry(1, "started", False),
    Entry(3, "retrying", False),
    Entry(6, "done", False),
]

SUPERVISOR = [
    Entry(2, "warned", False),
    Entry(3, "retrying", False),
    Entry(5, "retrying", False),
]


def test_the_two_runs_come_back_as_one_in_time_order():
    merged, _ = merge_runs(WORKER, SUPERVISOR)

    assert list(merged) == [
        Entry(1, "started", False),
        Entry(2, "warned", False),
        Entry(3, "retrying", False),
        Entry(5, "retrying", False),
        Entry(6, "done", False),
    ]


def test_the_same_message_logged_again_later_is_a_different_entry():
    """`retrying` at 3 is in both runs and is one entry; `retrying` at 5 is in
    the supervisor's run alone and is another."""
    merged, _ = merge_runs(WORKER, SUPERVISOR)

    assert [entry.at for entry in merged if entry.text == "retrying"] == [3, 5]


def test_what_the_two_runs_had_in_common_comes_back_in_the_left_runs_order():
    _, shared = merge_runs(WORKER, SUPERVISOR)

    assert list(shared) == [Entry(3, "retrying", False)]


def test_runs_with_nothing_in_common_share_nothing():
    merged, shared = merge_runs([Entry(1, "started", False)], [Entry(2, "done", False)])

    assert list(merged) == [Entry(1, "started", False), Entry(2, "done", False)]
    assert list(shared) == []


def test_at_a_shared_moment_the_left_run_comes_first():
    left = [Entry(4, "worker says", False)]
    right = [Entry(4, "supervisor says", False)]

    merged, shared = merge_runs(left, right)

    assert list(merged) == [
        Entry(4, "worker says", False),
        Entry(4, "supervisor says", False),
    ]
    assert list(shared) == []


def test_the_same_message_at_the_same_moment_marked_differently_is_two_entries():
    left = [Entry(7, "note", True)]
    right = [Entry(7, "note", False)]

    merged, shared = merge_runs(left, right)

    assert list(merged) == [Entry(7, "note", True), Entry(7, "note", False)]
    assert list(shared) == []


def test_an_entry_of_the_right_run_before_everything_on_the_left():
    merged, _ = merge_runs([Entry(9, "late", False)], [Entry(2, "early", False)])

    assert list(merged) == [Entry(2, "early", False), Entry(9, "late", False)]


def test_merging_with_an_empty_run_gives_back_the_other_one():
    assert list(merge_runs(WORKER, [])[0]) == WORKER
    assert list(merge_runs([], SUPERVISOR)[0]) == SUPERVISOR


def test_merging_two_empty_runs_gives_an_empty_run():
    merged, shared = merge_runs([], [])

    assert list(merged) == []
    assert list(shared) == []


def test_the_runs_the_caller_passed_in_are_left_alone():
    worker, supervisor = list(WORKER), list(SUPERVISOR)

    merge_runs(worker, supervisor)

    assert (worker, supervisor) == (WORKER, SUPERVISOR)


@pytest.mark.parametrize(
    "out_of_order",
    [
        [Entry(5, "later", False), Entry(2, "earlier", False)],
        [Entry(1, "a", False), Entry(4, "b", False), Entry(3, "c", False)],
    ],
)
def test_a_run_that_is_not_in_time_order_is_refused(out_of_order):
    with pytest.raises(ValueError):
        merge_runs(out_of_order, SUPERVISOR)
    with pytest.raises(ValueError):
        merge_runs(WORKER, out_of_order)
