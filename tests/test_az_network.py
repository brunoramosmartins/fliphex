"""Tests for ``az/network.py``.

Two of these exist because the module makes a claim that could quietly stop
being true:

- :func:`test_summing_raw_logits_equals_the_specified_log_softmax_rule` pins the
  algebraic shortcut. The head is *specified* as
  ``log p(cell) + log p(tile) + log p(rotation)`` renormalised over legal moves;
  the code sums raw logits instead. That is the same distribution only because
  the three normalising constants are shared by every move. If a factor ever
  gains a per-move term, the shortcut breaks and this test is what says so.
- :func:`test_evaluating_does_not_leave_the_network_in_eval_mode` pins a
  footgun: the search adapter is called from inside the training loop, and a
  helper that left ``eval`` set would freeze every batch-norm layer for the rest
  of a 60-hour run without raising anything.
"""

from __future__ import annotations

import pytest
import torch

from az.encoding import N_PLANES, encode
from az.network import (
    N_ROTATIONS,
    FlipHexNet,
    masked_log_policy,
    policy_and_value,
    to_tensor,
)
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.state import TILES
from fliphex.variant import Arm, Variant

FULL = Variant(5, 5, Arm("h1"))
SMALL = Variant(5, 3, Arm("h2"))
TINY = Variant(3, 3, Arm("h1"))
VARIANTS = [FULL, SMALL, TINY]


@pytest.fixture
def net() -> FlipHexNet:
    torch.manual_seed(0)
    return FlipHexNet(5, 5)


# -- shapes -------------------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS)
def test_the_heads_have_the_specified_widths(variant):
    """25 + 13 + 6 = 44 logits on the full board, not 1950."""
    net = FlipHexNet(variant.n_cols, variant.n_rows)
    board, state = variant.board(), variant.initial_state()

    x = to_tensor(encode(board, state), variant.n_cols, variant.n_rows)
    cells, tiles, rotations, value = net(x)

    assert cells.shape == (1, variant.n_cells)
    assert tiles.shape == (1, len(TILES))
    assert rotations.shape == (1, N_ROTATIONS)
    assert value.shape == (1,)
    assert cells.shape[1] + tiles.shape[1] + rotations.shape[1] == variant.n_cells + 19


def test_the_full_board_head_is_44_logits():
    assert 25 + len(TILES) + N_ROTATIONS == 44


def test_a_batch_keeps_its_order_and_shape():
    board = FULL.board()
    states = [FULL.initial_state()]
    for _ in range(3):
        moves = legal_moves(board, states[-1])
        states.append(apply_move(board, states[-1], moves[0]))
    buffers = [encode(board, s) for s in states]

    batched = to_tensor(buffers, 5, 5)

    assert batched.shape == (4, N_PLANES, 5, 5)
    assert batched.dtype == torch.float32
    for i, buffer in enumerate(buffers):
        single = to_tensor(buffer, 5, 5)
        assert torch.equal(batched[i], single[0])


# -- the factored policy ------------------------------------------------------


def test_summing_raw_logits_equals_the_specified_log_softmax_rule():
    """The shortcut in the docstring, checked against the literal specification."""
    torch.manual_seed(7)
    board, state = FULL.board(), FULL.initial_state()
    moves = legal_moves(board, state)

    cells = torch.randn(25)
    tiles = torch.randn(len(TILES))
    rotations = torch.randn(N_ROTATIONS)

    # The literal rule: normalise each factor, sum the log-probabilities, then
    # renormalise over the legal moves.
    log_cell = torch.log_softmax(cells, dim=0)
    log_tile = torch.log_softmax(tiles, dim=0)
    log_rotation = torch.log_softmax(rotations, dim=0)
    literal = torch.log_softmax(
        torch.tensor(
            [
                log_cell[m.cell] + log_tile[m.tile] + log_rotation[m.rotation]
                for m in moves
            ]
        ),
        dim=0,
    )

    assert torch.allclose(
        masked_log_policy(cells, tiles, rotations, moves), literal, atol=1e-6
    )


