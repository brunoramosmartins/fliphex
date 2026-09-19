"""How many positions FLIPHEX has, and how many of them a game can reach.

Three numbers, in decreasing order of size and increasing order of honesty.

**The orientation-inflated bound.** The roadmap's original expression multiplied
by ``6 ** n_cells`` for tile orientations. It is wrong, and
`adr-006 <../docs/adr/adr-006-no-chain-reaction.md>`_ is why: arrows fire once,
on the ply the tile is placed, and a placed tile is inert thereafter. Nothing
downstream can read its rotation, so the rotation is not part of the state. It
is kept here under :func:`orientation_inflated` because "the bound was corrected"
is a claim that should come with the discarded figure attached.

**The configuration space.** What remains once orientation is dropped: which
cells are filled, what colour each one shows, and which tiles each player has
spent. Per layer ``t``::

    C(n, t) * 2**t * C(d1, ceil(t / 2)) * C(d2, floor(t / 2))

This counts configurations *consistent with the invariants*, which is more than
the positions legal play produces, so it is an upper bound. It is also the
quantity `adr-010 <../docs/adr/adr-010-solver-correctness.md>`_ V1 checks the
solver's enumerator against layer by layer.

**The reachable bound.** Configurations minus those no move can produce. A
configuration has no predecessor exactly when every occupied cell carries the
colour of the player who did *not* just move: the last cell placed always shows
its placer's colour, because a tile's own arrows never point at the cell it
occupies, so if no cell shows the right colour then no cell can have been the
last. That is one of the ``2**t`` colourings under each (cell-set, hand-state),
which collapses the whole sum to a closed form with the ``2**t`` cancelled.

The correction is small and gets smaller: **3.28%** on the 3x3, **0.343%** on
the 5x3, **0.0079%** on the shipped 5x5. The mass of the space sits at high
``t``, where ``2**t`` is enormous.

Why there is no fourth number here
----------------------------------
The *transitive* closure — configurations no game reaches, rather than
configurations no single move produces — is strictly smaller again, and it has
no closed form. `EXP-007 <../experiments/registry.md>`_ measured six layers of
it on the 5x3 and was stopped: completing both arms was measured at ~100 hours
each, and on the shipped board the one-step correction is already in the fourth
decimal place. A table of games spanning 10^11 to 10^20 cannot tell the two
apart. The six measured layers are recorded in the registry; this module reports
the one-step bound and says so.

    python -m complexity.state_space
    python -m complexity.state_space --board 5 3
    python -m complexity.state_space --all --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from math import comb

from fliphex.variant import Arm, Variant

#: Rotations of a tile. Present only inside :func:`orientation_inflated`, which
#: exists to show what the corrected bound corrected.
ORIENTATIONS = 6


def configurations(n_cells: int, first: int, second: int, t: int) -> int:
    """Configurations with exactly ``t`` cells filled.

    Args:
        n_cells: Cells on the board.
        first: Hand size of the player who moves on odd plies. On every board
            this is the larger hand -- adr-011 gives the first player one tile
            more, so both hands exhaust exactly and the first player moves last.
        second: Hand size of the other player.
        t: Cells filled.

    The three factors are independent: which cells are filled, what colour each
    shows, and which tiles are spent. After ``t`` plies the first player has
    moved ``ceil(t / 2)`` times and the second ``floor(t / 2)``.
    """
    return comb(n_cells, t) * 2**t * comb(first, (t + 1) // 2) * comb(second, t // 2)


def orphans(n_cells: int, first: int, second: int, t: int) -> int:
    """Configurations in layer ``t`` that no single move produces.

    Exactly one colouring per (cell-set, hand-state) has no predecessor, so this
    is :func:`configurations` with the ``2**t`` factor cancelled rather than
    divided out -- the division would be exact anyway, but writing it as a
    product keeps the count in integers and makes the cancellation visible.

    **Layer 0 is not an orphan.** The identity calls it one, because the opening
    position has no predecessor. It is reachable by definition: it is where every
    game starts. Forgetting this is an off-by-one on every board, and the 3x3 is
    where it shows -- 23,371 against the unguarded sum's 23,372.
    """
    if t == 0:
        return 0
    return comb(n_cells, t) * comb(first, (t + 1) // 2) * comb(second, t // 2)


def orientation_inflated(n_cells: int, first: int, second: int) -> int:
    """The discarded bound: the configuration space times ``6 ** n_cells``.

    Recorded so the correction can be checked rather than believed. adr-006
    makes placed tiles inert, so nothing in the game can distinguish two
    positions that differ only in a placed tile's rotation, and a state
    representation that stored it would be counting distinctions the rules
    cannot see.
    """
    total = sum(configurations(n_cells, first, second, t) for t in range(n_cells + 1))
    return total * ORIENTATIONS**n_cells


@dataclass(frozen=True, slots=True)
class LayerCount:
    """One layer of the profile."""

    t: int
    configurations: int
    orphans: int

    @property
    def reachable(self) -> int:
        """Configurations with at least one legal predecessor."""
        return self.configurations - self.orphans

    @property
    def orphan_fraction(self) -> float:
        return self.orphans / self.configurations if self.configurations else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "layer": self.t,
            "configurations": self.configurations,
            "orphans": self.orphans,
            "reachable": self.reachable,
            "orphan_fraction": round(self.orphan_fraction, 8),
        }


@dataclass(frozen=True, slots=True)
class SpaceProfile:
    """The state space of one variant, layer by layer."""

    variant: str
    n_cells: int
    hands: tuple[int, int]
    layers: tuple[LayerCount, ...]

    @property
    def configurations(self) -> int:
        """The upper bound: every configuration consistent with the invariants."""
        return sum(layer.configurations for layer in self.layers)

    @property
    def orphans(self) -> int:
        return sum(layer.orphans for layer in self.layers)

    @property
    def reachable(self) -> int:
        """The tighter bound: configurations with at least one predecessor."""
        return self.configurations - self.orphans

    @property
    def orphan_fraction(self) -> float:
        return self.orphans / self.configurations

    @property
    def peak(self) -> LayerCount:
        """The largest layer. FLIPHEX's profile is a hump, not a funnel."""
        return max(self.layers, key=lambda layer: layer.configurations)

    def as_dict(self) -> dict[str, object]:
        return {
            "variant": self.variant,
            "cells": self.n_cells,
            "hands": list(self.hands),
            "configurations": self.configurations,
            "orphans": self.orphans,
            "reachable": self.reachable,
            "orphan_fraction": round(self.orphan_fraction, 8),
            "peak_layer": self.peak.t,
            "orientation_inflated": orientation_inflated(self.n_cells, *self.hands),
            "layers": [layer.as_dict() for layer in self.layers],
        }


