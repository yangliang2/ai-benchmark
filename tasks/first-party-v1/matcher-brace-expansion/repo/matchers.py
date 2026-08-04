"""Shell-style name matching with * and ?."""


def match(pattern, name):
    """Whether name matches pattern, where * matches any run of characters
    (possibly empty) and ? matches exactly one character."""
    return _match(pattern, 0, name, 0)


def _match(pattern, pattern_index, name, name_index):
    if pattern_index == len(pattern):
        return name_index == len(name)
    character = pattern[pattern_index]
    if character == "*":
        return any(
            _match(pattern, pattern_index + 1, name, skip_to)
            for skip_to in range(name_index, len(name) + 1)
        )
    if name_index == len(name):
        return False
    if character == "?" or character == name[name_index]:
        return _match(pattern, pattern_index + 1, name, name_index + 1)
    return False


def filter_names(pattern, names):
    """The names matching pattern, keeping their order."""
    return [name for name in names if match(pattern, name)]
