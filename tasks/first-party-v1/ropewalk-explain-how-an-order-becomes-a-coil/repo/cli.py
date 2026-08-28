"""How the clerk works the yard: one command, one change, saved and done."""

import argparse

import counter
import stores


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ropewalk", description=__doc__)
    parser.add_argument("--yard", default=stores.YARD_FILE, help="the yard file")
    commands = parser.add_subparsers(dest="command", required=True)

    ordered = commands.add_parser("order", help="take an order at the counter")
    ordered.add_argument("customer")
    ordered.add_argument("fathoms", type=int)
    ordered.add_argument("lay", choices=sorted(counter.STRANDS))

    put = commands.add_parser("put-up", help="a delivery of yarn onto the rack")
    put.add_argument("mark")
    put.add_argument("fathoms", type=int)

    commands.add_parser("rack", help="the yarn as it stands")
    commands.add_parser("book", help="every dispatch on the book")

    args = parser.parse_args(argv)
    yard = stores.load(args.yard)

    if args.command == "order":
        print(counter.take_order(yard, args.customer, args.fathoms, args.lay))
    elif args.command == "put-up":
        stores.put_up(yard, args.mark, args.fathoms)
    elif args.command == "rack":
        for bundle in yard["bundles"]:
            print(f"{bundle['mark']}  {bundle['fathoms']} fathom(s)")
        print(f"on hand  {stores.on_hand(yard)} fathom(s)")
        return
    else:
        for entry in yard["dispatches"]:
            print(
                f"{entry['tag']}  {entry['customer']}  asked {entry['asked']}, "
                f"walked {entry['walked']}  {entry['lay']}  "
                f"{entry['price_pence']}d"
            )
        return

    stores.save(yard, args.yard)


if __name__ == "__main__":
    main()
