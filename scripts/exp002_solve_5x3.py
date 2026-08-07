"""EXP-002 — the exact game value of the 5×3, and the H1/H2 partial verdicts.

Registered in ``experiments/registry.md`` before this script existed. This is the
**strategically meaningful** exact solve: 15 cells, hands 8 + 7, both hands
exactly exhausted, Player 1 moves last with the joker as the extra tile, and the
same Z/2 mirror as the shipped 5×5
(`adr-011 <../docs/adr/adr-011-reduced-variant-parity.md>`_).

Why the verification differs from EXP-001
-----------------------------------------
The 3×3 is small enough to solve **twice**, so adr-010 **V3** — forward
alpha-beta against the retrograde sweep — carries the correctness argument
there. It cannot here: 1.75 × 10¹⁰ configurations is an enumeration, and the
forward searcher would never finish. So V3 is not attempted, and its weight
moves onto V4 and V6, which the sweep can support.

The database never exists all at once, either. Widened to one byte per entry the
5×3 layers total 17.5 GB; at two bits and two layers resident the sweep peaks
around 2.5 GB. Everything below is therefore sampled through the sweep's
``observer`` hook **while each layer is still in memory**, and the layer is then
discarded. Nothing is written to disk but the artefact.

What this run checks
--------------------
* **V0** — the terminal layer is ``2**15 = 32,768``, decided by counting cells.
* **V1** — per-layer counts against ``scripts/layer_profile.py``, which imports
  nothing from the engine. Exact equality, no tolerance.
* **V2** — a tied terminal raises. On 15 cells it cannot happen; the assertion
  is total and free.
* **V4** — sampled positions re-derived by **direct forward search that never
  consults the sweep**, with the sample size and seed fixed before the run.
  Honest limitation: only positions shallow enough to prove within the node
  budget can be checked, so V4 covers the endgame and thins out going up. The
  count of positions that were *not* affordable is reported, never hidden.
* **V5** — a running SHA-256 over every layer, in layer order.
* **V6** — mirror consistency. The 5×3's automorphism is the same left-right
  reflection as the 5×5's, and `adr-008 <../docs/adr/adr-008-board-mirror-symmetry.md>`_
  says it is a *game* symmetry only once **both** copies of the chiral ``P3-y``
  are off the hands. So V6 samples only configurations satisfying that, and
  reports how many were eligible — a mirror check run indiscriminately would
  pass or fail for the wrong reason. This is the first board where V6 applies
  at all: the withdrawn 4×4's automorphism was a rotation, which no tile breaks.

    pypy scripts/exp002_solve_5x3.py --arm h1
    pypy scripts/exp002_solve_5x3.py --arm h1 --bits 2 --out data/subgame-solutions
    python scripts/exp002_solve_5x3.py --board 5 1 --arm h1     # smoke test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_symmetry import board_automorphisms  # noqa: E402
from layer_profile import layer as closed_form_layer  # noqa: E402

from fliphex.state import TILE_INDEX, Colour  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.minimax import WIN, BudgetExceededError, Solver  # noqa: E402
from solver.packed_sweep import PackedSweep  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN, LayerIndex  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402

CHIRAL = "P3-y"


@dataclass
class Checks:
    """Everything the observer collects while the layers are still resident."""

    variant: Variant
    v4_per_layer: int
    v6_per_layer: int
    seed: int
    #: Print a line per layer. A 5×3 arm runs for the better part of a day and
    #: the summary only prints at the end, so without this the log is empty for
    #: hours and there is no way to tell a slow sweep from a hung one.
    progress: bool = True

    digest: object = field(default_factory=hashlib.sha256)
    layer_counts: dict[int, int] = field(default_factory=dict)
    v1_problems: list[str] = field(default_factory=list)
    v4_samples: list[tuple[int, int, int]] = field(default_factory=list)
    v6_checked: int = 0
    v6_rejected: int = 0
    v6_problems: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = Random(self.seed)
        self.hand_sizes = tuple(len(h) for h in self.variant.deck_names())
        board = self.variant.board()
        self.mirror = _mirror_permutation(board)
        self.chiral_tile = TILE_INDEX[CHIRAL]
        self._started = self._last = time.perf_counter()

    # -- called once per layer, while `values` is still in memory -------------

    def __call__(self, t: int, values: bytearray, sweep: PackedSweep) -> None:
        size = sweep.layer_size(t)
        self.layer_counts[t] = size

        expected = closed_form_layer(self.variant.n_cells, *self.hand_sizes, t)
        if size != expected:
            self.v1_problems.append(f"layer {t}: {size:,} vs formula {expected:,}")

        self.digest.update(bytes(values))

        for _ in range(min(self.v4_per_layer, size)):
            index = self.rng.randrange(size)
            self.v4_samples.append((t, index, sweep.get(values, index)))

        self._mirror_check(t, values, sweep, size)

        if self.progress:
            now = time.perf_counter()
            print(
                f"    layer {t:2d}  {size:>15,} configs  "
                f"{now - self._last:7.1f}s  ({now - self._started:,.0f}s total)",
                flush=True,
            )
            self._last = now

    def _mirror_check(self, t, values, sweep, size) -> None:
        """A configuration and its mirror image must share a value.

        Only where the mirror is a game symmetry at all: adr-008 makes it one
        exactly when neither hand still holds ``P3-y``, because the chiral tile's
        reflection is not in the deck. Sampling without that filter would be
        measuring something else.
        """
        if self.mirror is None:
            return
        layer = LayerIndex(self.variant, t)
        checked = 0
        # Bounded by attempts as well as by hits: in early layers almost nothing
        # is eligible, because both copies of P3-y are still in hand, and an
        # unbounded search for eligible samples would stall the sweep there.
        for _ in range(20 * self.v6_per_layer):
            if checked >= self.v6_per_layer:
                break
            index = self.rng.randrange(size)
            state = layer.decode(index)
            if not self._chiral_spent(state):
                self.v6_rejected += 1
                continue
            mirrored = _mirror_state(state, self.mirror)
            other_index = layer.encode(mirrored)
            checked += 1
            self.v6_checked += 1
            if sweep.get(values, index) != sweep.get(values, other_index):
                self.v6_problems.append(
                    f"layer {t}: index {index} and its mirror {other_index} differ"
                )

    def _chiral_spent(self, state) -> bool:
        """Whether both players have already played their ``P3-y``.

        Until then the mirror is not a game symmetry at all (adr-008): the
        chiral tile's reflection is not in the deck, so a mirrored position has
        moves the original does not.
        """
        return all(not (hand >> self.chiral_tile) & 1 for hand in state.hands)


def _mirror_permutation(board) -> tuple[int, ...] | None:
    """The board's non-identity automorphism as a cell permutation, if it has one."""
    identity = tuple(range(board.n_cells))
    for _name, _rho, cell_map in board_automorphisms(board):
        perm = tuple(cell_map[c] for c in range(board.n_cells))
        if perm != identity:
            return perm
    return None


