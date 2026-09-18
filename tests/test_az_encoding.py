"""Tests for ``az/encoding.py``.

The one that matters most is
:func:`test_the_opponents_joker_is_visible_when_the_second_player_moves`. The
architecture record specifies 29 planes, splitting the hands 13 own / 12
opponent. Under an encoding written from the mover's point of view that is one
plane short: on every second ply the opponent *is* the first player, and the
first player is the one holding the joker. This file pins the repair so that a
later "simplification" back to 12 fails loudly instead of quietly hiding the
tile that decides who moves last.
"""

from __future__ import annotations

import pytest

from az.encoding import (
    EMPTY_PLANE,
    N_HAND_PLANES,
    N_PLANES,
    OPPONENT_COLOUR_PLANE,
    OPPONENT_HAND_PLANE,
    OWN_COLOUR_PLANE,
    OWN_HAND_PLANE,
    SIDE_TO_MOVE_PLANE,
    encode,
    plane_names,
)
from fliphex.moves import apply_move, legal_moves
from fliphex.state import JOKER_INDEX, Colour, other
from fliphex.variant import Arm, Variant

FULL = Variant(5, 5, Arm("h1"))
SMALL = Variant(5, 3, Arm("h2"))
TINY = Variant(3, 3, Arm("h1"))
VARIANTS = [FULL, SMALL, TINY]


def plane(buffer: bytes, index: int, n_cells: int) -> bytes:
    return buffer[index * n_cells : (index + 1) * n_cells]


def advance(variant: Variant, plies: int, *, avoid_tile: int | None = None):
    """Play ``plies`` deterministic moves, optionally never playing one tile."""
    board, state = variant.board(), variant.initial_state()
    for _ in range(plies):
        moves = legal_moves(board, state)
        if avoid_tile is not None:
            moves = [m for m in moves if m.tile != avoid_tile] or moves
        state = apply_move(board, state, moves[0])
    return board, state


# -- shape and partition ------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS)
def test_the_buffer_is_one_byte_per_plane_per_cell(variant):
    board, state = variant.board(), variant.initial_state()

    buffer = encode(board, state)

    assert len(buffer) == N_PLANES * board.n_cells
    assert set(buffer) <= {0, 1}


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("plies", [0, 1, 4, 7])
def test_every_cell_is_in_exactly_one_of_own_opponent_empty(variant, plies):
    """The three board planes partition the board — no cell in two, none in none."""
    board, state = advance(variant, plies)
    n_cells = board.n_cells

    buffer = encode(board, state)
    own = plane(buffer, OWN_COLOUR_PLANE, n_cells)
    opponent = plane(buffer, OPPONENT_COLOUR_PLANE, n_cells)
    empty = plane(buffer, EMPTY_PLANE, n_cells)

    for cell in range(n_cells):
        assert own[cell] + opponent[cell] + empty[cell] == 1


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("plies", [0, 3])
def test_the_board_planes_are_read_from_the_movers_side(variant, plies):
    board, state = advance(variant, plies)
    n_cells = board.n_cells

    buffer = encode(board, state)
    own = plane(buffer, OWN_COLOUR_PLANE, n_cells)
    opponent = plane(buffer, OPPONENT_COLOUR_PLANE, n_cells)

    for cell in range(n_cells):
        assert own[cell] == (state.colours[cell] == state.to_move)
        assert opponent[cell] == (state.colours[cell] == other(state.to_move))


def test_one_ply_swaps_own_and_opponent():
    """The same board seen by the other player exchanges the two colour planes."""
    board, state = FULL.board(), FULL.initial_state()
    move = legal_moves(board, state)[0]
    after = apply_move(board, state, move)
    n_cells = board.n_cells

    buffer = encode(board, after)

    # The mover has just changed, so the tile placed by the previous mover is
    # now on the *opponent* plane -- unless a flip took it, which cannot happen
    # on the opening ply because there is nothing adjacent to flip.
    assert plane(buffer, OPPONENT_COLOUR_PLANE, n_cells)[move.cell] == 1
    assert plane(buffer, OWN_COLOUR_PLANE, n_cells)[move.cell] == 0


