"""How many distinct games FLIPHEX has, and why no sampling is needed to say so.

The roadmap asked for a Monte Carlo estimate of game-tree size via random
rollouts. The estimate is not needed: **the count is exact and closed form.**

Why the tree is a product
-------------------------
A move is (empty cell, tile in hand, distinct rotation), and *every* such triple
is legal. There is no capture condition to satisfy, no passing, no move that
some position forbids. So a complete game is nothing more than three independent
choices made once each:

* a bijection from plies to cells -- ``n!`` ways;
* a bijection from the first player's plies to the first player's tiles, and the
  same for the second -- ``d1!`` and ``d2!``;
* a rotation per tile, from that tile's orbit.

Hence::

    games = n! * d1! * prod(orbits of hand 1) * d2! * prod(orbits of hand 2)

The tree is genuinely **unbalanced** -- the branching factor at a node depends on
which tiles the mover has left, and the orbits run from 1 (``P6``, ``JOKER``)
to 6 -- so no single ``b**d`` is exact. The leaf count is exact anyway, because
summing over orderings restores the symmetry that individual nodes break.

Truncate the sum at ``k`` plies and the same argument gives the number of
distinct ``k``-ply prefixes, with the products replaced by **elementary
symmetric polynomials** over the orbit sizes: choosing ``j`` tiles in order from
a hand contributes ``j! * e_j(orbits)``. At ``k = n`` every tile is chosen,
``e_d`` is the full product, and the two forms agree.

Verified against the engine
---------------------------
Gate 7 of ``docs/measurement-gates.md``. The closed form was checked against
exhaustive enumeration by ``fliphex.legal_moves`` / ``fliphex.apply_move`` on
both reduced boards and both deck arms, to three plies -- the depth at which one
player has spent two tiles, so the ``e_2`` term is exercised rather than
assumed. Sixteen cases, sixteen exact matches, recorded in :data:`KNOWN`.

What the estimator is still doing here
--------------------------------------
:func:`rollout_estimate` implements Knuth's 1975 random-path estimator, the one
the roadmap asked for. It is retained and it reports a number, but it is a
**verification of the formula, not the measurement** -- the same status
``EXP-005``'s hours-long run took when its quantity turned out to be a counting
identity. An estimator with an exact answer to check against is worth keeping;
an estimate published in place of that exact answer would not be.

And it is worth keeping for a second reason, which is that it is a good
argument against itself. The estimator is unbiased and still lands 25% from the
truth at 300 rollouts on the shipped board, because the tree's branching is
multiplicatively skewed. Reaching 1% would take on the order of 10^5 rollouts.
Read :func:`rollout_estimate` for the measured numbers; ``exercises/ex05`` asks
for exactly this variance argument.

    python -m complexity.game_tree
    python -m complexity.game_tree --all
    python -m complexity.game_tree --board 3 3 --samples 2000
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from math import factorial, log10, prod

from fliphex import apply_move, legal_moves, piece
from fliphex.variant import Arm, Variant


def _orbit_sizes() -> dict[str, int]:
    """Distinct rotations per archetype, derived rather than tabulated.

    ``P6`` has one, ``P3-tri`` two, the opposite-pair tiles three, the rest six,
    and the joker has no arrows at all. Summing over the shipped deck gives 58,
    which is why the opening ply has 25 x 58 = 1450 moves.
    """
    sizes: dict[str, int] = {}
    for tile in piece.DECK:
        seen, mask = set(), tile.mask
        for _ in range(piece.N_SLOTS):
            seen.add(mask)
            mask = piece.rotate_mask(mask, 1)
        sizes[tile.archetype] = len(seen)
    sizes["JOKER"] = 1
    return sizes


#: Distinct rotations per archetype.
ORBITS = _orbit_sizes()


def elementary_symmetric(values: list[int]) -> list[int]:
    """Return ``[e_0, e_1, ..., e_n]`` for ``values``.

    ``e_j`` is the sum over all ``j``-subsets of the product of their elements.
    It is what makes the prefix count exact on a hand whose tiles have different
    orbit sizes: ``sum(orbits) ** j`` would count ordered selections with
    repetition, and a tile cannot be played twice.
    """
    e = [1] + [0] * len(values)
    for value in values:
        for j in range(len(values), 0, -1):
            e[j] += e[j - 1] * value
    return e


def _orbits(variant: Variant) -> tuple[list[int], list[int]]:
    first, second = variant.deck_names()
    return [ORBITS[t] for t in first], [ORBITS[t] for t in second]


def prefixes(variant: Variant, k: int) -> int:
    """Distinct sequences of ``k`` legal plies from the opening.

    Args:
        variant: The board and deck.
        k: Plies, ``0 <= k <= variant.n_cells``.

    At ``k = variant.n_cells`` this is the game-tree complexity: the number of
    distinct complete games, which is what :func:`games` returns.
    """
    if not 0 <= k <= variant.n_cells:
        raise ValueError(f"k must be in 0..{variant.n_cells}, got {k}")
    first, second = _orbits(variant)
    e_first, e_second = (
        elementary_symmetric(first),
        elementary_symmetric(second),
    )
    spent_first, spent_second = (k + 1) // 2, k // 2
    cells = factorial(variant.n_cells) // factorial(variant.n_cells - k)
    return (
        cells
        * factorial(spent_first)
        * e_first[spent_first]
        * factorial(spent_second)
        * e_second[spent_second]
    )


def games(variant: Variant) -> int:
    """The game-tree complexity: distinct complete games from the opening."""
    first, second = _orbits(variant)
    return (
        factorial(variant.n_cells)
        * factorial(len(first))
        * prod(first)
        * factorial(len(second))
        * prod(second)
    )


def effective_branching(variant: Variant) -> float:
    """The uniform ``b`` a tree of this depth and leaf count would need.

    Not a branching factor anyone measured -- the real one varies by ply and by
    which tiles remain, which is ``complexity/branching.py``'s subject. This is
    the number the cross-game literature quotes as ``b`` when it writes ``b**d``,
    recovered from the exact leaf count instead of the other way round.
    """
    return 10 ** (log10(games(variant)) / variant.n_cells)


def minimal_tree(variant: Variant) -> float:
    """Knuth-Moore best case: leaves alpha-beta visits under perfect ordering.

    ``b**ceil(d/2) + b**floor(d/2) - 1``, with ``b`` from
    :func:`effective_branching`. **Two assumptions, neither of them measured
    here**: that move ordering is perfect, and that the branching is uniform.
    It is an order of magnitude, not a result, and it is the figure the
    cross-game table means by "the weak-solution route".

    Note ``ceil`` rather than a square root. The shipped board has odd depth, so
    the minimal tree is ``b**13``, which exceeds ``sqrt(b**25)`` by ``b**0.5``.
    """
    b = effective_branching(variant)
    return b ** ((variant.n_cells + 1) // 2) + b ** (variant.n_cells // 2) - 1


@dataclass(frozen=True, slots=True)
class RolloutEstimate:
    """What Knuth's random-path estimator returned, against the exact answer."""

    samples: int
    seed: int
    mean: float
    sd: float
    exact: int

    @property
    def relative_sd(self) -> float:
        """Spread of a single rollout, as a fraction of the exact count."""
        return self.sd / self.exact if self.exact else 0.0

    @property
    def ratio(self) -> float:
        """Estimate over truth. Unbiasedness says this tends to 1."""
        return self.mean / self.exact if self.exact else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "samples": self.samples,
            "seed": self.seed,
            "mean": self.mean,
            "sd": self.sd,
            "exact": self.exact,
            "relative_sd": self.relative_sd,
            "ratio": self.ratio,
        }


