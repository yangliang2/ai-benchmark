"""The ticket workflow."""

from fsm import Machine

TRANSITIONS = {
    ("new", "triage"): "triaged",
    ("triaged", "start"): "in-progress",
    ("in-progress", "finish"): "done",
    ("done", "reopen"): "in-progress",
}

MAX_REOPENS = 2


def _may_reopen(context):
    return context["reopens"] < MAX_REOPENS


def _count_reopen(context):
    context["reopens"] += 1


def new_ticket():
    """A fresh ticket at the start of the workflow."""
    ticket = Machine("new", TRANSITIONS, context={"reopens": 0})
    ticket.add_guard("done", "reopen", _may_reopen)
    ticket.add_hook("done", "reopen", _count_reopen)
    return ticket
