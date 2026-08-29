"""How many generated moves reach a position another move already reached?

``fliphex.moves.legal_moves`` deduplicates rotations **statically**, once per
tile from its rotation orbit. Per *position* there is much more to collapse: a
tile's arrows only ever flip occupied neighbours, so two rotations of the same
tile on the same cell give the same child whenever their arrow sets meet the
occupied neighbours identically — and on an empty neighbourhood every rotation
does, the tile landing inert and indistinguishable from the joker.

The collapse does **not** cross tiles. Spending a different tile leaves a
different hand, so those children differ however alike the board looks.

Children are keyed by colours + hands + mover. ``history`` is deliberately
excluded: it is part of ``GameState.__eq__`` but not of the position, and
keying on it would count every path separately and report no collapse at all.

This is an instrument, not a registered experiment — it measures a property of
the rules and consumes no result files.

    pypy scripts/measure_move_collapse.py
    pypy scripts/measure_move_collapse.py --board 5 5 --games 24 --seed 11
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.rules import is_terminal  # noqa: E402
from fliphex.state import GameState  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402


def position_key(state: GameState):
    """Board identity: colours, hands, mover — the tuple a TT would hash."""
    return (state.colours, state.hands, state.to_move)


def profile(variant: Variant, games: int, rng: Random) -> dict[int, list[int]]:
    """Walk random games, counting generated vs distinct children per ply."""
    board = variant.board()
    rows: dict[int, list[int]] = {}
    for _ in range(games):
        state = variant.initial_state()
        ply = 0
        while not is_terminal(state):
            moves = legal_moves(board, state)
            children = {position_key(apply_move(board, state, m)) for m in moves}
            row = rows.setdefault(ply, [0, 0, 0])
            row[0] += len(moves)
            row[1] += len(children)
            row[2] += 1
            state = apply_move(board, state, rng.choice(moves))
            ply += 1
    return rows


def report(variant: Variant, games: int, seed: int) -> float:
    rows = profile(variant, games, Random(seed))
    print(f"\n  === move collapse — {variant.name}, {variant.n_cells} cells ===")
    print(f"  {games} random games, seed {seed}\n")
    print(f"  {'ply':>4} {'generated':>10} {'distinct':>10} {'collapse':>9}")
    total_generated = total_distinct = 0
    for ply in sorted(rows):
        generated, distinct, n = rows[ply]
        total_generated += generated
        total_distinct += distinct
        print(
            f"  {ply:>4} {generated / n:>10.1f} {distinct / n:>10.1f} "
            f"{generated / distinct:>8.2f}x"
        )
    overall = total_generated / total_distinct
    print(f"  {'ALL':>4} {total_generated:>10,} {total_distinct:>10,} {overall:>8.2f}x")
    return overall


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--board", type=int, nargs=2, default=None, metavar=("COLS", "ROWS"))
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--games", type=int, default=None)
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()

    if args.board is None:
        # The two boards that matter: the shipped game and the solve target.
        report(Variant(5, 5, Arm(args.arm)), args.games or 12, args.seed)
        report(Variant(5, 3, Arm(args.arm)), args.games or 40, args.seed)
    else:
        report(
            Variant(args.board[0], args.board[1], Arm(args.arm)),
            args.games or 12,
            args.seed,
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
