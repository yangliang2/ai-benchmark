"""Picking records out of a list.

A record is a dict from field name to value. Values are numbers, strings,
booleans, or None — and None means the field is there but its value is not
known.

An unknown value is the reason nothing here answers with a plain bool.
Comparing something nobody knows against anything is neither true nor false,
so `compare` answers with one of TRUE, FALSE and UNKNOWN, and a caller
picking records out keeps only the ones that came back TRUE.
"""

TRUE = "true"
FALSE = "false"
UNKNOWN = "unknown"

OPERATORS = ("=", "!=", "<", "<=", ">", ">=")


def field_names(records):
    """Every field name any of these records carries, in name order."""
    names = set()
    for record in records:
        names.update(record)
    return sorted(names)


def kind_of(value):
    """Which of the four kinds of value this is.

    Booleans are their own kind and not a kind of number, however Python
    happens to spell them: True is not 1 here, and neither is it greater
    than 0.
    """
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    raise ValueError(f"not a value a record may hold: {value!r}")


def compare(left, operator, right):
    """Compare two values, answering TRUE, FALSE or UNKNOWN.

    An unknown value compares to nothing: every operator answers UNKNOWN.

    Two values of different kinds are never equal and are never ordered, so
    `=` answers FALSE and `!=` answers TRUE, while `<`, `<=`, `>` and `>=`
    raise ValueError. Within a kind: numbers compare numerically, strings
    compare character by character, and FALSE sorts before TRUE.
    """
    if operator not in OPERATORS:
        raise ValueError(f"no such operator: {operator!r}")
    left_kind, right_kind = kind_of(left), kind_of(right)
    if left_kind == "unknown" or right_kind == "unknown":
        return UNKNOWN
    if left_kind != right_kind:
        if operator == "=":
            return FALSE
        if operator == "!=":
            return TRUE
        raise ValueError(
            f"cannot order a {left_kind} against a {right_kind}")
    if left_kind == "boolean":
        left, right = int(left), int(right)
    if operator == "=":
        held = left == right
    elif operator == "!=":
        held = left != right
    elif operator == "<":
        held = left < right
    elif operator == "<=":
        held = left <= right
    elif operator == ">":
        held = left > right
    else:
        held = left >= right
    return TRUE if held else FALSE


def select_equal(records, field, value):
    """The records whose `field` is known to equal `value`, in the order they
    were given. A record without the field, or with it unknown, is not one of
    them."""
    kept = []
    for record in records:
        if field not in record:
            continue
        if compare(record[field], "=", value) == TRUE:
            kept.append(record)
    return kept


# --- the filter language ------------------------------------------------------

KEYWORDS = ("and", "or", "not", "is", "null", "in", "between", "true", "false")

_SYMBOLS = ("!=", "<=", ">=", "=", "<", ">", "(", ")", ",")


def select(records, expression):
    """The records the expression is TRUE of, in the order they were given.

    Neither the list nor the records in it are copied or changed: what comes
    back holds the very objects that went in.
    """
    tokens = _tokenize(expression)
    known = set(field_names(records))
    tree, rest = _parse_expression(tokens, 0)
    if rest != len(tokens):
        raise ValueError("expression does not end where it stops making "
                         f"sense: {expression!r}")
    if not records:
        return []
    for name in sorted(_fields_used(tree)):
        if name not in known:
            raise ValueError(f"no record has a field called {name!r}")
    return [record for record in records if _hold(tree, record) == TRUE]


def _tokenize(expression):
    tokens = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue
        if char == "'":
            text, index = _read_string(expression, index)
            tokens.append(("string", text))
            continue
        if char.isdigit() or (
                char == "-" and index + 1 < len(expression)
                and expression[index + 1].isdigit()):
            number, index = _read_number(expression, index)
            tokens.append(("number", number))
            continue
        if char.isalpha() or char == "_":
            word, index = _read_word(expression, index)
            if word.lower() in KEYWORDS:
                tokens.append((word.lower(), word.lower()))
            else:
                tokens.append(("field", word))
            continue
        for symbol in _SYMBOLS:
            if expression.startswith(symbol, index):
                tokens.append((symbol, symbol))
                index += len(symbol)
                break
        else:
            raise ValueError(
                f"this belongs to no token: {expression[index]!r}")
    return tokens


def _read_string(expression, index):
    index += 1
    letters = []
    while True:
        if index >= len(expression):
            raise ValueError("a text literal was never closed")
        char = expression[index]
        if char == "'":
            if expression.startswith("''", index):
                letters.append("'")
                index += 2
                continue
            return "".join(letters), index + 1
        letters.append(char)
        index += 1


