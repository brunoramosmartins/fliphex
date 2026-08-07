"""One-step-back reachability, layer by layer — the EXP-005 instrument.

`adr-012 <../docs/adr/adr-012-endgame-database-storage.md>`_ decision 7 allows
exactly one source of don't-cares: a configuration with **no legal
predecessor**. Nothing else may be treated as free, because nothing else is
recoverable once the table is filled. This module measures how many such
configurations there are, per layer, before any filling happens.

Why "one step back" and not "unreachable from the opening"
----------------------------------------------------------
They are different quantities, and the registered one is the first. A
configuration with no legal predecessor is provably unvisitable; a configuration
whose only predecessors are themselves unreachable is *also* unvisitable, but
proving that needs the transitive closure. The closure is strictly larger and
strictly more expensive, and `EXP-005`'s decision rule is written against the
local test. So this counts the local test, and the docstring says so rather than
letting a reader assume the stronger claim.

How it is counted, and why not by inverting the rule
-----------------------------------------------------
The obvious implementation inverts the flip rule: given a configuration, undo
each candidate placement and check the result is consistent. That would be a
second, hand-written statement of the rules — precisely what
:mod:`solver.packed_sweep` refuses to do, and for the same reason.

So this goes **forward** instead. It walks every configuration of layer ``t-1``,
generates every legal move with the machinery the sweep already uses, and marks
the successor's bit. What is left unmarked in layer ``t`` has no predecessor, by
construction rather than by argument. One bit per configuration: the 5×3's
largest layer is 5.02 × 10⁹ configurations, so 628 MB, and only one layer's
bitset is resident at a time.

It differs from :meth:`PackedSweep.sweep` in one way that matters: the sweep
stops at the first winning successor, and this must not stop at all. A
short-circuit here would undercount predecessors and inflate the orphan count —
which is why the loop is written out rather than shared.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fliphex.board import Board
from fliphex.variant import Variant
from solver.packed_sweep import PackedSweep

#: Population count per byte. The marking pass touches every configuration
#: once; counting them afterwards should not touch them again one bit at a time.
_POPCOUNT = bytes(bin(b).count("1") for b in range(256))


@dataclass
class LayerReach:
    """What one layer's predecessors look like."""

    t: int
    total: int
    with_predecessor: int

    @property
    def orphans(self) -> int:
        """Configurations no legal move can produce."""
        return self.total - self.with_predecessor

    @property
    def orphan_fraction(self) -> float:
        return self.orphans / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "layer": self.t,
            "total": self.total,
            "with_predecessor": self.with_predecessor,
            "orphans": self.orphans,
            "orphan_fraction": round(self.orphan_fraction, 6),
        }


@dataclass
class ReachResult:
    layers: list[LayerReach] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(layer.total for layer in self.layers)

    @property
    def orphans(self) -> int:
        return sum(layer.orphans for layer in self.layers)

    @property
    def orphan_fraction(self) -> float:
        return self.orphans / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "layers": [layer.as_dict() for layer in self.layers],
            "total": self.total,
            "orphans": self.orphans,
            "orphan_fraction": round(self.orphan_fraction, 6),
        }


class Reachability:
    """Predecessor marking over the same index the sweep uses.

    The index is deliberately :class:`~solver.packed_sweep.PackedSweep`'s, not a
    new one: a don't-care count is only usable by the sweep if it is expressed in
    the sweep's own coordinates.
    """

    def __init__(self, variant: Variant, board: Board | None = None) -> None:
        self.variant = variant
        self.board = board if board is not None else variant.board()
        self.sweep = PackedSweep(self.variant, self.board)
        self.n = self.sweep.n

    def layer_size(self, t: int) -> int:
        return self.sweep.layer_size(t)

    def predecessor_bits(self, t: int) -> bytearray:
        """Bitset over layer ``t``: set iff some layer ``t-1`` move produces it.

        Layer 0 is the opening position, which has no predecessor and needs
        none; it is reachable by definition and is handled by the caller.
        """
        if t < 1:
            raise ValueError("layer 0 has no predecessors to enumerate")

        sweep = self.sweep
        size = sweep.layer_size(t)
        marks = bytearray((size + 7) // 8)

        source = t - 1
        full = (1 << self.n) - 1
        mover_first = sweep.mover_is_first(source)
        mover_purple = mover_first == sweep.first_is_purple
        patterns = sweep.patterns[0 if mover_first else 1]
        flip = sweep.flip

        # Radices of the layer being marked, hoisted: they depend only on t.
        up_first, up_second = sweep.spent_counts(t)
        up_radix_first = sweep.binom[sweep.hand_sizes[0]][up_first]
        up_radix_second = sweep.binom[sweep.hand_sizes[1]][up_second]
        up_colour_shift = 1 << t
        rank_first, rank_second = sweep.spent_ranks
        rank_cells = sweep._rank_cells  # noqa: SLF001 — same module family

        for _index, occupied, purple, spent_f, spent_s in sweep._layer_configurations(  # noqa: SLF001
            source
        ):
            spent = spent_f if mover_first else spent_s

            remaining = full & ~occupied
            while remaining:
                low = remaining & -remaining
                remaining ^= low
                cell_flip = flip[low.bit_length() - 1]
                new_occupied = occupied | low

                for position, position_patterns in enumerate(patterns):
                    if spent >> position & 1:
                        continue
                    if mover_first:
                        tail = (
                            rank_first[spent_f | (1 << position)] * up_radix_second
                            + rank_second[spent_s]
                        )
                    else:
                        tail = (
                            rank_first[spent_f] * up_radix_second
                            + rank_second[spent_s | (1 << position)]
                        )
                    for pattern in position_patterns:
                        new_purple = purple ^ (cell_flip[pattern] & occupied)
                        if mover_purple:
                            new_purple |= low
                        cells_rank, colour_bits = rank_cells(new_occupied, new_purple)
                        child = (
                            cells_rank * up_colour_shift + colour_bits
                        ) * up_radix_first * up_radix_second + tail
                        marks[child >> 3] |= 1 << (child & 7)

        return marks

    def layer(self, t: int) -> LayerReach:
        """Count layer ``t``'s configurations that some move can produce."""
        size = self.layer_size(t)
        if t == 0:
            return LayerReach(t=0, total=size, with_predecessor=size)
        marks = self.predecessor_bits(t)
        return LayerReach(t=t, total=size, with_predecessor=_count(marks, size))

    def run(self, observer=None) -> ReachResult:
        """Every layer, bottom up. ``observer(LayerReach)`` after each."""
        result = ReachResult()
        for t in range(self.n + 1):
            layer = self.layer(t)
            result.layers.append(layer)
            if observer is not None:
                observer(layer)
        return result


def _count(marks: bytearray, size: int) -> int:
    """Set bits in ``marks``, ignoring the padding above ``size``.

    Padding bits are never written — ``child`` is always below ``size`` — but
    masking the tail anyway means a future indexing bug shows up as a failed
    assertion in the tests rather than as a plausible-looking count.
    """
    tail = size & 7
    if tail:
        last = len(marks) - 1
        if marks[last] & ~((1 << tail) - 1) & 0xFF:
            raise AssertionError("a mark landed above the layer's size")
    popcount = _POPCOUNT
    return sum(popcount[b] for b in marks)


def measure(variant: Variant, board: Board | None = None) -> ReachResult:
    """Run the whole measurement for ``variant``."""
    return Reachability(variant, board).run()
