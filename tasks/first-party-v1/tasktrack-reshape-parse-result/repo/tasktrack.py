"""Parsing one-line task entries.

A line is words: an "x" first word marks the task done, "!n" sets the
priority (default 3), "#word" adds a tag, and the remaining words are the
title, in order.
"""


def parse_task(line):
    """(title, priority, tags, done) for one task line."""
    words = line.split()
    done = bool(words) and words[0] == "x"
    if done:
        words = words[1:]
    title_words = []
    priority = 3
    tags = []
    for word in words:
        if word.startswith("!") and word[1:].isdigit():
            priority = int(word[1:])
        elif word.startswith("#") and len(word) > 1:
            tags.append(word[1:])
        else:
            title_words.append(word)
    return " ".join(title_words), priority, tags, done
