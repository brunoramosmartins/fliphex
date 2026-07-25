"""Generate the adjacency tables in docs/board-geometry.md.

Phase 0 tool. Deliberately standalone: it does not import the `fliphex`
package (which does not exist yet in Phase 0) so that the canonical geometry
document can be regenerated and diffed independently of the engine. In Phase 1,
`fliphex/board.py` must reproduce these tables exactly; `tests/test_board.py`
checks that by importing the functions here.

Geometry (read off the 2017 physical board, see docs/board-geometry.md):
flat-top hexagons in 5 vertical columns of 5 cells, odd columns pushed down
half a cell. Columns are labelled A..E left to right, rows 1..5 top to bottom.

Run:  python scripts/gen_board_geometry.py
"""

from __future__ import annotations

COLS = "ABCDE"
N_COLS = 5
N_ROWS = 5

# The six arrow directions, clockwise from North. Index i is arrow slot i of a
# piece at rotation 0. Flat-top hexagons have an edge facing each of these.
DIRECTION_NAMES = ["N", "NE", "SE", "S", "SW", "NW"]
AXIAL_DELTAS = [(0, -1), (+1, -1), (+1, 0), (0, +1), (-1, +1), (-1, 0)]


def cell_name(col: int, row: int) -> str:
    """(0, 0) -> 'A1'."""
    return f"{COLS[col]}{row + 1}"


def to_axial(col: int, row: int) -> tuple[int, int]:
    """odd-q offset -> axial (q, r). Odd columns sit half a cell lower."""
    return (col, row - (col - (col & 1)) // 2)


def all_cells() -> list[tuple[int, int]]:
    return [(c, r) for c in range(N_COLS) for r in range(N_ROWS)]


def axial_to_offset() -> dict[tuple[int, int], tuple[int, int]]:
    return {to_axial(c, r): (c, r) for c, r in all_cells()}


def neighbours(col: int, row: int) -> list[str | None]:
    """Neighbour of (col, row) in each of the 6 directions, None if off-board.

    Indexed by direction: entry i is the cell that arrow slot i points at.
    This is exactly the map the flip rule consumes.
    """
    lookup = axial_to_offset()
    q, r = to_axial(col, row)
    out: list[str | None] = []
    for dq, dr in AXIAL_DELTAS:
        target = lookup.get((q + dq, r + dr))
        out.append(cell_name(*target) if target else None)
    return out


def degree(col: int, row: int) -> int:
    return sum(n is not None for n in neighbours(col, row))


def adjacency_table() -> str:
    lines = [
        "| Cell | axial (q,r) | " + " | ".join(DIRECTION_NAMES) + " | deg |",
        "|---|---|" + "---|" * 7,
    ]
    for col, row in sorted(all_cells(), key=lambda cr: (cr[1], cr[0])):
        ns = " | ".join(n if n else "—" for n in neighbours(col, row))
        q, r = to_axial(col, row)
        lines.append(
            f"| **{cell_name(col, row)}** | ({q},{r}) | {ns} | {degree(col, row)} |"
        )
    return "\n".join(lines)


def degree_histogram() -> dict[int, int]:
    hist: dict[int, int] = {}
    for col, row in all_cells():
        d = degree(col, row)
        hist[d] = hist.get(d, 0) + 1
    return dict(sorted(hist.items()))


def edge_count() -> int:
    total = sum(degree(c, r) for c, r in all_cells())
    assert total % 2 == 0, "adjacency must be symmetric"
    return total // 2


def check_symmetry() -> None:
    """X neighbours Y in direction d iff Y neighbours X in direction d+3."""
    for col, row in all_cells():
        for i, name in enumerate(neighbours(col, row)):
            if name is None:
                continue
            back = (COLS.index(name[0]), int(name[1]) - 1)
            assert neighbours(*back)[(i + 3) % 6] == cell_name(col, row), (
                f"asymmetric edge {cell_name(col, row)} -> {name} in dir {i}"
            )


def ascii_board() -> str:
    """Zigzag rendering. Odd columns are drawn half a row lower, as on the board."""
    grid: dict[tuple[int, int], str] = {}
    for col, row in all_cells():
        grid[(col, 2 * row + (col & 1))] = cell_name(col, row)
    lines = []
    for band in range(2 * N_ROWS + 1):
        cells = [grid.get((c, band), "  ") for c in range(N_COLS)]
        if any(x.strip() for x in cells):
            lines.append(" ".join(f"({x})" if x.strip() else "    " for x in cells))
    return "\n".join(lines)


if __name__ == "__main__":
    check_symmetry()
    print(ascii_board())
    print()
    print(adjacency_table())
    print()
    print("degree histogram:", degree_histogram())
    print("edges:", edge_count())
