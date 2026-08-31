"""PUCT MCTS over the real state, with three child-expansion modes.

adr-001 makes this plain perfect-information MCTS: no determinization, no
information sets. adr-005 fixes PUCT over UCB1, Dirichlet noise at the root, and
temperature 1 for the opening plies then greedy.

The three modes exist because of R13
------------------------------------
1,450 root actions on the 5x5 reach only **325** distinct positions — 4.46x, and
2.28x over a whole game (``scripts/measure_move_collapse.py``). Expanding
aliased actions as separate children does two things at once, and both point the
same way: it **splits** one position's visit counts across up to six labels, and
it **gives each label its own prior**, so a position reachable by six rotations
collects roughly six times the prior mass of one reachable by a single rotation.
The training target is then read off those split counts.

The adr-005 Phase 3 amendment makes :data:`ExpansionMode.POSITION` mandatory.
The other two modes are not alternatives — they are EXP-010's controls, and they
exist so the benefit can be attributed:

===================  =====================  ==========================
mode                 children indexed by    isolates
===================  =====================  ==========================
``ACTION``           action                 the deployed-naive baseline
``POSITION``         resulting position     the ADR's design
``MULTIPLICITY``     action                 prior mass alone
===================  =====================  ==========================

``MULTIPLICITY`` keeps every action as its own child but divides each prior by
its alias multiplicity. Without it, a win for ``POSITION`` at a small simulation
budget is fully explained by *"it has ~4x fewer children and can finish one pass
over them"* — an effect you would also get by deleting three quarters of
``ACTION``'s children at random, which is not the ADR's mechanism.

Aliasing is decided without applying the move
---------------------------------------------
Two rotations of one tile on one cell reach the same position exactly when their
arrows meet the *occupied* neighbours identically — placed tiles are inert
(adr-003) and flips never chain (adr-006), so nothing else can differ. The class
key is therefore ``(cell, tile, rotated_mask & occupied_neighbour_mask)``, an
integer AND per move rather than a full ``apply_move``. This matters: at the
5x5 root, grouping by applying all 1,450 moves would cost more than the search.

This module is deliberately network-free
----------------------------------------
``prior`` and ``evaluate`` are injected. EXP-010 runs with a uniform prior and
random-rollout leaves — which makes the searcher plain UCT, adr-005's own
designated baseline — so that the measured difference between modes is a fact
about the *tree* and not about some network's quality.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from random import Random

from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.piece import N_SLOTS
from fliphex.rules import is_terminal, outcome
from fliphex.state import TILES, Colour, GameState

#: Value of a leaf, from the point of view of ``state.to_move``, in [-1, 1].
Evaluator = Callable[[Board, GameState], float]

#: Prior over a position's legal moves, from the point of view of the mover.
#: Returns one weight per move in the order given; need not be normalised.
PriorFn = Callable[[Board, GameState, list[Move]], list[float]]


class ExpansionMode(StrEnum):
    """How a node's children are indexed. See the module docstring."""

    ACTION = "action"
    POSITION = "position"
    MULTIPLICITY = "multiplicity"


def occupied_arrow_key(board: Board, state: GameState, move: Move) -> int:
    """Return the subset of ``move``'s arrows that point at occupied cells.

    This is the only part of a rotation that can affect the resulting position.
    An arrow at an empty neighbour — or off the board — fires into nothing, so
    every rotation whose arrows agree *here* lands the tile inert in the same
    way and produces the same board.
    """
    rotated = TILES[move.tile].rotated(move.rotation)
    key = 0
    for direction in range(N_SLOTS):
        if not rotated >> direction & 1:
            continue
        target = board.neighbour(move.cell, direction)
        if target != OFF_BOARD and state.colours[target] != Colour.EMPTY:
            key |= 1 << direction
    return key


