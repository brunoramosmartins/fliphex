"""The learned agent, and the prior-free floor it has to clear.

Both are thin adapters onto :class:`az.player.SearchPlayer`, which holds the move
selection itself. The split is a layering one: ``agents`` may import ``az``, and
``az`` must never import ``agents``. The evaluator gate lives in ``az`` and needs
to play matches, so the logic has to sit below this file rather than in it.

Not exported from ``agents/__init__.py``, on purpose
---------------------------------------------------
Importing any submodule of a package runs that package's ``__init__``. Listing
:class:`AZAgent` there would make ``from agents.random_agent import RandomAgent``
load torch — a second or two on every import, and an outright failure under the
faster interpreter the exact-solver runs use, which has no torch build. Import
this module directly instead::

    from agents.az_agent import AZAgent, UCTAgent

Evaluation determinism
----------------------
At ``temperature_plies=0`` and ``dirichlet_weight=0`` these agents are
deterministic functions of the position, and two of them replay one game. See
:mod:`az.player` and :mod:`az.gate`; the default here is *strength*, so a caller
running a match has to ask for diversity deliberately.
"""

from __future__ import annotations

from agents.base import Agent
from az.mcts import ExpansionMode
from az.network import FlipHexNet
from az.player import EVALUATION_TEMPERATURE_PLIES, SearchPlayer
from fliphex.board import Board
from fliphex.moves import Move
from fliphex.state import GameState

__all__ = ["EVALUATION_TEMPERATURE_PLIES", "AZAgent", "UCTAgent"]


class _PlayerAgent(Agent):
    """Adapter: an :class:`Agent` backed by a :class:`SearchPlayer`."""

    def __init__(self, player: SearchPlayer) -> None:
        self.player = player

    @property
    def simulations(self) -> int:
        return self.player.simulations

    @property
    def mode(self) -> ExpansionMode:
        return self.player.mode

    def select(self, board: Board, state: GameState) -> Move:
        return self.player.select(board, state)


class AZAgent(_PlayerAgent):
    """PUCT guided by a trained network.

    Args:
        net: The trained network.
        simulations: PUCT simulations per move.
        seed: Seeds the search and any opening sampling.
        temperature_plies: Opening plies sampled from the visit counts. Zero
            plays strongest and identically every game — read the module
            docstring before using zero in a match.
        dirichlet_weight: Root noise. Zero for evaluation.
        mode: Child expansion; ``POSITION`` is the mandated design.
    """

    name = "az"

    def __init__(self, net: FlipHexNet, **kwargs) -> None:
        super().__init__(SearchPlayer(net, **kwargs))

    def __repr__(self) -> str:
        return f"AZAgent(simulations={self.simulations}, mode={self.mode.value})"


class UCTAgent(_PlayerAgent):
    """Prior-free UCT with random playouts — the floor with no network in it.

    The learned agent must beat this before any result about it is reported. It
    depends on no training, so a bad run cannot flatter it, and its playouts are
    sound in a way they are not in Go: a playout is at most one ply per empty
    cell, always terminates, and always yields a decided winner because a draw is
    impossible on an odd cell count.
    """

    name = "uct"

    def __init__(self, **kwargs) -> None:
        super().__init__(SearchPlayer(None, **kwargs))

    def __repr__(self) -> str:
        return f"UCTAgent(simulations={self.simulations}, mode={self.mode.value})"
