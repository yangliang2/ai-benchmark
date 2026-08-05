# leaderboard

Standard-library standings for a small tournament ladder.

- `Player(name, points, bonus=0)` — a competitor and what they have scored
- `standings(players)` — the players in ranking order
- `top(players, count)` — the first `count` of them
- `rank_of(players, name)` — where one player places, counting from 1

Run the tests with `pytest`.
