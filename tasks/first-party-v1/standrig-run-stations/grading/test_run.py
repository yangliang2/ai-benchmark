"""How `run` is graded: by what the stand looks like once the run is over.

The near half — the stations come up in order, the work runs, the stations
go back down in the reverse order — is what a reader of the change checks,
and a plain `start` loop, `work()`, `stop` loop answers it step for step: on
a run where nothing goes wrong its log is identical to a correct one's.
What it has not done is arrange for the stations to come down when something
*does* go wrong, and nothing on the happy path says so. The stand is left
powered up, which is discovered by whoever walks up to it next.

The stations that fail are defined here, and every expectation is a log
written out literally, so what the verdict is measured against cannot be
rewritten by the diff being graded. `still_up` is read back through the
module because it says what a run left behind more plainly than a log
does — a convenience rather than the yardstick: every rule it is used for
is also asserted here against a literal log, so the verdict survives a
rewritten reader.
"""

import pytest
from standrig import run, stand, still_up


class WontStart:
    """A station that refuses to come up, and records nothing when it does.

    It logs its `stop`, though: that is how the rule about a station which
    never came up not being taken down is read off a run.
    """

    def __init__(self, name, log):
        self.name = name
        self.log = log

    def start(self):
        raise RuntimeError(f"{self.name} did not come up")

    def stop(self):
        self.log.append(f"stop {self.name}")


def rig(log, *names):
    """Stations for `names`, in order, sharing `log`."""
    return list(stand(names, log))


# --- the near half: a run where nothing goes wrong ------------------------------


def test_the_stations_come_up_in_order_and_go_down_in_the_reverse_order():
    log = []

    run(rig(log, "power", "pump", "probe"), lambda: None)

    assert log == [
        "start power",
        "start pump",
        "start probe",
        "stop probe",
        "stop pump",
        "stop power",
    ]


def test_the_value_the_work_returns_is_the_value_the_run_returns():
    assert run(rig([], "power"), lambda: "42 bar") == "42 bar"


def test_the_work_runs_while_every_station_is_up():
    log = []
    seen = []

    run(rig(log, "power", "pump"), lambda: seen.append(list(log)))

    assert seen == [["start power", "start pump"]]


def test_a_run_with_no_stations_still_does_the_work():
    log = []

    assert run(rig(log), lambda: "nothing to it") == "nothing to it"
    assert log == []


# --- the far half: a run where something goes wrong -----------------------------


def failing_work():
    raise ValueError("the sample cracked")


def test_work_that_fails_lets_the_failure_reach_the_caller():
    with pytest.raises(ValueError, match="sample cracked"):
        run(rig([], "power", "pump"), failing_work)


def test_work_that_fails_still_leaves_the_stand_shut_down():
    log = []

    with pytest.raises(ValueError):
        run(rig(log, "power", "pump", "probe"), failing_work)

    assert still_up(log) == []


def test_the_stand_comes_down_in_the_reverse_order_after_work_fails():
    log = []

    with pytest.raises(ValueError):
        run(rig(log, "power", "pump"), failing_work)

    assert log == ["start power", "start pump", "stop pump", "stop power"]


def test_a_station_that_will_not_come_up_lets_the_failure_reach_the_caller():
    log = []
    stations = [*rig(log, "power"), WontStart("pump", log)]

    with pytest.raises(RuntimeError, match="did not come up"):
        run(stations, lambda: None)


def test_the_stations_already_up_come_down_when_one_will_not_start():
    log = []
    stations = [*rig(log, "power", "pump"), WontStart("probe", log)]

    with pytest.raises(RuntimeError):
        run(stations, lambda: None)

    assert still_up(log) == []
    assert log == ["start power", "start pump", "stop pump", "stop power"]


def test_a_station_that_never_came_up_is_not_taken_down():
    log = []
    stations = [*rig(log, "power"), WontStart("pump", log), *rig(log, "probe")]

    with pytest.raises(RuntimeError):
        run(stations, lambda: None)

    assert log == ["start power", "stop power"]


def test_work_that_never_ran_because_a_station_failed_leaves_no_trace():
    log = []
    ran = []
    stations = [WontStart("power", log), *rig(log, "pump")]

    with pytest.raises(RuntimeError):
        run(stations, lambda: ran.append("worked"))

    assert ran == []
    assert log == []
