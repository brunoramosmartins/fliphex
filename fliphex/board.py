"""Board geometry: cells, coordinates, and the adjacency table.

The board is a honeycomb of flat-top hexagons in vertical columns, odd columns
dropped half a cell (odd-q offset). The full game is 5 columns of 5 = 25 cells,
but the class is parameterised by ``(n_cols, n_rows)`` so the reduced variants
of Phase 3 (3x3, 4x4) are first-class.

Per adr-002:

- **Axial** ``(q, r)`` is the internal coordinate; neighbour arithmetic is a
  parity-free constant offset per direction.
- **Offset labels** ``A1``..``E5`` are the human-facing names.
- Adjacency is precomputed once into a flat ``n_cells x 6`` table of cell ids,
  with :data:`OFF_BOARD` where a direction leaves the board.

Directions are indexed clockwise from North, matching docs/board-geometry.md::

    N=0, NE=1, SE=2, S=3, SW=4, NW=5
"""

from __future__ import annotations

#: Column labels, left to right. Indexed by column number.
COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#: Direction names, clockwise from North. Index i is arrow slot i at rotation 0.
DIRECTION_NAMES: tuple[str, ...] = ("N", "NE", "SE", "S", "SW", "NW")

#: Axial (dq, dr) per direction, same order as DIRECTION_NAMES.
_AXIAL_DELTAS: tuple[tuple[int, int], ...] = (
    (0, -1),  # N
    (1, -1),  # NE
    (1, 0),  # SE
    (0, 1),  # S
    (-1, 1),  # SW
    (-1, 0),  # NW
)

#: Sentinel returned by :meth:`Board.neighbour` when a direction leaves the board.
OFF_BOARD = -1


class Board:
    """A parameterised flat-top hex board with a precomputed adjacency table.

    Cells are integer ids ``0 .. n_cells-1`` laid out column-major, so
    ``id = col * n_rows + row`` and ``A1`` is id 0, ``A2`` is id 1, ``B1`` is
    id ``n_rows``. The layout matches ``scripts/gen_board_geometry.py`` exactly.

    The board carries no game state — only geometry — so one instance is shared
    across a whole game (and is safe to treat as immutable after construction).

    Attributes:
        n_cols: Number of columns.
        n_rows: Number of rows (cells per column).
        n_cells: ``n_cols * n_rows``.
    """

    def __init__(self, n_cols: int = 5, n_rows: int = 5) -> None:
        """Build the board and precompute its adjacency table.

        Args:
            n_cols: Columns, ``1 .. 26``.
            n_rows: Cells per column, ``>= 1``.

        Raises:
            ValueError: If the dimensions are out of range.
        """
        if not 1 <= n_cols <= len(COLS):
            raise ValueError(f"n_cols must be in 1..{len(COLS)}, got {n_cols}")
        if n_rows < 1:
            raise ValueError(f"n_rows must be >= 1, got {n_rows}")

        self.n_cols = n_cols
        self.n_rows = n_rows
        self.n_cells = n_cols * n_rows

        self._axial: tuple[tuple[int, int], ...] = tuple(
            self._to_axial(*self._colrow(cid)) for cid in range(self.n_cells)
        )
        axial_to_id = {axial: cid for cid, axial in enumerate(self._axial)}

        adjacency: list[tuple[int, ...]] = []
        for cid in range(self.n_cells):
            q, r = self._axial[cid]
            adjacency.append(
                tuple(
                    axial_to_id.get((q + dq, r + dr), OFF_BOARD)
                    for dq, dr in _AXIAL_DELTAS
                )
            )
        self._adjacency: tuple[tuple[int, ...], ...] = tuple(adjacency)

    # -- construction helpers -------------------------------------------------

    def _colrow(self, cid: int) -> tuple[int, int]:
        """Return the ``(col, row)`` of a cell id."""
        return divmod(cid, self.n_rows)

    @staticmethod
    def _to_axial(col: int, row: int) -> tuple[int, int]:
        """Convert odd-q offset ``(col, row)`` to axial ``(q, r)``."""
        return (col, row - (col - (col & 1)) // 2)

    # -- public geometry ------------------------------------------------------

    @property
    def cells(self) -> range:
        """All cell ids, ``0 .. n_cells-1``."""
        return range(self.n_cells)

    def cell_name(self, cid: int) -> str:
        """Return the human name (e.g. ``"C3"``) of a cell id."""
        col, row = self._colrow(cid)
        return f"{COLS[col]}{row + 1}"

    def cell_id(self, name: str) -> int:
        """Return the cell id for a name like ``"C3"``.

        Raises:
            ValueError: If the name is malformed or off the board.
        """
        name = name.strip().upper()
        if len(name) < 2 or not name[1:].isdigit():
            raise ValueError(f"malformed cell name: {name!r}")
        col = COLS.find(name[0])
        row = int(name[1:]) - 1
        if not (0 <= col < self.n_cols and 0 <= row < self.n_rows):
            raise ValueError(
                f"cell {name!r} is off a {self.n_cols}x{self.n_rows} board"
            )
        return col * self.n_rows + row

    def axial(self, cid: int) -> tuple[int, int]:
        """Return the axial ``(q, r)`` of a cell id."""
        return self._axial[cid]

    def neighbours(self, cid: int) -> tuple[int, ...]:
        """Return the 6 neighbour ids of ``cid``, :data:`OFF_BOARD` off-board.

        Entry ``i`` is the cell an arrow in direction ``i`` points at. This is
        the table the flip rule consumes.
        """
        return self._adjacency[cid]

    def neighbour(self, cid: int, direction: int) -> int:
        """Return the neighbour of ``cid`` in ``direction`` (0..5), or OFF_BOARD."""
        return self._adjacency[cid][direction]

    def degree(self, cid: int) -> int:
        """Return how many of ``cid``'s six directions stay on the board."""
        return sum(n != OFF_BOARD for n in self._adjacency[cid])

    def __repr__(self) -> str:
        return f"Board(n_cols={self.n_cols}, n_rows={self.n_rows})"
