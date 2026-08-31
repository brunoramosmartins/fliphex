"""State to input planes, from the mover's point of view.

Thirty binary planes over the board grid. Every plane is 0/1, so a position is
one byte per cell per plane and the encoder needs neither torch nor numpy —
``az/network.py`` turns the buffer into a tensor at the last moment. Keeping the
encoder free of both is deliberate: it is the piece self-play would need if
generation ever moved to a faster interpreter, and it lets the replay buffer
store positions without a tensor library in the loop.

The plane table
---------------
==========  ================================================================
plane       content
==========  ================================================================
0           own colour, per cell
1           opponent colour, per cell
2           empty, per cell
3           side to move (constant)
4..16       own hand: one constant plane per tile still held (13)
17..29      opponent hand: one constant plane per tile still held (13)
==========  ================================================================

"Own" and "opponent" are relative to :attr:`GameState.to_move`, so the network
always sees the position from the perspective of the player it is choosing for
and the value head's ``+1`` always means "good for the mover".

There is no orientation plane. Placed tiles are inert — arrows fire once, on the
ply the tile is placed — so rotation is not part of the state at all.

Thirty planes, not twenty-nine
------------------------------
The architecture decision this implements specifies **29** planes, splitting the
hands as 13 own and 12 opponent. That table does not survive the perspectival
encoding it sits next to, and the discrepancy is not cosmetic.

On the full board the first player's hand is the twelve archetypes **plus the
joker** — thirteen tiles — and the second player's is the twelve archetypes.
Under "own/opponent relative to the mover", the opponent is the first player on
every second ply, and a 12-plane opponent block then has nowhere to put the
joker. The joker is exactly the tile that guarantees the first player the last
ply, so whether it has been spent is not a detail.

The bit is not lost in the information-theoretic sense: occupied cells give the
ply count, the ply count gives how many tiles each side has played, and
subtracting the visible archetype planes leaves the joker. But that is a global
count across the board, which is the operation a small convolutional tower is
worst at. Recovering it would cost the network more than the plane costs the
input.

Making both hand blocks 13 also makes the layout **variant-independent**: the
3x3, the 5x3 and the 5x5 differ only in spatial size, and the tile planes always
mean the same thing. The cross-variant comparison in the project's third
hypothesis reads across all three, so one layout for all three is worth having.

Recorded as a proposed amendment rather than a silent fix; the alternative
reading — "own" always means the first player, keeping 29 — would cost the
canonical orientation that makes the value head's sign meaningful.
"""

from __future__ import annotations

from fliphex.board import Board
from fliphex.state import TILES, Colour, GameState, other

#: Own, opponent, empty.
N_BOARD_PLANES = 3
#: Side to move, as a constant plane.
N_SIDE_PLANES = 1
#: One constant plane per tile, per player. 13 = 12 archetypes + the joker.
N_HAND_PLANES = len(TILES)

#: Total input channels. See the module docstring on why this is 30, not 29.
N_PLANES = N_BOARD_PLANES + N_SIDE_PLANES + 2 * N_HAND_PLANES

#: First plane of each block, for tests and for anyone reading a tensor by hand.
OWN_COLOUR_PLANE = 0
OPPONENT_COLOUR_PLANE = 1
EMPTY_PLANE = 2
SIDE_TO_MOVE_PLANE = 3
OWN_HAND_PLANE = 4
OPPONENT_HAND_PLANE = OWN_HAND_PLANE + N_HAND_PLANES


def encode(board: Board, state: GameState) -> bytes:
    """Return ``state`` as ``N_PLANES * board.n_cells`` bytes of 0/1.

    The buffer is plane-major: plane ``p`` of cell ``c`` is at index
    ``p * n_cells + c``. Cell ids are the board's own, so reshaping to
    ``(N_PLANES, n_cols, n_rows)`` lays the grid out the way the board does.

    Args:
        board: The geometry. Only ``n_cells`` is read.
        state: The position to encode.

    Returns:
        A ``bytes`` of length ``N_PLANES * board.n_cells``.
    """
    n_cells = board.n_cells
    planes = bytearray(N_PLANES * n_cells)

    mover = state.to_move
    opponent = other(mover)

    for cell in range(n_cells):
        colour = state.colours[cell]
        if colour == mover:
            planes[OWN_COLOUR_PLANE * n_cells + cell] = 1
        elif colour == opponent:
            planes[OPPONENT_COLOUR_PLANE * n_cells + cell] = 1
        else:
            planes[EMPTY_PLANE * n_cells + cell] = 1

    # The side-to-move plane is not redundant with the perspectival colours: the
    # two hands are not the same size, so it is what tells the network whether
    # the mover is the player holding the extra tile.
    if mover == Colour.PURPLE:
        _fill(planes, SIDE_TO_MOVE_PLANE, n_cells)

    _fill_hand(planes, OWN_HAND_PLANE, state.hand(mover), n_cells)
    _fill_hand(planes, OPPONENT_HAND_PLANE, state.hand(opponent), n_cells)

    return bytes(planes)


def _fill(planes: bytearray, plane: int, n_cells: int) -> None:
    """Set every cell of one constant plane to 1."""
    start = plane * n_cells
    planes[start : start + n_cells] = b"\x01" * n_cells


def _fill_hand(planes: bytearray, first: int, hand: int, n_cells: int) -> None:
    """Set one constant plane per tile still in ``hand``."""
    for tile in range(N_HAND_PLANES):
        if hand >> tile & 1:
            _fill(planes, first + tile, n_cells)


def plane_names() -> list[str]:
    """Return a human-readable name per plane, for debugging and the write-up."""
    names = ["own colour", "opponent colour", "empty", "side to move is P1"]
    for who in ("own", "opponent"):
        names += [f"{who} hand: {piece.archetype}" for piece in TILES]
    return names
