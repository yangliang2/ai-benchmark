from spans import merge, total_length


def test_merge_collapses_overlaps():
    assert merge([(1, 3), (2, 5)]) == [(1, 5)]


def test_merge_collapses_touching_spans():
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_merge_sorts_and_drops_empty_spans():
    assert merge([(7, 8), (4, 4), (1, 2)]) == [(1, 2), (7, 8)]


def test_total_length_counts_overlaps_once():
    assert total_length([(0, 4), (2, 6)]) == 6
