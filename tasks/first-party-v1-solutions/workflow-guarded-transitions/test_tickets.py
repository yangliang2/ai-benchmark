from tickets import new_ticket


def test_a_ticket_walks_the_workflow():
    ticket = new_ticket()
    ticket.fire("triage")
    ticket.fire("start")
    ticket.fire("finish")
    assert ticket.state == "done"


def test_a_new_ticket_starts_at_new():
    assert new_ticket().state == "new"
