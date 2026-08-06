# outbox

An outbox for a small notifications service: messages are held until
something sends them, and they go out in batches. Standard library only.

- `Message(recipient, body)` — one message.
- `new_outbox()` — an outbox holding nothing.
- `hold(outbox, message)` — put a message at the back of the queue.
- `pending(outbox)` / `sent(outbox)` — the two queues, oldest first.
- `batches(messages, size)` — messages cut into consecutive batches.
- `describe(outbox)` — a one-line summary.

Run the tests with `pytest`.