def group_by_position(
    board: Board, state: GameState, moves: list[Move]
) -> list[list[Move]]:
    """Partition ``moves`` into classes that reach the same position.

    Order is deterministic — classes appear in the order their first member
    appears in ``moves`` — so a fixed seed pins the child ordering, which PUCT's
    tie-breaking reads at low visit counts.
    """
    classes: dict[tuple[int, int, int], list[Move]] = {}
    for move in moves:
        key = (move.cell, move.tile, occupied_arrow_key(board, state, move))
        classes.setdefault(key, []).append(move)
    return list(classes.values())


@dataclass(slots=True)
class Node:
    """One node. ``value_sum`` is accumulated from the mover's point of view."""

    prior: float
    move: Move | None = None
    #: How many aliased actions this child stands for. 1 in every mode but
    #: POSITION, where it is the class size and is what ``visit_counts`` needs
    #: to hand a comparable ``pi`` back to the caller.
    multiplicity: int = 1
    visits: int = 0
    value_sum: float = 0.0
    children: list[Node] = field(default_factory=list)
    expanded: bool = False

    @property
    def q(self) -> float:
        """Mean value, or 0 for an unvisited node (adr-005's PUCT convention)."""
        return self.value_sum / self.visits if self.visits else 0.0


class MCTS:
    """PUCT search. One instance per move; the tree is not reused across plies.

    Not reusing the tree is a deliberate simplification for v1: subtree reuse
    interacts with Dirichlet noise and with the temperature schedule in ways
    that are worth measuring separately, and EXP-010 compares expansion modes at
    a fixed budget where reuse would confound the comparison.
    """

    def __init__(
        self,
        board: Board,
        *,
        mode: ExpansionMode = ExpansionMode.POSITION,
        evaluate: Evaluator | None = None,
        prior: PriorFn | None = None,
        c_puct: float = 1.5,
        dirichlet_alpha: float = 0.3,
        dirichlet_weight: float = 0.0,
        seed: int = 0,
    ) -> None:
        self.board = board
        self.mode = mode
        self.c_puct = c_puct
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_weight = dirichlet_weight
        self.rng = Random(seed)
        self.evaluate = evaluate or self.rollout
        self.prior = prior or uniform_prior
        #: Counters EXP-010 reports as tree cost.
        self.nodes_expanded = 0
        self.simulations_run = 0

    # -- leaf evaluation ------------------------------------------------------

    def rollout(self, board: Board, state: GameState) -> float:
        """Play uniformly at random to the end; return +1/-1 for ``to_move``.

        Sound here in a way it is not in Go: FLIPHEX playouts are at most one
        ply per empty cell, always terminate, and always yield a decided winner
        because a draw is impossible on an odd cell count. R&N 6.4's
        early-termination machinery is void (adr-005 Phase 2 amendment, 3).
        """
        mover = state.to_move
        while not is_terminal(state):
            state = apply_move(board, state, self.rng.choice(legal_moves(board, state)))
        return float(outcome(state, mover))

    # -- the search -----------------------------------------------------------

    def run(self, state: GameState, simulations: int) -> Node:
        """Search ``state`` for ``simulations`` and return the populated root."""
        root = Node(prior=1.0)
        self._expand(root, state)
        self._add_root_noise(root)

        for _ in range(simulations):
            self._simulate(root, state)
            self.simulations_run += 1
        return root

    def _simulate(self, root: Node, root_state: GameState) -> None:
        node, state = root, root_state
        path = [node]

        # Descend while the node is expanded and has somewhere to go.
        while node.expanded and node.children:
            node = self._select_child(node)
            state = apply_move(self.board, state, node.move)
            path.append(node)

        if is_terminal(state):
            # A decided terminal, from the point of view of the player who would
            # be to move — the same convention _expand's leaves use.
            value = float(outcome(state, state.to_move))
        else:
            self._expand(node, state)
            value = self.evaluate(self.board, state)

        # Zero-sum backup: the value flips sign at every ply going up.
        for node in reversed(path):
            node.visits += 1
            node.value_sum += value
            value = -value

    def _select_child(self, node: Node) -> Node:
        """PUCT: argmax over Q + c_puct * P * sqrt(N) / (1 + n).

        ``-child.q`` because a child's mean is stored from *its own* mover's
        point of view, and this node's mover is the other player.
        """
        sqrt_n = math.sqrt(node.visits) if node.visits else 1.0
        best, best_score = None, -math.inf
        for child in node.children:
            score = -child.q + self.c_puct * child.prior * sqrt_n / (1 + child.visits)
            if score > best_score:
                best, best_score = child, score
        return best

    def _expand(self, node: Node, state: GameState) -> None:
        """Create ``node``'s children according to the expansion mode."""
        node.expanded = True
        if is_terminal(state):
            return
        self.nodes_expanded += 1

        moves = legal_moves(self.board, state)

        if self.mode is ExpansionMode.ACTION:
            reps, mults = moves, [1] * len(moves)
        else:
            classes = group_by_position(self.board, state, moves)
            if self.mode is ExpansionMode.POSITION:
                reps = [c[0] for c in classes]
                mults = [len(c) for c in classes]
            else:  # MULTIPLICITY — every action stays a child, priors divided
                reps, mults = [], []
                for cls in classes:
                    reps.extend(cls)
                    mults.extend([len(cls)] * len(cls))

        weights = self.prior(self.board, state, reps)
        if self.mode is ExpansionMode.MULTIPLICITY:
            weights = [w / m for w, m in zip(weights, mults, strict=True)]
        total = sum(weights) or 1.0

        node.children = [
            Node(prior=w / total, move=m, multiplicity=k)
            for m, w, k in zip(reps, weights, mults, strict=True)
        ]

    def _add_root_noise(self, root: Node) -> None:
        """Dirichlet noise at the root only, per adr-005."""
        if not self.dirichlet_weight or not root.children:
            return
        noise = [
            self.rng.gammavariate(self.dirichlet_alpha, 1.0) for _ in root.children
        ]
        total = sum(noise) or 1.0
        w = self.dirichlet_weight
        for child, n in zip(root.children, noise, strict=True):
            child.prior = (1 - w) * child.prior + w * (n / total)


