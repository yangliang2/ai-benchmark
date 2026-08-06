from standrig import Station, describe, stand, still_up


def test_a_station_records_being_started_and_stopped():
    log = []
    station = Station("pump", log)

    station.start()
    station.stop()

    assert log == ["start pump", "stop pump"]


def test_a_stand_builds_one_station_a_name_in_the_order_given():
    log = []

    stations = stand(["power", "pump"], log)

    assert [station.name for station in stations] == ["power", "pump"]


def test_every_station_of_a_stand_records_to_the_one_log():
    log = []

    for station in stand(["power", "pump"], log):
        station.start()

    assert log == ["start power", "start pump"]


def test_nothing_is_up_before_anything_starts():
    assert still_up([]) == []


def test_what_started_and_did_not_stop_is_still_up():
    log = ["start power", "start pump", "stop pump"]

    assert still_up(log) == ["power"]


def test_a_stand_taken_all_the_way_down_leaves_nothing_up():
    log = ["start power", "start pump", "stop pump", "stop power"]

    assert still_up(log) == []


def test_the_summary_names_what_was_left_up():
    log = ["start power", "start pump", "stop pump"]

    assert describe(log) == "3 steps, power still up"


def test_the_summary_of_a_clean_run_says_nothing_is_up():
    log = ["start power", "stop power"]

    assert describe(log) == "2 steps, nothing still up"
