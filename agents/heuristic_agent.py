"""Greedy flip-maximising agent — the baseline every learner must beat."""

from __future__ import annotations

import random

from agents.base import Agent
from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, legal_moves
from fliphex.piece import N_SLOTS
from fliphex.state import TILES, GameState, other


def net_flips(board: Board, state: GameState, move: Move) -> int:
    """Return the net colour swing ``move`` produces for the side to move.

    Flips are toggles (adr-007): an arrow at an opponent tile wins it (+1) but an
    arrow at one of the mover's own tiles hands it over (-1). Empty and off-board
    arrows count 0. A rational greedy maximises this net, not the raw flip count,
    so it does not damage itself.
    """
    mover = state.to_move
    opponent = other(mover)
    rotated = TILES[move.tile].rotated(move.rotation)
    net = 0
    for direction in range(N_SLOTS):
        if not rotated >> direction & 1:
            continue
        target = board.neighbour(move.cell, direction)
        if target == OFF_BOARD:
            continue
        if state.colours[target] == opponent:
            net += 1
        elif state.colours[target] == mover:
            net -= 1
    return net


class HeuristicAgent(Agent):
    """Plays the move with the largest net colour swing this ply; ties random."""

    name = "heuristic"

    def __init__(self, seed: int | None = None) -> None:
        """Args: seed: RNG seed for reproducible tie-breaking."""
        self._rng = random.Random(seed)

    def select(self, board: Board, state: GameState) -> Move:
        moves = legal_moves(board, state)
        best = max(net_flips(board, state, m) for m in moves)
        top = [m for m in moves if net_flips(board, state, m) == best]
        return self._rng.choice(top)
