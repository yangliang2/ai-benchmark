"""How the steward works the log: one command, one working, written and done."""

import argparse

import floorwork
import log
import monthend
import reckon


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="maltings", description=__doc__)
    parser.add_argument("--log", default=log.LOG_FILE, help="the log file")
    commands = parser.add_subparsers(dest="command", required=True)

    steeped = commands.add_parser("steep", help="barley into a steeping pit")
    steeped.add_argument("day")
    steeped.add_argument("quarters", type=int)
    steeped.add_argument("--pit", type=int, required=True)

    turned = commands.add_parser("turn", help="a growing floor turned")
    turned.add_argument("day")
    turned.add_argument("quarters", type=int)
    turned.add_argument("--floor", type=int, required=True)

    kilned = commands.add_parser("kiln", help="a kilning drawn off")
    kilned.add_argument("day")
    kilned.add_argument("quarters", type=int)

    dayed = commands.add_parser("day", help="a day's quarters by working")
    dayed.add_argument("day")

    commands.add_parser("standing", help="the quarters now in the house")

    carried = commands.add_parser("carry", help="a month summed and lifted out")
    carried.add_argument("month")

    args = parser.parse_args(argv)

    if args.command == "steep":
        floorwork.steep(args.day, args.quarters, args.pit, args.log)
    elif args.command == "turn":
        floorwork.turn(args.day, args.quarters, args.floor, args.log)
    elif args.command == "kiln":
        floorwork.kiln(args.day, args.quarters, args.log)
    elif args.command == "day":
        for working, quarters in sorted(reckon.day(args.day, args.log).items()):
            print(f"{working}  {quarters} quarter(s)")
    elif args.command == "standing":
        print(f"{reckon.standing(args.log)} quarter(s) in the house")
    else:
        for working, quarters in sorted(monthend.carry(args.month, args.log).items()):
            print(f"{args.month}  {working}  {quarters} quarter(s)")


if __name__ == "__main__":
    main()
