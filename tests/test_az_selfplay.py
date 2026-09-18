"""Tests for ``az/selfplay.py`` and the network's search adapter.

Three of these guard properties that are invisible in a training curve:

- :func:`test_no_search_seed_is_reused_across_a_generation` — the per-ply seed
  used to be ``game_seed + ply``, and game seeds from consecutive indices are
  themselves consecutive, so game *i* at ply 1 ran under the same seed as game
  *i+1* at ply 0. That does not produce identical games — the positions differ —
  but it reuses one Dirichlet realisation across games meant to be independent.
- :func:`test_parallel_generation_matches_sequential` — a generation must be the
  same set of games at any worker count, or a resumed run cannot be
  indistinguishable from an uninterrupted one.
- :func:`test_the_evaluator_asks_the_network_once_per_expansion` — the search
  calls ``prior`` and ``evaluate`` on the same state one line apart. Wired
  naively that is two forward passes for one leaf, and 41% on the whole budget.
"""

from __future__ import annotations

import pytest
import torch

from az.mcts import MCTS, ExpansionMode
from az.network import FlipHexNet, NetworkEvaluator, policy_and_value
from az.selfplay import (
    TEMPERATURE_PLIES,
    game_seed,
    generate,
    play_game,
)
from fliphex.moves import legal_moves
from fliphex.state import Colour
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))
SMALL = Variant(5, 3, Arm("h2"))


@pytest.fixture
def net() -> FlipHexNet:
    torch.manual_seed(0)
    model = FlipHexNet(3, 3)
    model.eval()
    return model


# -- one game -----------------------------------------------------------------


@pytest.mark.parametrize("variant", [TINY, SMALL])
def test_a_game_fills_the_board_and_ends_decided(variant, net):
    model = FlipHexNet(variant.n_cols, variant.n_rows)

    record = play_game(variant, model, simulations=8, seed=1)

    assert len(record.positions) == variant.n_cells
    assert len(record.moves) == variant.n_cells
    assert record.winner in (Colour.PURPLE, Colour.GREEN)


def test_the_recorded_movers_alternate(net):
    record = play_game(TINY, net, simulations=8, seed=2)

    movers = [mover for _, _, mover in record.positions]
    assert movers[0] == TINY.first
    assert all(a != b for a, b in zip(movers, movers[1:], strict=False))


def test_z_matches_the_winner_from_each_movers_side(net):
    record = play_game(TINY, net, simulations=8, seed=3)

    samples = record.samples()
    movers = [mover for _, _, mover in record.positions]
    for sample, mover in zip(samples, movers, strict=True):
        assert sample.value == (1.0 if mover == record.winner else -1.0)


def test_the_policy_target_is_recorded_at_temperature_one(net):
    """pi is the training target; sampling it greedily would discard the search's
    own uncertainty even on plies where the *move* is taken greedily."""
    record = play_game(TINY, net, simulations=16, seed=4, temperature_plies=0)

    _, pi, _ = record.positions[0]
    assert sum(pi.values()) == pytest.approx(1.0)
    assert sum(1 for p in pi.values() if p > 0) > 1, "a greedy target would be one-hot"


def test_the_same_seed_replays_the_same_game(net):
    first = play_game(TINY, net, simulations=8, seed=5)
    second = play_game(TINY, net, simulations=8, seed=5)

    assert first.moves == second.moves
    assert first.winner == second.winner
    assert first.search_seeds == second.search_seeds


def test_different_seeds_diverge(net):
    a = play_game(TINY, net, simulations=8, seed=5)
    b = play_game(TINY, net, simulations=8, seed=6)

    assert a.moves != b.moves or a.search_seeds != b.search_seeds


def test_without_a_network_the_search_is_the_plain_uct_floor():
    """adr-005's absolute baseline: no priors, no value head, random rollouts."""
    record = play_game(TINY, None, simulations=8, seed=7)

    assert len(record.positions) == TINY.n_cells
    assert record.winner in (Colour.PURPLE, Colour.GREEN)


# -- the temperature schedule -------------------------------------------------


def test_the_opening_is_sampled_and_the_rest_is_greedy(net):
    """After the temperature plies, the played move is pi's argmax."""
    record = play_game(TINY, net, simulations=24, seed=8, temperature_plies=2)

    for ply, ((_, pi, _), move) in enumerate(
        zip(record.positions, record.moves, strict=True)
    ):
        if ply >= 2:
            assert pi[move] == max(pi.values())


