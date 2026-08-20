"""The setting of the theatre's playbill.

Words set into lines of a fixed measure, and a line stood in the middle of
that measure.
"""


def set_bill(text, measure):
    """`text` set into lines, none of them wider than `measure` unless one
    word is."""
    _check_measure(measure)
    lines = []
    line = ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= measure:
            # The word fits the line being set, with its space before it.
            line = f"{line} {word}"
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def centre(line, measure):
    """`line` stood in the middle of `measure`, by the space put before it."""
    _check_measure(measure)
    return " " * ((measure - len(line)) // 2) + line


def _check_measure(measure):
    if measure < 1:
        raise ValueError("a measure of no characters sets nothing")