# -- constant planes ----------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS)
def test_the_side_to_move_plane_is_constant_and_marks_the_first_player(variant):
    board, state = variant.board(), variant.initial_state()
    n_cells = board.n_cells

    first = encode(board, state)
    second = encode(board, advance(variant, 1)[1])

    assert plane(first, SIDE_TO_MOVE_PLANE, n_cells) == b"\x01" * n_cells
    assert plane(second, SIDE_TO_MOVE_PLANE, n_cells) == b"\x00" * n_cells


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("plies", [0, 2, 5])
def test_hand_planes_reproduce_the_hand_bitmasks(variant, plies):
    board, state = advance(variant, plies)
    n_cells = board.n_cells
    buffer = encode(board, state)

    for offset, colour in (
        (OWN_HAND_PLANE, state.to_move),
        (OPPONENT_HAND_PLANE, other(state.to_move)),
    ):
        hand = state.hand(colour)
        for tile in range(N_HAND_PLANES):
            expected = b"\x01" * n_cells if hand >> tile & 1 else b"\x00" * n_cells
            assert plane(buffer, offset + tile, n_cells) == expected


# -- the reason there are 30 planes and not 29 --------------------------------


def test_the_opponents_joker_is_visible_when_the_second_player_moves():
    """The regression test for the 29-plane table.

    A 12-plane opponent block has room for the twelve archetypes and nowhere to
    put the joker. The joker is the first player's thirteenth tile and the whole
    reason they get the last ply, so on every second ply the specified encoding
    would hide exactly the tile that decides the parity of the game.
    """
    board, state = advance(FULL, 1, avoid_tile=JOKER_INDEX)
    n_cells = board.n_cells

    assert state.to_move == Colour.GREEN
    assert state.hand(Colour.PURPLE) >> JOKER_INDEX & 1, "P1 must still hold it"

    buffer = encode(board, state)
    joker_plane = plane(buffer, OPPONENT_HAND_PLANE + JOKER_INDEX, n_cells)

    assert joker_plane == b"\x01" * n_cells
    assert OPPONENT_HAND_PLANE + JOKER_INDEX < N_PLANES


def test_spending_the_joker_clears_its_plane():
    """The plane tracks the tile, not the seat."""
    board, state = FULL.board(), FULL.initial_state()
    joker_move = next(m for m in legal_moves(board, state) if m.tile == JOKER_INDEX)
    after = apply_move(board, state, joker_move)
    n_cells = board.n_cells

    buffer = encode(board, after)

    assert (
        plane(buffer, OPPONENT_HAND_PLANE + JOKER_INDEX, n_cells) == b"\x00" * n_cells
    )


def test_only_the_first_player_ever_shows_a_joker_plane():
    """Both hand blocks are 13 wide; the second player's joker plane stays 0."""
    board, state = FULL.board(), FULL.initial_state()
    n_cells = board.n_cells

    buffer = encode(board, state)

    assert plane(buffer, OWN_HAND_PLANE + JOKER_INDEX, n_cells) == b"\x01" * n_cells
    assert (
        plane(buffer, OPPONENT_HAND_PLANE + JOKER_INDEX, n_cells) == b"\x00" * n_cells
    )


# -- layout is variant-independent --------------------------------------------


def test_the_plane_layout_does_not_depend_on_the_variant():
    """Only the spatial size changes across the comparison set."""
    buffers = {v.name: encode(v.board(), v.initial_state()) for v in VARIANTS}

    for variant in VARIANTS:
        assert len(buffers[variant.name]) == N_PLANES * variant.n_cells

    assert len(plane_names()) == N_PLANES
    assert plane_names()[OPPONENT_HAND_PLANE + JOKER_INDEX] == "opponent hand: JOKER"


def test_there_are_no_orientation_planes():
    """Placed tiles are inert, so rotation is not part of the state.

    Two games reaching the same colours, hands and mover must encode
    identically even when the tiles were placed at different rotations.
    """
    board, state = FULL.board(), FULL.initial_state()

    groups: dict[tuple[int, int], list] = {}
    for move in legal_moves(board, state):
        groups.setdefault((move.cell, move.tile), []).append(move)
    rotatable = [g for g in groups.values() if len(g) > 1]
    assert rotatable, "the fixture needs a tile whose rotation orbit exceeds 1"

    for group in rotatable:
        encodings = {encode(board, apply_move(board, state, m)) for m in group}
        assert len(encodings) == 1
