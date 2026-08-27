"""How the clerk works the book: one command, one change, saved and done."""

import argparse

import basket
import book
import door
import tally


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="almshouse", description=__doc__)
    parser.add_argument("--book", default=book.BOOK_FILE, help="the book file")
    commands = parser.add_subparsers(dest="command", required=True)

    gave = commands.add_parser("give", help="a dole handed out at the door")
    gave.add_argument("day")
    gave.add_argument("who")
    gave.add_argument("kind")
    gave.add_argument("--note", default="")

    refused = commands.add_parser("refuse", help="a dole asked for and not given")
    refused.add_argument("day")
    refused.add_argument("who")
    refused.add_argument("kind")
    refused.add_argument("--note", required=True)

    dayed = commands.add_parser("day", help="a day's doles as they stand")
    dayed.add_argument("day")

    storied = commands.add_parser("history", help="one person's entries, whole")
    storied.add_argument("who")

    commands.add_parser("often", help="everyone in the book, counted")
    commands.add_parser("doles", help="the table of doles as it stands")

    args = parser.parse_args(argv)
    the_book = book.load(args.book)

    if args.command == "give":
        door.give(the_book, args.day, args.who, args.kind, args.note)
    elif args.command == "refuse":
        door.refuse(the_book, args.day, args.who, args.kind, args.note)
    elif args.command == "day":
        for entry in tally.helped(the_book, args.day):
            note = f"  ({entry['note']})" if entry["note"] else ""
            print(f"{entry['who']}  {entry['kind']}{note}")
        return
    elif args.command == "history":
        for entry in tally.history(the_book, args.who):
            note = f"  ({entry['note']})" if entry["note"] else ""
            print(f"{entry['day']}  {entry['kind']}{note}")
        return
    elif args.command == "often":
        for who, count in sorted(tally.often(the_book).items()):
            print(f"{who}  {count} entr(ies)")
        return
    else:
        for kind in basket.kinds():
            print(f"{kind}  {basket.DOLES[kind]}")
        return

    book.save(the_book, args.book)


if __name__ == "__main__":
    main()
