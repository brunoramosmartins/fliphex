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


# -- the flat head, EXP-011's other arm ---------------------------------------


def test_the_flat_head_spans_the_full_action_space():
    """Not the tiles this deck holds: that would be a fact the factored arm is
    not given, biasing the comparison toward the arm whose win amends the ADR."""
    from az.network import FlatHeadNet

    net = FlatHeadNet(5, 3)

    assert net.flat_head.out_features == 15 * 13 * 6 == 1170


def test_the_flat_head_shares_the_factored_tower():
    """Inheritance is what makes 'identical tower' structural rather than a claim."""
    from az.network import FlatHeadNet, FlipHexNet

    torch.manual_seed(0)
    flat = FlatHeadNet(5, 3)
    torch.manual_seed(0)
    factored = FlipHexNet(5, 3)

    assert isinstance(flat, FlipHexNet)
    for key, tensor in factored.tower.state_dict().items():
        assert torch.equal(flat.tower.state_dict()[key], tensor)


@pytest.mark.parametrize("variant", [FULL, SMALL, TINY])
@pytest.mark.parametrize("plies", [0, 4])
def test_the_legal_mask_selects_exactly_the_legal_moves(variant, plies):
    """The flat arm's notion of legal is the factored arm's, not a second one."""
    from az.network import flat_index
    from az.train import legal_mask

    board, state = advance(variant, plies)
    moves = legal_moves(board, state)

    mask = legal_mask(_planes(board, state), variant.n_cells)

    assert int(mask.sum()) == len(moves)
    for move in moves:
        assert mask[0, flat_index(move)]


@pytest.mark.parametrize("plies", [0, 5])
def test_the_flat_loss_equals_its_naive_masked_cross_entropy(plies):
    from az.network import FlatHeadNet, flat_masked_log_policy
    from az.train import flat_policy_loss

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
    logits = torch.randn(1, SMALL.n_cells * 13 * 6)

    computed = flat_policy_loss(logits, batch, SMALL.n_cells)

    log_p = flat_masked_log_policy(logits[0], moves)
    lookup = {m: log_p[i] for i, m in enumerate(moves)}
    naive = -sum(pi[m] * lookup[m] for m in support)

    assert computed.item() == pytest.approx(naive.item(), abs=1e-4)
    assert isinstance(FlatHeadNet(5, 3), object)


def test_a_flat_step_reduces_the_loss_and_reaches_every_parameter():
    from az.network import FlatHeadNet

    torch.manual_seed(0)
    net = FlatHeadNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-2)
    batch = make_batch([a_sample(TINY, 0), a_sample(TINY, 2)], 3, 3)

    first = train_step(net, optimiser, batch)
    for _ in range(20):
        last = train_step(net, optimiser, batch)

    assert last["policy"] < first["policy"]
    assert [n for n, p in net.named_parameters() if p.grad is None] == []


def test_the_flat_head_is_bigger_where_it_matters():
    """The comparison is a ratio of output widths: 34 against 1170 on the 5x3."""
    from az.network import FlatHeadNet, FlipHexNet

    factored = FlipHexNet(5, 3)
    flat = FlatHeadNet(5, 3)
    factored_logits = (
        factored.cell_head.out_features
        + factored.tile_head.out_features
        + factored.rotation_head.out_features
    )

    assert factored_logits == 34
    assert flat.flat_head.out_features == 1170
    assert flat.count_parameters() > factored.count_parameters()


# -- EXP-012's three matched arms ---------------------------------------------