def profile(variant: Variant) -> SpaceProfile:
    """Tabulate ``variant``'s state space.

    The hand sizes come from the variant's deck rather than from a rule of
    thumb, because adr-009 makes the deck a modelling choice that every artefact
    has to carry verbatim.
    """
    first, second = (len(names) for names in variant.deck_names())
    layers = tuple(
        LayerCount(
            t=t,
            configurations=configurations(variant.n_cells, first, second, t),
            orphans=orphans(variant.n_cells, first, second, t),
        )
        for t in range(variant.n_cells + 1)
    )
    return SpaceProfile(
        variant=variant.name,
        n_cells=variant.n_cells,
        hands=(first, second),
        layers=layers,
    )


#: Values established elsewhere, by other means, before this module existed.
#:
#: Gate 7 of ``docs/measurement-gates.md``: no instrument reports a number
#: before it reproduces one that is already known. The totals come from
#: ``scripts/layer_profile.py``, which computes the same formula and
#: deliberately imports nothing from ``fliphex`` so that adr-010 V1 compares two
#: genuinely independent implementations. The 3x3 total is also the figure
#: EXP-001 enumerated exhaustively, and the orphan counts are EXP-005's, whose
#: amendment of 2026-08-07 proved the identity this module relies on.
KNOWN: dict[tuple[int, int], dict[str, int]] = {
    (3, 3): {"configurations": 711_963, "orphans": 23_371},
    (5, 3): {"configurations": 17_506_580_337, "orphans": 60_009_757},
    (5, 5): {
        "configurations": 488_676_694_181_949_003,
        "orphans": 38_814_863_794_591,
    },
}


def self_check() -> list[str]:
    """Reproduce every known value. Returns the failures, empty when clean.

    Both arms are checked on the boards that have two, because the orphan count
    must **not** depend on the deck -- it counts colourings the mover's colour
    forbids and never looks at an arrow pattern. If the two arms ever disagreed
    here, the identity would be wrong rather than the decks interesting.
    """
    problems: list[str] = []
    for board, expected in KNOWN.items():
        arms = [Arm.H1, Arm.H2]
        if board == (5, 5):
            arms = [Arm.H1]  # no H2 arm exists: capacity 12 has nothing to promote
        for arm in arms:
            got = profile(Variant(board[0], board[1], arm))
            for field, want in expected.items():
                have = getattr(got, field)
                if have != want:
                    problems.append(
                        f"{got.variant}: {field} is {have:,}, expected {want:,}"
                    )
    return problems


def _render(space: SpaceProfile) -> None:
    hands = "+".join(str(h) for h in space.hands)
    print(f"\n  === {space.variant} — {space.n_cells} cells, hands {hands} ===\n")
    print(
        "    layer         configurations            orphans"
        "              reachable     frac"
    )
    for layer in space.layers:
        print(
            f"    {layer.t:5d} {layer.configurations:>22,} {layer.orphans:>18,} "
            f"{layer.reachable:>22,} {layer.orphan_fraction:>8.3%}"
        )
    inflated = orientation_inflated(space.n_cells, *space.hands)
    print()
    print(f"    orientation-inflated .. {inflated:.4g}   (wrong; adr-006)")
    print(f"    configurations ........ {space.configurations:,}")
    print(f"      as an upper bound ... {float(space.configurations):.4g}")
    print(
        f"    orphans ............... {space.orphans:,} ({space.orphan_fraction:.4%})"
    )
    print(f"    reachable bound ....... {space.reachable:,}")
    print(f"      as a bound .......... {float(space.reachable):.4g}")
    print(f"    peak layer ............ t = {space.peak.t}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", nargs=2, type=int, default=[5, 5], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--all", action="store_true", help="every board in KNOWN")
    p.add_argument("--json", action="store_true", help="machine-readable")
    args = p.parse_args()

    problems = self_check()
    if problems:
        print("  SELF-CHECK FAILED — no number below is reportable")
        for problem in problems:
            print(f"    {problem}")
        return 1

    boards = list(KNOWN) if args.all else [(args.board[0], args.board[1])]
    spaces = []
    for cols, rows in boards:
        arm = Arm.H1 if (args.all or (cols, rows) == (5, 5)) else Arm(args.arm)
        spaces.append(profile(Variant(cols, rows, arm)))

    if args.json:
        print(json.dumps([space.as_dict() for space in spaces], indent=2))
        return 0

    for space in spaces:
        _render(space)
    print("\n    self-check ............ ok (every known value reproduced)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
