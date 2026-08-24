"""How the clerk works the book: one command, one change, saved and done."""

import argparse

import crossings
import fares
import ledger
import report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ferryhouse", description=__doc__)
    parser.add_argument("--book", default=ledger.BOOK_FILE, help="the book file")
    commands = parser.add_subparsers(dest="command", required=True)

    priced = commands.add_parser("fare", help="set the board's fare for a class")
    priced.add_argument("kind")
    priced.add_argument("pence", type=int)

    quoted = commands.add_parser("quote", help="what a crossing costs today")
    quoted.add_argument("kind")

    crossed = commands.add_parser("cross", help="a crossing made and paid")
    refunded = commands.add_parser("refund", help="a crossing turned back")
    for line in (crossed, refunded):
        line.add_argument("day")
        line.add_argument("kind")
        line.add_argument("--note", default="")

    counted = commands.add_parser("takings", help="the box between two days")
    tallied = commands.add_parser("tally", help="crossings by class between two days")
    for span in (counted, tallied):
        span.add_argument("start")
        span.add_argument("end")

    args = parser.parse_args(argv)
    the_book = ledger.load(args.book)

    if args.command == "fare":
        fares.set_fare(the_book, args.kind, args.pence)
    elif args.command == "quote":
        print(f"{fares.fare_for(the_book, args.kind)}d")
        return
    elif args.command == "cross":
        crossings.cross(the_book, args.day, args.kind, args.note)
    elif args.command == "refund":
        crossings.refund(the_book, args.day, args.kind, args.note)
        print(f"hand back {fares.fare_for(the_book, args.kind)}d")
    elif args.command == "takings":
        print(f"{report.takings_between(the_book, args.start, args.end)}d")
        return
    else:
        print(report.tally_between(the_book, args.start, args.end))
        return

    ledger.save(the_book, args.book)


if __name__ == "__main__":
    main()