@pytest.mark.parametrize("readout", ["cell", "pooled", "tile"])
@pytest.mark.parametrize("variant", [FULL, SMALL, TINY])
@pytest.mark.parametrize("plies", [0, 3, 7])
def test_each_conditioned_normaliser_equals_brute_force(readout, variant, plies):
    """The precondition EXP-012 registers.

    The cell readout's score is not additively separable, so the two-term split
    the factored head uses is invalid for it. A wrong normaliser does not raise:
    it optimises the wrong distribution and reads as a slightly weaker arm --
    on the arm the adoption rule is about, in the direction that refutes it.
    """
    import math as _math

    from az.network import RotationReadout
    from az.train import conditioned_normaliser

    torch.manual_seed(plies + variant.n_cells)
    board, state = advance(variant, plies)
    moves = legal_moves(board, state)
    mode = RotationReadout(readout)

    cell = torch.randn(1, variant.n_cells)
    tile = torch.randn(1, 13)
    rows = torch.randn(1, max(variant.n_cells, 13), 6)
    planes = _planes(board, state)

    if mode is RotationReadout.CELL:

        def term(m):
            return rows[0, m.cell, m.rotation]
    elif mode is RotationReadout.TILE:

        def term(m):
            return rows[0, m.tile, m.rotation]
    else:
        pooled = rows.mean(dim=1) * _math.sqrt(rows.shape[1])

        def term(m):
            return pooled[0, m.rotation]

    brute = torch.logsumexp(
        torch.stack([cell[0, m.cell] + tile[0, m.tile] + term(m) for m in moves]),
        dim=0,
    )
    closed = conditioned_normaliser(cell, tile, rows, planes, mode)

    assert closed[0].item() == pytest.approx(brute.item(), abs=1e-4)


def test_the_three_arms_have_identical_parameter_counts():
    """B - C isolates the conditioning only if the size is held fixed."""
    from az.network import ConditionedHeadNet, RotationReadout

    counts = set()
    for readout in RotationReadout:
        torch.manual_seed(0)
        counts.add(ConditionedHeadNet(5, 3, readout=readout).count_parameters())

    assert counts == {373369}


def test_everything_but_the_policy_head_is_identical_across_architectures():
    """The value head is constructed first, so a head-size change cannot shift
    the RNG stream and give two arms different value heads at one seed."""
    from az.network import ConditionedHeadNet, FlatHeadNet, RotationReadout

    nets = []
    for build in (
        lambda: FlipHexNet(5, 3),
        lambda: FlatHeadNet(5, 3),
        lambda: ConditionedHeadNet(5, 3, readout=RotationReadout.CELL),
    ):
        torch.manual_seed(0)
        nets.append(build())

    reference = nets[0]
    for other in nets[1:]:
        for module in ("stem", "tower", "value_head", "policy_conv"):
            for a, b in zip(
                getattr(reference, module).parameters(),
                getattr(other, module).parameters(),
                strict=True,
            ):
                assert torch.equal(a, b), module


def test_the_pooled_arm_matches_the_factored_arms_initial_scale():
    """A plain mean would start the rotation term at 1/sqrt(15) of A's scale."""
    from az.network import ConditionedHeadNet, RotationReadout

    torch.manual_seed(0)
    pooled_net = ConditionedHeadNet(5, 3, readout=RotationReadout.POOLED)
    torch.manual_seed(0)
    factored = FlipHexNet(5, 3)

    x = torch.zeros(64, 30, 5, 3)
    x[:, 2] = 1.0
    pooled_net.eval()
    factored.eval()
    with torch.no_grad():
        _, _, rows, _ = pooled_net(x)
        pooled = pooled_net.pooled_vector(rows)
        _, _, plain, _ = factored(x)

    ratio = pooled.std().item() / plain.std().item()
    assert 0.5 < ratio < 2.0, f"scale ratio {ratio:.2f}; a plain mean gives ~0.26"


def test_the_pooled_arm_has_the_factored_arms_function_class():
    """Pooling collapses 90 weights to a 6-vector: expressive dimension 32."""
    from az.network import ConditionedHeadNet, RotationReadout

    torch.manual_seed(0)
    net = ConditionedHeadNet(5, 3, readout=RotationReadout.POOLED)
    x = torch.zeros(4, 30, 5, 3)
    x[:, 2] = 1.0
    net.eval()
    with torch.no_grad():
        _, _, rows, _ = net(x)

    assert net.pooled_vector(rows).shape == (4, 6)


@pytest.mark.parametrize("readout", ["cell", "pooled", "tile"])
def test_a_conditioned_step_trains_and_reaches_every_live_parameter(readout):
    from az.network import ConditionedHeadNet, RotationReadout

    torch.manual_seed(0)
    net = ConditionedHeadNet(3, 3, readout=RotationReadout(readout))
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-2)
    batch = make_batch([a_sample(TINY, 0), a_sample(TINY, 2)], 3, 3)

    first = train_step(net, optimiser, batch)
    for _ in range(20):
        last = train_step(net, optimiser, batch)

    assert last["policy"] < first["policy"]
    assert [n for n, p in net.named_parameters() if p.grad is None] == []


