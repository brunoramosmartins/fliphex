"""High-level rules: terminal test, score, winner, and zero-sum outcome.

Thin layer over :class:`fliphex.state.GameState`. Scoring is a cell count; the
winner is whoever shows more cells. Because the board has 25 cells (odd), the
counts can never tie — a draw is impossible, and code that produces one is a
bug (docs/rules-canonical.md §7).
"""

from __future__ import annotations

from fliphex.state import Colour, GameState


def score(state: GameState) -> tuple[int, int]:
    """Return ``(purple, green)`` cell counts."""
    return state.score()


def is_terminal(state: GameState) -> bool:
    """Return whether the game is over (board full)."""
    return state.is_terminal()


def winner(state: GameState) -> Colour | None:
    """Return the winning colour, or ``None`` if the game is not over.

    Raises:
        ValueError: If a terminal position is somehow tied (25 is odd, so this
            signals a bug rather than a real outcome).
    """
    if not state.is_terminal():
        return None
    purple, green = state.score()
    if purple == green:
        raise ValueError("tie on a 25-cell board is impossible — engine bug")
    return Colour.PURPLE if purple > green else Colour.GREEN


def margin(state: GameState) -> int:
    """Return the current lead of PURPLE over GREEN (may be negative)."""
    purple, green = state.score()
    return purple - green


def outcome(state: GameState, player: Colour) -> int:
    """Return ``+1`` if ``player`` won, ``-1`` if it lost.

    Raises:
        ValueError: If the game is not over.
    """
    win = winner(state)
    if win is None:
        raise ValueError("outcome is undefined before the game ends")
    return 1 if win == player else -1


__all__ = ["is_terminal", "margin", "outcome", "score", "winner"]
