"""Tests for ``agents/az_agent.py``.

Two of these are about the evaluator gate rather than about the agents:

- :func:`test_two_deterministic_agents_replay_one_game` records the trap. At
  temperature zero with no root noise a searcher is a pure function of the
  position, so a 400-game match between two of them measures one game and
  reports n = 400.
- :func:`test_sampling_the_opening_makes_the_games_distinct` records the way
  out, and that it weakens both sides identically.

:func:`test_importing_an_agent_does_not_pull_in_torch` guards the packaging
decision: the exact-solver runs use an interpreter with no torch build, and they
import this package.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
import torch

from agents.az_agent import EVALUATION_TEMPERATURE_PLIES, AZAgent, UCTAgent
from agents.base import Agent
from agents.random_agent import RandomAgent
from az.mcts import ExpansionMode
from az.network import FlipHexNet
from az.player import SearchPlayer
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import is_terminal
from fliphex.state import Colour
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))


@pytest.fixture
def net() -> FlipHexNet:
    torch.manual_seed(0)
    model = FlipHexNet(3, 3)
    model.eval()
    return model


def play(first: Agent, second: Agent, variant: Variant = TINY) -> list:
    """Play a whole game and return the move sequence."""
    board, state = variant.board(), variant.initial_state()
    moves = []
    while not is_terminal(state):
        agent = first if state.to_move == variant.first else second
        move = agent.select(board, state)
        moves.append(move)
        state = apply_move(board, state, move)
    return moves


# -- the interface ------------------------------------------------------------


def test_both_agents_satisfy_the_agent_interface(net):
    assert isinstance(AZAgent(net, simulations=4), Agent)
    assert isinstance(UCTAgent(simulations=4), Agent)


def test_they_return_a_legal_move(net):
    board, state = TINY.board(), TINY.initial_state()
    legal = set(legal_moves(board, state))

    assert AZAgent(net, simulations=8, seed=1).select(board, state) in legal
    assert UCTAgent(simulations=8, seed=1).select(board, state) in legal


def test_they_play_a_game_to_a_decided_end(net):
    az = AZAgent(net, simulations=6, seed=1)
    uct = UCTAgent(simulations=6, seed=2)

    moves = play(az, uct)

    assert len(moves) == TINY.n_cells


def test_they_name_themselves_for_the_benchmark_log(net):
    assert str(AZAgent(net, simulations=1)) == "az"
    assert str(UCTAgent(simulations=1)) == "uct"


def test_the_expansion_mode_is_deduplicating_by_default(net):
    assert AZAgent(net, simulations=1).mode is ExpansionMode.POSITION
    assert UCTAgent(simulations=1).mode is ExpansionMode.POSITION


# -- determinism, and why the gate has to care --------------------------------


def test_two_deterministic_agents_replay_one_game(net):
    """The trap a 400-game gate walks into.

    With no temperature and no root noise both agents are pure functions of the
    position, so every game of a match is the same game. The binomial interval
    would be computed on n = 400 while the effective sample is one.
    """
    first = play(AZAgent(net, simulations=8, seed=1), UCTAgent(simulations=8, seed=1))
    second = play(AZAgent(net, simulations=8, seed=1), UCTAgent(simulations=8, seed=1))

    assert first == second


def test_sampling_the_opening_makes_the_games_distinct(net):
    """The way out, and it weakens both sides identically."""
    games = {
        tuple(
            play(
                AZAgent(
                    net,
                    simulations=8,
                    seed=seed,
                    temperature_plies=EVALUATION_TEMPERATURE_PLIES,
                ),
                UCTAgent(
                    simulations=8,
                    seed=seed + 100,
                    temperature_plies=EVALUATION_TEMPERATURE_PLIES,
                ),
            )
        )
        for seed in range(6)
    }

    assert len(games) > 1


def test_the_same_seed_reproduces_a_match(net):
    a = play(AZAgent(net, simulations=6, seed=3, temperature_plies=4), RandomAgent(9))
    b = play(AZAgent(net, simulations=6, seed=3, temperature_plies=4), RandomAgent(9))

    assert a == b


def test_different_seeds_diverge_once_the_opening_is_sampled(net):
    a = play(AZAgent(net, simulations=6, seed=3, temperature_plies=4), RandomAgent(9))
    b = play(AZAgent(net, simulations=6, seed=4, temperature_plies=4), RandomAgent(9))

    assert a != b


def test_the_recommended_match_setting_is_stated():
    assert EVALUATION_TEMPERATURE_PLIES == 4


# -- the floor ----------------------------------------------------------------


def test_the_floor_needs_no_network():
    """It cannot be flattered by a bad training run, which is its whole point."""
    board, state = TINY.board(), TINY.initial_state()

    move = UCTAgent(simulations=16, seed=1).select(board, state)

    assert move in set(legal_moves(board, state))


def test_more_simulations_change_the_floors_choice():
    """A sanity check that the budget is actually being spent."""
    board, state = TINY.board(), TINY.initial_state()

    shallow = [UCTAgent(simulations=2, seed=s).select(board, state) for s in range(8)]
    deep = [UCTAgent(simulations=64, seed=s).select(board, state) for s in range(8)]

    assert shallow != deep


def test_the_floor_beats_random_more_often_than_not():
    """A weak but non-vacuous strength check on a 9-cell board."""
    wins = 0
    for seed in range(12):
        board, state = TINY.board(), TINY.initial_state()
        uct = UCTAgent(simulations=48, seed=seed)
        rnd = RandomAgent(seed + 500)
        while not is_terminal(state):
            agent = uct if state.to_move == TINY.first else rnd
            state = apply_move(board, state, agent.select(board, state))
        purple, green = state.score()
        wins += purple > green

    assert wins >= 7, f"UCT won only {wins}/12 as first player"


# -- packaging ----------------------------------------------------------------


def test_importing_an_agent_does_not_pull_in_torch():
    """The exact-solver runs use an interpreter without torch and import this
    package. Listing AZAgent in ``agents/__init__`` would break them."""
    code = (
        "import sys; from agents.random_agent import RandomAgent; "
        "print('torch' in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "False"


def test_the_package_export_list_stays_torch_free():
    import agents

    assert "AZAgent" not in agents.__all__
    assert "UCTAgent" not in agents.__all__


def test_the_agents_are_adapters_onto_the_az_layer(net):
    """The gate needs move selection and lives in az, so the logic must sit
    below this wrapper -- otherwise az imports agents and agents imports az."""
    assert isinstance(AZAgent(net, simulations=1).player, SearchPlayer)
    assert isinstance(UCTAgent(simulations=1).player, SearchPlayer)


def test_az_does_not_import_agents():
    import subprocess
    import sys as _sys

    code = "import sys, az.gate, az.player; print('agents' in sys.modules)"
    result = subprocess.run(
        [_sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "False"


def test_the_colours_are_what_the_helper_assumes():
    assert TINY.first in (Colour.PURPLE, Colour.GREEN)
