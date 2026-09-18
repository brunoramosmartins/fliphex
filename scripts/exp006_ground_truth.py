"""EXP-006 ground truth: exactly solved 5x5 endgame positions, for H3.

Registered in ``experiments/registry.md`` on 2026-08-05 — **before Axis 2
existed**, which is the entry's whole point: a comparison set fixed after seeing
the learner is not a comparison set. Amended 2026-08-07 (a second, disclosed
stratum) and 2026-09-16 (the denominator, the agent, the evaluation budget).
Read all three before changing anything here; every constant below is pinned
there.

This file produces **only the ground truth**. The agreement measurement — five
EXP-015 champions against these positions — is a separate instrument reading this
artefact, and the separation is deliberate: solving takes hours and must not be
repeated when the measurement changes.

What is produced
----------------
**Stratum A, the registered one.** 500 positions, seed 2, `k` split 166/167/167,
drawn by **random playout** to ply ``25 - k``. That sampler matches EXP-003's and
carries the same registered bias; it exists so Axis 2 does not choose its own
exam.

**Stratum B, disclosed 2026-08-07.** 250 positions, seed 4, `k` split 84/83/83,
drawn **uniformly from the layer index**. Takizawa 2023 §5 gives empirical
evidence that an evaluator's systematic errors concentrate where play does not
go, so measuring agreement only where a playout reaches risks reporting the
learner's easy half. **The two strata are never pooled** — the decision rule runs
on A, B is descriptive, and a gap between them is the finding.

Stratum B is uniform over the *layer*, not over the reachable set.
Uniform-over-reachable is not implementable here: the ``k = 8`` layer holds
5.017e16 configurations. Configurations with no legal predecessor are rejected
using EXP-005's closed characterisation, which at ``t = 17`` removes about 1 in
131,072 — a **correctness guard, not a meaningful filter**, and the residual gap
to true reachability is disclosed rather than closed.

**The value, and what it is for.** Every position is solved exactly. The 2026-09-16
amendment makes the decision rule's denominator the positions the mover **wins**,
because from a lost position every legal move preserves the value and the learner
scores a hit whatever it plays. Lost positions are counted and excluded, never
scored.

**The calibration sweep.** 100 positions of stratum A — the first 34/33/33 per
`k` in generation order — get every distinct child solved as well. That yields
the count of won positions where no move throws the win away (non-discriminating,
and therefore also vacuous), and the **random-move agreement baseline**, so the
headline rate is never quoted without the floor it sits on. It also *checks* the
amendment's central claim rather than assuming it: on every lost position in the
subsample, every child must be a win for the opponent.

Timing
------
``time.monotonic()`` throughout, never ``time.time()``. This run spans hours and
the machine hibernates; a wall clock moves backwards across a resume, and a probe
written for this entry measured a **negative** elapsed time that way before the
instrument existed.

Resumability
------------
Positions are appended to a JSONL work file as they are solved, and the sampling
streams are per ``(stratum, k)`` and derived from the registered seed, so a resume
re-derives the same sequence and skips what is already done. A kill costs at most
one position. Nothing is ever silently replaced: a position whose proof exceeds
the node budget is recorded as **excluded, with its count**, exactly as
registered.

Usage::

    .venv/bin/python scripts/exp006_ground_truth.py
    .venv/bin/python scripts/exp006_ground_truth.py --stratum registered
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.state import Colour, GameState, other  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.minimax import WIN, BudgetExceededError, Solver  # noqa: E402
from solver.retrograde import LayerIndex  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402

# -- pinned by the registry ---------------------------------------------------

VARIANT = Variant(5, 5, Arm("h1"))

#: EXP-003's tail run solved 200 positions per `k` at this budget with **zero**
#: censored at `k = 8` (median 806,474 nodes, p90 2,683,470, max 9,239,393). It
#: is reused rather than reinvented, the same discipline EXP-008 applied to
#: ``search_below_k``.
MAX_NODES = 20_000_000

#: Transposition table size. Shared between a root and its children so the child
#: sweep reuses the root's work; ``verify=True`` is the default and is kept,
#: because this artefact is cited.
TT_BITS = 20


@dataclass(frozen=True)
class Stratum:
    name: str
    seed: int
    counts: dict[int, int]
    sampler: str
    why: str


REGISTERED = Stratum(
    name="registered",
    seed=2,
    counts={6: 166, 7: 167, 8: 167},
    sampler="playout",
    why=(
        "Random playout to ply 25-k, matching EXP-003's sampler and carrying the "
        "same registered bias. Seed 2 rather than EXP-003's seed 1, so the "
        "learner is not evaluated on the positions whose cost justified this "
        "design. The decision rule runs on this stratum alone."
    ),
)

LAYER_UNIFORM = Stratum(
    name="layer_uniform",
    seed=4,
    counts={6: 84, 7: 83, 8: 83},
    sampler="layer",
    why=(
        "Uniform over the layer index, orphan-filtered. Disclosed 2026-08-07 "
        "against Takizawa 2023 §5: an evaluator's systematic errors concentrate "
        "where play does not go. Descriptive only; pooling with the registered "
        "stratum is forbidden."
    ),
)

STRATA = {s.name: s for s in (REGISTERED, LAYER_UNIFORM)}

#: Default run order: **the registered stratum first**, because it is the one
#: the decision rule runs on. Insertion order, never ``sorted()`` — alphabetical
#: puts ``layer_uniform`` first, which would leave a run interrupted for days
#: holding the descriptive half and not the primary one.
DEFAULT_ORDER = tuple(STRATA)

#: The calibration sweep, pre-declared: the first N per `k` of the registered
#: stratum in generation order. Deterministic, and it needs no further seed.
CALIBRATION = {6: 34, 7: 33, 8: 33}


# -- sampling -----------------------------------------------------------------


def stream(stratum: Stratum, k: int) -> Random:
    """One independent draw sequence per ``(stratum, k)``, from the pinned seed.

    Per-`k` streams rather than one shared generator so that resuming a partly
    finished `k` re-derives exactly the positions it had, without having to
    replay the other strata's draws in the right order.
    """
    return Random(f"exp006:{stratum.name}:{stratum.seed}:k{k}")


def playout_position(board, rng: Random, plies: int) -> GameState:
    """A position ``plies`` moves into a uniformly random legal game."""
    state = VARIANT.initial_state()
    for _ in range(plies):
        state = apply_move(board, state, rng.choice(legal_moves(board, state)))
    return state


def is_orphan(state: GameState) -> bool:
    """Whether no legal move can produce ``state``.

    EXP-005's closed characterisation: a configuration has no legal predecessor
    exactly when **every occupied cell carries the colour of the player who did
    not just move**. The last-placed cell always shows its placer's colour — a
    tile's arrows never point at the cell it occupies — so if no cell carries
    that colour, no cell can have been the last one placed. That is 1 of the
    ``2**t`` colourings under each (cell-set, hand-state), which is where the
    ``2**-t`` orphan identity comes from.
    """
    just_moved = other(state.to_move)
    return not any(colour == just_moved for colour in state.colours)


def layer_position(index: LayerIndex, rng: Random) -> tuple[GameState, int, int]:
    """Draw uniformly from the layer, rejecting orphans.

    Returns the state, its rank, and how many orphans were rejected first. At
    ``t = 17`` the rejection rate is about 1 in 131,072, so the count is expected
    to be zero and is recorded so that a surprise is visible rather than silent.
    """
    rejected = 0
    while True:
        rank = rng.randrange(index.size)
        state = index.decode(rank)
        if not is_orphan(state):
            return state, rank, rejected
        rejected += 1


def draw(stratum: Stratum, k: int, rng: Random, board) -> tuple[GameState, dict]:
    if stratum.sampler == "playout":
        return playout_position(board, rng, VARIANT.n_cells - k), {}
    state, rank, rejected = layer_position(
        LayerIndex(VARIANT, VARIANT.n_cells - k), rng
    )
    return state, {"layer_rank": rank, "orphans_rejected": rejected}


# -- solving ------------------------------------------------------------------


def solve_root(board, state: GameState) -> dict:
    """Prove one position, or record it as excluded at the budget.

    ``solver/minimax.py`` proves or raises: it has no evaluation function and no
    depth limit, so a returned value satisfies adr-004 R1 ``termination:
    exhausted`` by construction. A budget failure returns nothing partial and is
    **never replaced by a fresh sample** — that would select the sample on how
    hard it was to solve.
    """
    table = TranspositionTable(1 << TT_BITS)
    solver = Solver(board, tt=table, max_nodes=MAX_NODES)
    started = time.monotonic()
    try:
        result = solver.solve(state)
    except BudgetExceededError:
        return {
            "proved": False,
            "nodes": solver.stats.nodes,
            "seconds": time.monotonic() - started,
            "termination": "budget",
        }
    return {
        "proved": True,
        "value": "WIN" if result.value == WIN else "LOSS",
        "nodes": solver.stats.nodes,
        "seconds": time.monotonic() - started,
        "termination": solver.stats.termination,
        "table": table,
    }


def child_sweep(board, state: GameState, table: TranspositionTable) -> dict:
    """Solve every distinct child, reusing the root's transposition table.

    Children are deduplicated **by position**, not by action: risk R13 measured
    4.46x root aliasing, and counting one position several times would inflate
    both the child count and the random-move baseline computed from it.

    ``opponent_wins`` counts children the opponent wins — from a won root those
    are exactly the moves that throw the game away.
    """
    started = time.monotonic()
    seen: dict = {}
    for move in legal_moves(board, state):
        child = apply_move(board, state, move)
        key = child.key()
        if key in seen:
            continue
        seen[key] = Solver(board, tt=table, max_nodes=MAX_NODES).solve(child).value
    values = list(seen.values())
    opponent_wins = sum(1 for v in values if v == WIN)
    return {
        "legal_moves": len(legal_moves(board, state)),
        "distinct_children": len(values),
        "opponent_wins": opponent_wins,
        "seconds": time.monotonic() - started,
    }


# -- the work file ------------------------------------------------------------


def done_counts(rows: list[dict]) -> dict[tuple[str, int], int]:
    counts: dict[tuple[str, int], int] = {}
    for row in rows:
        key = (row["stratum"], row["k"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def read_work(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for index, line in enumerate(path.read_text().splitlines()):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            raise SystemExit(
                f"{path}: line {index + 1} is not JSON. A kill can truncate the "
                "last line; anything earlier is corruption. Inspect before "
                "deleting — these are solved positions and they cost hours."
            ) from None
    return rows


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
        handle.flush()


def encode_state(state: GameState) -> dict:
    return {
        "colours": [int(c) for c in state.colours],
        "hands": list(state.hands),
        "to_move": int(state.to_move),
    }


def decode_state(record: dict) -> GameState:
    return GameState.build(
        tuple(Colour(c) for c in record["colours"]),
        tuple(record["hands"]),
        Colour(record["to_move"]),
    )


# -- the run ------------------------------------------------------------------


def generate(stratum: Stratum, work: Path, board, rows: list[dict]) -> None:
    counts = done_counts(rows)
    for k, wanted in sorted(stratum.counts.items()):
        rng = stream(stratum, k)
        already = counts.get((stratum.name, k), 0)
        for index in range(wanted):
            state, extra = draw(stratum, k, rng, board)
            if index < already:
                continue  # re-derived, already solved and on disk
            calibrate = stratum.name == REGISTERED.name and index < CALIBRATION.get(
                k, 0
            )
            solved = solve_root(board, state)
            table = solved.pop("table", None)
            row = {
                "stratum": stratum.name,
                "k": k,
                "index": index,
                **encode_state(state),
                **extra,
                **solved,
            }
            if calibrate and table is not None:
                row["sweep"] = child_sweep(board, state, table)
            append(work, row)
            mark = "" if solved["proved"] else "  EXCLUDED (budget)"
            sweep = row.get("sweep")
            print(
                f"  {stratum.name:<13} k={k} {index + 1:>3}/{wanted}  "
                f"{solved.get('value', '----'):<4} {solved['nodes']:>9} nodes  "
                f"{solved['seconds']:>7.1f}s"
                + (
                    f"  sweep {sweep['distinct_children']:>3} children "
                    f"{sweep['seconds']:>6.1f}s"
                    if sweep
                    else ""
                )
                + mark,
                flush=True,
            )


# -- the artefact -------------------------------------------------------------


def summarise(rows: list[dict]) -> dict:
    summary: dict = {}
    for name in STRATA:
        per_k = {}
        for k in sorted(STRATA[name].counts):
            subset = [r for r in rows if r["stratum"] == name and r["k"] == k]
            proved = [r for r in subset if r["proved"]]
            wins = [r for r in proved if r["value"] == "WIN"]
            per_k[str(k)] = {
                "drawn": len(subset),
                "proved": len(proved),
                "excluded_at_budget": len(subset) - len(proved),
                "mover_wins": len(wins),
                "mover_loses": len(proved) - len(wins),
                "decision_denominator": len(wins),
                "median_nodes": _median([r["nodes"] for r in proved]),
                "seconds": sum(r["seconds"] for r in subset),
                "orphans_rejected": sum(r.get("orphans_rejected", 0) for r in subset),
            }
        summary[name] = per_k
    return summary


def calibration(rows: list[dict]) -> dict:
    swept = [r for r in rows if "sweep" in r and r["proved"]]
    won = [r for r in swept if r["value"] == "WIN"]
    lost = [r for r in swept if r["value"] == "LOSS"]

    # The amendment's central claim, checked rather than assumed: from a lost
    # position every legal move preserves the value, so every child must be a
    # win for the opponent.
    violations = [
        {"k": r["k"], "index": r["index"], "sweep": r["sweep"]}
        for r in lost
        if r["sweep"]["opponent_wins"] != r["sweep"]["distinct_children"]
    ]

    non_discriminating = [r for r in won if r["sweep"]["opponent_wins"] == 0]
    shares = [
        r["sweep"]["opponent_wins"] / r["sweep"]["distinct_children"] for r in won
    ]
    return {
        "positions_swept": len(swept),
        "won": len(won),
        "lost": len(lost),
        "lost_positions_all_moves_preserve": not violations,
        "violations": violations,
        "won_but_no_losing_move": len(non_discriminating),
        "median_losing_move_share": _median(shares),
        "random_move_agreement_on_won": (1 - _median(shares)) if shares else None,
        "sweep_seconds": sum(r["sweep"]["seconds"] for r in swept),
    }


def _median(values: list) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def assemble(rows: list[dict], out: Path) -> dict:
    purple, green = VARIANT.hands()
    artefact = {
        "experiment": "EXP-006",
        "registered": "experiments/registry.md",
        "variant": VARIANT.name,
        "cells": VARIANT.n_cells,
        "hands": [bin(purple).count("1"), bin(green).count("1")],
        # adr-004 R3, required on every Axis-1 artefact. H3's comparison set is
        # defined by *filtering* on these two fields, so they have to be true of
        # what a filter would then use. Every position carrying a value was
        # proved; a position that hit the budget carries no value, is excluded
        # from every denominator, and is counted here rather than left for a
        # reader to discover inside the summary. A whole artefact claiming
        # "exhausted" while holding an unproved row is exactly the prose claim
        # R3 exists to replace.
        "ordering": "internal",
        "termination": "exhausted",
        "termination_scope": (
            "Every position with a value was proved by an unbounded search. "
            "Positions that reached the node budget carry no value and are "
            "excluded from every denominator; see excluded_at_budget."
        ),
        "excluded_at_budget": sum(1 for r in rows if not r["proved"]),
        "max_nodes": MAX_NODES,
        "generated": date.today().isoformat(),
        "strata": {
            name: {
                "seed": s.seed,
                "counts": {str(k): v for k, v in s.counts.items()},
                "sampler": s.sampler,
                "why": s.why,
            }
            for name, s in STRATA.items()
        },
        "pooling": (
            "Forbidden. The H3 decision rule runs on the registered stratum "
            "only; layer_uniform is descriptive and a gap between them is the "
            "finding."
        ),
        "denominator": (
            "Positions the mover WINS. From a lost position every legal move "
            "preserves the value, so scoring those would measure the sample's "
            "loss fraction rather than the learner (amendment 2026-09-16)."
        ),
        "calibration": calibration(rows),
        "summary": summarise(rows),
        "positions": rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artefact, indent=2))
    return artefact


def report(artefact: dict) -> None:
    print("\n== positions ==")
    print(
        f"  {'stratum':<14} {'k':>2} {'proved':>7} {'excl':>5} {'WIN':>5} "
        f"{'LOSS':>5} {'denom':>6} {'median nodes':>13} {'hours':>6}"
    )
    for name, per_k in artefact["summary"].items():
        for k, s in per_k.items():
            print(
                f"  {name:<14} {k:>2} {s['proved']:>7} "
                f"{s['excluded_at_budget']:>5} {s['mover_wins']:>5} "
                f"{s['mover_loses']:>5} {s['decision_denominator']:>6} "
                f"{s['median_nodes'] or 0:>13.0f} {s['seconds'] / 3600:>6.2f}"
            )

    cal = artefact["calibration"]
    print("\n== calibration sweep ==")
    print(
        f"  {cal['positions_swept']} positions swept "
        f"({cal['won']} won, {cal['lost']} lost), "
        f"{cal['sweep_seconds'] / 3600:.2f} h"
    )
    if cal["lost"]:
        verdict = "HOLDS" if cal["lost_positions_all_moves_preserve"] else "VIOLATED"
        print(
            f"  every move preserves a loss: {verdict}"
            + (
                ""
                if cal["lost_positions_all_moves_preserve"]
                else f" {cal['violations']}"
            )
        )
    if cal["won"]:
        print(
            f"  won positions with no losing move: {cal['won_but_no_losing_move']}"
            f" of {cal['won']}  (these are vacuous too)"
        )
        print(
            f"  median share of moves that throw the win away: "
            f"{cal['median_losing_move_share']:.1%}  -> a random mover agrees on "
            f"about {cal['random_move_agreement_on_won']:.1%} of won positions"
        )
        print(
            "  That baseline must be quoted beside the headline rate. It is the "
            "floor the\n  measure sits on, not zero."
        )

    excluded = sum(
        s["excluded_at_budget"]
        for per_k in artefact["summary"].values()
        for s in per_k.values()
    )
    print(f"\n  excluded at the {MAX_NODES:,}-node budget: {excluded}")
    print(
        "  Excluded positions are reported, never replaced by fresh samples: "
        "replacing\n  them would select the sample on how hard it was to solve."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stratum", choices=sorted(STRATA), action="append")
    parser.add_argument("--out", default="data/ground-truth/5x5-endgame-seed2.json")
    parser.add_argument("--work", default="data/ground-truth/5x5-endgame-seed2.jsonl")
    parser.add_argument(
        "--assemble-only",
        action="store_true",
        help="write the artefact from the work file without solving anything",
    )
    args = parser.parse_args()

    board = VARIANT.board()
    work = Path(args.work)
    rows = read_work(work)
    chosen = [STRATA[name] for name in (args.stratum or DEFAULT_ORDER)]

    started = time.monotonic()
    if not args.assemble_only:
        for stratum in chosen:
            total = sum(stratum.counts.values())
            have = sum(1 for r in rows if r["stratum"] == stratum.name)
            print(
                f"{stratum.name}: {have}/{total} already solved"
                + (" -- complete" if have >= total else ""),
                flush=True,
            )
            generate(stratum, work, board, rows)
            rows = read_work(work)

    artefact = assemble(rows, Path(args.out))
    report(artefact)
    print(f"\n  this invocation: {(time.monotonic() - started) / 3600:.2f} h")
    print(f"written  {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
