"""A tiny calculator over reverse Polish token lists and infix strings."""

import re


def evaluate_rpn(tokens):
    """Evaluate tokens in reverse Polish notation.

    Tokens are strings: numbers, or one of + - * /. Raises ValueError on a
    malformed token stream.
    """
    stack = []
    for token in tokens:
        if token in ("+", "-", "*", "/"):
            if len(stack) < 2:
                raise ValueError(f"operator {token!r} needs two operands")
            right = stack.pop()
            left = stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            elif token == "*":
                stack.append(left * right)
            else:
                stack.append(left / right)
        else:
            try:
                stack.append(float(token))
            except ValueError:
                raise ValueError(f"unrecognised token {token!r}") from None
    if len(stack) != 1:
        raise ValueError("leftover operands")
    return stack[0]


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def evaluate(expression):
    """Evaluate an ordinary infix arithmetic expression string."""
    tokens = _tokenise(expression)
    value, position = _parse_sum(tokens, 0)
    if position != len(tokens):
        raise ValueError(f"unexpected token {tokens[position]!r}")
    return value


def _tokenise(expression):
    tokens = []
    index = 0
    while index < len(expression):
        character = expression[index]
        if character.isspace():
            index += 1
        elif character in "+-*/()":
            tokens.append(character)
            index += 1
        else:
            match = _NUMBER.match(expression, index)
            if match is None:
                raise ValueError(f"unrecognised character {character!r}")
            tokens.append(match.group())
            index = match.end()
    return tokens


def _parse_sum(tokens, position):
    value, position = _parse_product(tokens, position)
    while position < len(tokens) and tokens[position] in ("+", "-"):
        operator = tokens[position]
        right, position = _parse_product(tokens, position + 1)
        value = value + right if operator == "+" else value - right
    return value, position


def _parse_product(tokens, position):
    value, position = _parse_factor(tokens, position)
    while position < len(tokens) and tokens[position] in ("*", "/"):
        operator = tokens[position]
        right, position = _parse_factor(tokens, position + 1)
        value = value * right if operator == "*" else value / right
    return value, position


def _parse_factor(tokens, position):
    if position == len(tokens):
        raise ValueError("expression ended where an operand was expected")
    token = tokens[position]
    if token == "-":
        value, position = _parse_factor(tokens, position + 1)
        return -value, position
    if token == "(":
        value, position = _parse_sum(tokens, position + 1)
        if position == len(tokens) or tokens[position] != ")":
            raise ValueError("unbalanced parentheses")
        return value, position + 1
    if token in ("+", "*", "/", ")"):
        raise ValueError(f"unexpected token {token!r}")
    return float(token), position + 1