# -- EXP-013's convolutional parameterisation ---------------------------------


@pytest.mark.parametrize("variant", [FULL, SMALL, TINY])
@pytest.mark.parametrize("plies", [0, 3, 7])
def test_the_conv_rotation_normaliser_equals_brute_force(variant, plies):
    """EXP-013's first correctness precondition.

    The convolutional arm computes the same non-separable score as the adopted
    head, so the nested closed form applies unchanged -- but "applies unchanged"
    is a claim about code. A wrong normaliser does not raise: it optimises the
    wrong distribution and reads as a weaker arm, and it would land on the
    treatment arm specifically, in the direction that keeps the incumbent.
    """
    from az.network import ConvRotationNet, RotationReadout
    from az.train import conditioned_normaliser

    torch.manual_seed(plies + variant.n_cells)
    board, state = advance(variant, plies)
    moves = legal_moves(board, state)

    net = ConvRotationNet(variant.n_cols, variant.n_rows).eval()
    planes = _planes(board, state)
    with torch.no_grad():
        cell, tile, rows, _ = net(planes)

    brute = torch.logsumexp(
        torch.stack(
            [
                cell[0, m.cell] + tile[0, m.tile] + rows[0, m.cell, m.rotation]
                for m in moves
            ]
        ),
        dim=0,
    )
    closed = conditioned_normaliser(cell, tile, rows, planes, RotationReadout.CELL)

    assert closed[0].item() == pytest.approx(brute.item(), abs=1e-4)


@pytest.mark.parametrize("variant", [FULL, SMALL, TINY])
def test_the_conv_rows_are_the_convolution_at_that_cells_position(variant):
    """The cell ordering must match the board's, or every row is misattributed.

    ``az.encoding`` lays cell ``c`` at flat index ``c`` within each plane, so
    reshaping to ``(n_cols, n_rows)`` puts cell ``c`` at ``(c // n_rows,
    c % n_rows)``. The convolution's ``flatten(2)`` must walk the same order. A
    mismatch would not raise anywhere: rotation logits would simply be read from
    the wrong cell, and the arm would look worse for a reason that is a bug.
    """
    from az.network import ConvRotationNet

    torch.manual_seed(0)
    net = ConvRotationNet(variant.n_cols, variant.n_rows).eval()
    x = torch.randn(1, 30, variant.n_cols, variant.n_rows)

    with torch.no_grad():
        spatial = net.policy_conv[:3](net.tower(net.stem(x)))
        conv = net.rotation_head(spatial)
        _, _, rows, _ = net(x)

    for i in range(variant.n_cols):
        for j in range(variant.n_rows):
            cell = i * variant.n_rows + j
            assert torch.equal(rows[0, cell], conv[0, :, i, j] * net.rotation_scale)


def test_the_conv_arm_shares_every_non_rotation_parameter_with_the_adopted_head():
    """EXP-013 reuses the adopted arm's measured rows rather than retraining.

    That is only legitimate if the two arms differ in the rotation head alone.
    Constructing the conv arm through the parent keeps the RNG stream identical
    through everything built before it, which is the same discipline the value
    head's construction order enforces.
    """
    from az.network import ConditionedHeadNet, ConvRotationNet, RotationReadout

    torch.manual_seed(0)
    linear = ConditionedHeadNet(5, 3, readout=RotationReadout.CELL)
    torch.manual_seed(0)
    conv = ConvRotationNet(5, 3)

    for module in (
        "stem",
        "tower",
        "value_head",
        "policy_conv",
        "cell_head",
        "tile_head",
    ):
        left = getattr(linear, module).state_dict()
        right = getattr(conv, module).state_dict()
        assert left.keys() == right.keys()
        for key in left:
            assert torch.equal(left[key], right[key]), f"{module}.{key} differs"