def rollout_estimate(
    variant: Variant, samples: int = 400, seed: int = 1
) -> RolloutEstimate:
    """Knuth's 1975 estimator, run against the real engine.

    Walk uniformly at random from the opening to a full board, multiplying the
    legal-move count at every node. The product is an unbiased estimate of the
    leaf count: a leaf at depth ``d`` is reached with probability
    ``1 / prod(b_i)`` along its own path, so each leaf contributes exactly 1 in
    expectation, and the expectation is the number of leaves.

    **Unbiasedness is not accuracy, and here it is not even close to it.** The
    variance is driven by how unbalanced the tree is in the multiplicative
    sense, and FLIPHEX is badly unbalanced: a mover holding ``P6`` and the
    joker has two rotations available where a mover holding six ordinary tiles
    has thirty-six, and twenty-five plies of that compound into a very wide
    distribution. Measured relative standard deviation of a single rollout is
    **~4.0 on the 3x3 and ~5.1 on the shipped board** -- four to five times the
    quantity being estimated.

    The standard error of the mean therefore falls as ``relative_sd /
    sqrt(samples)``, which on the 3x3 means about **160,000 rollouts for 1%**.
    Measured convergence at seed 7: 0.67 at 100 samples, 1.14 at 1,000, 1.05 at
    10,000, 1.02 at 60,000. It converges, and :func:`games` returns the answer
    exactly in microseconds.

    The moves come from :func:`fliphex.legal_moves`, so this genuinely samples
    the engine's tree rather than the combinatorial model the closed form
    assumes. That is the point: agreement is evidence the two describe the same
    object.
    """
    if samples < 1:
        raise ValueError("samples must be at least 1")
    rng = random.Random(seed)
    board = variant.board()
    estimates: list[float] = []
    for _ in range(samples):
        state = variant.initial_state()
        product = 1.0
        for _ in range(variant.n_cells):
            moves = legal_moves(board, state)
            product *= len(moves)
            state = apply_move(board, state, rng.choice(moves))
        estimates.append(product)
    mean = sum(estimates) / len(estimates)
    if len(estimates) > 1:
        variance = sum((e - mean) ** 2 for e in estimates) / (len(estimates) - 1)
    else:
        variance = 0.0
    return RolloutEstimate(
        samples=samples,
        seed=seed,
        mean=mean,
        sd=variance**0.5,
        exact=games(variant),
    )


