"""How `digest` is graded: by what a digest has to be, not by one digest.

Which of the entries that could be left out are kept is the decision the
prompt deliberately leaves open — several digests satisfy the rules for the
same run and budget, and every one of them is a correct answer — so what is
checked is that the digest is the run in its own order with each left-out
stretch counted, that it fits the budget with gaps counted as places, that
everything which has to be kept is, and that nothing was left out which would
still have fitted.

The last of those is the one an editorial preference cannot argue with, and
it is measured here rather than read off the digest's own arithmetic: `places`
below counts what a digest keeping a given set of entries would run to, from
the run and nothing else. Nothing is read back through `stands_for` or
`must_keep` either, so a digest that arrived with a rewritten notion of what a
run holds cannot be graded against its own reading of it.
"""

from typing import NamedTuple

import pytest
from digest import Entry, Gap, digest

RUN = [
    Entry(1, "started", False),
    Entry(2, "loaded config", False),
    Entry(3, "cache warm", False),
    Entry(4, "disk full", True),
    Entry(5, "retrying", False),
    Entry(6, "retrying again", False),
    Entry(7, "recovered", True),
    Entry(8, "steady", False),
    Entry(9, "steady still", False),
    Entry(10, "steady yet", False),
    Entry(11, "stopping", False),
    Entry(12, "done", False),
]

# Everything in it has to be kept, so no budget above its length buys anything
# and no budget below its length is enough.
ALL_IMPORTANT = [Entry(at, f"step {at}", True) for at in range(1, 5)]

SHORT = [Entry(1, "only", False)]

PAIR = [Entry(1, "started", False), Entry(2, "done", False)]


class Case(NamedTuple):
    """One run, one budget, and what the rules settle about digesting it.

    `has_to_keep` is the positions of the entries that must survive whatever
    else does — the important ones and the two ends — written out rather than
    asked for. `whole` says the run fits the budget entire, which is the one
    case where the open decision has nothing left to decide.
    """

    entries: list
    budget: int
    has_to_keep: set
    whole: bool


CASES = {
    # 4 entries that have to stay and 3 stretches between them: 7 places is
    # the least a digest of this run can run to.
    "twelve-at-seven": Case(RUN, 7, {0, 3, 6, 11}, False),
    "twelve-at-eight": Case(RUN, 8, {0, 3, 6, 11}, False),
    "twelve-at-nine": Case(RUN, 9, {0, 3, 6, 11}, False),
    # One place short of the run itself, so exactly one stretch comes out and
    # it has to be a stretch of two.
    "twelve-at-eleven": Case(RUN, 11, {0, 3, 6, 11}, False),
    "twelve-at-twelve": Case(RUN, 12, {0, 3, 6, 11}, True),
    "twelve-at-twenty": Case(RUN, 20, {0, 3, 6, 11}, True),
    "all-important": Case(ALL_IMPORTANT, 4, {0, 1, 2, 3}, True),
    "short": Case(SHORT, 1, {0}, True),
    "pair": Case(PAIR, 2, {0, 1}, True),
}

NAMES = sorted(CASES)


def given(name):
    """One run, handed over as a list of its own, so that a solution which
    sorts or consumes what it was given fails the one rule about that and not
    the ones about something else."""
    return list(CASES[name].entries)


def kept_positions(digested):
    """Which positions of the run a digest keeps, read off the digest by
    walking it: an entry is one position, a gap is as many as it counts."""
    kept = set()
    at = 0
    for item in digested:
        if isinstance(item, Gap):
            at += item.dropped
        else:
            kept.add(at)
            at += 1
    return kept


def places(kept, total):
    """How many places a digest keeping exactly these positions runs to: one
    for each entry kept, and one for each stretch of the rest."""
    stretches = sum(
        1
        for position in range(total)
        if position not in kept and (position == 0 or position - 1 in kept)
    )
    return len(kept) + stretches


@pytest.mark.parametrize("name", NAMES)
def test_the_digest_is_the_run_in_its_own_order_with_the_rest_counted(name):
    """Which is three rules in one walk: the entries kept are the run's own,
    in the run's own order, and the gaps between them count exactly the
    entries that are missing, so the digest stands for the whole run."""
    entries = CASES[name].entries
    digested = digest(given(name), CASES[name].budget)

    at = 0
    for item in digested:
        if isinstance(item, Gap):
            assert item.dropped >= 1
            at += item.dropped
        else:
            assert at < len(entries)
            assert item == entries[at]
            at += 1

    assert at == len(entries)


@pytest.mark.parametrize("name", NAMES)
def test_a_stretch_left_out_is_one_gap_however_long_it_is(name):
    digested = list(digest(given(name), CASES[name].budget))

    for earlier, later in zip(digested, digested[1:]):
        assert not (isinstance(earlier, Gap) and isinstance(later, Gap))


@pytest.mark.parametrize("name", NAMES)
def test_the_digest_fits_the_budget_with_its_gaps_counted(name):
    assert len(digest(given(name), CASES[name].budget)) <= CASES[name].budget


@pytest.mark.parametrize("name", NAMES)
def test_everything_that_has_to_be_kept_is_kept(name):
    digested = digest(given(name), CASES[name].budget)

    assert CASES[name].has_to_keep <= kept_positions(digested)


@pytest.mark.parametrize("name", NAMES)
def test_nothing_was_left_out_that_would_still_have_fitted(name):
    """The clause that rules out the answer the arithmetic hands over — leave
    out everything that may be left out — and the one a preference cannot
    argue with: for each entry the digest dropped, a digest keeping that one
    as well would have run past the budget."""
    case = CASES[name]
    kept = kept_positions(digest(given(name), case.budget))

    for position in range(len(case.entries)):
        if position not in kept:
            assert places(kept | {position}, len(case.entries)) > case.budget


@pytest.mark.parametrize("name", [name for name in NAMES if CASES[name].whole])
def test_a_run_that_fits_is_kept_whole_with_no_gaps_in_it(name):
    assert list(digest(given(name), CASES[name].budget)) == CASES[name].entries


@pytest.mark.parametrize("budget", [0, 1, 7])
def test_an_empty_run_gives_an_empty_digest(budget):
    assert list(digest([], budget)) == []


@pytest.mark.parametrize("name", NAMES)
def test_the_run_the_caller_passed_in_is_left_alone(name):
    entries = given(name)

    digest(entries, CASES[name].budget)

    assert entries == CASES[name].entries


@pytest.mark.parametrize("budget", [6, 4, 0])
def test_a_budget_too_small_to_hold_a_digest_is_refused(budget):
    """Four entries have to be kept and three stretches lie between them, so
    seven places is the least this run can be shown in."""
    with pytest.raises(ValueError):
        digest(list(RUN), budget)


def test_a_budget_short_of_a_run_that_is_all_important_is_refused():
    with pytest.raises(ValueError):
        digest(list(ALL_IMPORTANT), 3)


def test_a_run_of_one_needs_one_place():
    with pytest.raises(ValueError):
        digest(list(SHORT), 0)
