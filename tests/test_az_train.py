"""Tests for ``az/train.py``.

Everything here rests on one claim: that the softmax normaliser over legal moves
can be computed without generating them, because legality factorises into
``empty cell`` x ``tile in hand`` x ``rotation in the tile's orbit``.

:func:`test_the_closed_form_normaliser_equals_the_brute_force_one` is that claim
checked against move generation itself, across variants and depths. If the
factorisation ever stops holding — a rule change, a new tile, a cell-dependent
restriction — the training loss silently starts optimising the wrong
distribution, and nothing else in the pipeline would notice.
"""

from __future__ import annotations

import pytest
import torch

from az.encoding import encode
from az.network import FlipHexNet, masked_log_policy
from az.replay_buffer import Sample, pack_policy
from az.train import (
    ORBIT_MASK,
    VALUE_WEIGHT,
    legal_normaliser,
    make_batch,
    policy_loss,
    train_generation,
    train_step,
    value_loss,
)
from fliphex.moves import apply_move, legal_moves
from fliphex.state import TILES
from fliphex.variant import Arm, Variant

FULL = Variant(5, 5, Arm("h1"))
SMALL = Variant(5, 3, Arm("h2"))
TINY = Variant(3, 3, Arm("h1"))


def advance(variant: Variant, plies: int):
    board, state = variant.board(), variant.initial_state()
    for _ in range(plies):
        state = apply_move(board, state, legal_moves(board, state)[0])
    return board, state


def a_sample(variant: Variant, plies: int, value: float = 1.0) -> Sample:
    board, state = advance(variant, plies)
    moves = legal_moves(board, state)[:5]
    pi = dict.fromkeys(moves, 1.0 / len(moves))
    packed_moves, probs = pack_policy(pi)
    return Sample(
        planes=encode(board, state), moves=packed_moves, probs=probs, value=value
    )


# -- the orbit table ----------------------------------------------------------


def test_the_orbit_table_reproduces_the_fifty_eight_pairs():
    """13 tiles whose orbits sum to 58 -- the figure move generation produces."""
    assert ORBIT_MASK.shape == (13, 6)
    assert int(ORBIT_MASK.sum()) == 58


def test_the_orbit_table_matches_each_piece():
    for tile, piece in enumerate(TILES):
        expected = set(piece.distinct_rotations())
        actual = {r for r in range(6) if ORBIT_MASK[tile, r]}
        assert actual == expected


def test_the_singleton_orbits_are_the_ones_the_geometry_predicts():
    """P6 and the joker are rotation-invariant; P3-tri has two, the opposite
    pairs three."""
    sizes = {TILES[t].archetype: int(ORBIT_MASK[t].sum()) for t in range(13)}

    assert sizes["P6"] == 1
    assert sizes["JOKER"] == 1
    assert sizes["P3-tri"] == 2
    assert sizes["P2-opp"] == sizes["P4-opp"] == 3


# -- the claim the whole loss rests on ----------------------------------------


@pytest.mark.parametrize("variant", [FULL, SMALL, TINY])
@pytest.mark.parametrize("plies", [0, 3, 7])
def test_the_closed_form_normaliser_equals_the_brute_force_one(variant, plies):
    """Checked against move generation, which is the definition."""
    torch.manual_seed(plies + variant.n_cells)
    board, state = advance(variant, plies)
    moves = legal_moves(board, state)

    cell = torch.randn(1, variant.n_cells)
    tile = torch.randn(1, 13)
    rotation = torch.randn(1, 6)
    planes = _planes(board, state)

    closed = legal_normaliser(cell, tile, rotation, planes)
    brute = torch.logsumexp(
        torch.stack(
            [cell[0, m.cell] + tile[0, m.tile] + rotation[0, m.rotation] for m in moves]
        ),
        dim=0,
    )

    assert closed[0].item() == pytest.approx(brute.item(), abs=1e-4)


