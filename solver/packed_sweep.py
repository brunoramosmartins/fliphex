"""The same retrograde sweep, on packed integers instead of ``GameState``.

:mod:`solver.retrograde` is the **reference**: it is written for legibility, it
goes through ``GameState``/``legal_moves``/``apply_move``, and it is what
``EXP-001`` cross-checks the forward searcher against. Measured on the 3×3 it
runs at ~1,900 configurations/second, which puts the 5×3 (1.75 × 10¹⁰
configurations) at **108 days** and 10 GB. That is not a target; this module is
why.

Where the time goes, and why none of it is the algorithm
--------------------------------------------------------
Per configuration the reference builds a full ``GameState`` — a tuple of
colours, hand masks, and a **Zobrist hash over every cell and every tile** — then
``legal_moves`` allocates ``Move`` objects and ``apply_move`` builds another
state per successor. In a sweep the index *is* the key: nothing is ever looked up
by hash, and nothing reads ``history``. Every one of those bytes is computed and
discarded.

So this module keeps four integers — occupied cells, purple cells, and a spent
mask per player — and moves between them with bit operations.

What it does **not** do, deliberately
-------------------------------------
It does not reimplement the rules. That would destroy the thing the reference
exists for: adr-010 **V3** is only evidence because two implementations can
disagree, and two implementations that share a hand-copied flip rule cannot.

Instead the flip rule is *tabulated from* :mod:`fliphex`. ``_flip_table`` asks
``Board.neighbour`` which cells each arrow of each pattern points at, once, at
construction. The per-move work is then ``flip_table[cell][pattern] & occupied``
— the same rule ``fliphex.moves.apply_move`` applies, read out of the same
adjacency, not restated.

The equivalence is not argued, it is checked: ``tests/test_packed_sweep.py``
compares this sweep against the reference **byte for byte, on every layer** of
boards where both are affordable. If they ever diverge, this module is wrong and
the reference is right.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb

from fliphex.board import OFF_BOARD, Board
from fliphex.piece import N_SLOTS
from fliphex.state import TILES, Colour, other, tiles_in
from fliphex.variant import Variant
from solver.minimax import LOSS, WIN
from solver.retrograde import (
    SLOT_LOSS,
    SLOT_UNSET,
    SLOT_WIN,
    RetrogradeResult,
    SweepStats,
    rank_subset,
)


def _flip_table(board: Board) -> list[list[int]]:
    """``table[cell][pattern]`` — cells that pattern's arrows point at.

    Tabulated by asking :meth:`fliphex.board.Board.neighbour`, so the geometry
    is read out of the engine rather than restated here. Off-board arrows
    contribute nothing, which is the rule's own "arrows pointing off the board
    do nothing".
    """
    table = []
    for cell in range(board.n_cells):
        neighbours = [board.neighbour(cell, d) for d in range(N_SLOTS)]
        per_pattern = []
        for pattern in range(1 << N_SLOTS):
            mask = 0
            for d in range(N_SLOTS):
                if pattern >> d & 1 and neighbours[d] != OFF_BOARD:
                    mask |= 1 << neighbours[d]
            per_pattern.append(mask)
        table.append(per_pattern)
    return table


def _patterns_per_position(hand_mask: int) -> list[tuple[int, ...]]:
    """For each position in the sorted hand, its distinct arrow patterns.

    Rotations are deduplicated by the piece's own orbit, exactly as
    ``fliphex.moves.legal_moves`` does — ``P6`` contributes one pattern, not six.
    """
    return [
        tuple(TILES[tile].rotated(r) for r in TILES[tile].distinct_rotations())
        for tile in tiles_in(hand_mask)
    ]


def _subset_ranks(n: int) -> list[int]:
    """``rank[mask]`` for every mask over ``n`` positions.

    A hand has at most 13 tiles, so this is at most 8,192 entries — small enough
    to precompute and turn every spent-set rank into one lookup.
    """
    ranks = []
    for mask in range(1 << n):
        positions = tuple(p for p in range(n) if mask >> p & 1)
        ranks.append(rank_subset(positions))
    return ranks


@dataclass
class PackedSweep:
    """Precomputed tables for one variant, reused across every layer."""

    variant: Variant
    board: Board

    def __post_init__(self) -> None:
        self.n = self.variant.n_cells
        self.flip = _flip_table(self.board)

        purple_hand, green_hand = self.variant.hands()
        first_is_purple = self.variant.first == Colour.PURPLE
        first_hand = purple_hand if first_is_purple else green_hand
        second_hand = green_hand if first_is_purple else purple_hand

        self.patterns = (
            _patterns_per_position(first_hand),
            _patterns_per_position(second_hand),
        )
        self.hand_sizes = (len(self.patterns[0]), len(self.patterns[1]))
        self.spent_ranks = (
            _subset_ranks(self.hand_sizes[0]),
            _subset_ranks(self.hand_sizes[1]),
        )
        self.first_is_purple = first_is_purple

        # `math.comb` was the hot call: `encode` needs one per filled cell, and
        # `encode` runs once per successor. A table turns each into a list index.
        # Rows are one longer than needed so `binom[c][i]` is always in range.
        self.binom = [
            [comb(row, col) for col in range(self.n + 2)] for row in range(self.n + 2)
        ]

    # -- layer arithmetic, all determined by t --------------------------------

    def spent_counts(self, t: int) -> tuple[int, int]:
        return (t + 1) // 2, t // 2

    def mover_is_first(self, t: int) -> bool:
        return t % 2 == 0

    def layer_size(self, t: int) -> int:
        first_spent, second_spent = self.spent_counts(t)
        return (
            comb(self.n, t)
            * 2**t
            * comb(self.hand_sizes[0], first_spent)
            * comb(self.hand_sizes[1], second_spent)
        )

    def encode(self, t: int, occupied: int, purple: int, spent: tuple[int, int]) -> int:
        """Rank a packed configuration. Same index as :class:`LayerIndex`.

        Kept as a method for tests and for the equivalence check; the sweep
        itself inlines this loop with the per-layer radices hoisted, because it
        runs once per successor and the hoisting is worth more than the reuse.
        """
        first_spent, second_spent = self.spent_counts(t)
        cells_rank, colour_bits = self._rank_cells(occupied, purple)
        index = cells_rank * (1 << t) + colour_bits
        index = index * self.binom[self.hand_sizes[0]][first_spent]
        index += self.spent_ranks[0][spent[0]]
        index = index * self.binom[self.hand_sizes[1]][second_spent]
        return index + self.spent_ranks[1][spent[1]]

    def _rank_cells(self, occupied: int, purple: int) -> tuple[int, int]:
        """Colex rank of the filled set, and the colours in that same order."""
        binom = self.binom
        cells_rank = 0
        colour_bits = 0
        position = 0
        remaining = occupied
        while remaining:
            low = remaining & -remaining
            cell = low.bit_length() - 1
            cells_rank += binom[cell][position + 1]
            if purple & low:
                colour_bits |= 1 << position
            position += 1
            remaining ^= low
        return cells_rank, colour_bits

    # -- the sweep ------------------------------------------------------------

    def _layer_configurations(self, t: int):
        """Yield ``(index, occupied, purple, spent_first, spent_second)``.

        Enumerated by iterating combinations rather than by unranking indices:
        the rank of each subset is computed once and then reused across the
        ``2**t`` colourings beneath it, so the expensive part happens
        ``C(n, t)`` times instead of ``layer_size`` times.
        """
        first_spent, second_spent = self.spent_counts(t)
        radix_first = comb(self.hand_sizes[0], first_spent)
        radix_second = comb(self.hand_sizes[1], second_spent)

        spent_first_masks = [
            (self.spent_ranks[0][_mask(positions)], _mask(positions))
            for positions in combinations(range(self.hand_sizes[0]), first_spent)
        ]
        spent_second_masks = [
            (self.spent_ranks[1][_mask(positions)], _mask(positions))
            for positions in combinations(range(self.hand_sizes[1]), second_spent)
        ]

        for filled in combinations(range(self.n), t):
            cells_rank = rank_subset(filled)
            occupied = _mask(filled)
            base_cells = cells_rank * (1 << t)
            for colour_bits in range(1 << t):
                purple = 0
                bits = colour_bits
                while bits:
                    low = bits & -bits
                    purple |= 1 << filled[low.bit_length() - 1]
                    bits ^= low
                base = (base_cells + colour_bits) * radix_first
                for first_rank, first_mask in spent_first_masks:
                    partial = (base + first_rank) * radix_second
                    for second_rank, second_mask in spent_second_masks:
                        yield (
                            partial + second_rank,
                            occupied,
                            purple,
                            first_mask,
                            second_mask,
                        )

    def sweep(self, keep: dict[int, bytearray] | None = None) -> RetrogradeResult:
        """Run the whole sweep, top layer to opening position."""
        stats = SweepStats()
        n = self.n
        full = (1 << n) - 1

        values = bytearray(self.layer_size(n))
        stats.layer_counts[n] = len(values)
        for index, _occupied, purple, _sf, _ss in self._layer_configurations(n):
            purple_count = purple.bit_count()
            green_count = n - purple_count
            if purple_count == green_count:  # adr-010 V2, asserted not sampled
                raise AssertionError(
                    f"tied terminal on a {n}-cell board — adr-011 makes N odd "
                    f"precisely so this cannot happen"
                )
            winner = Colour.PURPLE if purple_count > green_count else Colour.GREEN
            mover = self._mover_colour(n)
            slot = SLOT_WIN if winner == mover else SLOT_LOSS
            values[index] = slot
            if slot == SLOT_WIN:
                stats.terminal_wins += 1
        if keep is not None:
            keep[n] = values

        for t in range(n - 1, -1, -1):
            current = bytearray(self.layer_size(t))
            stats.layer_counts[t] = len(current)
            mover_first = self.mover_is_first(t)
            mover_purple = mover_first == self.first_is_purple
            patterns = self.patterns[0 if mover_first else 1]
            flip = self.flip

            # Radices of the layer above, hoisted: they depend only on t.
            up_first, up_second = self.spent_counts(t + 1)
            up_radix_first = self.binom[self.hand_sizes[0]][up_first]
            up_radix_second = self.binom[self.hand_sizes[1]][up_second]
            up_colour_shift = 1 << (t + 1)
            rank_first, rank_second = self.spent_ranks
            rank_cells = self._rank_cells

            for cfg in self._layer_configurations(t):
                index, occupied, purple, spent_f, spent_s = cfg
                spent = spent_f if mover_first else spent_s
                slot = SLOT_LOSS

                remaining = full & ~occupied
                while remaining and slot == SLOT_LOSS:
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
                            cells_rank, colour_bits = rank_cells(
                                new_occupied, new_purple
                            )
                            child = (
                                cells_rank * up_colour_shift + colour_bits
                            ) * up_radix_first * up_radix_second + tail
                            if values[child] == SLOT_LOSS:
                                slot = SLOT_WIN
                                break
                        if slot == SLOT_WIN:
                            break

                current[index] = slot

            values = current
            if keep is not None:
                keep[t] = values

        opening = values[0]
        if opening == SLOT_UNSET:
            raise AssertionError("the sweep left the opening position unwritten")
        return RetrogradeResult(value=WIN if opening == SLOT_WIN else LOSS, stats=stats)

    def _mover_colour(self, t: int) -> Colour:
        first = self.variant.first
        return first if self.mover_is_first(t) else other(first)


def _mask(positions) -> int:
    mask = 0
    for p in positions:
        mask |= 1 << p
    return mask


def solve(variant: Variant, board: Board | None = None) -> RetrogradeResult:
    """Solve ``variant`` with the packed sweep. See :func:`solver.retrograde.solve`."""
    board = board if board is not None else variant.board()
    return PackedSweep(variant, board).sweep()


def solve_layers(
    variant: Variant, board: Board | None = None
) -> tuple[dict[int, bytearray], RetrogradeResult]:
    """Solve and retain every layer. Memory is one byte per configuration."""
    board = board if board is not None else variant.board()
    tables: dict[int, bytearray] = {}
    result = PackedSweep(variant, board).sweep(keep=tables)
    return tables, result
