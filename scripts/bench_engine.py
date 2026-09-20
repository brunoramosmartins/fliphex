"""Time the engine, so a port can be designed against a number rather than a guess.

Every workload here is **pure standard library** and touches only ``fliphex``,
``solver`` and ``az.mcts``. That is what makes it the same instrument in both
environments: CPython runs it directly, and Pyodide runs *this file* unmodified
inside WebAssembly. Nothing is extrapolated across the boundary, because
extrapolating a cost across a boundary is what this project has now got wrong
twice — Phase 4's composed pipeline was 4.9x off, and EXP-007's closure was out
by more than a factor of four.

Usage::

    python scripts/bench_engine.py                # everything
    python scripts/bench_engine.py --quick        # the fast workloads only
    python scripts/bench_engine.py --json         # machine-readable

The browser harness that runs it under Pyodide lives outside the repository,
because it needs an ``npm install``; this file is the part that has to be
identical on both sides, so this is the part that is tracked.

Reading the output
------------------
``rate`` is the honest headline for the throughput workloads and ``seconds`` for
the whole-game ones. The ratio between two environments is the only thing a
design decision should rest on: an absolute number here describes this machine.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import time
from collections.abc import Callable
from typing import Any

from agents.heuristic_agent import HeuristicAgent
from fliphex.moves import apply_move, legal_moves
from fliphex.variant import FULL_GAME, THREE_BY_THREE, Variant

#: Workloads that finish in well under a second even on a slow interpreter.
QUICK = ("legal_moves_opening", "apply_move", "random_playout", "heuristic_game")


def _time(work: Callable[[], int], budget: float) -> tuple[int, float]:
    """Run ``work`` until ``budget`` seconds have passed; return (units, seconds).

    ``work`` returns how many units it did, so a workload whose natural grain is
    a game and one whose grain is a move can share a timer.
    """
    units = 0
    start = time.perf_counter()
    while True:
        units += work()
        elapsed = time.perf_counter() - start
        if elapsed >= budget:
            return units, elapsed


# -- workloads ----------------------------------------------------------------


def bench_legal_moves(variant: Variant, budget: float) -> dict[str, Any]:
    """Move generation at the opening — 1,450 moves on the shipped board.

    The single hottest call in every agent and every search.
    """
    board, state = variant.board(), variant.initial_state()
    width = len(legal_moves(board, state))

    def once() -> int:
        legal_moves(board, state)
        return width

    moves, seconds = _time(once, budget)
    return {"unit": "moves", "count": moves, "seconds": seconds, "width": width}


def bench_apply_move(variant: Variant, budget: float) -> dict[str, Any]:
    """Applying a move: the arrow sweep and the state rebuild."""
    board, state = variant.board(), variant.initial_state()
    moves = legal_moves(board, state)

    def once() -> int:
        for move in moves[:100]:
            apply_move(board, state, move)
        return min(100, len(moves))

    applied, seconds = _time(once, budget)
    return {"unit": "moves", "count": applied, "seconds": seconds}


def bench_random_playout(variant: Variant, budget: float) -> dict[str, Any]:
    """A full uniform-random game — the leaf evaluation prior-free UCT uses.

    At most one ply per empty cell, always terminating, always decided: a draw
    is impossible on an odd cell count.
    """
    board = variant.board()
    rng = random.Random(0)

    def once() -> int:
        state = variant.initial_state()
        while not state.is_terminal():
            state = apply_move(board, state, rng.choice(legal_moves(board, state)))
        return 1

    games, seconds = _time(once, budget)
    return {"unit": "games", "count": games, "seconds": seconds}


def bench_heuristic_game(variant: Variant, budget: float) -> dict[str, Any]:
    """A complete game between two flip-maximisers — the web build's first seat."""
    board = variant.board()
    purple, green = HeuristicAgent(seed=0), HeuristicAgent(seed=1)

    def once() -> int:
        state = variant.initial_state()
        while not state.is_terminal():
            mover = purple if state.to_move == 1 else green
            state = apply_move(board, state, mover.select(board, state))
        return 1

    games, seconds = _time(once, budget)
    return {"unit": "games", "count": games, "seconds": seconds}


