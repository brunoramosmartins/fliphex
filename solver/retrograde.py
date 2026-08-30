"""Layer-stratified retrograde solve.

The shape of this module is fixed by
`adr-012 <../docs/adr/adr-012-endgame-database-storage.md>`_, and it is not the
shape the chess/checkers literature would suggest.

**Pull, not push.** Chess and checkers material slices are closed under
successors and contain *cycles*, so that literature propagates from predecessors
with successor counters and iterates to a fixpoint. FLIPHEX layer ``t`` depends
only on layer ``t + 1`` — one sweep, no counters, no iteration. There is a second
reason, sharper than the first: `adr-003 <../docs/adr/adr-003-piece-representation.md>`_
discards tile identity and rotation from the state, so un-placing a tile is not
locally invertible — you would have to guess which arrow pattern caused which
flips. Forward move generation already exists in :mod:`fliphex.moves`, so the
sweep enumerates layer ``t`` and *reads* layer ``t + 1``.

**No symmetry folding.** The Z/2 mirror saves 50% against 8–15× per layer, costs
on every write and every probe, and adr-010 V6 needs an unfolded sample anyway.
The mirror stays a check, not an index transform.

**The index is a mixed-radix rank**, composing exactly the four factors of the
state-space bound: which cells are filled, their colours, which tiles the first
player has spent, which the second has. Side to move and both spent-counts are
*determined* by ``t``, so they are not stored — they are recomputed from it.

That last point is what makes this enumerate the **configuration space** rather
than the reachable closure, which is what the adr-010 Phase 3 amendment requires
of V1: per-layer counts must equal the closed form *exactly*, a genuine ``perft``
with no tolerance. Nothing here imports that closed form — the comparison is only
evidence if the two sides are computed by different means, so it lives in the
tests and in ``scripts/layer_profile.py``.

**Reachability is not needed for correctness.** Backward induction over every
configuration gives correct values on the reachable subset regardless; unreachable
configurations get values that no legal game ever queries. Reachability buys
space, and measuring it is ``EXP-005``'s job, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import comb

from fliphex.board import Board
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import winner
from fliphex.state import Colour, GameState, other, tiles_in
from fliphex.variant import Variant
from solver.minimax import LOSS, WIN

# Slot encoding for a layer's value array. Deliberately NOT the same integers as
# :data:`solver.minimax.WIN` / :data:`~solver.minimax.LOSS`, and deliberately not
# the same names: a bytearray needs an "unwritten" value, so 0 is reserved and
# the two encodings cannot coincide. Two constants called WIN meaning different
# integers in one package is how a solver returns a plausible wrong answer.
# Storage speaks slots; :class:`RetrogradeResult` speaks the project's values.

#: Slot never written. A sweep that leaves one is a bug.
SLOT_UNSET = 0
#: Slot: the side to move at this configuration wins with perfect play.
SLOT_WIN = 1
#: Slot: ...and loses. There is no third outcome — adr-011 keeps ``N`` odd.
SLOT_LOSS = 2


# -- the combinatorial number system ------------------------------------------


def rank_subset(items: tuple[int, ...]) -> int:
    """Rank a strictly increasing tuple in the combinatorial number system.

    ``items`` must be sorted ascending. The rank is ``sum C(items[i], i + 1)``,
    which is a bijection onto ``0 .. C(n, k) - 1`` and — unlike a lexicographic
    rank — does not depend on ``n``. That independence is what lets the same
    routine index cells and hands without carrying their universe sizes around.
    """
    return sum(comb(c, i + 1) for i, c in enumerate(items))


def unrank_subset(rank: int, k: int) -> tuple[int, ...]:
    """Invert :func:`rank_subset` for a ``k``-subset.

    The universe size is not a parameter: the combinatorial number system ranks
    a ``k``-subset independently of ``n``, which is what lets one routine index
    both cells and hands.
    """
    out: list[int] = []
    remaining = rank
    for i in range(k, 0, -1):
        # Largest c with comb(c, i) <= remaining.
        c = i - 1
        while comb(c + 1, i) <= remaining:
            c += 1
        out.append(c)
        remaining -= comb(c, i)
    out.reverse()
    return tuple(out)


# -- one layer ----------------------------------------------------------------


@dataclass(frozen=True)
class LayerIndex:
    """The mixed-radix rank for every configuration with ``t`` cells filled.

    Attributes:
        variant: The game being solved.
        t: Number of filled cells, equal to the ply reached.
    """

    variant: Variant
    t: int

    @property
    def n_cells(self) -> int:
        return self.variant.n_cells

    @property
    def first_spent(self) -> int:
        """Tiles the first player has placed after ``t`` plies."""
        return (self.t + 1) // 2

    @property
    def second_spent(self) -> int:
        return self.t // 2

    @property
    def to_move(self) -> Colour:
        """Determined by ``t``: play strictly alternates from the first player.

        This is why the side to move is not stored in the index — it is a
        function of the layer, not free information about the position.
        """
        first = self.variant.first
        return first if self.t % 2 == 0 else other(first)

    def _hand_tiles(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """The two starting hands as sorted tile-index tuples, first player first."""
        purple, green = self.variant.hands()
        first_mask = purple if self.variant.first == Colour.PURPLE else green
        second_mask = green if self.variant.first == Colour.PURPLE else purple
        return tuple(tiles_in(first_mask)), tuple(tiles_in(second_mask))

    @property
    def size(self) -> int:
        """Configurations in this layer. The closed form, computed structurally.

        Note this is *derived from the enumeration's own radices*, not imported
        from ``scripts/layer_profile.py``. adr-010 V1 compares the two, and a
        comparison between a value and a copy of itself is not evidence.
        """
        first, second = self._hand_tiles()
        return (
            comb(self.n_cells, self.t)
            * 2**self.t
            * comb(len(first), self.first_spent)
            * comb(len(second), self.second_spent)
        )

    def decode(self, index: int) -> GameState:
        """Turn a rank into the configuration it names."""
        first, second = self._hand_tiles()
        n_first, n_second = len(first), len(second)

        radix_second = comb(n_second, self.second_spent)
        index, second_rank = divmod(index, radix_second)
        radix_first = comb(n_first, self.first_spent)
        index, first_rank = divmod(index, radix_first)
        cells_rank, colour_bits = divmod(index, 2**self.t)

        filled = unrank_subset(cells_rank, self.t)
        colours = [Colour.EMPTY] * self.n_cells
        for i, cell in enumerate(filled):
            colours[cell] = Colour.PURPLE if (colour_bits >> i) & 1 else Colour.GREEN

        spent_first = unrank_subset(first_rank, self.first_spent)
        spent_second = unrank_subset(second_rank, self.second_spent)
        hand_first = _mask_without(first, spent_first)
        hand_second = _mask_without(second, spent_second)

        if self.variant.first == Colour.PURPLE:
            hands = (hand_first, hand_second)
        else:
            hands = (hand_second, hand_first)
        return GameState.build(tuple(colours), hands, self.to_move)

    def encode(self, state: GameState) -> int:
        """Turn a configuration into its rank. Inverse of :meth:`decode`."""
        first, second = self._hand_tiles()
        filled = tuple(i for i, c in enumerate(state.colours) if c != Colour.EMPTY)
        colour_bits = sum(
            1 << i
            for i, cell in enumerate(filled)
            if state.colours[cell] == Colour.PURPLE
        )

        purple_hand, green_hand = state.hands
        if self.variant.first == Colour.PURPLE:
            hand_first, hand_second = purple_hand, green_hand
        else:
            hand_first, hand_second = green_hand, purple_hand

        first_rank = rank_subset(_spent_positions(first, hand_first))
        second_rank = rank_subset(_spent_positions(second, hand_second))

        index = rank_subset(filled) * 2**self.t + colour_bits
        index = index * comb(len(first), self.first_spent) + first_rank
        return index * comb(len(second), self.second_spent) + second_rank


def _mask_without(tiles: tuple[int, ...], spent_positions: tuple[int, ...]) -> int:
    """Hand bitmask for ``tiles`` minus the entries at ``spent_positions``."""
    spent = set(spent_positions)
    mask = 0
    for position, tile in enumerate(tiles):
        if position not in spent:
            mask |= 1 << tile
    return mask


def _spent_positions(tiles: tuple[int, ...], hand: int) -> tuple[int, ...]:
    """Positions within ``tiles`` of the tiles no longer in ``hand``."""
    return tuple(p for p, tile in enumerate(tiles) if not (hand >> tile) & 1)


# -- the sweep ----------------------------------------------------------------


@dataclass
class SweepStats:
    """Per-layer evidence, and the provenance an artefact header needs.

    Attributes:
        layer_counts: ``t -> configurations enumerated``. adr-010 V1 compares
            this against the closed form, computed independently.
        terminal_wins: Terminal configurations won by the side to move.
        ordering: Always ``"internal"`` — a retrograde sweep has no move order.
        termination: ``"exhausted"``; a partial sweep raises instead.
    """

    layer_counts: dict[int, int] = field(default_factory=dict)
    terminal_wins: int = 0
    ordering: str = "internal"
    termination: str = "exhausted"

    def as_dict(self) -> dict[str, object]:
        return {
            "layer_counts": dict(sorted(self.layer_counts.items())),
            "terminal_wins": self.terminal_wins,
            "ordering": self.ordering,
            "termination": self.termination,
        }


@dataclass
class RetrogradeResult:
    """The value of the opening position, and the evidence behind it.

    ``value`` is :data:`solver.minimax.WIN` / :data:`~solver.minimax.LOSS`, not a
    slot code, so a retrograde result and a forward result compare directly —
    which is exactly what adr-010 V3 needs to be a plain equality rather than a
    translation the caller could get backwards.
    """

    value: int
    stats: SweepStats

    @property
    def first_player_wins(self) -> bool:
        return self.value == WIN


def solve_layers(
    variant: Variant, board: Board | None = None
) -> tuple[dict[int, bytearray], RetrogradeResult]:
    """Solve, and **retain every layer** rather than only the two in flight.

    :func:`solve` holds two layers at a time, which is the whole point of a
    stratified sweep. This variant keeps all of them, which costs one byte per
    configuration — fine for the 3×3 (711,963 bytes) and out of the question for
    the 5×3 (1.75 × 10¹⁰). It exists because adr-010 **V3** compares the two
    solvers position by position, and that needs the values to still be there
    when the forward search finishes.

    Raises:
        MemoryError: Never explicitly, but a caller reaching for this on a large
            variant will meet one. Use :func:`solve` unless the layers are the
            product you want.
    """
    board = board if board is not None else variant.board()
    tables: dict[int, bytearray] = {}
    result = _sweep(variant, board, keep=tables)
    return tables, result


def solve(variant: Variant, board: Board | None = None) -> RetrogradeResult:
    """Solve ``variant`` exactly by sweeping layers from full board to empty.

    Two layers are resident at a time: the one being written and the one being
    read. That is the whole memory profile — there is no fixpoint to hold open.

    Raises:
        AssertionError: If a terminal configuration is tied. That is adr-010
            **V2** asserted rather than sampled, and on an odd board it cannot
            happen (adr-011).
    """
    board = board if board is not None else variant.board()
    return _sweep(variant, board, keep=None)


def _sweep(
    variant: Variant, board: Board, keep: dict[int, bytearray] | None
) -> RetrogradeResult:
    """The sweep itself. ``keep`` retains every layer when it is a dict."""
    n = variant.n_cells
    stats = SweepStats()

    terminal = LayerIndex(variant, n)
    values = bytearray(terminal.size)
    stats.layer_counts[n] = terminal.size
    for index in range(terminal.size):
        state = terminal.decode(index)
        who = winner(state)  # raises on a tie: adr-010 V2
        slot = SLOT_WIN if who == state.to_move else SLOT_LOSS
        values[index] = slot
        if slot == SLOT_WIN:
            stats.terminal_wins += 1
    if keep is not None:
        keep[n] = values

    for t in range(n - 1, -1, -1):
        layer = LayerIndex(variant, t)
        above = LayerIndex(variant, t + 1)
        current = bytearray(layer.size)
        stats.layer_counts[t] = layer.size

        for index in range(layer.size):
            state = layer.decode(index)
            best = SLOT_LOSS
            for move in legal_moves(board, state):
                child = apply_move(board, state, move)
                if values[above.encode(child)] == SLOT_LOSS:
                    # The opponent loses there, so the mover wins here.
                    best = SLOT_WIN
                    break
            current[index] = best

        values = current
        if keep is not None:
            keep[t] = values

    root = LayerIndex(variant, 0)
    slot = values[root.encode(variant.initial_state())]
    if slot == SLOT_UNSET:
        raise AssertionError("the sweep left the opening position unwritten")
    return RetrogradeResult(value=WIN if slot == SLOT_WIN else LOSS, stats=stats)
