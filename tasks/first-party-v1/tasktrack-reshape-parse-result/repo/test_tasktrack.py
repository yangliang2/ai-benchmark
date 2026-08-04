from boardview import board, lane_for
from digest import daily_digest
from tasktrack import parse_task


def test_parse_task_reads_every_marker():
    title, priority, tags, done = parse_task("x pay rent !1 #home #money")

    assert title == "pay rent"
    assert priority == 1
    assert tags == ["home", "money"]
    assert done is True


def test_lane_for_prefers_done_over_urgency():
    assert lane_for("x fix roof !1") == "done"
    assert lane_for("fix roof !1") == "urgent"


def test_board_keeps_input_order():
    lanes = board(["a !1", "b !2", "c", "x d"])

    assert lanes == {
        "done": ["d"], "urgent": ["a"], "soon": ["b"], "later": ["c"],
    }


def test_daily_digest_counts_open_and_lists_urgent():
    digest = daily_digest(["water plants", "call bank !1 #money", "x old thing"])

    assert digest == "open tasks: 2\n* call bank #money"
