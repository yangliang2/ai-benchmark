from spans import free, merge


def test_an_uncovered_window_is_entirely_free():
    assert free([], (0, 10)) == [(0, 10)]


def test_gaps_between_spans_inside_the_window():
    assert free([(2, 4), (6, 8)], (0, 10)) == [(0, 2), (4, 6), (8, 10)]


def test_unsorted_overlapping_spans_are_handled():
    assert free([(6, 8), (2, 4), (3, 5)], (0, 10)) == [(0, 2), (5, 6), (8, 10)]


def test_spans_reaching_past_the_window_are_clipped():
    assert free([(-5, 3), (8, 15)], (0, 10)) == [(3, 8)]


def test_a_fully_covered_window_has_no_free_room():
    assert free([(0, 4), (4, 10)], (0, 10)) == []


def test_a_span_touching_the_window_edge_leaves_no_sliver():
    assert free([(0, 5)], (0, 10)) == [(5, 10)]


def test_empty_spans_cover_nothing():
    assert free([(3, 3)], (2, 5)) == [(2, 5)]


def test_an_empty_window_is_never_free():
    assert free([(0, 2)], (4, 4)) == []


def test_existing_behaviour_is_preserved():
    assert merge([(1, 3), (2, 5), (7, 8)]) == [(1, 5), (7, 8)]
