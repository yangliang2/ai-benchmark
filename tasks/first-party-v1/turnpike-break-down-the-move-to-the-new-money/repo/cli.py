"""How the keeper works the roll: one command, one change, saved and done."""

import argparse

import gate
import roll
import tariff
import till


def pence(amount: int) -> str:
    """An amount of money the way the keeper writes it: 5d., 1d., free."""
    return f"{amount}d." if amount else "free"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tollhouse", description=__doc__)
    parser.add_argument("--roll", default=roll.ROLL_FILE, help="the roll file")
    commands = parser.add_subparsers(dest="command", required=True)

    crossed = commands.add_parser("cross", help="a crossing taken at the gate")
    crossed.add_argument("day")
    crossed.add_argument("kind")
    crossed.add_argument("--note", default="")

    waved = commands.add_parser("wave", help="a crossing let past unpaid")
    waved.add_argument("day")
    waved.add_argument("kind")
    waved.add_argument("--note", required=True)

    took = commands.add_parser("takings", help="what a day took at the gate")
    took.add_argument("day")

    counted = commands.add_parser("count", help="a day's crossings by kind")
    counted.add_argument("day")

    commands.add_parser("check", help="the audit: lines taken down wrong")
    commands.add_parser("rates", help="the table of tolls as it stands")

    args = parser.parse_args(argv)
    the_roll = roll.load(args.roll)

    if args.command == "cross":
        gate.cross(the_roll, args.day, args.kind, args.note)
    elif args.command == "wave":
        gate.wave_through(the_roll, args.day, args.kind, args.note)
    elif args.command == "takings":
        print(f"{args.day} took {pence(till.takings(the_roll, args.day))}")
        return
    elif args.command == "count":
        for kind, count in sorted(till.crossings(the_roll, args.day).items()):
            print(f"{kind}  {count} crossing(s)")
        return
    elif args.command == "check":
        for line in till.misrecorded(the_roll):
            print(
                f"{line['day']}  {line['kind']}  took {pence(line['charge'])} "
                f"against the table's {pence(tariff.rate(line['kind']))}"
            )
        return
    else:
        for kind in tariff.kinds():
            print(f"{kind}  {pence(tariff.RATES[kind])}")
        return

    roll.save(the_roll, args.roll)


if __name__ == "__main__":
    main()
