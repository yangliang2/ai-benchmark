from wordcount import top_words, word_counts


def test_returns_the_most_frequent_words_first():
    assert top_words("a b b c c c", 2) == ["c", "b"]


def test_breaks_ties_alphabetically():
    assert top_words("pear apple pear apple fig", 2) == ["apple", "pear"]


def test_n_larger_than_the_vocabulary_returns_every_word():
    assert top_words("b a", 5) == ["a", "b"]


def test_empty_text_returns_an_empty_list():
    assert top_words("", 3) == []


def test_existing_behaviour_is_preserved():
    assert word_counts("a b a") == {"a": 2, "b": 1}
