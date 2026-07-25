"""Tests for the baseline agents, including the >=60% heuristic exit criterion."""

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent, flips_gained
from agents.random_agent import RandomAgent
from fliphex.board import Board
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import is_terminal, winner
from fliphex.state import Colour, GameState


def _play(board: Board, purple: Agent, green: Agent, first: Colour) -> Colour:
    agents = {Colour.PURPLE: purple, Colour.GREEN: green}
    state = GameState.initial(board.n_cells, first)
    while not is_terminal(state):
        state = apply_move(board, state, agents[state.to_move].select(board, state))
    return winner(state)


# -- random agent -------------------------------------------------------------


def test_random_is_reproducible_with_seed():
    board, s = Board(), GameState.initial()
    a, b = RandomAgent(seed=42), RandomAgent(seed=42)
    assert a.select(board, s) == b.select(board, s)


def test_random_only_plays_legal_moves():
    board = Board()
    s = GameState.initial()
    agent = RandomAgent(seed=1)
    legal = set(legal_moves(board, s))
    for _ in range(20):
        assert agent.select(board, s) in legal


# -- heuristic agent ----------------------------------------------------------


def test_heuristic_picks_a_max_flip_move():
    board = Board()
    c = board.cell_id
    # Two green pieces on C3's N (C2) and S (C4); purple can flip both at once.
    s = GameState.initial(first=Colour.PURPLE)
    s = s.with_colour(c("C2"), Colour.GREEN).with_colour(c("C4"), Colour.GREEN)

    best = max(flips_gained(board, s, m) for m in legal_moves(board, s))
    assert best == 2  # only the N+S piece on C3 hits both

    chosen = HeuristicAgent(seed=0).select(board, s)
    assert flips_gained(board, s, chosen) == best


def test_heuristic_beats_random_at_least_60_percent():
    board = Board()
    games = 100
    heuristic_wins = 0
    for i in range(games):
        # Alternate seats so the first-move effect is shared evenly.
        if i % 2 == 0:
            w = _play(board, HeuristicAgent(seed=i), RandomAgent(seed=i), Colour.PURPLE)
            heuristic_wins += w == Colour.PURPLE
        else:
            w = _play(board, RandomAgent(seed=i), HeuristicAgent(seed=i), Colour.PURPLE)
            heuristic_wins += w == Colour.GREEN
    assert heuristic_wins / games >= 0.60
