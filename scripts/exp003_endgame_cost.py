"""EXP-003 — does searching the endgame beat storing it?

Registered in ``experiments/registry.md`` before this script existed. It decides
`adr-012 <../docs/adr/adr-012-endgame-database-storage.md>`_ between Option A
(build a retrograde database) and Option B (don't; search the endgame exactly on
demand, as Othello was solved).

The question, precisely: at how many empty cells ``k`` does an exact search below
a position stop being cheap? The pre-registered **decision rule** is

    if the MEDIAN exact search at k costs under 10**6 nodes,
    no database is built for that k.

and ``k*`` is the smallest ``k`` whose median exceeds it. The pre-registered
**prediction** is ``k* >= 6``, i.e. the roadmap's ``k <= 5`` target — some
1.2 x 10**15 positions, ~150 TB at one bit — is not worth materialising.

Three things the registry entry fixes, restated here because they are easy to
"improve" into meaninglessness:

* **Sampling is by random playout**, which does *not* sample uniformly from
  reachable positions — it samples uniformly from random-play trajectories, and
  positions from random play may be systematically easier or harder than those a
  real search meets. The method stays as registered; the bias is reported with
  the result and not corrected in analysis.
* **Every sampled position gets a fresh table.** Sharing one would amortise work
  across samples, which is exactly what a database does, and would bias the
  comparison toward "searching is cheap". A fresh table is search's worst case,
  so a result favouring search is conservative.
* **Censoring is reported.** A sample over ``--max-nodes`` is recorded at the
  budget, so a median computed over censored samples is a *lower bound* — enough
  for a rule that only asks whether the median clears 10**6.

    python scripts/exp003_endgame_cost.py
    python scripts/exp003_endgame_cost.py --k-max 8 --samples 50
    python scripts/exp003_endgame_cost.py --out results/exp003.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.state import GameState  # noqa: E402
from fliphex.variant import FULL_GAME  # noqa: E402
from solver.minimax import BudgetExceededError, Solver  # noqa: E402
from solver.transposition import NullTable, TranspositionTable  # noqa: E402

#: The pre-registered threshold, in nodes. Not a tuning knob.
THRESHOLD = 10**6


@dataclass
class Sample:
    """One solved endgame position."""

    nodes: int
    seconds: float
    censored: bool


@dataclass
class Measurement:
    """All samples at one value of ``k``."""

    k: int
    with_tt: list[Sample] = field(default_factory=list)
    without_tt: list[Sample] = field(default_factory=list)

    @staticmethod
    def _summary(samples: list[Sample]) -> dict[str, float | int | bool]:
        nodes = sorted(s.nodes for s in samples)
        censored = sum(s.censored for s in samples)
        return {
            "n": len(samples),
            "median": statistics.median(nodes),
            "p90": nodes[min(len(nodes) - 1, int(0.9 * len(nodes)))],
            "max": nodes[-1],
            "total_seconds": sum(s.seconds for s in samples),
            "censored": censored,
            # A median over censored samples understates the truth.
            "median_is_lower_bound": censored > len(samples) // 2,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "k": self.k,
            "with_tt": self._summary(self.with_tt),
            "without_tt": self._summary(self.without_tt),
        }

    @property
    def median_with_tt(self) -> float:
        return statistics.median(s.nodes for s in self.with_tt)


def sample_position(board, rng: Random, plies: int) -> GameState:
    """Return a position ``plies`` moves into a uniformly random legal game."""
    state = FULL_GAME.initial_state()
    for _ in range(plies):
        moves = legal_moves(board, state)
        state = apply_move(board, state, rng.choice(moves))
    return state


def solve_one(board, state: GameState, use_tt: bool, max_nodes: int) -> Sample:
    """Solve one position exactly, or record it as censored at the budget."""
    table = TranspositionTable(1 << 16) if use_tt else NullTable()
    solver = Solver(board, tt=table, max_nodes=max_nodes)
    started = time.perf_counter()
    try:
        solver.solve(state)
        censored = False
    except BudgetExceededError:
        censored = True
    elapsed = time.perf_counter() - started
    return Sample(nodes=solver.stats.nodes, seconds=elapsed, censored=censored)


def measure(board, k: int, samples: int, seed: int, max_nodes: int) -> Measurement:
    """Sample and solve ``samples`` positions with ``k`` empty cells."""
    plies = board.n_cells - k
    # Seeded per k so that adding a k to the sweep does not shift the others.
    rng = Random(seed * 1000 + k)
    out = Measurement(k=k)
    for i in range(samples):
        state = sample_position(board, rng, plies)
        out.with_tt.append(solve_one(board, state, True, max_nodes))
        out.without_tt.append(solve_one(board, state, False, max_nodes))
        print(
            f"    k={k}  {i + 1}/{samples}"
            f"  tt={out.with_tt[-1].nodes:>10,}"
            f"  raw={out.without_tt[-1].nodes:>12,}",
            end="\r",
            flush=True,
        )
    print(" " * 70, end="\r")
    return out


def report(results: list[Measurement], threshold: int) -> int | None:
    """Print the table and apply the pre-registered decision rule."""
    print()
    print("  EXP-003 — exact endgame search cost on the shipped 5x5")
    print("  " + "-" * 68)
    print(
        f"  {'k':>3} {'ply':>4} {'median (TT)':>13} {'p90 (TT)':>12} "
        f"{'median (raw)':>14} {'cens':>7}"
    )
    print("  " + "-" * 68)
    for m in results:
        row = m.as_dict()
        tt, raw = row["with_tt"], row["without_tt"]
        # Both arms, never just one: showing only the with-TT count once printed
        # "cens 0" on a k where the no-TT arm had a censored sample. Censoring
        # that a run can hide is worse than censoring it reports.
        censored = f"{tt['censored']}/{raw['censored']}"
        flag = "  <== over threshold" if m.median_with_tt >= threshold else ""
        print(
            f"  {m.k:>3} {25 - m.k:>4} {tt['median']:>13,.0f} {tt['p90']:>12,.0f} "
            f"{raw['median']:>14,.0f} {censored:>7}{flag}"
        )

    over = [m.k for m in results if m.median_with_tt >= threshold]
    k_star = min(over) if over else None

    print()
    print(f"  decision rule: build no database for any k whose median < {threshold:,}")
    if k_star is None:
        print(f"  -> no k in this sweep exceeds the threshold. k* > {results[-1].k}.")
        print("     adr-012 Option B: ship no endgame database, and record that")
        print("     H3 loses its 5x5 endgame-layer comparison member.")
    else:
        print(f"  -> k* = {k_star}")
        if k_star >= 6:
            print("     The pre-registered prediction (k* >= 6) holds: the")
            print("     roadmap's k <= 5 target is not worth materialising.")
        else:
            print("     The pre-registered prediction (k* >= 6) is REFUTED.")
            print("     Report it as such — do not re-run with other settings.")
    print()
    print("  Sampling is by random playout, which samples random-play")
    print("  trajectories rather than reachable positions uniformly. Positions")
    print("  from random play may differ systematically from those a real")
    print("  search meets. Registered that way; carried with the result.")
    return k_star


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--k-min", type=int, default=3, help="smallest k (default 3)")
    p.add_argument("--k-max", type=int, default=6, help="largest k (default 6)")
    p.add_argument(
        "--samples", type=int, default=200, help="positions per k (default 200)"
    )
    p.add_argument("--seed", type=int, default=1, help="RNG seed (registered: 1)")
    p.add_argument(
        "--max-nodes",
        type=int,
        default=2 * THRESHOLD,
        help="per-position node budget; samples above it are censored "
        f"(default {2 * THRESHOLD:,}, i.e. twice the decision threshold)",
    )
    p.add_argument("--out", type=Path, help="write the raw results as JSON")
    args = p.parse_args()

    if args.k_min < 1 or args.k_max < args.k_min:
        p.error("need 1 <= --k-min <= --k-max")

    board = FULL_GAME.board()
    print(f"  board: {board.n_cells} cells, hands 13 + 12, seed {args.seed}")
    print(f"  {args.samples} positions per k, budget {args.max_nodes:,} nodes each")

    results = [
        measure(board, k, args.samples, args.seed, args.max_nodes)
        for k in range(args.k_min, args.k_max + 1)
    ]
    k_star = report(results, THRESHOLD)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "experiment": "EXP-003",
                    "board_cells": board.n_cells,
                    "hands": [13, 12],
                    "seed": args.seed,
                    "samples_per_k": args.samples,
                    "max_nodes": args.max_nodes,
                    "threshold": THRESHOLD,
                    "k_star": k_star,
                    "sampling": "random playout (see registry: known bias)",
                    "results": [m.as_dict() for m in results],
                },
                indent=2,
            )
        )
        print(f"  raw results -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