@pytest.mark.parametrize("variant", VARIANTS)
def test_priors_are_a_distribution_over_exactly_the_legal_moves(variant):
    torch.manual_seed(3)
    net = FlipHexNet(variant.n_cols, variant.n_rows)
    board, state = variant.board(), variant.initial_state()
    moves = legal_moves(board, state)

    priors, _ = policy_and_value(net, board, state, moves)

    assert len(priors) == len(moves)
    assert all(p > 0 for p in priors)
    assert sum(priors) == pytest.approx(1.0)


def test_an_illegal_combination_receives_no_mass(net):
    """Masking is what keeps the factored head from scoring impossible moves.

    The head assigns a score to every (cell, tile, rotation) triple, including
    triples that are not moves. Restricting the renormalisation to the legal
    list is what removes them, so shrinking the list must move mass, not merely
    relabel it.
    """
    board, state = FULL.board(), FULL.initial_state()
    moves = legal_moves(board, state)
    subset = moves[:10]

    full_priors, _ = policy_and_value(net, board, state, moves)
    subset_priors, _ = policy_and_value(net, board, state, subset)

    assert sum(subset_priors) == pytest.approx(1.0)
    assert subset_priors[0] > full_priors[0]


def test_a_terminal_position_has_no_policy(net):
    with pytest.raises(ValueError, match="terminal"):
        masked_log_policy(torch.randn(25), torch.randn(13), torch.randn(6), [])


def test_the_relative_order_of_two_moves_follows_the_three_factors():
    """A move beats another exactly when its summed factors are larger."""
    cells = torch.tensor([0.0, 5.0] + [0.0] * 23)
    tiles = torch.zeros(len(TILES))
    rotations = torch.zeros(N_ROTATIONS)
    moves = [Move(0, 0, 0), Move(1, 0, 0)]

    log_priors = masked_log_policy(cells, tiles, rotations, moves)

    assert log_priors[1] > log_priors[0]
    assert (log_priors[1] - log_priors[0]).item() == pytest.approx(5.0, abs=1e-5)


# -- the value head -----------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS)
def test_the_value_is_a_tanh_output(variant):
    torch.manual_seed(5)
    net = FlipHexNet(variant.n_cols, variant.n_rows)
    board, state = variant.board(), variant.initial_state()

    _, value = policy_and_value(net, board, state, legal_moves(board, state))

    assert -1.0 <= value <= 1.0


# -- mode handling ------------------------------------------------------------


def test_evaluating_does_not_leave_the_network_in_eval_mode(net):
    board, state = FULL.board(), FULL.initial_state()
    moves = legal_moves(board, state)

    net.train()
    policy_and_value(net, board, state, moves)
    assert net.training is True

    net.eval()
    policy_and_value(net, board, state, moves)
    assert net.training is False


def test_evaluation_is_deterministic(net):
    board, state = FULL.board(), FULL.initial_state()
    moves = legal_moves(board, state)

    first = policy_and_value(net, board, state, moves)
    second = policy_and_value(net, board, state, moves)

    assert first == second


def test_evaluation_does_not_build_a_graph(net):
    """The search calls this millions of times; a retained graph would leak."""
    board, state = FULL.board(), FULL.initial_state()
    x = to_tensor(encode(board, state), 5, 5)

    with torch.no_grad():
        cells, _, _, value = net(x)

    assert not cells.requires_grad
    assert not value.requires_grad


# -- size ---------------------------------------------------------------------


def test_the_tower_is_four_blocks_of_sixty_four(net):
    assert len(net.tower) == 4
    assert net.stem[0].out_channels == 64


def test_the_parameter_count_is_small_enough_to_train_here(net):
    """The head is 44 logits, so the tower dominates and the model stays small."""
    count = net.count_parameters()

    assert 300_000 < count < 400_000
    assert count < 500_000, (
        "below the 0.5-1.5 M band the architecture record targets; the factored "
        "head removes the projection that band was estimated with"
    )
