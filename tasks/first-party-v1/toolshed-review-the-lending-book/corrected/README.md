# The tool shed

The village tool shed, as the people behind the desk run it: what sits on the
racks, which afternoons the doors are open, and what has gone out with whom.

## The modules

- `shed.py` — the racks, and the tools that live on them.
- `rota.py` — the afternoons the doors are open, and whose turn it is.
- `labels.py` — the label on a handle, and finding a tool by it.
- `loans.py` — the loans book.
- `desk.py` — what the desk prints.

## The house rules

- A tool belongs to one rack, and goes back to the rack it came off.
- A label names the whole of what is on a handle and never a part of it:
  somebody after the saw is not after the jigsaw.
- A member may have more than one thing out at a time, and what the desk shows
  against a member is every one of them.
- The loans book holds its loans in the order they went out, and printing
  anything off it leaves that order alone.

`review.diff` is the change that brought the labels and the desk in, in the
state the shed's own copy of it is in.
