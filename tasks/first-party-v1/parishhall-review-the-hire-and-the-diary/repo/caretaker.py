"""The caretaker's round: whose keys are out, and when the doors are locked."""

USUAL_LOCK_UP = 22


def lock_up_at(hours, day):
    """The hour the doors are locked on this day: the hour set for the day
    where one is set, and the usual hour where none is. An hour of nothing is
    midnight, which is an hour like any other."""
    hour = hours.get(day)
    return hour if hour is not None else USUAL_LOCK_UP


def hand_back(held, who):
    """Take every key this person holds out of the list of keys that are out;
    how many of them came back."""
    back = 0
    for holder in list(held):
        if holder == who:
            held.remove(holder)
            back += 1
    return back