def test_the_conv_rotation_head_is_198_parameters_on_every_board():
    """The claim the entry rests on: 218x smaller, and board-independent."""
    from az.network import ConditionedHeadNet, ConvRotationNet, RotationReadout

    for variant in (FULL, SMALL, TINY):
        torch.manual_seed(0)
        conv = ConvRotationNet(variant.n_cols, variant.n_rows)
        torch.manual_seed(0)
        linear = ConditionedHeadNet(
            variant.n_cols, variant.n_rows, readout=RotationReadout.CELL
        )

        conv_head = sum(p.numel() for p in conv.rotation_head.parameters())
        linear_head = sum(p.numel() for p in linear.rotation_head.parameters())

        assert conv_head == 198
        assert linear_head > conv_head
        assert conv.count_parameters() < linear.count_parameters()

    # On the shipped board the conditioned network is smaller than the factored
    # head it replaced -- full cell conditioning for less than not conditioning.
    torch.manual_seed(0)
    assert ConvRotationNet(5, 5).count_parameters() == 347_887
    assert FlipHexNet(5, 5).count_parameters() == 352_495


def test_a_conv_rotation_step_trains_and_reaches_every_parameter():
    from az.network import ConvRotationNet

    torch.manual_seed(0)
    net = ConvRotationNet(3, 3)
    optimiser = torch.optim.Adam(net.parameters(), lr=1e-2)
    batch = make_batch([a_sample(TINY, 0), a_sample(TINY, 2)], 3, 3)

    first = train_step(net, optimiser, batch)
    for _ in range(20):
        last = train_step(net, optimiser, batch)

    assert last["policy"] < first["policy"]
    assert [n for n, p in net.named_parameters() if p.grad is None] == []


def test_rotation_scale_multiplies_the_rows_and_nothing_else():
    """The scale exists to match initial logit magnitude across arms.

    It must be a pure output scaling -- if it touched the cell or tile logits it
    would no longer leave the function class alone.
    """
    from az.network import ConvRotationNet

    torch.manual_seed(0)
    plain = ConvRotationNet(5, 3, rotation_scale=1.0).eval()
    torch.manual_seed(0)
    scaled = ConvRotationNet(5, 3, rotation_scale=2.5).eval()
    x = torch.randn(2, 30, 5, 3)

    with torch.no_grad():
        c1, t1, r1, v1 = plain(x)
        c2, t2, r2, v2 = scaled(x)

    assert torch.equal(c1, c2)
    assert torch.equal(t1, t2)
    assert torch.equal(v1, v2)
    assert torch.allclose(r2, r1 * 2.5)


def test_the_evaluator_factory_matches_the_head_and_the_search_can_drive_it():
    """The deployment path must be able to play the adopted architecture.

    Before EXP-013 this was false: ``az/player.py`` and ``az/selfplay.py`` both
    hard-coded the factored evaluator, whose ``masked_log_policy`` expects a
    6-wide rotation vector. Handed the conditioned head adr-005 adopted, it
    raised -- so self-play, the gate and the agents were all still
    factored-only after the architecture record had moved.
    """
    from az.network import (
        ConditionedHeadNet,
        ConditionedNetworkEvaluator,
        ConvRotationNet,
        FlatHeadNet,
        FlatNetworkEvaluator,
        NetworkEvaluator,
        RotationReadout,
        evaluator_for,
    )

    board = SMALL.board()
    state = SMALL.initial_state()
    moves = legal_moves(board, state)

    torch.manual_seed(0)
    cases = [
        (FlipHexNet(5, 3), NetworkEvaluator),
        (
            ConditionedHeadNet(5, 3, readout=RotationReadout.CELL),
            ConditionedNetworkEvaluator,
        ),
        (
            ConditionedHeadNet(5, 3, readout=RotationReadout.POOLED),
            ConditionedNetworkEvaluator,
        ),
        (ConvRotationNet(5, 3), ConditionedNetworkEvaluator),
        (FlatHeadNet(5, 3), FlatNetworkEvaluator),
    ]
    for net, expected in cases:
        evaluator = evaluator_for(net, board)
        assert type(evaluator) is expected, f"{type(net).__name__} -> {type(evaluator)}"

        priors = evaluator.prior(board, state, moves)
        assert len(priors) == len(moves)
        assert sum(priors) == pytest.approx(1.0, abs=1e-5)
        assert all(p > 0.0 for p in priors)
        assert -1.0 <= evaluator.evaluate(board, state) <= 1.0
        # One forward for both hooks: the cache is keyed on state identity.
        assert evaluator.forwards == 1


