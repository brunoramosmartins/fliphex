"""Tabulate the state-space bound layer by layer.

The reachable-state bound of `adr-003 <../docs/adr/adr-003-piece-representation.md>`_
is a sum over the number of filled cells ``t``::

    S = sum_t  C(N, t) * 2^t * C(d1, ceil(t/2)) * C(d2, floor(t/2))

for a board of ``N`` cells and decks of ``d1`` (Player 1, moves on odd plies) and
``d2`` (Player 2) tiles. This script evaluates the summand rather than only the
total, which is what makes it useful:

* the **shape** of the profile decides whether the game converges (a funnel, as
  in checkers) or not (a hump, as in FLIPHEX) -- ``exercises/ex02`` Q6(c);
* the **terminal layer** is the closed-form base case of the retrograde sweep,
  and is small enough to verify exhaustively -- ``adr-010`` V0;
* the **endgame slices** size the retrograde databases -- ``adr-004`` part 3.

Everything here is closed form. Nothing imports ``fliphex``: that is deliberate.
``adr-010`` V1 compares this formula against what the solver's enumerator
actually produces, and a comparison is only evidence if the two sides are
computed by genuinely different means. Keep this file free of engine imports.

Note the bound counts *configurations consistent with the invariants*, not
positions reachable by legal play, so it is an upper bound. Measuring the gap is
V1's other job.

Cell counts must be **odd** (``adr-011``): scoring is a cell count, so an even
board admits ties and the canonical rules define no tie-break. ``--even`` exists
only to inspect such a board, never to cost a solve on one.

    python scripts/layer_profile.py                  # shipped 5x5, full deck
    python scripts/layer_profile.py --cells 15 --hands 8 7    # 5x3, adr-011 deck
    python scripts/layer_profile.py --cells 9 --hands 5 4     # 3x3, adr-011 deck
    python scripts/layer_profile.py --cells 9                 # 3x3, full deck
"""

from __future__ import annotations

import argparse
from math import comb


def layer(n_cells: int, d1: int, d2: int, t: int) -> int:
    """Number of configurations with exactly ``t`` cells filled."""
    return comb(n_cells, t) * 2**t * comb(d1, (t + 1) // 2) * comb(d2, t // 2)


def profile(n_cells: int, d1: int, d2: int) -> list[int]:
    return [layer(n_cells, d1, d2, t) for t in range(n_cells + 1)]


def sci(x: int | float) -> str:
    """Render as a mantissa/exponent string, or plainly when small."""
    if x == 0:
        return "0"
    if x < 10_000:
        return f"{x:>9,}"
    return f"{x:>9.3g}"


def report(n_cells: int, d1: int, d2: int, endgame: int) -> None:
    counts = profile(n_cells, d1, d2)
    total = sum(counts)
    peak = max(range(len(counts)), key=counts.__getitem__)

    print(f"Board: {n_cells} cells   hands: {d1} (P1, odd plies) + {d2} (P2)")
    print(f"Plies: {n_cells}   ({d1} + {d2} = {d1 + d2} tiles available)")
    if d1 + d2 < n_cells:
        print("  !! hands cannot fill the board -- check the deck sizes")
    print()

    print(
        f"  {'t':>3} {'ply':>4} {'k empty':>8} {'configurations':>12} "
        f"{'% total':>8}  profile"
    )
    print("  " + "-" * 62)
    widest = counts[peak]
    for t, c in enumerate(counts):
        share = 100 * c / total
        bar = "#" * round(40 * c / widest)
        mark = "  <== peak" if t == peak else ""
        print(f"  {t:>3} {t:>4} {n_cells - t:>8} {sci(c)} {share:>7.2f}%  {bar}{mark}")

    print()
    print(f"  total ................ {total:.4g}")
    print(
        f"  peak layer ........... t = {peak} ({counts[peak]:.4g}, "
        f"{100 * counts[peak] / total:.1f}% of all states)"
    )
    print(f"  terminal layer t = {n_cells} .. {counts[-1]:,}")
    print("      (all cells filled, both hands exhausted -- decided by counting")
    print("       cells, so it is verifiable in closed form: adr-010 V0)")

    print()
    print("  endgame slices (k = empty cells, i.e. the last k plies):")
    cum = 0
    for k in range(0, min(endgame, n_cells) + 1):
        cum += counts[n_cells - k]
        print(f"    k <= {k} ............... {cum:.4g}")

    shape = "hump" if 0 < peak < n_cells else "monotone"
    print()
    print(f"  shape: {shape}. ", end="")
    if shape == "hump":
        print("The widest part of the state space is the MIDDLE, not")
        print("  the endgame -- so there is no convergence to exploit, and")
        print("  meeting in the middle is the worst available meeting point.")
    else:
        print("Monotone profile.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cells", type=int, default=25, help="board cells (default 25)")
    p.add_argument(
        "--hands",
        type=int,
        nargs=2,
        metavar=("D1", "D2"),
        default=(13, 12),
        help="deck sizes for P1 and P2 (default 13 12)",
    )
    p.add_argument(
        "--endgame",
        type=int,
        default=5,
        help="largest k to report an endgame slice for (default 5)",
    )
    p.add_argument(
        "--even",
        action="store_true",
        help="allow an even cell count (adr-011 forbids it for a playable "
        "variant; this is for inspecting a board, not costing a solve)",
    )
    args = p.parse_args()
    if args.cells % 2 == 0 and not args.even:
        p.error(
            f"{args.cells} cells is even, so the board admits ties and the rules "
            f"define no tie-break -- adr-011 forbids it as a variant. Pass "
            f"--even to profile it anyway."
        )
    report(args.cells, args.hands[0], args.hands[1], args.endgame)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