@pytest.mark.parametrize("plies", [0, 4, 9])
def test_the_loss_equals_the_naive_masked_cross_entropy(plies):
    """The algebraic collapse ``Z - sum pi * score``, against the literal form."""
    torch.manual_seed(plies)
    board, state = advance(SMALL, plies)
    moves = legal_moves(board, state)
    support = moves[:4]
    pi = dict.fromkeys(support, 0.25)

    packed_moves, probs = pack_policy(pi)
    sample = Sample(
        planes=encode(board, state), moves=packed_moves, probs=probs, value=1.0
    )
    batch = make_batch([sample], SMALL.n_cols, SMALL.n_rows)

    cell = torch.randn(1, SMALL.n_cells)
    tile = torch.randn(1, 13)
    rotation = torch.randn(1, 6)

    computed = policy_loss(cell, tile, rotation, batch)

    # The literal form: log-probabilities over every legal move, then the
    # cross-entropy against pi.
    log_p = masked_log_policy(cell[0], tile[0], rotation[0], moves)
    lookup = {m: log_p[i] for i, m in enumerate(moves)}
    naive = -sum(pi[m] * lookup[m] for m in support)

    assert computed.item() == pytest.approx(naive.item(), abs=1e-4)


def _planes(board, state) -> torch.Tensor:
    from az.network import to_tensor

    return to_tensor(encode(board, state), board.n_cols, board.n_rows)


# -- batching -----------------------------------------------------------------


def test_a_ragged_batch_keeps_each_policy_with_its_own_row():
    first = a_sample(TINY, 0)
    second = a_sample(TINY, 2)
    batch = make_batch([first, second], TINY.n_cols, TINY.n_rows)

    assert len(batch) == 2
    assert batch.index.tolist() == [0] * len(first.policy) + [1] * len(second.policy)
    assert batch.probs.shape == batch.cells.shape
    assert batch.value.tolist() == [1.0, 1.0]


def test_the_batch_planes_match_the_samples():
    samples = [a_sample(TINY, 0), a_sample(TINY, 1)]
    batch = make_batch(samples, TINY.n_cols, TINY.n_rows)

    assert batch.planes.shape[0] == 2
    assert batch.planes.dtype == torch.float32


# -- the value term -----------------------------------------------------------


def test_the_value_loss_is_zero_on_a_perfect_prediction():
    assert value_loss(torch.tensor([1.0, -1.0]), torch.tensor([1.0, -1.0])) == 0.0


def test_the_value_loss_is_worst_when_the_sign_is_backwards():
    """z is exactly +/-1, so the worst case is bounded and known: 4.0."""
    loss = value_loss(torch.tensor([1.0, -1.0]), torch.tensor([-1.0, 1.0]))

    assert loss.item() == pytest.approx(4.0)


def test_the_value_weight_is_stated():
    assert VALUE_WEIGHT == 1.0


# -- the step -----------------------------------------------------------------


def test_a_step_reduces_the_loss_on_a_fixed_batch():
    """Overfitting one batch is the cheapest evidence the gradient is wired."""
    torch.manual_seed(0)
    net = FlipHexNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-2)
    batch = make_batch([a_sample(TINY, 0), a_sample(TINY, 2)], 3, 3)

    first = train_step(net, optimiser, batch)
    for _ in range(20):
        last = train_step(net, optimiser, batch)

    assert last["total"] < first["total"]
    assert last["policy"] < first["policy"]


def test_a_step_leaves_the_network_in_training_mode():
    torch.manual_seed(0)
    net = FlipHexNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-3)
    batch = make_batch([a_sample(TINY, 0)], 3, 3)

    train_step(net, optimiser, batch)

    assert net.training is True


def test_every_parameter_receives_a_gradient():
    """A head wired to nothing would train silently and never improve."""
    torch.manual_seed(0)
    net = FlipHexNet(3, 3)
    optimiser = torch.optim.SGD(net.parameters(), lr=1e-3)
    batch = make_batch([a_sample(TINY, 0), a_sample(TINY, 4)], 3, 3)

    train_step(net, optimiser, batch)

    missing = [n for n, p in net.named_parameters() if p.grad is None]
    assert missing == []


def test_a_generation_trains_from_the_buffers_own_stream():
    """Batches come from the buffer RNG the checkpoint saves."""
    from az.replay_buffer import ReplayBuffer

    torch.manual_seed(0)
    net = FlipHexNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-3)
    buffer = ReplayBuffer(capacity=16, seed=4)
    buffer.extend(a_sample(TINY, i % 5) for i in range(10))

    history = train_generation(
        net, optimiser, buffer, steps=3, batch_size=4, n_cols=3, n_rows=3
    )

    assert len(history) == 3
    assert all(set(row) == {"policy", "value", "total"} for row in history)