def _mirror_state(state, perm: tuple[int, ...]):
    colours = [Colour.EMPTY] * state.n_cells
    for cell, colour in enumerate(state.colours):
        colours[perm[cell]] = colour
    return type(state).build(tuple(colours), state.hands, state.to_move)


def run_v4(variant: Variant, checks: Checks, budget: int) -> dict:
    """Re-derive sampled values by forward search, never consulting the sweep."""
    board = variant.board()
    agreed = disagreed = unaffordable = 0
    problems: list[str] = []

    for t, index, slot in checks.v4_samples:
        state = LayerIndex(variant, t).decode(index)
        if state.is_terminal():
            continue
        try:
            forward = Solver(
                board, tt=TranspositionTable(1 << 16), max_nodes=budget
            ).solve(state)
        except BudgetExceededError:
            unaffordable += 1
            continue
        expected = SLOT_WIN if forward.value == WIN else SLOT_LOSS
        if expected == slot:
            agreed += 1
        else:
            disagreed += 1
            problems.append(
                f"layer {t} index {index}: sweep {slot}, forward {expected}"
            )

    return {
        "agreed": agreed,
        "disagreed": disagreed,
        "unaffordable": unaffordable,
        "node_budget": budget,
        "passed": disagreed == 0 and agreed > 0,
        "problems": problems[:20],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument(
        "--board", type=int, nargs=2, default=(5, 3), metavar=("COLS", "ROWS")
    )
    p.add_argument("--bits", type=int, choices=(2, 8), default=2)
    p.add_argument("--seed", type=int, default=3, help="sampling seed (registered: 3)")
    p.add_argument("--v4-per-layer", type=int, default=40)
    p.add_argument("--v6-per-layer", type=int, default=40)
    p.add_argument("--v4-budget", type=int, default=2_000_000)
    p.add_argument("--out", type=Path, default=Path("data/subgame-solutions"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    board = variant.board()
    hands = "+".join(str(len(h)) for h in variant.deck_names())
    total = sum(
        closed_form_layer(variant.n_cells, *(len(h) for h in variant.deck_names()), t)
        for t in range(variant.n_cells + 1)
    )

    print(f"  === EXP-002 — {variant.name}, {variant.n_cells} cells, hands {hands} ===")
    print(f"  {total:,} configurations, {args.bits} bits/entry, seed {args.seed}")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}",
        flush=True,
    )

    checks = Checks(variant, args.v4_per_layer, args.v6_per_layer, args.seed)
    started = time.perf_counter()
    result = PackedSweep(variant, board, args.bits).sweep(observer=checks)
    sweep_seconds = time.perf_counter() - started
    print(
        f"  sweep done in {sweep_seconds / 3600:.2f} h "
        f"({total / sweep_seconds:,.0f} cfg/s)"
    )

    print("  V4 — re-deriving sampled positions by forward search ...", flush=True)
    v4 = run_v4(variant, checks, args.v4_budget)

    terminal = checks.layer_counts[variant.n_cells]
    v0_ok = terminal == 2**variant.n_cells
    checksum = checks.digest.hexdigest()
    who = "P1" if result.value == WIN else "P2"

    print()
    print(f"    VALUE ................. {who} wins with perfect play")
    print(f"    V0 terminal layer ..... {terminal:,} ({'ok' if v0_ok else 'MISMATCH'})")
    print(f"    V1 per-layer counts ... {'ok' if not checks.v1_problems else 'FAILED'}")
    for problem in checks.v1_problems:
        print(f"       {problem}")
    print("    V2 no-draw ............ asserted on every terminal")
    print(
        f"    V4 sampled re-derive .. {v4['agreed']:,} agree, "
        f"{v4['disagreed']} disagree, {v4['unaffordable']} over budget"
    )
    for problem in v4["problems"][:5]:
        print(f"       {problem}")
    print(f"    V5 checksum ........... {checksum[:16]}...")
    if checks.mirror is None:
        print("    V6 mirror ............. N/A — this board has no reflection")
    else:
        print(
            f"    V6 mirror ............. {checks.v6_checked:,} eligible pairs "
            f"checked, {len(checks.v6_problems)} differ "
            f"({checks.v6_rejected:,} sampled but ineligible — P3-y still in hand)"
        )
    for problem in checks.v6_problems[:5]:
        print(f"       {problem}")

    passed = (
        v0_ok and not checks.v1_problems and v4["passed"] and not checks.v6_problems
    )
    print()
    print(
        f"  {variant.name}: {who} wins — "
        f"{'ALL CHECKS PASSED' if passed else 'CHECKS FAILED'}"
    )
    print()
    print("  adr-009: a reduced-board result transfers to the shipped 5x5 as")
    print("  evidence, never as proof. Report it with its board and deck.")

    artefact = {
        "experiment": "EXP-002",
        "variant": variant.name,
        "board": list(args.board),
        "cells": variant.n_cells,
        "hands": [list(h) for h in variant.deck_names()],
        "configurations": total,
        "value": who,
        "ordering": "internal",
        "termination": "exhausted",
        "bits_per_entry": args.bits,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seed": args.seed,
        "seconds": sweep_seconds,
        "verification": {
            "V0_terminal_layer": {"count": terminal, "passed": v0_ok},
            "V1_layer_counts": {
                "passed": not checks.v1_problems,
                "problems": checks.v1_problems,
            },
            "V2_no_draw": {"passed": True, "mode": "asserted on every terminal"},
            "V4_sampled_rederivation": v4,
            "V5_checksum_sha256": checksum,
            "V6_mirror": {
                "applicable": checks.mirror is not None,
                "pairs_checked": checks.v6_checked,
                "sampled_but_ineligible": checks.v6_rejected,
                "problems": checks.v6_problems[:20],
                "passed": not checks.v6_problems,
            },
        },
        "layer_counts": dict(sorted(checks.layer_counts.items())),
        "passed": passed,
    }

    if not args.no_write:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / f"{variant.name}.json"
        path.write_text(json.dumps(artefact, indent=2))
        print(f"  artefact -> {path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