def test_zero_temperature_plies_makes_every_move_greedy(net):
    record = play_game(TINY, net, simulations=24, seed=9, temperature_plies=0)

    for (_, pi, _), move in zip(record.positions, record.moves, strict=True):
        assert pi[move] == max(pi.values())


def test_the_temperature_window_is_a_third_of_a_short_game():
    """Stated so that changing it is a decision rather than a drift."""
    assert TEMPERATURE_PLIES == 8


# -- seeds --------------------------------------------------------------------


def test_game_seed_is_a_pure_function_of_its_coordinates():
    assert game_seed(7, 0, 3) == game_seed(7, 0, 3)
    assert game_seed(7, 0, 3) != game_seed(7, 1, 3)
    assert game_seed(7, 0, 3) != game_seed(8, 0, 3)


def test_no_search_seed_is_reused_across_a_generation(net):
    """The regression test for ``game_seed + ply``.

    Consecutive game indices give consecutive game seeds, so adding the ply
    number made game i's ply 1 collide with game i+1's ply 0. The positions
    differ, so the games do not come out identical — what is reused is the
    Dirichlet realisation, across games that are supposed to be independent.
    """
    seeds = []
    for index in range(6):
        record = play_game(TINY, net, simulations=4, seed=game_seed(11, 0, index))
        seeds += record.search_seeds

    assert len(seeds) == len(set(seeds))


# -- generations --------------------------------------------------------------


def test_a_generation_yields_one_sample_per_ply_per_game(net):
    samples = generate(TINY, net, n_games=3, simulations=4, seed=13)

    assert len(samples) == 3 * TINY.n_cells


def test_successive_generations_do_not_replay_the_same_games(net):
    first = generate(TINY, net, n_games=2, simulations=4, seed=13, generation=0)
    second = generate(TINY, net, n_games=2, simulations=4, seed=13, generation=1)

    assert [s.planes for s in first] != [s.planes for s in second]


def test_parallel_generation_matches_sequential(net):
    """A generation must not depend on which worker finished first."""
    sequential = generate(TINY, net, n_games=4, simulations=4, seed=17, workers=1)
    parallel = generate(TINY, net, n_games=4, simulations=4, seed=17, workers=2)

    assert len(sequential) == len(parallel)
    for a, b in zip(sequential, parallel, strict=True):
        assert a == b


# -- the network adapter ------------------------------------------------------


def test_the_evaluator_asks_the_network_once_per_expansion():
    """Two forward passes per leaf would be 41% on the whole self-play budget."""
    torch.manual_seed(0)
    board, state = TINY.board(), TINY.initial_state()
    model = FlipHexNet(3, 3)
    model.eval()
    evaluator = NetworkEvaluator(model, board)

    search = MCTS(
        board,
        mode=ExpansionMode.POSITION,
        prior=evaluator.prior,
        evaluate=evaluator.evaluate,
        dirichlet_weight=0.25,
        seed=1,
    )
    search.run(state, 40)

    assert evaluator.forwards == search.nodes_expanded


def test_the_cache_returns_what_an_uncached_call_would(net):
    """The optimisation must not be able to change an answer, only its cost."""
    board, state = TINY.board(), TINY.initial_state()
    moves = legal_moves(board, state)
    evaluator = NetworkEvaluator(net, board)

    cached_priors = evaluator.prior(board, state, moves)
    cached_value = evaluator.evaluate(board, state)
    direct_priors, direct_value = policy_and_value(net, board, state, moves)

    assert cached_priors == pytest.approx(direct_priors)
    assert cached_value == pytest.approx(direct_value)


def test_a_new_state_misses_the_cache(net):
    board = TINY.board()
    state = TINY.initial_state()
    evaluator = NetworkEvaluator(net, board)

    evaluator.evaluate(board, state)
    assert evaluator.forwards == 1

    evaluator.evaluate(board, state)
    assert evaluator.forwards == 1, "same object, cached"

    from fliphex.moves import apply_move

    evaluator.evaluate(board, apply_move(board, state, legal_moves(board, state)[0]))
    assert evaluator.forwards == 2
