"""Greedy flip-maximising agent — the baseline every learner must beat."""

from __future__ import annotations

import random

from agents.base import Agent
from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, legal_moves
from fliphex.piece import N_SLOTS
from fliphex.state import TILES, GameState, other


def flips_gained(board: Board, state: GameState, move: Move) -> int:
    """Return how many opponent cells ``move`` would flip.

    Counts arrow-hit neighbours currently the opponent's colour. Own-colour and
    empty neighbours are not flips (the score swing comes only from opponents).
    """
    opponent = other(state.to_move)
    rotated = TILES[move.tile].rotated(move.rotation)
    count = 0
    for direction in range(N_SLOTS):
        if not rotated >> direction & 1:
            continue
        target = board.neighbour(move.cell, direction)
        if target != OFF_BOARD and state.colours[target] == opponent:
            count += 1
    return count


class HeuristicAgent(Agent):
    """Plays the move flipping the most opponent pieces this ply; ties random."""

    name = "heuristic"

    def __init__(self, seed: int | None = None) -> None:
        """Args: seed: RNG seed for reproducible tie-breaking."""
        self._rng = random.Random(seed)

    def select(self, board: Board, state: GameState) -> Move:
        moves = legal_moves(board, state)
        best = max(flips_gained(board, state, m) for m in moves)
        top = [m for m in moves if flips_gained(board, state, m) == best]
        return self._rng.choice(top)
