"""The label on a tool's handle, and finding a tool by it."""


def tidy(label):
    """A label as the shed has it down: no stray spaces, and all in small
    letters, so that 'Long Bar Clamp' and 'long bar clamp' are one label."""
    return " ".join(label.split()).lower()


def matching(tools, label):
    """Every tool of the shed whose label is this label."""
    wanted = tidy(label)
    return [tool for tool in tools if tidy(tool.label) == wanted]


def one(tools, label):
    """The single tool of this label, or None where the shed has none of it
    or has more than one."""
    matched = matching(tools, label)
    return matched[0] if len(matched) == 1 else None
