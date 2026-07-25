"""Move generation and application — the flip rule.

A move is a ``(cell, tile, rotation)`` triple: place ``tile`` from the mover's
hand on an empty ``cell`` at ``rotation``, then fire its arrows once.

The flip rule (docs/rules-canonical.md §4, adr-006): every arrow of the placed
tile that points at an *occupied* neighbour flips that neighbour to the mover's
colour. Flips are unconditional (no bracketing), never chain (depth exactly 1),
and setting a cell already the mover's colour is a harmless no-op. A placed
tile's arrows fire on this ply and never again — which is why the state need not
remember them (adr-003).
"""

from __future__ import annotations

from typing import NamedTuple

from fliphex.board import OFF_BOARD, Board
from fliphex.piece import N_SLOTS
from fliphex.state import TILES, Colour, GameState, tiles_in


class Move(NamedTuple):
    """A move: place ``tile`` on ``cell`` at ``rotation`` (0..5)."""

    cell: int
    tile: int
    rotation: int


def legal_moves(board: Board, state: GameState) -> list[Move]:
    """Return every legal move for the side to move.

    Empty cell x tile in hand x **distinct** rotation. Rotations are
    deduplicated per tile, so a symmetric piece contributes fewer moves (see
    :meth:`fliphex.piece.Piece.distinct_rotations`). On the opening ply this is
    25 x 58 = 1450 moves.
    """
    hand = state.hand(state.to_move)
    moves: list[Move] = []
    for cell in board.cells:
        if state.colours[cell] != Colour.EMPTY:
            continue
        for tile in tiles_in(hand):
            for rotation in TILES[tile].distinct_rotations():
                moves.append(Move(cell, tile, rotation))
    return moves


def apply_move(board: Board, state: GameState, move: Move) -> GameState:
    """Return the state after playing ``move``.

    Placement, then the flip rule, then hand/history/turn bookkeeping. The
    result is a new state; ``state`` is unchanged.
    """
    mover = state.to_move
    cell, tile, rotation = move

    new = state.with_colour(cell, mover)

    rotated = TILES[tile].rotated(rotation)
    for direction in range(N_SLOTS):
        if not rotated >> direction & 1:
            continue
        target = board.neighbour(cell, direction)
        if target != OFF_BOARD and new.colours[target] != Colour.EMPTY:
            new = new.with_colour(target, mover)

    return new.without_tile(mover, tile).with_history(cell, tile, rotation).switched()
