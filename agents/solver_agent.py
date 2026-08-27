"""Exact agent — plays proved moves, and says so when it cannot.

Two backends, because the project has two kinds of position.

**A solved variant.** Where a completed sweep exists on disk, every move is a
table lookup: pick a child the database calls a loss for the opponent. This is
perfect play by construction and costs microseconds. The 5×3 has such a
database; the 5×5 never will — its largest layer alone is 1.09 × 10¹⁷
configurations, 27.3 PB at two bits.

**Everything else.** The move is proved by forward search instead. There is no
depth limit and no evaluation function in ``solver.minimax`` (adr-004), so a
search either proves the position or proves nothing — it cannot return a
"pretty good" move. That is the right guarantee for a solver and the wrong one
for an agent that must move regardless, so a position beyond the node budget is
delegated to a fallback agent.

Which brings up the number that matters more than the agent
----------------------------------------------------------
An agent named "solver" that quietly plays its fallback in nine positions out of
ten is exactly the instrument defect this project keeps finding: it produces a
plausible result that is read as a fact about the solver. So the split is
counted, not assumed — :attr:`SolverAgent.proved` and
:attr:`SolverAgent.delegated` — and **any result citing this agent must report
them**. On the 5×5, EXP-003 measured a median of 806,474 nodes to prove one
position at ``k = 8`` empty cells and 6,660 at ``k = 6``, so a budget in the low
millions buys the endgame and nothing before it. Expect the split to be lopsided
there, and report it rather than discovering it later.
"""

from __future__ import annotations

import random

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent
from fliphex.board import Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.state import GameState
from solver.minimax import LOSS, BudgetExceededError, Solver
from solver.sweep_reader import SweepReader
from solver.transposition import TranspositionTable


class SolverAgent(Agent):
    """Plays a proved-optimal move, from a database when one exists.

    Args:
        reader: A :class:`~solver.sweep_reader.SweepReader` over a completed
            sweep for this variant. When supplied, every move is proved by
            lookup and ``max_nodes`` is never consulted.
        max_nodes: Node budget per move for the search backend. ``None`` means
            unlimited, which is correct for reduced variants and will hang on
            the 5×5 opening.
        fallback: Agent to consult when a search exceeds its budget. Defaults to
            :class:`~agents.heuristic_agent.HeuristicAgent`.
        tt_bits: Log2 of the transposition table size for the search backend.
            The table is shared across moves, so a game reuses its own work.
        seed: RNG seed, used only to break ties between moves that are equal in
            value.

    Attributes:
        proved: Moves returned from a database lookup or a completed search.
        delegated: Moves returned by ``fallback`` because the search ran out of
            budget. Report this alongside any result.
    """

    name = "solver"

    def __init__(
        self,
        *,
        reader: SweepReader | None = None,
        max_nodes: int | None = None,
        fallback: Agent | None = None,
        tt_bits: int = 22,
        seed: int | None = None,
    ) -> None:
        self.reader = reader
        self.max_nodes = max_nodes
        self.fallback = fallback if fallback is not None else HeuristicAgent(seed=seed)
        self._rng = random.Random(seed)
        self._tt = None if reader is not None else TranspositionTable(1 << tt_bits)
        self.proved = 0
        self.delegated = 0

    # -- backends -------------------------------------------------------------

    def _from_database(self, board: Board, state: GameState) -> Move:
        """Pick a move the database proves winning, else accept the loss.

        In a lost position *every* move loses, so all of them are optimal in the
        game-theoretic sense and one is chosen at random. A stronger practical
        agent would pick the move leaving the opponent fewest winning replies —
        maximising the chance of a mistake — but that is a claim about the
        opponent, not about the game, and this class does not make one.
        """
        losing_for_opponent = []
        for move in legal_moves(board, state):
            child = apply_move(board, state, move)
            if self.reader.value(child) == LOSS:
                losing_for_opponent.append(move)
        if losing_for_opponent:
            return self._rng.choice(losing_for_opponent)
        return self._rng.choice(legal_moves(board, state))

    def _from_search(self, board: Board, state: GameState) -> Move | None:
        """Prove the position, or return ``None`` if the budget ran out."""
        solver = Solver(board, tt=self._tt, max_nodes=self.max_nodes)
        try:
            result = solver.solve(state)
        except BudgetExceededError:
            return None
        return result.best

    # -- Agent ---------------------------------------------------------------

    def select(self, board: Board, state: GameState) -> Move:
        if self.reader is not None:
            self.proved += 1
            return self._from_database(board, state)

        move = self._from_search(board, state)
        if move is None:
            self.delegated += 1
            return self.fallback.select(board, state)
        self.proved += 1
        return move

    # -- reporting -----------------------------------------------------------

    def stats(self) -> dict[str, int | float | str]:
        """Counters for a run record. ``proved_rate`` is the honest headline."""
        total = self.proved + self.delegated
        return {
            "backend": "database" if self.reader is not None else "search",
            "moves": total,
            "proved": self.proved,
            "delegated": self.delegated,
            "proved_rate": self.proved / total if total else 0.0,
            "max_nodes": self.max_nodes,
            "fallback": str(self.fallback),
        }

    def __repr__(self) -> str:
        backend = "database" if self.reader is not None else "search"
        return (
            f"SolverAgent(backend={backend}, max_nodes={self.max_nodes}, "
            f"proved={self.proved}, delegated={self.delegated})"
        )
