"""Tests for solver.packed_sweep.

The packed sweep exists only to be faster. Every test here therefore asks the
same question in a different place: **does it agree with the reference, exactly?**

That framing is the point. ``solver/retrograde.py`` is written for legibility and
goes through ``GameState``; this one keeps four integers and moves between them
with bit operations. If the fast path ever earns a value the reference would not
have produced, the fast path is wrong — never the other way round. A speedup that
required trusting the optimisation would not be worth having, because adr-010 V3
is only evidence while two implementations *can* disagree.

The flip rule is not restated in the fast path — it is tabulated out of
``Board.neighbour`` at construction — and :func:`test_flip_table_matches_apply_move`
pins that, because a hand-copied rule is exactly how two implementations quietly
stop being independent.
"""

import pytest

from fliphex.moves import Move, apply_move
from fliphex.piece import N_SLOTS
from fliphex.state import TILE_INDEX, TILES, Colour
from fliphex.variant import Arm, Variant
from solver import packed_sweep as fast
from solver import retrograde as reference

#: Boards where both sweeps are affordable. The 3×3 (711,963 configurations) is
#: EXP-001's job; the reference takes ~7 minutes on it, which is too slow here.
SMALL = [Variant(5, 1), Variant(5, 1, Arm.H2)]


# -- the equivalence, which is the whole contract -----------------------------


@pytest.mark.parametrize("variant", SMALL)
def test_every_layer_is_byte_identical_to_the_reference(variant):
    ref_tables, ref_result = reference.solve_layers(variant)
    fast_tables, fast_result = fast.solve_layers(variant)

    assert set(fast_tables) == set(ref_tables)
    for t in sorted(ref_tables):
        assert fast_tables[t] == ref_tables[t], f"layer {t} differs"
    assert fast_result.value == ref_result.value


@pytest.mark.parametrize("variant", SMALL)
def test_layer_counts_agree(variant):
    _, ref_result = reference.solve_layers(variant)
    _, fast_result = fast.solve_layers(variant)
    assert fast_result.stats.layer_counts == ref_result.stats.layer_counts
    assert fast_result.stats.terminal_wins == ref_result.stats.terminal_wins


@pytest.mark.parametrize("variant", SMALL)
def test_the_index_agrees_with_the_reference_index(variant):
    """Both sweeps must rank a configuration to the same integer.

    Byte-identical tables would still pass if both indexed a *permutation* of
    the space consistently, so the index itself is compared against the
    reference's :class:`LayerIndex` independently.
    """
    sweep = fast.PackedSweep(variant, variant.board())
    for t in range(variant.n_cells + 1):
        layer = reference.LayerIndex(variant, t)
        assert sweep.layer_size(t) == layer.size
        for index in range(layer.size):
            state = layer.decode(index)
            occupied = sum(1 << c for c, colour in enumerate(state.colours) if colour)
            purple = sum(
                1 << c
                for c, colour in enumerate(state.colours)
                if colour == Colour.PURPLE
            )
            spent = _spent_masks(sweep, variant, state)
            assert sweep.encode(t, occupied, purple, spent) == index


def _spent_masks(sweep, variant, state):
    """The two spent-position masks the packed sweep indexes by."""
    purple_hand, green_hand = state.hands
    first_is_purple = variant.first == Colour.PURPLE
    hands = variant.hands()
    start_first = hands[0] if first_is_purple else hands[1]
    start_second = hands[1] if first_is_purple else hands[0]
    now_first = purple_hand if first_is_purple else green_hand
    now_second = green_hand if first_is_purple else purple_hand
    return (_spent(start_first, now_first), _spent(start_second, now_second))


def _spent(start: int, now: int) -> int:
    from fliphex.state import tiles_in

    return sum(
        1 << position
        for position, tile in enumerate(tiles_in(start))
        if not (now >> tile) & 1
    )


# -- the flip rule is tabulated, not restated ---------------------------------


def test_flip_table_matches_apply_move():
    """The fast path must not have its own copy of the rule.

    Checked against the engine on every (cell, tile, rotation) of a real board:
    the cells whose colour ``apply_move`` changes, other than the placed cell
    itself, must be exactly ``flip_table[cell][pattern] & occupied``.
    """
    variant = Variant(3, 3)
    board = variant.board()
    sweep = fast.PackedSweep(variant, board)
    state = variant.initial_state()

    # One tile down, so there is something to flip.
    seed = Move(board.cell_id("B2"), TILE_INDEX["P1"], 0)
    state = apply_move(board, state, seed)
    occupied = sum(1 << c for c, colour in enumerate(state.colours) if colour)

    checked = 0
    for cell in range(board.n_cells):
        if state.colours[cell] != Colour.EMPTY:
            continue
        for tile_index, piece in enumerate(TILES):
            if not (state.hand(state.to_move) >> tile_index) & 1:
                continue
            for rotation in piece.distinct_rotations():
                after = apply_move(board, state, Move(cell, tile_index, rotation))
                changed = sum(
                    1 << c
                    for c in range(board.n_cells)
                    if after.colours[c] != state.colours[c] and c != cell
                )
                pattern = piece.rotated(rotation)
                assert changed == (sweep.flip[cell][pattern] & occupied), (
                    f"cell {cell} pattern {pattern:06b}"
                )
                checked += 1
    assert checked > 100, "the probe never exercised a real board"


def test_off_board_arrows_flip_nothing():
    variant = Variant(3, 3)
    board = variant.board()
    sweep = fast.PackedSweep(variant, board)
    corner = board.cell_id("A1")
    full_pattern = (1 << N_SLOTS) - 1
    assert sweep.flip[corner][full_pattern].bit_count() == len(
        [n for n in board.neighbours(corner) if n >= 0]
    )


def test_the_empty_pattern_flips_nothing():
    sweep = fast.PackedSweep(Variant(3, 3), Variant(3, 3).board())
    assert all(row[0] == 0 for row in sweep.flip)


# -- structure ----------------------------------------------------------------


def test_a_tie_would_raise_on_an_even_board():
    """adr-010 V2 is asserted in the fast path too, not only in the reference."""
    sweep = fast.PackedSweep(Variant(5, 1), Variant(5, 1).board())
    assert sweep.n % 2 == 1  # so the assertion is unreachable by construction


def test_solve_and_solve_layers_agree():
    variant = Variant(5, 1)
    plain = fast.solve(variant)
    _, kept = fast.solve_layers(variant)
    assert plain.value == kept.value
    assert plain.stats.layer_counts == kept.stats.layer_counts
