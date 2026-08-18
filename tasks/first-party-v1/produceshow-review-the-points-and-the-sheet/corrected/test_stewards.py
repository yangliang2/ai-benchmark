from stewards import ROUND, Steward, duty_at, in_tent, left_of


def test_the_stewards_of_a_tent_come_out_in_the_order_of_the_duty_list():
    stewards = [
        Steward("ada", "the big tent"),
        Steward("bob", "the small tent"),
        Steward("cid", "the big tent"),
    ]

    assert [steward.who for steward in in_tent(stewards, "the big tent")] == [
        "ada",
        "cid",
    ]


def test_a_round_with_nothing_handed_in_comes_back_whole_both_times():
    steward = Steward("ada", "the big tent")

    assert left_of(steward) == list(ROUND)
    assert left_of(steward) == list(ROUND)


def test_a_round_less_what_has_been_done():
    steward = Steward("ada", "the big tent")

    assert left_of(steward, ["setting out"]) == ["judging", "clearing away"]


def test_the_hour_the_tent_is_cleared_is_the_hour_everybody_clears():
    assert duty_at(9) == "setting out"
    assert duty_at(11) == "judging"
    assert duty_at(16) == "clearing away"
