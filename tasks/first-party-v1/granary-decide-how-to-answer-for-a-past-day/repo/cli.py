"""How the clerk works the book: one command, one change, saved and done."""

import argparse

import book
import ledger
import report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="granary", description=__doc__)
    parser.add_argument("--book", default=ledger.BOOK_FILE, help="the book file")
    commands = parser.add_subparsers(dest="command", required=True)

    opened = commands.add_parser("open", help="take a bin onto the book")
    opened.add_argument("day")
    opened.add_argument("name")
    opened.add_argument("grain")
    opened.add_argument("sacks", type=int)

    took = commands.add_parser("in", help="a delivery into a bin")
    gave = commands.add_parser("out", help="an issue out of a bin")
    for movement in (took, gave):
        movement.add_argument("day")
        movement.add_argument("name")
        movement.add_argument("sacks", type=int)
        movement.add_argument("--note", default="")

    counted = commands.add_parser("set-right", help="the stocktake correction")
    counted.add_argument("day")
    counted.add_argument("name")
    counted.add_argument("counted", type=int)

    commands.add_parser("stocktake", help="every bin as it stands")

    listed = commands.add_parser("movements", help="the door between two days")
    listed.add_argument("start")
    listed.add_argument("end")

    args = parser.parse_args(argv)
    the_book = ledger.load(args.book)

    if args.command == "open":
        book.open_bin(the_book, args.day, args.name, args.grain, args.sacks)
    elif args.command == "in":
        book.take_in(the_book, args.day, args.name, args.sacks, args.note)
    elif args.command == "out":
        book.give_out(the_book, args.day, args.name, args.sacks, args.note)
    elif args.command == "set-right":
        book.set_right(the_book, args.day, args.name, args.counted)
    elif args.command == "stocktake":
        print(report.stocktake(the_book))
        return
    else:
        for line in report.movements_between(the_book, args.start, args.end):
            print(
                f"{line['day']}  {line['bin']}  {line['kind']:>3}  "
                f"{line['sacks']} sack(s)  {line['note']}"
            )
        return

    ledger.save(the_book, args.book)


if __name__ == "__main__":
    main()
