# leftluggage

The station's left-luggage office, over `node:http` and the standard library
alone. There is nothing to install: no `package.json`, no `node_modules`.

- `tickets.ts` — how a ticket number is read off whatever somebody wrote it
  on, and how one bag is written up in the day book
- `shelf.ts` — a `Bag`, and the `Shelf` the office keeps them on: what stands
  against a ticket, what it weighed, and who left it
- `charges.ts` — the `Tariff` the office charges by, and `Charges`: what is
  owed on one bag and what has been paid on it
- `desk.ts` — the `Desk` the counter answers from, the request handler over it,
  and the `node:http` server that puts it on a port

The scales at the end of the counter are not always working. A bag nobody
wrote a weight down for has no charge against it: the counter asks nothing for
it, its ticket goes on the list to be put back on the scales, and the office
carries no charge for it until somebody has weighed it again.

Run the tests with `node --test`.

Start the service with `node desk.ts`. It listens on `PORT` where the
environment names one, and otherwise on the port `desk.ts` names itself.
