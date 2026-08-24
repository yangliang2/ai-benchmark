"""How the clerk works the book: one command, one change, saved and done."""

import argparse

import intake
import ledger
import render


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pumphouse", description=__doc__)
    parser.add_argument("--book", default=ledger.BOOK_FILE, help="the book file")
    commands = parser.add_subparsers(dest="command", required=True)

    fitted = commands.add_parser("fit", help="meter a house for the first time")
    refitted = commands.add_parser("refit", help="a fresh meter on a metered house")
    for fitting in (fitted, refitted):
        fitting.add_argument("day")
        fitting.add_argument("name")

    visited = commands.add_parser("read", help="the reader's visit: dial as it stands")
    visited.add_argument("day")
    visited.add_argument("name")
    visited.add_argument("dial", type=int)
    visited.add_argument("--note", default="")

    commands.add_parser("stand", help="every house's newest dial")

    billed = commands.add_parser("bill", help="a house's quarter at the board's rate")
    billed.add_argument("name")
    billed.add_argument("start")
    billed.add_argument("end")
    billed.add_argument("pence", type=int)

    args = parser.parse_args(argv)
    the_book = ledger.load(args.book)

    if args.command == "fit":
        intake.fit(the_book, args.day, args.name)
    elif args.command == "refit":
        intake.refit(the_book, args.day, args.name)
    elif args.command == "read":
        intake.read_meter(the_book, args.day, args.name, args.dial, args.note)
    elif args.command == "stand":
        print(render.stand(the_book))
        return
    else:
        print(f"{render.bill(the_book, args.name, args.start, args.end, args.pence)}d")
        return

    ledger.save(the_book, args.book)


if __name__ == "__main__":
    main()
