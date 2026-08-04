"""Behaviour half of the grading suite: must pass before and after the
reshape, so it observes only what the callers render — never the shape of
parse_task's return value."""

from boardview import board, lane_for
from digest import daily_digest


def test_lane_for_prefers_done_over_urgency():
    assert lane_for("x fix roof !1") == "done"
    assert lane_for("fix roof !1") == "urgent"
    assert lane_for("fix roof !2") == "soon"
    assert lane_for("fix roof") == "later"


def test_board_keeps_input_order_and_every_lane():
    lanes = board(["a !1", "b !2", "c", "x d", "e !1"])

    assert lanes == {
        "done": ["d"], "urgent": ["a", "e"], "soon": ["b"], "later": ["c"],
    }


def test_board_of_nothing_still_has_every_lane():
    assert board([]) == {"done": [], "urgent": [], "soon": [], "later": []}


def test_daily_digest_counts_open_and_lists_urgent_with_tags():
    digest = daily_digest(
        ["water plants", "call bank !1 #money #urgent", "x old thing", "run !1"]
    )

    assert digest == "open tasks: 3\n* call bank #money #urgent\n* run"


def test_daily_digest_keeps_tag_order():
    assert daily_digest(["a !1 #b #a #c"]) == "open tasks: 1\n* a #b #a #c"


def test_markers_can_appear_anywhere_after_the_done_flag():
    assert daily_digest(["#late pay !1 rent"]) == "open tasks: 1\n* pay rent #late"
