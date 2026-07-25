"""The Agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from fliphex.board import Board
from fliphex.moves import Move
from fliphex.state import GameState


class Agent(ABC):
    """Something that chooses a move for the side to move.

    Agents are stateless with respect to the game — everything they need is in
    the ``(board, state)`` pair — so one instance can play many games. Any
    randomness is injected at construction for reproducibility.
    """

    name: str = "agent"

    @abstractmethod
    def select(self, board: Board, state: GameState) -> Move:
        """Return the move to play. ``state`` must be non-terminal."""

    def __str__(self) -> str:
        return self.name