def test_the_conditioned_evaluator_agrees_with_the_training_path():
    """The prior the search sees must be the distribution training optimises.

    Two code paths compute the same score -- the evaluator for play and
    ``conditioned_policy_loss`` for training. If they drift, the network is
    trained on one distribution and played on another, and nothing raises.
    """
    from az.network import (
        ConvRotationNet,
        evaluator_for,
        masked_conditioned_log_policy,
        to_tensor,
    )

    board, state = advance(SMALL, 5)
    moves = legal_moves(board, state)

    torch.manual_seed(0)
    net = ConvRotationNet(5, 3).eval()
    with torch.no_grad():
        cell, tile, rows, _ = net(to_tensor(encode(board, state), 5, 3))
        direct = masked_conditioned_log_policy(net, cell[0], tile[0], rows, moves)

    priors = evaluator_for(net, board).prior(board, state, moves)
    for got, want in zip(priors, direct.exp().tolist(), strict=True):
        assert got == pytest.approx(want, abs=1e-6)


# -- shipping a network across a process boundary -----------------------------


def test_net_spec_round_trips_every_head_type():
    """A state_dict does not say what shape of network it belongs to.

    Self-play workers rebuilt the network as a plain FlipHexNet for as long as
    that was the only head there was. The conditioned head adr-005 adopted does
    not load into it, and the failure appears only under workers > 1, which no
    test exercises -- so the spec is what makes the weights meaningful.
    """
    from az.network import (
        ConditionedHeadNet,
        ConvRotationNet,
        FlatHeadNet,
        RotationReadout,
        build_net,
        net_spec,
        to_tensor,
    )

    board = SMALL.board()
    state = SMALL.initial_state()
    x = to_tensor(encode(board, state), 5, 3)

    torch.manual_seed(0)
    originals = [
        FlipHexNet(5, 3),
        ConditionedHeadNet(5, 3, readout=RotationReadout.CELL),
        ConditionedHeadNet(5, 3, readout=RotationReadout.POOLED),
        ConditionedHeadNet(5, 3, readout=RotationReadout.TILE),
        ConvRotationNet(5, 3, rotation_scale=0.4826),
        FlatHeadNet(5, 3),
    ]
    for net in originals:
        net.eval()
        rebuilt = build_net(net_spec(net))
        rebuilt.load_state_dict(net.state_dict())
        rebuilt.eval()

        assert type(rebuilt) is type(net)
        assert rebuilt.count_parameters() == net.count_parameters()
        with torch.no_grad():
            before, after = net(x), rebuilt(x)
        for left, right in zip(before, after, strict=True):
            assert torch.equal(left, right), type(net).__name__

    # The measured scale is a persistent buffer, so it travels in the weights
    # rather than the spec -- two sources of truth for one constant is how they
    # drift apart.
    conv = ConvRotationNet(5, 3, rotation_scale=0.4826)
    assert "rotation_scale" not in net_spec(conv)
    restored = build_net(net_spec(conv))
    restored.load_state_dict(conv.state_dict())
    assert float(restored.rotation_scale) == pytest.approx(0.4826)


def test_net_spec_carries_a_non_default_tower():
    """Read off the built network, not assumed to be the constructor defaults.

    A spec that silently rebuilds a different tower is worse than no spec: the
    weights would fail to load, or worse, happen to fit.
    """
    from az.network import build_net, net_spec

    torch.manual_seed(0)
    net = FlipHexNet(5, 3, filters=32, blocks=2)
    spec = net_spec(net)

    assert spec["filters"] == 32
    assert spec["blocks"] == 2
    rebuilt = build_net(spec)
    rebuilt.load_state_dict(net.state_dict())
    assert rebuilt.count_parameters() == net.count_parameters()


def test_build_net_refuses_an_unknown_class():
    from az.network import build_net

    with pytest.raises(ValueError, match="unknown network class"):
        build_net({"class": "NotANet", "n_cols": 5, "n_rows": 3})


def test_parallel_self_play_works_with_the_adopted_head():
    """The regression the spec exists for, exercised on the path that broke.

    Every other self-play test runs in process, where the network object is
    passed directly and no rebuild happens. This one crosses a process boundary,
    which is the only place the defect was reachable.
    """
    from az.network import ConvRotationNet
    from az.selfplay import generate

    torch.manual_seed(0)
    net = ConvRotationNet(3, 3)
    samples = generate(
        TINY, net, n_games=2, simulations=4, seed=11, generation=0, workers=2
    )

    assert samples
    assert all(s.planes for s in samples)
