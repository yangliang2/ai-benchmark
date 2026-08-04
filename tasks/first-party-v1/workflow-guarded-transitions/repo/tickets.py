"""The ticket workflow."""

from fsm import Machine

TRANSITIONS = {
    ("new", "triage"): "triaged",
    ("triaged", "start"): "in-progress",
    ("in-progress", "finish"): "done",
}


def new_ticket():
    """A fresh ticket at the start of the workflow."""
    return Machine("new", TRANSITIONS)
