"""How the shed works the book: one command, one change, saved and done."""

import argparse

import boards
import shedbook


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tramshed", description=__doc__)
    parser.add_argument("--book", default=shedbook.BOOK_FILE, help="the shed book")
    commands = parser.add_subparsers(dest="command", required=True)

    entered = commands.add_parser("enter", help="chalk one working into the book")
    entered.add_argument("car", type=int)
    entered.add_argument("end", choices=shedbook.ENDS)
    entered.add_argument("leaves")

    commands.add_parser("town", help="the town-end board")
    commands.add_parser("quay", help="the quay-end board")
    commands.add_parser("book", help="the workings as they were chalked")

    args = parser.parse_args(argv)
    book = shedbook.load(args.book)

    if args.command == "enter":
        shedbook.enter(book, args.car, args.end, args.leaves)
        shedbook.save(book, args.book)
        return

    if args.command == "town":
        for working in boards.town_board(book):
            print(f"car {working['car']}  leaves {working['leaves']}")
    elif args.command == "quay":
        for working in boards.quay_board(book):
            print(f"car {working['car']}  leaves {working['leaves']}")
    else:
        for working in book["workings"]:
            print(
                f"car {working['car']}  {working['end']} end  "
                f"leaves {working['leaves']}"
            )


if __name__ == "__main__":
    main()