def bench_uct_move(variant: Variant, budget: float, simulations: int = 100) -> dict:
    """One prior-free UCT move: tree search with random-rollout leaves.

    ``az.mcts`` is pure standard library — only the *network* evaluator needs
    torch — so the search itself is portable and this measures it honestly. A
    learned agent adds an inference cost on top of this number, not instead
    of it.
    """
    from az.mcts import MCTS

    board, state = variant.board(), variant.initial_state()

    def once() -> int:
        MCTS(board, seed=0).run(state, simulations)
        return 1

    moves, seconds = _time(once, budget)
    return {
        "unit": "moves",
        "count": moves,
        "seconds": seconds,
        "simulations": simulations,
    }


def bench_solve_3x3(variant: Variant, budget: float) -> dict[str, Any]:
    """Prove the 3x3 opening outright. The board a browser could play perfectly.

    Not a throughput measure — one solve, reported in seconds, because that is
    what a player waits for.
    """
    from solver.minimax import Solver

    board = THREE_BY_THREE.board()
    start = time.perf_counter()
    result = Solver(board).solve(THREE_BY_THREE.initial_state())
    seconds = time.perf_counter() - start
    return {
        "unit": "solves",
        "count": 1,
        "seconds": seconds,
        "value": str(result.value),
    }


WORKLOADS: dict[str, Callable[..., dict[str, Any]]] = {
    "legal_moves_opening": bench_legal_moves,
    "apply_move": bench_apply_move,
    "random_playout": bench_random_playout,
    "heuristic_game": bench_heuristic_game,
    "uct_move_100sims": bench_uct_move,
    "solve_3x3": bench_solve_3x3,
}

#: Which board each workload is measured on. The solve is pinned to the 3x3
#: because it is the only board a solve finishes on.
BOARDS: dict[str, Variant] = {
    "legal_moves_opening": FULL_GAME,
    "apply_move": FULL_GAME,
    "random_playout": FULL_GAME,
    "heuristic_game": FULL_GAME,
    "uct_move_100sims": FULL_GAME,
    "solve_3x3": THREE_BY_THREE,
}


def run(names: list[str], budget: float) -> dict[str, Any]:
    """Run the named workloads and return one record."""
    results: dict[str, Any] = {}
    for name in names:
        measured = WORKLOADS[name](BOARDS[name], budget)
        measured["rate"] = measured["count"] / measured["seconds"]
        measured["board"] = BOARDS[name].name
        results[name] = measured
    return {
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": sys.platform,
            # Pyodide sets this; CPython on Linux does not.
            "emscripten": sys.platform == "emscripten",
        },
        "budget_seconds": budget,
        "workloads": results,
    }


def render(record: dict[str, Any]) -> str:
    """A table, for reading rather than for parsing."""
    env = record["environment"]
    lines = [
        "",
        f"  {env['implementation']} {env['python']} on {env['platform']}",
        "",
        f"  {'workload':<22} {'board':<8} {'rate':>16}  unit",
        f"  {'-' * 22} {'-' * 8} {'-' * 16}  {'-' * 12}",
    ]
    for name, measured in record["workloads"].items():
        lines.append(
            f"  {name:<22} {measured['board']:<8} "
            f"{measured['rate']:>16,.1f}  {measured['unit']}/s"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="skip the slow workloads")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument(
        "--budget",
        type=float,
        default=1.0,
        help="seconds per throughput workload (default 1.0)",
    )
    parser.add_argument("--only", help="one workload by name")
    args = parser.parse_args(argv)

    if args.only:
        if args.only not in WORKLOADS:
            print(f"  no workload {args.only!r}; have {sorted(WORKLOADS)}")
            return 1
        names = [args.only]
    else:
        names = list(QUICK) if args.quick else list(WORKLOADS)

    record = run(names, args.budget)
    print(json.dumps(record) if args.json else render(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
