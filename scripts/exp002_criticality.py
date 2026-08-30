"""EXP-002 — criticality of P1's extra tile, and a free cross-arm verification.

**Register this before running it.** See the amendment of 2026-08-30 under
EXP-002 in ``experiments/registry.md``.

What H2 actually asks
---------------------
Root-value agreement between the arms is at most one bit against a 50% prior,
and the registry recorded that caveat before either arm ran. The registered
measure is **criticality**: the fraction of solved positions whose value changes
when P1's extra tile is swapped — `JOKER` in h1, `P3-tri` in h2, with the other
seven archetypes and the whole of P2's hand identical.

Both arms index the same object — 15 cells, hands 8 + 7, 17,506,580,337
configurations, the same mixed-radix encoding — so this is a comparison of two
4.1 GB files, not a search.

The correspondence is NOT index-to-index
----------------------------------------
It is tempting, and wrong. ``LayerIndex`` orders a hand by **tile index**, not by
the deck listing, and the tile indices are `P3-tri = 6`, `P6 = 11`,
`JOKER = 12`. So P1's hand positions are:

    h1: (P1, P2-adj, P2-skip, P2-opp, P3-fan, P3-y, P6,      JOKER)
    h2: (P1, P2-adj, P2-skip, P2-opp, P3-fan, P3-y, P3-tri,  P6)

The extra tile sits at position 7 in one arm and position 6 in the other, and
`P6` — which the arms *share* — moves with it. Comparing index against index
would line "P6 spent" up against "P3-tri spent" and report a criticality
manufactured entirely by the encoding.

The true correspondence is the permutation carrying one hand's positions onto
the other's by tile identity, with the two extra tiles mapped to each other. It
is derived here from the hand tuples rather than hard-coded, so it stays correct
if a deck changes, and it is asserted against decoded hands before use.

The partition that makes the measure honest
-------------------------------------------
Under that correspondence, index ``i`` and its partner decode to the same cells,
colours, mover, and the same spent *tiles* up to the swap. Two cases:

* **The extra tile is already spent.** Both arms then hold the same remaining
  tiles on the same board with the same mover — *the same game position*. Placed
  tiles are inert (adr-003), so which tile was spent cannot matter. The values
  **must** agree; a disagreement is a bug in a sweep, not a fact about the joker.
* **The extra tile is still in hand.** P1 holds a different tile, and only here
  can the value legitimately differ. This is criticality's denominator.

Computing criticality over all 17.5 × 10⁹ indices would dilute it with a large
subset that is identical by construction, reporting a number too small for a
reason with nothing to do with the game.

The verification is the larger prize
------------------------------------
That first bucket is an exhaustive cross-arm check over billions of positions,
free as a by-product. It is not a second implementation — both arms ran the same
code — so it cannot catch a shared logic error. What it *can* catch is the deck
leaking where it must not: if P1's hand were consulted for P2's moves, or a
rotation-orbit count applied to the wrong hand, the sweeps would disagree here.
V4 sampled 601 positions and searched 344; this compares billions.

    pypy scripts/exp002_criticality.py
    pypy scripts/exp002_criticality.py --max-layer 6      # shape, in seconds
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.retrograde import LayerIndex, rank_subset, unrank_subset  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402


def hand_correspondence(a: LayerIndex, b: LayerIndex) -> tuple[list[int], int, int]:
    """Map ``a``'s first-player hand positions onto ``b``'s, by tile identity.

    Returns ``(position_map, a_extra_position, b_extra_position)``. The extra
    tiles — the one tile each arm holds that the other does not — are mapped to
    each other; every shared tile is mapped to wherever the other arm sorted it.

    Derived from the hands rather than hard-coded, because the position of a tile
    is an artefact of ``TILE_INDEX`` ordering and changing a deck would silently
    move it.
    """
    tiles_a, tiles_b = a._hand_tiles()[0], b._hand_tiles()[0]
    only_a = [t for t in tiles_a if t not in tiles_b]
    only_b = [t for t in tiles_b if t not in tiles_a]
    if len(only_a) != 1 or len(only_b) != 1:
        raise SystemExit(
            f"arms must differ in exactly one tile; got {only_a} vs {only_b}. "
            f"This instrument measures one swap, not a general deck change."
        )
    extra_a, extra_b = only_a[0], only_b[0]
    position_map = [
        tiles_b.index(extra_b) if tile == extra_a else tiles_b.index(tile)
        for tile in tiles_a
    ]
    return position_map, tiles_a.index(extra_a), tiles_b.index(extra_b)


def rank_permutation(position_map: list[int], spent: int) -> list[int]:
    """Permutation of first-player spent-set ranks, ``a``'s ordering to ``b``'s.

    Small — ``C(8, spent)`` is at most 70 — and rebuilt per layer.
    """
    size = comb(len(position_map), spent)
    return [
        rank_subset(tuple(sorted(position_map[p] for p in unrank_subset(r, spent))))
        for r in range(size)
    ]


def compare_layer(values_a, values_b, index_a, index_b, perm, extra_position):
    """Compare one layer under the correspondence.

    Returns ``(critical, n_free, mismatch, n_spent, examples)``. Walks
    ``(cells, colours)`` blocks and, inside each, the first-player rank
    sub-blocks — the only component the permutation touches. The second player's
    ranks are untouched and contiguous, which is the inner loop.
    """
    t = index_a.t
    s1, s2 = index_a.first_spent, index_a.second_spent
    radix_first = comb(len(index_a._hand_tiles()[0]), s1)
    radix_second = comb(len(index_a._hand_tiles()[1]), s2)
    blocks = comb(index_a.n_cells, t) * (1 << t)

    # Whether the extra tile is still in hand, per first-player rank.
    free_rank = [extra_position not in unrank_subset(r, s1) for r in range(radix_first)]

    critical = mismatch = n_free = n_spent = 0
    examples: list[dict] = []
    period = radix_first * radix_second

    for block in range(blocks):
        base = block * period
        for r in range(radix_first):
            start_a = base + r * radix_second
            start_b = base + perm[r] * radix_second
            free = free_rank[r]
            differing = 0
            for k in range(radix_second):
                ia, ib = start_a + k, start_b + k
                va = (values_a[ia >> 2] >> ((ia & 3) << 1)) & 3
                vb = (values_b[ib >> 2] >> ((ib & 3) << 1)) & 3
                if va != vb:
                    differing += 1
                    if not free and len(examples) < 10:
                        examples.append(
                            {
                                "layer": t,
                                "index_h1": ia,
                                "index_h2": ib,
                                "h1": va,
                                "h2": vb,
                            }
                        )
            if free:
                n_free += radix_second
                critical += differing
            else:
                n_spent += radix_second
                mismatch += differing

    return critical, n_free, mismatch, n_spent, examples


def assert_correspondence(index_a, index_b, position_map, perm, extra_position):
    """Confirm the premise against decoded hands before trusting it on billions.

    Everything rests on: partnered indices carry the same board and the same
    remaining tiles up to the swap, and they differ in exactly the extra tile
    precisely while it is unspent. That is derived from colex ranking and the
    deck layout — and a derivation nobody checked is how this project has lost
    weeks before. An earlier draft of this file assumed index-to-index
    correspondence and would have compared "P6 spent" against "P3-tri spent".
    """
    t = index_a.t
    s1 = index_a.first_spent
    radix_first = comb(len(index_a._hand_tiles()[0]), s1)
    shared_a = set(index_a._hand_tiles()[0]) & set(index_b._hand_tiles()[0])

    for r in range(radix_first):
        spent_a = set(unrank_subset(r, s1))
        spent_b = set(unrank_subset(perm[r], s1))
        tiles_a, tiles_b = index_a._hand_tiles()[0], index_b._hand_tiles()[0]
        left = {tiles_a[p] for p in range(len(tiles_a)) if p not in spent_a}
        right = {tiles_b[p] for p in range(len(tiles_b)) if p not in spent_b}
        free = extra_position not in spent_a

        if (left & shared_a) != (right & shared_a):
            raise SystemExit(
                f"layer {t} rank {r}: the shared tiles left in hand differ "
                f"({sorted(left & shared_a)} vs {sorted(right & shared_a)}) — "
                f"the position map is wrong"
            )
        if free == (left == right):
            raise SystemExit(
                f"layer {t} rank {r}: hands {'agree' if left == right else 'differ'} "
                f"but the extra tile is {'in hand' if free else 'spent'}"
            )


def run(args) -> dict:
    h1 = Variant(args.board[0], args.board[1], Arm("h1"))
    h2 = Variant(args.board[0], args.board[1], Arm("h2"))
    reader1 = SweepReader(h1, Checkpoint(args.checkpoint / h1.name))
    reader2 = SweepReader(h2, Checkpoint(args.checkpoint / h2.name))

    print(f"\n  === EXP-002 criticality — {h1.name} vs {h2.name} ===")
    print(
        f"  P1 extra tile: {h1.deck_names()[0][-1]} (h1) vs "
        f"{h2.deck_names()[0][-1]} (h2)"
    )
    print(f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}")
    print("  positions where the extra tile is already spent MUST agree", flush=True)

    top = args.max_layer if args.max_layer is not None else h1.n_cells
    top = min(top, h1.n_cells)

    started = time.perf_counter()
    rows: list[dict] = []
    all_examples: list[dict] = []

    print(
        f"\n  {'t':>3} {'in hand':>15} {'critical':>13} {'crit %':>8} "
        f"{'spent':>15} {'mismatch':>9} {'sec':>7}"
    )
    for t in range(top + 1):
        index_a, index_b = LayerIndex(h1, t), LayerIndex(h2, t)
        position_map, extra_a, _extra_b = hand_correspondence(index_a, index_b)
        perm = rank_permutation(position_map, index_a.first_spent)
        assert_correspondence(index_a, index_b, position_map, perm, extra_a)

        t0 = time.perf_counter()
        critical, n_free, mismatch, n_spent, examples = compare_layer(
            reader1.layer(t), reader2.layer(t), index_a, index_b, perm, extra_a
        )
        dt = time.perf_counter() - t0
        all_examples.extend(examples)

        rows.append(
            {
                "layer": t,
                "in_hand": n_free,
                "critical": critical,
                "spent": n_spent,
                "mismatch": mismatch,
                "seconds": dt,
            }
        )
        rate = 100 * critical / n_free if n_free else 0.0
        print(
            f"  {t:>3} {n_free:>15,} {critical:>13,} {rate:>7.2f}% "
            f"{n_spent:>15,} {mismatch:>9,} {dt:>7.1f}",
            flush=True,
        )
        reader1.release()
        reader2.release()

    elapsed = time.perf_counter() - started
    total_free = sum(r["in_hand"] for r in rows)
    total_crit = sum(r["critical"] for r in rows)
    total_spent = sum(r["spent"] for r in rows)
    total_mismatch = sum(r["mismatch"] for r in rows)

    print()
    if total_free:
        print(
            f"    criticality ........... {total_crit:,} of {total_free:,} "
            f"= {100 * total_crit / total_free:.3f}%"
        )
    print(
        f"    cross-arm verification  {total_spent:,} positions compared, "
        f"{total_mismatch:,} mismatches"
    )
    print(f"    elapsed ............... {elapsed:,.1f}s")
    if total_mismatch:
        print("\n    FAILED — the arms disagree where the extra tile is spent.")
        print("    Those are the same game position; this is a solver bug.")
        for example in all_examples[:5]:
            print(f"      {example}")
    print(flush=True)

    return {
        "experiment": "EXP-002",
        "check": "extra-tile criticality and cross-arm verification",
        "arms": [h1.name, h2.name],
        "extra_tile": [h1.deck_names()[0][-1], h2.deck_names()[0][-1]],
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "complete": top == h1.n_cells,
        "max_layer": top,
        "layers": rows,
        "criticality_numerator": total_crit,
        "criticality_denominator": total_free,
        "criticality": total_crit / total_free if total_free else None,
        "verification_compared": total_spent,
        "verification_mismatches": total_mismatch,
        "verification_passed": total_mismatch == 0,
        "mismatch_examples": all_examples[:10],
        "seconds": elapsed,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 3], metavar=("COLS", "ROWS")
    )
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument(
        "--max-layer",
        type=int,
        default=None,
        help="stop after this layer; a partial run reports the layers it covered "
        "and is marked complete: false",
    )
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    artefact = run(args)

    if not args.no_write:
        name = f"exp002-criticality-{args.board[0]}x{args.board[1]}.json"
        atomic_write(args.out / name, json.dumps(artefact, indent=2).encode())
        print(f"    artefact -> {args.out / name}\n")
    return 0 if artefact["verification_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
