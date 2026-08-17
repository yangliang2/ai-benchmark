from machines import Floor, Machine


def test_a_load_goes_in_a_drum_that_is_big_enough_for_it():
    assert Machine(1, "small").takes(5)
    assert not Machine(1, "small").takes(8)


def test_the_first_drum_that_is_free_and_big_enough_is_the_one_offered():
    floor = Floor([Machine(1, "small"), Machine(2, "large")])

    assert floor.free_for(10, busy={1}).number == 2
    assert floor.free_for(4, busy={1, 2}) is None
