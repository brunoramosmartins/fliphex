"""EXP-008 — how strong is an exact agent with no endgame database?

**Register this before running it.** See EXP-008 in ``experiments/registry.md``.

Phase 3's third exit criterion asks whether an *"alpha-beta agent + endgame
database"* beats random and heuristic play at 90% on the shipped 5×5. adr-012
cancelled the database on EXP-003's measurement, so the criterion names an
artefact that was deliberately not built. This runs the half that survives.

The number that must travel with the win rate
---------------------------------------------
On 25 cells with ``search_below_k = 8`` the agent can prove at most the last
eight plies; the rest are its fallback's. A win rate quoted alone would
therefore be largely a fact about ``HeuristicAgent``, which is precisely the
instrument defect ``agents/solver_agent.py`` exists to make visible. Every rate
here is reported with ``proved_rate`` beside it, and the artefact carries the
per-seat split so neither can be quoted without the other.

Seats are balanced deliberately
-------------------------------
H1 says the seat itself may carry an advantage. Playing the exact agent as P1
more often than the baseline would measure that advantage and call it strength,
so every pairing runs an equal number of games in each seat.

    pypy scripts/exp008_agent_strength.py
    pypy scripts/exp008_agent_strength.py --games 5      # smoke test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.heuristic_agent import HeuristicAgent  # noqa: E402
from agents.random_agent import RandomAgent  # noqa: E402
from agents.solver_agent import SolverAgent  # noqa: E402
from fliphex.moves import apply_move  # noqa: E402
from fliphex.rules import is_terminal, winner  # noqa: E402
from fliphex.state import Colour  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Never report a bare proportion (house rule)."""
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def play(board, root, exact, opponent, exact_is_first: bool):
    """One game. Returns True if the exact agent won."""
    first = root.to_move
    second = Colour(3 - first)
    seats = (
        {first: exact, second: opponent}
        if exact_is_first
        else {first: opponent, second: exact}
    )
    exact_colour = first if exact_is_first else second

    state = root
    while not is_terminal(state):
        state = apply_move(board, state, seats[state.to_move].select(board, state))
    return winner(state) == exact_colour


def run_pairing(variant, name, make_opponent, args) -> dict:
    board = variant.board()
    root = variant.initial_state()
    rows = []

    for seat, exact_is_first in (("P1", True), ("P2", False)):
        wins = 0
        proved = over_budget = unattempted = 0
        started = time.perf_counter()

        for game in range(args.games):
            # A fresh agent per game: the transposition table is shared across
            # moves within a game by design, but sharing it across games would
            # let game 250 profit from game 1 and make the per-game cost
            # unreportable.
            exact = SolverAgent(
                max_nodes=args.max_nodes,
                search_below_k=args.search_below_k,
                seed=args.seed + game,
                tt_bits=args.tt_bits,
            )
            opponent = make_opponent(args.seed + 10_000 + game)
            wins += play(board, root, exact, opponent, exact_is_first)
            proved += exact.proved
            over_budget += exact.over_budget
            unattempted += exact.unattempted

        elapsed = time.perf_counter() - started
        moves = proved + over_budget + unattempted
        low, high = wilson(wins, args.games)
        rows.append(
            {
                "opponent": name,
                "exact_seat": seat,
                "games": args.games,
                "wins": wins,
                "win_rate": wins / args.games,
                "wilson_low": low,
                "wilson_high": high,
                "moves": moves,
                "proved": proved,
                "delegated_over_budget": over_budget,
                "delegated_unattempted": unattempted,
                "proved_rate": proved / moves if moves else 0.0,
                "seconds": elapsed,
            }
        )
        print(
            f"    vs {name:<9} as {seat}  {wins:>4}/{args.games}  "
            f"{100 * wins / args.games:5.1f}%  "
            f"[{100 * low:5.1f}, {100 * high:5.1f}]  "
            f"proved {100 * rows[-1]['proved_rate']:4.1f}%  {elapsed:7.1f}s",
            flush=True,
        )
    return rows


