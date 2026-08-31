"""The residual tower, the factored policy head, and the value head.

A small network for a small game: 25 plies, no draws, and a state space around
5e17. The published AlphaZero tower — 20 to 40 blocks of 256 filters — is wildly
oversized here, so this is a 3x3 convolutional stem into 64 filters, four
residual blocks, and two heads.

The factored policy head
------------------------
A move is ``(cell, tile, rotation)`` = 25 x 13 x 6 = **1,950** slots, of which at
most 1,450 are ever legal. A flat head over 1,950 logits, trained on games 25
plies long, is a poor ratio of parameters to signal. The head instead emits
three factors — ``n_cells`` cell logits, 13 tile logits, 6 rotation logits, so
**44** on the full board — and scores a move by summing them.

This assumes cell, tile and rotation are conditionally independent given the
state, which is **false**: the best rotation depends heavily on the cell. That
is the main modelling risk on this axis and it is checked explicitly rather than
assumed away. The fallbacks, in order, are to condition the rotation logits on
the chosen cell, and then a flat 1,950-logit head. Neither fixes action aliasing
— only deduplicated expansion in the search does that.

Summing raw logits is exactly the specified rule
------------------------------------------------
The head is specified as ``log p(cell) + log p(tile) + log p(rotation)``, masked
to the legal moves and renormalised. :func:`masked_log_policy` sums the *raw*
logits instead, which is the same distribution: each ``log softmax`` differs
from its logits by a term constant across moves, and three constants added to
every legal move's score vanish in the renormalisation. Summing raw logits saves
three softmaxes and is better conditioned.

Masking is not a detail
-----------------------
Renormalising over legal moves only is what keeps the head honest: the factored
score assigns mass to combinations that are not legal moves at all — a tile no
longer in hand, an occupied cell, a rotation duplicated by the tile's symmetry
orbit. Those never reach the search.

This module imports the game engine and nothing else from the project. In
particular it never imports the exact solver, so no trained network can be
selected using ground truth the two axes are later compared against.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

from az.encoding import N_HAND_PLANES, N_PLANES, encode
from fliphex.board import Board
from fliphex.moves import Move
from fliphex.piece import N_SLOTS
from fliphex.state import GameState

#: Rotations a tile can be placed at, before its symmetry orbit collapses some.
N_ROTATIONS = N_SLOTS


class ResidualBlock(nn.Module):
    """Two 3x3 convolutions with a skip connection, pre-activation ordering."""

    def __init__(self, filters: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(filters, filters, 3, padding=1, bias=False)
        self.norm1 = nn.BatchNorm2d(filters)
        self.conv2 = nn.Conv2d(filters, filters, 3, padding=1, bias=False)
        self.norm2 = nn.BatchNorm2d(filters)

    def forward(self, x: Tensor) -> Tensor:
        y = torch.relu(self.norm1(self.conv1(x)))
        y = self.norm2(self.conv2(y))
        return torch.relu(x + y)


class FlipHexNet(nn.Module):
    """Residual tower with a factored policy head and a scalar value head.

    Args:
        n_cols: Board columns. 5 on the full game.
        n_rows: Cells per column. 5 on the full game.
        filters: Channels in the tower.
        blocks: Residual blocks.

    The board is laid on a square grid, so a 3x3 kernel's neighbourhood does not
    match hex adjacency — and it cannot, since the offset layout makes a hex
    neighbour's position depend on column parity while conv weights are shared.
    Four blocks give a receptive field covering the whole board, so the network
    can learn the true adjacency rather than have it built in. A hex-aware
    convolution is not worth it at this size.
    """

    def __init__(
        self,
        n_cols: int = 5,
        n_rows: int = 5,
        *,
        filters: int = 64,
        blocks: int = 4,
    ) -> None:
        super().__init__()
        self.n_cols = n_cols
        self.n_rows = n_rows
        self.n_cells = n_cols * n_rows

        self.stem = nn.Sequential(
            nn.Conv2d(N_PLANES, filters, 3, padding=1, bias=False),
            nn.BatchNorm2d(filters),
            nn.ReLU(inplace=True),
        )
        self.tower = nn.Sequential(*(ResidualBlock(filters) for _ in range(blocks)))

        # -- policy head: three factors, 1x1 conv down then one linear each ----
        self.policy_conv = nn.Sequential(
            nn.Conv2d(filters, 32, 1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Flatten(),
        )
        policy_features = 32 * self.n_cells
        self.cell_head = nn.Linear(policy_features, self.n_cells)
        self.tile_head = nn.Linear(policy_features, N_HAND_PLANES)
        self.rotation_head = nn.Linear(policy_features, N_ROTATIONS)

        # -- value head -------------------------------------------------------
        self.value_head = nn.Sequential(
            nn.Conv2d(filters, 1, 1, bias=False),
            nn.BatchNorm2d(1),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(self.n_cells, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
            nn.Tanh(),
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        """Return ``(cell_logits, tile_logits, rotation_logits, value)``.

        Args:
            x: ``(batch, N_PLANES, n_cols, n_rows)`` float tensor.

        Returns:
            Three logit tensors and a ``(batch,)`` value in ``[-1, 1]``, read
            from the point of view of the side to move. ``z`` is always exactly
            +/-1 in training because draws are impossible on an odd cell count.
        """
        features = self.tower(self.stem(x))
        policy = self.policy_conv(features)
        return (
            self.cell_head(policy),
            self.tile_head(policy),
            self.rotation_head(policy),
            self.value_head(features).squeeze(-1),
        )

    def count_parameters(self) -> int:
        """Return the number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class FlatHeadNet(FlipHexNet):
    """The same tower, with one logit per ``(cell, tile, rotation)`` triple.

    This is the fallback the architecture record keeps in reserve, and the arm
    the factored head is measured against. It **subclasses** rather than
    reimplements: the registration promises the two arms share a tower,
    optimiser, epochs and batch order, and inheriting the constructor makes that
    structurally true instead of a claim someone has to re-verify.

    The head spans the **full** action space — ``n_cells x 13 x 6``, so 1,170 on
    the 5x3 — not the tiles a particular deck happens to hold. Sizing it to the
    deck would hand this arm a fact the factored arm is not given, and would
    bias the comparison toward the head whose win amends the architecture.

    Note it does **not** fix action aliasing: 1,170 logits over 540 legal moves
    is the same redundancy with more parameters. Only deduplicated expansion in
    the search addresses that.
    """

    def __init__(self, n_cols: int = 5, n_rows: int = 5, **kwargs) -> None:
        super().__init__(n_cols, n_rows, **kwargs)
        del self.cell_head, self.tile_head, self.rotation_head
        self.flat_head = nn.Linear(
            32 * self.n_cells, self.n_cells * N_HAND_PLANES * N_ROTATIONS
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:  # type: ignore[override]
        """Return ``(flat_logits, value)``.

        The signature differs from the factored head's deliberately: these are
        different parameterisations of the policy, and a caller that has to
        branch on which one it holds is better than one that silently treats a
        1,170-wide tensor as a 15-wide one.
        """
        features = self.tower(self.stem(x))
        policy = self.policy_conv(features)
        return self.flat_head(policy), self.value_head(features).squeeze(-1)


def flat_index(move: Move) -> int:
    """Position of ``move`` in a flat head's output.

    ``(cell * 13 + tile) * 6 + rotation``, matching the ``(cells, tiles,
    rotations)`` ordering the masks in :mod:`az.train` are built with.
    """
    return (move.cell * N_HAND_PLANES + move.tile) * N_ROTATIONS + move.rotation


def flat_masked_log_policy(logits: Tensor, moves: list[Move]) -> Tensor:
    """Score ``moves`` from a flat head and renormalise over them.

    Args:
        logits: ``(n_cells * 13 * 6,)`` for a single position.
        moves: The legal moves. Must be non-empty.

    Returns:
        ``(len(moves),)`` log-probabilities.

    Raises:
        ValueError: If ``moves`` is empty.
    """
    if not moves:
        raise ValueError("no legal moves: a terminal position has no policy")
    index = torch.tensor([flat_index(m) for m in moves], device=logits.device)
    return torch.log_softmax(logits[index], dim=0)


def to_tensor(
    buffers: bytes | list[bytes],
    n_cols: int,
    n_rows: int,
    *,
    device: torch.device | str = "cpu",
) -> Tensor:
    """Turn one or more :func:`az.encoding.encode` buffers into a batch tensor.

    Args:
        buffers: One encoded position, or a list of them.
        n_cols: Board columns.
        n_rows: Cells per column.
        device: Where to put the tensor.

    Returns:
        A ``(batch, N_PLANES, n_cols, n_rows)`` float tensor.
    """
    if isinstance(buffers, bytes):
        buffers = [buffers]
    flat = torch.frombuffer(bytearray(b"".join(buffers)), dtype=torch.uint8)
    return flat.view(len(buffers), N_PLANES, n_cols, n_rows).to(device, torch.float32)


def masked_log_policy(
    cell_logits: Tensor,
    tile_logits: Tensor,
    rotation_logits: Tensor,
    moves: list[Move],
) -> Tensor:
    """Score ``moves`` from the three factors and renormalise over them.

    Args:
        cell_logits: ``(n_cells,)`` for a single position.
        tile_logits: ``(13,)``.
        rotation_logits: ``(6,)``.
        moves: The legal moves to distribute mass over. Must be non-empty.

    Returns:
        A ``(len(moves),)`` tensor of log-probabilities summing to 1 in
        probability space.

    Raises:
        ValueError: If ``moves`` is empty. A terminal position has no policy,
            and silently returning an empty distribution would let a caller
            average over nothing.
    """
    if not moves:
        raise ValueError("no legal moves: a terminal position has no policy")

    cells = torch.tensor([m.cell for m in moves], device=cell_logits.device)
    tiles = torch.tensor([m.tile for m in moves], device=cell_logits.device)
    rotations = torch.tensor([m.rotation for m in moves], device=cell_logits.device)

    scores = cell_logits[cells] + tile_logits[tiles] + rotation_logits[rotations]
    return torch.log_softmax(scores, dim=0)


class NetworkEvaluator:
    """Adapts a network to the search's ``prior`` and ``evaluate`` hooks.

    The search calls both on the same position, one immediately after the other:
    ``_expand`` asks for the priors and the very next line asks for the leaf
    value. Wired naively that is **two forward passes over identical input**,
    which at the measured batch-1 cost of 0.90 ms takes a simulation from
    2.18 ms to 3.08 ms — a 41% increase in the whole self-play budget, about 24
    hours over a five-seed run.

    So one result is cached, keyed on the state *object*. ``_expand`` and
    ``evaluate`` receive the same instance, so the check is an identity test and
    always hits. If that call pattern ever changes the cache simply misses and
    the network is asked again: the optimisation cannot make an answer wrong,
    only slower.

    Args:
        net: The network to evaluate with.
        board: The geometry, needed to encode.
    """

    def __init__(self, net: FlipHexNet, board: Board) -> None:
        self.net = net
        self.board = board
        self.forwards = 0
        self._state: GameState | None = None
        self._cell: Tensor | None = None
        self._tile: Tensor | None = None
        self._rotation: Tensor | None = None
        self._value: float = 0.0

    def _ensure(self, state: GameState) -> None:
        if self._state is state:
            return
        was_training = self.net.training
        self.net.eval()
        try:
            with torch.no_grad():
                x = to_tensor(
                    encode(self.board, state), self.board.n_cols, self.board.n_rows
                )
                cell, tile, rotation, value = self.net(x)
        finally:
            self.net.train(was_training)
        self._state = state
        self._cell, self._tile, self._rotation = cell[0], tile[0], rotation[0]
        self._value = float(value[0])
        self.forwards += 1

    def prior(self, board: Board, state: GameState, moves: list[Move]) -> list[float]:
        """Priors over ``moves``, matching the search's ``PriorFn`` signature."""
        self._ensure(state)
        log_priors = masked_log_policy(self._cell, self._tile, self._rotation, moves)
        return log_priors.exp().tolist()

    def evaluate(self, board: Board, state: GameState) -> float:
        """The leaf value for ``state``'s mover, matching ``Evaluator``."""
        self._ensure(state)
        return self._value


class FlatNetworkEvaluator(NetworkEvaluator):
    """:class:`NetworkEvaluator` for a :class:`FlatHeadNet`.

    Same one-entry cache and the same reason for it: the search asks for the
    priors and the leaf value on the same state, one line apart.
    """

    def _ensure(self, state: GameState) -> None:
        if self._state is state:
            return
        was_training = self.net.training
        self.net.eval()
        try:
            with torch.no_grad():
                x = to_tensor(
                    encode(self.board, state), self.board.n_cols, self.board.n_rows
                )
                logits, value = self.net(x)
        finally:
            self.net.train(was_training)
        self._state = state
        self._logits = logits[0]
        self._value = float(value[0])
        self.forwards += 1

    def prior(self, board: Board, state: GameState, moves: list[Move]) -> list[float]:
        self._ensure(state)
        return flat_masked_log_policy(self._logits, moves).exp().tolist()


@torch.no_grad()
def policy_and_value(
    net: FlipHexNet,
    board: Board,
    state: GameState,
    moves: list[Move],
) -> tuple[list[float], float]:
    """Evaluate one position: priors over ``moves``, and the value for the mover.

    This is the adapter the search uses. It is batch-1 by construction, which
    the environment measurements show is the expensive way to call the network —
    a batched evaluator is the optimisation, and it belongs in the self-play
    loop where several games can be advanced together, not here.

    The training mode is saved and restored rather than simply set: evaluation
    happens inside the training loop too, and a helper that quietly left the
    network in ``eval`` would freeze every batch-norm layer for the rest of the
    run without raising anything.
    """
    was_training = net.training
    net.eval()
    try:
        x = to_tensor(encode(board, state), board.n_cols, board.n_rows)
        cell_logits, tile_logits, rotation_logits, value = net(x)
        log_priors = masked_log_policy(
            cell_logits[0], tile_logits[0], rotation_logits[0], moves
        )
        return log_priors.exp().tolist(), float(value[0])
    finally:
        net.train(was_training)
