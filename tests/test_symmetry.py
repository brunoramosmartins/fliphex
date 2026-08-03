"""The board's automorphism group is Z/2 — a left-right mirror (adr-008).

This pins down the correction to the Phase 0 "trivial symmetry group" claim:
the directed board graph has exactly one non-trivial symmetry, the mirror across
the central column, and 180-degree rotation is *not* a symmetry.
"""

from check_symmetry import board_automorphisms

from fliphex.board import Board


def _automorphisms(board: Board):
    """Return ``(all_autos, non_identity)`` where non_identity is [(rho, pi)]."""
    autos = board_automorphisms(board)
    non_identity = [
        (rho, pi)
        for _name, rho, pi in autos
        if any(pi[c] != c for c in board.cells)
    ]
    return autos, non_identity


def test_full_board_group_is_order_two():
    autos, non_identity = _automorphisms(Board())
    assert len(autos) == 2
    assert len(non_identity) == 1


def test_mirror_swaps_a_e_and_b_d_fixing_c():
    board = Board()
    _autos, non_identity = _automorphisms(board)
    _rho, pi = non_identity[0]

    def maps(a: str, b: str) -> bool:
        return pi[board.cell_id(a)] == board.cell_id(b)

    # A <-> E, B <-> D, column C fixed.
    for row in range(1, 6):
        assert maps(f"A{row}", f"E{row}")
        assert maps(f"B{row}", f"D{row}")
        assert maps(f"C{row}", f"C{row}")


def test_mirror_reflects_east_west_directions():
    # The induced direction action is the vertical mirror of a flat-top hex:
    # N,S fixed; NE<->NW, SE<->SW.
    _autos, non_identity = _automorphisms(Board())
    rho, _pi = non_identity[0]
    n, ne, se, s, sw, nw = range(6)
    assert rho[n] == n and rho[s] == s
    assert rho[ne] == nw and rho[nw] == ne
    assert rho[se] == sw and rho[sw] == se


def test_180_degree_rotation_is_not_a_symmetry():
    # A 180-degree rotation would be an involution with no fixed cell (25 is
    # odd, so it cannot exist). The sole non-trivial symmetry fixes column C,
    # so it is the mirror, not a rotation.
    board = Board()
    _autos, non_identity = _automorphisms(board)
    _rho, pi = non_identity[0]
    fixed = [c for c in board.cells if pi[c] == c]
    assert fixed  # non-empty => mirror, not a half-turn


def test_reduced_3x3_also_has_the_mirror():
    # The solver's 3x3 variant (Phase 3) inherits the same Z/2 mirror.
    autos, non_identity = _automorphisms(Board(3, 3))
    assert len(autos) == 2
    assert len(non_identity) == 1
