"""Shell-style name matching with * and ?."""


def match(pattern, name):
    """Whether name matches pattern, where * matches any run of characters
    (possibly empty) and ? matches exactly one character."""
    return _match(pattern, 0, name, 0)


def _match(pattern, p, name, n):
    if p == len(pattern):
        return n == len(name)
    character = pattern[p]
    if character == "*":
        return any(
            _match(pattern, p + 1, name, i) for i in range(n, len(name) + 1)
        )
    if n == len(name):
        return False
    if character == "?" or character == name[n]:
        return _match(pattern, p + 1, name, n + 1)
    return False


def filter_names(pattern, names):
    """The names matching pattern, keeping their order."""
    return [name for name in names if match(pattern, name)]
