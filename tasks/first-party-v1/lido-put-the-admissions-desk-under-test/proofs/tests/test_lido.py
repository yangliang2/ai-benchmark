"""The author's reference suite for the lido's admissions desk.

The task's registered existence proof: the suite a perfect agent would have
written, at the shape the prompt asks for — `test_*.py` under `tests/`,
standing on its own, no conftest.py and no helper module beside it. The lint
runs it against the pristine repository and against each planted behaviour
change in turn, which is what says the task is solvable exactly as written.

Never overlaid into a workdir, never collected by a verdict: it lives here,
beside repo/, where every action's existence proof lives.
"""

import pytest

from lido import SESSION_KINDS, admit, roll_call


def session(kind="family", capacity=10, admitted=0):
    return {"kind": kind, "capacity": capacity, "admitted": admitted}


def swimmer(name="ada", age=30, member=True, accompanied=False):
    return {"name": name, "age": age, "member": member, "accompanied": accompanied}


# --- the three refusals --------------------------------------------------------


def test_a_club_session_is_for_members():
    assert admit(session("club"), swimmer(member=False)) == "refused"
    assert admit(session("club"), swimmer(member=True)) == "admitted"


def test_a_club_session_refuses_a_visitor_however_empty_the_water_is():
    empty = session("club", capacity=50, admitted=0)

    assert admit(empty, swimmer(member=False)) == "refused"


def test_a_lane_session_is_for_swimmers_of_sixteen_and_over():
    assert admit(session("lane"), swimmer(age=15)) == "refused"
    assert admit(session("lane"), swimmer(age=16)) == "admitted"
    assert admit(session("lane"), swimmer(age=17)) == "admitted"


def test_a_family_session_takes_a_swimmer_a_lane_session_would_not():
    assert admit(session("family"), swimmer(age=15)) == "admitted"


def test_a_child_under_eight_is_refused_unless_somebody_comes_in_with_them():
    assert admit(session(), swimmer(age=7, accompanied=False)) == "refused"
    assert admit(session(), swimmer(age=7, accompanied=True)) == "admitted"


def test_eight_is_old_enough_to_go_in_alone():
    assert admit(session(), swimmer(age=8, accompanied=False)) == "admitted"


def test_the_child_rule_holds_at_every_kind_of_session():
    for kind in SESSION_KINDS:
        alone = admit(session(kind), swimmer(age=6, accompanied=False))
        assert alone == "refused", kind


# --- refusals are settled before the water is counted --------------------------


def test_a_swimmer_the_rules_turn_away_is_refused_rather_than_left_waiting():
    full = session("lane", capacity=4, admitted=4)

    assert admit(full, swimmer(age=12)) == "refused"
    assert admit(session("club", capacity=4, admitted=4), swimmer(member=False)) == (
        "refused"
    )
    assert admit(full, swimmer(age=6, accompanied=False)) == "refused"


# --- the places, and the one held for members ----------------------------------


def test_a_member_is_admitted_while_any_place_is_free():
    assert admit(session(capacity=4, admitted=3), swimmer(member=True)) == "admitted"


def test_a_member_waits_once_the_water_is_full():
    assert admit(session(capacity=4, admitted=4), swimmer(member=True)) == "waiting"


def test_the_last_place_is_held_for_a_member():
    one_left = session(capacity=4, admitted=3)

    assert admit(one_left, swimmer(member=False)) == "waiting"
    assert admit(one_left, swimmer(member=True)) == "admitted"


def test_a_visitor_is_admitted_while_a_second_place_is_free_behind_them():
    assert admit(session(capacity=4, admitted=2), swimmer(member=False)) == "admitted"


def test_a_visitor_waits_at_a_full_session_too():
    assert admit(session(capacity=4, admitted=4), swimmer(member=False)) == "waiting"


def test_a_session_of_one_place_holds_it_for_a_member():
    only = session(capacity=1, admitted=0)

    assert admit(only, swimmer(member=False)) == "waiting"
    assert admit(only, swimmer(member=True)) == "admitted"


# --- what the desk refuses to answer at all ------------------------------------


def test_a_session_of_no_known_kind_is_an_error():
    with pytest.raises(ValueError):
        admit(session("gala"), swimmer())


def test_a_session_with_no_places_is_an_error():
    with pytest.raises(ValueError):
        admit(session(capacity=0), swimmer())


def test_more_swimmers_in_the_water_than_places_is_an_error():
    with pytest.raises(ValueError):
        admit(session(capacity=4, admitted=5), swimmer())


def test_a_negative_count_of_swimmers_in_the_water_is_an_error():
    with pytest.raises(ValueError):
        admit(session(capacity=4, admitted=-1), swimmer())


def test_a_negative_age_is_an_error():
    with pytest.raises(ValueError):
        admit(session(), swimmer(age=-1))


def test_a_full_session_is_answered_rather_than_refused_as_an_error():
    assert admit(session(capacity=4, admitted=4), swimmer(member=True)) == "waiting"


def test_the_error_is_raised_before_any_rule_is_applied():
    # A swimmer the rules would refuse anyway, at a session that is not a
    # session: the complaint is about the session, not the swimmer.
    with pytest.raises(ValueError):
        admit(session("gala"), swimmer(age=4, accompanied=False))


# --- the queue -----------------------------------------------------------------


def test_a_roll_call_gives_back_the_three_lists_in_the_order_presented():
    called = roll_call(
        session(capacity=10),
        [
            swimmer(name="ada"),
            swimmer(name="bram", age=6, accompanied=False),
            swimmer(name="cleo", member=False),
        ],
    )

    assert called == {
        "admitted": ["ada", "cleo"],
        "waiting": [],
        "refused": ["bram"],
    }


def test_an_empty_queue_gives_three_empty_lists():
    assert roll_call(session(), []) == {
        "admitted": [],
        "waiting": [],
        "refused": [],
    }


def test_a_place_taken_by_somebody_ahead_in_the_queue_is_not_offered_again():
    called = roll_call(
        session(capacity=2, admitted=0),
        [swimmer(name="ada"), swimmer(name="bram"), swimmer(name="cleo")],
    )

    assert called["admitted"] == ["ada", "bram"]
    assert called["waiting"] == ["cleo"]


def test_the_queue_fills_the_water_one_place_at_a_time():
    called = roll_call(
        session(capacity=3, admitted=1),
        [swimmer(name="ada"), swimmer(name="bram"), swimmer(name="cleo")],
    )

    assert called["admitted"] == ["ada", "bram"]
    assert called["waiting"] == ["cleo"]


def test_a_swimmer_who_waits_or_is_refused_takes_up_no_place():
    called = roll_call(
        session("lane", capacity=2, admitted=1),
        [
            swimmer(name="ada", age=12),
            swimmer(name="bram", member=False),
            swimmer(name="cleo"),
        ],
    )

    # ada is refused and bram waits for want of the held place; neither of
    # them costs cleo the one place that was free.
    assert called == {
        "admitted": ["cleo"],
        "waiting": ["bram"],
        "refused": ["ada"],
    }


def test_a_roll_call_leaves_the_session_it_was_handed_as_it_found_it():
    desk = session(capacity=5, admitted=1)

    roll_call(desk, [swimmer(name="ada"), swimmer(name="bram")])

    assert desk == {"kind": "family", "capacity": 5, "admitted": 1}


def test_a_value_error_comes_straight_back_out_of_a_roll_call():
    with pytest.raises(ValueError):
        roll_call(session("gala"), [swimmer(name="ada")])
    with pytest.raises(ValueError):
        roll_call(session(), [swimmer(name="ada", age=-2)])
