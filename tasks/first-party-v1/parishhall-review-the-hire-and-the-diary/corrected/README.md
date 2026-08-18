# The parish hall

The hall as the committee keeps it: which rooms there are, who has them and
when, what an evening costs, and who locks up afterwards.

## The modules

- `hall.py` — the rooms, and what each of them will take.
- `caretaker.py` — the keys that are out, and the hour the doors are locked.
- `diary.py` — the bookings.
- `charges.py` — what a booking is charged.

## The house rules

- A room is booked for whole hours, and the diary holds its bookings in the
  order they were taken.
- A hirer who takes their bookings out of the diary takes out every one of
  them, and not the first of them alone.
- A room is hired at the rate on the room for the hours booked, and from
  November to March the heating goes on the bill as well; what the hirer is
  asked for is the whole of that, rounded up to the pound.
- A booking may have a price agreed with the committee, and where one has
  been agreed that is what the hirer is charged — an evening agreed at
  nothing is an evening that costs nothing.

`review.diff` is the change that brought the charges and the cancelling in,
in the state the hall's own copy of it is in.
