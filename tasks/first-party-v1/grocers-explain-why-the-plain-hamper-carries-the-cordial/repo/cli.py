"""How the back room works the day's book: make up every hamper, then
write out every docket."""

import argparse
import json
from pathlib import Path

import docket
import hampers

BOOK_FILE = "orders.json"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="grocers", description=__doc__)
    parser.add_argument("--book", default=BOOK_FILE, help="the day's order book")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("book", help="the orders as they came in")
    commands.add_parser("make-up", help="make up the book and write the dockets")

    args = parser.parse_args(argv)
    book = json.loads(Path(args.book).read_text(encoding="utf-8"))

    if args.command == "book":
        for order in book["orders"]:
            kind = "bespoke" if "wants" in order else "standard"
            extras = ", ".join(order.get("extras", [])) or "none"
            print(f"{order['customer']}  {kind}  extras: {extras}")
        return

    # The van is loaded in one go, so the whole book is made up first
    # and the dockets are written out together at the end.
    made = []
    for order in book["orders"]:
        hamper = hampers.make_up(order["customer"], order.get("wants"))
        for item in order.get("extras", []):
            hampers.add_extra(hamper, item)
        made.append(hamper)

    for hamper in made:
        print(docket.docket(hamper))
        print()


if __name__ == "__main__":
    main()
