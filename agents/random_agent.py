"""Uniform-random agent — the strength floor."""

from __future__ import annotations

import random

from agents.base import Agent
from fliphex.board import Board
from fliphex.moves import Move, legal_moves
from fliphex.state import GameState


class RandomAgent(Agent):
    """Plays a move drawn uniformly from the legal moves."""

    name = "random"

    def __init__(self, seed: int | None = None) -> None:
        """Args: seed: RNG seed for reproducible play (``None`` = nondeterministic)."""
        self._rng = random.Random(seed)

    def select(self, board: Board, state: GameState) -> Move:
        return self._rng.choice(legal_moves(board, state))
