# Engineering

Architecture, testing, and CI conventions. Freely editable.

## Layout

| Package | Axis | Responsibility |
|---|---|---|
| `fliphex/` | — | The game itself. Board, pieces, state, moves, rules, notation. Everything depends on this; it depends on nothing. |
| `solver/` | 1 | Alpha-beta, transposition tables, retrograde endgames, reduced variants. |
| `az/` | 2 | Network, PUCT MCTS, self-play, training, replay buffer. |
| `complexity/` | 3 | State-space and game-tree bounds, branching, cross-game comparison. |
| `agents/` | — | A single `Agent` interface. Random, heuristic, solver-backed, AZ-backed. |
| `stats/` | — | Wilson intervals, bootstrap, paired tests. |
| `ui/` | extras | CLI, pygame, replay viewer. |
| `scripts/` | — | Experiment entry points and documentation generators. |

**Dependency rule:** `fliphex/` imports nothing from the project. `solver/`,
`az/`, `complexity/` import `fliphex/` and never each other — that separation is
what keeps the cross-axis verification in Phase 5 honest. `agents/` may import
any of them.

## Core design decisions

Live in [`adr/`](adr/). The two that shape the most code:

- **[adr-003](adr/adr-003-piece-representation.md)** — placed tiles collapse to
  a colour; arrow patterns are 6-bit masks; hands are bitmasks. The state used
  for search must never contain a tile's identity or rotation.
- **[adr-002](adr/adr-002-coordinate-system.md)** — axial internally, `A1`–`E5`
  at every boundary, adjacency precomputed into a flat `25 × 6` table.

## Generated documentation

`docs/board-geometry.md` and `docs/piece-archetypes.md` are **generated** by
`scripts/build_docs.py`. Never edit them; edit the generator. They carry a
banner saying so.

Both generators are standalone — they do not import `fliphex/` — so the
canonical geometry can be regenerated and diffed independently of the engine.
From Phase 1, `tests/test_board.py` imports the generators and asserts the
engine agrees with them, and CI re-runs `build_docs.py` and fails if the working
tree is dirty. That is R12 in the risk register.

## Testing

`pytest`. The engine's test suite is the gate for Phase 1 and everything
downstream rests on it.

Required coverage:

- **Adjacency** — every cell's neighbour list, symmetry (`X→Y` in direction `d`
  iff `Y→X` in `d+3`), and off-board handling at all 16 border cells.
- **Rotation** — slot `i` at rotation `k` maps to direction `(i+k) mod 6`;
  orbit sizes match `piece-archetypes.md` (notably `P6` has 1 and `P3-tri` has
  2, so the move generator must deduplicate).
- **Flip logic** — flips are unconditional toggles (adr-007), one deep, and
  never chain; an arrow at your own tile is a self-flip to the opponent; arrows
  off the board or at empty cells do nothing.
- **Invariants I1–I6** from `rules-canonical.md`, asserted after every ply of a
  random game.
- **Joker** — no arrows, Player 1 only, flippable once placed, counted by
  colour at the end.
- **Termination** — every game is exactly 25 plies, the board ends full, and no
  game ends in a draw.
- **Property tests** — 1000 random games complete without error and satisfy all
  invariants at every ply.

## Style

- Python 3.12+. `ruff` for lint and format.
- Type hints throughout. `fliphex/` is the strictest module.
- Docstrings explain *why*, not *what*. The what is in the type signature.
- Frozen dataclasses for anything hashable.

## CI

GitHub Actions on push and PR:

1. `ruff check` and `ruff format --check`
2. `pytest`
3. `python scripts/build_docs.py && git diff --exit-code docs/`

Step 3 is what stops the generated docs from drifting.

## Reproducibility

Every experiment gets an entry in
[`experiments/registry.md`](../experiments/registry.md) **before it runs**, with
its seed, config, and the hypothesis it addresses. Results are appended after.
An experiment without a registry entry does not exist.
