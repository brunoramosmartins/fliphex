"""EXP-010 — deduplicated MCTS expansion against the naive tree.

**Registered before this file existed.** See EXP-010 in
``experiments/registry.md``, which is the authority on every number below; this
script implements that entry and nothing else. Where the two disagree, the entry
is right and this is a bug.

What it does not decide
-----------------------
adr-005's Phase 3 amendment already *requires* by-position expansion. This
measures what that buys and separates it from what merely having fewer children
buys — it does not choose between the designs, and its only channel to change
anything is the pre-registered falsifier.

Why three arms
--------------
``ACTION`` is the deployed-naive baseline. ``POSITION`` is the ADR's design.
``MULTIPLICITY`` keeps every action a child but divides priors by alias
multiplicity: without it, a win for POSITION at a small budget is fully
explained by "~4x fewer children, one pass finishes" — an effect obtainable by
deleting three quarters of ACTION's children at random.

Why the sample is restricted to WIN positions
---------------------------------------------
In a position that is a loss for the side to move, **no optimal move exists**,
so every arm scores zero deterministically and the pooled metric becomes a
parity-weighted mixture of degenerate cases. The restriction is a declared
domain, fixed before any run, not a filter applied after seeing results.

    pypy scripts/exp010_mcts_dedup.py --smoke     # minutes
    pypy scripts/exp010_mcts_dedup.py             # the registered run
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from az.mcts import (  # noqa: E402
    MCTS,
    ExpansionMode,
    best_move,
    group_by_position,
)
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

#: Pinned by the registry. The run aborts rather than reading a different arm.
EXPECTED_V5 = "51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43"

#: Registered: seed 17, layers t = 5..14, 300 per layer, primary at budget 400.
SEED = 17
LAYERS = tuple(range(5, 15))
PER_LAYER = 300
BUDGETS = (100, 400, 1600)
PRIMARY_BUDGET = 400


def verify_ground_truth(path: Path) -> dict:
    """Read the solution artefact and check its V5 digest against the registry.

    Provenance, not correctness: it proves which artefact was read, which is
    what "5x3-h2" alone does not say.
    """
    artefact = json.loads(path.read_text())
    digest = artefact["verification"]["V5_checksum_sha256"]
    if digest != EXPECTED_V5:
        raise SystemExit(
            f"ground-truth digest mismatch\n  expected {EXPECTED_V5}\n  found    "
            f"{digest}\nThe registry pins the arm this experiment reads."
        )
    if artefact["termination"] != "exhausted":
        raise SystemExit("adr-004 R1: only an exhausted solve may ground an axis")
    return artefact


# -- statistics ---------------------------------------------------------------


def mcnemar(a_hits: list[bool], b_hits: list[bool]) -> dict:
    """Paired comparison of two arms on the same positions.

    Reports the discordant counts, because they — not the sample size — set the
    power, and the registry commits to recomputing the detectable difference
    from the realised discordance rather than reinterpreting the threshold.
    """
    n = len(a_hits)
    b_only = sum(1 for x, y in zip(a_hits, b_hits, strict=True) if x and not y)
    c_only = sum(1 for x, y in zip(a_hits, b_hits, strict=True) if y and not x)
    discordant = b_only + c_only
    diff = (c_only - b_only) / n if n else 0.0

    if discordant:
        chi2 = (abs(b_only - c_only) - 1) ** 2 / discordant
        var = (discordant - (c_only - b_only) ** 2 / n) / (n * n)
        half = 1.96 * math.sqrt(max(var, 0.0))
    else:
        chi2, half = 0.0, 0.0

    return {
        "n": n,
        "a_only": b_only,
        "b_only": c_only,
        "discordant": discordant,
        "discordant_rate": discordant / n if n else 0.0,
        "difference": diff,
        "ci_low": diff - half,
        "ci_high": diff + half,
        "chi2": chi2,
        # The registered falsifier is a NON-INFERIORITY test: the interval must
        # lie below -2 points, not below zero.
        "below_minus_2_margin": (diff + half) < -0.02,
    }


def detectable_difference(discordant_rate: float, n: int) -> float:
    """The difference McNemar resolves at 80% power, two-sided 5%.

    Reported so the achieved power is a measured number rather than the
    planning assumption. Solved numerically from the same expression used to
    size the run.
    """
    if discordant_rate <= 0 or n <= 0:
        return 1.0
    z_a, z_b = 1.96, 0.8416
    lo, hi = 1e-5, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        need = (
            z_a * math.sqrt(discordant_rate)
            + z_b * math.sqrt(max(discordant_rate - mid * mid, 1e-12))
        ) ** 2 / (mid * mid)
        if need > n:
            lo = mid
        else:
            hi = mid
    return hi


# -- the sample ---------------------------------------------------------------


def draw_layer(reader: SweepReader, t: int, count: int, rng: random.Random) -> list:
    """Draw ``count`` distinct WIN positions from layer ``t`` by rejection."""
    index = reader.index[t]
    size = index.size
    layer = reader.layer(t)
    seen: set[int] = set()
    drawn = []
    attempts = 0
    while len(drawn) < count:
        attempts += 1
        if attempts > count * 5000:
            raise SystemExit(f"layer {t}: could not draw {count} WIN positions")
        i = rng.randrange(size)
        if i in seen:
            continue
        seen.add(i)
        if reader.sweep.get(layer, i) != SLOT_WIN:
            continue
        drawn.append((i, index.decode(i)))
    return drawn, attempts


def optimal_moves(board, reader: SweepReader, state):
    """Every move whose resulting position the database calls a loss.

    Returns the set of optimal moves and the count of distinct optimal
    *positions*, because the registry defines the floor over actions (what a
    random agent would do) and the aliasing diagnostic over positions.
    """
    moves = legal_moves(board, state)
    best = set()
    for move in moves:
        if reader.slot(apply_move(board, state, move)) == SLOT_LOSS:
            best.add(move)
    return moves, best


def aliased_mass(board, state, moves) -> float:
    """Share of action labels beyond the first in their position class."""
    classes = group_by_position(board, state, moves)
    total = sum(len(c) for c in classes)
    return sum(len(c) - 1 for c in classes) / total if total else 0.0


# -- the run ------------------------------------------------------------------


def run(args) -> dict:
    variant = Variant(5, 3, Arm("h2"))
    board = variant.board()

    artefact = verify_ground_truth(Path(args.solution))
    reader = SweepReader(variant, Checkpoint(Path(args.checkpoint) / variant.name))
    rng = random.Random(args.seed)

    layers = LAYERS if not args.smoke else (5, 9, 13)
    per_layer = args.per_layer
    budgets = BUDGETS if not args.smoke else (args.primary_budget,)

    print(f"\n  === EXP-010 — deduplicated MCTS expansion, {variant.name} ===")
    print(f"  ground truth V5 {EXPECTED_V5[:16]}… ({artefact['termination']})")
    print(f"  layers {layers[0]}..{layers[-1]}, {per_layer}/layer, seed {args.seed}")
    print(f"  budgets {budgets}, primary {args.primary_budget}")
    print(
        f"  interpreter {sys.implementation.name} {sys.version.split()[0]}\n",
        flush=True,
    )

    rows: list[dict] = []
    started = time.perf_counter()

    for t in layers:
        drawn, attempts = draw_layer(reader, t, per_layer, rng)
        t0 = time.perf_counter()

        for _rank, state in drawn:
            moves, best = optimal_moves(board, reader, state)
            row = {
                "t": t,
                "n_actions": len(moves),
                "n_optimal_actions": len(best),
                "random_floor": len(best) / len(moves),
                "aliased_mass": aliased_mass(board, state, moves),
                "hits": {},
                "seconds": {},
            }
            for budget in budgets:
                for mode in ExpansionMode:
                    search = MCTS(
                        board, mode=mode, seed=args.seed + t, c_puct=args.c_puct
                    )
                    s0 = time.perf_counter()
                    root = search.run(state, budget)
                    row["seconds"][f"{mode.value}@{budget}"] = time.perf_counter() - s0
                    row["hits"][f"{mode.value}@{budget}"] = best_move(root) in best
            rows.append(row)

        el = time.perf_counter() - t0
        floor = sum(r["random_floor"] for r in rows[-per_layer:]) / per_layer
        alias = sum(r["aliased_mass"] for r in rows[-per_layer:]) / per_layer
        hit = {
            m.value: sum(
                r["hits"][f"{m.value}@{args.primary_budget}"] for r in rows[-per_layer:]
            )
            / per_layer
            for m in ExpansionMode
        }
        print(
            f"    t={t:<3} floor {100 * floor:5.1f}%  alias {100 * alias:5.1f}%  "
            f"A {100 * hit['action']:5.1f}%  B {100 * hit['position']:5.1f}%  "
            f"C {100 * hit['multiplicity']:5.1f}%   {el:7.1f}s  "
            f"({attempts} draws)",
            flush=True,
        )
        reader.release()

    elapsed = time.perf_counter() - started
    return summarise(rows, budgets, args, artefact, elapsed)


def summarise(rows, budgets, args, artefact, elapsed) -> dict:
    def hits(mode, budget):
        return [r["hits"][f"{mode.value}@{budget}"] for r in rows]

    per_budget = {}
    for budget in budgets:
        rates = {m.value: sum(hits(m, budget)) / len(rows) for m in ExpansionMode}
        comparisons = {
            "B_vs_A": mcnemar(
                hits(ExpansionMode.ACTION, budget), hits(ExpansionMode.POSITION, budget)
            ),
            "B_vs_C": mcnemar(
                hits(ExpansionMode.MULTIPLICITY, budget),
                hits(ExpansionMode.POSITION, budget),
            ),
            "C_vs_A": mcnemar(
                hits(ExpansionMode.ACTION, budget),
                hits(ExpansionMode.MULTIPLICITY, budget),
            ),
        }
        for name, cmp in comparisons.items():
            cmp["detectable_at_80_power"] = detectable_difference(
                cmp["discordant_rate"], cmp["n"]
            )
            comparisons[name] = cmp
        per_budget[budget] = {
            "top1_optimality": rates,
            "comparisons": comparisons,
            # Tree cost only. There is no network here, so inference cost is
            # absent by construction and must not be inferred from this.
            "seconds_per_search": {
                m.value: sum(r["seconds"][f"{m.value}@{budget}"] for r in rows)
                / len(rows)
                for m in ExpansionMode
            },
        }

    by_layer = {}
    for t in sorted({r["t"] for r in rows}):
        sub = [r for r in rows if r["t"] == t]
        by_layer[t] = {
            "n": len(sub),
            "random_floor": sum(r["random_floor"] for r in sub) / len(sub),
            "aliased_mass": sum(r["aliased_mass"] for r in sub) / len(sub),
            "top1_optimality": {
                m.value: sum(r["hits"][f"{m.value}@{args.primary_budget}"] for r in sub)
                / len(sub)
                for m in ExpansionMode
            },
        }

    primary = per_budget[args.primary_budget]
    b_vs_a = primary["comparisons"]["B_vs_A"]
    overhead = (
        primary["seconds_per_search"]["position"]
        / primary["seconds_per_search"]["action"]
        - 1
    )

    floor = 100 * sum(r["random_floor"] for r in rows) / len(rows)
    alias = 100 * sum(r["aliased_mass"] for r in rows) / len(rows)

    print(f"\n    pooled at the primary budget ({args.primary_budget}):")
    print(f"      random floor ......... {floor:5.1f}%")
    print("      exact ceiling ........ 100.0%  (by construction)")
    for m in ExpansionMode:
        rate = 100 * primary["top1_optimality"][m.value]
        print(f"      {m.value:<14} ....... {rate:5.1f}%")
    print(
        f"      B - A ................ {100 * b_vs_a['difference']:+5.2f} pts  "
        f"[{100 * b_vs_a['ci_low']:+5.2f}, {100 * b_vs_a['ci_high']:+5.2f}]  "
        f"discordant {b_vs_a['discordant']}"
    )
    detectable = 100 * b_vs_a["detectable_at_80_power"]
    print(f"      detectable at 80% .... {detectable:5.2f} pts")
    print(f"      aliased mass ......... {alias:5.1f}%")
    print(f"      tree overhead (B/A) .. {100 * overhead:+5.1f}%  (no network here)")
    print(f"      falsifier fired ...... {b_vs_a['below_minus_2_margin']}")
    print(f"\n    elapsed .............. {elapsed:,.1f}s\n", flush=True)

    return {
        "experiment": "EXP-010",
        "variant": "5x3-h2",
        "ground_truth_v5": EXPECTED_V5,
        "ground_truth_termination": artefact["termination"],
        "seed": args.seed,
        "c_puct": args.c_puct,
        "layers": sorted({r["t"] for r in rows}),
        "per_layer": args.per_layer,
        "positions": len(rows),
        "sample_restriction": (
            "WIN for the side to move; a lost position has no optimal move"
        ),
        "primary_budget": args.primary_budget,
        "budgets_secondary_descriptive": [
            b for b in budgets if b != args.primary_budget
        ],
        "pooled_random_floor": sum(r["random_floor"] for r in rows) / len(rows),
        "pooled_aliased_mass": sum(r["aliased_mass"] for r in rows) / len(rows),
        "by_budget": {str(k): v for k, v in per_budget.items()},
        "by_layer": {str(k): v for k, v in by_layer.items()},
        "tree_overhead_position_over_action": overhead,
        "inference_cost": None,
        "falsifier_fired": b_vs_a["below_minus_2_margin"],
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seconds": elapsed,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--checkpoint", default="data/checkpoints")
    p.add_argument("--solution", default="data/subgame-solutions/5x3-h2.json")
    p.add_argument("--seed", type=int, default=SEED, help="registered: 17")
    p.add_argument("--per-layer", type=int, default=PER_LAYER)
    p.add_argument("--primary-budget", type=int, default=PRIMARY_BUDGET)
    p.add_argument("--c-puct", type=float, default=1.5)
    p.add_argument("--smoke", action="store_true", help="3 layers, one budget")
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    artefact = run(args)

    if not args.no_write:
        path = args.out / "exp010-mcts-dedup-5x3-h2.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artefact, indent=2))
        print(f"    artefact -> {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
