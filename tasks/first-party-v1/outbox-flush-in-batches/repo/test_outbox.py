import pytest
from outbox import Message, batches, describe, hold, new_outbox, pending, sent

LETTERS = [
    Message("ana", "hello"),
    Message("ben", "hello"),
    Message("cal", "hello"),
]


def filled():
    outbox = new_outbox()
    for letter in LETTERS:
        hold(outbox, letter)
    return outbox


def test_a_new_outbox_holds_nothing():
    outbox = new_outbox()

    assert pending(outbox) == []
    assert sent(outbox) == []


def test_holding_a_message_puts_it_at_the_back_of_the_queue():
    assert pending(filled()) == LETTERS


def test_nothing_has_gone_out_just_because_it_is_held():
    assert sent(filled()) == []


def test_the_queue_readers_hand_back_lists_of_their_own():
    outbox = filled()

    pending(outbox).clear()

    assert pending(outbox) == LETTERS


def test_batches_are_consecutive_and_at_most_the_size_given():
    assert batches([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_a_batch_bigger_than_the_messages_is_one_batch():
    assert batches([1, 2], 9) == [[1, 2]]


def test_no_messages_make_no_batches():
    assert batches([], 3) == []


def test_a_batch_size_below_one_is_refused():
    with pytest.raises(ValueError):
        batches([1, 2], 0)


def test_the_summary_counts_both_queues():
    assert describe(filled()) == "0 sent, 3 waiting"