def uniform_prior(board: Board, state: GameState, moves: list[Move]) -> list[float]:
    """Flat prior. EXP-010 runs on this: no network, so no network to blame."""
    return [1.0] * len(moves)


def visit_counts(root: Node, *, aggregate_aliases: bool = False) -> dict[Move, int]:
    """Visits per child, keyed by that child's representative move.

    ``aggregate_aliases`` is a no-op except in ``ACTION`` mode, where several
    children may denote one position. EXP-010 registers the naive arm's readout
    as the argmax over *action labels* — which is what adr-005 says happens in
    deployment, "``pi`` is then read off those split counts" — so the default is
    False and the aggregating variant exists to be reported beside it.
    """
    if not aggregate_aliases:
        return {c.move: c.visits for c in root.children}
    merged: dict[Move, int] = {}
    for child in root.children:
        merged[child.move] = merged.get(child.move, 0) + child.visits
    return merged


def best_move(root: Node) -> Move:
    """The most-visited child's move. Ties break on child order, which is
    deterministic given the seed — see :func:`group_by_position`."""
    return max(root.children, key=lambda c: c.visits).move


def policy_target(root: Node, temperature: float = 1.0) -> dict[Move, float]:
    """The MCTS policy ``pi``, as adr-005's training target.

    Temperature 1 gives normalised visit counts; ``temperature = 0`` is greedy.
    """
    counts = {c.move: c.visits for c in root.children}
    if temperature <= 0:
        top = max(counts.values(), default=0)
        winners = [m for m, n in counts.items() if n == top]
        return {m: (1.0 / len(winners) if m in winners else 0.0) for m in counts}
    scaled = {m: n ** (1.0 / temperature) for m, n in counts.items()}
    total = sum(scaled.values()) or 1.0
    return {m: v / total for m, v in scaled.items()}


__all__ = [
    "Evaluator",
    "ExpansionMode",
    "MCTS",
    "Node",
    "PriorFn",
    "best_move",
    "group_by_position",
    "occupied_arrow_key",
    "policy_target",
    "uniform_prior",
    "visit_counts",
]
