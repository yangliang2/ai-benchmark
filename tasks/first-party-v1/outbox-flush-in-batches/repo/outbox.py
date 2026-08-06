"""Holding messages until they go out, and cutting them into batches."""

from collections import namedtuple

# One message waiting to go out: who it is for, and what it says.
Message = namedtuple("Message", "recipient body")


def new_outbox():
    """An outbox with nothing in it."""
    return {"pending": [], "sent": []}


def hold(outbox, message):
    """Put `message` at the back of the queue waiting to go out."""
    outbox["pending"].append(message)


def pending(outbox):
    """The messages still waiting to go out, oldest first."""
    return list(outbox["pending"])


def sent(outbox):
    """The messages that have gone out, in the order they went."""
    return list(outbox["sent"])


def batches(messages, size):
    """`messages` cut into consecutive batches of at most `size`, in order."""
    if size < 1:
        raise ValueError(f"a batch of at most {size} messages holds nothing")
    return [messages[start : start + size] for start in range(0, len(messages), size)]


def describe(outbox):
    """A one-line summary of what has gone out and what has not."""
    return f"{len(outbox['sent'])} sent, {len(outbox['pending'])} waiting"