def _read_number(expression, index):
    start = index
    if expression[index] == "-":
        index += 1
    digits = index
    while index < len(expression) and expression[index].isdigit():
        index += 1
    if index == digits:
        raise ValueError("a number with no digits in it")
    if index < len(expression) and expression[index] == ".":
        index += 1
        decimals = index
        while index < len(expression) and expression[index].isdigit():
            index += 1
        if index == decimals:
            raise ValueError("a number with nothing after its point")
        return float(expression[start:index]), index
    return int(expression[start:index]), index


def _read_word(expression, index):
    start = index
    while index < len(expression) and (
            expression[index].isalnum() or expression[index] == "_"):
        index += 1
    return expression[start:index], index


def _kind(tokens, index):
    return tokens[index][0] if index < len(tokens) else None


def _parse_expression(tokens, index):
    node, index = _parse_and(tokens, index)
    parts = [node]
    while _kind(tokens, index) == "or":
        node, index = _parse_and(tokens, index + 1)
        parts.append(node)
    return (("or", parts) if len(parts) > 1 else parts[0]), index


def _parse_and(tokens, index):
    node, index = _parse_not(tokens, index)
    parts = [node]
    while _kind(tokens, index) == "and":
        node, index = _parse_not(tokens, index + 1)
        parts.append(node)
    return (("and", parts) if len(parts) > 1 else parts[0]), index


def _parse_not(tokens, index):
    if _kind(tokens, index) == "not":
        node, index = _parse_not(tokens, index + 1)
        return ("not", node), index
    return _parse_primary(tokens, index)


def _parse_primary(tokens, index):
    kind = _kind(tokens, index)
    if kind == "(":
        node, index = _parse_expression(tokens, index + 1)
        if _kind(tokens, index) != ")":
            raise ValueError("a bracket was never closed")
        return node, index + 1
    if kind in ("true", "false"):
        return ("constant", TRUE if kind == "true" else FALSE), index + 1
    if kind != "field":
        raise ValueError("a field name was expected here")
    name = tokens[index][1]
    index += 1
    kind = _kind(tokens, index)
    if kind == "is":
        index += 1
        negated = _kind(tokens, index) == "not"
        if negated:
            index += 1
        if _kind(tokens, index) != "null":
            raise ValueError("IS must be followed by NULL or NOT NULL")
        return ("is-null", name, negated), index + 1
    if kind == "in":
        index += 1
        if _kind(tokens, index) != "(":
            raise ValueError("IN must be followed by a bracketed list")
        index += 1
        values = []
        while True:
            value, index = _parse_literal(tokens, index)
            values.append(value)
            if _kind(tokens, index) == ",":
                index += 1
                continue
            if _kind(tokens, index) == ")":
                return ("in", name, values), index + 1
            raise ValueError("a bracketed list was never closed")
    if kind == "between":
        low, index = _parse_literal(tokens, index + 1)
        if _kind(tokens, index) != "and":
            raise ValueError("BETWEEN takes two values with AND between them")
        high, index = _parse_literal(tokens, index + 1)
        return ("between", name, low, high), index
    if kind in OPERATORS:
        value, index = _parse_literal(tokens, index + 1)
        return ("compare", name, kind, value), index
    raise ValueError("a field name is not a test on its own")


def _parse_literal(tokens, index):
    kind = _kind(tokens, index)
    if kind in ("number", "string"):
        return tokens[index][1], index + 1
    if kind == "null":
        return None, index + 1
    if kind in ("true", "false"):
        return kind == "true", index + 1
    raise ValueError("a value was expected here")


def _fields_used(node):
    if node[0] in ("and", "or"):
        names = set()
        for part in node[1]:
            names |= _fields_used(part)
        return names
    if node[0] == "not":
        return _fields_used(node[1])
    if node[0] == "constant":
        return set()
    return {node[1]}


def _hold(node, record):
    shape = node[0]
    if shape == "constant":
        return node[1]
    if shape == "not":
        held = _hold(node[1], record)
        if held == UNKNOWN:
            return UNKNOWN
        return FALSE if held == TRUE else TRUE
    if shape == "and":
        return _all_of([_hold(part, record) for part in node[1]])
    if shape == "or":
        return _any_of([_hold(part, record) for part in node[1]])
    if shape == "is-null":
        missing = record.get(node[1]) is None
        held = FALSE if missing == node[2] else TRUE
        return held
    value = record.get(node[1])
    if shape == "compare":
        return compare(value, node[2], node[3])
    if shape == "in":
        return _any_of([compare(value, "=", wanted) for wanted in node[2]])
    return _all_of([compare(value, ">=", node[2]),
                    compare(value, "<=", node[3])])


def _all_of(held):
    if FALSE in held:
        return FALSE
    return UNKNOWN if UNKNOWN in held else TRUE


def _any_of(held):
    if TRUE in held:
        return TRUE
    return UNKNOWN if UNKNOWN in held else FALSE
