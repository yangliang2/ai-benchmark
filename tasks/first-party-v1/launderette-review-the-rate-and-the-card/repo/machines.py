"""The machines on the floor, and what each of them takes."""

KILOS_BY_SIZE = {"small": 6, "medium": 9, "large": 12}


class Machine:
    """One drum, by the number painted on its door."""

    def __init__(self, number, size):
        self.number = number
        self.size = size

    def takes(self, kilos):
        """Whether a load this heavy goes in."""
        return kilos <= KILOS_BY_SIZE[self.size]


class Floor:
    """Every machine in the room, in the order they were put in."""

    def __init__(self, machines):
        self.machines = list(machines)

    def free_for(self, kilos, busy):
        """The first machine that nobody is using and that takes this load."""
        for machine in self.machines:
            if machine.number not in busy and machine.takes(kilos):
                return machine
        return None
