"""Tests for fliphex.board.

Two kinds of checks:

- **Independent facts** taken from docs/rules-canonical.md (the worked example)
  and the board's structural properties. These hold even if the generator has
  the same bug as the engine.
- **Cross-check against scripts/gen_board_geometry.py**, the canonical source of
  the adjacency table (risk R12 — the engine must not drift from the docs).
"""

import gen_board_geometry as geo
import pytest

from fliphex.board import DIRECTION_NAMES, OFF_BOARD, Board


def _named_neighbours(board: Board, cid: int) -> dict[str, str | None]:
    """Map direction name -> neighbour cell name (or None off-board)."""
    return {
        DIRECTION_NAMES[i]: (board.cell_name(n) if n != OFF_BOARD else None)
        for i, n in enumerate(board.neighbours(cid))
    }


# -- independent facts --------------------------------------------------------


def test_full_board_is_5x5_25_cells():
    board = Board()
    assert (board.n_cols, board.n_rows, board.n_cells) == (5, 5, 25)
    assert board.cell_name(0) == "A1"
    assert board.cell_name(board.n_cells - 1) == "E5"


def test_worked_example_c3_neighbours():
    # docs/rules-canonical.md §8: C3's neighbours by direction.
    board = Board()
    assert _named_neighbours(board, board.cell_id("C3")) == {
        "N": "C2",
        "NE": "D2",
        "SE": "D3",
        "S": "C4",
        "SW": "B3",
        "NW": "B2",
    }


def test_a1_is_a_degree_two_corner():
    board = Board()
    a1 = board.cell_id("A1")
    assert board.degree(a1) == 2
    nb = _named_neighbours(board, a1)
    assert nb["SE"] == "B1" and nb["S"] == "A2"
    assert nb["N"] is nb["NE"] is nb["SW"] is nb["NW"] is None


def test_adjacency_is_symmetric():
    # X neighbours Y in direction d  <=>  Y neighbours X in direction d+3.
    board = Board()
    for cid in board.cells:
        for d in range(6):
            n = board.neighbour(cid, d)
            if n != OFF_BOARD:
                assert board.neighbour(n, (d + 3) % 6) == cid


def test_name_id_roundtrip():
    board = Board()
    for cid in board.cells:
        assert board.cell_id(board.cell_name(cid)) == cid


def test_edge_count_is_56():
    board = Board()
    total = sum(board.degree(cid) for cid in board.cells)
    assert total % 2 == 0
    assert total // 2 == 56


# -- input validation ---------------------------------------------------------


@pytest.mark.parametrize("bad", ["F1", "A6", "A0", "A", "1", "AA"])
def test_cell_id_rejects_bad_names(bad):
    board = Board()
    with pytest.raises(ValueError):
        board.cell_id(bad)


@pytest.mark.parametrize("dims", [(0, 5), (5, 0), (27, 5)])
def test_constructor_rejects_bad_dimensions(dims):
    with pytest.raises(ValueError):
        Board(*dims)


# -- reduced variants (Phase 3 depends on this) -------------------------------


def test_reduced_3x3_is_sized_and_symmetric():
    board = Board(3, 3)
    assert board.n_cells == 9
    assert board.cell_name(0) == "A1"
    assert board.cell_name(8) == "C3"
    for cid in board.cells:
        for d in range(6):
            n = board.neighbour(cid, d)
            if n != OFF_BOARD:
                assert board.neighbour(n, (d + 3) % 6) == cid


# -- cross-check against the canonical generator (R12) ------------------------


def test_cell_names_match_generator():
    board = Board()
    for col in range(geo.N_COLS):
        for row in range(geo.N_ROWS):
            cid = col * board.n_rows + row
            assert board.cell_name(cid) == geo.cell_name(col, row)


def test_adjacency_matches_generator():
    board = Board()
    for col in range(geo.N_COLS):
        for row in range(geo.N_ROWS):
            cid = col * board.n_rows + row
            got = [
                board.cell_name(n) if n != OFF_BOARD else None
                for n in board.neighbours(cid)
            ]
            assert got == geo.neighbours(col, row)


def test_degree_histogram_matches_generator():
    board = Board()
    hist: dict[int, int] = {}
    for cid in board.cells:
        d = board.degree(cid)
        hist[d] = hist.get(d, 0) + 1
    assert dict(sorted(hist.items())) == geo.degree_histogram()


def test_edge_count_matches_generator():
    board = Board()
    total = sum(board.degree(cid) for cid in board.cells) // 2
    assert total == geo.edge_count()
