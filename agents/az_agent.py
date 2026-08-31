"""The learned agent, and the prior-free floor it has to clear.

Both wrap a PUCT search behind the same interface as the random, heuristic and
solver agents, so the benchmark protocol applies to them unchanged.

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
deterministic functions of the position. Two deterministic agents replay one
game for as many games as you ask for, so a 400-game evaluator gate between them
measures a sample of size one while reporting ``n = 400``.

The default here is therefore *strength*, not variety: the caller must introduce
diversity deliberately. :data:`EVALUATION_TEMPERATURE_PLIES` is the recommended
setting for match play — the opening is sampled from the visit counts, the rest
is greedy — which weakens both sides identically and so leaves the comparison
fair while making the games distinct.
"""

from __future__ import annotations

import random

from agents.base import Agent
from az.mcts import MCTS, ExpansionMode, policy_target
from az.network import FlipHexNet, NetworkEvaluator
from fliphex.board import Board
from fliphex.moves import Move
from fliphex.state import GameState

#: Opening plies to sample rather than take greedily, when two searchers meet in
#: a match. Zero is strongest and identical every game; see the module docstring.
EVALUATION_TEMPERATURE_PLIES = 4


class _SearchAgent(Agent):
    """Shared plumbing: one search per move, seeded per call.

    The tree is not reused across plies. That is the same simplification the
    self-play loop makes, and keeping the two identical means a gate result is
    about the networks rather than about a search difference.
    """

    def __init__(
        self,
        *,
        simulations: int,
        seed: int | None = None,
        temperature_plies: int = 0,
        dirichlet_weight: float = 0.0,
        mode: ExpansionMode = ExpansionMode.POSITION,
    ) -> None:
        self.simulations = simulations
        self.temperature_plies = temperature_plies
        self.dirichlet_weight = dirichlet_weight
        self.mode = mode
        self._rng = random.Random(seed)

    def _hooks(self, board: Board):
        """Return ``(prior, evaluate)`` for the search. ``None`` means default."""
        raise NotImplementedError

    def select(self, board: Board, state: GameState) -> Move:
        prior, evaluate = self._hooks(board)
        search = MCTS(
            board,
            mode=self.mode,
            prior=prior,
            evaluate=evaluate,
            dirichlet_weight=self.dirichlet_weight,
            seed=self._rng.randrange(2**31),
        )
        root = search.run(state, self.simulations)
        pi = policy_target(root, temperature=1.0)

        if state.ply() < self.temperature_plies:
            moves = sorted(pi)
            return self._rng.choices(moves, weights=[pi[m] for m in moves], k=1)[0]
        return max(pi, key=lambda m: (pi[m], m))


class AZAgent(_SearchAgent):
    """PUCT guided by a trained network.

    Args:
        net: The trained network.
        simulations: PUCT simulations per move.
        seed: Seeds the search and any opening sampling.
        temperature_plies: Opening plies sampled from the visit counts. Zero
            plays strongest and identically every game — see the module
            docstring before using zero in a match.
        dirichlet_weight: Root noise. Zero for evaluation; the self-play loop
            supplies its own.
        mode: Child expansion. ``POSITION`` deduplicates aliased actions and is
            the mandated design; the others exist for the aliasing experiment.
    """

    name = "az"

    def __init__(self, net: FlipHexNet, **kwargs) -> None:
        super().__init__(**kwargs)
        self.net = net

    def _hooks(self, board: Board):
        evaluator = NetworkEvaluator(self.net, board)
        return evaluator.prior, evaluator.evaluate

    def __repr__(self) -> str:
        return f"AZAgent(simulations={self.simulations}, mode={self.mode.value})"


class UCTAgent(_SearchAgent):
    """Prior-free UCT with random playouts — the floor with no network in it.

    The learned agent must beat this before any result about it is reported.
    It depends on no training, so it cannot be flattered by a bad one, and its
    playouts are sound here in a way they are not in Go: a playout is at most one
    ply per empty cell, always terminates, and always yields a decided winner
    because a draw is impossible on an odd cell count.

    Args:
        simulations: Simulations per move.
        seed: Seeds the search, the playouts and any opening sampling.
        temperature_plies: As :class:`AZAgent`.
        dirichlet_weight: As :class:`AZAgent`.
        mode: As :class:`AZAgent`. Kept configurable so the floor can be run with
            the same expansion mode as whatever it is measuring.
    """

    name = "uct"

    def _hooks(self, board: Board):
        # None, None gives the search its own defaults: a uniform prior and a
        # random rollout to a decided terminal.
        return None, None

    def __repr__(self) -> str:
        return f"UCTAgent(simulations={self.simulations}, mode={self.mode.value})"
