"""Bringing a hardware test stand's stations up and down."""


class Station:
    """One station of the stand, which records what happens to it.

    The log is shared with whoever built the station, so what a run did to
    the stand can be read back afterwards.
    """

    def __init__(self, name, log):
        self.name = name
        self.log = log

    def start(self):
        """Bring this station up."""
        self.log.append(f"start {self.name}")

    def stop(self):
        """Take this station down."""
        self.log.append(f"stop {self.name}")


def stand(names, log):
    """A station per name, in the order given, all recording to `log`."""
    return [Station(name, log) for name in names]


def still_up(log):
    """The stations started and not since stopped, earliest start first."""
    up = []
    for line in log:
        happened, name = line.split(" ", 1)
        if happened == "start":
            up.append(name)
        elif name in up:
            up.remove(name)
    return up


def describe(log):
    """A one-line summary of what a run left behind."""
    left = still_up(log)
    return f"{len(log)} steps, {', '.join(left) if left else 'nothing'} still up"
