"""Tests for the exact agent.

Two properties carry the weight, and both are silent when they break.

**It must actually play optimally.** An agent that is merely *strong* would pass
a win-rate test against weak baselines while being wrong about the game. So the
search-backed agent is checked against the solver directly — every move it picks
must preserve the position's true value — rather than by counting wins.

**It must not hide its fallback.** ``solver.minimax`` has no evaluation
function, so a position beyond the node budget yields no move at all and the
agent delegates. An agent named "solver" that silently plays its fallback most
of the time is the instrument defect this project keeps finding, so the split is
counted and the counters are pinned here.
"""

import pytest

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from agents.solver_agent import SolverAgent
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import is_terminal, winner
from fliphex.state import Colour, GameState
from fliphex.variant import THREE_BY_THREE
from solver.minimax import LOSS, WIN, Solver


@pytest.fixture
def tiny():
    """The 3×3 fixture: small enough to solve inside a test."""
    return THREE_BY_THREE.board(), THREE_BY_THREE.initial_state()


def _play(board, first_agent, second_agent, root):
    """Play a full game from ``root``; return the winning colour."""
    agents = {root.to_move: first_agent, Colour(3 - root.to_move): second_agent}
    state = root
    while not is_terminal(state):
        state = apply_move(board, state, agents[state.to_move].select(board, state))
    return winner(state)


# -- optimality, checked against the solver rather than against opponents -----


def test_every_move_preserves_the_true_value(tiny):
    """The definition of optimal play, asserted ply by ply.

    From a won position the agent's move must leave the opponent lost; from a
    lost one it cannot do better, so only the won side is a real constraint.
    """
    board, root = tiny
    agent = SolverAgent(seed=7)
    state = root

    while not is_terminal(state):
        before = Solver(board).solve(state).value
        move = agent.select(board, state)
        after = Solver(board).solve(apply_move(board, state, move)).value
        if before == WIN:
            assert after == LOSS, "a winning position was thrown away"
        state = apply_move(board, state, move)

    assert agent.delegated == 0


def test_it_only_plays_legal_moves(tiny):
    board, root = tiny
    agent = SolverAgent(seed=1)
    assert agent.select(board, root) in set(legal_moves(board, root))


def test_the_solved_side_never_loses(tiny):
    """Against any opponent, from a won root, the exact agent must win."""
    board, root = tiny
    assert Solver(board).solve(root).value == WIN

    for opponent in (RandomAgent(seed=3), HeuristicAgent(seed=3)):
        agent = SolverAgent(seed=5)
        assert _play(board, agent, opponent, root) == root.to_move


# -- the fallback must be visible --------------------------------------------


def test_a_budget_too_small_delegates_and_counts_it(tiny):
    board, root = tiny
    agent = SolverAgent(max_nodes=1, seed=2)

    move = agent.select(board, root)

    assert move in set(legal_moves(board, root))
    assert agent.delegated == 1
    assert agent.proved == 0
    assert agent.stats()["proved_rate"] == 0.0


def test_stats_report_the_split(tiny):
    board, root = tiny
    agent = SolverAgent(seed=2)
    agent.select(board, root)

    stats = agent.stats()
    assert stats["backend"] == "search"
    assert stats["moves"] == 1
    assert stats["proved"] == 1
    assert stats["proved_rate"] == 1.0


def test_the_fallback_is_configurable(tiny):
    board, root = tiny
    sentinel = RandomAgent(seed=9)
    agent = SolverAgent(max_nodes=1, fallback=sentinel, seed=2)
    assert agent.select(board, root) in set(legal_moves(board, root))
    assert agent.stats()["fallback"] == "random"


# -- the database backend ----------------------------------------------------


class _StubReader:
    """A SweepReader stand-in: a real one needs the 4.1 GB checkpoint on disk."""

    def __init__(self, losing: set) -> None:
        self._losing = losing

    def value(self, state: GameState) -> int:
        return LOSS if state.zobrist in self._losing else WIN


def test_database_backend_plays_a_move_the_table_calls_a_loss(tiny):
    """Asserted on the resulting *position*, not on the move.

    Several moves reach the same position — a rotation only matters through the
    cells its arrows point at, so distinct ``(tile, rotation)`` pairs collapse
    whenever they flip the same set (adr-003: the state stores a colour per
    cell and nothing else). Demanding a particular move back would pin an
    arbitrary tie-break rather than the property that matters.
    """
    board, root = tiny
    losing_child = apply_move(board, root, legal_moves(board, root)[3]).zobrist

    agent = SolverAgent(reader=_StubReader({losing_child}), seed=4)
    chosen = agent.select(board, root)

    assert apply_move(board, root, chosen).zobrist == losing_child
    assert agent.proved == 1
    assert agent.stats()["backend"] == "database"


def test_database_backend_still_moves_from_a_lost_position(tiny):
    """Every move loses, so any is optimal — but it must still return one."""
    board, root = tiny
    agent = SolverAgent(reader=_StubReader(set()), seed=4)

    assert agent.select(board, root) in set(legal_moves(board, root))
    assert agent.delegated == 0


def test_database_backend_never_consults_the_budget(tiny):
    """A lookup is not a search; max_nodes must not make it delegate."""
    board, root = tiny
    agent = SolverAgent(reader=_StubReader(set()), max_nodes=1, seed=4)

    agent.select(board, root)

    assert agent.delegated == 0
    assert agent.proved == 1
