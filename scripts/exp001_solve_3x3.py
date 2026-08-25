"""EXP-001 — solve the 3×3 twice, by two different methods, and compare.

Registered in ``experiments/registry.md`` before this script existed. It is the
solver's **correctness fixture**, not a strategy result: 9 cells is too cramped
for the tactics the 5×5 design is about, and
`adr-010 <../docs/adr/adr-010-solver-correctness.md>`_ **V3** is what gives the
3×3 a job worth doing — *"two different programs on the same position"*, in
Schaeffer's phrase.

The two methods share the rules and nothing else:

* ``solver/minimax.py`` walks the **game tree** forward, with alpha-beta pruning
  and a transposition table, from the opening position outward.
* ``solver/retrograde.py`` enumerates the **configuration space** backward, layer
  by layer from the full board, with no pruning and no table.

A bug producing the same wrong answer in both would have to live in ``fliphex/``
itself — which is the point, and is why V3 is worth more than running one solver
twice.

What this run checks, and against what
--------------------------------------
* **V0** — the terminal layer is ``2**9 = 512``, decided by counting cells.
* **V1** — per-layer counts against the closed form in
  ``scripts/layer_profile.py``, which imports nothing from the engine. Exact
  equality, no tolerance: the adr-010 Phase 3 amendment made V1 a genuine
  ``perft`` and moved the reachability measurement out to ``EXP-005``.
* **V2** — a tied terminal raises inside ``fliphex.rules.winner``, on every
  terminal configuration rather than on a sample.
* **V3** — the two methods must agree on every position the forward search
  visited. Configurations the sweep covers but the search never reaches are
  counted and reported, not silently folded in.
* **V5** — the artefact carries a SHA-256 of its own value tables.

    python scripts/exp001_solve_3x3.py
    python scripts/exp001_solve_3x3.py --arm h1
    python scripts/exp001_solve_3x3.py --no-write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from layer_profile import layer as closed_form_layer  # noqa: E402

from fliphex.moves import apply_move  # noqa: E402
from fliphex.notation import encode_move  # noqa: E402
from fliphex.state import GameState  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.minimax import LOSS, WIN, Solver  # noqa: E402
from solver.retrograde import (  # noqa: E402
    SLOT_LOSS,
    SLOT_WIN,
    LayerIndex,
    solve_layers,
)
from solver.transposition import Flag, TranspositionTable  # noqa: E402


def check_v1(variant: Variant, counts: dict[int, int]) -> list[str]:
    """Exact per-layer equality against the independent closed form."""
    first, second = (len(hand) for hand in variant.deck_names())
    problems = []
    for t, enumerated in sorted(counts.items()):
        expected = closed_form_layer(variant.n_cells, first, second, t)
        if enumerated != expected:
            problems.append(
                f"layer {t}: enumerated {enumerated:,} vs formula {expected:,}"
            )
    return problems


def check_v3(
    variant: Variant, tables: dict[int, bytearray], tt: TranspositionTable
) -> tuple[int, list[str]]:
    """Compare every value the forward search stored against the sweep's.

    Every forward entry is exact whatever its flag. The window is always
    ``(LOSS, WIN)`` — alpha only ever rises to ``WIN``, which cuts immediately —
    so a stored bound is always extremal, and an extremal bound on a two-valued
    quantity *is* the value. That is checked below rather than assumed: if the
    objective ever grew a range (a margin, say) this reasoning would quietly
    stop holding and the comparison would start passing vacuously.
    """
    indices = {t: LayerIndex(variant, t) for t in tables}
    compared, problems = 0, []

    for entry in tt.entries():  # reading the table *is* the check
        if entry.key is None:
            continue
        colours, purple, green, to_move = entry.key

        if entry.value not in (WIN, LOSS):
            problems.append(f"forward value {entry.value} is outside {{WIN, LOSS}}")
            continue
        if entry.flag is Flag.LOWER and entry.value != WIN:
            problems.append(f"a LOWER bound of {entry.value} is not extremal")
            continue
        if entry.flag is Flag.UPPER and entry.value != LOSS:
            problems.append(f"an UPPER bound of {entry.value} is not extremal")
            continue

        t = sum(1 for c in colours if c)
        state = GameState.build(colours, (purple, green), to_move)
        expected = SLOT_WIN if entry.value == WIN else SLOT_LOSS
        actual = tables[t][indices[t].encode(state)]
        compared += 1
        if actual != expected:
            problems.append(
                f"layer {t}: forward says {entry.value}, sweep says slot {actual}"
            )
    return compared, problems


def principal_variation(variant: Variant, board, tt: TranspositionTable) -> list[str]:
    """The optimal line from the opening position, in board notation."""
    line = Solver(board, tt=tt).principal_variation(variant.initial_state())
    out, state = [], variant.initial_state()
    for move in line:
        out.append(encode_move(board, move))
        state = apply_move(board, state, move)
    return out


def run(
    variant: Variant, out_dir: Path | None, prune: bool = True, tt_bits: int = 21
) -> dict:
    board = variant.board()
    hands = "+".join(str(len(hand)) for hand in variant.deck_names())
    print(f"\n  === {variant.name} — {variant.n_cells} cells, hands {hands} ===")

    print("  retrograde sweep (configuration space, backwards) ...", flush=True)
    started = time.perf_counter()
    tables, backward = solve_layers(variant, board)
    sweep_seconds = time.perf_counter() - started

    mode = "with pruning" if prune else "UNPRUNED (V3 coverage mode)"
    print(
        f"  forward alpha-beta (game tree, from the opening) — {mode} ...", flush=True
    )
    started = time.perf_counter()
    tt = TranspositionTable(1 << tt_bits, verify=True)
    forward = Solver(board, tt=tt, prune=prune).solve(variant.initial_state())
    forward_seconds = time.perf_counter() - started

    v1 = check_v1(variant, backward.stats.layer_counts)
    compared, v3 = check_v3(variant, tables, tt)
    terminal = backward.stats.layer_counts[variant.n_cells]
    v0_ok = terminal == 2**variant.n_cells
    roots_agree = backward.value == forward.value
    total_configs = sum(backward.stats.layer_counts.values())

    digest = hashlib.sha256()
    for t in sorted(tables):
        digest.update(bytes(tables[t]))
    checksum = digest.hexdigest()

    who = "P1 (first player)" if forward.value == WIN else "P2 (second player)"
    print(f"    value ................. {who} wins with perfect play")
    print(
        f"    V0 terminal layer ..... {terminal:,} "
        f"({'ok' if v0_ok else 'MISMATCH'}, expected {2**variant.n_cells:,})"
    )
    print(f"    V1 per-layer counts ... {'ok' if not v1 else 'FAILED'}")
    for problem in v1:
        print(f"       {problem}")
    print("    V2 no-draw ............ asserted on every terminal (winner() raises)")
    coverage = 100 * compared / total_configs
    print(
        f"    V3 two methods ........ {compared:,} of {total_configs:,} "
        f"({coverage:.1f}%) compared, "
        f"{'agree' if not v3 and roots_agree else 'DISAGREE'}"
    )
    # The comparison reads surviving table entries, so coverage is capped by
    # what the table *retained*, not by what the search visited: the table is
    # direct-indexed (`zobrist & mask`, one entry per slot), so at this load
    # colliding positions overwrite each other before V3 ever sees them.
    # Reported alongside the coverage because otherwise the shortfall reads as
    # a property of the game rather than of the instrument.
    print(
        f"    ^ table ............... 2^{tt_bits} slots, "
        f"{tt.load:.1%} occupied, {tt.replacements:,} replacements"
    )
    for problem in v3[:5]:
        print(f"       {problem}")
    print(f"    V5 checksum ........... {checksum[:16]}...")
    print(
        f"    sweep {sweep_seconds:,.1f}s   forward {forward_seconds:,.1f}s   "
        f"{forward.stats.nodes:,} nodes"
    )

    pv = principal_variation(variant, board, tt)
    print(f"    principal variation ... {' '.join(pv) if pv else '(none recorded)'}")

    passed = v0_ok and not v1 and not v3 and roots_agree
    artefact = {
        "experiment": "EXP-001",
        "variant": variant.name,
        "board": [variant.n_cols, variant.n_rows],
        "cells": variant.n_cells,
        "hands": [list(hand) for hand in variant.deck_names()],
        "value": "P1" if forward.value == WIN else "P2",
        "principal_variation": pv,
        "ordering": forward.stats.ordering,
        "termination": forward.stats.termination,
        "pruning": forward.stats.pruning,
        "verification": {
            "V0_terminal_layer": {"count": terminal, "passed": v0_ok},
            "V1_layer_counts": {"passed": not v1, "problems": v1},
            "V2_no_draw": {"passed": True, "mode": "asserted on every terminal"},
            "V3_two_methods": {
                "positions_compared": compared,
                "configurations_total": total_configs,
                "coverage_percent": round(coverage, 3),
                "forward_pruning": forward.stats.pruning,
                "tt_capacity": tt.capacity,
                "tt_occupied": len(tt),
                "tt_replacements": tt.replacements,
                "roots_agree": roots_agree,
                "passed": not v3 and roots_agree,
                "problems": v3[:20],
            },
            "V5_checksum_sha256": checksum,
        },
        "layer_counts": dict(sorted(backward.stats.layer_counts.items())),
        "forward_nodes": forward.stats.nodes,
        "seconds": {"sweep": sweep_seconds, "forward": forward_seconds},
        "passed": passed,
    }

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "" if forward.stats.pruning else "-unpruned"
        path = out_dir / f"{variant.name}{suffix}.json"
        path.write_text(json.dumps(artefact, indent=2))
        print(f"    artefact -> {path}")
    return artefact


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--arm", choices=["h1", "h2", "both"], default="both")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data/subgame-solutions"),
        help="artefact directory (default data/subgame-solutions)",
    )
    p.add_argument("--no-write", action="store_true", help="print only")
    p.add_argument(
        "--no-prune",
        action="store_true",
        help="run the forward pass without beta cutoffs. Values are identical "
        "either way; what changes is V3's coverage, from 'positions pruning "
        "left' to 'every position reachable from the opening'. Slower, and the "
        "artefact records which mode produced it.",
    )
    p.add_argument(
        "--tt-bits",
        type=int,
        default=21,
        help="log2 of the transposition table's slot count (default 21). V3 "
        "compares surviving table entries, and the table is direct-indexed, so "
        "coverage is capped by retention rather than by what the search "
        "visited. Raising this raises coverage without changing any value.",
    )
    args = p.parse_args()

    arms = [Arm.H1, Arm.H2] if args.arm == "both" else [Arm(args.arm)]
    results = [
        run(
            Variant(3, 3, arm),
            None if args.no_write else args.out,
            not args.no_prune,
            args.tt_bits,
        )
        for arm in arms
    ]

    print()
    for r in results:
        state = "ALL CHECKS PASSED" if r["passed"] else "CHECKS FAILED"
        print(f"  {r['variant']}: {r['value']} wins — {state}")
    print()
    print("  Reminder: this is a correctness fixture. 9 cells is too cramped to")
    print("  carry a strategy claim, and adr-009 says a reduced-board result")
    print("  transfers to the shipped 5x5 as evidence, never as proof.")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
