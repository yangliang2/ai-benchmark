from wordcount import word_counts, words


def test_words_are_lowercased_and_stripped_of_punctuation():
    assert words("The the, CAT!") == ["the", "the", "cat"]


def test_word_counts_totals_each_word():
    assert word_counts("a b a") == {"a": 2, "b": 1}


def test_word_counts_of_empty_text_is_empty():
    assert word_counts("") == {}
