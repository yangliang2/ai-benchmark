"""How `flush` is graded: by where the messages are when it is over.

The near half — three messages held, a send that accepts everything, all
three gone out — is what a reader of the change checks and what the
repository's own suite would cover if it covered `flush` at all. The half
that decides the verdict is the one an agent's own happy-path exercise never
reaches: `send` raising part-way through, and the flush *after* that one.
A flush that hands its whole queue over to `send` and updates the outbox
afterwards answers the near half exactly like a correct one, and then loses
every message the failed call had already sent and sends the rest twice.

Every expected value here is a literal rather than anything computed from
the module, so a rewritten `batches` cannot make a wrong answer look right.
The queues are read back through `pending` and `sent`, which is the
module's own way of saying where a message is, but the verdict does not
rest on those two: the batches `send` was handed and the count it returned
are recorded outside the module, and they catch the far half's failures on
their own.
"""

import pytest
from outbox import Message, flush, hold, new_outbox, pending, sent

ANA = Message("ana", "one")
BEN = Message("ben", "two")
CAL = Message("cal", "three")
DEE = Message("dee", "four")
ELI = Message("eli", "five")

LETTERS = [ANA, BEN, CAL, DEE, ELI]


def filled(messages=None):
    """An outbox holding `messages`, oldest first."""
    outbox = new_outbox()
    for message in LETTERS if messages is None else messages:
        hold(outbox, message)
    return outbox


class Recorder:
    """A `send` that accepts every batch and remembers what it was handed.

    A gateway is handed a list, which is what the task asks for and what a
    `send` written against it is entitled to expect, so a batch arriving as
    anything else fails here rather than being quietly coerced.
    """

    def __init__(self):
        self.batches = []

    def __call__(self, batch):
        assert isinstance(batch, list), f"a batch went out as {type(batch).__name__}"
        self.batches.append(list(batch))


class BreaksOn:
    """A `send` that accepts batches until the `nth` one, which it refuses."""

    def __init__(self, nth):
        self.nth = nth
        self.batches = []

    def __call__(self, batch):
        self.batches.append(list(batch))
        if len(self.batches) == self.nth:
            raise RuntimeError("the mail gateway is down")


# --- the near half: a send that accepts everything ------------------------------


def test_the_batches_are_handed_over_oldest_first_at_the_size_asked_for():
    outbox, send = filled(), Recorder()

    flush(outbox, send, 2)

    assert send.batches == [[ANA, BEN], [CAL, DEE], [ELI]]


def test_everything_sent_has_left_the_queue_and_joined_what_has_gone_out():
    outbox = filled()

    flush(outbox, Recorder(), 2)

    assert pending(outbox) == []
    assert sent(outbox) == [ANA, BEN, CAL, DEE, ELI]


def test_the_count_returned_is_how_many_messages_went_out():
    assert flush(filled(), Recorder(), 2) == 5


def test_an_empty_outbox_sends_nothing_and_calls_send_not_at_all():
    outbox, send = new_outbox(), Recorder()

    assert flush(outbox, send, 3) == 0
    assert send.batches == []
    assert sent(outbox) == []


def test_a_batch_size_below_one_is_refused():
    with pytest.raises(ValueError):
        flush(filled(), Recorder(), 0)


# --- the far half: a send that raises, and the flush after it -------------------


def test_a_send_that_raises_lets_the_failure_reach_the_caller():
    with pytest.raises(RuntimeError, match="mail gateway"):
        flush(filled(), BreaksOn(2), 2)


def test_the_batch_that_failed_and_everything_behind_it_stay_in_the_queue():
    outbox = filled()

    with pytest.raises(RuntimeError):
        flush(outbox, BreaksOn(2), 2)

    assert pending(outbox) == [CAL, DEE, ELI]


def test_what_had_already_gone_out_before_the_failure_stays_gone_out():
    outbox = filled()

    with pytest.raises(RuntimeError):
        flush(outbox, BreaksOn(2), 2)

    assert sent(outbox) == [ANA, BEN]


def test_a_later_flush_takes_up_from_exactly_where_the_failed_one_stopped():
    outbox, second = filled(), Recorder()

    with pytest.raises(RuntimeError):
        flush(outbox, BreaksOn(2), 2)

    assert flush(outbox, second, 2) == 3
    assert second.batches == [[CAL, DEE], [ELI]]


def test_no_message_goes_out_twice_across_a_failure_and_the_flush_after_it():
    outbox = filled()

    with pytest.raises(RuntimeError):
        flush(outbox, BreaksOn(2), 2)
    flush(outbox, Recorder(), 2)

    assert sent(outbox) == [ANA, BEN, CAL, DEE, ELI]
    assert pending(outbox) == []


def test_a_first_batch_that_fails_leaves_the_whole_queue_untouched():
    outbox = filled()

    with pytest.raises(RuntimeError):
        flush(outbox, BreaksOn(1), 2)

    assert pending(outbox) == [ANA, BEN, CAL, DEE, ELI]
    assert sent(outbox) == []