#: Prefix counts enumerated exhaustively by the engine, before this module
#: existed. Gate 7: no instrument reports a number until it reproduces one that
#: is already known by other means. Depth 3 is the shallowest depth at which a
#: player has spent two tiles, so it is the shallowest that tests ``e_2``.
KNOWN: dict[str, tuple[int, ...]] = {
    #        k = 0, 1,       2,          3
    "3x3-h1": (1, 180, 27_360, 2_777_040),
    "3x3-h2": (1, 225, 34_200, 4_596_480),
    "5x3-h1": (1, 525, 249_900, 95_975_880),
    "5x3-h2": (1, 540, 257_040, 102_287_640),
}

#: Complete games counted exhaustively, at **full depth** rather than a prefix.
#:
#: The 5x1 is the smallest board adr-011 admits -- five cells, hands 3 + 2 --
#: and it is small enough to walk to the last ply. That makes it the only place
#: :func:`games` itself is checked against the rules rather than against its own
#: prefix at ``k = n``. The registry already uses the 5x1 the same way, as the
#: board where EXP-005's one-step identity was first confirmed.
KNOWN_GAMES: dict[str, int] = {
    "5x1-h1": 51_840,
    "5x1-h2": 311_040,
}

#: The opening ply on the shipped board, from ``fliphex/moves.py``'s docstring
#: and ``.claude/CLAUDE.md``: 25 cells x 58 distinct (tile, rotation) pairs.
SHIPPED_OPENING_MOVES = 1450


def self_check() -> list[str]:
    """Reproduce every known value. Returns the failures, empty when clean."""
    problems: list[str] = []
    for name, counts in KNOWN.items():
        board, arm = name.rsplit("-", 1)
        cols, rows = (int(x) for x in board.split("x"))
        variant = Variant(cols, rows, Arm(arm))
        for k, want in enumerate(counts):
            have = prefixes(variant, k)
            if have != want:
                problems.append(f"{name} k={k}: {have:,}, expected {want:,}")
    for name, want in KNOWN_GAMES.items():
        board, arm = name.rsplit("-", 1)
        cols, rows = (int(x) for x in board.split("x"))
        have = games(Variant(cols, rows, Arm(arm)))
        if have != want:
            problems.append(f"{name} games: {have:,}, expected {want:,}")
    shipped = Variant(5, 5, Arm.H1)
    opening = prefixes(shipped, 1)
    if opening != SHIPPED_OPENING_MOVES:
        problems.append(
            f"5x5-h1 opening: {opening:,}, expected {SHIPPED_OPENING_MOVES:,}"
        )
    if sum(ORBITS[t] for t in shipped.deck_names()[0]) != 58:
        problems.append("shipped deck does not sum to 58 distinct rotations")
    return problems


def _render(variant: Variant, estimate: RolloutEstimate | None) -> None:
    total = games(variant)
    print(f"\n  === {variant.name} — {variant.n_cells} cells ===\n")
    print(f"    opening moves ......... {prefixes(variant, 1):,}")
    print(f"    games (exact) ......... {float(total):.4g}")
    print(f"      log10 ............... {log10(total):.2f}")
    print(f"      in full ............. {total:,}")
    print(f"    effective b ........... {effective_branching(variant):.1f}")
    print(f"    Knuth-Moore minimal ... 10^{log10(minimal_tree(variant)):.2f}")
    if estimate is not None:
        print()
        print(f"    rollout estimate ...... {estimate.mean:.4g}")
        print(f"      samples / seed ...... {estimate.samples} / {estimate.seed}")
        print(f"      estimate / exact .... {estimate.ratio:.4f}")
        print(f"      relative sd ......... {estimate.relative_sd:.4f}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", nargs=2, type=int, default=[5, 5], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--all", action="store_true", help="3x3, 5x3 and the shipped 5x5")
    p.add_argument("--samples", type=int, default=400)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--no-rollout", action="store_true", help="closed form only")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    problems = self_check()
    if problems:
        print("  SELF-CHECK FAILED — no number below is reportable")
        for problem in problems:
            print(f"    {problem}")
        return 1

    boards = [(3, 3), (5, 3), (5, 5)] if args.all else [tuple(args.board)]
    rows = []
    for cols, rows_ in boards:
        arm = Arm.H1 if (args.all or (cols, rows_) == (5, 5)) else Arm(args.arm)
        variant = Variant(cols, rows_, arm)
        estimate = (
            None
            if args.no_rollout
            else rollout_estimate(variant, args.samples, args.seed)
        )
        rows.append((variant, estimate))

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "variant": v.name,
                        "cells": v.n_cells,
                        "opening_moves": prefixes(v, 1),
                        "games": games(v),
                        "log10_games": round(log10(games(v)), 4),
                        "effective_branching": round(effective_branching(v), 4),
                        "log10_minimal_tree": round(log10(minimal_tree(v)), 4),
                        "rollout": e.as_dict() if e else None,
                    }
                    for v, e in rows
                ],
                indent=2,
            )
        )
        return 0

    for variant, estimate in rows:
        _render(variant, estimate)
    print("\n    self-check ............ ok (every known value reproduced)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
