"""Shell-style name matching with * and ?, plus brace expansion."""


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


def expand(pattern):
    """Brace-expand pattern into the list of patterns it stands for."""
    results, _ = _expand_sequence(pattern, 0, top_level=True)
    return results


def _expand_sequence(pattern, position, *, top_level):
    """Expand up to the end of the pattern (at top level) or up to the ','
    or '}' that ends an alternative (inside a group)."""
    results = [""]
    while position < len(pattern):
        character = pattern[position]
        if character == "\\" and position + 1 < len(pattern):
            results = [result + pattern[position + 1] for result in results]
            position += 2
        elif character == "{":
            alternatives, position = _expand_group(pattern, position + 1)
            results = [
                result + alternative
                for result in results
                for alternative in alternatives
            ]
        elif character == "}" or (character == "," and not top_level):
            if top_level:
                raise ValueError("'}' with no open group")
            return results, position
        else:
            results = [result + character for result in results]
            position += 1
    if not top_level:
        raise ValueError("unclosed '{'")
    return results, position


def _expand_group(pattern, position):
    """Expand the alternatives of the group opened just before position,
    returning them and the position after the closing '}'."""
    alternatives = []
    while True:
        expanded, position = _expand_sequence(pattern, position, top_level=False)
        alternatives.extend(expanded)
        if pattern[position] == ",":
            position += 1
        else:
            return alternatives, position + 1
