"""Word-frequency helpers over plain text."""

import re

_WORD = re.compile(r"[a-z0-9']+")


def words(text):
    """Split text into lowercase words, dropping punctuation and whitespace."""
    return _WORD.findall(text.lower())


def word_counts(text):
    """Count how often each word occurs in text."""
    counts = {}
    for word in words(text):
        counts[word] = counts.get(word, 0) + 1
    return counts


def top_words(text, n):
    """The n most frequent words, most frequent first, ties alphabetical."""
    counts = word_counts(text)
    ordered = sorted(counts, key=lambda word: (-counts[word], word))
    return ordered[:n]