def run_control(variant, args) -> dict:
    """HeuristicAgent against itself — the seat effect with no solver in it.

    Added 2026-08-30 **after** the treatment numbers were seen, and recorded as
    post hoc in the registry. It carries no decision rule and cannot be biased by
    knowing the treatment: it measures what the first seat is worth between two
    identical agents, which is the only way to read the exact agent's margin over
    the heuristic as *the value of perfect endgame play* rather than as the seat.
    Without it, 61% is a number with two explanations and no way to choose.
    """
    board = variant.board()
    root = variant.initial_state()
    wins = 0
    started = time.perf_counter()
    for game in range(args.games):
        first = HeuristicAgent(seed=args.seed + game)
        second = HeuristicAgent(seed=args.seed + 10_000 + game)
        wins += play(board, root, first, second, exact_is_first=True)
    elapsed = time.perf_counter() - started
    low, high = wilson(wins, args.games)
    print(
        f"\n    control: heuristic vs heuristic, first seat  "
        f"{wins:>4}/{args.games}  {100 * wins / args.games:5.1f}%  "
        f"[{100 * low:5.1f}, {100 * high:5.1f}]  {elapsed:7.1f}s",
        flush=True,
    )
    return {
        "pairing": "heuristic vs heuristic",
        "measures": "first-seat advantage with no solver involved",
        "post_hoc": True,
        "games": args.games,
        "first_seat_wins": wins,
        "first_seat_rate": wins / args.games,
        "wilson_low": low,
        "wilson_high": high,
        "seconds": elapsed,
    }


def run(args) -> dict:
    variant = Variant(args.board[0], args.board[1], Arm(args.arm))

    print(f"\n  === EXP-008 — exact agent strength, {variant.name} ===")
    print(
        f"  {variant.n_cells} cells, budget {args.max_nodes:,} nodes, "
        f"search below k = {args.search_below_k}"
    )
    print(f"  {args.games} games per (opponent x seat), seed {args.seed}")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}\n",
        flush=True,
    )

    started = time.perf_counter()
    rows: list[dict] = []
    rows += run_pairing(variant, "random", lambda s: RandomAgent(seed=s), args)
    rows += run_pairing(variant, "heuristic", lambda s: HeuristicAgent(seed=s), args)
    control = run_control(variant, args)
    elapsed = time.perf_counter() - started

    pooled = {}
    for name in ("random", "heuristic"):
        both = [r for r in rows if r["opponent"] == name]
        wins = sum(r["wins"] for r in both)
        n = sum(r["games"] for r in both)
        moves = sum(r["moves"] for r in both)
        proved = sum(r["proved"] for r in both)
        low, high = wilson(wins, n)
        pooled[name] = {
            "games": n,
            "wins": wins,
            "win_rate": wins / n,
            "wilson_low": low,
            "wilson_high": high,
            "proved_rate": proved / moves if moves else 0.0,
            # The registered rule reads the LOWER bound, not the point estimate.
            "clears_90_percent": low >= 0.90,
        }

    print()
    for name, row in pooled.items():
        print(
            f"    vs {name:<9} pooled  {row['wins']:>4}/{row['games']}  "
            f"{100 * row['win_rate']:5.1f}%  "
            f"[{100 * row['wilson_low']:5.1f}, {100 * row['wilson_high']:5.1f}]  "
            f"proved {100 * row['proved_rate']:4.1f}%  "
            f"{'CLEARS 90%' if row['clears_90_percent'] else 'below 90%'}"
        )
    print(f"\n    elapsed ............... {elapsed:,.1f}s")
    met = all(r["clears_90_percent"] for r in pooled.values())
    print(f"    exit criterion ........ {'MET' if met else 'NOT MET'}")
    print("    (a win rate here may not be quoted without proved_rate — the")
    print("     agent proves at most the last 8 plies and the rest is the")
    print("     fallback's play.)\n", flush=True)

    return {
        "experiment": "EXP-008",
        "variant": variant.name,
        "cells": variant.n_cells,
        "max_nodes": args.max_nodes,
        "search_below_k": args.search_below_k,
        "seed": args.seed,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "per_seat": rows,
        "pooled": pooled,
        "control": control,
        "exit_criterion_met": met,
        "seconds": elapsed,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 5], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--games", type=int, default=250, help="per opponent per seat")
    p.add_argument("--max-nodes", type=int, default=2_000_000)
    p.add_argument("--search-below-k", type=int, default=8)
    p.add_argument("--tt-bits", type=int, default=22)
    p.add_argument("--seed", type=int, default=5, help="registered: 5")
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    artefact = run(args)

    if not args.no_write:
        path = args.out / "exp008-agent-strength.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artefact, indent=2))
        print(f"    artefact -> {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
