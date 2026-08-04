"""A tiny calculator over reverse Polish token lists."""


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
