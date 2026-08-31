"""The loss and the training step.

Cross-entropy on the search policy plus mean-squared error on the outcome, with
weight decay. ``z`` is exactly ±1 — draws are impossible on an odd cell count —
so the value head faces a clean binary target with no draw mass pulling it
toward zero.

The normaliser is computed in closed form
-----------------------------------------
The policy the network defines is the factored score **renormalised over the
legal moves**, so the loss needs

    log p(m) = score(m) − log Σ_{m' legal} exp score(m')

and that sum runs over *every* legal move, not only the moves the search
visited. A replay sample stores the visited support alone, so the obvious
implementations are to store the whole legal move list beside it — several
kilobytes a sample, more than doubling the buffer — or to call ``legal_moves``
on every sample of every batch.

Neither is necessary, because **legality factorises exactly**. A move is legal
iff the cell is empty, the tile is in hand, and the rotation lies in that tile's
rotation orbit; the orbit depends on the tile alone and never on the cell.
Measured across variants and depths:

=======  ======  =====  =====  =======
variant  ply     moves  empty  x pairs
=======  ======  =====  =====  =======
5x5-h1   0       1,450  25     58
5x5-h1   7         702  18     39
5x3-h2   11         28   4      7
=======  ======  =====  =====  =======

Every row is an exact product. So the normaliser splits:

    Z = logsumexp over empty cells of  cell
      + logsumexp over available (t, r) of  tile[t] + rotation[r]

Both factors read straight off the input planes — the empty plane gives the
first mask, the own-hand planes give the second — and the orbit table is static.
The training loop therefore never calls ``legal_moves`` at all, and the whole
normaliser is one vectorised operation over the batch.

With ``Σ_m π(m) = 1`` the cross-entropy then collapses to

    policy loss = Z − Σ_m π(m) · score(m)

which is what :func:`policy_loss` computes.

This module imports the game engine and nothing else from the project — never
the exact solver, so no checkpoint can be selected against the ground truth the
two axes are later compared on.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor

from az.encoding import EMPTY_PLANE, N_HAND_PLANES, OWN_HAND_PLANE
from az.network import N_ROTATIONS, FlipHexNet
from az.replay_buffer import ReplayBuffer, Sample
from fliphex.state import TILES

#: ``(13, 6)`` mask: which rotations of each tile are distinct placements.
#: ``P6`` and the joker have an orbit of one, ``P3-tri`` two, the opposite-pair
#: tiles three; the rest six. 58 pairs in total, which is the figure the
#: factorisation above is checked against.
ORBIT_MASK: Tensor = torch.zeros(N_HAND_PLANES, N_ROTATIONS, dtype=torch.bool)
for _tile, _piece in enumerate(TILES):
    for _rotation in _piece.distinct_rotations():
        ORBIT_MASK[_tile, _rotation] = True

#: Weight on the value term. adr-005 does not fix it; 1.0 is the AlphaZero
#: default and is stated here so a change is a decision.
VALUE_WEIGHT = 1.0

NEG_INF = float("-inf")


@dataclass
class Batch:
    """One training batch, flattened so the sparse policies pack together.

    Attributes:
        planes: ``(B, N_PLANES, n_cols, n_rows)``.
        index: ``(M,)`` which sample each policy entry belongs to.
        cells, tiles, rotations: ``(M,)`` the move each entry scores.
        probs: ``(M,)`` the search probability of that move.
        value: ``(B,)`` the outcome, ±1.
    """

    planes: Tensor
    index: Tensor
    cells: Tensor
    tiles: Tensor
    rotations: Tensor
    probs: Tensor
    value: Tensor

    def __len__(self) -> int:
        return self.planes.shape[0]


def make_batch(
    samples: list[Sample],
    n_cols: int,
    n_rows: int,
    *,
    device: torch.device | str = "cpu",
) -> Batch:
    """Pack samples into flat tensors.

    Policies are ragged — each position visited a different number of moves — so
    they are concatenated with an index rather than padded. Padding to the widest
    policy in a batch would allocate for the worst case on every row.
    """
    index, cells, tiles, rotations, probs = [], [], [], [], []
    for row, sample in enumerate(samples):
        for move, probability in sample.policy:
            index.append(row)
            cells.append(move.cell)
            tiles.append(move.tile)
            rotations.append(move.rotation)
            probs.append(probability)

    from az.network import to_tensor

    return Batch(
        planes=to_tensor([s.planes for s in samples], n_cols, n_rows, device=device),
        index=torch.tensor(index, dtype=torch.long, device=device),
        cells=torch.tensor(cells, dtype=torch.long, device=device),
        tiles=torch.tensor(tiles, dtype=torch.long, device=device),
        rotations=torch.tensor(rotations, dtype=torch.long, device=device),
        probs=torch.tensor(probs, dtype=torch.float32, device=device),
        value=torch.tensor(
            [s.value for s in samples], dtype=torch.float32, device=device
        ),
    )


def legal_normaliser(
    cell_logits: Tensor,
    tile_logits: Tensor,
    rotation_logits: Tensor,
    planes: Tensor,
) -> Tensor:
    """``log Σ exp(score)`` over the legal moves, in closed form.

    Reads the empty-cell mask and the mover's hand straight off the input
    planes, and uses the static rotation-orbit table. No move generation.

    Args:
        cell_logits: ``(B, n_cells)``.
        tile_logits: ``(B, 13)``.
        rotation_logits: ``(B, 6)``.
        planes: ``(B, N_PLANES, n_cols, n_rows)``, the same input the logits
            came from.

    Returns:
        ``(B,)`` normalisers.
    """
    batch = planes.shape[0]
    empty = planes[:, EMPTY_PLANE].reshape(batch, -1).bool()
    # Hand planes are constant across the board, so one cell carries the bit.
    hand = planes[:, OWN_HAND_PLANE : OWN_HAND_PLANE + N_HAND_PLANES, 0, 0].bool()

    cells = torch.logsumexp(cell_logits.masked_fill(~empty, NEG_INF), dim=1)

    pairs = tile_logits.unsqueeze(2) + rotation_logits.unsqueeze(1)  # (B, 13, 6)
    available = hand.unsqueeze(2) & ORBIT_MASK.to(planes.device).unsqueeze(0)
    pairs = torch.logsumexp(
        pairs.masked_fill(~available, NEG_INF).reshape(batch, -1), dim=1
    )

    return cells + pairs


def policy_loss(
    cell_logits: Tensor,
    tile_logits: Tensor,
    rotation_logits: Tensor,
    batch: Batch,
) -> Tensor:
    """Mean cross-entropy between the search policy and the network's.

    ``Σ_m π(m) = 1`` for every sample, so the cross-entropy reduces to
    ``Z − Σ_m π(m) · score(m)`` and the normaliser is the only term needing the
    full legal set.
    """
    size = len(batch)
    normaliser = legal_normaliser(
        cell_logits, tile_logits, rotation_logits, batch.planes
    )

    scores = (
        cell_logits[batch.index, batch.cells]
        + tile_logits[batch.index, batch.tiles]
        + rotation_logits[batch.index, batch.rotations]
    )
    expected = torch.zeros(size, device=scores.device, dtype=scores.dtype)
    expected.index_add_(0, batch.index, batch.probs * scores)

    return (normaliser - expected).mean()


def value_loss(predicted: Tensor, target: Tensor) -> Tensor:
    """Mean-squared error on an outcome that is always exactly ±1."""
    return torch.nn.functional.mse_loss(predicted, target)


def train_step(
    net: FlipHexNet,
    optimiser: torch.optim.Optimizer,
    batch: Batch,
    *,
    value_weight: float = VALUE_WEIGHT,
) -> dict[str, float]:
    """One gradient step. Returns the losses for the run log."""
    net.train()
    optimiser.zero_grad(set_to_none=True)

    cell_logits, tile_logits, rotation_logits, value = net(batch.planes)
    policy = policy_loss(cell_logits, tile_logits, rotation_logits, batch)
    outcome = value_loss(value, batch.value)
    total = policy + value_weight * outcome

    total.backward()
    optimiser.step()

    return {
        "policy": policy.detach().item(),
        "value": outcome.detach().item(),
        "total": total.detach().item(),
    }


def train_generation(
    net: FlipHexNet,
    optimiser: torch.optim.Optimizer,
    buffer: ReplayBuffer,
    *,
    steps: int,
    batch_size: int,
    n_cols: int,
    n_rows: int,
    value_weight: float = VALUE_WEIGHT,
) -> list[dict[str, float]]:
    """Run ``steps`` gradient steps against ``buffer``.

    Batches are drawn from the buffer's own RNG, which the checkpoint saves, so
    a resumed run trains on the same batches an uninterrupted one would have.
    """
    history = []
    for _ in range(steps):
        batch = make_batch(buffer.sample(batch_size), n_cols, n_rows)
        history.append(train_step(net, optimiser, batch, value_weight=value_weight))
    return history
