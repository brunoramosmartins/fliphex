"""Exact alpha-beta search.

This module **never returns an approximate value.** It either proves the game
value of a position by searching to the end, or it raises
:class:`BudgetExceededError`. There is no depth limit and no evaluation function,
because a heuristic leaf is exactly what would let an unproven number be cited
as a proof — `adr-004 <../docs/adr/adr-004-solver-approach.md>`_ R1 says a result
counts as evidence only when the run terminated by exhaustion, and making that
structural is stronger than making it a convention. Depth-limited play with a
heuristic belongs in ``agents/``, where a wrong value costs a move.

What is being solved
--------------------
The value is **win/loss for the side to move**, ``+1`` or ``-1``. Never zero:
`adr-011 <../docs/adr/adr-011-reduced-variant-parity.md>`_ keeps every variant's
cell count odd, so a draw is arithmetically impossible and
:func:`fliphex.rules.winner` raises if one appears — that raise *is* adr-010's
V2, asserted rather than sampled.

Note this is a genuine modelling choice and not merely an encoding. Solving for
win/loss answers "who wins with perfect play", which is what H1 and H2 ask.
Solving instead for the final cell *margin* would be a different game: a player
indifferent between winning by one and winning by nine plays differently from one
maximising the margin, and their optimal move sets can diverge. ``margin`` stays
available in :mod:`fliphex.rules` for reporting, and must not be quietly promoted
into the objective.

Search shape
------------
FLIPHEX terminates at a fixed depth: the remaining plies are exactly
``n_cells - ply``, determined by the position rather than chosen by the search.
So there is no iterative deepening to do on the proof path — every node is
searched to the end, and the transposition table's depth test is trivially
satisfied within a layer.

Ordering is internal only (TT move first, then killers). adr-004 R2 forbids
seeding a proof-producing run's ordering from Axis 2; the ``order`` hook exists
for experiments, and anything passed through it makes the run's provenance
``ordering: external``, which :attr:`SearchStats.ordering` records.

Which boards this can actually solve
------------------------------------
The 3×3 (``7.12 × 10⁵`` configurations) is within reach here, and this module is
the forward half of adr-010 **V3** — the same variant solved twice by
fundamentally different methods, forward alpha-beta against a retrograde sweep.
That is what ``EXP-001`` uses it for.

The 5×3 is **not** a target for this module. At ``1.75 × 10¹⁰`` configurations no
transposition table holds the state space and no Python search walks it, and that
is not an optimisation gap — it is adr-004's Phase 3 amendment restated: on that
board the game tree is astronomically larger than the state table, so the 5×3 is
an *enumeration* problem and belongs to the retrograde path. Reaching for
``max_nodes`` and a bigger table there is the wrong instrument, not a slower one.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fliphex.board import Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.rules import winner
from fliphex.state import GameState
from solver.transposition import Flag, TranspositionTable

#: Value of a position for a side to move who wins with perfect play.
WIN = 1
#: ...and for one who loses. There is no third value (adr-011, adr-010 V2).
LOSS = -1

#: A move-ordering hook: given the board, the position, the legal moves and the
#: transposition table's suggestion, return the moves in the order to try.
Orderer = Callable[[Board, GameState, list[Move], Move | None], list[Move]]

#: How many killer moves to remember per ply.
KILLERS_PER_PLY = 2


class BudgetExceededError(RuntimeError):
    """Raised when a search hits its node budget before proving a value.

    Deliberately an exception rather than a partial result. A partial value
    would be indistinguishable from a proved one at the call site, which is the
    failure this axis exists to rule out.
    """


@dataclass
class SearchStats:
    """Everything an artefact header needs about how a value was obtained.

    Attributes:
        nodes: Nodes visited, including transposition-table hits.
        terminals: Terminal positions evaluated.
        cutoffs: Beta cutoffs taken.
        tt_cutoffs: Nodes settled by the table without expanding a move.
        ordering: ``"internal"`` or ``"external"`` (adr-004 R2/R3).
        termination: ``"exhausted"`` or ``"budget"`` (adr-004 R1/R3).
        pruning: Whether beta cutoffs were taken. A run with ``pruning=False``
            is a different instrument, not a slower one — it visits every
            reachable position instead of only those pruning left, which is what
            adr-010 V3's coverage depends on.
    """

    nodes: int = 0
    terminals: int = 0
    cutoffs: int = 0
    tt_cutoffs: int = 0
    ordering: str = "internal"
    termination: str = "exhausted"
    pruning: bool = True

    def as_dict(self) -> dict[str, int | str]:
        """Return the fields, for a JSON artefact header."""
        return {
            "nodes": self.nodes,
            "terminals": self.terminals,
            "cutoffs": self.cutoffs,
            "tt_cutoffs": self.tt_cutoffs,
            "ordering": self.ordering,
            "termination": self.termination,
            "pruning": self.pruning,
        }


@dataclass
class SearchResult:
    """A proved game value, with the evidence of how it was proved.

    Attributes:
        value: :data:`WIN` or :data:`LOSS`, for the side to move at the root.
        best: A move achieving ``value``.
        stats: See :class:`SearchStats`.
    """

    value: int
    best: Move | None
    stats: SearchStats = field(default_factory=SearchStats)

    @property
    def winner_is_side_to_move(self) -> bool:
        """Whether the player to move at the root wins with perfect play."""
        return self.value == WIN


class Solver:
    """Exact alpha-beta over a fixed board.

    Args:
        board: The board to search on.
        tt: A transposition table. One is created if omitted. Keep
            ``verify=True`` for anything that will be cited — see
            :mod:`solver.transposition`.
        order: Optional move-ordering hook. Supplying one marks the run
            ``ordering: external``, which disqualifies it from adr-004 R2's
            proof path unless the hook is itself internal to Axis 1.
        max_nodes: Node budget. ``None`` means unlimited, which is what a proof
            run uses.
        prune: Take beta cutoffs. Turning this off does **not** change any
            value — pruning is a speed decision, never a correctness one — but
            it changes *which positions get visited*, from "those pruning left"
            to "every position reachable from the root". adr-010 V3 compares the
            forward and backward solvers position by position, and a pruned
            search simply has no value to offer for a position it never reached,
            so the coverage of that check is bounded by this flag. The
            transposition table still memoises, so an unpruned run stays
            feasible: it visits each reachable position once, not once per path.

            ``prune=False`` also stops the window from narrowing, so every node
            is searched at ``(LOSS, WIN)``. That is not cosmetic: it is what
            keeps every stored bound **extremal**, and V3 reads the table by
            trusting exactly that. See the comment in :meth:`_negamax`.
    """

    def __init__(
        self,
        board: Board,
        tt: TranspositionTable | None = None,
        order: Orderer | None = None,
        max_nodes: int | None = None,
        prune: bool = True,
    ) -> None:
        self.board = board
        self.tt = tt if tt is not None else TranspositionTable()
        self.order = order
        self.max_nodes = max_nodes
        self.prune = prune
        self.stats = SearchStats(
            ordering="internal" if order is None else "external", pruning=prune
        )
        self._killers: list[list[Move]] = [[] for _ in range(board.n_cells + 1)]

    # -- public ---------------------------------------------------------------

    def solve(self, state: GameState) -> SearchResult:
        """Prove the value of ``state``.

        Returns:
            A :class:`SearchResult` whose ``value`` is the true game value for
            the side to move.

        Raises:
            BudgetExceededError: If ``max_nodes`` was reached first. Nothing
                partial is returned.
        """
        self.stats = SearchStats(
            ordering="internal" if self.order is None else "external",
            pruning=self.prune,
        )
        self._killers = [[] for _ in range(self.board.n_cells + 1)]
        try:
            value = self._negamax(state, LOSS, WIN)
        except BudgetExceededError:
            self.stats.termination = "budget"
            raise
        _, best = self.tt.probe(state, self._depth(state), LOSS, WIN)
        return SearchResult(value=value, best=best, stats=self.stats)

    def principal_variation(self, state: GameState) -> list[Move]:
        """Walk the table's best moves from ``state`` to a terminal position.

        This is the input to the principal-variation audit that ``EXP-002``
        registers: adr-010 V4 bounds the *rate* of errors in a database, while
        the reported number is a single root value, and only re-deriving the PV
        independently targets that number.

        The walk stops early if the table has no move for a position — entries
        can be overwritten by the replacement policy, so a short PV is a fact
        about the table, not about the position.
        """
        line: list[Move] = []
        current = state
        while not current.is_terminal():
            _, best = self.tt.probe(current, self._depth(current), LOSS, WIN)
            if best is None:
                break
            line.append(best)
            current = apply_move(self.board, current, best)
        return line

    # -- search ---------------------------------------------------------------

    def _depth(self, state: GameState) -> int:
        """Plies remaining below ``state``. Determined by the position."""
        return state.n_cells - state.ply()

    def _negamax(self, state: GameState, alpha: int, beta: int) -> int:
        self.stats.nodes += 1
        if self.max_nodes is not None and self.stats.nodes > self.max_nodes:
            raise BudgetExceededError(
                f"node budget {self.max_nodes} reached without proving a value"
            )

        if state.is_terminal():
            self.stats.terminals += 1
            # winner() raises on a tie, which is adr-010 V2 asserted rather
            # than sampled: an odd cell count makes a tie impossible.
            return WIN if winner(state) == state.to_move else LOSS

        depth = self._depth(state)
        original_alpha = alpha
        value, tt_move = self.tt.probe(state, depth, alpha, beta)
        if value is not None:
            self.stats.tt_cutoffs += 1
            return value

        moves = self._ordered(state, tt_move)
        best_value = LOSS - 1
        best_move: Move | None = None

        for move in moves:
            child = apply_move(self.board, state, move)
            if self.prune:
                score = -self._negamax(child, -beta, -alpha)
            else:
                # Not pruning means not narrowing either. Disabling only the
                # cutoff while still passing `(-beta, -alpha)` is the worst of
                # both: once alpha reaches WIN the remaining children are
                # searched at `alpha == beta`, and a node entered with
                # `alpha = WIN` whose value is WIN is flagged UPPER — an upper
                # bound on the maximum, which says nothing. EXP-001's V3 then
                # has to discard those entries, which is exactly what it did.
                score = -self._negamax(child, LOSS, WIN)
            if score > best_value:
                best_value, best_move = score, move
            if best_value > alpha:
                alpha = best_value
            if self.prune and alpha >= beta:
                self.stats.cutoffs += 1
                self._remember_killer(state, move)
                break

        self.tt.store(
            state,
            best_value,
            self._flag(best_value, original_alpha, beta),
            depth,
            best_move,
            exhaustive=True,
        )
        return best_value

    @staticmethod
    def _flag(value: int, alpha: int, beta: int) -> Flag:
        """Classify a returned score against the window it was searched in."""
        if value <= alpha:
            return Flag.UPPER
        if value >= beta:
            return Flag.LOWER
        return Flag.EXACT

    # -- ordering -------------------------------------------------------------

    def _ordered(self, state: GameState, tt_move: Move | None) -> list[Move]:
        moves = legal_moves(self.board, state)
        if not moves:
            raise AssertionError(
                "a non-terminal FLIPHEX position always has a legal move: hands "
                "are exactly exhausted (adr-011), so the mover holds a tile and "
                "every empty cell accepts one"
            )
        if self.order is not None:
            return self.order(self.board, state, moves, tt_move)

        head: list[Move] = []
        if tt_move is not None and tt_move in moves:
            head.append(tt_move)
        for killer in self._killers[state.ply()]:
            if killer in moves and killer not in head:
                head.append(killer)
        if not head:
            return moves
        rest = [m for m in moves if m not in head]
        return head + rest

    def _remember_killer(self, state: GameState, move: Move) -> None:
        slot = self._killers[state.ply()]
        if move in slot:
            return
        slot.insert(0, move)
        del slot[KILLERS_PER_PLY:]


def solve(
    board: Board,
    state: GameState,
    tt: TranspositionTable | None = None,
    max_nodes: int | None = None,
) -> SearchResult:
    """Prove the value of ``state`` with a fresh solver. See :class:`Solver`."""
    return Solver(board, tt=tt, max_nodes=max_nodes).solve(state)
