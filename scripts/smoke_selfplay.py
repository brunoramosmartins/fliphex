"""Play many random games and assert the engine's invariants hold throughout.

Covers the Phase 1 exit criterion "1000 random-vs-random games run without
errors". Kept out of the pytest suite so the suite stays fast; run it directly:

    python scripts/smoke_selfplay.py            # 1000 games
    python scripts/smoke_selfplay.py 5000 --seed 1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random  # noqa: E402

from fliphex.board import Board  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.rules import winner  # noqa: E402
from fliphex.state import Colour, GameState  # noqa: E402


def _check_invariants(state: GameState, ply: int) -> None:
    assert state.ply() == ply, f"I1: ply {state.ply()} != {ply}"
    remaining = bin(state.hand(Colour.PURPLE)).count("1") + bin(
        state.hand(Colour.GREEN)
    ).count("1")
    assert ply + remaining == 25, f"I5: placed {ply} + hand {remaining} != 25"


def play_random_game(board: Board, rng: random.Random, first: Colour) -> Colour:
    """Play one uniform-random game, asserting invariants at every ply."""
    state = GameState.initial(board.n_cells, first)
    ply = 0
    while not state.is_terminal():
        _check_invariants(state, ply)
        moves = legal_moves(board, state)
        assert moves, "I4: no legal move but board not full"
        state = apply_move(board, state, rng.choice(moves))
        ply += 1
    assert ply == 25, f"game ended in {ply} plies, expected 25"
    assert Colour.EMPTY not in state.colours, "I2: board not full at end"
    purple, green = state.score()
    assert purple + green == 25 and purple != green, "scoring or no-draw violated"
    assert len(state.history) == 25
    return winner(state)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Random self-play smoke test.")
    parser.add_argument("games", type=int, nargs="?", default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    board = Board()
    rng = random.Random(args.seed)
    wins = {Colour.PURPLE: 0, Colour.GREEN: 0}

    start = time.perf_counter()
    for i in range(args.games):
        first = Colour.PURPLE if i % 2 == 0 else Colour.GREEN
        wins[play_random_game(board, rng, first)] += 1
    elapsed = time.perf_counter() - start

    p, g = wins[Colour.PURPLE], wins[Colour.GREEN]
    print(f"{args.games} games OK in {elapsed:.2f}s — all invariants held")
    print(f"wins: PURPLE {p} ({p / args.games:.1%})  GREEN {g} ({g / args.games:.1%})")


if __name__ == "__main__":
    main()
