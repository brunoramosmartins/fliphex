"""Choosing a move with a search — the part that belongs to the axis, not to the
agent wrapper.

``agents/az_agent.py`` is a thin adapter onto these, and the evaluator gate uses
them directly. Putting the logic here is what keeps the dependency edge in one
direction: ``agents`` may import ``az``, and ``az`` must never import ``agents``.
Writing the gate against ``AZAgent`` closed that loop, and Python would have
tolerated it only for as long as the import order happened to work out.

Evaluation determinism
----------------------
At ``temperature_plies=0`` a player is a **pure function of the position**. Two
of them replay one game for as many games as they are asked to play, so a
400-game match between them reports ``n = 400`` on an effective sample of one,
and produces a win rate of 0% or 100% — which reads as a decisive result rather
than a broken measurement. Sampling the opening from the visit counts weakens
both sides identically and makes the games genuinely distinct.
"""

from __future__ import annotations

import random

from az.mcts import MCTS, ExpansionMode, policy_target
from az.network import FlipHexNet, NetworkEvaluator
from fliphex.board import Board
from fliphex.moves import Move
from fliphex.state import GameState

#: Opening plies to sample rather than take greedily when two searchers meet.
EVALUATION_TEMPERATURE_PLIES = 4


class SearchPlayer:
    """PUCT move selection. One search per move; the tree is not reused.

    Not reusing the tree is the same simplification the self-play loop makes, and
    keeping the two identical means a gate result is about the networks rather
    than about a search difference.

    Args:
        net: The network guiding the search, or ``None`` for the prior-free
            floor — uniform priors and random rollouts, which depends on no
            training and so cannot be flattered by a bad run.
        simulations: PUCT simulations per move.
        seed: Seeds the search, the rollouts, and any opening sampling.
        temperature_plies: Opening plies sampled from the visit counts. Zero
            plays strongest and identically every game.
        dirichlet_weight: Root noise. Zero for evaluation; self-play supplies
            its own.
        mode: Child expansion. ``POSITION`` deduplicates aliased actions and is
            the mandated design.
    """

    def __init__(
        self,
        net: FlipHexNet | None = None,
        *,
        simulations: int,
        seed: int | None = None,
        temperature_plies: int = 0,
        dirichlet_weight: float = 0.0,
        mode: ExpansionMode = ExpansionMode.POSITION,
    ) -> None:
        self.net = net
        self.simulations = simulations
        self.temperature_plies = temperature_plies
        self.dirichlet_weight = dirichlet_weight
        self.mode = mode
        self._rng = random.Random(seed)

    def select(self, board: Board, state: GameState) -> Move:
        """Return the move to play. ``state`` must be non-terminal."""
        prior = evaluate = None
        if self.net is not None:
            evaluator = NetworkEvaluator(self.net, board)
            prior, evaluate = evaluator.prior, evaluator.evaluate

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

    def __repr__(self) -> str:
        kind = "network" if self.net is not None else "uct"
        return f"SearchPlayer({kind}, simulations={self.simulations})"
