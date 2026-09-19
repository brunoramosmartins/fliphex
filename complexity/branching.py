"""How wide the game is at each ply, exactly rather than by sampling.

The legal-move count at a node is::

    (cells still empty) * (sum of rotation orbits over the mover's remaining tiles)

The first factor is fixed by the ply: ``n - t``, always. The second is not --
it depends on *which* tiles the mover has already spent, and the orbits run
from 1 (``P6``, ``JOKER``) to 6. So there is no single branching factor at ply
``t``; there is a distribution, and this module computes it in closed form.

Weighting, which is the part that is easy to get wrong
------------------------------------------------------
Nodes at ply ``t`` are not spread evenly over the mover's possible spent sets.
A prefix that spends a 6-orbit tile can have reached its position by six times
as many routes as one that spends ``P6``, so a spent set ``S`` carries weight
proportional to ``prod(orbits of S)``. Averaging over spent sets uniformly would
answer a different question -- one about hands rather than about the tree.

The difference is not decorative, and it runs one way at every ply. On the
shipped board the node-weighted mean is **628.7** at ``t = 8`` against **682.6**
counting each spent set once, **161.8** against **200.8** at ``t = 16``, and
**2.9** against **4.5** at the last ply -- a gap that grows from 8% to 36%.
The weighting favours having spent the wide tiles and being left with the narrow
ones, so **the tree's typical node is narrower than the hands alone suggest**,
increasingly so as the game goes on.

The identity that makes this checkable
--------------------------------------
Every node at ply ``t`` has one child per legal move, so::

    node-weighted mean branching at t  ==  prefixes(t + 1) / prefixes(t)

exactly, as a ratio of integers. :func:`cross_check` asserts it on every ply,
against ``complexity.game_tree.prefixes``, which is derived by a different route
(elementary symmetric polynomials over the whole hand, no subset enumeration).
Because the means are ratios rather than averages of products, they telescope:
their product over all plies is the exact game-tree complexity, with no Jensen
gap to apologise for.

What the shape says
-------------------
The branching profile falls monotonically -- FLIPHEX gets narrower every ply,
on both factors at once. The hump in ``complexity/state_space.py``'s profile is
therefore *not* a branching effect; it comes from the ``C(n, t)`` cell factor,
which peaks in the middle while the width only shrinks.

The spread is what makes random-rollout tree estimation expensive. At ``t = 16``
the widest node is three times the narrowest; at the last ply it is six times.
Compounded over 25 plies that is the multiplicative skew
``complexity.game_tree.rollout_estimate`` measures as a relative standard
deviation of about five.

    python -m complexity.branching
    python -m complexity.branching --board 5 3
    python -m complexity.branching --all --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import factorial, perm, prod

from complexity.game_tree import (
    ORBITS,
    elementary_symmetric,
    games,
    prefixes,
)
from fliphex.variant import Arm, Variant


@dataclass(frozen=True, slots=True)
class Branching:
    """The exact distribution of legal-move counts at one ply."""

    t: int
    mover_is_first: bool
    #: ``(legal moves, number of nodes)``, ascending by move count.
    width: tuple[tuple[int, int], ...]
    #: Mean width over the mover's possible spent sets, each counted once.
    #: Kept as a field rather than derived, because recovering it from
    #: :attr:`width` is impossible: the collapse to distinct widths has already
    #: thrown away how many spent sets produced each one.
    uniform_mean: float

    @property
    def nodes(self) -> int:
        """Nodes at this ply. Equals ``prefixes(variant, t)``."""
        return sum(count for _, count in self.width)

    @property
    def minimum(self) -> int:
        return self.width[0][0]

    @property
    def maximum(self) -> int:
        return self.width[-1][0]

    @property
    def distinct(self) -> int:
        """How many different widths occur. 1 means the ply is uniform."""
        return len(self.width)

    @property
    def mean_exact(self) -> Fraction:
        """Node-weighted mean, exact. This is the quantity that telescopes."""
        return Fraction(sum(moves * count for moves, count in self.width), self.nodes)

    @property
    def mean(self) -> float:
        return float(self.mean_exact)

    @property
    def spread(self) -> float:
        """Widest node over narrowest. 1.0 at a uniform ply."""
        return self.maximum / self.minimum

    def as_dict(self) -> dict[str, object]:
        return {
            "ply": self.t,
            "mover": 1 if self.mover_is_first else 2,
            "nodes": self.nodes,
            "min": self.minimum,
            "max": self.maximum,
            "mean": self.mean,
            "uniform_mean": self.uniform_mean,
            "spread": self.spread,
            "distinct": self.distinct,
            "width": [list(pair) for pair in self.width],
        }


def branching_at(variant: Variant, t: int) -> Branching:
    """The exact width distribution at ply ``t``, node-weighted.

    Args:
        variant: The board and deck.
        t: Ply index, ``0 <= t < variant.n_cells``. The last legal ply is
            ``n_cells - 1``; there is no ply ``n_cells``, because the board is
            full and, adr-011 having made the cell count odd, both hands have
            exhausted exactly.

    Enumerates the mover's spent sets -- at most ``C(13, 6) = 1716`` of them on
    the shipped board -- and weights each by the product of its orbits.
    """
    if not 0 <= t < variant.n_cells:
        raise ValueError(f"t must be in 0..{variant.n_cells - 1}, got {t}")

    mover_is_first = t % 2 == 0
    first_hand, second_hand = variant.deck_names()
    hand = first_hand if mover_is_first else second_hand
    other = second_hand if mover_is_first else first_hand

    orbits = [ORBITS[tile] for tile in hand]
    available = sum(orbits)
    spent_count = t // 2
    empty_cells = variant.n_cells - t

    # Everything the mover's own spent set does not vary over: which cell each
    # ply used, the order each player played its tiles in, and the other
    # player's spent set with its rotations. Constant across the loop, so it
    # does not touch the mean -- but without it the weights are not node
    # counts, and the identity against ``prefixes`` has nothing to compare.
    spent_first, spent_second = (t + 1) // 2, t // 2
    elsewhere = elementary_symmetric([ORBITS[tile] for tile in other])[
        spent_second if mover_is_first else spent_first
    ]
    scale = (
        perm(variant.n_cells, t)
        * factorial(spent_first)
        * factorial(spent_second)
        * elsewhere
    )

    tally: dict[int, int] = {}
    unweighted, sets = 0, 0
    for spent in combinations(range(len(orbits)), spent_count):
        weight = scale * prod(orbits[i] for i in spent)
        moves = empty_cells * (available - sum(orbits[i] for i in spent))
        tally[moves] = tally.get(moves, 0) + weight
        unweighted += moves
        sets += 1

    return Branching(
        t=t,
        mover_is_first=mover_is_first,
        width=tuple(sorted(tally.items())),
        uniform_mean=unweighted / sets,
    )


def profile(variant: Variant) -> tuple[Branching, ...]:
    """Every ply, ``t = 0`` through ``n_cells - 1``."""
    return tuple(branching_at(variant, t) for t in range(variant.n_cells))


def cross_check(variant: Variant) -> list[str]:
    """Verify the distribution against ``game_tree``. Empty when clean.

    Three claims, each against a quantity derived without enumerating subsets:

    1. the node count at ply ``t`` is ``prefixes(t)``;
    2. the node-weighted mean is ``prefixes(t + 1) / prefixes(t)``, exactly;
    3. the means telescope to the exact game-tree complexity.
    """
    problems: list[str] = []
    product = Fraction(1)
    for ply in profile(variant):
        expected_nodes = prefixes(variant, ply.t)
        if ply.nodes != expected_nodes:
            problems.append(
                f"t={ply.t}: {ply.nodes:,} nodes, expected {expected_nodes:,}"
            )
        expected_mean = Fraction(prefixes(variant, ply.t + 1), prefixes(variant, ply.t))
        if ply.mean_exact != expected_mean:
            problems.append(
                f"t={ply.t}: mean {ply.mean_exact}, expected {expected_mean}"
            )
        product *= ply.mean_exact
    if product != games(variant):
        problems.append(f"means telescope to {product}, expected {games(variant):,}")
    return problems


def self_check() -> list[str]:
    """Cross-check every board this project solves, both arms where they exist."""
    problems: list[str] = []
    for cols, rows in ((5, 1), (3, 3), (5, 3), (5, 5)):
        arms = [Arm.H1] if (cols, rows) == (5, 5) else [Arm.H1, Arm.H2]
        for arm in arms:
            variant = Variant(cols, rows, arm)
            problems += [f"{variant.name}: {p}" for p in cross_check(variant)]
    return problems


def _render(variant: Variant) -> None:
    print(f"\n  === {variant.name} — {variant.n_cells} cells ===\n")
    print("      ply  mover      min      max     mean   uniform  spread  distinct")
    for ply in profile(variant):
        print(
            f"    {ply.t:5d}    P{1 if ply.mover_is_first else 2}  "
            f"{ply.minimum:8,} {ply.maximum:8,} {ply.mean:8.1f} "
            f"{ply.uniform_mean:9.1f} {ply.spread:7.2f} {ply.distinct:9d}"
        )
    print()
    print(f"    means telescope to .... {games(variant):,}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", nargs=2, type=int, default=[5, 5], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--all", action="store_true", help="3x3, 5x3 and the shipped 5x5")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    problems = self_check()
    if problems:
        print("  SELF-CHECK FAILED — no number below is reportable")
        for problem in problems:
            print(f"    {problem}")
        return 1

    boards = [(3, 3), (5, 3), (5, 5)] if args.all else [tuple(args.board)]
    variants = [
        Variant(
            cols,
            rows,
            Arm.H1 if (args.all or (cols, rows) == (5, 5)) else Arm(args.arm),
        )
        for cols, rows in boards
    ]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "variant": v.name,
                        "cells": v.n_cells,
                        "games": games(v),
                        "plies": [ply.as_dict() for ply in profile(v)],
                    }
                    for v in variants
                ],
                indent=2,
            )
        )
        return 0

    for variant in variants:
        _render(variant)
    print("\n    self-check ............ ok (identity holds on every ply)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
